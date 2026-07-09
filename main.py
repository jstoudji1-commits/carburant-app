from fastapi import FastAPI, Request
from fastapi import HTTPException
from fastapi.responses import PlainTextResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from typing import Literal, Optional
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field


import asyncio
import csv
from contextlib import asynccontextmanager, suppress
from datetime import datetime
from email.message import EmailMessage
from email.utils import getaddresses
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
APP_BASE_URL = os.getenv("APP_BASE_URL", "").strip().rstrip("/")
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
CORRECTIONS_STATIONS_ADMIN_FICHIER = (
    DOSSIER_DONNEES_UTILISATEURS
    / "stations_admin_overrides.json"
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
PREMIUM_TEST_ACTIF = True
DELAI_VALIDATION_EMAIL_SECONDES = 24 * 60 * 60


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
    lieux_trajet: dict = Field(default_factory=dict)
    rayon_stations: int = 25


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


class AdminTestEmail(BaseModel):

    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=5, max_length=160)


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
            detail="Session expirée. Reconnectez-vous.",
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


def ecrire_fichier_enrichissement_stations(fichier, donnees):

    fichier.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    temporaire = fichier.with_suffix(".tmp")
    temporaire.write_text(
        json.dumps(
            donnees,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    temporaire.replace(fichier)


def charger_enrichissements_stations():

    enrichissements = {}

    for fichier, source_admin in (
        (ENRICHISSEMENT_STATIONS_REPO_FICHIER, False),
        (ENRICHISSEMENT_STATIONS_ADMIN_FICHIER, True),
        (CORRECTIONS_STATIONS_ADMIN_FICHIER, True),
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
    entree_correction = {
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
    entree.update(entree_correction)
    donnees["generated_at"] = datetime.now().astimezone().isoformat()
    donnees["source"] = "admin"
    ecrire_fichier_enrichissement_stations(
        ENRICHISSEMENT_STATIONS_ADMIN_FICHIER,
        donnees,
    )

    corrections = lire_fichier_enrichissement_stations(
        CORRECTIONS_STATIONS_ADMIN_FICHIER
    )
    corrections.setdefault("stations", {})[station_id] = entree_correction
    corrections["generated_at"] = datetime.now().astimezone().isoformat()
    corrections["source"] = "admin-overrides"
    ecrire_fichier_enrichissement_stations(
        CORRECTIONS_STATIONS_ADMIN_FICHIER,
        corrections,
    )


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
    donnees.rayon_stations = max(
        5,
        min(50, int(donnees.rayon_stations or 25)),
    )
    if PREMIUM_TEST_ACTIF:
        donnees.plan = "premium"

    return donnees.model_dump()


def donnees_compte_premium_test(donnees):

    donnees = dict(donnees or {})
    if PREMIUM_TEST_ACTIF:
        donnees["plan"] = "premium"
    return donnees


def lire_configuration_smtp():

    hote = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    port_brut = os.getenv("SMTP_PORT", "587").strip()
    try:
        port = int(port_brut)
    except ValueError:
        port = 0
    utilisateur = os.getenv("SMTP_USER", "").strip()
    mot_de_passe_brut = os.getenv("SMTP_PASSWORD", "")
    mot_de_passe = mot_de_passe_brut.strip()
    if "gmail" in hote.lower() or utilisateur.lower().endswith("@gmail.com"):
        mot_de_passe = re.sub(r"\s+", "", mot_de_passe_brut)
    expediteur = os.getenv("SMTP_FROM", utilisateur).strip()

    return {
        "host": hote,
        "port": port,
        "port_raw": port_brut,
        "user": utilisateur,
        "password": mot_de_passe,
        "from": expediteur,
    }


def lire_configuration_email_api():

    brevo_api_key = os.getenv("BREVO_API_KEY", "").strip()
    resend_api_key = os.getenv("RESEND_API_KEY", "").strip()

    return {
        "provider": "brevo" if brevo_api_key else (
            "resend" if resend_api_key else "smtp"
        ),
        "brevo_api_key": brevo_api_key,
        "resend_api_key": resend_api_key,
    }


def masquer_email_admin(email):

    if not email or "@" not in email:
        return email or ""

    nom, domaine = email.split("@", 1)
    if len(nom) <= 2:
        nom_masque = nom[:1] + "*"
    else:
        nom_masque = nom[:2] + "***" + nom[-1:]

    return nom_masque + "@" + domaine


def resume_configuration_smtp():

    configuration = lire_configuration_smtp()
    mot_de_passe = configuration["password"]
    utilisateur = configuration["user"]
    expediteur = configuration["from"]
    port = configuration["port"]

    champs_manquants = [
        nom
        for nom, valeur in (
            ("SMTP_USER", utilisateur),
            ("SMTP_PASSWORD", mot_de_passe),
            ("SMTP_FROM", expediteur),
        )
        if not valeur
    ]

    if port <= 0:
        champs_manquants.append("SMTP_PORT")

    return {
        "provider": lire_configuration_email_api()["provider"],
        "host": configuration["host"],
        "port": port or configuration["port_raw"],
        "user": masquer_email_admin(utilisateur),
        "from": masquer_email_admin(expediteur),
        "password_configured": bool(mot_de_passe),
        "password_length": len(mot_de_passe),
        "ready": not champs_manquants,
        "missing": champs_manquants,
        "app_base_url": APP_BASE_URL,
    }


def message_erreur_smtp(erreur):

    configuration = lire_configuration_smtp()
    hote = configuration["host"]
    port = configuration["port"]
    hote_minuscule = hote.lower()

    if isinstance(erreur, smtplib.SMTPAuthenticationError):
        detail = ""
        if getattr(erreur, "smtp_error", None):
            detail = erreur.smtp_error.decode(
                "utf-8",
                errors="replace",
            )
        return (
            "Authentification SMTP refusée. Vérifiez que SMTP_USER est "
            "l'adresse e-mail complète, que SMTP_PASSWORD est le mot de passe "
            "de cette boîte mail, et que SMTP_FROM utilise la même adresse "
            "ou un alias autorisé."
            + (f" Réponse SMTP : {detail}" if detail else "")
        )

    if isinstance(erreur, smtplib.SMTPConnectError):
        return (
            f"Connexion au serveur SMTP impossible ({hote}:{port}). "
            "Vérifiez SMTP_HOST et SMTP_PORT sur Render."
        )

    if isinstance(erreur, smtplib.SMTPServerDisconnected):
        return (
            "Le serveur SMTP a coupé la connexion. Vérifiez le port SMTP "
            "et relancez le déploiement Render."
        )

    if isinstance(erreur, smtplib.SMTPNotSupportedError):
        return (
            "Le serveur SMTP ne prend pas en charge la sécurité demandée. "
            "Essayez SMTP_PORT=465 avec SSL, ou vérifiez le serveur sortant "
            "fourni par votre boîte mail."
        )

    if isinstance(erreur, smtplib.SMTPRecipientsRefused):
        return (
            "Le serveur SMTP a refusé le destinataire. Testez avec une autre "
            "adresse e-mail et vérifiez que la boîte d'envoi est active."
        )

    if isinstance(erreur, smtplib.SMTPSenderRefused):
        return (
            "Le serveur SMTP a refusé l'expéditeur. Mettez SMTP_FROM égal à "
            "SMTP_USER sur Render."
        )

    if isinstance(erreur, (TimeoutError, OSError)):
        if hote_minuscule.startswith("pro") and hote_minuscule.endswith(
            ".mail.ovh.net"
        ) and port == 465:
            return (
                "Connexion SMTP impossible : OVH Email Pro utilise "
                f"{hote}:587 en STARTTLS. Mettez SMTP_PORT=587 sur Render, "
                "puis Save, rebuild, and deploy."
            )

        return (
            f"Connexion SMTP impossible depuis Render vers {hote}:{port}. "
            "Pour OVH Email Pro, utilisez SMTP_HOST=pro2.mail.ovh.net "
            "et SMTP_PORT=587."
        )

    return f"Erreur SMTP ({type(erreur).__name__}) : {erreur}"


def extraire_contenu_email(message):

    texte = ""
    html = ""

    corps_texte = message.get_body(preferencelist=("plain",))
    corps_html = message.get_body(preferencelist=("html",))

    if corps_texte:
        texte = corps_texte.get_content()
    elif not message.is_multipart():
        texte = message.get_content()

    if corps_html:
        html = corps_html.get_content()

    return texte, html


def adresses_destinataires_email(message):

    adresses = getaddresses(message.get_all("To", []))
    return [
        email
        for _nom, email in adresses
        if email
    ]


def envoyer_email_brevo(message, api_key):

    configuration = lire_configuration_smtp()
    expediteur = message.get("From") or configuration["from"]
    destinataires = adresses_destinataires_email(message)
    texte, html = extraire_contenu_email(message)

    if not expediteur:
        raise RuntimeError("Configuration e-mail incomplète : SMTP_FROM")

    if not destinataires:
        raise RuntimeError("Aucun destinataire e-mail.")

    payload = {
        "sender": {"email": expediteur},
        "to": [{"email": email} for email in destinataires],
        "subject": message.get("Subject", "OptiPlein"),
    }

    if html:
        payload["htmlContent"] = html

    if texte:
        payload["textContent"] = texte

    reponse = http_requests.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={
            "accept": "application/json",
            "api-key": api_key,
            "content-type": "application/json",
        },
        json=payload,
        timeout=20,
    )

    if reponse.status_code >= 400:
        detail = reponse.text[:500]
        raise RuntimeError(
            "Brevo a refusé l'envoi e-mail "
            f"({reponse.status_code}) : {detail}"
        )


def envoyer_email(message):

    configuration_api = lire_configuration_email_api()

    if configuration_api["brevo_api_key"]:
        envoyer_email_brevo(message, configuration_api["brevo_api_key"])
        return

    configuration = lire_configuration_smtp()
    hote = configuration["host"]
    port = configuration["port"]
    utilisateur = configuration["user"]
    mot_de_passe = configuration["password"]
    expediteur = configuration["from"]

    if port <= 0 or not utilisateur or not mot_de_passe or not expediteur:
        champs_manquants = [
            nom
            for nom, valeur in (
                ("SMTP_PORT", port),
                ("SMTP_USER", utilisateur),
                ("SMTP_PASSWORD", mot_de_passe),
                ("SMTP_FROM", expediteur),
            )
            if not valeur
        ]
        raise RuntimeError(
            "Configuration SMTP incomplète : "
            + ", ".join(champs_manquants)
        )

    if not message.get("From"):
        message["From"] = expediteur

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


def envoyer_signalement_email(signalement):

    message = EmailMessage()
    message["Subject"] = (
        "[OptiPlein] Signalement - "
        + signalement.categorie
    )
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

    envoyer_email(message)


def creer_jeton_validation_email():

    jeton = secrets.token_urlsafe(32)
    empreinte = hashlib.sha256(
        jeton.encode("utf-8")
    ).hexdigest()
    expiration = time.time() + DELAI_VALIDATION_EMAIL_SECONDES

    return jeton, empreinte, expiration


def url_base_application(request):

    if APP_BASE_URL:
        return APP_BASE_URL

    return str(request.base_url).rstrip("/")


def html_logo_email(base_url):

    return (
        '<p style="margin:0 0 24px 0;">'
        f'<img src="{base_url}/static/logo.png" alt="OptiPlein" '
        'style="display:block;max-width:210px;height:auto;">'
        "</p>"
    )


def envoyer_email_validation_compte(email, lien_validation, base_url):

    message = EmailMessage()
    message["Subject"] = "Validez votre compte OptiPlein"
    message["To"] = email
    message.set_content(
        "Bienvenue sur OptiPlein.\n\n"
        "Pour activer votre compte et débloquer la découverte Premium, "
        "cliquez sur ce lien :\n"
        f"{lien_validation}\n\n"
        "Ce lien est valable 24 heures. Si vous n’êtes pas à l’origine "
        "de cette demande, ignorez simplement cet e-mail.\n"
    )
    message.add_alternative(
        '<div style="font-family:Arial,sans-serif;color:#102536;'
        'line-height:1.55;font-size:16px;">'
        + html_logo_email(base_url)
        + "<h1 style=\"font-size:22px;margin:0 0 12px 0;\">"
        "Validez votre compte OptiPlein"
        "</h1>"
        "<p>Bienvenue sur OptiPlein.</p>"
        "<p>Pour activer votre compte et d&eacute;bloquer la "
        "d&eacute;couverte Premium, cliquez sur le bouton ci-dessous.</p>"
        '<p style="margin:24px 0;">'
        f'<a href="{lien_validation}" '
        'style="display:inline-block;background:#149f38;color:#ffffff;'
        'text-decoration:none;font-weight:700;padding:12px 18px;'
        'border-radius:8px;">Valider mon e-mail</a>'
        "</p>"
        "<p>Ce lien est valable 24 heures. Si vous n’&ecirc;tes pas &agrave; "
        "l’origine de cette demande, ignorez simplement cet e-mail.</p>"
        "</div>",
        subtype="html",
    )

    envoyer_email(message)


def envoyer_email_bienvenue_premium(email, base_url):

    message = EmailMessage()
    message["Subject"] = "Votre accès Premium OptiPlein est activé"
    message["To"] = email
    message.set_content(
        "Votre compte OptiPlein est validé.\n\n"
        "Pendant la phase de test de cet été, vous avez accès gratuitement "
        "aux fonctions Premium : préparation de trajet, calcul de la station "
        "la plus rentable, historique des économies, plusieurs véhicules, "
        "favoris illimités, tendances de prix et suggestions de "
        "ravitaillement.\n\n"
        "Vos retours vont aider à améliorer l’application avant son "
        "lancement officiel. Merci de faire partie des premiers testeurs.\n\n"
        f"Accéder à l’application : {base_url}/web\n"
    )
    message.add_alternative(
        '<div style="font-family:Arial,sans-serif;color:#102536;'
        'line-height:1.55;font-size:16px;">'
        + html_logo_email(base_url)
        + "<h1 style=\"font-size:22px;margin:0 0 12px 0;\">"
        "Bienvenue dans la d&eacute;couverte Premium"
        "</h1>"
        "<p>Votre compte OptiPlein est valid&eacute; et votre acc&egrave;s Premium est "
        "activ&eacute; gratuitement pendant la phase de test de cet &eacute;t&eacute;.</p>"
        "<p>Vous pouvez maintenant profiter des fonctions avanc&eacute;es : "
        "pr&eacute;paration de trajet, calcul de la station la plus rentable, "
        "historique des &eacute;conomies, plusieurs v&eacute;hicules, favoris illimit&eacute;s, "
        "tendances de prix et suggestions de ravitaillement.</p>"
        "<p>Vos retours vont aider &agrave; am&eacute;liorer l’application avant son "
        "lancement officiel. Merci de faire partie des premiers testeurs.</p>"
        '<p style="margin:24px 0;">'
        f'<a href="{base_url}/web" '
        'style="display:inline-block;background:#149f38;color:#ffffff;'
        'text-decoration:none;font-weight:700;padding:12px 18px;'
        'border-radius:8px;">Ouvrir OptiPlein</a>'
        "</p>"
        "</div>",
        subtype="html",
    )

    envoyer_email(message)


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

    date_mise_a_jour = date_mise_a_jour_stations()

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


def normaliser_date_utc(date):

    if not date:
        return None

    if date.tzinfo is None:
        return date.replace(tzinfo=datetime.now().astimezone().tzinfo)

    return date.astimezone(datetime.now().astimezone().tzinfo)


def date_mise_a_jour_stations():

    dates = [
        lire_date_metadata(chemin_metadata_stations()),
        date_derniere_mise_a_jour(),
    ]

    for fichier in (
        STATIONS_RUNTIME_CSV,
        STATIONS_REPO_CSV,
    ):
        try:
            if fichier.exists():
                dates.append(
                    datetime.fromtimestamp(
                        fichier.stat().st_mtime,
                        datetime.now().astimezone().tzinfo,
                    )
                )
        except OSError:
            continue

    dates_valides = [
        normaliser_date_utc(date)
        for date in dates
        if normaliser_date_utc(date)
    ]

    return max(dates_valides) if dates_valides else None


def version_donnees_stations():

    fichier = chemin_stations_csv()
    date_mise_a_jour = date_mise_a_jour_stations()

    try:
        stat = fichier.stat()
        return "|".join(
            (
                date_mise_a_jour.isoformat() if date_mise_a_jour else "",
                str(stat.st_mtime_ns),
                str(stat.st_size),
            )
        )
    except OSError:
        return date_mise_a_jour.isoformat() if date_mise_a_jour else ""


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
def rediriger_vers_application():

    return RedirectResponse(url="/web", status_code=307)


@app.get("/landing")
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
                "Une mise à jour des stations est en cours. "
                "Réessayez dans quelques secondes."
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
        date_mise_a_jour = date_mise_a_jour_stations()
        return {
            "ok": True,
            "stations": len(stations),
            "updated_at": (
                date_mise_a_jour.isoformat()
                if date_mise_a_jour
                else None
            ),
            "data_version": version_donnees_stations(),
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


@app.get("/api/admin/email-status")
def statut_email_admin(request: Request):

    verifier_admin(request)
    return resume_configuration_smtp()


@app.post("/api/admin/test-email")
async def tester_email_admin(test: AdminTestEmail, request: Request):

    verifier_admin(request)
    email = normaliser_email(test.email)

    if not email_valide(email):
        raise HTTPException(
            status_code=422,
            detail="L'adresse e-mail n'est pas valide.",
        )

    message = EmailMessage()
    message["Subject"] = "Test e-mail OptiPlein"
    message["To"] = email
    message.set_content(
        "Test d'envoi OptiPlein réussi.\n\n"
        "Si vous recevez ce message, la configuration SMTP de Render "
        "fonctionne pour les e-mails de validation de compte.\n"
    )

    try:
        await asyncio.to_thread(envoyer_email, message)
    except Exception as erreur:
        logger.exception("Test e-mail admin échoué : %s", erreur)
        raise HTTPException(
            status_code=503,
            detail=message_erreur_smtp(erreur),
        ) from erreur

    return {"ok": True, "email": email}


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


def ajuster_maneuvre_graphhopper(instruction, type_maneuvre, modificateur):

    texte = " ".join(
        str(instruction.get(cle, "") or "").lower()
        for cle in ("text", "street_name", "heading")
    )

    if "sortie" in texte or "exit" in texte:
        return "off ramp", modificateur

    if "bretelle" in texte and (
        "prenez" in texte or "take" in texte
    ):
        return "off ramp", modificateur

    if "restez" in texte or "keep" in texte:
        return "fork", modificateur

    return type_maneuvre, modificateur


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
        type_maneuvre, modificateur = ajuster_maneuvre_graphhopper(
            instruction,
            type_maneuvre,
            modificateur,
        )
        etapes.append(
            {
                "distance": instruction.get("distance", 0),
                "duration": (instruction.get("time", 0) or 0) / 1000,
                "name": instruction.get("street_name", "")
                    or instruction.get("text", "")
                    or "",
                "instruction": instruction.get("text", "") or "",
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

    date_mise_a_jour = date_mise_a_jour_stations()
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
        "updated_at": (
            date_mise_a_jour.isoformat()
            if date_mise_a_jour
            else None
        ),
        "data_version": version_donnees_stations(),
    }


@app.get("/api/derniere-mise-a-jour")
def get_derniere_mise_a_jour():

    rattrapage_lance = lancer_mise_a_jour_stations_si_retard()
    date_mise_a_jour = date_mise_a_jour_stations()
    maintenant = datetime.now().astimezone()
    age_secondes = (
        max(0, int((maintenant - date_mise_a_jour).total_seconds()))
        if date_mise_a_jour
        else None
    )

    return {
        "updated_at": (
            date_mise_a_jour.isoformat()
            if date_mise_a_jour
            else None
        ),
        "server_now": maintenant.isoformat(),
        "age_seconds": age_secondes,
        "data_version": version_donnees_stations(),
        "update_pending": rattrapage_lance,
    }


@app.post("/api/compte/inscription")
def creer_compte(
    identifiants: CompteIdentifiants,
    request: Request,
):

    email = normaliser_email(identifiants.email)

    if not email_valide(email):
        raise HTTPException(
            status_code=422,
            detail="L'adresse e-mail n'est pas valide.",
        )

    comptes = charger_comptes_utilisateurs()
    utilisateurs = comptes.setdefault("users", {})

    utilisateur_existant = utilisateurs.get(email)

    if utilisateur_existant and utilisateur_existant.get(
        "email_verified",
        True,
    ):
        raise HTTPException(
            status_code=409,
            detail="Un compte existe deja avec cette adresse.",
        )

    jeton_validation, empreinte_validation, expiration_validation = (
        creer_jeton_validation_email()
    )
    base_url = url_base_application(request)
    lien_validation = (
        f"{base_url}/api/compte/validation-email"
        f"?token={jeton_validation}"
    )
    maintenant = datetime.now().astimezone().isoformat()

    utilisateurs[email] = {
        "email": email,
        "password": hasher_mot_de_passe(
            identifiants.mot_de_passe
        ),
        "created_at": utilisateur_existant.get(
            "created_at",
            maintenant,
        ) if utilisateur_existant else maintenant,
        "updated_at": maintenant,
        "email_verified": False,
        "email_verification_hash": empreinte_validation,
        "email_verification_expires_at": expiration_validation,
        "data": utilisateur_existant.get(
            "data",
            limiter_donnees_compte(DonneesCompte()),
        ) if utilisateur_existant else limiter_donnees_compte(
            DonneesCompte()
        ),
    }

    try:
        envoyer_email_validation_compte(
            email,
            lien_validation,
            base_url,
        )
    except Exception as erreur:
        logger.exception(
            "Impossible d’envoyer l’e-mail de validation : %s | SMTP=%s",
            erreur,
            resume_configuration_smtp(),
        )
        raise HTTPException(
            status_code=503,
            detail=(
                "L’e-mail de validation n’a pas pu être envoyé. "
                "Réessayez dans quelques instants."
            ),
        ) from erreur

    enregistrer_comptes_utilisateurs(comptes)

    return {
        "ok": True,
        "email": email,
        "verification_required": True,
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

    if not utilisateur.get("email_verified", True):
        raise HTTPException(
            status_code=403,
            detail=(
                "Validez d’abord votre adresse e-mail avec le lien reçu."
            ),
        )

    return {
        "ok": True,
        "email": email,
        "token": creer_session(email),
        "donnees": donnees_compte_premium_test(
            utilisateur.get("data", {})
        ),
    }


@app.get("/api/compte/validation-email")
def valider_email_compte(token: str, request: Request):

    empreinte = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()
    comptes = charger_comptes_utilisateurs()
    utilisateurs = comptes.setdefault("users", {})

    for email, utilisateur in utilisateurs.items():
        if not hmac.compare_digest(
            utilisateur.get("email_verification_hash", ""),
            empreinte,
        ):
            continue

        if time.time() > float(
            utilisateur.get("email_verification_expires_at", 0)
        ):
            raise HTTPException(
                status_code=410,
                detail=(
                    "Le lien de validation a expiré. "
                    "Créez à nouveau votre compte pour recevoir un nouveau lien."
                ),
            )

        utilisateur["email_verified"] = True
        utilisateur.pop("email_verification_hash", None)
        utilisateur.pop("email_verification_expires_at", None)
        utilisateur["updated_at"] = datetime.now().astimezone().isoformat()
        enregistrer_comptes_utilisateurs(comptes)

        try:
            envoyer_email_bienvenue_premium(
                email,
                url_base_application(request),
            )
        except Exception:
            logger.exception(
                "Impossible d’envoyer l’e-mail de bienvenue Premium."
            )

        return RedirectResponse(
            url="/web?email_verifie=1",
            status_code=303,
        )

    raise HTTPException(
        status_code=400,
        detail="Lien de validation invalide.",
    )


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
        "donnees": donnees_compte_premium_test(
            utilisateur.get("data", {})
        ),
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
        "donnees": donnees_compte_premium_test(
            utilisateur.get("data", {})
        ),
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
            detail="L’envoi des signalements n’est pas encore configuré.",
        )
    except Exception:
        logger.exception("L’envoi du signalement a échoué.")
        raise HTTPException(
            status_code=502,
            detail="Le message n’a pas pu être envoyé. Réessayez plus tard.",
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
    date_mise_a_jour = date_mise_a_jour_stations()
    maintenant = datetime.now().astimezone()

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

            "texte_verification": "vérification en attente",

            "date_verification": (
                date_mise_a_jour.isoformat()
                if date_mise_a_jour
                else None
            ),
            "date_serveur": maintenant.isoformat(),
            "age_verification_secondes": (
                max(0, int((maintenant - date_mise_a_jour).total_seconds()))
                if date_mise_a_jour
                else None
            ),
            "data_version": version_donnees_stations(),

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



