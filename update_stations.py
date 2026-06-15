import csv
import requests
from pyproj import Transformer

URL = (
    "https://www.data.gouv.fr/api/1/datasets/r/"
    "edd67f5b-46d0-4663-9de9-e5db1c880160"
)

transformer = Transformer.from_crs(
    "EPSG:2154",
    "EPSG:4326",
    always_xy=True
)


def update_stations():

    print("Téléchargement du flux...")

    response = requests.get(
        URL,
        timeout=60
    )

    response.raise_for_status()

    lignes = response.text.splitlines()

    if lignes:
        lignes[0] = lignes[0].replace(
            "\ufeff",
            ""
        )

    lecteur = csv.DictReader(
        lignes,
        delimiter=";"
    )

    with open(
        "stations.csv",
        "w",
        newline="",
        encoding="utf-8"
    ) as fichier:

        writer = csv.writer(fichier)

        writer.writerow([
            "id",
            "cp",
            "ville",
            "adresse",
            "latitude",
            "longitude",
            "gazole",
            "e10",
            "sp98"
        ])

        for station in lecteur:

            try:

                latitude_gps = (
                    float(station["latitude"])
                    / 100000
                )

                longitude_gps = (
                     float(station["longitude"])
                     / 100000
                )

            except:

                latitude_gps = ""
                longitude_gps = ""

            writer.writerow([
                station.get("id", ""),
                station.get("Code postal", ""),
                station.get("Ville", ""),
                station.get("Adresse", ""),
                round(latitude_gps, 6)
                    if latitude_gps != ""
                    else "",
                round(longitude_gps, 6)
                    if longitude_gps != ""
                    else "",
                station.get("Prix Gazole", ""),
                station.get("Prix E10", ""),
                station.get("Prix SP98", "")
            ])

    print("stations.csv mis à jour")


if __name__ == "__main__":
    update_stations()