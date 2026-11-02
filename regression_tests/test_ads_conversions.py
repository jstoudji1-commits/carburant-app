import copy
import hashlib
import time
import unittest
from http.cookies import SimpleCookie
from unittest.mock import patch
from starlette.requests import Request
from starlette.responses import Response
import main
import ads_tracking


def request(consent='granted', cookies=''):
    return Request({'type':'http','method':'GET','scheme':'https','path':'/api/compte/validation-email','server':('testserver',443),'client':('127.0.0.1',1),'query_string':b'', 'headers':[(b'cookie',('optiplein_ads_consent='+consent+'; '+cookies).encode())]})

class AdsConversionsTests(unittest.TestCase):
    def test_both_validation_routes_issue_anonymous_receipt_only_on_success(self):
        for kind in ('compte','testeur'):
            user={'email':'person@example.com','email_verified':False,'email_verification_hash':hashlib.sha256(b'valid').hexdigest(),'email_verification_expires_at':time.time()+1000}
            data={'users':{'person@example.com':user}} if kind=='compte' else {'testeurs':[user]}
            loader='charger_comptes_utilisateurs' if kind=='compte' else 'charger_testeurs_landing'
            saver='enregistrer_comptes_utilisateurs' if kind=='compte' else 'enregistrer_testeurs_landing'
            route=main.valider_email_compte if kind=='compte' else main.valider_email_testeur
            with patch.object(main,loader,return_value=data),patch.object(main,saver),patch.object(main,'synchroniser_meta_securite'),patch.object(main,'envoyer_email_bienvenue_testeur'):
                with self.assertRaises(main.HTTPException):route('wrong',request())
                result=route('valid',request())
                self.assertEqual(result.status_code,303)
                jar=SimpleCookie();jar.load(result.headers['set-cookie'])
                cookie=jar[ads_tracking.receipt_cookie(kind)]
                self.assertTrue(cookie['httponly']);self.assertTrue(cookie['secure'])
                receipt=ads_tracking.read_receipt(cookie.value,main.secret_session_compte())
                self.assertEqual(receipt['kind'],kind)
                self.assertNotIn('person',str(receipt));self.assertEqual(len(receipt['id']),32)
                with self.assertRaises(main.HTTPException):route('valid',request())
    def test_refusal_sets_no_tracking_receipt(self):
        response=ads_tracking.mark_validation(Response(),request('denied'),'compte',b'secret')
        self.assertNotIn('set-cookie',response.headers)
    def test_tamper_expiry_and_consent(self):
        receipt=ads_tracking.encode_receipt('testeur',main.secret_session_compte())
        self.assertIsNone(ads_tracking.read_receipt(receipt+'x',main.secret_session_compte()))
        with patch.object(ads_tracking.time,'time',return_value=time.time()+90000):
            self.assertIsNone(ads_tracking.read_receipt(receipt,main.secret_session_compte()))
        cookies=ads_tracking.receipt_cookie('testeur')+'='+receipt
        response=Response()
        self.assertEqual(main.conversions_ads_validees(request('denied',cookies),response),{'conversions':[]})
        result=main.conversions_ads_validees(request('granted',cookies),response)
        self.assertEqual(len(result['conversions']),1)
        self.assertEqual(response.headers['cache-control'],'no-store')
        # A success URL alone is not proof of registration.
        self.assertEqual(main.conversions_ads_validees(request(),Response()),{'conversions':[]})
