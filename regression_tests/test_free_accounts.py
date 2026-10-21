"""Account regression checks. Storage and email are replaced with in-memory mocks.

Run from the repository: python -m unittest discover -s regression_tests -v
"""
import copy
from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from starlette.requests import Request

import main


def request(platform, token=None):
    headers = [(b"x-optiplein-platform", platform.encode())]
    if token:
        headers.append((b"authorization", f"Bearer {token}".encode()))
    return Request({
        "type": "http", "method": "GET", "path": "/", "root_path": "",
        "scheme": "https", "server": ("testserver", 443),
        "client": ("127.0.0.1", 1234), "headers": headers,
        "query_string": b"",
    })


class FreeAccountTests(unittest.TestCase):
    def setUp(self):
        self.accounts = {"users": {}}
        for name, kwargs in (
            ("charger_comptes_utilisateurs", {"side_effect": lambda: copy.deepcopy(self.accounts)}),
            ("enregistrer_comptes_utilisateurs", {"side_effect": self.save}),
            ("envoyer_email", {}),
            ("verifier_limite_action", {}),
        ):
            patcher = patch.object(main, name, **kwargs)
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)
        patcher = patch.dict(main.SESSIONS_UTILISATEURS, {}, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def save(self, accounts):
        self.accounts = copy.deepcopy(accounts)

    def signup(self, platform):
        credentials = main.CompteIdentifiants(
            email=f"new-{platform}@example.com",
            mot_de_passe="Account-regression-123!",
            plateforme=platform,
        )
        result = main.creer_compte(credentials, request(platform))
        self.assertTrue(result["verification_required"])
        return credentials

    def assert_free(self, data):
        self.assertEqual(data["plan"], "free")
        self.assertFalse(data["premium"]["active"])
        limits = data["premium"]["limites"]
        self.assertEqual(limits["favoris_max"], 3)
        self.assertEqual(limits["vehicules_max"], 1)
        self.assertEqual(limits["recalcul_secondes"], 180)
        self.assertFalse(limits["longs_trajets"])

    def test_signup_validation_login_and_save_remain_free_on_all_platforms(self):
        for platform in ("web", "android", "ios"):
            with self.subTest(platform=platform):
                credentials = self.signup(platform)
                self.assert_free(self.accounts["users"][credentials.email]["data"])
                message = self.envoyer_email.call_args.args[0]
                content = message.get_body(preferencelist=("plain",)).get_content()
                self.assertIn("compte gratuit", content)
                self.assertNotIn("Premium", content)
                link = next(line for line in content.splitlines() if "?token=" in line)
                token = parse_qs(urlparse(link).query)["token"][0]
                sent = self.envoyer_email.call_count
                response = main.valider_email_compte(token, request(platform))
                self.assertEqual(response.status_code, 303)
                self.assertEqual(self.envoyer_email.call_count, sent)
                login = main.connecter_compte(credentials, request(platform))
                self.assert_free(login["donnees"])
                authenticated = request(platform, login["token"])
                self.assert_free(main.lire_donnees_compte(authenticated)["donnees"])
                # A stale/modified browser must not grant Premium when saving.
                forged = main.SauvegardeCompte(donnees=main.DonneesCompte(
                    plan="premium", premium={"active": True},
                    abonnement_apple={"product_id": main.APPLE_PREMIUM_PRODUCT_ID},
                    parrainage={"bonus_until": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()},
                ))
                self.assert_free(main.sauvegarder_donnees_compte(forged, authenticated)["donnees"])
                with self.assertRaises(main.HTTPException) as denied:
                    main.compte_premium_requis(authenticated)
                self.assertEqual(denied.exception.status_code, 403)

    def test_repeated_signup_resets_unverified_legacy_account_to_free(self):
        credentials = self.signup("android")
        self.accounts["users"][credentials.email]["data"]["plan"] = "premium"
        main.creer_compte(credentials, request("android"))
        self.assert_free(self.accounts["users"][credentials.email]["data"])

    def test_existing_premium_is_preserved_across_platforms(self):
        for platform in ("web", "android", "ios"):
            with self.subTest(platform=platform):
                data = main.limiter_donnees_compte(main.DonneesCompte(plan="premium"), platform)
                result = main.donnees_compte_pour_client(data, platform)
                self.assertEqual(result["plan"], "premium")
                self.assertTrue(result["premium"]["active"])
                self.assertEqual(result["premium"]["limites"]["vehicules_max"], 5)

    def test_referral_bonus_only_grants_premium_while_active(self):
        for days in (-1, 1):
            data = {"plan": "free", "parrainage": {
                "bonus_until": (datetime.now(timezone.utc) + timedelta(days=days)).isoformat(),
            }}
            self.assertEqual(main.premium_actif_donnees(data), days > 0)

    def test_public_architecture_uses_free_limits(self):
        for platform in ("web", "android", "ios"):
            result = main.architecture_premium(request(platform))
            self.assertFalse(result["limites"]["premium_actif"])
            self.assertEqual(result["limites"]["favoris_max"], 3)
            self.assertEqual(result["prix"], "4,99 €/an")

    def test_verified_apple_purchase_still_activates_premium(self):
        credentials = self.signup("ios")
        self.accounts["users"][credentials.email]["email_verified"] = True
        authenticated = request("ios", main.creer_session(credentials.email))
        with patch.object(main, "verifier_transaction_apple_premium", return_value={"transaction_id": "test-purchase"}):
            result = main.activer_premium_apple(main.AchatApplePremium(
                product_id=main.APPLE_PREMIUM_PRODUCT_ID,
                transaction_id="test-purchase",
            ), authenticated)
        self.assertEqual(result["plan"], "premium")
        self.assertTrue(result["donnees"]["premium"]["active"])


if __name__ == "__main__":
    unittest.main()
