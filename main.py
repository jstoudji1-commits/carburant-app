from fastapi import FastAPI, Request
from fastapi import HTTPException
from fastapi.responses import PlainTextResponse
from fastapi.templating import Jinja2Templates

from typing import Literal, Optional
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field


import asyncio
import csv
from contextlib import asynccontextmanager, suppress
from datetime import datetime
from email.message import EmailMessage
import hashlib
import hmac
import json
import logging
import math
import os
from pathlib import Path
import re
import secrets
import smtplib
import ssl
import threading
import time
import requests as http_requests
from update_data import (
    date_derniere_mise_a_jour,
    mettre_a_jour_stations,
    signature_adresse,
    texte_derniere_mise_a_jour,
)


INTERVALLE_MISE_A_JOUR_SECONDES = 10 * 60
RETARD_MISE_A_JOUR_TOLERE_SECONDES = 60
logger = logging.getLogger("optiplein.update")
MISE_A_JOUR_FOND_ACTIVE = os.getenv(
    "OPTIPLEIN_BACKGROUND_UPDATE",
    "false",
).strip().lower() in {"1", "true", "yes", "on"}
EMAIL_SIGNALEMENT = os.getenv(
    "REPORT_EMAIL",
    "optiplein5@gmail.com"
)
ADSENSE_CLIENT = os.getenv(
    "ADSENSE_CLIENT",
    "ca-pub-4904497922619715",
).strip()
ADSENSE_SLOT_MAP = os.getenv("ADSENSE_SLOT_MAP", "").strip()
signalements_recents = {}
mise_a_jour_admin_lock = threading.Lock()
ATTENTE_VERROU_ADMIN_SECONDES = 45
DOSSIER_DONNEES_UTILISATEURS = Path(
    os.getenv("OPTIPLEIN_DATA_DIR", ".")
)
COMPTES_UTILISATEURS_FICHIER = (
    DOSSIER_DONNEES_UTILISATEURS
    / "comptes_utilisateurs.json"
)
TESTEURS_FICHIER = (
    DOSSIER_DONNEES_UTILISATEURS
    / "testeurs_landing.json"
)
STATIONS_REPO_CSV = Path(__file__).resolve().parent / "stations.csv"
STATIONS_RUNTIME_CSV = DOSSIER_DONNEES_UTILISATEURS / "stations.csv"
ENRICHISSEMENT_STATIONS_REPO_FICHIER = (
    Path(__file__).resolve().parent
    / "stations_enrichment.json"
)
ENRICHISSEMENT_STATIONS_ADMIN_FICHIER = (
    DOSSIER_DONNEES_UTILISATEURS
    / "stations_enrichment.json"
)
ADMIN_PASSWORD = os.getenv(
    "ADMIN_PASSWORD",
    "",
)
def lire_variable_graphhopper():

    for nom_variable in (
        "GRAPHHOPPER_API_KEY",
        "GRAPH_HOPPER_API_KEY",
        "GRAPHHOPPER_KEY",
        "GRAPHOPPER_API_KEY",
    ):
        valeur = os.getenv(nom_variable, "").strip()
        if valeur:
            return valeur

    return ""


GRAPHHOPPER_API_KEY = lire_variable_graphhopper()
SESSIONS_UTILISATEURS = {}
PBKDF2_ITERATIONS = 260000


class SignalementProbleme(BaseModel):

    model_config = ConfigDict(extra="forbid")

    categorie: Literal[
        "Prix ou station",
        "Carte ou GPS",
        "Itineraire",
        "Affichage",
        "Autre",
    ]
    description: str = Field(min_length=10, max_length=2000)
    station: str = Field(default="", max_length=160)
    email: str = Field(default="", max_length=160)
    page: str = Field(default="", max_length=300)
    site_web: str = Field(default="", max_length=120)


class CompteIdentifiants(BaseModel):

    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=5, max_length=160)
    mot_de_passe: str = Field(min_length=8, max_length=120)


class DonneesCompte(BaseModel):

    model_config = ConfigDict(extra="allow")

    favoris: list = Field(default_factory=list)
    vehicules: list = Field(default_factory=list)
    vehicule_actif: str = ""
    plan: Literal["free", "premium"] = "free"
    historique_economies: list = Field(default_factory=list)


class PointItineraire(BaseModel):

    model_config = ConfigDict(extra="forbid")

    latitude: float
    longitude: float


def formater_libelle_adresse_francaise(feature, recherche):

    proprietes = feature.get("properties", {})
    ville = " ".join(
        morceau
        for morceau in (
            proprietes.get("postcode", ""),
            proprietes.get("city", ""),
        )
        if morceau
    )
    libelle = ", ".join(
        morceau
        for morceau in (
            proprietes.get("name", ""),
            ville,
        )
        if morceau
    )
    return libelle or proprietes.get("label") or recherche


def rechercher_adresses_francaises(recherche, limite):

    reponse = http_requests.get(
        "https://api-adresse.data.gouv.fr/search/",
        params={
            "q": recherche,
            "limit": limite,
            "autocomplete": 1,
        },
        timeout=8,
    )
    reponse.raise_for_status()

    suggestions = []
    for feature in reponse.json().get("features", []):
        coordonnees = feature.get("geometry", {}).get("coordinates", [])
        if len(coordonnees) < 2:
            continue

        longitude, latitude = coordonnees[:2]
        score = feature.get("properties", {}).get("score", 0)
        if score < 0.28:
            continue

        suggestions.append({
            "latitude": latitude,
            "longitude": longitude,
            "libelle": formater_libelle_adresse_francaise(
                feature,
                recherche,
            ),
            "source": "adresse.data.gouv.fr",
            "score": score,
        })

    return suggestions


def formater_libelle_adresse_osm(resultat, recherche):

    adresse = resultat.get("address", {}) or {}
    nom = (
        resultat.get("name")
        or adresse.get("amenity")
        or adresse.get("building")
        or adresse.get("road")
        or recherche
    )
    ville = (
        adresse.get("city")
        or adresse.get("town")
        or adresse.get("village")
        or adresse.get("municipality")
    )
    code_postal = adresse.get("postcode", "")
    localisation = " ".join(
        morceau for morceau in (code_postal, ville) if morceau
    )

    if localisation:
        return f"{nom}, {localisation}"

    return resultat.get("display_name") or recherche


def rechercher_adresses_osm(recherche, limite):

    reponse = http_requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={
            "format": "json",
            "addressdetails": 1,
            "limit": limite,
            "countrycodes": "fr,be,lu,de,es,it",
            "q": recherche,
        },
        headers={
            "User-Agent": "OptiPlein/1.0",
            "Accept": "application/json",
        },
        timeout=4,
    )
    reponse.raise_for_status()

    suggestions = []
    for resultat in reponse.json() or []:
        try:
            latitude = float(resultat.get("lat"))
            longitude = float(resultat.get("lon"))
        except (TypeError, ValueError):
            continue

        suggestions.append({
            "latitude": latitude,
            "longitude": longitude,
            "libelle": formater_libelle_adresse_osm(resultat, recherche),
            "source": "openstreetmap",
            "score": float(resultat.get("importance") or 0),
        })

    return suggestions


def dedoublonner_adresses(suggestions, limite):

    adresses = []
    signatures = set()

    for suggestion in suggestions:
        libelle_signature = suggestion["libelle"].strip().lower()
        signature = (
            round(float(suggestion["latitude"]), 4),
            round(float(suggestion["longitude"]), 4),
            libelle_signature,
        )
        if signature in signatures or libelle_signature in signatures:
            continue

        signatures.add(signature)
        signatures.add(libelle_signature)
        adresses.append(suggestion)

        if len(adresses) >= limite:
            break

    return adresses


def recherche_ressemble_a_adresse(recherche):

    texte = recherche.lower()
    mots_adresse = (
        "rue",
        "avenue",
        "av ",
        "boulevard",
        "bd ",
        "chemin",
        "route",
        "impasse",
        "allee",
        "allée",
        "place",
        "quai",
        "cours",
    )

    return bool(re.search(r"\d", texte)) or any(
        mot in texte for mot in mots_adresse
    )


class RequeteItineraire(BaseModel):

    model_config = ConfigDict(extra="forbid")

    points: list[PointItineraire] = Field(min_length=2, max_length=12)
    cap_depart: Optional[float] = None
    moteur: Literal["auto", "graphhopper", "osrm"] = "auto"


class SauvegardeCompte(BaseModel):

    model_config = ConfigDict(extra="forbid")

    donnees: DonneesCompte


class AdminChangementPlan(BaseModel):

    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=5, max_length=160)
    plan: Literal["free", "premium"]


class AdminCorrectionStation(BaseModel):

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=32)
    enseigne: str = Field(default="", max_length=120)
    adresse: str = Field(default="", max_length=180)
    cp: str = Field(default="", max_length=12)
    ville: str = Field(default="", max_length=90)
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class InscriptionTesteur(BaseModel):

    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=5, max_length=160)
    source: str = Field(default="landing", max_length=80)


def normaliser_email(email):

    return email.strip().lower()


def email_valide(email):

    return bool(
        re.fullmatch(
            r"[^\s@]+@[^\s@]+\.[^\s@]+",
            email,
        )
    )


def charger_comptes_utilisateurs():

    if not COMPTES_UTILISATEURS_FICHIER.exists():
        return {"users": {}}

    try:
        with COMPTES_UTILISATEURS_FICHIER.open(
            encoding="utf-8"
        ) as fichier:
            donnees = json.load(fichier)
            if isinstance(donnees, dict) and "users" in donnees:
                return donnees
    except (OSError, ValueError, TypeError):
        logger.exception(
            "Impossible de lire les comptes utilisateurs."
        )

    return {"users": {}}


def enregistrer_comptes_utilisateurs(donnees):

    COMPTES_UTILISATEURS_FICHIER.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    temporaire = COMPTES_UTILISATEURS_FICHIER.with_suffix(
        ".tmp"
    )

    with temporaire.open("w", encoding="utf-8") as fichier:
        json.dump(
            donnees,
            fichier,
            ensure_ascii=False,
            indent=2,
        )

    temporaire.replace(COMPTES_UTILISATEURS_FICHIER)


def charger_testeurs_landing():

    if not TESTEURS_FICHIER.exists():
        return {"testeurs": []}

    try:
        with TESTEURS_FICHIER.open(encoding="utf-8") as fichier:
            donnees = json.load(fichier)
            if isinstance(donnees, dict) and "testeurs" in donnees:
                return donnees
    except (OSError, ValueError, TypeError):
        logger.exception("Impossible de lire les testeurs landing.")

    return {"testeurs": []}


def enregistrer_testeurs_landing(donnees):

    TESTEURS_FICHIER.parent.mkdir(parents=True, exist_ok=True)
    temporaire = TESTEURS_FICHIER.with_suffix(".tmp")

    with temporaire.open("w", encoding="utf-8") as fichier:
        json.dump(
            donnees,
            fichier,
            ensure_ascii=False,
            indent=2,
        )

    temporaire.replace(TESTEURS_FICHIER)


def hasher_mot_de_passe(mot_de_passe, sel=None):

    sel = sel or secrets.token_hex(16)
    empreinte = hashlib.pbkdf2_hmac(
        "sha256",
        mot_de_passe.encode("utf-8"),
        sel.encode("utf-8"),
        PBKDF2_ITERATIONS,
    ).hex()

    return {
        "salt": sel,
        "hash": empreinte,
        "iterations": PBKDF2_ITERATIONS,
    }


def verifier_mot_de_passe(mot_de_passe, securite):

    sel = securite.get("salt", "")
    attendu = securite.get("hash", "")
    iterations = int(
        securite.get("iterations", PBKDF2_ITERATIONS)
    )

    if not sel or not attendu:
        return False

    obtenu = hashlib.pbkdf2_hmac(
        "sha256",
        mot_de_passe.encode("utf-8"),
        sel.encode("utf-8"),
        iterations,
    ).hex()

    return hmac.compare_digest(obtenu, attendu)


def creer_session(email):

    jeton = secrets.token_urlsafe(32)
    SESSIONS_UTILISATEURS[jeton] = email

    return jeton


def email_depuis_requete(request):

    autorisation = request.headers.get("Authorization", "")
    prefixe = "Bearer "

    if not autorisation.startswith(prefixe):
        raise HTTPException(
            status_code=401,
            detail="Connexion requise.",
        )

    jeton = autorisation[len(prefixe):].strip()
    email = SESSIONS_UTILISATEURS.get(jeton)

    if not email:
        raise HTTPException(
            status_code=401,
            detail="Session expiree. Reconnectez-vous.",
        )

    return email


def compte_premium_requis(request):

    email = email_depuis_requete(request)
    comptes = charger_comptes_utilisateurs()
    utilisateur = comptes.get("users", {}).get(email, {})
    donnees = utilisateur.get("data", {})

    if donnees.get("plan") != "premium":
        raise HTTPException(
            status_code=403,
            detail="Acces Premium requis.",
        )

    return email


def verifier_admin(request):

    mot_de_passe = request.headers.get("X-Admin-Password", "")
    mot_de_passe_attendu = ADMIN_PASSWORD
    adresse_client = request.client.host if request.client else ""

    if (
        not mot_de_passe_attendu
        and adresse_client in {"127.0.0.1", "localhost", "::1"}
    ):
        mot_de_passe_attendu = "optiplein-admin"

    if not mot_de_passe_attendu:
        raise HTTPException(
            status_code=503,
            detail="Mot de passe admin non configure.",
        )

    if not hmac.compare_digest(mot_de_passe, mot_de_passe_attendu):
        raise HTTPException(
            status_code=401,
            detail="Mot de passe admin incorrect.",
        )


def construire_resume_admin():

    comptes = charger_comptes_utilisateurs()
    utilisateurs = comptes.get("users", {})
    lignes_comptes = []

    for email, utilisateur in sorted(utilisateurs.items()):
        donnees = utilisateur.get("data", {})
        lignes_comptes.append(
            {
                "email": email,
                "plan": donnees.get("plan", "free"),
                "created_at": utilisateur.get("created_at", ""),
                "updated_at": utilisateur.get("updated_at", ""),
                "favoris": len(donnees.get("favoris", [])),
                "vehicules": len(donnees.get("vehicules", [])),
                "historique": len(
                    donnees.get("historique_economies", [])
                ),
                "vehicule_actif": donnees.get("vehicule_actif", ""),
            }
        )

    donnees_testeurs = charger_testeurs_landing()
    testeurs = sorted(
        donnees_testeurs.get("testeurs", []),
        key=lambda ligne: ligne.get("created_at", ""),
        reverse=True,
    )

    return {
        "comptes": lignes_comptes,
        "testeurs": testeurs,
        "stats": {
            "comptes": len(lignes_comptes),
            "premium": sum(
                1
                for ligne in lignes_comptes
                if ligne.get("plan") == "premium"
            ),
            "testeurs": len(testeurs),
        },
    }


def lire_fichier_enrichissement_stations(fichier):

    if not fichier.exists():
        return {"stations": {}}

    try:
        donnees = json.loads(fichier.read_text(encoding="utf-8"))
        if isinstance(donnees, dict):
            donnees.setdefault("stations", {})
            return donnees
    except (OSError, ValueError, TypeError):
        logger.exception(
            "Impossible de lire les enrichissements stations."
        )

    return {"stations": {}}


def charger_enrichissements_stations():

    enrichissements = {}

    for fichier, source_admin in (
        (ENRICHISSEMENT_STATIONS_REPO_FICHIER, False),
        (ENRICHISSEMENT_STATIONS_ADMIN_FICHIER, True),
    ):
        donnees = lire_fichier_enrichissement_stations(fichier)
        for station_id, correction in donnees.get("stations", {}).items():
            correction = dict(correction or {})

            if source_admin:
                correction["source_correction"] = (
                    correction.get("source_correction")
                    or "Admin OptiPlein"
                )
                correction["source_enseigne"] = (
                    correction.get("source_enseigne")
                    or "Admin OptiPlein"
                )
                correction["forcer_correction"] = True

            enrichissements[str(station_id)] = correction

    return enrichissements


def enregistrer_enrichissement_station(station, correction):

    donnees = lire_fichier_enrichissement_stations(
        ENRICHISSEMENT_STATIONS_ADMIN_FICHIER
    )
    stations = donnees.setdefault("stations", {})
    station_id = str(station.get("id", "") or correction.id)

    entree = stations.setdefault(station_id, {})
    latitude_corrigee = (
        correction.latitude
        if correction.latitude is not None
        else entree.get("latitude_corrigee")
    )
    longitude_corrigee = (
        correction.longitude
        if correction.longitude is not None
        else entree.get("longitude_corrigee")
    )
    entree.update(
        {
            "signature": signature_adresse(station),
            "enseigne": correction.enseigne.strip(),
            "adresse": correction.adresse.strip(),
            "cp": correction.cp.strip(),
            "ville": correction.ville.strip(),
            "latitude_corrigee": latitude_corrigee,
            "longitude_corrigee": longitude_corrigee,
            "source_enseigne": "Admin OptiPlein",
            "source_correction": "Admin OptiPlein",
            "forcer_correction": True,
            "updated_at": datetime.now().astimezone().isoformat(),
        }
    )
    donnees["generated_at"] = datetime.now().astimezone().isoformat()
    donnees["source"] = "admin"

    ENRICHISSEMENT_STATIONS_ADMIN_FICHIER.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    temporaire = ENRICHISSEMENT_STATIONS_ADMIN_FICHIER.with_suffix(
        ".tmp"
    )
    temporaire.write_text(
        json.dumps(
            donnees,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    temporaire.replace(ENRICHISSEMENT_STATIONS_ADMIN_FICHIER)


def appliquer_enrichissements_admin(stations):

    enrichissements = charger_enrichissements_stations()

    for station in stations:
        enrichissement = enrichissements.get(str(station.get("id", "")))

        if not enrichissement:
            continue

        signature = enrichissement.get("signature")

        if (
            not enrichissement.get("forcer_correction")
            and enrichissement.get("source_correction") != "Admin OptiPlein"
            and signature
            and signature != signature_adresse(station)
        ):
            continue

        for champ in ("enseigne", "adresse", "cp", "ville"):
            if champ in enrichissement:
                station[champ] = enrichissement.get(champ) or ""

        latitude = enrichissement.get("latitude_corrigee")
        longitude = enrichissement.get("longitude_corrigee")

        if latitude is not None and longitude is not None:
            try:
                latitude_corrigee = float(latitude)
                longitude_corrigee = float(longitude)
            except (TypeError, ValueError):
                continue

            if (
                math.isfinite(latitude_corrigee)
                and math.isfinite(longitude_corrigee)
            ):
                station["latitude"] = latitude_corrigee
                station["longitude"] = longitude_corrigee


def station_resume_admin(station):

    return {
        "id": station.get("id", ""),
        "enseigne": station.get("enseigne", ""),
        "adresse": station.get("adresse", ""),
        "cp": station.get("cp", ""),
        "ville": station.get("ville", ""),
        "latitude": station.get("latitude", ""),
        "longitude": station.get("longitude", ""),
        "gazole": station.get("gazole", ""),
        "e10": station.get("e10", ""),
        "sp98": station.get("sp98", ""),
    }


def limiter_donnees_compte(donnees):

    donnees.favoris = donnees.favoris[:500]
    donnees.vehicules = donnees.vehicules[:5]
    donnees.historique_economies = donnees.historique_economies[:300]

    return donnees.model_dump()


def envoyer_signalement_email(signalement):

    hote = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    utilisateur = os.getenv("SMTP_USER", "")
    mot_de_passe = os.getenv("SMTP_PASSWORD", "")
    expediteur = os.getenv("SMTP_FROM", utilisateur)

    if not utilisateur or not mot_de_passe or not expediteur:
        raise RuntimeError("Configuration SMTP absente")

    message = EmailMessage()
    message["Subject"] = (
        "[OptiPlein] Signalement - "
        + signalement.categorie
    )
    message["From"] = expediteur
    message["To"] = EMAIL_SIGNALEMENT

    if signalement.email:
        message["Reply-To"] = signalement.email

    message.set_content(
        "Nouveau signalement OptiPlein\n\n"
        f"Categorie : {signalement.categorie}\n"
        f"Station : {signalement.station or 'Non precisee'}\n"
        f"Contact : {signalement.email or 'Non renseigne'}\n"
        f"Page : {signalement.page or '/web'}\n"
        f"Date : {datetime.now().astimezone():%d/%m/%Y %H:%M:%S %Z}\n\n"
        "Description :\n"
        f"{signalement.description.strip()}\n"
    )

    contexte_ssl = ssl.create_default_context()

    if port == 465:
        with smtplib.SMTP_SSL(
            hote,
            port,
            timeout=20,
            context=contexte_ssl,
        ) as serveur:
            serveur.login(utilisateur, mot_de_passe)
            serveur.send_message(message)
    else:
        with smtplib.SMTP(hote, port, timeout=20) as serveur:
            serveur.ehlo()
            serveur.starttls(context=contexte_ssl)
            serveur.ehlo()
            serveur.login(utilisateur, mot_de_passe)
            serveur.send_message(message)


async def actualiser_prix_periodiquement():

    boucle = asyncio.get_running_loop()

    while True:

        debut = boucle.time()

        if not mise_a_jour_admin_lock.acquire(blocking=False):
            logger.info(
                "Mise a jour automatique ignoree : "
                "une mise a jour est deja en cours."
            )
        else:
            try:
                await asyncio.to_thread(
                    mettre_a_jour_stations
                )
            except Exception:
                logger.exception(
                    "La mise a jour automatique des prix a echoue."
                )
            finally:
                mise_a_jour_admin_lock.release()

        duree = boucle.time() - debut

        await asyncio.sleep(
            max(
                0,
                INTERVALLE_MISE_A_JOUR_SECONDES - duree
            )
        )


def mise_a_jour_stations_en_retard():

    date_mise_a_jour = lire_date_metadata(
        chemin_metadata_stations()
    ) or date_derniere_mise_a_jour()

    if not date_mise_a_jour:
        return True

    if date_mise_a_jour.tzinfo is None:
        date_mise_a_jour = date_mise_a_jour.replace(
            tzinfo=datetime.now().astimezone().tzinfo
        )

    age_secondes = (
        datetime.now(date_mise_a_jour.tzinfo) - date_mise_a_jour
    ).total_seconds()

    return age_secondes > (
        INTERVALLE_MISE_A_JOUR_SECONDES
        + RETARD_MISE_A_JOUR_TOLERE_SECONDES
    )


def lancer_mise_a_jour_stations_si_retard():

    if not mise_a_jour_stations_en_retard():
        return False

    if not mise_a_jour_admin_lock.acquire(blocking=False):
        return False

    def executer():
        try:
            mettre_a_jour_stations()
        except Exception:
            logger.exception(
                "La mise a jour automatique de rattrapage a echoue."
            )
        finally:
            mise_a_jour_admin_lock.release()

    threading.Thread(
        target=executer,
        name="optiplein-stations-rattrapage",
        daemon=True,
    ).start()

    return True


@asynccontextmanager
async def duree_de_vie_application(app):

    tache_mise_a_jour = None

    if MISE_A_JOUR_FOND_ACTIVE:
        tache_mise_a_jour = asyncio.create_task(
            actualiser_prix_periodiquement()
        )

    yield

    if not tache_mise_a_jour:
        return

    tache_mise_a_jour.cancel()

    with suppress(asyncio.CancelledError):
        await tache_mise_a_jour


app = FastAPI(
    lifespan=duree_de_vie_application
)

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

templates = Jinja2Templates(
    directory="templates"
)


def chemin_stations_csv():

    if not STATIONS_RUNTIME_CSV.exists():
        return STATIONS_REPO_CSV

    if not STATIONS_REPO_CSV.exists():
        return STATIONS_RUNTIME_CSV

    try:
        metadata_runtime = STATIONS_RUNTIME_CSV.with_name(
            "stations_metadata.json"
        )
        metadata_repo = STATIONS_REPO_CSV.with_name(
            "stations_metadata.json"
        )
        date_runtime = lire_date_metadata(metadata_runtime)
        date_repo = lire_date_metadata(metadata_repo)

        if date_repo and (not date_runtime or date_repo > date_runtime):
            return STATIONS_REPO_CSV
    except Exception:
        logger.exception(
            "Impossible de comparer les fichiers stations."
        )

    return STATIONS_RUNTIME_CSV


def chemin_metadata_stations():

    metadata_runtime = STATIONS_RUNTIME_CSV.with_name(
        "stations_metadata.json"
    )
    metadata_repo = STATIONS_REPO_CSV.with_name(
        "stations_metadata.json"
    )
    date_runtime = lire_date_metadata(metadata_runtime)
    date_repo = lire_date_metadata(metadata_repo)

    if date_repo and (not date_runtime or date_repo > date_runtime):
        return metadata_repo

    if metadata_runtime.exists():
        return metadata_runtime

    return metadata_repo


def lire_date_metadata(fichier):

    if not fichier.exists():
        return None

    try:
        texte = json.loads(
            fichier.read_text(encoding="utf-8")
        ).get("updated_at")
        if not texte:
            return None

        return datetime.fromisoformat(
            texte.replace("Z", "+00:00")
        )
    except (OSError, ValueError, TypeError):
        return None


def charger_stations(appliquer_corrections=True):

    stations = []

    with chemin_stations_csv().open(encoding="utf-8-sig") as fichier:

        lecteur = csv.DictReader(
            fichier
        )

        for ligne in lecteur:

            stations.append(
                ligne
            )

    if appliquer_corrections:
        appliquer_enrichissements_admin(stations)

    return stations


def distance_km(
    lat1,
    lon1,
    lat2,
    lon2
):

    rayon = 6371

    lat1 = math.radians(float(lat1))
    lon1 = math.radians(float(lon1))

    lat2 = math.radians(float(lat2))
    lon2 = math.radians(float(lon2))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        +
        math.cos(lat1)
        *
        math.cos(lat2)
        *
        math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return rayon * c


def preparer_stations_pour_carte(
    stations,
    carburant,
    latitude=None,
    longitude=None,
    rayon=25,
):

    stations_preparees = []

    def prix_tri(station):
        try:
            return float(str(station.get(carburant, "")).replace(",", "."))
        except (TypeError, ValueError):
            return 999

    if latitude is not None and longitude is not None:
        for station in stations:
            try:
                distance = distance_km(
                    latitude,
                    longitude,
                    float(station["latitude"]),
                    float(station["longitude"]),
                )
            except (TypeError, ValueError, KeyError):
                continue

            if distance > rayon:
                continue

            station = station.copy()
            station["distance"] = round(distance, 2)
            stations_preparees.append(station)

        stations_preparees.sort(key=lambda x: x["distance"])
    else:
        stations_preparees = [station.copy() for station in stations]
        stations_preparees.sort(
            key=prix_tri
        )
        stations_preparees = stations_preparees[:50]

    for station in stations_preparees:
        station["carburant_selectionne"] = station.get(carburant, "")
        station["tendance_selectionnee"] = station.get(
            f"tendance_{carburant}",
            "",
        )
        station["tendance_demain_selectionnee"] = station.get(
            f"tendance_demain_{carburant}",
            "",
        )
        station["confiance_demain_selectionnee"] = station.get(
            f"confiance_demain_{carburant}",
            "",
        )

    return stations_preparees


@app.get("/")
def landing_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="landing.html",
        context={
            "adsense_client": ADSENSE_CLIENT,
            "adsense_active": bool(ADSENSE_CLIENT),
        }
    )


@app.get("/admin")
def page_admin(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={}
    )


@app.get("/api/admin/donnees")
def donnees_admin(request: Request):

    verifier_admin(request)
    return construire_resume_admin()


@app.post("/api/admin/plan")
def changer_plan_admin(
    changement: AdminChangementPlan,
    request: Request,
):

    verifier_admin(request)
    email = normaliser_email(changement.email)
    comptes = charger_comptes_utilisateurs()
    utilisateur = comptes.get("users", {}).get(email)

    if not utilisateur:
        raise HTTPException(
            status_code=404,
            detail="Compte introuvable.",
        )

    donnees = utilisateur.setdefault("data", {})
    donnees["plan"] = changement.plan
    utilisateur["updated_at"] = datetime.now().astimezone().isoformat()
    enregistrer_comptes_utilisateurs(comptes)

    return {
        "ok": True,
        "email": email,
        "plan": changement.plan,
        "updated_at": utilisateur["updated_at"],
    }


@app.get("/api/admin/stations")
def rechercher_stations_admin(
    request: Request,
    q: str = "",
):

    verifier_admin(request)
    recherche = " ".join(q.casefold().split())
    enrichissements = charger_enrichissements_stations()
    stations = charger_stations()

    if recherche:
        stations = [
            station
            for station in stations
            if recherche in " ".join(
                str(station.get(champ, "") or "").casefold()
                for champ in (
                    "id",
                    "enseigne",
                    "adresse",
                    "cp",
                    "ville",
                )
            )
        ]

    stations = stations[:80]

    return {
        "stations": [
            dict(
                station_resume_admin(station),
                corrigee=str(station.get("id", "")) in enrichissements,
            )
            for station in stations
        ]
    }


@app.post("/api/admin/station")
def corriger_station_admin(
    correction: AdminCorrectionStation,
    request: Request,
):

    verifier_admin(request)

    if (
        correction.latitude is not None
        and not -90 <= correction.latitude <= 90
    ):
        raise HTTPException(
            status_code=400,
            detail="Latitude invalide.",
        )

    if (
        correction.longitude is not None
        and not -180 <= correction.longitude <= 180
    ):
        raise HTTPException(
            status_code=400,
            detail="Longitude invalide.",
        )

    verrou_obtenu = mise_a_jour_admin_lock.acquire(
        timeout=ATTENTE_VERROU_ADMIN_SECONDES
    )

    if not verrou_obtenu:
        raise HTTPException(
            status_code=409,
            detail=(
                "Une mise a jour des stations est en cours. "
                "Reessayez dans quelques secondes."
            ),
        )

    try:
        stations_brutes = charger_stations(appliquer_corrections=False)
        station = next(
            (
                ligne
                for ligne in stations_brutes
                if str(ligne.get("id", "")) == str(correction.id)
            ),
            None,
        )

        if not station:
            raise HTTPException(
                status_code=404,
                detail="Station introuvable.",
            )

        enregistrer_enrichissement_station(station, correction)

        station_corrigee = dict(station)
        appliquer_enrichissements_admin([station_corrigee])

        return {
            "ok": True,
            "station": station_resume_admin(station_corrigee),
        }
    finally:
        mise_a_jour_admin_lock.release()


@app.post("/api/admin/forcer-mise-a-jour")
async def forcer_mise_a_jour_admin(request: Request):

    verifier_admin(request)

    if not mise_a_jour_admin_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail="Une mise a jour est deja en cours.",
        )

    try:
        await asyncio.to_thread(mettre_a_jour_stations)
        stations = charger_stations()
        date_mise_a_jour = date_derniere_mise_a_jour()
        return {
            "ok": True,
            "stations": len(stations),
            "updated_at": (
                date_mise_a_jour.isoformat()
                if date_mise_a_jour
                else None
            ),
        }
    except Exception as erreur:
        logger.exception(
            "La mise a jour forcee depuis l'admin a echoue."
        )
        raise HTTPException(
            status_code=500,
            detail=(
                "Mise a jour impossible pour le moment : "
                + str(erreur)
            ),
        ) from erreur
    finally:
        mise_a_jour_admin_lock.release()


@app.post("/api/testeurs")
def inscrire_testeur(inscription: InscriptionTesteur, request: Request):

    email = normaliser_email(inscription.email)

    if not email_valide(email):
        raise HTTPException(
            status_code=400,
            detail="Adresse e-mail invalide.",
        )

    donnees = charger_testeurs_landing()
    testeurs = donnees.setdefault("testeurs", [])
    maintenant = datetime.utcnow().isoformat() + "Z"
    adresse_ip = request.client.host if request.client else ""
    existe = next(
        (
            ligne
            for ligne in testeurs
            if ligne.get("email") == email
        ),
        None
    )

    if existe:
        existe["updated_at"] = maintenant
        existe["source"] = inscription.source or "landing"
    else:
        testeurs.append(
            {
                "email": email,
                "source": inscription.source or "landing",
                "created_at": maintenant,
                "updated_at": maintenant,
                "ip": adresse_ip,
            }
        )

    enregistrer_testeurs_landing(donnees)

    return {"ok": True}


@app.get("/confidentialite")
def confidentialite(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="confidentialite.html",
        context={}
    )


@app.get("/suppression-compte")
def suppression_compte(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="suppression_compte.html",
        context={}
    )

@app.get("/stations")
def get_stations():

    stations = charger_stations()

    stations.sort(
        key=lambda x: (
            float(x["gazole"])
            if x["gazole"].strip()
            else 999
        )
    )

    return stations


def signe_graphhopper_vers_maneuvre(signe):

    correspondance = {
        -3: ("turn", "sharp left"),
        -2: ("turn", "left"),
        -1: ("turn", "slight left"),
        0: ("continue", "straight"),
        1: ("turn", "slight right"),
        2: ("turn", "right"),
        3: ("turn", "sharp right"),
        4: ("arrive", "straight"),
        5: ("arrive", "straight"),
        6: ("roundabout", "right"),
        7: ("roundabout", "right"),
        -7: ("roundabout", "left"),
        -6: ("roundabout", "left"),
    }

    return correspondance.get(
        int(signe or 0),
        ("continue", "straight"),
    )


def convertir_route_graphhopper(donnees):

    chemin = (donnees.get("paths") or [None])[0]

    if not chemin:
        raise ValueError("route GraphHopper introuvable")

    points = chemin.get("points") or {}
    coordonnees = points.get("coordinates") or []
    instructions = chemin.get("instructions") or []
    etapes = []

    for instruction in instructions:
        intervalle = instruction.get("interval") or [0, 0]
        index_point = max(0, min(int(intervalle[0] or 0), len(coordonnees) - 1))
        coordonnee = coordonnees[index_point] if coordonnees else [0, 0]
        type_maneuvre, modificateur = signe_graphhopper_vers_maneuvre(
            instruction.get("sign")
        )
        etapes.append(
            {
                "distance": instruction.get("distance", 0),
                "duration": (instruction.get("time", 0) or 0) / 1000,
                "name": instruction.get("street_name", "") or "",
                "maneuver": {
                    "type": type_maneuvre,
                    "modifier": modificateur,
                    "location": coordonnee,
                },
            }
        )

    return {
        "distance": chemin.get("distance", 0),
        "duration": (chemin.get("time", 0) or 0) / 1000,
        "geometry": {
            "type": "LineString",
            "coordinates": coordonnees,
        },
        "legs": [
            {
                "steps": etapes,
            }
        ],
        "provider": "graphhopper",
    }


def calculer_itineraire_graphhopper(points):

    if not GRAPHHOPPER_API_KEY:
        raise ValueError("clé GraphHopper absente")

    parametres = [
        ("vehicle", "car"),
        ("locale", "fr"),
        ("points_encoded", "false"),
        ("instructions", "true"),
        ("calc_points", "true"),
        ("key", GRAPHHOPPER_API_KEY),
    ]
    parametres.extend(
        ("point", f"{point.latitude},{point.longitude}")
        for point in points
    )

    reponse = http_requests.get(
        "https://graphhopper.com/api/1/route",
        params=parametres,
        timeout=10,
    )
    reponse.raise_for_status()

    return {
        "routes": [
            convertir_route_graphhopper(reponse.json())
        ],
        "waypoints": [],
        "provider": "graphhopper",
    }


def calculer_itineraire_osrm(points, cap_depart=None):

    coordonnees = ";".join(
        f"{point.longitude},{point.latitude}"
        for point in points
    )
    url = (
        "https://router.project-osrm.org/route/v1/driving/"
        + coordonnees
    )
    parametres = {
        "overview": "full",
        "geometries": "geojson",
        "steps": "true",
        "continue_straight": "true",
    }

    if cap_depart is not None and math.isfinite(cap_depart):
        parametres["bearings"] = f"{round(cap_depart)},45;"

    reponse = http_requests.get(
        url,
        params=parametres,
        timeout=10,
    )
    reponse.raise_for_status()
    donnees = reponse.json()
    donnees["provider"] = "osrm"
    return donnees


@app.post("/api/itineraire")
async def calculer_itineraire(requete: RequeteItineraire):

    try:
        if (
            requete.moteur in {"auto", "graphhopper"}
            and GRAPHHOPPER_API_KEY
        ):
            return await asyncio.to_thread(
                calculer_itineraire_graphhopper,
                requete.points,
            )
    except Exception:
        logger.exception(
            "GraphHopper indisponible, bascule sur OSRM."
        )

        if requete.moteur == "graphhopper":
            raise HTTPException(
                status_code=502,
                detail="GraphHopper indisponible",
            )

    try:
        return await asyncio.to_thread(
            calculer_itineraire_osrm,
            requete.points,
            requete.cap_depart,
        )
    except Exception as erreur:
        logger.exception("Itinéraire indisponible.")
        raise HTTPException(
            status_code=502,
            detail="itinéraire indisponible",
        ) from erreur


@app.get("/api/itineraire/statut")
def statut_itineraire():

    return {
        "graphhopper_configure": bool(GRAPHHOPPER_API_KEY),
        "moteur_prioritaire": (
            "graphhopper" if GRAPHHOPPER_API_KEY else "osrm"
        ),
        "fallback": "osrm",
        "variables_acceptees": [
            "GRAPHHOPPER_API_KEY",
            "GRAPH_HOPPER_API_KEY",
            "GRAPHHOPPER_KEY",
            "GRAPHOPPER_API_KEY",
        ],
    }


@app.get("/api/adresses")
async def rechercher_adresses(q: str, limit: int = 5):

    recherche = q.strip()
    limite = max(1, min(limit, 8))

    if len(recherche) < 3:
        return {
            "suggestions": []
        }

    suggestions_francaises = []
    suggestions_osm = []
    est_adresse = recherche_ressemble_a_adresse(recherche)

    try:
        suggestions_francaises.extend(
            await asyncio.to_thread(
                rechercher_adresses_francaises,
                recherche,
                limite,
            )
        )
    except Exception:
        logger.exception("Recherche d'adresse francaise indisponible.")

    if not est_adresse or len(suggestions_francaises) < limite:
        try:
            suggestions_osm.extend(
                await asyncio.to_thread(
                    rechercher_adresses_osm,
                    recherche,
                    limite,
                )
            )
        except Exception:
            logger.exception("Recherche d'adresse OSM indisponible.")

    suggestions = (
        suggestions_francaises + suggestions_osm
        if est_adresse
        else suggestions_osm + suggestions_francaises
    )

    return {
        "suggestions": dedoublonner_adresses(suggestions, limite)
    }


@app.get("/api/stations-proches")
def get_stations_proches(
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    carburant: str = "gazole",
    rayon: int = 25,
):

    stations = preparer_stations_pour_carte(
        charger_stations(),
        carburant,
        latitude,
        longitude,
        rayon,
    )

    return {
        "stations": [
            {
                "id": station.get("id", ""),
                "enseigne": station.get("enseigne", ""),
                "adresse": station.get("adresse", ""),
                "cp": station.get("cp", ""),
                "ville": station.get("ville", ""),
                "latitude": station.get("latitude", ""),
                "longitude": station.get("longitude", ""),
                "distance": station.get("distance"),
                "prix": station.get("carburant_selectionne", ""),
                "carburant": carburant,
                "tendance": station.get("tendance_selectionnee", ""),
                "tendance_demain": station.get(
                    "tendance_demain_selectionnee",
                    "",
                ),
                "confiance_demain": station.get(
                    "confiance_demain_selectionnee",
                    "",
                ),
            }
            for station in stations
        ],
        "count": len(stations),
    }


@app.get("/api/derniere-mise-a-jour")
def get_derniere_mise_a_jour():

    rattrapage_lance = lancer_mise_a_jour_stations_si_retard()
    date_mise_a_jour = lire_date_metadata(
        chemin_metadata_stations()
    ) or date_derniere_mise_a_jour()

    return {
        "updated_at": (
            date_mise_a_jour.isoformat()
            if date_mise_a_jour
            else None
        ),
        "update_pending": rattrapage_lance,
    }


@app.post("/api/compte/inscription")
def creer_compte(identifiants: CompteIdentifiants):

    email = normaliser_email(identifiants.email)

    if not email_valide(email):
        raise HTTPException(
            status_code=422,
            detail="L'adresse e-mail n'est pas valide.",
        )

    comptes = charger_comptes_utilisateurs()
    utilisateurs = comptes.setdefault("users", {})

    if email in utilisateurs:
        raise HTTPException(
            status_code=409,
            detail="Un compte existe deja avec cette adresse.",
        )

    utilisateurs[email] = {
        "email": email,
        "password": hasher_mot_de_passe(
            identifiants.mot_de_passe
        ),
        "created_at": datetime.now().astimezone().isoformat(),
        "updated_at": datetime.now().astimezone().isoformat(),
        "data": limiter_donnees_compte(DonneesCompte()),
    }
    enregistrer_comptes_utilisateurs(comptes)

    return {
        "ok": True,
        "email": email,
        "token": creer_session(email),
        "donnees": utilisateurs[email]["data"],
    }


@app.post("/api/compte/connexion")
def connecter_compte(identifiants: CompteIdentifiants):

    email = normaliser_email(identifiants.email)
    comptes = charger_comptes_utilisateurs()
    utilisateur = comptes.get("users", {}).get(email)

    if not utilisateur or not verifier_mot_de_passe(
        identifiants.mot_de_passe,
        utilisateur.get("password", {}),
    ):
        raise HTTPException(
            status_code=401,
            detail="Adresse e-mail ou mot de passe incorrect.",
        )

    return {
        "ok": True,
        "email": email,
        "token": creer_session(email),
        "donnees": utilisateur.get("data", {}),
    }


@app.get("/api/compte/donnees")
def lire_donnees_compte(request: Request):

    email = email_depuis_requete(request)
    comptes = charger_comptes_utilisateurs()
    utilisateur = comptes.get("users", {}).get(email)

    if not utilisateur:
        raise HTTPException(
            status_code=404,
            detail="Compte introuvable.",
        )

    return {
        "ok": True,
        "email": email,
        "donnees": utilisateur.get("data", {}),
    }


@app.post("/api/compte/sauvegarde")
def sauvegarder_donnees_compte(
    sauvegarde: SauvegardeCompte,
    request: Request,
):

    email = email_depuis_requete(request)
    comptes = charger_comptes_utilisateurs()
    utilisateur = comptes.get("users", {}).get(email)

    if not utilisateur:
        raise HTTPException(
            status_code=404,
            detail="Compte introuvable.",
        )

    utilisateur["data"] = limiter_donnees_compte(
        sauvegarde.donnees
    )
    utilisateur["updated_at"] = datetime.now().astimezone().isoformat()
    enregistrer_comptes_utilisateurs(comptes)

    return {
        "ok": True,
        "updated_at": utilisateur["updated_at"],
    }


@app.post("/api/signaler-probleme")
async def signaler_probleme(
    signalement: SignalementProbleme,
    request: Request,
):

    if signalement.site_web:
        return {"ok": True}

    signalement.description = signalement.description.strip()
    signalement.station = signalement.station.strip()
    signalement.email = signalement.email.strip()

    if len(signalement.description) < 10:
        raise HTTPException(
            status_code=422,
            detail="La description doit contenir au moins 10 caracteres.",
        )

    if signalement.email and not re.fullmatch(
        r"[^\s@]+@[^\s@]+\.[^\s@]+",
        signalement.email,
    ):
        raise HTTPException(
            status_code=422,
            detail="L'adresse e-mail n'est pas valide.",
        )

    adresse_client = (
        request.client.host
        if request.client
        else "inconnue"
    )
    maintenant = time.monotonic()
    dernier_envoi = signalements_recents.get(adresse_client, 0)

    if maintenant - dernier_envoi < 60:
        raise HTTPException(
            status_code=429,
            detail="Veuillez patienter une minute avant un nouvel envoi.",
        )

    try:
        await asyncio.to_thread(
            envoyer_signalement_email,
            signalement,
        )
    except RuntimeError:
        raise HTTPException(
            status_code=503,
            detail="L'envoi des signalements n'est pas encore configure.",
        )
    except Exception:
        logger.exception("L'envoi du signalement a echoue.")
        raise HTTPException(
            status_code=502,
            detail="Le message n'a pas pu etre envoye. Reessayez plus tard.",
        )

    signalements_recents[adresse_client] = maintenant

    return {"ok": True}


@app.get("/web")
def page_web(
    request: Request,
    ville: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    carburant: str = "gazole",
    rayon: int = 25
):

    stations = charger_stations()

    # Recherche ville ou code postal

    if ville:

        recherche = ville.lower()

        stations = [

            station

            for station in stations

            if (

                recherche in station["ville"].lower()

                or

                recherche in station["cp"]

            )

        ]

    stations = preparer_stations_pour_carte(
        stations,
        carburant,
        latitude,
        longitude,
        rayon,
    )

    nombre_stations = len(stations)

    stations_avec_prix = []

    for station in stations:
        try:
            prix = float(station.get(carburant, ""))
            if prix not in (0, 9.999):
                stations_avec_prix.append((prix, station))
        except (TypeError, ValueError):
            continue

    station_prix_min = (
        min(stations_avec_prix, key=lambda element: element[0])
        if stations_avec_prix
        else None
    )
    prix_min = station_prix_min[0] if station_prix_min else None

    return templates.TemplateResponse(

        request=request,

        name="index.html",

        context={

            "stations": stations,

            "nombre_stations": nombre_stations,

            "prix_min": prix_min,

            "station_prix_min": station_prix_min[1] if station_prix_min else None,

            "carburant": carburant,

            "rayon": rayon,

            "texte_verification": texte_derniere_mise_a_jour(),

            "date_verification": (
                date_derniere_mise_a_jour().isoformat()
                if date_derniere_mise_a_jour()
                else None
            ),

            "adsense_client": ADSENSE_CLIENT,

            "adsense_slot_map": ADSENSE_SLOT_MAP,

            "adsense_active": bool(ADSENSE_CLIENT),

        }

    )    


@app.get("/ads.txt")
def ads_txt():

    identifiant_editeur = ADSENSE_CLIENT.replace("ca-", "")

    return PlainTextResponse(
        "google.com, "
        + identifiant_editeur
        + ", DIRECT, f08c47fec0942fa0\n",
        media_type="text/plain",
    )



