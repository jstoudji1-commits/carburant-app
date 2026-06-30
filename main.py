from fastapi import FastAPI, Request
from fastapi import HTTPException
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
import time
from update_data import (
    date_derniere_mise_a_jour,
    mettre_a_jour_stations,
    signature_adresse,
    texte_derniere_mise_a_jour,
)


INTERVALLE_MISE_A_JOUR_SECONDES = 10 * 60
logger = logging.getLogger("optiplein.update")
MISE_A_JOUR_FOND_ACTIVE = os.getenv(
    "OPTIPLEIN_BACKGROUND_UPDATE",
    "false",
).strip().lower() in {"1", "true", "yes", "on"}
EMAIL_SIGNALEMENT = os.getenv(
    "REPORT_EMAIL",
    "optiplein5@gmail.com"
)
signalements_recents = {}
DOSSIER_DONNEES_UTILISATEURS = Path(
    os.getenv("OPTIPLEIN_DATA_DIR", ".")
)
COMPTES_UTILISATEURS_FICHIER = (
    DOSSIER_DONNEES_UTILISATEURS
    / "comptes_utilisateurs.json"
)
STATIONS_EUROPE_CSV = (
    Path(__file__).resolve().parent
    / "stations_europe.csv"
)
STATIONS_EUROPE_METADATA_JSON = (
    Path(__file__).resolve().parent
    / "stations_europe_metadata.json"
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

    for fichier in (
        ENRICHISSEMENT_STATIONS_REPO_FICHIER,
        ENRICHISSEMENT_STATIONS_ADMIN_FICHIER,
    ):
        donnees = lire_fichier_enrichissement_stations(fichier)
        enrichissements.update(donnees.get("stations", {}))

    return enrichissements


def enregistrer_enrichissement_station(station, correction):

    donnees = lire_fichier_enrichissement_stations(
        ENRICHISSEMENT_STATIONS_ADMIN_FICHIER
    )
    stations = donnees.setdefault("stations", {})
    station_id = str(station.get("id", "") or correction.id)

    entree = stations.setdefault(station_id, {})
    entree.update(
        {
            "signature": signature_adresse(station),
            "enseigne": correction.enseigne.strip(),
            "adresse": correction.adresse.strip(),
            "cp": correction.cp.strip(),
            "ville": correction.ville.strip(),
            "latitude_corrigee": correction.latitude,
            "longitude_corrigee": correction.longitude,
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

        try:
            await asyncio.to_thread(
                mettre_a_jour_stations
            )
        except Exception:
            logger.exception(
                "La mise a jour automatique des prix a echoue."
            )

        duree = boucle.time() - debut

        await asyncio.sleep(
            max(
                0,
                INTERVALLE_MISE_A_JOUR_SECONDES - duree
            )
        )


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

    if STATIONS_RUNTIME_CSV.exists():
        return STATIONS_RUNTIME_CSV

    return STATIONS_REPO_CSV


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


def charger_stations_europe():

    if not STATIONS_EUROPE_CSV.exists():
        return []

    with STATIONS_EUROPE_CSV.open(
        encoding="utf-8"
    ) as fichier:
        return list(csv.DictReader(fichier))


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
        context={}
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


@app.get("/api/stations-europe")
def get_stations_europe(
    request: Request,
    country: str = "",
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    rayon: int = 25,
):

    stations = charger_stations_europe()
    country = country.strip().upper()

    if country:
        stations = [
            station
            for station in stations
            if station.get("country_code", "").upper() == country
        ]

    if latitude is not None and longitude is not None:
        stations_autour = []

        for station in stations:
            try:
                distance = distance_km(
                    latitude,
                    longitude,
                    float(station.get("latitude") or 0),
                    float(station.get("longitude") or 0),
                )
            except (TypeError, ValueError):
                continue

            if distance <= rayon:
                station = dict(station)
                station["distance"] = round(distance, 2)
                stations_autour.append(station)

        stations = sorted(
            stations_autour,
            key=lambda station: station.get("distance", 999),
        )
    else:
        stations = stations[:500]

    metadata = {}
    if STATIONS_EUROPE_METADATA_JSON.exists():
        try:
            metadata = json.loads(
                STATIONS_EUROPE_METADATA_JSON.read_text(
                    encoding="utf-8"
                )
            )
        except (OSError, ValueError, TypeError):
            metadata = {}

    return {
        "stations": stations,
        "count": len(stations),
        "metadata": metadata,
    }


@app.get("/api/derniere-mise-a-jour")
def get_derniere_mise_a_jour():

    date_mise_a_jour = date_derniere_mise_a_jour()

    return {
        "updated_at": (
            date_mise_a_jour.isoformat()
            if date_mise_a_jour
            else None
        )
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
            )

        }

    )    



