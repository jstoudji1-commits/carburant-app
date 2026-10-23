import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from starlette.requests import Request
import main

class AdminUsersTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.accounts={'users':{
            'admin-test@example.com':{'password':{'hash':'SECRET'},'updated_at':'v1','email_verified':False,
                'email_verification_hash':'TOKEN','data':{'plan':'free','profil':{'nom':'Test'},
                'parrainage':{'code':'TESTCODE'},'historique_economies':[{'economie':12.5}],
                'abonnement_apple':{'transaction_id':'PRIVATE','product_id':'premium','expiration_date':'2027-01-01'}}},
            'child@example.com':{'data':{'parrainage':{'parrain_code':'TESTCODE'}}}}}
        for target,value in [('DOSSIER_DONNEES_UTILISATEURS',Path(self.tmp.name))]:
            p=patch.object(main,target,value);p.start();self.addCleanup(p.stop)
        p=patch.object(main,'base_donnees_active',return_value=False);p.start();self.addCleanup(p.stop)
    def payload(self, **changes):
        fields=dict(email='admin-test@example.com',version='v1',nom='Modifie',ville='',telephone='',
            plan='premium',email_verified=True,bonus_until='2027-01-01T00:00:00+01:00',note='Interne',motif='Correction support')
        fields.update(changes);return main.AdminFicheUtilisateur(**fields)
    def test_detail_safe_and_referrals_complete(self):
        result=main.fiche_utilisateur_admin('admin-test@example.com',self.accounts)
        self.assertEqual(result['statistiques']['economies_total'],12.5)
        self.assertEqual(result['filleuls_comptes'][0]['email'],'child@example.com')
        self.assertNotIn('SECRET',str(result));self.assertNotIn('TOKEN',str(result));self.assertNotIn('PRIVATE',str(result))
    def test_update_preserves_other_data_and_logs(self):
        original=copy.deepcopy(self.accounts['users']['admin-test@example.com']['data'])
        with patch.object(main,'verifier_admin'),patch.object(main,'charger_comptes_utilisateurs',return_value=self.accounts),patch.object(main,'enregistrer_comptes_utilisateurs') as save:
            result=main.modifier_fiche_utilisateur_admin(self.payload(),None)
        save.assert_called_once();self.assertEqual(result['note'],'Interne');self.assertEqual(len(result['journal']),1)
        user=self.accounts['users']['admin-test@example.com']
        self.assertEqual(user['data']['historique_economies'],original['historique_economies'])
        self.assertEqual(user['data']['abonnement_apple'],original['abonnement_apple'])
        self.assertNotIn('email_verification_hash',user)
        self.assertNotIn('admin_note',user['data'])
    def test_stale_and_bad_date_do_not_write(self):
        for values in [{'version':'stale'},{'bonus_until':'invalid'},{'bonus_until':'2027-01-01'}]:
            with patch.object(main,'verifier_admin'),patch.object(main,'charger_comptes_utilisateurs',return_value=self.accounts),patch.object(main,'enregistrer_comptes_utilisateurs') as save:
                with self.assertRaises(main.HTTPException):main.modifier_fiche_utilisateur_admin(self.payload(**values),None)
                save.assert_not_called()
    def test_direct_password_header_cannot_access_admin(self):
        request=Request({'type':'http','client':('8.8.8.8',1),'headers':[(b'x-admin-password',b'password'),(b'x-admin-request',b'1')]})
        with self.assertRaises(main.HTTPException):main.lire_fiche_utilisateur_admin(request,'admin-test@example.com')
    def test_metadata_postgres_separate_from_customer_data(self):
        with patch.object(main,'base_donnees_active',return_value=True),patch.object(main,'enregistrer_donnee_application_postgres') as write,patch.object(main,'charger_donnee_application_postgres',return_value={'note':'private'}):
            main.ecrire_metadonnees_admin('a@b.fr',{'note':'private'})
            self.assertEqual(main.lire_metadonnees_admin('a@b.fr')['note'],'private')
            write.assert_called_once()

if __name__=='__main__':unittest.main()
