"""Configuration commune pour tous les tests."""
import json
import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from fastapi.testclient import TestClient
import sys
import os

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import après modification du path
from main import app


@pytest.fixture
def client():
    """Client FastAPI pour les tests."""
    return TestClient(app)


@pytest.fixture
def temp_data_dir():
    """Crée un dossier temporaire pour les données de test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_accounts(temp_data_dir):
    """Crée des comptes de test."""
    accounts_file = temp_data_dir / "comptes_utilisateurs.json"
    test_accounts = {
        "users": {
            "test@example.com": {
                "email": "test@example.com",
                "password": {
                    "salt": "test_salt",
                    "hash": "test_hash",
                    "iterations": 260000
                },
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "email_verified": True,
                "data": {
                    "favoris": [],
                    "vehicules": [],
                    "vehicule_actif": "",
                    "plan": "free",
                    "historique_economies": [],
                    "lieux_trajet": {},
                    "rayon_stations": 25
                }
            }
        }
    }
    accounts_file.write_text(json.dumps(test_accounts, indent=2), encoding="utf-8")
    return test_accounts


@pytest.fixture
def mock_stations(temp_data_dir):
    """Crée des stations de test."""
    stations_file = temp_data_dir / "stations.csv"
    csv_content = """id,enseigne,adresse,cp,ville,latitude,longitude,gazole,e10,sp98,tendance_gazole,tendance_e10,tendance_sp98
1,Shell,123 Rue de Paris,75001,Paris,48.8566,2.3522,1.45,1.55,1.65,stable,stable,stable
2,Total,456 Avenue des Champs,75008,Paris,48.8698,2.3073,1.42,1.52,1.62,hausse,stable,baisse
3,Carrefour,789 Boulevard Victor,75015,Paris,48.8382,2.2865,1.40,1.50,1.60,baisse,baisse,hausse
"""
    stations_file.write_text(csv_content, encoding="utf-8")
    return stations_file


@pytest.fixture
def monkeypatch_env(monkeypatch):
    """Configure les variables d'environnement pour les tests."""
    monkeypatch.setenv("ADMIN_PASSWORD", "test-admin-pass")
    monkeypatch.setenv("SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "test@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "test-password")
    monkeypatch.setenv("SMTP_FROM", "test@gmail.com")
    monkeypatch.setenv("OPTIPLEIN_BACKGROUND_UPDATE", "false")
    monkeypatch.setenv("APP_BASE_URL", "https://test.example.com")
