import csv
import io
import json
import math
import time
import unicodedata
import uuid
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from update_data import (
    BASE_DIR,
    ENRICHISSEMENT_STATIONS_JSON,
    STATIONS_CSV,
    ecrire_stations_csv,
    signature_adresse,
)


BAN_CSV_URL = "https://data.geopf.fr/geocodage/search/csv"
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
RAPPORT_COORDONNEES_JSON = BASE_DIR / "stations_coordinates_report.json"
RAYON_NOM_METRES = 150
RAYON_CONFIRMATION_OSM_METRES = 500
ECART_CORRECTION_METRES = 1000


def distance_metres(latitude_1, longitude_1, latitude_2, longitude_2):
    rayon = 6371000
    conversion = math.pi / 180
    delta_latitude = (latitude_2 - latitude_1) * conversion
    delta_longitude = (longitude_2 - longitude_1) * conversion
    latitude_1 *= conversion
    latitude_2 *= conversion
    valeur = (
        math.sin(delta_latitude / 2) ** 2
        + math.cos(latitude_1)
        * math.cos(latitude_2)
        * math.sin(delta_longitude / 2) ** 2
    )
    return rayon * 2 * math.atan2(math.sqrt(valeur), math.sqrt(1 - valeur))


def lire_stations():
    with STATIONS_CSV.open("r", encoding="utf-8-sig", newline="") as fichier:
        return list(csv.DictReader(fichier))


def construire_multipart(donnees_csv):
    limite = "----OptiPlein" + uuid.uuid4().hex
    morceaux = []

    for colonne in ("adresse", "cp", "ville"):
        morceaux.extend(
            [
                f"--{limite}\r\n".encode(),
                b'Content-Disposition: form-data; name="columns"\r\n\r\n',
                colonne.encode("utf-8"),
                b"\r\n",
            ]
        )

    morceaux.extend(
        [
            f"--{limite}\r\n".encode(),
            b'Content-Disposition: form-data; name="data"; filename="stations.csv"\r\n',
            b"Content-Type: text/csv; charset=utf-8\r\n\r\n",
            donnees_csv,
            b"\r\n",
            f"--{limite}--\r\n".encode(),
        ]
    )
    return b"".join(morceaux), limite


def geocoder_adresses(stations):
    sortie = io.StringIO(newline="")
    writer = csv.DictWriter(
        sortie,
        fieldnames=["id", "adresse", "cp", "ville"],
    )
    writer.writeheader()
    for station in stations:
        writer.writerow(
            {
                "id": station.get("id", ""),
                "adresse": station.get("adresse", ""),
                "cp": station.get("cp", ""),
                "ville": station.get("ville", ""),
            }
        )

    corps, limite = construire_multipart(sortie.getvalue().encode("utf-8"))
    requete = Request(
        BAN_CSV_URL,
        data=corps,
        headers={
            "Content-Type": f"multipart/form-data; boundary={limite}",
            "User-Agent": "OptiPlein/1.0 verification-coordonnees",
        },
        method="POST",
    )
    with urlopen(requete, timeout=180) as reponse:
        texte = reponse.read().decode("utf-8-sig")

    return {
        ligne.get("id", ""): ligne
        for ligne in csv.DictReader(io.StringIO(texte))
    }


def telecharger_stations_osm():
    requete_overpass = (
        "[out:json][timeout:240];"
        "nwr[amenity=fuel](41,-5.5,51.5,10);"
        "out center tags;"
    )
    derniere_erreur = None

    for url in OVERPASS_URLS:
        try:
            corps = urlencode({"data": requete_overpass}).encode("utf-8")
            requete = Request(
                url,
                data=corps,
                headers={
                    "User-Agent": "OptiPlein/1.0 verification-coordonnees",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                method="POST",
            )
            with urlopen(requete, timeout=300) as reponse:
                contenu = json.loads(reponse.read().decode("utf-8"))
            return extraire_stations_osm(contenu.get("elements", []))
        except Exception as erreur:
            derniere_erreur = erreur
            time.sleep(3)

    raise RuntimeError("Impossible de charger les stations OpenStreetMap") from derniere_erreur


def extraire_stations_osm(elements):
    stations = []
    for element in elements:
        centre = element.get("center", {})
        latitude = element.get("lat", centre.get("lat"))
        longitude = element.get("lon", centre.get("lon"))
        if latitude is None or longitude is None:
            continue

        tags = element.get("tags", {})
        enseigne = (
            tags.get("brand")
            or tags.get("name")
            or tags.get("operator")
            or ""
        ).strip()
        stations.append(
            {
                "latitude": float(latitude),
                "longitude": float(longitude),
                "enseigne": enseigne,
                "osm_id": f"{element.get('type', '')}/{element.get('id', '')}",
            }
        )
    return stations


def cle_grille(latitude, longitude):
    return (math.floor(latitude * 100), math.floor(longitude * 100))


def indexer_stations_osm(stations_osm):
    index = {}
    for station in stations_osm:
        index.setdefault(
            cle_grille(station["latitude"], station["longitude"]),
            [],
        ).append(station)
    return index


def stations_osm_proches(index_osm, latitude, longitude, rayon_metres):
    cle_latitude, cle_longitude = cle_grille(latitude, longitude)
    candidates = []
    for delta_latitude in range(-2, 3):
        for delta_longitude in range(-2, 3):
            candidates.extend(
                index_osm.get(
                    (cle_latitude + delta_latitude, cle_longitude + delta_longitude),
                    [],
                )
            )

    resultats = []
    for station in candidates:
        distance = distance_metres(
            latitude,
            longitude,
            station["latitude"],
            station["longitude"],
        )
        if distance <= rayon_metres:
            resultats.append((distance, station))
    return sorted(resultats, key=lambda element: element[0])


def nombre(valeur, valeur_defaut=None):
    try:
        return float(valeur)
    except (TypeError, ValueError):
        return valeur_defaut


def normaliser_enseigne(enseigne):
    texte = unicodedata.normalize("NFKC", enseigne or "")
    return " ".join(texte.replace(";", " ").split())[:80]


def correspondance_ban_fiable(station, resultat_ban):
    score = nombre(resultat_ban.get("result_score"), 0)
    score_suivant = nombre(resultat_ban.get("result_score_next"), 0)
    code_postal = (resultat_ban.get("result_postcode") or "").strip()
    return (
        resultat_ban.get("result_status") == "ok"
        and score >= 0.8
        and score - score_suivant >= 0.15
        and code_postal == (station.get("cp") or "").strip()
    )


def verifier_stations(stations, resultats_ban, stations_osm):
    index_osm = indexer_stations_osm(stations_osm)
    enrichissements_precedents = {}
    if ENRICHISSEMENT_STATIONS_JSON.exists():
        try:
            enrichissements_precedents = json.loads(
                ENRICHISSEMENT_STATIONS_JSON.read_text(encoding="utf-8")
            ).get("stations", {})
        except (OSError, ValueError, TypeError):
            enrichissements_precedents = {}
    enrichissements = {}
    controles = []
    compteurs = {
        "stations_total": len(stations),
        "adresses_ban_trouvees": 0,
        "enseignes_trouvees": 0,
        "coordonnees_corrigees": 0,
        "a_verifier_manuellement": 0,
    }

    for station in stations:
        station_id = str(station.get("id", ""))
        latitude = nombre(station.get("latitude"))
        longitude = nombre(station.get("longitude"))
        resultat_ban = resultats_ban.get(station_id, {})
        latitude_ban = nombre(resultat_ban.get("latitude"))
        longitude_ban = nombre(resultat_ban.get("longitude"))
        ban_fiable = correspondance_ban_fiable(station, resultat_ban)

        if resultat_ban.get("result_status") == "ok":
            compteurs["adresses_ban_trouvees"] += 1

        proches_origine = []
        if latitude is not None and longitude is not None:
            proches_origine = stations_osm_proches(
                index_osm,
                latitude,
                longitude,
                RAYON_CONFIRMATION_OSM_METRES,
            )

        enseigne = ""
        station_osm = None
        if proches_origine and proches_origine[0][0] <= RAYON_NOM_METRES:
            station_osm = proches_origine[0][1]
            enseigne = normaliser_enseigne(station_osm.get("enseigne"))

        latitude_corrigee = None
        longitude_corrigee = None
        source_correction = ""
        ecart_ban = None
        enrichissement_precedent = enrichissements_precedents.get(
            station_id,
            {},
        )

        if (
            not enseigne
            and enrichissement_precedent.get("signature")
            == signature_adresse(station)
        ):
            enseigne = normaliser_enseigne(
                enrichissement_precedent.get("enseigne", "")
            )

        if (
            latitude is not None
            and longitude is not None
            and latitude_ban is not None
            and longitude_ban is not None
        ):
            ecart_ban = distance_metres(
                latitude,
                longitude,
                latitude_ban,
                longitude_ban,
            )

        if ban_fiable and ecart_ban is not None and ecart_ban >= ECART_CORRECTION_METRES:
            proches_ban = stations_osm_proches(
                index_osm,
                latitude_ban,
                longitude_ban,
                RAYON_CONFIRMATION_OSM_METRES,
            )

            if proches_ban:
                meilleure_distance, meilleure_osm = proches_ban[0]
                deuxieme_distance = (
                    proches_ban[1][0]
                    if len(proches_ban) > 1
                    else float("inf")
                )
                correspondance_unique = (
                    meilleure_distance <= 200
                    or deuxieme_distance >= meilleure_distance * 1.8
                )
                if correspondance_unique:
                    latitude_corrigee = meilleure_osm["latitude"]
                    longitude_corrigee = meilleure_osm["longitude"]
                    source_correction = "BAN + OpenStreetMap"
                    station_osm = meilleure_osm
                    enseigne = normaliser_enseigne(
                        meilleure_osm.get("enseigne")
                    )
            elif resultat_ban.get("result_type") == "housenumber":
                latitude_corrigee = latitude_ban
                longitude_corrigee = longitude_ban
                source_correction = "Base Adresse Nationale"

        if (
            latitude_corrigee is None
            and enrichissement_precedent.get("signature")
            == signature_adresse(station)
            and enrichissement_precedent.get("latitude_corrigee") is not None
            and enrichissement_precedent.get("longitude_corrigee") is not None
        ):
            latitude_corrigee = enrichissement_precedent["latitude_corrigee"]
            longitude_corrigee = enrichissement_precedent["longitude_corrigee"]
            source_correction = enrichissement_precedent.get(
                "source_correction",
                "Correction precedente conservee",
            )

        if latitude_corrigee is not None:
            compteurs["coordonnees_corrigees"] += 1

        if enseigne:
            compteurs["enseignes_trouvees"] += 1

        if enseigne or latitude_corrigee is not None:
            enrichissements[station_id] = {
                "signature": signature_adresse(station),
                "enseigne": enseigne,
                "latitude_corrigee": latitude_corrigee,
                "longitude_corrigee": longitude_corrigee,
                "source_correction": source_correction,
                "osm_id": station_osm.get("osm_id") if station_osm else None,
            }

        if ecart_ban is not None and ecart_ban >= ECART_CORRECTION_METRES:
            corrigee = latitude_corrigee is not None
            if not corrigee:
                compteurs["a_verifier_manuellement"] += 1
            controles.append(
                {
                    "id": station_id,
                    "adresse": station.get("adresse", ""),
                    "cp": station.get("cp", ""),
                    "ville": station.get("ville", ""),
                    "ecart_ban_metres": round(ecart_ban),
                    "score_ban": nombre(resultat_ban.get("result_score"), 0),
                    "resultat_ban": resultat_ban.get("result_label", ""),
                    "corrigee": corrigee,
                    "source_correction": source_correction,
                }
            )

    controles.sort(key=lambda controle: controle["ecart_ban_metres"], reverse=True)
    return enrichissements, compteurs, controles


def enregistrer_resultats(stations, enrichissements, compteurs, controles):
    genere_le = datetime.now(timezone.utc).isoformat()
    ENRICHISSEMENT_STATIONS_JSON.write_text(
        json.dumps(
            {
                "generated_at": genere_le,
                "sources": [BAN_CSV_URL, "https://www.openstreetmap.org"],
                "stations": enrichissements,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    RAPPORT_COORDONNEES_JSON.write_text(
        json.dumps(
            {
                "generated_at": genere_le,
                "summary": compteurs,
                "review_required": [
                    controle for controle in controles if not controle["corrigee"]
                ],
                "corrected": [
                    controle for controle in controles if controle["corrigee"]
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    for station in stations:
        enrichissement = enrichissements.get(str(station.get("id", "")), {})
        station["enseigne"] = enrichissement.get("enseigne", "")
        if enrichissement.get("latitude_corrigee") is not None:
            station["latitude"] = enrichissement["latitude_corrigee"]
            station["longitude"] = enrichissement["longitude_corrigee"]
    ecrire_stations_csv(stations)


def main():
    stations = lire_stations()
    print(f"Verification BAN de {len(stations)} stations...")
    resultats_ban = geocoder_adresses(stations)
    print("Chargement des stations OpenStreetMap...")
    stations_osm = telecharger_stations_osm()
    print(f"{len(stations_osm)} stations OSM chargees")
    enrichissements, compteurs, controles = verifier_stations(
        stations,
        resultats_ban,
        stations_osm,
    )
    enregistrer_resultats(
        stations,
        enrichissements,
        compteurs,
        controles,
    )
    print(json.dumps(compteurs, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
