import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from update_data import _extraire_lignes


BASE_DIR = Path(__file__).resolve().parent
STATIONS_CSV = BASE_DIR / "stations.csv"
RAPPORT_JSON = BASE_DIR / "stations_prix_carburants_gouv_compare.json"
RAPPORT_CSV = BASE_DIR / "stations_prix_carburants_gouv_ecarts.csv"
SOURCE_PRIX_CARBURANTS_GOUV = (
    "https://donnees.roulez-eco.fr/opendata/instantane"
)
CARBURANTS = ("gazole", "e10", "sp98")


def normaliser_texte(valeur):
    return " ".join(str(valeur or "").casefold().split())


def normaliser_prix(valeur):
    texte = str(valeur or "").replace(",", ".").strip()
    if not texte:
        return ""
    try:
        return f"{float(texte):.3f}"
    except ValueError:
        return texte


def normaliser_coordonnees(valeur):
    texte = str(valeur or "").strip()
    if not texte:
        return ""
    try:
        return f"{float(texte):.6f}"
    except ValueError:
        return texte


def lire_stations_locales():
    with STATIONS_CSV.open("r", encoding="utf-8-sig", newline="") as fichier:
        return {
            str(ligne.get("id", "")): ligne
            for ligne in csv.DictReader(fichier)
            if ligne.get("id")
        }


def telecharger_stations_prix_carburants_gouv():
    requete = Request(
        SOURCE_PRIX_CARBURANTS_GOUV,
        headers={"User-Agent": "OptiPlein/1.0 comparaison-officielle"},
    )
    with urlopen(requete, timeout=120) as reponse:
        contenu = reponse.read()
    return {
        str(ligne.get("id", "")): ligne
        for ligne in _extraire_lignes(contenu)
        if ligne.get("id")
    }


def comparer_station(station_id, locale, officielle):
    ecarts = []

    champs_textes = ("cp", "ville", "adresse")
    for champ in champs_textes:
        if normaliser_texte(locale.get(champ)) != normaliser_texte(
            officielle.get(champ)
        ):
            ecarts.append(
                {
                    "id": station_id,
                    "champ": champ,
                    "valeur_locale": locale.get(champ, ""),
                    "valeur_officielle": officielle.get(champ, ""),
                }
            )

    for champ in ("latitude", "longitude"):
        if normaliser_coordonnees(locale.get(champ)) != normaliser_coordonnees(
            officielle.get(champ)
        ):
            ecarts.append(
                {
                    "id": station_id,
                    "champ": champ,
                    "valeur_locale": locale.get(champ, ""),
                    "valeur_officielle": officielle.get(champ, ""),
                }
            )

    for carburant in CARBURANTS:
        if normaliser_prix(locale.get(carburant)) != normaliser_prix(
            officielle.get(carburant)
        ):
            ecarts.append(
                {
                    "id": station_id,
                    "champ": carburant,
                    "valeur_locale": locale.get(carburant, ""),
                    "valeur_officielle": officielle.get(carburant, ""),
                }
            )

    return ecarts


def ecrire_csv(ecarts):
    champs = [
        "id",
        "champ",
        "valeur_locale",
        "valeur_officielle",
    ]
    with RAPPORT_CSV.open("w", encoding="utf-8-sig", newline="") as fichier:
        writer = csv.DictWriter(fichier, fieldnames=champs, delimiter=";")
        writer.writeheader()
        writer.writerows(ecarts)


def main():
    locales = lire_stations_locales()
    officielles = telecharger_stations_prix_carburants_gouv()

    ids_locaux = set(locales)
    ids_officiels = set(officielles)
    ids_communs = ids_locaux & ids_officiels

    ecarts = []
    for station_id in sorted(ids_communs):
        ecarts.extend(
            comparer_station(
                station_id,
                locales[station_id],
                officielles[station_id],
            )
        )

    manquantes_local = sorted(ids_officiels - ids_locaux)
    absentes_officiel = sorted(ids_locaux - ids_officiels)

    rapport = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_officielle": SOURCE_PRIX_CARBURANTS_GOUV,
        "stations_locales": len(locales),
        "stations_officielles": len(officielles),
        "stations_communes": len(ids_communs),
        "stations_manquantes_localement": manquantes_local,
        "stations_absentes_du_flux_officiel": absentes_officiel,
        "nombre_ecarts": len(ecarts),
        "ecarts_par_champ": {},
        "fichier_ecarts": RAPPORT_CSV.name,
    }

    for ecart in ecarts:
        rapport["ecarts_par_champ"][ecart["champ"]] = (
            rapport["ecarts_par_champ"].get(ecart["champ"], 0) + 1
        )

    RAPPORT_JSON.write_text(
        json.dumps(rapport, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    ecrire_csv(ecarts)

    print(json.dumps(rapport, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
