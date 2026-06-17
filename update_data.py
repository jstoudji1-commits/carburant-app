import csv
import io
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET
from urllib.request import urlopen


BASE_DIR = Path(__file__).resolve().parent
STATIONS_CSV = BASE_DIR / "stations.csv"
METADATA_JSON = BASE_DIR / "stations_metadata.json"

SOURCE_OFFICIELLE_URL = (
    "https://www.data.gouv.fr/api/1/datasets/r/"
    "edd67f5b-46d0-4663-9de9-e5db1c880160"
)

ENTETES = [
    "id",
    "cp",
    "ville",
    "adresse",
    "latitude",
    "longitude",
    "gazole",
    "e10",
    "sp98",
]


def _prix(valeur):

    return (valeur or "").replace(",", ".").strip()


def _coordonnees(valeur):

    try:

        return round(
            float(valeur) / 100000,
            6
        )

    except (TypeError, ValueError):

        return ""


def _lignes_depuis_xml(contenu):

    root = ET.fromstring(contenu)

    for station in root:

        donnees = {
            "id": station.attrib.get("id", ""),
            "cp": station.attrib.get("cp", ""),
            "ville": "",
            "adresse": "",
            "latitude": _coordonnees(
                station.attrib.get("latitude")
            ),
            "longitude": _coordonnees(
                station.attrib.get("longitude")
            ),
            "gazole": "",
            "e10": "",
            "sp98": "",
        }

        for enfant in station:

            if enfant.tag == "ville":

                donnees["ville"] = enfant.text or ""

            elif enfant.tag == "adresse":

                donnees["adresse"] = enfant.text or ""

            elif enfant.tag == "prix":

                nom = enfant.attrib.get("nom", "")
                valeur = _prix(
                    enfant.attrib.get("valeur", "")
                )

                if nom == "Gazole":

                    donnees["gazole"] = valeur

                elif nom == "E10":

                    donnees["e10"] = valeur

                elif nom == "SP98":

                    donnees["sp98"] = valeur

        yield donnees


def _lignes_depuis_csv(contenu):

    texte = contenu.decode(
        "utf-8-sig"
    )

    lecteur = csv.DictReader(
        texte.splitlines(),
        delimiter=";"
    )

    for station in lecteur:

        yield {
            "id": station.get("id", ""),
            "cp": (
                station.get("Code postal")
                or station.get("cp")
                or ""
            ),
            "ville": (
                station.get("Ville")
                or station.get("ville")
                or ""
            ),
            "adresse": (
                station.get("Adresse")
                or station.get("adresse")
                or ""
            ),
            "latitude": _coordonnees(
                station.get("latitude")
            ),
            "longitude": _coordonnees(
                station.get("longitude")
            ),
            "gazole": _prix(
                station.get("Prix Gazole")
                or station.get("gazole")
                or ""
            ),
            "e10": _prix(
                station.get("Prix E10")
                or station.get("e10")
                or ""
            ),
            "sp98": _prix(
                station.get("Prix SP98")
                or station.get("sp98")
                or ""
            ),
        }


def _extraire_lignes(contenu):

    archive_candidate = io.BytesIO(contenu)

    if zipfile.is_zipfile(archive_candidate):

        archive_candidate.seek(0)

        with zipfile.ZipFile(archive_candidate) as archive:

            nom_xml = next(
                nom
                for nom in archive.namelist()
                if nom.lower().endswith(".xml")
            )

            return list(
                _lignes_depuis_xml(
                    archive.read(nom_xml)
                )
            )

    if contenu.lstrip().startswith(b"<"):

        return list(
            _lignes_depuis_xml(contenu)
        )

    return list(
        _lignes_depuis_csv(contenu)
    )


def telecharger_donnees_officielles():

    with urlopen(
        SOURCE_OFFICIELLE_URL,
        timeout=90
    ) as response:

        return response.read()


def ecrire_stations_csv(lignes):

    fichier_temporaire = STATIONS_CSV.with_suffix(
        ".csv.tmp"
    )

    with fichier_temporaire.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as fichier:

        writer = csv.DictWriter(
            fichier,
            fieldnames=ENTETES
        )
        writer.writeheader()
        writer.writerows(lignes)

    os.replace(
        fichier_temporaire,
        STATIONS_CSV
    )


def ecrire_metadata(nombre_stations):

    metadata = {
        "source": SOURCE_OFFICIELLE_URL,
        "stations": nombre_stations,
        "updated_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }

    METADATA_JSON.write_text(
        json.dumps(
            metadata,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


def mettre_a_jour_stations():

    contenu = telecharger_donnees_officielles()
    lignes = _extraire_lignes(contenu)

    if not lignes:

        raise RuntimeError(
            "Aucune station trouvee dans les donnees officielles."
        )

    ecrire_stations_csv(lignes)
    ecrire_metadata(len(lignes))

    print(
        f"stations.csv mis a jour avec {len(lignes)} stations"
    )


def date_derniere_mise_a_jour():

    if METADATA_JSON.exists():

        try:

            metadata = json.loads(
                METADATA_JSON.read_text(
                    encoding="utf-8"
                )
            )
            date_texte = metadata.get(
                "updated_at"
            )

            if date_texte:

                return datetime.fromisoformat(
                    date_texte
                )

        except (OSError, ValueError, TypeError):

            pass

    if not STATIONS_CSV.exists():

        return None

    return datetime.fromtimestamp(
        STATIONS_CSV.stat().st_mtime,
        timezone.utc
    )


def minutes_depuis_derniere_mise_a_jour():

    derniere_modification = date_derniere_mise_a_jour()

    if derniere_modification is None:

        return None

    age = (
        datetime.now(timezone.utc)
        - derniere_modification
    )

    return max(
        0,
        int(age.total_seconds() // 60)
    )


def texte_derniere_mise_a_jour():

    minutes = minutes_depuis_derniere_mise_a_jour()

    if minutes is None:

        return "vérification en attente"

    if minutes < 1:

        return "vérifié il y a moins d'une minute"

    if minutes == 1:

        return "vérifié il y a 1 minute"

    return f"vérifié il y a {minutes} minutes"


def mise_a_jour_necessaire(max_age_minutes=10):

    minutes = minutes_depuis_derniere_mise_a_jour()

    if minutes is None:

        return True

    return minutes >= max_age_minutes


def mettre_a_jour_si_necessaire(max_age_minutes=10):

    if not mise_a_jour_necessaire(max_age_minutes):

        return

    try:

        mettre_a_jour_stations()

    except Exception as erreur:

        print(
            "Mise a jour des stations impossible :",
            erreur
        )


if __name__ == "__main__":
    mettre_a_jour_stations()


