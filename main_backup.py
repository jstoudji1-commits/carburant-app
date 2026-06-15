from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
import csv

from typing import Optional

app = FastAPI()
templates = Jinja2Templates(directory="templates")

def charger_stations():
    stations = []

    with open("stations.csv", encoding="utf-8") as fichier:
        lecteur = csv.DictReader(fichier)

        for ligne in lecteur:
            stations.append(ligne)

    return stations

@app.get("/")
def home():
    return {"application": "Comparateur Carburant"}

@app.get("/stations")
def get_stations():
    stations = charger_stations()

    stations.sort(
    key=lambda x: float(x["gazole"])
    if x["gazole"]
    else 999
)

    return stations

@app.get("/stations/{ville}")
def stations_par_ville(ville: str):
    resultat = []

    for station in charger_stations():
        if station["ville"].lower() == ville.lower():
            resultat.append(station)

    return resultat

@app.get("/web")
def page_web(
    request: Request,
    ville: Optional[str] = None
):

    stations = charger_stations()

    if ville:

        recherche = ville.lower()

        stations = [
            station
            for station in stations
            if (
                recherche in station["ville"].lower()
                or recherche in station["cp"]
            )
        ]

    stations.sort(
        key=lambda x: (
            float(x["gazole"])
            if x["gazole"].strip()
            else 999
        )
    )

    stations = stations[:50]

    nombre_stations = len(stations)

    prix_valides = [
        float(station["gazole"])
        for station in stations
        if station["gazole"].strip()
    ]

    prix_min = min(prix_valides) if prix_valides else 0

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "stations": stations,
            "nombre_stations": nombre_stations,
            "prix_min": prix_min
        }
    )