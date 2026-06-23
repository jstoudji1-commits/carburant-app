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
RAYON_NOM_METRES = 300
RAYON_CONFIRMATION_OSM_METRES = 650
ECART_CORRECTION_BAN_METRES = 450
ECART_CORRECTION_OSM_METRES = 80
ECART_AUDIT_METRES = 250
BORNES_OVERPASS = [
    ("metropole-corse", (41, -5.5, 51.5, 10)),
    ("guadeloupe", (15.8, -61.9, 16.6, -61.0)),
    ("martinique", (14.3, -61.3, 14.95, -60.75)),
    ("guyane", (2.0, -54.8, 5.9, -51.4)),
    ("reunion", (-21.5, 55.1, -20.8, 56.0)),
    ("mayotte", (-13.1, 44.9, -12.5, 45.4)),
    ("saint-pierre-et-miquelon", (46.7, -56.6, 47.2, -56.0)),
]
ENSEIGNES_REFERENCES = [
    ("Total Access", ["total access"]),
    ("TotalEnergies", ["totalenergies", "total energies"]),
    ("Total", ["station total", "relais total", "total"]),
    ("E.Leclerc", ["e leclerc", "eleclerc", "leclerc"]),
    ("Intermarché", ["intermarche", "mousquetaires"]),
    ("Carrefour Market", ["carrefour market"]),
    ("Carrefour Contact", ["carrefour contact"]),
    ("Carrefour", ["carrefour"]),
    ("Hyper U", ["hyper u"]),
    ("Super U", ["super u"]),
    ("Système U", ["systeme u", "station u", "la station u", "u express"]),
    ("Auchan", ["auchan"]),
    ("Esso Express", ["esso express"]),
    ("Esso", ["esso"]),
    ("Avia XPress", ["avia xpress"]),
    ("Avia", ["avia"]),
    ("BP", ["bp"]),
    ("Shell", ["shell"]),
    ("Eni", ["eni", "agip"]),
    ("Elan", ["elan"]),
    ("Dyneff", ["dyneff"]),
    ("Netto", ["netto"]),
    ("Vito", ["vito"]),
    ("Casino", ["casino"]),
    ("Cora", ["cora"]),
    ("Match", ["match"]),
    ("Rompetrol", ["rompetrol"]),
    ("AS24", ["as24", "as 24"]),
    ("IDS", ["ids"]),
]


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


def interroger_overpass(nom_zone, bornes):
    sud, ouest, nord, est = bornes
    requete_overpass = (
        "[out:json][timeout:240];"
        f"nwr[amenity=fuel]({sud},{ouest},{nord},{est});"
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
            return contenu.get("elements", [])
        except Exception as erreur:
            derniere_erreur = erreur
            time.sleep(3)

    raise RuntimeError(
        f"Impossible de charger les stations OpenStreetMap pour {nom_zone}"
    ) from derniere_erreur


def telecharger_stations_osm():
    elements = []
    erreurs = []

    for nom_zone, bornes in BORNES_OVERPASS:
        try:
            elements.extend(interroger_overpass(nom_zone, bornes))
        except Exception as erreur:
            erreurs.append(str(erreur))

    if not elements:
        raise RuntimeError(
            "Impossible de charger les stations OpenStreetMap: "
            + " | ".join(erreurs)
        )

    return extraire_stations_osm(elements)


def extraire_stations_osm(elements):
    stations = []
    ids_vus = set()
    for element in elements:
        osm_id = f"{element.get('type', '')}/{element.get('id', '')}"
        if osm_id in ids_vus:
            continue
        ids_vus.add(osm_id)

        centre = element.get("center", {})
        latitude = element.get("lat", centre.get("lat"))
        longitude = element.get("lon", centre.get("lon"))
        if latitude is None or longitude is None:
            continue

        tags = element.get("tags", {})
        textes_enseigne = [
            tags.get("brand"),
            tags.get("name"),
            tags.get("operator"),
        ]
        enseigne = normaliser_enseigne(
            next((texte for texte in textes_enseigne if texte), "")
        )
        stations.append(
            {
                "latitude": float(latitude),
                "longitude": float(longitude),
                "enseigne": enseigne,
                "osm_id": osm_id,
                "nom": normaliser_enseigne(tags.get("name", "")),
                "operateur": normaliser_enseigne(tags.get("operator", "")),
                "cp": (tags.get("addr:postcode") or "").strip(),
                "ville": normaliser_enseigne(tags.get("addr:city", "")),
                "texte": " ".join(
                    str(valeur or "")
                    for valeur in (
                        tags.get("brand"),
                        tags.get("name"),
                        tags.get("operator"),
                        tags.get("addr:housenumber"),
                        tags.get("addr:street"),
                        tags.get("addr:postcode"),
                        tags.get("addr:city"),
                    )
                ),
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


def texte_recherche(texte):
    texte = unicodedata.normalize("NFKD", texte or "")
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


def detecter_enseigne_connue(*textes):
    recherche = f" {texte_recherche(' '.join(str(texte or '') for texte in textes))} "
    if not recherche.strip():
        return ""

    for enseigne, variantes in ENSEIGNES_REFERENCES:
        for variante in variantes:
            variante_normalisee = f" {texte_recherche(variante)} "
            if variante_normalisee in recherche:
                return enseigne
    return ""


def normaliser_enseigne(enseigne):
    texte = unicodedata.normalize("NFKC", enseigne or "")
    texte = " ".join(texte.replace(";", " ").split())[:80]
    return detecter_enseigne_connue(texte) or texte


def enseigne_depuis_station(station):
    return detecter_enseigne_connue(
        station.get("enseigne", ""),
        station.get("adresse", ""),
        station.get("ville", ""),
    )


def enseigne_depuis_osm(station_osm):
    return (
        normaliser_enseigne(station_osm.get("enseigne", ""))
        or detecter_enseigne_connue(station_osm.get("texte", ""))
    )


def score_station_osm(station, distance, station_osm):
    score = 0
    enseigne_station = enseigne_depuis_station(station)
    enseigne_osm = enseigne_depuis_osm(station_osm)
    cp_osm = (station_osm.get("cp") or "").strip()
    cp_station = (station.get("cp") or "").strip()

    if distance <= 60:
        score += 45
    elif distance <= 120:
        score += 34
    elif distance <= 250:
        score += 22
    else:
        score += 10

    if enseigne_osm:
        score += 20

    if enseigne_station and enseigne_osm == enseigne_station:
        score += 45
    elif enseigne_station and enseigne_osm:
        score -= 15

    if cp_osm and cp_osm == cp_station:
        score += 25
    elif cp_osm:
        score -= 20

    if station_osm.get("nom") or station_osm.get("operateur"):
        score += 8

    return score


def choisir_station_osm(station, candidates):
    if not candidates:
        return None, None, False

    scores = sorted(
        (
            (
                score_station_osm(station, distance, station_osm),
                distance,
                station_osm,
            )
            for distance, station_osm in candidates
        ),
        key=lambda element: (-element[0], element[1]),
    )
    meilleur_score, meilleure_distance, meilleure_station = scores[0]
    deuxieme_score = scores[1][0] if len(scores) > 1 else -999
    deuxieme_distance = scores[1][1] if len(scores) > 1 else float("inf")
    unique = (
        len(scores) == 1
        or meilleur_score - deuxieme_score >= 25
        or deuxieme_distance
        >= max(meilleure_distance * 1.8, meilleure_distance + 120)
    )
    fiable = meilleur_score >= 48 and unique
    return meilleure_distance, meilleure_station, fiable


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
        "enseignes_openstreetmap": 0,
        "enseignes_deduites": 0,
        "enseignes_conservees": 0,
        "coordonnees_corrigees": 0,
        "coordonnees_corrigees_openstreetmap": 0,
        "coordonnees_corrigees_ban": 0,
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
        distance_osm, station_osm, osm_fiable = choisir_station_osm(
            station,
            proches_origine,
        )

        enseigne = ""
        source_enseigne = ""
        if station_osm and (
            osm_fiable
            or (
                distance_osm is not None
                and distance_osm <= RAYON_NOM_METRES
            )
        ):
            enseigne = enseigne_depuis_osm(station_osm)
            if enseigne:
                source_enseigne = "OpenStreetMap"
                compteurs["enseignes_openstreetmap"] += 1

        if not enseigne:
            enseigne = enseigne_depuis_station(station)
            if enseigne:
                source_enseigne = "Adresse officielle"
                compteurs["enseignes_deduites"] += 1

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
            if enseigne:
                source_enseigne = enrichissement_precedent.get(
                    "source_enseigne",
                    "Correction precedente conservee",
                )
                compteurs["enseignes_conservees"] += 1

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

        if (
            station_osm
            and osm_fiable
            and distance_osm is not None
            and distance_osm >= ECART_CORRECTION_OSM_METRES
        ):
            latitude_corrigee = station_osm["latitude"]
            longitude_corrigee = station_osm["longitude"]
            source_correction = "OpenStreetMap"
            compteurs["coordonnees_corrigees_openstreetmap"] += 1

        if (
            latitude_corrigee is None
            and ban_fiable
            and ecart_ban is not None
            and ecart_ban >= ECART_CORRECTION_BAN_METRES
        ):
            proches_ban = stations_osm_proches(
                index_osm,
                latitude_ban,
                longitude_ban,
                RAYON_CONFIRMATION_OSM_METRES,
            )
            distance_ban_osm, station_ban_osm, ban_osm_fiable = choisir_station_osm(
                station,
                proches_ban,
            )

            if station_ban_osm and ban_osm_fiable:
                latitude_corrigee = station_ban_osm["latitude"]
                longitude_corrigee = station_ban_osm["longitude"]
                source_correction = "BAN + OpenStreetMap"
                station_osm = station_ban_osm
                distance_osm = distance_ban_osm
                compteurs["coordonnees_corrigees_openstreetmap"] += 1
                if not enseigne:
                    enseigne = enseigne_depuis_osm(station_ban_osm)
                    if enseigne:
                        source_enseigne = "OpenStreetMap"
                        compteurs["enseignes_openstreetmap"] += 1
            elif resultat_ban.get("result_type") == "housenumber":
                latitude_corrigee = latitude_ban
                longitude_corrigee = longitude_ban
                source_correction = "Base Adresse Nationale"
                compteurs["coordonnees_corrigees_ban"] += 1

        if (
            latitude_corrigee is not None
            and latitude is not None
            and longitude is not None
            and distance_metres(latitude, longitude, latitude_corrigee, longitude_corrigee)
            < 5
        ):
            latitude_corrigee = None
            longitude_corrigee = None
            source_correction = ""

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
                "source_enseigne": source_enseigne,
                "latitude_corrigee": latitude_corrigee,
                "longitude_corrigee": longitude_corrigee,
                "source_correction": source_correction,
                "osm_id": station_osm.get("osm_id") if station_osm else None,
                "distance_osm_metres": (
                    round(distance_osm)
                    if distance_osm is not None
                    else None
                ),
            }

        motifs_controle = []
        if not enseigne:
            motifs_controle.append("enseigne inconnue")
        if ecart_ban is not None and ecart_ban >= ECART_AUDIT_METRES:
            motifs_controle.append("adresse BAN eloignee des coordonnees")
        if proches_origine and not osm_fiable:
            motifs_controle.append("correspondance OpenStreetMap ambigue")
        if (
            not proches_origine
            and latitude is not None
            and longitude is not None
        ):
            motifs_controle.append("aucune station OpenStreetMap proche")

        if latitude_corrigee is not None:
            motifs_controle.append("coordonnees corrigees")

        if motifs_controle:
            corrigee = latitude_corrigee is not None
            if not corrigee:
                compteurs["a_verifier_manuellement"] += 1
            controles.append(
                {
                    "id": station_id,
                    "adresse": station.get("adresse", ""),
                    "cp": station.get("cp", ""),
                    "ville": station.get("ville", ""),
                    "enseigne": enseigne,
                    "motifs": motifs_controle,
                    "ecart_ban_metres": (
                        round(ecart_ban)
                        if ecart_ban is not None
                        else None
                    ),
                    "distance_osm_metres": (
                        round(distance_osm)
                        if distance_osm is not None
                        else None
                    ),
                    "score_ban": nombre(resultat_ban.get("result_score"), 0),
                    "resultat_ban": resultat_ban.get("result_label", ""),
                    "corrigee": corrigee,
                    "source_correction": source_correction,
                    "osm_id": station_osm.get("osm_id") if station_osm else None,
                }
            )

    controles.sort(
        key=lambda controle: (
            controle["corrigee"],
            controle["ecart_ban_metres"] or 0,
            controle["distance_osm_metres"] or 0,
        ),
        reverse=True,
    )
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
