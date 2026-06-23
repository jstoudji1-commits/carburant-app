import csv
import json
import unicodedata
from pathlib import Path

from update_data import signature_adresse
from verify_station_coordinates import (
    ENSEIGNES_REFERENCES,
    detecter_enseigne_connue,
)


BASE_DIR = Path(__file__).resolve().parent
STATIONS_CSV = BASE_DIR / "stations.csv"
ENRICHISSEMENT_JSON = BASE_DIR / "stations_enrichment.json"
RAPPORT_COORDONNEES_JSON = BASE_DIR / "stations_coordinates_report.json"
SORTIE_CSV = BASE_DIR / "stations_enseignes_a_enrichir.csv"
SORTIE_JSON = BASE_DIR / "stations_enseignes_a_enrichir.json"


ENSEIGNES_GENERIQUES = {
    "",
    "Independent",
    "Station-service",
    "Station Service",
    "Station",
    "U",
}


def normaliser(texte):
    texte = unicodedata.normalize("NFKD", str(texte or ""))
    texte = "".join(
        caractere
        for caractere in texte
        if not unicodedata.combining(caractere)
    )
    return " ".join(texte.casefold().split())


def lire_stations():
    with STATIONS_CSV.open("r", encoding="utf-8-sig", newline="") as fichier:
        return list(csv.DictReader(fichier))


def lire_json(path, defaut):
    if not path.exists():
        return defaut
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return defaut


def trouver_indices_enseigne(station):
    texte = " ".join(
        str(station.get(cle, "") or "")
        for cle in ("enseigne", "adresse", "ville")
    )
    indices = []

    enseigne_detectee = detecter_enseigne_connue(texte)
    if enseigne_detectee:
        indices.append(enseigne_detectee)

    texte_normalise = normaliser(texte)
    for enseigne, variantes in ENSEIGNES_REFERENCES:
        if enseigne in indices:
            continue
        if any(normaliser(variante) in texte_normalise for variante in variantes):
            indices.append(enseigne)

    return indices


def qualite_enseigne(station, enrichissement, controle):
    enseigne = (station.get("enseigne") or "").strip()
    if enseigne in ENSEIGNES_GENERIQUES:
        return "a_completer"

    source = (enrichissement or {}).get("source_enseigne", "")
    if source == "OpenStreetMap":
        return "ok_osm"

    if controle:
        motifs = controle.get("motifs", [])
        if "correspondance OpenStreetMap ambigue" in motifs:
            return "a_verifier_osm_ambigu"
        if "aucune station OpenStreetMap proche" in motifs:
            return "a_verifier_absente_osm"

    return "a_verifier"


def main():
    stations = lire_stations()
    enrichissements = lire_json(
        ENRICHISSEMENT_JSON,
        {},
    ).get("stations", {})
    rapport = lire_json(RAPPORT_COORDONNEES_JSON, {})
    controles = {
        str(item.get("id", "")): item
        for item in rapport.get("review_required", [])
    }
    lignes = []

    for station in stations:
        station_id = str(station.get("id", ""))
        enrichissement = enrichissements.get(station_id, {})
        controle = controles.get(station_id, {})
        statut = qualite_enseigne(station, enrichissement, controle)
        indices = trouver_indices_enseigne(station)

        if statut.startswith("ok") and not indices:
            continue

        if statut.startswith("ok") and station.get("enseigne") in indices:
            continue

        lignes.append(
            {
                "id": station_id,
                "enseigne_actuelle": station.get("enseigne", ""),
                "statut_enseigne": statut,
                "suggestions_enseigne": " | ".join(indices),
                "adresse": station.get("adresse", ""),
                "cp": station.get("cp", ""),
                "ville": station.get("ville", ""),
                "latitude": station.get("latitude", ""),
                "longitude": station.get("longitude", ""),
                "source_enseigne": enrichissement.get("source_enseigne", ""),
                "osm_id": enrichissement.get("osm_id", ""),
                "motifs_controle": " | ".join(controle.get("motifs", [])),
                "signature": signature_adresse(station),
                "enseigne_corrigee": "",
                "decision": "",
                "commentaire": "",
            }
        )

    champs = [
        "id",
        "enseigne_actuelle",
        "statut_enseigne",
        "suggestions_enseigne",
        "adresse",
        "cp",
        "ville",
        "latitude",
        "longitude",
        "source_enseigne",
        "osm_id",
        "motifs_controle",
        "signature",
        "enseigne_corrigee",
        "decision",
        "commentaire",
    ]

    with SORTIE_CSV.open("w", encoding="utf-8-sig", newline="") as fichier:
        writer = csv.DictWriter(fichier, fieldnames=champs, delimiter=";")
        writer.writeheader()
        writer.writerows(lignes)

    resume = {
        "stations_total": len(stations),
        "stations_a_enrichir": len(lignes),
        "fichier_csv": SORTIE_CSV.name,
        "colonnes_a_remplir": ["enseigne_corrigee", "decision", "commentaire"],
    }
    SORTIE_JSON.write_text(
        json.dumps(resume, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(resume, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
