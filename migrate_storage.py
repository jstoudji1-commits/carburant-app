import argparse
import json
from pathlib import Path

from optiplein_db import (
    base_donnees_active,
    charger_comptes,
    charger_corrections_stations,
    charger_testeurs,
    enregistrer_comptes,
    enregistrer_correction_station,
    enregistrer_testeurs,
)


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(__import__("os").getenv("OPTIPLEIN_DATA_DIR", "/var/data"))


def _lire_json(path, defaut):

    if not path.exists():
        return defaut

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return defaut


def _ecrire_json(path, donnees):

    path.parent.mkdir(parents=True, exist_ok=True)
    temporaire = path.with_suffix(".tmp")
    temporaire.write_text(
        json.dumps(donnees, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporaire.replace(path)


def verifier_postgres():

    if not base_donnees_active():
        raise SystemExit(
            "DATABASE_URL n'est pas configure ou les dependances SQLAlchemy "
            "ne sont pas installees."
        )


def importer_json_vers_postgres(force=False):

    verifier_postgres()
    comptes_existants = charger_comptes() or {"users": {}}
    testeurs_existants = charger_testeurs() or {"testeurs": []}
    corrections_existantes = charger_corrections_stations() or {"stations": {}}

    if (
        not force
        and (
            comptes_existants.get("users")
            or testeurs_existants.get("testeurs")
            or corrections_existantes.get("stations")
        )
    ):
        raise SystemExit(
            "Import annule : la base PostgreSQL contient deja des donnees. "
            "Utilisez --force uniquement apres avoir exporte une sauvegarde."
        )

    comptes = _lire_json(DATA_DIR / "comptes_utilisateurs.json", {"users": {}})
    testeurs = _lire_json(DATA_DIR / "testeurs_landing.json", {"testeurs": []})
    corrections = _lire_json(
        DATA_DIR / "stations_admin_overrides.json",
        {"stations": {}},
    )

    enregistrer_comptes(comptes)
    enregistrer_testeurs(testeurs)

    for station_id, correction in corrections.get("stations", {}).items():
        enregistrer_correction_station(station_id, correction)

    print(
        "Import termine : "
        f"{len(comptes.get('users', {}))} comptes, "
        f"{len(testeurs.get('testeurs', []))} testeurs, "
        f"{len(corrections.get('stations', {}))} corrections stations."
    )


def exporter_postgres_vers_json():

    verifier_postgres()
    comptes = charger_comptes() or {"users": {}}
    testeurs = charger_testeurs() or {"testeurs": []}
    corrections = charger_corrections_stations() or {"stations": {}}

    _ecrire_json(DATA_DIR / "comptes_utilisateurs.json", comptes)
    _ecrire_json(DATA_DIR / "comptes_utilisateurs.backup.json", comptes)
    _ecrire_json(DATA_DIR / "testeurs_landing.json", testeurs)
    _ecrire_json(DATA_DIR / "stations_admin_overrides.json", corrections)

    print(
        "Export termine : "
        f"{len(comptes.get('users', {}))} comptes, "
        f"{len(testeurs.get('testeurs', []))} testeurs, "
        f"{len(corrections.get('stations', {}))} corrections stations."
    )


def main():

    parseur = argparse.ArgumentParser(
        description="Migration reversible du stockage OptiPlein."
    )
    parseur.add_argument(
        "action",
        choices=("import-json", "export-json"),
    )
    parseur.add_argument(
        "--force",
        action="store_true",
        help="Autorise l'import JSON meme si PostgreSQL contient deja des donnees.",
    )
    arguments = parseur.parse_args()

    if arguments.action == "import-json":
        importer_json_vers_postgres(arguments.force)
    else:
        exporter_postgres_vers_json()


if __name__ == "__main__":
    main()
