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
import logging
import math
import os
import re
import smtplib
import ssl
import time
from update_data import (
    date_derniere_mise_a_jour,
    mettre_a_jour_stations,
    texte_derniere_mise_a_jour,
)


INTERVALLE_MISE_A_JOUR_SECONDES = 10 * 60
logger = logging.getLogger("optiplein.update")
EMAIL_SIGNALEMENT = os.getenv(
    "REPORT_EMAIL",
    "j.stoudji1@gmail.com"
)
signalements_recents = {}


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

    tache_mise_a_jour = asyncio.create_task(
        actualiser_prix_periodiquement()
    )

    yield

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


def charger_stations():

    stations = []

    with open(
        "stations.csv",
        encoding="utf-8"
    ) as fichier:

        lecteur = csv.DictReader(
            fichier
        )

        for ligne in lecteur:

            stations.append(
                ligne
            )

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


from fastapi.responses import RedirectResponse

@app.get("/")
def home():

    return RedirectResponse(
        url="/web"
    )


@app.get("/confidentialite")
def confidentialite(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="confidentialite.html",
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
    rayon: int = 15
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

    # Recherche autour de moi

    if latitude and longitude:

        stations_valides = []

        for station in stations:

            try:

                distance = distance_km(

                    latitude,
                    longitude,

                    float(
                        station["latitude"]
                    ),

                    float(
                        station["longitude"]
                    )

                )

                station["distance"] = round(
                    distance,
                    2
                )

                station[
                    "carburant_selectionne"
                ] = station.get(
                    carburant,
                    ""
                )

                station[
                    "tendance_selectionnee"
                ] = station.get(
                    f"tendance_{carburant}",
                    ""
                )

                if distance <= rayon:

                    stations_valides.append(
                        station
                    )

            except:

                pass

        stations = stations_valides

        stations.sort(
            key=lambda x: x["distance"]
        )

    else:

        for station in stations:

            station[
                "carburant_selectionne"
            ] = station.get(
                carburant,
                ""
            )

            station[
                "tendance_selectionnee"
            ] = station.get(
                f"tendance_{carburant}",
                ""
            )

        stations.sort(
            key=lambda x: (

                float(
                    x.get(
                        carburant,
                        ""
                    )
                )

                if x.get(
                    carburant,
                    ""
                ).strip()

                else 999

            )
        )

        stations = stations[:50]

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



