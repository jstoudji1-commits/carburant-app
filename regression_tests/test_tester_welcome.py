"""Tester welcome lifecycle; no real messages or user files are touched."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from starlette.requests import Request
import main


def request():
    return Request({
        "type": "http", "method": "GET", "path": "/", "root_path": "",
        "scheme": "https", "server": ("testserver", 443),
        "client": ("127.0.0.1", 1234), "headers": [], "query_string": b"",
    })


class TesterWelcomeTests(unittest.TestCase):
    def setUp(self):
        self.token = "tester-validation-token"
        self.data = {"testeurs": [{
            "email": "tester@gmail.com",
            "email_verified": False,
            "email_verification_hash": hashlib.sha256(self.token.encode()).hexdigest(),
            "email_verification_expires_at": time.time() + 86400,
        }]}
        for name, kwargs in (
            ("charger_testeurs_landing", {"side_effect": lambda: copy.deepcopy(self.data)}),
            ("enregistrer_testeurs_landing", {"side_effect": self.save}),
            ("envoyer_email", {}),
        ):
            patcher = patch.object(main, name, **kwargs)
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)

    def save(self, data):
        self.data = copy.deepcopy(data)

    def test_validation_sends_approved_welcome_after_saving_and_only_once(self):
        def check_saved(message):
            self.assertTrue(self.data["testeurs"][0]["email_verified"])
            self.assertNotIn("email_verification_hash", self.data["testeurs"][0])
        self.envoyer_email.side_effect = check_saved
        result = main.valider_email_testeur(self.token, request())
        self.assertEqual(result.status_code, 303)
        self.assertEqual(result.headers["location"], "/landing?testeur_valide=1#devenir-testeur")
        message = self.envoyer_email.call_args.args[0]
        self.assertEqual(message["Subject"], "Bienvenue parmi les testeurs Android OptiPlein !")
        self.assertEqual(message["To"], "tester@gmail.com")
        self.assertEqual(message["Reply-To"], "contact@optiplein.fr")
        for kind in ("plain", "html"):
            content = message.get_body(preferencelist=(kind,)).get_content()
            self.assertIn("contact@optiplein.fr", content)
            self.assertNotIn("optiplein5@gmail.com", content)
            self.assertIn("de la formule gratuite", content)
            self.assertIn("À la fin de la période de recrutement", content)
            self.assertIn("L’inscription comme testeur est distincte", content)
        self.assertIn("bienvenue_email_sent_at", self.data["testeurs"][0])
        with self.assertRaises(main.HTTPException) as error:
            main.valider_email_testeur(self.token, request())
        self.assertEqual(error.exception.status_code, 400)
        self.envoyer_email.assert_called_once()

    def test_expired_or_invalid_token_sends_nothing(self):
        for token, expiration, status in (
            ("wrong-token", time.time() + 86400, 400),
            (self.token, time.time() - 10, 410),
        ):
            with self.subTest(status=status):
                self.data["testeurs"][0]["email_verification_expires_at"] = expiration
                with self.assertRaises(main.HTTPException) as error:
                    main.valider_email_testeur(token, request())
                self.assertEqual(error.exception.status_code, status)
                self.assertFalse(self.data["testeurs"][0]["email_verified"])
        self.envoyer_email.assert_not_called()

    def test_mail_failure_does_not_undo_validation(self):
        self.envoyer_email.side_effect = RuntimeError("Simulated email provider outage")
        with self.assertLogs(main.logger, level="ERROR"):
            result = main.valider_email_testeur(self.token, request())
        self.assertEqual(result.status_code, 303)
        tester = self.data["testeurs"][0]
        self.assertTrue(tester["email_verified"])
        self.assertIn("bienvenue_email_error_at", tester)
        self.assertNotIn("bienvenue_email_sent_at", tester)

    def test_recorded_welcome_is_not_sent_again(self):
        self.data["testeurs"][0]["bienvenue_email_sent_at"] = "2026-10-21T12:00:00Z"
        main.valider_email_testeur(self.token, request())
        self.envoyer_email.assert_not_called()

    def test_registration_only_sends_validation_message(self):
        self.data = {"testeurs": []}
        main.inscrire_testeur(main.InscriptionTesteur(email="newtester@gmail.com"), request())
        self.envoyer_email.assert_called_once()
        message = self.envoyer_email.call_args.args[0]
        self.assertEqual(message["Subject"], "Validez votre inscription testeur Android OptiPlein")
        self.assertFalse(self.data["testeurs"][0]["email_verified"])

    def test_welcome_tracking_survives_validation_metadata_roundtrip(self):
        self.data["testeurs"][0].update({
            "bienvenue_email_sent_at": "2026-10-21T12:00:00Z",
            "bienvenue_email_error_at": "2026-10-21T11:00:00Z",
        })
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "testeurs_validation.json"
            with patch.object(main, "TESTEURS_VALIDATION_FICHIER", path):
                main.enregistrer_validations_testeurs_landing(self.data)
                loaded = main.appliquer_validations_testeurs_landing({"testeurs": [{"email": "tester@gmail.com"}]})
        tester = loaded["testeurs"][0]
        self.assertEqual(tester["bienvenue_email_sent_at"], "2026-10-21T12:00:00Z")
        self.assertEqual(tester["bienvenue_email_error_at"], "2026-10-21T11:00:00Z")


if __name__ == "__main__":
    unittest.main()
