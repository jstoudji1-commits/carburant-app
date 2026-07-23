"""Script de migration des données JSON vers PostgreSQL."""
import json
import csv
from pathlib import Path
from datetime import datetime, timezone
import sys
import os
from sqlalchemy.orm import Session

# Import models
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from models import (
    User,
    Station,
    Tester,
    get_database_url,
    create_db_engine,
    Base,
)


def migrate_users_from_json(db: Session, json_file: Path) -> int:
    """Migre les utilisateurs depuis le fichier JSON."""
    if not json_file.exists():
        print(f"⚠️  Fichier utilisateurs non trouvé: {json_file}")
        return 0

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    users_data = data.get("users", {})
    count = 0

    for email, user_info in users_data.items():
        # Vérifier si l'utilisateur existe déjà
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"⏭️  Utilisateur déjà existant: {email}")
            continue

        password_info = user_info.get("password", {})
        user_data = user_info.get("data", {})

        user = User(
            email=email,
            password_salt=password_info.get("salt", ""),
            password_hash=password_info.get("hash", ""),
            password_iterations=password_info.get("iterations", 260000),
            email_verified=user_info.get("email_verified", False),
            email_verification_hash=user_info.get("email_verification_hash"),
            email_verification_expires_at=user_info.get("email_verification_expires_at"),
            created_at=datetime.fromisoformat(
                user_info.get("created_at", "").replace("Z", "+00:00")
            ) if user_info.get("created_at") else datetime.now(timezone.utc),
            updated_at=datetime.fromisoformat(
                user_info.get("updated_at", "").replace("Z", "+00:00")
            ) if user_info.get("updated_at") else datetime.now(timezone.utc),
            favoris=user_data.get("favoris", []),
            vehicules=user_data.get("vehicules", []),
            vehicule_actif=user_data.get("vehicule_actif", ""),
            plan=user_data.get("plan", "free"),
            historique_economies=user_data.get("historique_economies", []),
            lieux_trajet=user_data.get("lieux_trajet", {}),
            rayon_stations=user_data.get("rayon_stations", 25),
        )
        db.add(user)
        count += 1

    db.commit()
    print(f"✅ {count} utilisateurs migrés")
    return count


def migrate_stations_from_csv(db: Session, csv_file: Path) -> int:
    """Migre les stations depuis le fichier CSV."""
    if not csv_file.exists():
        print(f"⚠️  Fichier stations non trouvé: {csv_file}")
        return 0

    count = 0
    with open(csv_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Vérifier si la station existe déjà
            station_id = row.get("id", "")
            existing = db.query(Station).filter(Station.id == station_id).first()
            if existing:
                continue

            station = Station(
                id=station_id,
                enseigne=row.get("enseigne", ""),
                adresse=row.get("adresse", ""),
                cp=row.get("cp", ""),
                ville=row.get("ville", ""),
                latitude=float(row.get("latitude", 0)),
                longitude=float(row.get("longitude", 0)),
                gazole=row.get("gazole", ""),
                e10=row.get("e10", ""),
                sp98=row.get("sp98", ""),
                tendance_gazole=row.get("tendance_gazole", ""),
                tendance_e10=row.get("tendance_e10", ""),
                tendance_sp98=row.get("tendance_sp98", ""),
                tendance_demain_gazole=row.get("tendance_demain_gazole", ""),
                tendance_demain_e10=row.get("tendance_demain_e10", ""),
                tendance_demain_sp98=row.get("tendance_demain_sp98", ""),
                confiance_demain_gazole=row.get("confiance_demain_gazole", ""),
                confiance_demain_e10=row.get("confiance_demain_e10", ""),
                confiance_demain_sp98=row.get("confiance_demain_sp98", ""),
            )
            db.add(station)
            count += 1

    db.commit()
    print(f"✅ {count} stations migrées")
    return count


def migrate_testers_from_json(db: Session, json_file: Path) -> int:
    """Migre les testeurs depuis le fichier JSON."""
    if not json_file.exists():
        print(f"⚠️  Fichier testeurs non trouvé: {json_file}")
        return 0

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    testers_list = data.get("testeurs", [])
    count = 0

    for tester_info in testers_list:
        email = tester_info.get("email", "")
        # Vérifier si le testeur existe déjà
        existing = db.query(Tester).filter(Tester.email == email).first()
        if existing:
            continue

        tester = Tester(
            email=email,
            source=tester_info.get("source", "landing"),
            ip_address=tester_info.get("ip", ""),
            created_at=datetime.fromisoformat(
                tester_info.get("created_at", "").replace("Z", "+00:00")
            ) if tester_info.get("created_at") else datetime.now(timezone.utc),
            updated_at=datetime.fromisoformat(
                tester_info.get("updated_at", "").replace("Z", "+00:00")
            ) if tester_info.get("updated_at") else datetime.now(timezone.utc),
        )
        db.add(tester)
        count += 1

    db.commit()
    print(f"✅ {count} testeurs migrés")
    return count


def run_migration(
    json_accounts: Path = None,
    csv_stations: Path = None,
    json_testers: Path = None,
):
    """Lance la migration complète."""
    print("🔄 Démarrage de la migration vers PostgreSQL...\n")

    engine = create_db_engine()
    print(f"📊 Base de données: {get_database_url()}\n")

    # Créer les tables
    print("📝 Création des tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables créées\n")

    # Créer une session
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Chemins par défaut
        if not json_accounts:
            json_accounts = Path(".") / "comptes_utilisateurs.json"
        if not csv_stations:
            csv_stations = Path(".") / "stations.csv"
        if not json_testers:
            json_testers = Path(".") / "testeurs_landing.json"

        # Migrer les données
        print("👥 Migration des utilisateurs...")
        users_count = migrate_users_from_json(db, json_accounts)
        print()

        print("🏪 Migration des stations...")
        stations_count = migrate_stations_from_csv(db, csv_stations)
        print()

        print("🧪 Migration des testeurs...")
        testers_count = migrate_testers_from_json(db, json_testers)
        print()

        print("=" * 50)
        print("📊 RÉSUMÉ DE LA MIGRATION")
        print("=" * 50)
        print(f"✅ Utilisateurs: {users_count}")
        print(f"✅ Stations: {stations_count}")
        print(f"✅ Testeurs: {testers_count}")
        print("=" * 50)
        print("\n🎉 Migration terminée avec succès!")

    except Exception as e:
        print(f"❌ Erreur lors de la migration: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrer les données vers PostgreSQL")
    parser.add_argument(
        "--accounts",
        type=Path,
        help="Chemin du fichier comptes_utilisateurs.json"
    )
    parser.add_argument(
        "--stations",
        type=Path,
        help="Chemin du fichier stations.csv"
    )
    parser.add_argument(
        "--testers",
        type=Path,
        help="Chemin du fichier testeurs_landing.json"
    )

    args = parser.parse_args()
    run_migration(args.accounts, args.stations, args.testers)
