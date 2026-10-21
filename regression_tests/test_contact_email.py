"""Outbound contact addresses; providers are mocked, no email is sent."""
from email.message import EmailMessage
import unittest
from unittest.mock import Mock, patch

import main


class ContactEmailTests(unittest.TestCase):
    def test_automatic_emails_reply_to_contact(self):
        with patch.object(main, "lire_configuration_email_api", return_value={"brevo_api_key": ""}), patch.object(main, "envoyer_email_smtp") as smtp:
            main.envoyer_email_validation_compte("tester@example.com", "https://example.com/validate", "https://example.com")
        message = smtp.call_args.args[0]
        self.assertEqual(message["Reply-To"], "contact@optiplein.fr")
        self.assertEqual(message["To"], "tester@example.com")

    def test_contact_form_keeps_the_visitors_reply_address(self):
        with patch.object(main, "EMAIL_SIGNALEMENT", "contact@optiplein.fr"), patch.object(main, "lire_configuration_email_api", return_value={"brevo_api_key": ""}), patch.object(main, "envoyer_email_smtp") as smtp:
            main.envoyer_contact_email(main.MessageContact(
                nom="Test", email="visitor@example.com", sujet="Question de test",
                message="Message de test sans envoi réel.",
            ))
        message = smtp.call_args.args[0]
        self.assertEqual(message["To"], "contact@optiplein.fr")
        self.assertEqual(message["Reply-To"], "visitor@example.com")

    def test_brevo_preserves_reply_to(self):
        for reply in ("contact@optiplein.fr", "visitor@example.com"):
            with self.subTest(reply=reply):
                message = EmailMessage()
                message["To"] = "tester@example.com"
                message["Subject"] = "Test"
                message["Reply-To"] = reply
                message.set_content("Test sans envoi réel.")
                with patch.object(main, "lire_configuration_smtp", return_value={"from": "contact@optiplein.fr"}), patch.object(main.http_requests, "post", return_value=Mock(status_code=201)) as post:
                    main.envoyer_email_brevo(message, "fake-test-key")
                payload = post.call_args.kwargs["json"]
                self.assertEqual(payload["replyTo"], {"email": reply})
                self.assertEqual(payload["sender"], {"email": "contact@optiplein.fr"})


if __name__ == "__main__":
    unittest.main()
