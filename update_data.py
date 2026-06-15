import zipfile
import xml.etree.ElementTree as ET
import csv


def update_stations():

    with zipfile.ZipFile("instantane_ruptures.zip") as archive:

        fichier_xml = archive.namelist()[0]

        contenu = archive.read(fichier_xml)

    root = ET.fromstring(contenu)

    with open(
        "stations.csv",
        "w",
        newline="",
        encoding="utf-8"
    ) as fichier_csv:

        writer = csv.writer(fichier_csv)

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

        for station in root:

            ville = ""
            adresse = ""

            gazole = ""
            e10 = ""
            sp98 = ""

            try:

                latitude_gps = (
                    float(
                        station.attrib.get(
                            "latitude",
                            0
                        )
                    )
                    / 100000
                )

                longitude_gps = (
                    float(
                        station.attrib.get(
                            "longitude",
                            0
                        )
                    )
                    / 100000
                )

            except:

                latitude_gps = ""
                longitude_gps = ""

            for enfant in station:

                if enfant.tag == "ville":
                    ville = enfant.text or ""

                elif enfant.tag == "adresse":
                    adresse = enfant.text or ""

                elif enfant.tag == "prix":

                    nom = enfant.attrib.get(
                        "nom",
                        ""
                    )

                    valeur = enfant.attrib.get(
                        "valeur",
                        ""
                    )

                    if nom == "Gazole":
                        gazole = valeur

                    elif nom == "E10":
                        e10 = valeur

                    elif nom == "SP98":
                        sp98 = valeur

            writer.writerow([
                station.attrib.get("id", ""),
                station.attrib.get("cp", ""),
                ville,
                adresse,
                round(latitude_gps, 6)
                if latitude_gps != ""
                else "",
                round(longitude_gps, 6)
                if longitude_gps != ""
                else "",
                gazole,
                e10,
                sp98
            ])

    print("stations.csv mis à jour")


if __name__ == "__main__":
    update_stations()