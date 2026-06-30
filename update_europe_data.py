import csv
import io
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


BASE_DIR = Path(__file__).resolve().parent
EUROPE_STATIONS_CSV = BASE_DIR / "stations_europe.csv"
EUROPE_METADATA_JSON = BASE_DIR / "stations_europe_metadata.json"

SOURCES = {
    "espagne": {
        "country_code": "ES",
        "url": (
            "https://sedeaplicaciones.minetur.gob.es/"
            "ServiciosRESTCarburantes/PreciosCarburantes/"
            "EstacionesTerrestres/"
        ),
        "source": "Ministerio para la Transicion Ecologica - Geoportal Hidrocarburos",
    },
    "italie_prix": {
        "url": "https://www.mimit.gov.it/images/exportCSV/prezzo_alle_8.csv",
        "source": "MIMIT - Osservaprezzi carburanti",
    },
    "italie_stations": {
        "url": "https://www.mimit.gov.it/images/exportCSV/anagrafica_impianti_attivi.csv",
        "source": "MIMIT - Osservaprezzi carburanti",
    },
}

ENTETES = [
    "country",
    "country_code",
    "id",
    "cp",
    "ville",
    "adresse",
    "latitude",
    "longitude",
    "enseigne",
    "gazole",
    "e10",
    "sp98",
    "updated_at",
    "source",
]


def telecharger(url, timeout=60):

    derniere_erreur = None

    for tentative in range(3):
        requete = Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 OptiPlein/1.0 "
                    "(contact: optiplein5@gmail.com)"
                ),
                "Accept": "*/*",
            },
        )

        try:
            with urlopen(requete, timeout=timeout) as reponse:
                return reponse.read()
        except Exception as erreur:
            derniere_erreur = erreur
            time.sleep(2 + tentative * 2)

    try:
        resultat = subprocess.run(
            [
                "curl",
                "-L",
                "--fail",
                "--silent",
                "--show-error",
                "--max-time",
                str(timeout),
                url,
            ],
            check=True,
            capture_output=True,
        )
        return resultat.stdout
    except Exception:
        raise derniere_erreur


def decimal_fr(valeur):

    valeur = str(valeur or "").strip().replace(",", ".")

    if not valeur:
        return ""

    try:
        prix = float(valeur)
    except ValueError:
        return ""

    if prix <= 0 or prix == 9.999:
        return ""

    return f"{prix:.3f}"


def coordonnee(valeur):

    valeur = str(valeur or "").strip().replace(",", ".")

    if not valeur:
        return ""

    try:
        return str(float(valeur))
    except ValueError:
        return ""


def lignes_espagne():

    contenu = telecharger(SOURCES["espagne"]["url"])
    donnees = json.loads(contenu.decode("utf-8-sig"))
    date_source = donnees.get("Fecha", "")

    for station in donnees.get("ListaEESSPrecio", []):
        yield {
            "country": "Espagne",
            "country_code": "ES",
            "id": "ES-" + str(station.get("IDEESS", "")),
            "cp": station.get("C.P.", ""),
            "ville": station.get("Municipio") or station.get("Localidad", ""),
            "adresse": station.get("Direccion")
            or station.get("Dirección")
            or "",
            "latitude": coordonnee(station.get("Latitud")),
            "longitude": coordonnee(station.get("Longitud (WGS84)")),
            "enseigne": station.get("Rotulo")
            or station.get("Rótulo")
            or "",
            "gazole": decimal_fr(station.get("Precio Gasoleo A")),
            "e10": decimal_fr(
                station.get("Precio Gasolina 95 E10")
                or station.get("Precio Gasolina 95 E5")
            ),
            "sp98": decimal_fr(
                station.get("Precio Gasolina 98 E10")
                or station.get("Precio Gasolina 98 E5")
            ),
            "updated_at": date_source,
            "source": SOURCES["espagne"]["source"],
        }


def lecteur_pipe_csv(contenu):

    texte = contenu.decode("utf-8-sig", errors="replace")
    lignes = texte.splitlines()

    if lignes and lignes[0].startswith("Estrazione del "):
        lignes = lignes[1:]

    return csv.DictReader(
        io.StringIO("\n".join(lignes)),
        delimiter="|",
    )


def lignes_italie():

    stations = {}
    contenu_stations = telecharger(SOURCES["italie_stations"]["url"])

    for ligne in lecteur_pipe_csv(contenu_stations):
        station_id = str(ligne.get("idImpianto", "")).strip()

        if not station_id:
            continue

        stations[station_id] = {
            "country": "Italie",
            "country_code": "IT",
            "id": "IT-" + station_id,
            "cp": "",
            "ville": ligne.get("Comune", ""),
            "adresse": ligne.get("Indirizzo", ""),
            "latitude": coordonnee(ligne.get("Latitudine")),
            "longitude": coordonnee(ligne.get("Longitudine")),
            "enseigne": ligne.get("Bandiera")
            or ligne.get("Nome Impianto")
            or "",
            "gazole": "",
            "e10": "",
            "sp98": "",
            "updated_at": "",
            "source": SOURCES["italie_stations"]["source"],
        }

    contenu_prix = telecharger(SOURCES["italie_prix"]["url"])

    for ligne in lecteur_pipe_csv(contenu_prix):
        station_id = str(ligne.get("idImpianto", "")).strip()
        station = stations.get(station_id)

        if not station:
            continue

        carburant = str(ligne.get("descCarburante", "")).casefold()
        prix = decimal_fr(ligne.get("prezzo"))
        date_prix = ligne.get("dtComu", "")

        if not prix:
            continue

        if "gasolio" in carburant and not station["gazole"]:
            station["gazole"] = prix
        elif "benzina" in carburant and not station["e10"]:
            station["e10"] = prix
        elif "super plus" in carburant or "98" in carburant:
            station["sp98"] = prix

        if date_prix:
            station["updated_at"] = date_prix

    yield from stations.values()


def lignes_europe():

    sources = (
        ("Espagne", lignes_espagne),
        ("Italie", lignes_italie),
    )

    for nom_source, fonction_source in sources:
        try:
            yield from fonction_source()
        except Exception as erreur:
            print(
                f"Source Europe ignoree temporairement ({nom_source}) : "
                f"{erreur}"
            )


def ecrire_stations_europe(lignes):

    fichier_temporaire = EUROPE_STATIONS_CSV.with_suffix(".tmp")

    with fichier_temporaire.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as fichier:
        writer = csv.DictWriter(fichier, fieldnames=ENTETES)
        writer.writeheader()

        for ligne in lignes:
            writer.writerow(
                {
                    entete: ligne.get(entete, "")
                    for entete in ENTETES
                }
            )

    fichier_temporaire.replace(EUROPE_STATIONS_CSV)


def mettre_a_jour_stations_europe():

    lignes = list(lignes_europe())

    if not lignes:
        raise RuntimeError(
            "Aucune station europeenne telechargee."
        )

    ecrire_stations_europe(lignes)

    pays = {}
    for ligne in lignes:
        pays[ligne["country_code"]] = pays.get(ligne["country_code"], 0) + 1

    EUROPE_METADATA_JSON.write_text(
        json.dumps(
            {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "count": len(lignes),
                "countries": pays,
                "sources": SOURCES,
                "notes": {
                    "DE": (
                        "Prix temps reel MTS-K accessibles via une cle API "
                        "Tankerkönig; integration a brancher avec une cle."
                    ),
                    "BE": (
                        "Prix officiels disponibles surtout en prix maximum "
                        "nationaux; source station-par-station a confirmer."
                    ),
                    "LU": (
                        "Prix publics reglementes; source station-par-station "
                        "a confirmer."
                    ),
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return lignes


if __name__ == "__main__":
    resultat = mettre_a_jour_stations_europe()
    print(f"{len(resultat)} stations europeennes telechargees")
