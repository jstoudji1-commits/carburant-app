import copy
import hashlib
import time
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from starlette.requests import Request
import main

class ReferralSignupTests(unittest.TestCase):
    def setUp(self):
        self.parent={'email_verified':True,'data':{'plan':'free'}}
        self.child={'email_verified':False,'data':{'plan':'free'}}
        self.accounts={'users':{'parent@example.com':self.parent,'child@example.com':self.child}}
        self.code=main.assurer_parrainage_utilisateur(self.parent,'parent@example.com')['code']
        main.enregistrer_code_parrain_inscription(self.accounts,'child@example.com',self.child['data'],self.code)
    def reward(self):
        return main.attribuer_bonus_parrainage_premium(self.accounts,'child@example.com',self.child['data'])
    def test_no_reward_before_validation_then_one_month_each(self):
        self.assertIsNone(self.reward())
        self.assertFalse(main.premium_actif_donnees(self.child['data']))
        self.child['email_verified']=True
        self.assertIsNotNone(self.reward())
        for user in [self.parent,self.child]:
            self.assertEqual(user['data']['plan'],'free')
            self.assertTrue(main.premium_actif_donnees(user['data']))
            referral=user['data']['parrainage']
            self.assertEqual(referral['bonus_mois_total'],1)
            expiry=main.datetime_depuis_valeur_apple(referral['bonus_until'])
            days=(expiry-datetime.now(timezone.utc)).total_seconds()/86400
            self.assertGreater(days,27);self.assertLessEqual(days,31.01)
        self.assertEqual(self.parent['data']['parrainage']['filleuls_en_attente_total'],0)
        snapshot=copy.deepcopy(self.accounts)
        self.assertIsNone(self.reward());self.assertEqual(snapshot,self.accounts)
    def test_accumulation_extends_existing_paid_rights_and_expiry(self):
        expiry='2030-01-31T00:00:00+00:00'
        self.parent['data']['abonnement_apple']={'expiration_date':expiry}
        self.child['email_verified']=True;self.reward()
        self.assertTrue(self.parent['data']['parrainage']['bonus_until'].startswith('2030-02-28'))
        other={'email_verified':True,'data':{'plan':'free'}}
        self.accounts['users']['second@example.com']=other
        main.enregistrer_code_parrain_inscription(self.accounts,'second@example.com',other['data'],self.code)
        main.attribuer_bonus_parrainage_premium(self.accounts,'second@example.com',other['data'])
        self.assertTrue(self.parent['data']['parrainage']['bonus_until'].startswith('2030-03-28'))
        self.assertEqual(self.parent['data']['parrainage']['bonus_mois_total'],2)
        expired={'plan':'free','parrainage':{'bonus_until':'2000-01-01T00:00:00+00:00'}}
        self.assertFalse(main.premium_actif_donnees(expired))
    def test_self_referral_no_code_and_recreated_account(self):
        with self.assertRaises(main.HTTPException):
            main.enregistrer_code_parrain_inscription(self.accounts,'parent@example.com',self.parent['data'],self.code)
        self.child['email_verified']=True;self.reward()
        self.child['data']={'plan':'free','parrainage':{'parrain_code':self.code}}
        self.assertIsNone(self.reward())
        self.child['data']={'plan':'free'}
        self.assertIsNone(self.reward())
    def test_real_validation_endpoint_awards_once_and_invalid_link_never_awards(self):
        self.child.update(email_verification_hash=hashlib.sha256(b'test-token').hexdigest(),email_verification_expires_at=time.time()+1000)
        request=Request({'type':'http','method':'GET','path':'/','scheme':'https','server':('testserver',443),'headers':[]})
        with patch.object(main,'charger_comptes_utilisateurs',return_value=self.accounts),patch.object(main,'enregistrer_comptes_utilisateurs') as save:
            with self.assertRaises(main.HTTPException):main.valider_email_compte('wrong',request)
            save.assert_not_called()
            response=main.valider_email_compte('test-token',request)
            self.assertEqual(response.status_code,303)
            self.assertTrue(main.premium_actif_donnees(self.parent['data']))
            self.assertTrue(main.premium_actif_donnees(self.child['data']))
            save.assert_called_once()
            with self.assertRaises(main.HTTPException):main.valider_email_compte('test-token',request)
            self.assertEqual(self.parent['data']['parrainage']['bonus_mois_total'],1)
