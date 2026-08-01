from fastapi import FastAPI, Request
from fastapi import HTTPException
from fastapi.responses import PlainTextResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from typing import Literal, Optional
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field


import asyncio
import csv
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timedelta
from email.message import EmailMessage
from email.utils import getaddresses
import base64
import hashlib
import hmac
import json
import logging
import math
import os
from pathlib import Path
import re
import secrets
import shutil
import smtplib
import ssl
import threading
import time
from zoneinfo import ZoneInfo
import requests as http_requests
from update_data import (
    date_derniere_mise_a_jour,
    mettre_a_jour_stations,
    signature_adresse,
    texte_derniere_mise_a_jour,
)
from optiplein_db import (
    base_donnees_active,
    charger_comptes as charger_comptes_postgres,
    charger_corrections_stations as charger_corrections_stations_postgres,
    charger_testeurs as charger_testeurs_postgres,
    enregistrer_comptes as enregistrer_comptes_postgres,
    enregistrer_correction_station as enregistrer_correction_station_postgres,
    enregistrer_testeurs as enregistrer_testeurs_postgres,
    libelle_stockage,
)


INTERVALLE_MISE_A_JOUR_SECONDES = 10 * 60
RETARD_MISE_A_JOUR_TOLERE_SECONDES = 60
logger = logging.getLogger("optiplein.update")
MISE_A_JOUR_FOND_ACTIVE = os.getenv(
    "OPTIPLEIN_BACKGROUND_UPDATE",
    "false",
).strip().lower() in {"1", "true", "yes", "on"}
MISE_A_JOUR_IRVE_ACTIVE = os.getenv(
    "OPTIPLEIN_IRVE_DAILY_UPDATE",
    "true",
).strip().lower() in {"1", "true", "yes", "on"}
MISE_A_JOUR_IRVE_DYNAMIQUE_ACTIVE = os.getenv(
    "OPTIPLEIN_IRVE_DYNAMIC_UPDATE",
    "true",
).strip().lower() in {"1", "true", "yes", "on"}
IRVE_FUSEAU_HORAIRE = ZoneInfo("Europe/Paris")
IRVE_HEURE_MISE_A_JOUR = 6
EMAIL_SIGNALEMENT = os.getenv(
    "REPORT_EMAIL",
    "optiplein5@gmail.com"
)
APP_BASE_URL = os.getenv("APP_BASE_URL", "").strip().rstrip("/")
ADSENSE_CLIENT = os.getenv(
    "ADSENSE_CLIENT",
    "ca-pub-4904497922619715",
).strip()


def lire_variable_adsense_slot():

    for nom_variable in (
        "ADSENSE_SLOT_MAP",
        "ADSENSE_SLOT",
        "ADSENSE_AD_SLOT",
        "GOOGLE_AD_SLOT",
    ):
        valeur = os.getenv(nom_variable, "").strip()
        if valeur:
            return valeur

    return ""


ADSENSE_SLOT_MAP = lire_variable_adsense_slot()
signalements_recents = {}
mise_a_jour_admin_lock = threading.Lock()
ATTENTE_VERROU_ADMIN_SECONDES = 45


def resoudre_dossier_donnees_utilisateurs():

    dossier_env = os.getenv("OPTIPLEIN_DATA_DIR", "").strip()
    if dossier_env:
        return Path(dossier_env)

    dossier_render = Path("/var/data")
    if dossier_render.exists():
        return dossier_render

    return Path(".")


DOSSIER_DONNEES_UTILISATEURS = resoudre_dossier_donnees_utilisateurs()
COMPTES_UTILISATEURS_FICHIER = (
    DOSSIER_DONNEES_UTILISATEURS
    / "comptes_utilisateurs.json"
)
COMPTES_UTILISATEURS_BACKUP_FICHIER = (
    DOSSIER_DONNEES_UTILISATEURS
    / "comptes_utilisateurs.backup.json"
)
TESTEURS_FICHIER = (
    DOSSIER_DONNEES_UTILISATEURS
    / "testeurs_landing.json"
)
STATIONS_REPO_CSV = Path(__file__).resolve().parent / "stations.csv"
STATIONS_RUNTIME_CSV = DOSSIER_DONNEES_UTILISATEURS / "stations.csv"
IRVE_STATIQUE_URL = (
    "https://proxy.transport.data.gouv.fr/resource/"
    "consolidation-transport-irve-statique"
)
IRVE_DYNAMIQUE_URL = (
    "https://proxy.transport.data.gouv.fr/resource/"
    "consolidation-nationale-irve-dynamique"
)
IRVE_STATIQUE_RESOURCE_ID = "4ca78c71-4ea4-475d-bd3a-d4aef88f7bf8"
IRVE_STATIQUE_API_URL = (
    "https://tabular-api.data.gouv.fr/api/resources/"
    + IRVE_STATIQUE_RESOURCE_ID
    + "/data/"
)
IRVE_STATIQUE_CACHE = DOSSIER_DONNEES_UTILISATEURS / "irve_statique.csv"
IRVE_DYNAMIQUE_CACHE = DOSSIER_DONNEES_UTILISATEURS / "irve_dynamique.csv"
IRVE_STATIQUE_TTL_SECONDES = 24 * 60 * 60
IRVE_DYNAMIQUE_TTL_SECONDES = 5 * 60
IRVE_PRIX_KWH_ESTIME = 0.39
IRVE_CACHE_LOCK = threading.Lock()
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
DELAI_RECUPERATION_MOT_DE_PASSE_SECONDES = 60 * 60
DUREE_SESSION_COMPTE_SECONDES = 90 * 24 * 60 * 60


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

    profil: dict = Field(default_factory=dict)
    favoris: list = Field(default_factory=list)
    vehicules: list = Field(default_factory=list)
    vehicule_actif: str = ""
    vehicule_principal: str = ""
    plan: Literal["free", "premium"] = "free"
    preferences: dict = Field(default_factory=dict)
    historique_economies: list = Field(default_factory=list)
    lieux_trajet: dict = Field(default_factory=dict)
    rayon_stations: int = 25
    securite: dict = Field(default_factory=dict)
    premium: dict = Field(default_factory=dict)
    alertes_prix: list = Field(default_factory=list)
    statistiques: dict = Field(default_factory=dict)
    optimisation: dict = Field(default_factory=dict)


class MiseAJourProfilCompte(BaseModel):

    model_config = ConfigDict(extra="forbid")

    nom: str = Field(default="", max_length=80)
    telephone: str = Field(default="", max_length=30)
    ville: str = Field(default="", max_length=90)


class MiseAJourPreferencesCompte(BaseModel):

    model_config = ConfigDict(extra="allow")

    carburant: str = Field(default="gazole", max_length=20)
    rayon_stations: int = 25
    theme: Literal["auto", "jour", "nuit"] = "auto"
    notifications: bool = True


class ChoixVehiculePrincipalCompte(BaseModel):

    model_config = ConfigDict(extra="forbid")

    vehicule_id: str = Field(max_length=80)


class ListeFavorisCompte(BaseModel):

    model_config = ConfigDict(extra="forbid")

    favoris: list = Field(default_factory=list)


class ListeVehiculesCompte(BaseModel):

    model_config = ConfigDict(extra="forbid")

    vehicules: list = Field(default_factory=list)
    vehicule_actif: str = ""
    vehicule_principal: str = ""


class ListeAlertesPrixCompte(BaseModel):

    model_config = ConfigDict(extra="forbid")

    alertes_prix: list = Field(default_factory=list)


class OptimisationCompte(BaseModel):

    model_config = ConfigDict(extra="allow")

    mode: str = Field(default="rentabilite_reelle", max_length=40)
    valeur_temps_euro_h: float = 9
    detour_max_km: float = 8
    recalcul_auto: bool = True
    longs_trajets: bool = True


class ChangementMotDePasseCompte(BaseModel):

    model_config = ConfigDict(extra="forbid")

    ancien_mot_de_passe: str = Field(min_length=8, max_length=120)
    nouveau_mot_de_passe: str = Field(min_length=8, max_length=120)


class DemandeRecuperationMotDePasse(BaseModel):

    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=5, max_length=160)


class ReinitialisationMotDePasse(BaseModel):

    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=16, max_length=200)
    nouveau_mot_de_passe: str = Field(min_length=8, max_length=120)


class RenvoiValidationEmailCompte(BaseModel):

    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=5, max_length=160)


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
    moteur: Literal[
        "auto",
        "graphhopper",
        "openstreetmap",
        "osm",
        "osrm",
    ] = "auto"


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


def lire_comptes_utilisateurs_depuis_fichier(fichier):

    if not fichier.exists():
        return None

    try:
        with fichier.open(
            encoding="utf-8"
        ) as fichier:
            donnees = json.load(fichier)
            if isinstance(donnees, dict) and "users" in donnees:
                return donnees
    except (OSError, ValueError, TypeError):
        logger.exception(
            "Impossible de lire les comptes utilisateurs."
        )

    return None


def charger_comptes_utilisateurs():

    comptes_postgres = charger_comptes_postgres()
    if comptes_postgres is not None:
        return comptes_postgres

    donnees = lire_comptes_utilisateurs_depuis_fichier(
        COMPTES_UTILISATEURS_FICHIER
    )
    if donnees is not None:
        return donnees

    sauvegarde = lire_comptes_utilisateurs_depuis_fichier(
        COMPTES_UTILISATEURS_BACKUP_FICHIER
    )
    if sauvegarde is not None:
        try:
            COMPTES_UTILISATEURS_FICHIER.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            shutil.copy2(
                COMPTES_UTILISATEURS_BACKUP_FICHIER,
                COMPTES_UTILISATEURS_FICHIER,
            )
        except OSError:
            logger.exception(
                "Impossible de restaurer la sauvegarde des comptes."
            )
        return sauvegarde

    return {"users": {}}


def enregistrer_comptes_utilisateurs(donnees):

    if enregistrer_comptes_postgres(donnees):
        return

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

    try:
        shutil.copy2(
            COMPTES_UTILISATEURS_FICHIER,
            COMPTES_UTILISATEURS_BACKUP_FICHIER,
        )
    except OSError:
        logger.exception(
            "Impossible de créer la sauvegarde des comptes utilisateurs."
        )


def charger_testeurs_landing():

    testeurs_postgres = charger_testeurs_postgres()
    if testeurs_postgres is not None:
        return testeurs_postgres

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

    if enregistrer_testeurs_postgres(donnees):
        return

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


def secret_session_compte():

    secret = (
        os.getenv("ACCOUNT_TOKEN_SECRET", "").strip()
        or ADMIN_PASSWORD
        or APP_BASE_URL
        or "optiplein-session-locale"
    )

    return secret.encode("utf-8")


def encoder_base64_url(donnees):

    return base64.urlsafe_b64encode(donnees).decode("ascii").rstrip("=")


def decoder_base64_url(texte):

    padding = "=" * (-len(texte) % 4)
    return base64.urlsafe_b64decode((texte + padding).encode("ascii"))


def signer_session_compte(corps):

    signature = hmac.new(
        secret_session_compte(),
        corps.encode("ascii"),
        hashlib.sha256,
    ).digest()

    return encoder_base64_url(signature)


def creer_session(email):

    maintenant = int(time.time())
    payload = {
        "email": email,
        "iat": maintenant,
        "exp": maintenant + DUREE_SESSION_COMPTE_SECONDES,
    }
    corps = encoder_base64_url(
        json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    signature = signer_session_compte(corps)
    jeton = f"v1.{corps}.{signature}"
    SESSIONS_UTILISATEURS[jeton] = email

    return jeton


def email_depuis_session_signee(jeton):

    try:
        version, corps, signature = jeton.split(".", 2)
    except ValueError:
        return None

    if version != "v1":
        return None

    signature_attendue = signer_session_compte(corps)
    if not hmac.compare_digest(signature, signature_attendue):
        return None

    try:
        payload = json.loads(
            decoder_base64_url(corps).decode("utf-8")
        )
    except (ValueError, TypeError, UnicodeDecodeError):
        return None

    email = normaliser_email(payload.get("email", ""))
    expiration = int(payload.get("exp", 0) or 0)

    if not email or time.time() > expiration:
        return None

    return email


def email_depuis_requete(request):

    autorisation = request.headers.get("Authorization", "")
    prefixe = "Bearer "

    if not autorisation.startswith(prefixe):
        raise HTTPException(
            status_code=401,
            detail="Connexion requise.",
        )

    jeton = autorisation[len(prefixe):].strip()
    email = email_depuis_session_signee(jeton)

    if not email:
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

    if not premium_actif_donnees(donnees):
        raise HTTPException(
            status_code=403,
            detail="Acces Premium requis.",
        )

    return email


def compte_depuis_email_ou_404(comptes, email):

    utilisateur = comptes.get("users", {}).get(email)

    if not utilisateur:
        raise HTTPException(
            status_code=404,
            detail="Compte introuvable.",
        )

    return utilisateur


def compte_depuis_requete_ou_404(request):

    email = email_depuis_requete(request)
    comptes = charger_comptes_utilisateurs()
    utilisateur = compte_depuis_email_ou_404(comptes, email)

    return email, comptes, utilisateur


def date_iso_maintenant():

    return datetime.now().astimezone().isoformat()


def ids_vehicules(donnees):

    return {
        str(vehicule.get("id", ""))
        for vehicule in donnees.get("vehicules", [])
        if isinstance(vehicule, dict) and vehicule.get("id")
    }


def premier_id_vehicule(donnees):

    for vehicule in donnees.get("vehicules", []):
        if isinstance(vehicule, dict) and vehicule.get("id"):
            return str(vehicule.get("id"))

    return ""


def synchroniser_meta_securite(utilisateur):

    donnees = utilisateur.setdefault("data", {})
    donnees["profil"] = profil_compte_nettoye(
        donnees.get("profil", {}),
        utilisateur.get("email", ""),
    )
    donnees["preferences"] = preferences_compte_nettoye(
        donnees.get("preferences", {}),
        donnees.get("rayon_stations", 25),
    )
    donnees["rayon_stations"] = donnees["preferences"]["rayon_stations"]
    donnees["securite"] = securite_compte_nettoyee(
        donnees.get("securite", {}),
        utilisateur,
    )
    return donnees


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
        "stockage": {
            "type": libelle_stockage(),
            "postgresql_active": base_donnees_active(),
            "data_dir": str(DOSSIER_DONNEES_UTILISATEURS),
            "accounts_file": str(COMPTES_UTILISATEURS_FICHIER),
            "accounts_file_exists": COMPTES_UTILISATEURS_FICHIER.exists(),
            "accounts_backup_exists": (
                COMPTES_UTILISATEURS_BACKUP_FICHIER.exists()
            ),
        },
        "adsense": {
            "client_configured": bool(ADSENSE_CLIENT),
            "slot_map_configured": bool(ADSENSE_SLOT_MAP),
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

    sources = [
        (lire_fichier_enrichissement_stations(
            ENRICHISSEMENT_STATIONS_REPO_FICHIER
        ), False),
    ]

    corrections_postgres = charger_corrections_stations_postgres()

    if corrections_postgres is not None:
        sources.append((corrections_postgres, True))
    else:
        sources.extend(
            [
                (
                    lire_fichier_enrichissement_stations(
                        ENRICHISSEMENT_STATIONS_ADMIN_FICHIER
                    ),
                    True,
                ),
                (
                    lire_fichier_enrichissement_stations(
                        CORRECTIONS_STATIONS_ADMIN_FICHIER
                    ),
                    True,
                ),
            ]
        )

    for donnees, source_admin in sources:
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

    station_id = str(station.get("id", "") or correction.id)
    corrections_existantes = charger_enrichissements_stations()
    entree = corrections_existantes.get(station_id, {})
    latitude_corrigee = correction.latitude
    if latitude_corrigee is None:
        latitude_corrigee = entree.get("latitude_corrigee")
    longitude_corrigee = correction.longitude
    if longitude_corrigee is None:
        longitude_corrigee = entree.get("longitude_corrigee")
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

    if enregistrer_correction_station_postgres(
        station_id,
        entree_correction,
    ):
        return

    donnees = lire_fichier_enrichissement_stations(
        ENRICHISSEMENT_STATIONS_ADMIN_FICHIER
    )
    stations = donnees.setdefault("stations", {})
    entree = stations.setdefault(station_id, {})
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


def limiter_texte_compte(valeur, longueur):

    return str(valeur or "").strip()[:longueur]


def profil_compte_nettoye(profil, email=""):

    profil = dict(profil or {})

    return {
        "email": normaliser_email(profil.get("email") or email),
        "nom": limiter_texte_compte(profil.get("nom"), 80),
        "telephone": limiter_texte_compte(profil.get("telephone"), 30),
        "ville": limiter_texte_compte(profil.get("ville"), 90),
    }


def preferences_compte_nettoye(preferences, rayon_stations=25):

    preferences = dict(preferences or {})
    carburant = limiter_texte_compte(
        preferences.get("carburant", "gazole"),
        20,
    ).lower()
    if carburant not in {
        "gazole",
        "sp95",
        "sp98",
        "e10",
        "e85",
        "gplc",
        "electrique",
    }:
        carburant = "gazole"

    theme = preferences.get("theme", "auto")
    if theme not in {"auto", "jour", "nuit"}:
        theme = "auto"

    try:
        rayon = int(preferences.get("rayon_stations", rayon_stations) or 25)
    except (TypeError, ValueError):
        rayon = 25

    return {
        "carburant": carburant,
        "rayon_stations": max(5, min(50, rayon)),
        "theme": theme,
        "notifications": bool(preferences.get("notifications", True)),
    }


PROFILS_VEHICULES_AUTORISES = {
    "essence",
    "diesel",
    "e85",
    "gpl",
    "hybride",
    "electrique",
}


PROFILS_VEHICULES = {
    "essence": {
        "libelle": "Essence",
        "capacite_unite": "L",
        "consommation_unite": "L/100 km",
    },
    "diesel": {
        "libelle": "Diesel",
        "capacite_unite": "L",
        "consommation_unite": "L/100 km",
    },
    "e85": {
        "libelle": "E85",
        "capacite_unite": "L",
        "consommation_unite": "L/100 km",
    },
    "gpl": {
        "libelle": "GPL",
        "capacite_unite": "L",
        "consommation_unite": "L/100 km",
    },
    "hybride": {
        "libelle": "Hybride",
        "capacite_unite": "L",
        "consommation_unite": "L/100 km",
    },
    "electrique": {
        "libelle": "\u00c9lectrique",
        "capacite_unite": "kWh",
        "consommation_unite": "kWh/100 km",
    },
}


def profil_vehicule_valide(profil):

    profil = limiter_texte_compte(profil, 30).lower()

    return profil if profil in PROFILS_VEHICULES_AUTORISES else "essence"


def normaliser_nombre_texte(valeur, longueur=20):

    texte = limiter_texte_compte(valeur, longueur).replace(",", ".")

    if not texte:
        return ""

    try:
        nombre = float(texte)
    except ValueError:
        return ""

    if nombre <= 0:
        return ""

    if nombre.is_integer():
        return str(int(nombre))

    return str(round(nombre, 2)).rstrip("0").rstrip(".")


def vehicule_compte_nettoye(vehicule):

    vehicule = dict(vehicule or {})
    profil = profil_vehicule_valide(
        vehicule.get("profil") or vehicule.get("motorisation")
    )
    reservoir = normaliser_nombre_texte(vehicule.get("reservoir"))
    conso = normaliser_nombre_texte(vehicule.get("conso"))
    autonomie = normaliser_nombre_texte(vehicule.get("autonomie"))

    if not autonomie and reservoir and conso:
        try:
            autonomie = str(round(float(reservoir) / float(conso) * 100))
        except (TypeError, ValueError, ZeroDivisionError):
            autonomie = ""

    try:
        jauge = int(float(vehicule.get("jauge", 50) or 50))
    except (TypeError, ValueError):
        jauge = 50

    return {
        "id": limiter_texte_compte(vehicule.get("id"), 80),
        "nom": limiter_texte_compte(vehicule.get("nom"), 40) or "Mon v\u00e9hicule",
        "profil": profil,
        "motorisation": profil,
        "reservoir": reservoir,
        "conso": conso,
        "autonomie": autonomie,
        "parametres": limiter_texte_compte(vehicule.get("parametres"), 160),
        "jauge": max(0, min(100, jauge)),
    }


def vehicules_compte_nettoyes(vehicules):

    vehicules_nettoyes = []
    ids = set()

    for vehicule in list(vehicules or [])[:5]:
        vehicule_nettoye = vehicule_compte_nettoye(vehicule)
        if not vehicule_nettoye["id"] or vehicule_nettoye["id"] in ids:
            continue

        ids.add(vehicule_nettoye["id"])
        vehicules_nettoyes.append(vehicule_nettoye)

    return vehicules_nettoyes


def securite_compte_nettoyee(securite, utilisateur=None):

    securite = dict(securite or {})
    utilisateur = utilisateur or {}

    return {
        "email_verifie": bool(utilisateur.get("email_verified", True)),
        "dernier_changement_mot_de_passe": limiter_texte_compte(
            securite.get("dernier_changement_mot_de_passe"),
            40,
        ),
        "derniere_connexion": limiter_texte_compte(
            securite.get("derniere_connexion"),
            40,
        ),
    }


CAPACITES_PREMIUM = {
    "optimisation_avancee": {
        "libelle": "Optimisation avancée",
        "description": (
            "Compare les stations une à une avec détour, consommation, "
            "temps perdu, puissance de charge et trajet réel."
        ),
    },
    "alertes_prix": {
        "libelle": "Alertes de prix",
        "description": (
            "Prépare des seuils d'alerte par carburant, station ou zone."
        ),
    },
    "favoris_illimites": {
        "libelle": "Favoris illimités",
        "description": "Retire la limite de 3 favoris de la version gratuite.",
    },
    "historique_avance": {
        "libelle": "Historique avancé",
        "description": (
            "Conserve les économies détaillées avec station, véhicule, "
            "énergie, distance et contexte du trajet."
        ),
    },
    "statistiques": {
        "libelle": "Statistiques",
        "description": (
            "Calcule les économies totales, moyennes et les usages par "
            "véhicule ou énergie."
        ),
    },
    "optimisation_longs_trajets": {
        "libelle": "Optimisation des longs trajets",
        "description": (
            "Prépare plusieurs ravitaillements ou recharges selon autonomie, "
            "jauge et rentabilité réelle."
        ),
    },
}


def premium_actif_donnees(donnees):

    return PREMIUM_TEST_ACTIF or donnees.get("plan") == "premium"


def limites_premium(donnees):

    premium = premium_actif_donnees(donnees)

    return {
        "premium_actif": premium,
        "favoris_max": None if premium else 3,
        "vehicules_max": 5 if premium else 1,
        "historique_max": 1000 if premium else 30,
        "recalcul_secondes": 15 if premium else 180,
        "longs_trajets": premium,
        "alertes_prix": premium,
        "statistiques": premium,
        "prix": "gratuit tout l'été" if PREMIUM_TEST_ACTIF else "3,99 €/an",
    }


def normaliser_alerte_prix(alerte):

    alerte = dict(alerte or {})
    type_energie = limiter_texte_compte(
        alerte.get("energie") or alerte.get("carburant") or "gazole",
        20,
    ).lower()

    return {
        "id": limiter_texte_compte(alerte.get("id"), 80),
        "energie": type_energie,
        "carburant": type_energie,
        "seuil": normaliser_nombre_texte(alerte.get("seuil")),
        "condition": limiter_texte_compte(
            alerte.get("condition") or "inferieur",
            30,
        ),
        "zone": limiter_texte_compte(alerte.get("zone"), 120),
        "station_id": limiter_texte_compte(alerte.get("station_id"), 80),
        "active": bool(alerte.get("active", True)),
        "created_at": limiter_texte_compte(alerte.get("created_at"), 40),
    }


def alertes_prix_nettoyees(alertes):

    alertes_nettoyees = []
    ids = set()

    for alerte in list(alertes or [])[:100]:
        alerte_nettoyee = normaliser_alerte_prix(alerte)
        if not alerte_nettoyee["id"]:
            alerte_nettoyee["id"] = secrets.token_urlsafe(8)
        if alerte_nettoyee["id"] in ids:
            continue
        ids.add(alerte_nettoyee["id"])
        alertes_nettoyees.append(alerte_nettoyee)

    return alertes_nettoyees


def optimisation_compte_nettoyee(optimisation):

    optimisation = dict(optimisation or {})

    try:
        valeur_temps = float(
            str(optimisation.get("valeur_temps_euro_h", 9))
            .replace(",", ".")
        )
    except (TypeError, ValueError):
        valeur_temps = 9

    try:
        marge_detour = float(
            str(optimisation.get("detour_max_km", 8)).replace(",", ".")
        )
    except (TypeError, ValueError):
        marge_detour = 8

    return {
        "mode": limiter_texte_compte(
            optimisation.get("mode") or "rentabilite_reelle",
            40,
        ),
        "valeur_temps_euro_h": max(0, min(60, valeur_temps)),
        "detour_max_km": max(0, min(80, marge_detour)),
        "recalcul_auto": bool(optimisation.get("recalcul_auto", True)),
        "longs_trajets": bool(optimisation.get("longs_trajets", True)),
    }


def statistiques_compte(historique):

    total = 0.0
    total_2026 = 0.0
    economies = []
    par_energie = {}
    par_vehicule = {}

    for ligne in list(historique or []):
        try:
            economie = float(ligne.get("economie", 0) or 0)
        except (TypeError, ValueError):
            economie = 0.0

        total += economie
        economies.append(economie)

        date = None
        try:
            date = datetime.fromisoformat(
                str(ligne.get("date", "")).replace("Z", "+00:00")
            )
        except ValueError:
            date = None
        if date and date.year == 2026:
            total_2026 += economie

        energie = ligne.get("carburant") or ligne.get("energie") or "inconnu"
        vehicule = ligne.get("vehicule") or "Véhicule non renseigné"
        par_energie[energie] = par_energie.get(energie, 0.0) + economie
        par_vehicule[vehicule] = par_vehicule.get(vehicule, 0.0) + economie

    return {
        "economies_total": round(total, 2),
        "economies_2026": round(total_2026, 2),
        "trajets": len(economies),
        "economie_moyenne": round(total / len(economies), 2)
            if economies else 0,
        "par_energie": {
            cle: round(valeur, 2)
            for cle, valeur in par_energie.items()
        },
        "par_vehicule": {
            cle: round(valeur, 2)
            for cle, valeur in par_vehicule.items()
        },
    }


def premium_compte_nettoye(donnees):

    historique = donnees.get("historique_economies", [])

    return {
        "test_gratuit_ete": PREMIUM_TEST_ACTIF,
        "capacites": CAPACITES_PREMIUM,
        "limites": limites_premium(donnees),
        "alertes_prix": alertes_prix_nettoyees(
            donnees.get("alertes_prix", [])
        ),
        "optimisation": optimisation_compte_nettoyee(
            donnees.get("optimisation", {})
        ),
        "statistiques": statistiques_compte(historique),
    }


def limiter_donnees_compte(donnees):

    donnees.favoris = donnees.favoris[:500]
    donnees.vehicules = vehicules_compte_nettoyes(donnees.vehicules)
    donnees.historique_economies = donnees.historique_economies[:1000]
    donnees.alertes_prix = alertes_prix_nettoyees(donnees.alertes_prix)
    donnees.optimisation = optimisation_compte_nettoyee(donnees.optimisation)
    donnees.rayon_stations = max(
        5,
        min(50, int(donnees.rayon_stations or 25)),
    )
    if PREMIUM_TEST_ACTIF:
        donnees.plan = "premium"

    donnees.profil = profil_compte_nettoye(donnees.profil)
    donnees.preferences = preferences_compte_nettoye(
        donnees.preferences,
        donnees.rayon_stations,
    )
    donnees.rayon_stations = donnees.preferences["rayon_stations"]
    donnees.vehicule_principal = limiter_texte_compte(
        donnees.vehicule_principal or donnees.vehicule_actif,
        80,
    )
    ids = ids_vehicules(donnees.model_dump())
    if donnees.vehicule_actif not in ids:
        donnees.vehicule_actif = premier_id_vehicule(donnees.model_dump())
    if donnees.vehicule_principal not in ids:
        donnees.vehicule_principal = donnees.vehicule_actif
    donnees.securite = securite_compte_nettoyee(donnees.securite)
    donnees.statistiques = statistiques_compte(donnees.historique_economies)
    donnees.premium = premium_compte_nettoye(donnees.model_dump())

    return donnees.model_dump()


def donnees_compte_premium_test(donnees):

    donnees = dict(donnees or {})
    donnees.setdefault("profil", profil_compte_nettoye({}))
    donnees.setdefault("preferences", preferences_compte_nettoye({}))
    donnees.setdefault("vehicule_principal", donnees.get("vehicule_actif", ""))
    donnees.setdefault("securite", securite_compte_nettoyee({}))
    donnees.setdefault("alertes_prix", alertes_prix_nettoyees([]))
    donnees.setdefault("optimisation", optimisation_compte_nettoyee({}))
    donnees.setdefault(
        "statistiques",
        statistiques_compte(donnees.get("historique_economies", [])),
    )
    if PREMIUM_TEST_ACTIF:
        donnees["plan"] = "premium"
    donnees["premium"] = premium_compte_nettoye(donnees)
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


def creer_jeton_recuperation_mot_de_passe():

    jeton = secrets.token_urlsafe(32)
    empreinte = hashlib.sha256(
        jeton.encode("utf-8")
    ).hexdigest()
    expiration = time.time() + DELAI_RECUPERATION_MOT_DE_PASSE_SECONDES

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


def envoyer_email_recuperation_mot_de_passe(email, lien, base_url):

    message = EmailMessage()
    message["Subject"] = "R\u00e9initialisation de votre mot de passe OptiPlein"
    message["To"] = email
    message.set_content(
        "Vous avez demand\u00e9 la r\u00e9initialisation de votre mot de passe "
        "OptiPlein.\n\n"
        "Cliquez sur ce lien pour choisir un nouveau mot de passe :\n"
        f"{lien}\n\n"
        "Ce lien est valable 1 heure. Si vous n'\u00eates pas \u00e0 l'origine "
        "de cette demande, ignorez simplement cet e-mail.\n"
    )
    message.add_alternative(
        '<div style="font-family:Arial,sans-serif;color:#102536;'
        'line-height:1.55;font-size:16px;">'
        + html_logo_email(base_url)
        + "<h1 style=\"font-size:22px;margin:0 0 12px 0;\">"
        "R\u00e9initialisation de votre mot de passe"
        "</h1>"
        "<p>Vous avez demand&eacute; la r&eacute;initialisation de votre mot de "
        "passe OptiPlein.</p>"
        '<p style="margin:24px 0;">'
        f'<a href="{lien}" '
        'style="display:inline-block;background:#149f38;color:#ffffff;'
        'text-decoration:none;font-weight:700;padding:12px 18px;'
        'border-radius:8px;">Choisir un nouveau mot de passe</a>'
        "</p>"
        "<p>Ce lien est valable 1 heure. Si vous n'&ecirc;tes pas &agrave; "
        "l'origine de cette demande, ignorez simplement cet e-mail.</p>"
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
                "Mise \u00e0 jour automatique ignor\u00e9e : "
                "une mise \u00e0 jour est d\u00e9j\u00e0 en cours."
            )
        else:
            try:
                await asyncio.to_thread(
                    mettre_a_jour_stations
                )
            except Exception:
                logger.exception(
                    "La mise \u00e0 jour automatique des prix a \u00e9chou\u00e9."
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


def prochaine_mise_a_jour_irve(maintenant=None):

    maintenant = maintenant or datetime.now(IRVE_FUSEAU_HORAIRE)
    maintenant = maintenant.astimezone(IRVE_FUSEAU_HORAIRE)
    prochaine = maintenant.replace(
        hour=IRVE_HEURE_MISE_A_JOUR,
        minute=0,
        second=0,
        microsecond=0,
    )
    if prochaine <= maintenant:
        prochaine += timedelta(days=1)
    return prochaine


async def actualiser_irve_statique_quotidiennement():

    if not IRVE_STATIQUE_CACHE.exists():
        try:
            await asyncio.to_thread(telecharger_irve_statique)
        except Exception:
            logger.exception(
                "Le t\u00e9l\u00e9chargement initial du fichier IRVE a \u00e9chou\u00e9."
            )

    while True:
        maintenant = datetime.now(IRVE_FUSEAU_HORAIRE)
        prochaine = prochaine_mise_a_jour_irve(maintenant)
        attente = max(0, (prochaine - maintenant).total_seconds())
        logger.info(
            "Prochaine mise \u00e0 jour IRVE statique programm\u00e9e pour %s.",
            prochaine.isoformat(),
        )
        await asyncio.sleep(attente)

        try:
            await asyncio.to_thread(telecharger_irve_statique)
        except Exception:
            logger.exception(
                "La mise \u00e0 jour quotidienne du fichier IRVE a \u00e9chou\u00e9."
            )


async def actualiser_irve_dynamique_periodiquement():

    while True:
        debut = asyncio.get_running_loop().time()

        try:
            await asyncio.to_thread(telecharger_irve_dynamique)
        except Exception:
            logger.exception(
                "La mise \u00e0 jour du fichier IRVE dynamique a \u00e9chou\u00e9."
            )

        duree = asyncio.get_running_loop().time() - debut
        await asyncio.sleep(
            max(0, IRVE_DYNAMIQUE_TTL_SECONDES - duree)
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
                "La mise \u00e0 jour automatique de rattrapage a \u00e9chou\u00e9."
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
    tache_mise_a_jour_irve = None
    tache_mise_a_jour_irve_dynamique = None

    if MISE_A_JOUR_FOND_ACTIVE:
        tache_mise_a_jour = asyncio.create_task(
            actualiser_prix_periodiquement()
        )
    if MISE_A_JOUR_IRVE_ACTIVE:
        tache_mise_a_jour_irve = asyncio.create_task(
            actualiser_irve_statique_quotidiennement()
        )
    if MISE_A_JOUR_IRVE_DYNAMIQUE_ACTIVE:
        tache_mise_a_jour_irve_dynamique = asyncio.create_task(
            actualiser_irve_dynamique_periodiquement()
        )

    yield

    taches = [
        tache
        for tache in (
            tache_mise_a_jour,
            tache_mise_a_jour_irve,
            tache_mise_a_jour_irve_dynamique,
        )
        if tache
    ]
    for tache in taches:
        tache.cancel()
    for tache in taches:
        with suppress(asyncio.CancelledError):
            await tache


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


def fichier_cache_recent(chemin, ttl_secondes):

    try:
        return (
            chemin.exists()
            and time.time() - chemin.stat().st_mtime < ttl_secondes
            and chemin.stat().st_size > 0
        )
    except OSError:
        return False


def rafraichir_cache_csv(url, chemin, ttl_secondes):

    if fichier_cache_recent(chemin, ttl_secondes):
        return chemin

    with IRVE_CACHE_LOCK:
        if fichier_cache_recent(chemin, ttl_secondes):
            return chemin

        chemin.parent.mkdir(parents=True, exist_ok=True)
        temporaire = chemin.with_suffix(chemin.suffix + ".tmp")
        with http_requests.get(url, stream=True, timeout=45) as reponse:
            reponse.raise_for_status()
            with temporaire.open("wb") as fichier:
                for bloc in reponse.iter_content(1024 * 1024):
                    if bloc:
                        fichier.write(bloc)
        temporaire.replace(chemin)

    return chemin


def telecharger_irve_statique():

    chemin = IRVE_STATIQUE_CACHE

    with IRVE_CACHE_LOCK:
        chemin.parent.mkdir(parents=True, exist_ok=True)
        temporaire = chemin.with_suffix(chemin.suffix + ".tmp")

        try:
            with http_requests.get(
                IRVE_STATIQUE_URL,
                stream=True,
                timeout=120,
            ) as reponse:
                reponse.raise_for_status()
                with temporaire.open("wb") as fichier:
                    for bloc in reponse.iter_content(1024 * 1024):
                        if bloc:
                            fichier.write(bloc)

            if not temporaire.exists() or temporaire.stat().st_size == 0:
                raise ValueError("Le fichier IRVE telecharge est vide.")

            # Verifie que la ressource ressemble bien a un CSV avant de
            # remplacer la derniere copie exploitable.
            with temporaire.open("rb") as fichier:
                entete = fichier.read(4096)
            if b"id_station" not in entete and b"id_pdc" not in entete:
                raise ValueError("Le fichier IRVE telecharge est invalide.")

            temporaire.replace(chemin)
        finally:
            temporaire.unlink(missing_ok=True)

    logger.info(
        "Fichier IRVE statique actualise (%s octets).",
        chemin.stat().st_size,
    )
    return chemin


def telecharger_irve_dynamique():

    chemin = IRVE_DYNAMIQUE_CACHE

    with IRVE_CACHE_LOCK:
        chemin.parent.mkdir(parents=True, exist_ok=True)
        temporaire = chemin.with_suffix(chemin.suffix + ".tmp")

        try:
            with http_requests.get(
                IRVE_DYNAMIQUE_URL,
                stream=True,
                timeout=60,
            ) as reponse:
                reponse.raise_for_status()
                with temporaire.open("wb") as fichier:
                    for bloc in reponse.iter_content(1024 * 1024):
                        if bloc:
                            fichier.write(bloc)

            if not temporaire.exists() or temporaire.stat().st_size == 0:
                raise ValueError(
                    "Le fichier IRVE dynamique telecharge est vide."
                )

            with temporaire.open("rb") as fichier:
                entete = fichier.read(4096)
            if b"id_pdc" not in entete or b"etat_pdc" not in entete:
                raise ValueError(
                    "Le fichier IRVE dynamique telecharge est invalide."
                )

            temporaire.replace(chemin)
        finally:
            temporaire.unlink(missing_ok=True)

    logger.info(
        "Fichier IRVE dynamique actualise (%s octets).",
        chemin.stat().st_size,
    )
    return chemin


def lignes_csv_cache(chemin):

    with chemin.open(encoding="utf-8-sig", newline="") as fichier:
        echantillon = fichier.read(4096)
        fichier.seek(0)
        try:
            dialecte = csv.Sniffer().sniff(echantillon, delimiters=",;\t")
        except csv.Error:
            dialecte = csv.excel

        yield from csv.DictReader(fichier, dialect=dialecte)


def valeur_booleenne_irve(valeur):

    return str(valeur or "").strip().lower() in {"true", "1", "yes", "oui"}


def valeur_float_irve(valeur):

    try:
        return float(str(valeur or "").replace(",", "."))
    except (TypeError, ValueError):
        return None


def coordonnees_irve(ligne):

    latitude = valeur_float_irve(ligne.get("consolidated_latitude"))
    longitude = valeur_float_irve(ligne.get("consolidated_longitude"))

    if latitude is not None and longitude is not None:
        return latitude, longitude

    texte = str(ligne.get("coordonneesXY") or "").strip(" []")
    morceaux = [morceau.strip() for morceau in texte.split(",")]
    if len(morceaux) >= 2:
        longitude = valeur_float_irve(morceaux[0])
        latitude = valeur_float_irve(morceaux[1])
        if latitude is not None and longitude is not None:
            return latitude, longitude

    return None, None


def prises_irve(ligne):

    prises = []
    correspondance = (
        ("prise_type_combo_ccs", "Combo CCS"),
        ("prise_type_chademo", "CHAdeMO"),
        ("prise_type_2", "Type 2"),
        ("prise_type_ef", "EF"),
        ("prise_type_autre", "Autre"),
    )

    for champ, libelle in correspondance:
        if valeur_booleenne_irve(ligne.get(champ)):
            prises.append(libelle)

    return prises


def prix_kwh_irve(ligne):

    if valeur_booleenne_irve(ligne.get("gratuit")):
        return 0.0, False

    texte = str(ligne.get("tarification") or "")
    recherche = re.search(
        r"(\d+(?:[,.]\d+)?)\s*(?:€|eur|euro)?\s*/?\s*kwh",
        texte,
        re.IGNORECASE,
    )

    if recherche:
        prix = valeur_float_irve(recherche.group(1))
        if prix is not None and 0 <= prix <= 3:
            return prix, False

    return IRVE_PRIX_KWH_ESTIME, True


def charger_disponibilites_irve():

    try:
        chemin = rafraichir_cache_csv(
            IRVE_DYNAMIQUE_URL,
            IRVE_DYNAMIQUE_CACHE,
            IRVE_DYNAMIQUE_TTL_SECONDES,
        )
    except Exception:
        logger.exception("Disponibilite IRVE indisponible.")
        return {}

    disponibilites = {}
    for ligne in lignes_csv_cache(chemin):
        identifiant = str(ligne.get("id_pdc_itinerance") or "").strip()
        if not identifiant:
            continue

        disponibilites[identifiant] = {
            "etat": ligne.get("etat_pdc", "") or "",
            "occupation": ligne.get("occupation_pdc", "") or "",
            "horodatage": ligne.get("horodatage", "") or "",
        }

    return disponibilites


def ajouter_disponibilite_irve(station, disponibilite):

    if not disponibilite:
        station["disponibilite_inconnue"] += 1
        return

    etat = str(disponibilite.get("etat") or "").lower()
    occupation = str(disponibilite.get("occupation") or "").lower()

    if etat == "en_service" and occupation == "libre":
        station["disponibles"] += 1
    elif etat == "en_service" and occupation in {"occupe", "occupé"}:
        station["occupes"] += 1
    elif etat and etat not in {"inconnu", "unknown"}:
        station["hors_service"] += 1
    else:
        station["disponibilite_inconnue"] += 1

    if disponibilite.get("horodatage"):
        station["disponibilite_horodatage"] = max(
            station.get("disponibilite_horodatage", ""),
            disponibilite.get("horodatage", ""),
        )


def libelle_disponibilite_irve(station):

    if station["disponibles"]:
        return f"{station['disponibles']} disponible(s)"

    if station["occupes"]:
        return "occupée"

    if station["hors_service"]:
        return "hors service"

    return "disponibilité inconnue"


def limites_recherche_irve(latitude, longitude, rayon):

    latitude = float(latitude)
    longitude = float(longitude)
    rayon = max(1, min(100, int(rayon or 25)))
    marge_latitude = rayon / 111
    marge_longitude = rayon / (
        111 * max(0.25, math.cos(math.radians(latitude)))
    )

    return {
        "consolidated_latitude__greater": latitude - marge_latitude,
        "consolidated_latitude__less": latitude + marge_latitude,
        "consolidated_longitude__greater": longitude - marge_longitude,
        "consolidated_longitude__less": longitude + marge_longitude,
    }


def lignes_irve_statiques_api(latitude, longitude, rayon, limite):

    parametres = {
        cle: str(valeur)
        for cle, valeur in limites_recherche_irve(
            latitude,
            longitude,
            rayon,
        ).items()
    }
    # L'API tabulaire data.gouv.fr limite actuellement les pages a 200
    # lignes. Une valeur superieure provoque une erreur 400 et empeche
    # l'affichage de toutes les bornes.
    parametres["page_size"] = str(max(50, min(200, int(limite or 250) * 4)))

    url = IRVE_STATIQUE_API_URL
    lignes = []
    pages = 0
    while url and pages < 8 and len(lignes) < max(500, limite * 6):
        reponse = http_requests.get(
            url,
            params=parametres if pages == 0 else None,
            timeout=15,
        )
        reponse.raise_for_status()
        donnees = reponse.json()
        lignes.extend(donnees.get("data") or [])
        url = (donnees.get("links") or {}).get("next")
        parametres = None
        pages += 1

    return lignes


def preparer_bornes_irve(
    latitude,
    longitude,
    rayon=25,
    limite=250,
):

    if latitude is None or longitude is None:
        return []

    try:
        lignes_statiques = lignes_irve_statiques_api(
            latitude,
            longitude,
            rayon,
            limite,
        )
    except Exception as erreur:
        logger.exception("API IRVE statique indisponible.")
        raise HTTPException(
            status_code=503,
            detail="Bornes IRVE indisponibles",
        ) from erreur

    disponibilites = charger_disponibilites_irve()
    rayon = max(1, min(100, int(rayon or 25)))
    stations = {}

    for ligne in lignes_statiques:
        latitude_borne, longitude_borne = coordonnees_irve(ligne)
        if latitude_borne is None or longitude_borne is None:
            continue

        distance = distance_km(
            latitude,
            longitude,
            latitude_borne,
            longitude_borne,
        )
        if distance > rayon:
            continue

        station_id = (
            ligne.get("id_station_itinerance")
            or ligne.get("id_station_local")
            or ligne.get("id_pdc_itinerance")
            or ligne.get("id_pdc_local")
            or ""
        ).strip()
        if not station_id:
            continue

        station = stations.setdefault(
            station_id,
            {
                "id": "irve-" + station_id,
                "source_id": station_id,
                "enseigne": (
                    ligne.get("nom_enseigne")
                    or ligne.get("nom_station")
                    or ligne.get("nom_operateur")
                    or "Borne de recharge"
                ),
                "adresse": ligne.get("adresse_station", "") or "",
                "cp": ligne.get("consolidated_code_postal", "") or "",
                "ville": ligne.get("consolidated_commune", "") or "",
                "latitude": latitude_borne,
                "longitude": longitude_borne,
                "distance": round(distance, 2),
                "energie": "electric",
                "carburant": "electrique",
                "prises": set(),
                "puissance_kw": 0.0,
                "nbre_pdc": 0,
                "disponibles": 0,
                "occupes": 0,
                "hors_service": 0,
                "disponibilite_inconnue": 0,
                "disponibilite_horodatage": "",
                "prix": IRVE_PRIX_KWH_ESTIME,
                "prix_estime": True,
                "tarification": "",
            },
        )

        station["distance"] = min(station["distance"], round(distance, 2))
        station["puissance_kw"] = max(
            station["puissance_kw"],
            valeur_float_irve(ligne.get("puissance_nominale")) or 0.0,
        )
        station["nbre_pdc"] += 1
        station["prises"].update(prises_irve(ligne))
        prix, prix_estime = prix_kwh_irve(ligne)
        if not prix_estime or station["prix_estime"]:
            station["prix"] = prix
            station["prix_estime"] = prix_estime
        if ligne.get("tarification") and not station["tarification"]:
            station["tarification"] = ligne.get("tarification", "")

        ajouter_disponibilite_irve(
            station,
            disponibilites.get(
                str(ligne.get("id_pdc_itinerance") or "").strip()
            ),
        )

    bornes = []
    for station in stations.values():
        station["prises"] = sorted(station["prises"])
        station["disponibilite"] = libelle_disponibilite_irve(station)
        bornes.append(station)

    bornes.sort(
        key=lambda station: (
            0 if station["disponibles"] else 1,
            station["distance"],
            -station["puissance_kw"],
        )
    )

    return bornes[:max(1, min(500, int(limite or 250)))]


MENU_PAGES_EDITORIALES = [
    ("accueil", "Accueil", "/"),
    ("fonctionnement", "Fonctionnement", "/comment-fonctionne-optiplein"),
    ("pourquoi", "Pourquoi OptiPlein", "/pourquoi-optiplein"),
    ("faq", "FAQ", "/faq"),
    ("contact", "Contact", "/contact"),
]


PAGES_EDITORIALES = {
    "accueil": {
        "slug": "",
        "title": "OptiPlein - Le plein malin",
        "nav_title": "Accueil",
        "description": (
            "OptiPlein aide les conducteurs \u00e0 comparer les prix des "
            "carburants, rep\u00e9rer les stations proches et choisir le "
            "ravitaillement le plus rentable."
        ),
        "eyebrow": "Comparateur carburant et assistant de trajet",
        "hero_title": "Le plein malin, avant m\u00eame d'arriver \u00e0 la pompe.",
        "lead": (
            "OptiPlein combine prix officiels, position, v\u00e9hicule et "
            "itin\u00e9raire pour aider chaque conducteur \u00e0 prendre une d\u00e9cision "
            "simple : o\u00f9 faire le plein sans perdre son temps ni son argent."
        ),
        "cta_label": "Ouvrir l'application",
        "cta_url": "/web",
        "secondary_cta_label": "Devenir testeur",
        "secondary_cta_url": "/landing",
        "highlights": [
            {
                "title": "Prix actualis\u00e9s",
                "text": "Les donn\u00e9es carburants sont mises \u00e0 jour r\u00e9guli\u00e8rement \u00e0 partir des sources publiques disponibles.",
            },
            {
                "title": "Calcul utile",
                "text": "Le prix seul ne suffit pas : OptiPlein tient compte du trajet et de votre v\u00e9hicule.",
            },
            {
                "title": "Carte lisible",
                "text": "Les stations et les prix sont affich\u00e9s directement sur la carte pour comparer rapidement.",
            },
        ],
        "sections": [
            {
                "title": "Une application pens\u00e9e pour les conducteurs",
                "paragraphs": [
                    (
                        "Comparer quelques centimes par litre peut sembler simple, "
                        "mais le meilleur choix d\u00e9pend aussi de la distance, de la "
                        "consommation, du niveau du r\u00e9servoir et de la direction que "
                        "vous prenez."
                    ),
                    (
                        "OptiPlein regroupe ces informations dans une interface "
                        "lisible afin de vous aider \u00e0 choisir une station sans "
                        "multiplier les recherches."
                    ),
                ],
            },
            {
                "title": "Des fonctions gratuites pendant la phase de test",
                "paragraphs": [
                    (
                        "Pendant la d\u00e9couverte de l'application, la cr\u00e9ation de "
                        "compte permet d'acc\u00e9der gratuitement aux fonctions avanc\u00e9es "
                        "pr\u00e9vues pour les testeurs."
                    )
                ],
                "bullets": [
                    "comparaison des stations proches",
                    "v\u00e9hicules sauvegard\u00e9s",
                    "favoris",
                    "historique des \u00e9conomies",
                    "pr\u00e9paration de trajet avec ravitaillements conseill\u00e9s",
                ],
            },
        ],
    },
    "fonctionnement": {
        "slug": "comment-fonctionne-optiplein",
        "title": "Comment fonctionne OptiPlein ?",
        "nav_title": "Fonctionnement",
        "description": (
            "Découvrez comment OptiPlein utilise les prix carburants, la "
            "g\u00e9olocalisation et les informations du v\u00e9hicule pour calculer "
            "les stations les plus rentables."
        ),
        "eyebrow": "Mode d'emploi",
        "hero_title": "Comment fonctionne OptiPlein",
        "lead": (
            "L'application part d'une id\u00e9e simple : le carburant le moins cher "
            "n'est pas toujours le plein le plus rentable si le d\u00e9tour co\u00fbte "
            "plus cher que l'\u00e9conomie r\u00e9alis\u00e9e."
        ),
        "sections": [
            {
                "title": "1. S\u00e9lection du carburant",
                "paragraphs": [
                    (
                        "L'utilisateur choisit son carburant. Les prix disponibles "
                        "s'affichent ensuite automatiquement sur la carte autour "
                        "de sa position ou du trajet pr\u00e9par\u00e9."
                    )
                ],
            },
            {
                "title": "2. Prise en compte du v\u00e9hicule",
                "paragraphs": [
                    (
                        "Le nom du v\u00e9hicule, la taille du r\u00e9servoir et la "
                        "consommation moyenne permettent d'affiner les calculs. "
                        "Ces informations aident \u00e0 estimer le co\u00fbt r\u00e9el d'un "
                        "d\u00e9tour et l'int\u00e9r\u00eat d'un ravitaillement."
                    )
                ],
            },
            {
                "title": "3. Comparaison des stations",
                "paragraphs": [
                    (
                        "OptiPlein compare les stations une \u00e0 une dans le rayon "
                        "choisi. L'objectif est de faire ressortir la solution la "
                        "plus logique, pas seulement le prix brut le plus bas."
                    )
                ],
            },
            {
                "title": "4. Guidage et recalcul",
                "paragraphs": [
                    (
                        "Lorsque l'utilisateur lance un itin\u00e9raire, l'application "
                        "affiche le trajet et peut proposer un recalcul si une "
                        "station devient plus int\u00e9ressante ou si l'utilisateur "
                        "s'\u00e9carte du parcours."
                    )
                ],
            },
        ],
    },
    "pourquoi": {
        "slug": "pourquoi-optiplein",
        "title": "Pourquoi utiliser OptiPlein ?",
        "nav_title": "Pourquoi",
        "description": (
            "OptiPlein aide \u00e0 \u00e9viter les mauvais choix carburant en comparant "
            "prix, distance, consommation et trajet r\u00e9el."
        ),
        "eyebrow": "La promesse",
        "hero_title": "Parce que le meilleur prix n'est pas toujours le meilleur choix.",
        "lead": (
            "Une station peut afficher un prix attractif, mais devenir moins "
            "int\u00e9ressante si elle impose un d\u00e9tour trop long. OptiPlein met "
            "les chiffres dans le bon ordre."
        ),
        "highlights": [
            {
                "title": "Moins d'hésitation",
                "text": "Les prix sont visibles directement sur la carte.",
            },
            {
                "title": "Moins de d\u00e9tours inutiles",
                "text": "Le calcul tient compte de la distance et du v\u00e9hicule.",
            },
            {
                "title": "Plus de transparence",
                "text": "Les donn\u00e9es utilis\u00e9es sont expliqu\u00e9es et mises \u00e0 jour.",
            },
        ],
        "sections": [
            {
                "title": "Un outil pour le quotidien",
                "paragraphs": [
                    (
                        "OptiPlein s'adresse aux conducteurs qui veulent garder "
                        "la main sur leur budget carburant sans passer plusieurs "
                        "minutes \u00e0 comparer des applications ou des panneaux de "
                        "prix."
                    )
                ],
            },
            {
                "title": "Une aide, pas une promesse magique",
                "paragraphs": [
                    (
                        "Les r\u00e9sultats d\u00e9pendent des prix disponibles, de la "
                        "position, du trafic, de la consommation renseign\u00e9e et du "
                        "trajet r\u00e9el. L'application donne une estimation utile "
                        "pour aider \u00e0 d\u00e9cider, mais le conducteur reste toujours "
                        "responsable de sa conduite et de ses choix."
                    )
                ],
            },
        ],
    },
    "a-propos": {
        "slug": "a-propos",
        "title": "\u00c0 propos d'OptiPlein",
        "nav_title": "\u00c0 propos",
        "description": (
            "OptiPlein est un projet fran\u00e7ais qui aide les conducteurs \u00e0 mieux "
            "comparer les stations-service et les prix des carburants."
        ),
        "eyebrow": "Le projet",
        "hero_title": "\u00c0 propos d'OptiPlein",
        "lead": (
            "OptiPlein est construit avec une ambition concr\u00e8te : rendre la "
            "comparaison carburant plus utile, plus lisible et plus proche de "
            "la vraie d\u00e9cision du conducteur."
        ),
        "sections": [
            {
                "title": "Une application en phase de test",
                "paragraphs": [
                    (
                        "L'application \u00e9volue avec les retours des premiers "
                        "utilisateurs. Les tests permettent d'am\u00e9liorer la "
                        "qualit\u00e9 de la carte, les calculs d'\u00e9conomie, le guidage "
                        "et l'exp\u00e9rience mobile."
                    )
                ],
            },
            {
                "title": "Une approche progressive",
                "paragraphs": [
                    (
                        "OptiPlein ajoute les fonctionnalit\u00e9s et les donn\u00e9es \u00e9tape "
                        "par \u00e9tape afin de garder une application claire et fiable. "
                        "Les informations importantes pour l'utilisateur sont "
                        "mises en avant avant les options plus avanc\u00e9es."
                    )
                ],
            },
        ],
    },
    "faq": {
        "slug": "faq",
        "title": "FAQ OptiPlein",
        "nav_title": "FAQ",
        "description": (
            "Questions fr\u00e9quentes sur OptiPlein, les prix carburants, les "
            "comptes, la g\u00e9olocalisation, les favoris et les donn\u00e9es utilis\u00e9es."
        ),
        "eyebrow": "Questions fr\u00e9quentes",
        "hero_title": "FAQ OptiPlein",
        "lead": "Les r\u00e9ponses aux questions les plus utiles avant d'utiliser l'application.",
        "faq_items": [
            {
                "question": "OptiPlein vend-il du carburant ?",
                "answer": (
                    "Non. OptiPlein est un service d'aide \u00e0 la comparaison. "
                    "L'application ne vend pas de carburant et ne fixe pas les prix."
                ),
            },
            {
                "question": "D'o\u00f9 viennent les prix affich\u00e9s ?",
                "answer": (
                    "Les prix proviennent des donn\u00e9es publiques disponibles et "
                    "peuvent \u00eatre compl\u00e9t\u00e9s par des corrections manuelles lorsque "
                    "des informations de station doivent \u00eatre pr\u00e9cis\u00e9es."
                ),
            },
            {
                "question": "Pourquoi une station peut-elle \u00eatre indiqu\u00e9e comme plus rentable ?",
                "answer": (
                    "Le calcul ne regarde pas uniquement le prix au litre. Il "
                    "prend aussi en compte la distance, la consommation renseign\u00e9e "
                    "et le co\u00fbt du trajet pour \u00e9viter les d\u00e9tours qui annulent "
                    "l'\u00e9conomie."
                ),
            },
            {
                "question": "La g\u00e9olocalisation est-elle obligatoire ?",
                "answer": (
                    "Elle est n\u00e9cessaire pour afficher votre position, trouver les "
                    "stations autour de vous et calculer un itin\u00e9raire. Vous pouvez "
                    "la refuser dans les r\u00e9glages de votre appareil."
                ),
            },
            {
                "question": "Pourquoi cr\u00e9er un compte ?",
                "answer": (
                    "Le compte permet de sauvegarder les v\u00e9hicules, favoris, "
                    "pr\u00e9f\u00e9rences et historiques afin de les retrouver sur un autre "
                    "t\u00e9l\u00e9phone."
                ),
            },
        ],
    },
    "contact": {
        "slug": "contact",
        "title": "Contact OptiPlein",
        "nav_title": "Contact",
        "description": (
            "Contacter OptiPlein pour une question, un retour testeur, un "
            "signalement ou une demande li\u00e9e aux donn\u00e9es personnelles."
        ),
        "eyebrow": "Nous contacter",
        "hero_title": "Contact",
        "lead": (
            "Une question, un retour ou un probl\u00e8me \u00e0 signaler ? Le contact "
            "principal d'OptiPlein est disponible par e-mail."
        ),
        "contact": True,
        "sections": [
            {
                "title": "Demandes utiles",
                "paragraphs": [
                    (
                        "Pour acc\u00e9l\u00e9rer le traitement, indiquez votre appareil, "
                        "la ville concern\u00e9e, le carburant s\u00e9lectionn\u00e9 et une "
                        "description pr\u00e9cise du probl\u00e8me lorsque c'est possible."
                    )
                ],
                "bullets": [
                    "question sur l'application",
                    "probl\u00e8me d'affichage ou de carte",
                    "station mal renseign\u00e9e",
                    "demande relative au compte ou aux donn\u00e9es personnelles",
                ],
            }
        ],
    },
    "mentions": {
        "slug": "mentions-legales",
        "title": "Mentions l\u00e9gales OptiPlein",
        "nav_title": "Mentions l\u00e9gales",
        "description": (
            "Mentions l\u00e9gales du site et de l'application OptiPlein : \u00e9diteur, "
            "contact, h\u00e9bergement et responsabilit\u00e9s."
        ),
        "eyebrow": "Informations l\u00e9gales",
        "hero_title": "Mentions l\u00e9gales",
        "lead": "Les informations d'identification et de contact du service OptiPlein.",
        "sections": [
            {
                "title": "\u00c9diteur du service",
                "paragraphs": [
                    (
                        "OptiPlein est un service \u00e9dit\u00e9 par J. Stoudji. Pour toute "
                        "question relative au site, \u00e0 l'application ou aux donn\u00e9es, "
                        "vous pouvez \u00e9crire \u00e0 optiplein5@gmail.com."
                    )
                ],
            },
            {
                "title": "H\u00e9bergement",
                "paragraphs": [
                    (
                        "Le service web est h\u00e9berg\u00e9 par Render. Les noms de domaine "
                        "et services techniques associ\u00e9s peuvent \u00eatre fournis par "
                        "les prestataires configur\u00e9s pour optiplein.fr."
                    )
                ],
            },
            {
                "title": "Responsabilit\u00e9",
                "paragraphs": [
                    (
                        "OptiPlein fournit une aide \u00e0 la d\u00e9cision \u00e0 partir des "
                        "donn\u00e9es disponibles. Les prix, disponibilit\u00e9s, trajets et "
                        "conditions de circulation peuvent varier. Le conducteur "
                        "reste responsable de sa conduite, de ses arr\u00eats et du "
                        "respect du code de la route."
                    )
                ],
            },
        ],
    },
    "confidentialite": {
        "slug": "confidentialite",
        "title": "Politique de confidentialit\u00e9 OptiPlein",
        "nav_title": "Confidentialit\u00e9",
        "description": (
            "Politique de confidentialit\u00e9 OptiPlein : g\u00e9olocalisation, compte, "
            "v\u00e9hicules, favoris, historique et droits des utilisateurs."
        ),
        "eyebrow": "Donn\u00e9es personnelles",
        "hero_title": "Politique de confidentialit\u00e9",
        "lead": (
            "Cette page explique quelles donn\u00e9es sont utilis\u00e9es par OptiPlein "
            "et pour quelles finalit\u00e9s."
        ),
        "updated": "24 juillet 2026",
        "sections": [
            {
                "title": "G\u00e9olocalisation",
                "paragraphs": [
                    (
                        "Avec l'autorisation de l'utilisateur, OptiPlein utilise "
                        "la position pr\u00e9cise de l'appareil pour afficher la carte, "
                        "rechercher les stations proches, estimer les \u00e9conomies et "
                        "calculer un itin\u00e9raire."
                    )
                ],
            },
            {
                "title": "Compte et v\u00e9hicules",
                "paragraphs": [
                    (
                        "Lorsqu'un compte est cr\u00e9\u00e9, OptiPlein peut conserver "
                        "l'adresse e-mail, les v\u00e9hicules enregistr\u00e9s, les favoris, "
                        "le type de compte, l'historique d'\u00e9conomies et les "
                        "pr\u00e9f\u00e9rences utiles \u00e0 l'exp\u00e9rience."
                    )
                ],
            },
            {
                "title": "Services techniques",
                "paragraphs": [
                    (
                        "La carte, le calcul d'itin\u00e9raire, l'h\u00e9bergement et les "
                        "outils de mesure ou de publicit\u00e9 peuvent recevoir des "
                        "informations techniques strictement n\u00e9cessaires \u00e0 leur "
                        "fonctionnement, comme l'adresse IP ou les donn\u00e9es utiles "
                        "\u00e0 la requ\u00eate demand\u00e9e."
                    )
                ],
            },
            {
                "title": "Vos droits",
                "paragraphs": [
                    (
                        "Vous pouvez demander l'acc\u00e8s, la rectification ou la "
                        "suppression de vos informations en \u00e9crivant \u00e0 "
                        "optiplein5@gmail.com. Une page d\u00e9di\u00e9e \u00e0 la suppression "
                        "de compte est \u00e9galement disponible."
                    )
                ],
            },
        ],
    },
    "conditions": {
        "slug": "conditions-utilisation",
        "title": "Conditions d'utilisation OptiPlein",
        "nav_title": "Conditions",
        "description": (
            "Conditions d'utilisation du site et de l'application OptiPlein : "
            "service, compte, responsabilit\u00e9s et limites."
        ),
        "eyebrow": "Cadre d'utilisation",
        "hero_title": "Conditions d'utilisation",
        "lead": (
            "Ces conditions encadrent l'utilisation du site, de l'application "
            "et des services OptiPlein."
        ),
        "updated": "24 juillet 2026",
        "sections": [
            {
                "title": "Objet du service",
                "paragraphs": [
                    (
                        "OptiPlein aide les utilisateurs \u00e0 comparer des stations, "
                        "des prix de carburant et des trajets. Le service est une "
                        "aide \u00e0 la d\u00e9cision et ne remplace pas le jugement du "
                        "conducteur."
                    )
                ],
            },
            {
                "title": "Utilisation responsable",
                "paragraphs": [
                    (
                        "L'application ne doit pas \u00eatre manipul\u00e9e de mani\u00e8re "
                        "dangereuse pendant la conduite. Toute consultation ou "
                        "modification doit \u00eatre effectu\u00e9e dans le respect des "
                        "r\u00e8gles de s\u00e9curit\u00e9 routi\u00e8re."
                    )
                ],
            },
            {
                "title": "Compte utilisateur",
                "paragraphs": [
                    (
                        "L'utilisateur est responsable de l'exactitude des "
                        "informations renseign\u00e9es, notamment les caract\u00e9ristiques "
                        "du v\u00e9hicule. Ces informations influencent les calculs "
                        "d'\u00e9conomie."
                    )
                ],
            },
            {
                "title": "\u00c9volution du service",
                "paragraphs": [
                    (
                        "OptiPlein peut \u00e9voluer, corriger ou suspendre certaines "
                        "fonctionnalit\u00e9s afin d'am\u00e9liorer la fiabilit\u00e9, la s\u00e9curit\u00e9 "
                        "ou l'exp\u00e9rience utilisateur."
                    )
                ],
            },
        ],
    },
    "cookies": {
        "slug": "politique-cookies",
        "title": "Politique des cookies OptiPlein",
        "nav_title": "Cookies",
        "description": (
            "Politique des cookies OptiPlein : stockage local, compte, "
            "pr\u00e9f\u00e9rences, publicit\u00e9 et services tiers."
        ),
        "eyebrow": "Cookies et stockage local",
        "hero_title": "Politique des cookies",
        "lead": (
            "OptiPlein utilise le stockage local et peut utiliser des cookies "
            "ou technologies similaires pour faire fonctionner l'application et "
            "les services associ\u00e9s."
        ),
        "updated": "24 juillet 2026",
        "sections": [
            {
                "title": "Stockage n\u00e9cessaire",
                "paragraphs": [
                    (
                        "Certaines informations sont stock\u00e9es localement pour "
                        "conserver les pr\u00e9f\u00e9rences, les v\u00e9hicules, les favoris ou "
                        "la session du compte. Ce stockage est utile au bon "
                        "fonctionnement de l'application."
                    )
                ],
            },
            {
                "title": "Publicit\u00e9",
                "paragraphs": [
                    (
                        "Lorsque Google AdSense est activ\u00e9, Google peut utiliser "
                        "des cookies ou technologies similaires pour mesurer et "
                        "diffuser les annonces selon ses propres r\u00e8gles."
                    )
                ],
            },
            {
                "title": "Gestion",
                "paragraphs": [
                    (
                        "Vous pouvez supprimer les cookies et donn\u00e9es de site via "
                        "les r\u00e9glages de votre navigateur. Sur mobile, certaines "
                        "autorisations se g\u00e8rent aussi depuis les r\u00e9glages du "
                        "t\u00e9l\u00e9phone."
                    )
                ],
            },
        ],
    },
}


def chemin_page_editoriale(identifiant):

    page = PAGES_EDITORIALES[identifiant]
    slug = page.get("slug", "")

    return "/" + slug if slug else "/"


def contexte_page_editoriale(request, identifiant):

    base_url = url_base_application(request)
    chemin = chemin_page_editoriale(identifiant)
    page = dict(PAGES_EDITORIALES[identifiant])
    page["path"] = chemin

    return {
        "page": page,
        "active_page": identifiant,
        "menu_pages": MENU_PAGES_EDITORIALES,
        "footer_pages": [
            ("a-propos", "\u00c0 propos", "/a-propos"),
            ("contact", "Contact", "/contact"),
            ("mentions", "Mentions l\u00e9gales", "/mentions-legales"),
            ("confidentialite", "Confidentialit\u00e9", "/confidentialite"),
            ("conditions", "Conditions d'utilisation", "/conditions-utilisation"),
            ("cookies", "Cookies", "/politique-cookies"),
        ],
        "canonical_url": base_url + chemin,
        "base_url": base_url,
        "og_image": base_url + "/static/logo.png",
        "adsense_client": ADSENSE_CLIENT,
    }


def rendre_page_editoriale(request, identifiant):

    if identifiant not in PAGES_EDITORIALES:
        raise HTTPException(status_code=404, detail="Page introuvable.")

    return templates.TemplateResponse(
        request=request,
        name="editorial.html",
        context=contexte_page_editoriale(request, identifiant),
    )


@app.get("/")
def accueil_editorial(request: Request):

    return rendre_page_editoriale(request, "accueil")


@app.get("/accueil")
def accueil_editorial_alias(request: Request):

    return rendre_page_editoriale(request, "accueil")


@app.get("/comment-fonctionne-optiplein")
def page_fonctionnement(request: Request):

    return rendre_page_editoriale(request, "fonctionnement")


@app.get("/pourquoi-optiplein")
def page_pourquoi(request: Request):

    return rendre_page_editoriale(request, "pourquoi")


@app.get("/a-propos")
def page_a_propos(request: Request):

    return rendre_page_editoriale(request, "a-propos")


@app.get("/faq")
def page_faq(request: Request):

    return rendre_page_editoriale(request, "faq")


@app.get("/contact")
def page_contact(request: Request):

    return rendre_page_editoriale(request, "contact")


@app.get("/mentions-legales")
def page_mentions_legales(request: Request):

    return rendre_page_editoriale(request, "mentions")


@app.get("/conditions-utilisation")
def page_conditions_utilisation(request: Request):

    return rendre_page_editoriale(request, "conditions")


@app.get("/conditions")
def page_conditions_alias(request: Request):

    return RedirectResponse(url="/conditions-utilisation", status_code=308)


@app.get("/politique-cookies")
def page_cookies(request: Request):

    return rendre_page_editoriale(request, "cookies")


@app.get("/cookies")
def page_cookies_alias():

    return RedirectResponse(url="/politique-cookies", status_code=308)


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
            detail="Une mise \u00e0 jour est d\u00e9j\u00e0 en cours.",
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
            "La mise \u00e0 jour forc\u00e9e depuis l'administration a \u00e9chou\u00e9."
        )
        raise HTTPException(
            status_code=500,
            detail=(
                "Mise \u00e0 jour impossible pour le moment : "
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

    return rendre_page_editoriale(request, "confidentialite")


@app.get("/politique-de-confidentialite")
def confidentialite_alias():

    return RedirectResponse(url="/confidentialite", status_code=308)


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


def calculer_itineraire_openstreetmap(points, cap_depart=None):

    donnees = calculer_itineraire_osrm(points, cap_depart)
    donnees["provider"] = "openstreetmap"
    return donnees


def normaliser_moteur_itineraire(moteur):

    if moteur in {"openstreetmap", "osm", "osrm"}:
        return "openstreetmap"

    if moteur == "graphhopper":
        return "graphhopper"

    return "auto"


def fournisseurs_itineraire(moteur):

    moteur = normaliser_moteur_itineraire(moteur)
    fournisseurs = {
        "graphhopper": {
            "nom": "graphhopper",
            "actif": bool(GRAPHHOPPER_API_KEY),
            "calculer": calculer_itineraire_graphhopper,
            "utilise_cap_depart": False,
            "erreur": "GraphHopper indisponible",
        },
        "openstreetmap": {
            "nom": "openstreetmap",
            "actif": True,
            "calculer": calculer_itineraire_openstreetmap,
            "utilise_cap_depart": True,
            "erreur": "OpenStreetMap indisponible",
        },
    }

    if moteur == "auto":
        return [
            fournisseur
            for fournisseur in (
                fournisseurs["graphhopper"],
                fournisseurs["openstreetmap"],
            )
            if fournisseur["actif"]
        ]

    return [fournisseurs[moteur]] if fournisseurs[moteur]["actif"] else []


@app.post("/api/itineraire")
async def calculer_itineraire(requete: RequeteItineraire):

    moteur = normaliser_moteur_itineraire(requete.moteur)
    fournisseurs = fournisseurs_itineraire(moteur)
    derniere_erreur = None

    if not fournisseurs:
        raise HTTPException(
            status_code=502,
            detail=(
                "GraphHopper indisponible"
                if moteur == "graphhopper"
                else "itinéraire indisponible"
            ),
        )

    for fournisseur in fournisseurs:
        try:
            if fournisseur["utilise_cap_depart"]:
                return await asyncio.to_thread(
                    fournisseur["calculer"],
                    requete.points,
                    requete.cap_depart,
                )

            return await asyncio.to_thread(
                fournisseur["calculer"],
                requete.points,
            )
        except Exception as erreur:
            derniere_erreur = erreur
            logger.exception(
                "%s indisponible.",
                fournisseur["nom"],
            )

            if moteur != "auto":
                raise HTTPException(
                    status_code=502,
                    detail=fournisseur["erreur"],
                ) from erreur

    if derniere_erreur:
        logger.error(
            "Itinéraire indisponible avec tous les fournisseurs."
        )

    raise HTTPException(
        status_code=502,
        detail="itinéraire indisponible",
    )


@app.get("/api/itineraire/statut")
def statut_itineraire():

    fournisseurs = fournisseurs_itineraire("auto")

    return {
        "graphhopper_configure": bool(GRAPHHOPPER_API_KEY),
        "moteur_prioritaire": (
            "graphhopper" if GRAPHHOPPER_API_KEY else "openstreetmap"
        ),
        "fournisseurs": [
            fournisseur["nom"]
            for fournisseur in fournisseurs
        ],
        "fallback": "openstreetmap",
        "alias": {
            "osrm": "openstreetmap",
            "osm": "openstreetmap",
        },
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

    carburant = (carburant or "gazole").lower()
    if carburant == "electrique":
        bornes = preparer_bornes_irve(latitude, longitude, rayon)
        return {
            "stations": bornes,
            "count": len(bornes),
            "updated_at": None,
            "data_version": version_irve(),
            "source": "irve",
        }

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


def version_irve():

    try:
        statique = IRVE_STATIQUE_CACHE.stat()
        dynamique = IRVE_DYNAMIQUE_CACHE.stat()
        return "|".join(
            (
                str(statique.st_mtime_ns),
                str(statique.st_size),
                str(dynamique.st_mtime_ns),
                str(dynamique.st_size),
            )
        )
    except OSError:
        return "irve"


@app.get("/api/bornes-irve")
def get_bornes_irve(
    latitude: float,
    longitude: float,
    rayon: int = 25,
    limite: int = 250,
):

    bornes = preparer_bornes_irve(
        latitude,
        longitude,
        rayon,
        limite,
    )

    return {
        "bornes": bornes,
        "stations": bornes,
        "count": len(bornes),
        "updated_at": None,
        "data_version": version_irve(),
        "source": "irve",
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
            detail="Un compte existe d\u00e9j\u00e0 avec cette adresse.",
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
    donnees_initiales = utilisateur_existant.get(
        "data",
        limiter_donnees_compte(DonneesCompte()),
    ) if utilisateur_existant else limiter_donnees_compte(DonneesCompte())
    donnees_initiales["profil"] = profil_compte_nettoye(
        donnees_initiales.get("profil", {}),
        email,
    )
    donnees_initiales["securite"] = securite_compte_nettoyee(
        donnees_initiales.get("securite", {}),
        {"email_verified": False},
    )

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
        "data": donnees_initiales,
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

    donnees = synchroniser_meta_securite(utilisateur)
    donnees["securite"]["derniere_connexion"] = date_iso_maintenant()
    utilisateur["updated_at"] = date_iso_maintenant()
    enregistrer_comptes_utilisateurs(comptes)

    return {
        "ok": True,
        "email": email,
        "token": creer_session(email),
        "donnees": donnees_compte_premium_test(
            donnees
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
            str(utilisateur.get("email_verification_hash") or ""),
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
        utilisateur["updated_at"] = date_iso_maintenant()
        synchroniser_meta_securite(utilisateur)
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

    email, _comptes, utilisateur = compte_depuis_requete_ou_404(request)
    donnees = synchroniser_meta_securite(utilisateur)

    return {
        "ok": True,
        "email": email,
        "donnees": donnees_compte_premium_test(
            donnees
        ),
    }


@app.post("/api/compte/sauvegarde")
def sauvegarder_donnees_compte(
    sauvegarde: SauvegardeCompte,
    request: Request,
):

    email, comptes, utilisateur = compte_depuis_requete_ou_404(request)

    utilisateur["data"] = limiter_donnees_compte(
        sauvegarde.donnees
    )
    utilisateur["data"]["profil"] = profil_compte_nettoye(
        utilisateur["data"].get("profil", {}),
        email,
    )
    utilisateur["data"]["securite"] = securite_compte_nettoyee(
        utilisateur["data"].get("securite", {}),
        utilisateur,
    )
    utilisateur["updated_at"] = date_iso_maintenant()
    enregistrer_comptes_utilisateurs(comptes)

    return {
        "ok": True,
        "updated_at": utilisateur["updated_at"],
        "donnees": donnees_compte_premium_test(
            utilisateur.get("data", {})
        ),
    }


@app.get("/api/compte/profil")
def lire_profil_compte(request: Request):

    email, _comptes, utilisateur = compte_depuis_requete_ou_404(request)
    donnees = synchroniser_meta_securite(utilisateur)

    return {
        "ok": True,
        "email": email,
        "profil": donnees.get("profil", {}),
        "securite": donnees.get("securite", {}),
    }


@app.patch("/api/compte/profil")
def modifier_profil_compte(
    profil: MiseAJourProfilCompte,
    request: Request,
):

    email, comptes, utilisateur = compte_depuis_requete_ou_404(request)
    donnees = synchroniser_meta_securite(utilisateur)
    donnees["profil"] = profil_compte_nettoye(
        profil.model_dump(),
        email,
    )
    utilisateur["updated_at"] = date_iso_maintenant()
    enregistrer_comptes_utilisateurs(comptes)

    return {
        "ok": True,
        "profil": donnees["profil"],
        "updated_at": utilisateur["updated_at"],
    }


@app.patch("/api/compte/preferences")
def modifier_preferences_compte(
    preferences: MiseAJourPreferencesCompte,
    request: Request,
):

    _email, comptes, utilisateur = compte_depuis_requete_ou_404(request)
    donnees = synchroniser_meta_securite(utilisateur)
    donnees["preferences"] = preferences_compte_nettoye(
        preferences.model_dump(),
        preferences.rayon_stations,
    )
    donnees["rayon_stations"] = donnees["preferences"]["rayon_stations"]
    utilisateur["updated_at"] = date_iso_maintenant()
    enregistrer_comptes_utilisateurs(comptes)

    return {
        "ok": True,
        "preferences": donnees["preferences"],
        "updated_at": utilisateur["updated_at"],
    }


@app.get("/api/compte/vehicules")
def lire_vehicules_compte(request: Request):

    _email, _comptes, utilisateur = compte_depuis_requete_ou_404(request)
    donnees = synchroniser_meta_securite(utilisateur)

    return {
        "ok": True,
        "vehicules": donnees.get("vehicules", []),
        "vehicule_actif": donnees.get("vehicule_actif", ""),
        "vehicule_principal": donnees.get("vehicule_principal", ""),
    }


@app.get("/api/compte/profils-vehicules")
def lire_profils_vehicules_compte():

    return {
        "ok": True,
        "profils": PROFILS_VEHICULES,
    }


@app.get("/api/premium/architecture")
def architecture_premium():

    donnees = {
        "plan": "premium" if PREMIUM_TEST_ACTIF else "free",
        "historique_economies": [],
    }

    return {
        "test_gratuit_ete": PREMIUM_TEST_ACTIF,
        "prix": "gratuit tout l'été" if PREMIUM_TEST_ACTIF else "3,99 €/an",
        "capacites": CAPACITES_PREMIUM,
        "limites": limites_premium(donnees),
        "modules": {
            "optimisation_avancee": "moteur_rentabilite",
            "alertes_prix": "alertes_prix",
            "favoris_illimites": "favoris",
            "historique_avance": "historique_economies",
            "statistiques": "statistiques",
            "optimisation_longs_trajets": "trajets_prepares",
        },
    }


@app.put("/api/compte/vehicules")
def remplacer_vehicules_compte(
    vehicules: ListeVehiculesCompte,
    request: Request,
):

    _email, comptes, utilisateur = compte_depuis_requete_ou_404(request)
    donnees = synchroniser_meta_securite(utilisateur)
    vehicules_limites = vehicules_compte_nettoyes(vehicules.vehicules)
    donnees["vehicules"] = vehicules_limites
    ids = ids_vehicules(donnees)
    donnees["vehicule_actif"] = (
        vehicules.vehicule_actif
        if vehicules.vehicule_actif in ids
        else premier_id_vehicule(donnees)
    )
    donnees["vehicule_principal"] = (
        vehicules.vehicule_principal
        if vehicules.vehicule_principal in ids
        else donnees["vehicule_actif"]
    )
    utilisateur["updated_at"] = date_iso_maintenant()
    enregistrer_comptes_utilisateurs(comptes)

    return {
        "ok": True,
        "vehicules": donnees["vehicules"],
        "vehicule_actif": donnees["vehicule_actif"],
        "vehicule_principal": donnees["vehicule_principal"],
        "updated_at": utilisateur["updated_at"],
    }


@app.put("/api/compte/vehicule-principal")
def definir_vehicule_principal_compte(
    choix: ChoixVehiculePrincipalCompte,
    request: Request,
):

    _email, comptes, utilisateur = compte_depuis_requete_ou_404(request)
    donnees = synchroniser_meta_securite(utilisateur)

    if choix.vehicule_id not in ids_vehicules(donnees):
        raise HTTPException(
            status_code=404,
            detail="V\u00e9hicule introuvable.",
        )

    donnees["vehicule_principal"] = choix.vehicule_id
    donnees["vehicule_actif"] = choix.vehicule_id
    utilisateur["updated_at"] = date_iso_maintenant()
    enregistrer_comptes_utilisateurs(comptes)

    return {
        "ok": True,
        "vehicule_principal": choix.vehicule_id,
        "updated_at": utilisateur["updated_at"],
    }


@app.get("/api/compte/favoris")
def lire_favoris_compte(request: Request):

    _email, _comptes, utilisateur = compte_depuis_requete_ou_404(request)
    donnees = synchroniser_meta_securite(utilisateur)

    return {
        "ok": True,
        "favoris": donnees.get("favoris", []),
    }


@app.put("/api/compte/favoris")
def remplacer_favoris_compte(
    favoris: ListeFavorisCompte,
    request: Request,
):

    _email, comptes, utilisateur = compte_depuis_requete_ou_404(request)
    donnees = synchroniser_meta_securite(utilisateur)
    donnees["favoris"] = favoris.favoris[:500]
    utilisateur["updated_at"] = date_iso_maintenant()
    enregistrer_comptes_utilisateurs(comptes)

    return {
        "ok": True,
        "favoris": donnees["favoris"],
        "updated_at": utilisateur["updated_at"],
    }


@app.get("/api/compte/historique")
def lire_historique_compte(request: Request):

    _email, _comptes, utilisateur = compte_depuis_requete_ou_404(request)
    donnees = synchroniser_meta_securite(utilisateur)

    return {
        "ok": True,
        "historique_economies": donnees.get("historique_economies", []),
    }


@app.delete("/api/compte/historique")
def vider_historique_compte(request: Request):

    _email, comptes, utilisateur = compte_depuis_requete_ou_404(request)
    donnees = synchroniser_meta_securite(utilisateur)
    donnees["historique_economies"] = []
    utilisateur["updated_at"] = date_iso_maintenant()
    enregistrer_comptes_utilisateurs(comptes)

    return {
        "ok": True,
        "historique_economies": [],
        "updated_at": utilisateur["updated_at"],
    }


@app.get("/api/compte/premium")
def lire_premium_compte(request: Request):

    _email, _comptes, utilisateur = compte_depuis_requete_ou_404(request)
    donnees = synchroniser_meta_securite(utilisateur)
    donnees["premium"] = premium_compte_nettoye(donnees)

    return {
        "ok": True,
        "premium": donnees["premium"],
        "plan": donnees.get("plan", "free"),
    }


@app.get("/api/compte/alertes-prix")
def lire_alertes_prix_compte(request: Request):

    _email, _comptes, utilisateur = compte_depuis_requete_ou_404(request)
    donnees = synchroniser_meta_securite(utilisateur)

    return {
        "ok": True,
        "alertes_prix": alertes_prix_nettoyees(
            donnees.get("alertes_prix", [])
        ),
    }


@app.put("/api/compte/alertes-prix")
def remplacer_alertes_prix_compte(
    payload: ListeAlertesPrixCompte,
    request: Request,
):

    _email, comptes, utilisateur = compte_depuis_requete_ou_404(request)
    donnees = synchroniser_meta_securite(utilisateur)
    donnees["alertes_prix"] = alertes_prix_nettoyees(payload.alertes_prix)
    utilisateur["updated_at"] = date_iso_maintenant()
    enregistrer_comptes_utilisateurs(comptes)

    return {
        "ok": True,
        "alertes_prix": donnees["alertes_prix"],
        "updated_at": utilisateur["updated_at"],
    }


@app.get("/api/compte/statistiques")
def lire_statistiques_compte(request: Request):

    _email, _comptes, utilisateur = compte_depuis_requete_ou_404(request)
    donnees = synchroniser_meta_securite(utilisateur)
    statistiques = statistiques_compte(
        donnees.get("historique_economies", [])
    )

    return {
        "ok": True,
        "statistiques": statistiques,
    }


@app.put("/api/compte/optimisation")
def remplacer_optimisation_compte(
    optimisation: OptimisationCompte,
    request: Request,
):

    _email, comptes, utilisateur = compte_depuis_requete_ou_404(request)
    donnees = synchroniser_meta_securite(utilisateur)
    donnees["optimisation"] = optimisation_compte_nettoyee(
        optimisation.model_dump()
    )
    utilisateur["updated_at"] = date_iso_maintenant()
    enregistrer_comptes_utilisateurs(comptes)

    return {
        "ok": True,
        "optimisation": donnees["optimisation"],
        "updated_at": utilisateur["updated_at"],
    }


@app.get("/api/compte/securite")
def lire_securite_compte(request: Request):

    email, _comptes, utilisateur = compte_depuis_requete_ou_404(request)
    donnees = synchroniser_meta_securite(utilisateur)

    return {
        "ok": True,
        "email": email,
        "email_verified": bool(utilisateur.get("email_verified", True)),
        "securite": donnees.get("securite", {}),
    }


@app.post("/api/compte/mot-de-passe")
def changer_mot_de_passe_compte(
    changement: ChangementMotDePasseCompte,
    request: Request,
):

    _email, comptes, utilisateur = compte_depuis_requete_ou_404(request)

    if not verifier_mot_de_passe(
        changement.ancien_mot_de_passe,
        utilisateur.get("password", {}),
    ):
        raise HTTPException(
            status_code=401,
            detail="Mot de passe actuel incorrect.",
        )

    maintenant = date_iso_maintenant()
    utilisateur["password"] = hasher_mot_de_passe(
        changement.nouveau_mot_de_passe
    )
    utilisateur["updated_at"] = maintenant
    donnees = synchroniser_meta_securite(utilisateur)
    donnees["securite"]["dernier_changement_mot_de_passe"] = maintenant
    enregistrer_comptes_utilisateurs(comptes)

    return {
        "ok": True,
        "updated_at": maintenant,
    }


@app.post("/api/compte/mot-de-passe/oublie")
def demander_recuperation_mot_de_passe(
    demande: DemandeRecuperationMotDePasse,
    request: Request,
):

    email = normaliser_email(demande.email)
    comptes = charger_comptes_utilisateurs()
    utilisateur = comptes.get("users", {}).get(email)

    if utilisateur and utilisateur.get("email_verified", True):
        jeton, empreinte, expiration = creer_jeton_recuperation_mot_de_passe()
        utilisateur["password_reset_hash"] = empreinte
        utilisateur["password_reset_expires_at"] = expiration
        utilisateur["updated_at"] = date_iso_maintenant()
        enregistrer_comptes_utilisateurs(comptes)
        base_url = url_base_application(request)
        lien = f"{base_url}/web?reset_token={jeton}"

        try:
            envoyer_email_recuperation_mot_de_passe(email, lien, base_url)
        except Exception as erreur:
            logger.exception(
                "Impossible d’envoyer l’e-mail de récupération : %s",
                erreur,
            )
            raise HTTPException(
                status_code=503,
                detail="L’e-mail de récupération n’a pas pu être envoyé.",
            ) from erreur

    return {
        "ok": True,
        "message": (
            "Si un compte valide existe avec cette adresse, un lien de "
            "récupération vient d’être envoyé."
        ),
    }


@app.post("/api/compte/mot-de-passe/reinitialisation")
def reinitialiser_mot_de_passe(
    reinitialisation: ReinitialisationMotDePasse,
):

    empreinte = hashlib.sha256(
        reinitialisation.token.encode("utf-8")
    ).hexdigest()
    comptes = charger_comptes_utilisateurs()

    for _email, utilisateur in comptes.get("users", {}).items():
        if not hmac.compare_digest(
            str(utilisateur.get("password_reset_hash") or ""),
            empreinte,
        ):
            continue

        if time.time() > float(
            utilisateur.get("password_reset_expires_at", 0)
        ):
            raise HTTPException(
                status_code=410,
                detail="Le lien de récupération a expiré.",
            )

        maintenant = date_iso_maintenant()
        utilisateur["password"] = hasher_mot_de_passe(
            reinitialisation.nouveau_mot_de_passe
        )
        utilisateur.pop("password_reset_hash", None)
        utilisateur.pop("password_reset_expires_at", None)
        utilisateur["updated_at"] = maintenant
        donnees = synchroniser_meta_securite(utilisateur)
        donnees["securite"]["dernier_changement_mot_de_passe"] = maintenant
        enregistrer_comptes_utilisateurs(comptes)

        return {"ok": True}

    raise HTTPException(
        status_code=400,
        detail="Lien de récupération invalide.",
    )


@app.post("/api/compte/renvoyer-validation-email")
def renvoyer_validation_email_compte(
    demande: RenvoiValidationEmailCompte,
    request: Request,
):

    email = normaliser_email(demande.email)
    comptes = charger_comptes_utilisateurs()
    utilisateur = comptes.get("users", {}).get(email)

    if not utilisateur:
        return {"ok": True}

    if utilisateur.get("email_verified", True):
        return {"ok": True, "email_verified": True}

    jeton_validation, empreinte_validation, expiration_validation = (
        creer_jeton_validation_email()
    )
    utilisateur["email_verification_hash"] = empreinte_validation
    utilisateur["email_verification_expires_at"] = expiration_validation
    utilisateur["updated_at"] = date_iso_maintenant()
    enregistrer_comptes_utilisateurs(comptes)

    base_url = url_base_application(request)
    lien_validation = (
        f"{base_url}/api/compte/validation-email"
        f"?token={jeton_validation}"
    )
    envoyer_email_validation_compte(email, lien_validation, base_url)

    return {
        "ok": True,
        "verification_required": True,
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
    latitude: Optional[str] = None,
    longitude: Optional[str] = None,
    carburant: str = "gazole",
    rayon: int = 25
):

    try:
        latitude = float(latitude) if str(latitude or "").strip() else None
    except (TypeError, ValueError):
        latitude = None

    try:
        longitude = float(longitude) if str(longitude or "").strip() else None
    except (TypeError, ValueError):
        longitude = None

    carburant = (carburant or "gazole").lower()
    if carburant not in {
        "gazole",
        "sp95",
        "sp98",
        "e10",
        "e85",
        "gplc",
        "electrique",
    }:
        carburant = "gazole"

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

    if carburant == "electrique":
        stations = []
    elif (latitude is None or longitude is None) and not ville:
        # Sans position, ne pas afficher le minimum national comme s'il
        # se trouvait autour de l'utilisateur. Le navigateur actualisera
        # ce resume des que le GPS aura fourni des coordonnees.
        stations = []
    else:
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


@app.get("/robots.txt")
def robots_txt(request: Request):

    base_url = url_base_application(request)

    return PlainTextResponse(
        "User-agent: *\n"
        "Allow: /\n"
        f"Sitemap: {base_url}/sitemap.xml\n",
        media_type="text/plain",
    )


@app.get("/sitemap.xml")
def sitemap_xml(request: Request):

    base_url = url_base_application(request)
    chemins = []

    for identifiant in PAGES_EDITORIALES:
        chemin = chemin_page_editoriale(identifiant)
        if chemin not in chemins:
            chemins.append(chemin)

    chemins.extend(
        [
            "/landing",
            "/web",
            "/suppression-compte",
        ]
    )

    date_jour = datetime.now().date().isoformat()
    entrees = "\n".join(
        "    <url>\n"
        f"        <loc>{base_url}{chemin}</loc>\n"
        f"        <lastmod>{date_jour}</lastmod>\n"
        "        <changefreq>weekly</changefreq>\n"
        "    </url>"
        for chemin in chemins
    )

    return Response(
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n"
        f"{entrees}\n"
        "</urlset>\n",
        media_type="application/xml",
    )
