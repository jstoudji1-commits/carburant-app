from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

from typing import Optional

import csv
import math
import requests
import time

app = FastAPI()

templates = Jinja2Templates(
    directory="templates"
)


def charger_stations():

    url = (
        "https://data.economie.gouv.fr/"
        "api/explore/v2.1/catalog/datasets/"
        "prix-des-carburants-en-france-flux-instantane-v2/"
        "records?limit=10000"
    )

    response = requests.get(
        url,
        timeout=30
    )

    data = response.json()

    stations = []

    for station in data["results"]:

        stations.append({

            "id":
                station.get("id", ""),

            "cp":
                station.get("code_postal", ""),

            "ville":
                station.get("ville", ""),

            "adresse":
                station.get("adresse", ""),

            "latitude":
                station.get("latitude", ""),

            "longitude":
                station.get("longitude", ""),

            "gazole":
                station.get(
                    "prix_gazole",
                    ""
                ),

            "e10":
                station.get(
                    "prix_e10",
                    ""
                ),

            "sp98":
                station.get(
                    "prix_sp98",
                    ""
                )

        })

    print(
        "Stations chargées :",
        len(stations)
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


@app.get("/web")
def page_web(
    request: Request,
    ville: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    carburant: str = "gazole",
    rayon: int = 10
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

        stations = stations[:10]

    else:

        for station in stations:

            station[
                "carburant_selectionne"
            ] = station.get(
                carburant,
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

    ]

    prix_min = (

        min(prix_valides)

        if prix_valides

        else 0

    )

    return templates.TemplateResponse(

        request=request,

        name="index.html",

        context={

            "stations": stations,

            "nombre_stations": nombre_stations,

            "prix_min": prix_min,

            "carburant": carburant,

            "rayon": rayon

        }

    )    