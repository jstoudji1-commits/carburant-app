"""Tests pour l'authentification et la gestion des comptes."""
import pytest
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import (
    normaliser_email,
    email_valide,
    hasher_mot_de_passe,
    verifier_mot_de_passe,
    creer_session,
    email_depuis_session_signee,
    secret_session_compte,
)


class TestEmailValidation:
    """Tests pour la validation d'email."""

    def test_normaliser_email(self):
        """Test normalisation d'email."""
        assert normaliser_email("  TEST@EXAMPLE.COM  ") == "test@example.com"
        assert normaliser_email("User@Gmail.COM") == "user@gmail.com"

    def test_email_valide_valid(self):
        """Test validation d'email valide."""
        assert email_valide("test@example.com") is True
        assert email_valide("user.name+tag@example.co.uk") is True

    def test_email_valide_invalid(self):
        """Test validation d'email invalide."""
        assert email_valide("invalid") is False
        assert email_valide("@example.com") is False
        assert email_valide("test@") is False
        assert email_valide("") is False
        assert email_valide("test @example.com") is False


class TestPasswordHashing:
    """Tests pour le hachage de mot de passe."""

    def test_hasher_mot_de_passe(self):
        """Test hachage de mot de passe."""
        password = "MySecurePassword123!"
        hashed = hasher_mot_de_passe(password)

        assert "salt" in hashed
        assert "hash" in hashed
        assert "iterations" in hashed
        assert hashed["iterations"] == 260000

    def test_hasher_mot_de_passe_avec_sel(self):
        """Test hachage avec sel fourni."""
        password = "TestPassword"
        salt = "test_salt_12345"
        hashed = hasher_mot_de_passe(password, salt)

        assert hashed["salt"] == salt

    def test_verifier_mot_de_passe_correct(self):
        """Test vérification de mot de passe correct."""
        password = "CorrectPassword123"
        hashed = hasher_mot_de_passe(password)

        assert verifier_mot_de_passe(password, hashed) is True

    def test_verifier_mot_de_passe_incorrect(self):
        """Test vérification de mot de passe incorrect."""
        password = "CorrectPassword123"
        wrong_password = "WrongPassword456"
        hashed = hasher_mot_de_passe(password)

        assert verifier_mot_de_passe(wrong_password, hashed) is False

    def test_verifier_mot_de_passe_vide(self):
        """Test vérification avec hash vide."""
        hashed_vide = {"salt": "", "hash": "", "iterations": 260000}
        assert verifier_mot_de_passe("any_password", hashed_vide) is False


class TestSessionManagement:
    """Tests pour la gestion des sessions JWT."""

    def test_creer_session(self):
        """Test création de session."""
        email = "test@example.com"
        token = creer_session(email)

        assert token is not None
        assert token.startswith("v1.")
        assert token.count(".") == 2

    def test_email_depuis_session_signee_valid(self):
        """Test extraction d'email depuis session valide."""
        email = "test@example.com"
        token = creer_session(email)
        extracted_email = email_depuis_session_signee(token)

        assert extracted_email == email

    def test_email_depuis_session_signee_invalid_format(self):
        """Test extraction avec format invalide."""
        assert email_depuis_session_signee("invalid.format") is None
        assert email_depuis_session_signee("too.many.dots.here") is None
        assert email_depuis_session_signee("") is None

    def test_email_depuis_session_signee_invalid_version(self):
        """Test extraction avec version invalide."""
        # Forcer une version incorrecte
        token = "v2.invalid.signature"
        assert email_depuis_session_signee(token) is None

    def test_email_depuis_session_signee_tampered(self):
        """Test détection de session modifiée."""
        email = "test@example.com"
        token = creer_session(email)
        parts = token.split(".")

        # Modifier le corps
        tampered_token = f"{parts[0]}.modified_body.{parts[2]}"
        assert email_depuis_session_signee(tampered_token) is None

    def test_secret_session_compte(self):
        """Test génération du secret de session."""
        secret = secret_session_compte()
        assert isinstance(secret, bytes)
        assert len(secret) > 0
