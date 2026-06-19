from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

from typing import Optional
from fastapi.staticfiles import StaticFiles


import asyncio
import csv
from contextlib import asynccontextmanager, suppress
import logging
import math
from update_data import (
    date_derniere_mise_a_jour,
    mettre_a_jour_stations,
    texte_derniere_mise_a_jour,
)


INTERVALLE_MISE_A_JOUR_SECONDES = 10 * 60
logger = logging.getLogger("optiplein.update")


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

    prix_valides = [

        float(
            station.get(
                carburant,
                ""
            )
        )

        for station in stations

        if station.get(
            carburant,
            ""
        ).strip()
        and float(station.get(carburant, "")) not in (0, 9.999)

    ]

    prix_min = (

        min(prix_valides)

        if prix_valides

        else None

    )

    return templates.TemplateResponse(

        request=request,

        name="index.html",

        context={

            "stations": stations,

            "nombre_stations": nombre_stations,

            "prix_min": prix_min,

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



