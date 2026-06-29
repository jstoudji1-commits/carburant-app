import csv
import gzip
import io
import json
import os
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
import statistics
import zipfile
import xml.etree.ElementTree as ET
from urllib.error import URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


BASE_DIR = Path(__file__).resolve().parent
STATIONS_CSV = BASE_DIR / "stations.csv"
METADATA_JSON = BASE_DIR / "stations_metadata.json"
REFERENCES_PRIX_JSON = BASE_DIR / "stations_prix_9h.json"
HISTORIQUE_PRIX_JSON = BASE_DIR / "stations_historique_prix.json"
MARCHE_CARBURANT_JSON = BASE_DIR / "carburant_market_signals.json"
ENRICHISSEMENT_STATIONS_JSON = BASE_DIR / "stations_enrichment.json"
FUSEAU_PARIS = ZoneInfo("Europe/Paris")
CARBURANTS = ["gazole", "e10", "sp98"]
STATIONS_EXCLUES = {
    # Prix poids lourds : ne pas afficher comme station grand public.
    "13016007",
}

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
    "enseigne",
    "gazole",
    "e10",
    "sp98",
    "tendance_gazole",
    "tendance_e10",
    "tendance_sp98",
    "tendance_demain_gazole",
    "confiance_demain_gazole",
    "tendance_demain_e10",
    "confiance_demain_e10",
    "tendance_demain_sp98",
    "confiance_demain_sp98",
]


def signature_adresse(station):

    texte = "|".join(
        str(station.get(cle, "") or "")
        for cle in ("adresse", "cp", "ville")
    )
    return " ".join(texte.casefold().split())


def appliquer_enrichissements(lignes):

    enrichissements = {}

    if ENRICHISSEMENT_STATIONS_JSON.exists():
        try:
            contenu = json.loads(
                ENRICHISSEMENT_STATIONS_JSON.read_text(
                    encoding="utf-8"
                )
            )
            enrichissements = contenu.get("stations", {})
        except (OSError, ValueError, TypeError):
            enrichissements = {}

    for station in lignes:
        station["enseigne"] = ""
        enrichissement = enrichissements.get(
            str(station.get("id", "")),
            {}
        )

        if enrichissement.get("signature") != signature_adresse(station):
            continue

        station["enseigne"] = enrichissement.get("enseigne", "")

        latitude = enrichissement.get("latitude_corrigee")
        longitude = enrichissement.get("longitude_corrigee")
        if latitude is not None and longitude is not None:
            station["latitude"] = latitude
            station["longitude"] = longitude


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

    if contenu.startswith(b"\x1f\x8b"):

        contenu = gzip.decompress(contenu)

    archive_candidate = io.BytesIO(contenu)

    if zipfile.is_zipfile(archive_candidate):

        archive_candidate.seek(0)

        with zipfile.ZipFile(archive_candidate) as archive:

            fichiers_donnees = [
                nom
                for nom in archive.namelist()
                if nom.lower().endswith(
                    (".xml", ".csv")
                )
            ]

            if not fichiers_donnees:

                raise ValueError(
                    "L'archive officielle ne contient "
                    "ni fichier XML ni fichier CSV."
                )

            nom_donnees = next(
                (
                    nom
                    for nom in fichiers_donnees
                    if nom.lower().endswith(".xml")
                ),
                fichiers_donnees[0]
            )

            return _extraire_lignes(
                archive.read(nom_donnees)
            )

    if contenu.lstrip().startswith(b"<"):

        return list(
            _lignes_depuis_xml(contenu)
        )

    return list(
        _lignes_depuis_csv(contenu)
    )


def telecharger_donnees_officielles():

    requete = Request(
        SOURCE_OFFICIELLE_URL,
        headers={
            "User-Agent": "OptiPlein/1.0"
        }
    )

    for tentative in range(3):

        try:

            with urlopen(
                requete,
                timeout=90
            ) as response:

                return response.read()

        except (URLError, TimeoutError, OSError):

            if tentative == 2:
                raise

            time.sleep(5 * (tentative + 1))


def _instantane_prix(lignes, date_reference):

    prix = {}

    for station in lignes:

        station_id = station.get("id", "")

        if not station_id:

            continue

        prix[station_id] = [
            station.get(carburant, "")
            for carburant in CARBURANTS
        ]

    return {
        "date": date_reference.date().isoformat(),
        "captured_at": date_reference.isoformat(),
        "prices": prix,
    }


def _lire_references_prix():

    if not REFERENCES_PRIX_JSON.exists():

        return {}

    try:

        return json.loads(
            REFERENCES_PRIX_JSON.read_text(
                encoding="utf-8"
            )
        )

    except (OSError, ValueError, TypeError):

        return {}


def _ecrire_references_prix(references):

    REFERENCES_PRIX_JSON.write_text(
        json.dumps(
            references,
            ensure_ascii=False,
            separators=(",", ":")
        ),
        encoding="utf-8"
    )


def mettre_a_jour_references_9h(lignes):

    maintenant = datetime.now(FUSEAU_PARIS)
    references = _lire_references_prix()
    reference_actuelle = references.get("current")
    date_actuelle = (
        reference_actuelle or {}
    ).get("date")

    if (
        maintenant.hour >= 9
        and date_actuelle != maintenant.date().isoformat()
    ):

        if reference_actuelle:

            references["previous"] = reference_actuelle

        references["current"] = _instantane_prix(
            lignes,
            maintenant
        )
        _ecrire_references_prix(references)

    return references


def _comparer_prix(prix_precedent, prix_actuel):

    if not prix_precedent or not prix_actuel:

        return ""

    try:

        precedent = Decimal(str(prix_precedent))
        actuel = Decimal(str(prix_actuel))

    except (InvalidOperation, ValueError):

        return ""

    if actuel < precedent:

        return "baisse"

    if actuel > precedent:

        return "hausse"

    return "egal"


def ajouter_tendances(lignes, references):

    prix_precedents = (
        references.get("previous") or {}
    ).get("prices", {})
    prix_actuels = (
        references.get("current") or {}
    ).get("prices", {})

    for station in lignes:

        station_id = station.get("id", "")
        precedent = prix_precedents.get(station_id, [])
        actuel = prix_actuels.get(station_id, [])

        for index, carburant in enumerate(CARBURANTS):

            station[f"tendance_{carburant}"] = (
                _comparer_prix(
                    precedent[index]
                    if index < len(precedent)
                    else "",
                    actuel[index]
                    if index < len(actuel)
                    else ""
                )
            )


def _lire_json(fichier, defaut):

    if not fichier.exists():
        return defaut

    try:
        return json.loads(fichier.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return defaut


def _prix_decimal(valeur):

    try:
        if valeur in ("", None):
            return None
        prix = Decimal(str(valeur).replace(",", "."))
    except (InvalidOperation, ValueError):
        return None

    if prix <= 0 or prix == Decimal("9.999"):
        return None

    return float(prix)


def _moyennes_nationales(lignes):

    moyennes = {}

    for carburant in CARBURANTS:
        valeurs = [
            _prix_decimal(station.get(carburant))
            for station in lignes
        ]
        valeurs = [
            valeur
            for valeur in valeurs
            if valeur is not None
        ]
        moyennes[carburant] = (
            round(statistics.mean(valeurs), 5)
            if valeurs
            else None
        )

    return moyennes


def mettre_a_jour_historique_prix(lignes):

    historique = _lire_json(
        HISTORIQUE_PRIX_JSON,
        {"snapshots": []}
    )
    snapshots = historique.setdefault("snapshots", [])
    maintenant = datetime.now(timezone.utc)
    dernier = snapshots[-1] if snapshots else {}
    dernier_capture = dernier.get("captured_at")

    if dernier_capture:
        try:
            date_dernier = datetime.fromisoformat(dernier_capture)
            if (
                maintenant - date_dernier
            ).total_seconds() < 55 * 60:
                return historique
        except ValueError:
            pass

    snapshots.append(
        {
            "captured_at": maintenant.isoformat(),
            "national": _moyennes_nationales(lignes),
            "stations": {
                str(station.get("id", "")): {
                    carburant: station.get(carburant, "")
                    for carburant in CARBURANTS
                }
                for station in lignes
                if station.get("id")
            },
        }
    )

    limite_secondes = 8 * 24 * 60 * 60
    snapshots[:] = [
        snapshot
        for snapshot in snapshots
        if snapshot.get("captured_at")
    ]
    snapshots[:] = [
        snapshot
        for snapshot in snapshots
        if _snapshot_recent(snapshot, maintenant, limite_secondes)
    ]

    HISTORIQUE_PRIX_JSON.write_text(
        json.dumps(
            historique,
            ensure_ascii=False,
            separators=(",", ":")
        ),
        encoding="utf-8"
    )

    return historique


def _snapshot_recent(snapshot, maintenant, limite_secondes):

    try:
        date_snapshot = datetime.fromisoformat(
            snapshot.get("captured_at", "")
        )
    except (TypeError, ValueError):
        return False

    return (
        maintenant - date_snapshot
    ).total_seconds() <= limite_secondes


def _valeur_snapshot_station(snapshot, station_id, carburant):

    return _prix_decimal(
        (
            snapshot.get("stations", {})
            .get(station_id, {})
            .get(carburant)
        )
    )


def _snapshot_avant(historique, heures):

    snapshots = historique.get("snapshots", [])

    if not snapshots:
        return None

    maintenant = datetime.fromisoformat(
        snapshots[-1]["captured_at"]
    )
    cible_secondes = heures * 3600
    meilleur = None
    meilleur_ecart = None

    for snapshot in snapshots[:-1]:
        try:
            date_snapshot = datetime.fromisoformat(
                snapshot.get("captured_at", "")
            )
        except ValueError:
            continue

        age = (maintenant - date_snapshot).total_seconds()
        ecart = abs(age - cible_secondes)

        if meilleur is None or ecart < meilleur_ecart:
            meilleur = snapshot
            meilleur_ecart = ecart

    if meilleur_ecart is not None and meilleur_ecart <= 8 * 3600:
        return meilleur

    return None


def _extraire_derniere_valeur_csv(texte, index_valeur=4):

    lignes = [
        ligne.split(",")
        for ligne in texte.splitlines()
        if "," in ligne
    ]

    for colonnes in reversed(lignes):
        if len(colonnes) <= index_valeur:
            continue
        try:
            return float(colonnes[index_valeur])
        except ValueError:
            continue

    return None


def _telecharger_texte(url, timeout=12):

    requete = Request(
        url,
        headers={"User-Agent": "OptiPlein/1.0"}
    )

    with urlopen(requete, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="ignore")


def recuperer_signaux_marche():

    signaux = _lire_json(
        MARCHE_CARBURANT_JSON,
        {
            "brent_usd": None,
            "brent_usd_previous": None,
            "eur_usd": None,
            "eur_usd_previous": None,
            "updated_at": None,
        }
    )

    try:
        texte = _telecharger_texte(
            "https://stooq.com/q/d/l/?s=bc.f&i=d"
        )
        lignes = [
            ligne.split(",")
            for ligne in texte.splitlines()[1:]
            if "," in ligne
        ]
        valeurs = []
        for colonnes in lignes[-7:]:
            if len(colonnes) >= 5:
                try:
                    valeurs.append(float(colonnes[4]))
                except ValueError:
                    pass
        if valeurs:
            signaux["brent_usd_previous"] = (
                valeurs[-2]
                if len(valeurs) > 1
                else signaux.get("brent_usd")
            )
            signaux["brent_usd"] = valeurs[-1]
    except (OSError, URLError, TimeoutError, ValueError):
        pass

    try:
        texte = _telecharger_texte(
            "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml"
        )
        root = ET.fromstring(texte)
        valeurs = []
        for cube in root.iter():
            if cube.attrib.get("currency") == "USD":
                try:
                    valeurs.append(float(cube.attrib["rate"]))
                except (KeyError, ValueError):
                    pass
        if valeurs:
            signaux["eur_usd_previous"] = (
                valeurs[1]
                if len(valeurs) > 1
                else signaux.get("eur_usd")
            )
            signaux["eur_usd"] = valeurs[0]
    except (OSError, URLError, TimeoutError, ET.ParseError, ValueError):
        pass

    signaux["updated_at"] = datetime.now(timezone.utc).isoformat()
    MARCHE_CARBURANT_JSON.write_text(
        json.dumps(signaux, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    return signaux


def _variation_relative(actuel, precedent):

    if (
        actuel is None
        or precedent in (None, 0)
    ):
        return None

    return (actuel - precedent) / precedent


def _score_marche(signaux):

    brent = _variation_relative(
        signaux.get("brent_usd"),
        signaux.get("brent_usd_previous")
    )
    eur_usd = _variation_relative(
        signaux.get("eur_usd"),
        signaux.get("eur_usd_previous")
    )
    score = 0
    poids = 0

    if brent is not None:
        score += max(-1, min(1, brent / 0.025)) * 0.65
        poids += 0.65

    if eur_usd is not None:
        # Euro plus fort = carburant importe moins cher.
        score += max(-1, min(1, -eur_usd / 0.01)) * 0.25
        poids += 0.25

    demande = datetime.now(FUSEAU_PARIS).weekday()
    if demande in (4, 5, 6):
        score += 0.10
        poids += 0.10

    return score / poids if poids else 0


def _classer_score(score, confiance):

    if score >= 0.18:
        return "hausse"

    if score <= -0.18:
        return "baisse"

    return "stable"


def ajouter_tendances_demain(lignes, historique, signaux):

    snapshots = historique.get("snapshots", [])
    dernier = snapshots[-1] if snapshots else None
    snapshot_24h = _snapshot_avant(historique, 24)
    snapshot_48h = _snapshot_avant(historique, 48)
    score_marche = _score_marche(signaux)

    for station in lignes:
        station_id = str(station.get("id", ""))

        for carburant in CARBURANTS:
            tendance_cle = f"tendance_demain_{carburant}"
            confiance_cle = f"confiance_demain_{carburant}"
            station[tendance_cle] = "stable"
            station[confiance_cle] = "1"

            if not dernier:
                continue

            actuel = _prix_decimal(station.get(carburant))
            station_24h = (
                _valeur_snapshot_station(
                    snapshot_24h,
                    station_id,
                    carburant
                )
                if snapshot_24h
                else None
            )
            station_48h = (
                _valeur_snapshot_station(
                    snapshot_48h,
                    station_id,
                    carburant
                )
                if snapshot_48h
                else None
            )
            national_actuel = (
                dernier.get("national", {}).get(carburant)
            )
            national_24h = (
                snapshot_24h.get("national", {}).get(carburant)
                if snapshot_24h
                else None
            )

            signaux_disponibles = 0
            score = 0
            poids = 0

            if actuel is not None and station_24h is not None:
                delta = actuel - station_24h
                score += max(-1, min(1, delta / 0.012)) * 0.40
                poids += 0.40
                signaux_disponibles += 1

            if station_24h is not None and station_48h is not None:
                delta = station_24h - station_48h
                score += max(-1, min(1, delta / 0.012)) * 0.20
                poids += 0.20
                signaux_disponibles += 1

            if national_actuel is not None and national_24h is not None:
                delta = national_actuel - national_24h
                score += max(-1, min(1, delta / 0.008)) * 0.25
                poids += 0.25
                signaux_disponibles += 1

            score += score_marche * 0.15
            poids += 0.15

            if poids:
                score /= poids

            confiance = min(
                5,
                max(
                    1,
                    int(
                        1
                        + signaux_disponibles
                        + min(1, abs(score) * 1.2)
                    )
                )
            )

            station[tendance_cle] = _classer_score(score, confiance)
            station[confiance_cle] = str(confiance)


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
    lignes = [
        station
        for station in lignes
        if str(station.get("id", "")) not in STATIONS_EXCLUES
    ]

    if not lignes:

        raise RuntimeError(
            "Aucune station trouvee dans les donnees officielles."
        )

    references = mettre_a_jour_references_9h(lignes)
    ajouter_tendances(lignes, references)
    historique = mettre_a_jour_historique_prix(lignes)
    signaux_marche = recuperer_signaux_marche()
    ajouter_tendances_demain(lignes, historique, signaux_marche)
    appliquer_enrichissements(lignes)
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


