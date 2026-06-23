import csv
import io
import json
import math
import time
import unicodedata
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from verify_station_coordinates import normaliser_enseigne


BASE_DIR = Path(__file__).resolve().parent
SOURCE_CSV = BASE_DIR / "stations_sans_enseigne_a_completer.csv"
SORTIE_CSV = BASE_DIR / "stations_sans_enseigne_a_completer_complete.csv"
RAPPORT_JSON = BASE_DIR / "stations_sans_enseigne_a_completer_rapport.json"
BANCO_URL = "https://geodatamine.fr/dump/shop_craft_office_csv.zip"
RAYON_CORRESPONDANCE_METRES = 160


def texte_recherche(texte):
    texte = unicodedata.normalize("NFKD", str(texte or ""))
    texte = "".join(
        caractere
        for caractere in texte
        if not unicodedata.combining(caractere)
    )
    texte = texte.casefold()
    texte = "".join(
        caractere if caractere.isalnum() else " "
        for caractere in texte
    )
    return " ".join(texte.split())


def nombre(valeur):
    try:
        return float(str(valeur or "").replace(",", "."))
    except ValueError:
        return None


def distance_metres(lat1, lon1, lat2, lon2):
    rayon = 6371000
    conversion = math.pi / 180
    dlat = (lat2 - lat1) * conversion
    dlon = (lon2 - lon1) * conversion
    lat1 *= conversion
    lat2 *= conversion
    valeur = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    return rayon * 2 * math.atan2(math.sqrt(valeur), math.sqrt(1 - valeur))


def lire_stations_a_completer():
    with SOURCE_CSV.open("r", encoding="utf-8-sig", newline="") as fichier:
        reader = csv.DictReader(fichier, delimiter=";")
        return list(reader), reader.fieldnames or []


def telecharger_banco():
    derniere_erreur = None
    for tentative in range(3):
        try:
            requete = Request(
                BANCO_URL,
                headers={"User-Agent": "OptiPlein/1.0 enrichissement-enseignes"},
            )
            with urlopen(requete, timeout=240) as reponse:
                return reponse.read()
        except OSError as erreur:
            derniere_erreur = erreur
            time.sleep(4 * (tentative + 1))
    raise RuntimeError("Impossible de telecharger BANCO") from derniere_erreur


def enseigne_banco(row):
    for champ in ("brand", "operator", "name"):
        enseigne = normaliser_enseigne(row.get(champ, ""))
        if enseigne:
            return enseigne
    return ""


def extraire_stations_banco(contenu_zip):
    stations = []
    with zipfile.ZipFile(io.BytesIO(contenu_zip)) as archive:
        with archive.open("data.csv") as fichier:
            texte = io.TextIOWrapper(fichier, encoding="utf-8-sig", newline="")
            reader = csv.DictReader(texte, delimiter=";")
            for row in reader:
                if row.get("type") != "fuel":
                    continue
                latitude = nombre(row.get("Y"))
                longitude = nombre(row.get("X"))
                if latitude is None or longitude is None:
                    continue
                enseigne = enseigne_banco(row)
                if not enseigne:
                    continue
                stations.append(
                    {
                        "latitude": latitude,
                        "longitude": longitude,
                        "enseigne": enseigne,
                        "adresse": row.get("address", ""),
                        "ville": row.get("com_nom", ""),
                        "osm_id": row.get("osm_id", ""),
                        "profession_ref": row.get("profession_ref", ""),
                    }
                )
    return stations


def cle_grille(latitude, longitude):
    return (math.floor(latitude * 100), math.floor(longitude * 100))


def indexer_banco(stations):
    index = {}
    par_reference = {}
    for station in stations:
        index.setdefault(
            cle_grille(station["latitude"], station["longitude"]),
            [],
        ).append(station)
        reference = str(station.get("profession_ref", "")).strip()
        if reference:
            par_reference[reference] = station
    return index, par_reference


def candidates_proches(index, latitude, longitude):
    cle_lat, cle_lon = cle_grille(latitude, longitude)
    candidates = []
    for dlat in range(-1, 2):
        for dlon in range(-1, 2):
            candidates.extend(index.get((cle_lat + dlat, cle_lon + dlon), []))
    return candidates


def choisir_banco(station, index, par_reference):
    station_id = str(station.get("id", "")).strip()
    if station_id in par_reference:
        return par_reference[station_id], 0, "reference_prix_carburants"

    latitude = nombre(station.get("latitude"))
    longitude = nombre(station.get("longitude"))
    if latitude is None or longitude is None:
        return None, None, ""

    ville_station = texte_recherche(station.get("ville", ""))
    meilleurs = []
    for candidate in candidates_proches(index, latitude, longitude):
        distance = distance_metres(
            latitude,
            longitude,
            candidate["latitude"],
            candidate["longitude"],
        )
        if distance > RAYON_CORRESPONDANCE_METRES:
            continue
        score = 1000 - distance
        if ville_station and ville_station == texte_recherche(candidate.get("ville", "")):
            score += 120
        if texte_recherche(station.get("adresse", "")) and texte_recherche(
            candidate.get("adresse", "")
        ):
            score += 40
        meilleurs.append((score, distance, candidate))

    if not meilleurs:
        return None, None, ""

    meilleurs.sort(key=lambda item: (-item[0], item[1]))
    meilleur_score, meilleure_distance, meilleure_station = meilleurs[0]
    deuxieme_score = meilleurs[1][0] if len(meilleurs) > 1 else -9999
    if len(meilleurs) > 1 and meilleur_score - deuxieme_score < 80:
        return None, round(meilleure_distance), "correspondance_ambigue"

    return meilleure_station, round(meilleure_distance), "proximite_gps"


def main():
    lignes, champs = lire_stations_a_completer()
    banco = extraire_stations_banco(telecharger_banco())
    index, par_reference = indexer_banco(banco)
    completees = 0
    ambigues = 0

    for ligne in lignes:
        station_banco, distance, source = choisir_banco(ligne, index, par_reference)
        if station_banco:
            ligne["enseigne_corrigee"] = station_banco["enseigne"]
            ligne["decision"] = "complete_auto_banco"
            ligne["commentaire"] = (
                f"{source}; osm={station_banco.get('osm_id', '')}; "
                f"distance={distance}m"
            )
            completees += 1
        elif source == "correspondance_ambigue":
            ligne["decision"] = "a_verifier_manuellement"
            ligne["commentaire"] = f"correspondance BANCO ambigue; distance={distance}m"
            ambigues += 1

    with SORTIE_CSV.open("w", encoding="utf-8-sig", newline="") as fichier:
        writer = csv.DictWriter(fichier, fieldnames=champs, delimiter=";")
        writer.writeheader()
        writer.writerows(lignes)

    rapport = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": BANCO_URL,
        "stations_a_completer": len(lignes),
        "stations_completees": completees,
        "stations_ambigues": ambigues,
        "stations_restantes": len(lignes) - completees,
        "fichier": SORTIE_CSV.name,
    }
    RAPPORT_JSON.write_text(
        json.dumps(rapport, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(rapport, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
