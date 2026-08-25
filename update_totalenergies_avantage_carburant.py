#!/usr/bin/env python3
"""Génère la liste OptiPlein des stations Avantage Carburant TotalEnergies.

La liste officielle est dynamique et publiée dans le localisateur TotalEnergies.
Ce script récupère les stations portant le code ``OpeAvantageCarburant`` puis
les rapproche du référentiel gouvernemental déjà utilisé par OptiPlein.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import tempfile
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WOOSMAP_URL = "https://api.woosmap.com/stores/search/"
# Clé publique du localisateur web TotalEnergies, pas une clé serveur secrète.
DEFAULT_PUBLIC_KEY = "woos-c236c6f3-31fe-3118-82e7-a19ca42466f7"
OFFICIAL_TAG = "OpeAvantageCarburant"
LOCATOR_ORIGIN = "https://locator.totalenergies.com"
MAX_MATCH_DISTANCE_METERS = 500


def normaliser(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(char for char in text if not unicodedata.combining(char)).casefold().strip()


def distance_metres(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    rayon = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * rayon * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def recuperer_stations_officielles(api_key: str) -> list[dict]:
    headers = {"Referer": f"{LOCATOR_ORIGIN}/", "Origin": LOCATOR_ORIGIN}
    stations: list[dict] = []
    page = 1
    while True:
        params = urllib.parse.urlencode(
            {
                "key": api_key,
                "query": f'tag:"{OFFICIAL_TAG}"',
                "stores_by_page": 300,
                "page": page,
            }
        )
        request = urllib.request.Request(f"{WOOSMAP_URL}?{params}", headers=headers)
        with urllib.request.urlopen(request, timeout=45) as response:
            payload = json.load(response)
        stations.extend(payload.get("features") or [])
        page_count = int((payload.get("pagination") or {}).get("pageCount") or 1)
        if page >= page_count:
            break
        page += 1
    if len(stations) < 100:
        raise RuntimeError(
            f"Réponse officielle anormalement faible ({len(stations)} stations) : fichier non remplacé."
        )
    return stations


def charger_stations_gouvernementales(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    stations = []
    for row in rows:
        try:
            row["_latitude"] = float(row["latitude"])
            row["_longitude"] = float(row["longitude"])
        except (TypeError, ValueError, KeyError):
            continue
        row["_cp"] = str(row.get("cp") or "").zfill(5)
        row["_ville"] = normaliser(row.get("ville"))
        row["_adresse"] = normaliser(row.get("adresse"))
        stations.append(row)
    return stations


def rapprocher(feature: dict, stations_gouv: list[dict]) -> tuple[dict | None, float | None, str]:
    properties = feature.get("properties") or {}
    address = properties.get("address") or {}
    coordinates = (feature.get("geometry") or {}).get("coordinates") or []
    if len(coordinates) < 2:
        return None, None, "coordonnees_officielles_absentes"
    lon, lat = float(coordinates[0]), float(coordinates[1])
    cp = str(address.get("zipcode") or "").zfill(5)
    ville = normaliser(address.get("city"))

    # Le code postal réduit les homonymes ; un repli départemental couvre les
    # stations placées juste de l'autre côté d'une limite postale.
    candidates = [s for s in stations_gouv if s["_cp"] == cp]
    if not candidates and len(cp) >= 2:
        candidates = [s for s in stations_gouv if s["_cp"].startswith(cp[:2])]
    if not candidates:
        candidates = stations_gouv

    scored = []
    for station in candidates:
        distance = distance_metres(lat, lon, station["_latitude"], station["_longitude"])
        bonus_ville = 20 if ville and ville == station["_ville"] else 0
        scored.append((distance - bonus_ville, distance, station))
    if not scored:
        return None, None, "aucun_candidat"
    _, distance, station = min(scored, key=lambda item: item[0])
    if distance > MAX_MATCH_DISTANCE_METERS:
        return None, round(distance, 1), "distance_superieure_a_500_m"
    return station, round(distance, 1), "coordonnees_et_code_postal"


def construire_document(features: list[dict], stations_gouv: list[dict]) -> dict:
    stations: dict[str, dict] = {}
    non_rapprochees: list[dict] = []
    conflits: list[dict] = []
    for feature in features:
        properties = feature.get("properties") or {}
        user = properties.get("user_properties") or {}
        address = properties.get("address") or {}
        coordinates = (feature.get("geometry") or {}).get("coordinates") or [None, None]
        locator_id = str(user.get("location_id") or "").strip()
        common = {
            "locator_id": locator_id,
            "nom": properties.get("name"),
            "marque": user.get("brand"),
            "adresse": ", ".join(address.get("lines") or []),
            "code_postal": address.get("zipcode"),
            "ville": address.get("city"),
            "latitude": coordinates[1],
            "longitude": coordinates[0],
            "mise_a_jour_source": properties.get("last_updated"),
            "source_url": f"{LOCATOR_ORIGIN}/{locator_id}?business_type=RETAIL&type=FUELING",
            "code_offre": OFFICIAL_TAG,
        }
        station, distance, methode = rapprocher(feature, stations_gouv)
        if station is None:
            common.update({"distance_candidat_m": distance, "motif": methode})
            non_rapprochees.append(common)
            continue
        station_id = str(station.get("id") or "").strip()
        entry = {
            **common,
            "distance_rapprochement_m": distance,
            "methode_rapprochement": methode,
        }
        if station_id in stations:
            precedent = stations[station_id]
            if entry["distance_rapprochement_m"] < precedent["distance_rapprochement_m"]:
                conflits.append({"id_gouvernemental": station_id, "station_ecartee": precedent})
                stations[station_id] = entry
            else:
                conflits.append({"id_gouvernemental": station_id, "station_ecartee": entry})
        else:
            stations[station_id] = entry

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return {
        "schema_version": 2,
        "offer_name": "Avantage Carburant",
        "price_cap_eur_per_litre": 1.99,
        "valid_until": "2026-12-31",
        "official_filter_code": OFFICIAL_TAG,
        "source_url": "https://services.totalenergies.fr/stations",
        "source_locator_url": LOCATOR_ORIGIN,
        "generated_at": now,
        "methodology": (
            "Filtre officiel du localisateur TotalEnergies, puis rapprochement avec stations.csv "
            "par code postal et distance géographique (500 m maximum)."
        ),
        "counts": {
            "official_participants": len(features),
            "matched_government_stations": len(stations),
            "unmatched_official_stations": len(non_rapprochees),
            "conflicts": len(conflits),
        },
        "stations": dict(sorted(stations.items())),
        "unmatched": non_rapprochees,
        "conflicts": conflits,
    }


def ecrire_atomiquement(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        json.dump(document, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        temp_path = Path(stream.name)
    temp_path.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stations", type=Path, default=ROOT / "stations.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "totalenergies_avantage_carburant.json")
    args = parser.parse_args()
    api_key = os.getenv("TOTALENERGIES_WOOSMAP_KEY", DEFAULT_PUBLIC_KEY)
    features = recuperer_stations_officielles(api_key)
    document = construire_document(features, charger_stations_gouvernementales(args.stations))
    ecrire_atomiquement(args.output, document)
    print(json.dumps(document["counts"], ensure_ascii=False))


if __name__ == "__main__":
    main()
