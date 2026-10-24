import tempfile
import unittest
from http.cookies import SimpleCookie
from pathlib import Path
from unittest.mock import patch
from fastapi import Response
from starlette.requests import Request
import main

class AdminProxyFlowTests(unittest.TestCase):
    def test_email_code_and_session_survive_render_proxy_change(self):
        def request(peer, cookies=''):
            return Request({'type':'http','method':'POST','scheme':'https','path':'/api/admin/auth/code',
                'server':('www.optiplein.fr',443),'client':(peer,1234),
                'headers':[(b'host',b'www.optiplein.fr'),(b'x-admin-request',b'1'),
                           (b'x-forwarded-for',b'8.8.8.8'),(b'cookie',cookies.encode())]})
        codes=[]
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(main,'DOSSIER_DONNEES_UTILISATEURS',Path(folder)), \
             patch.object(main,'ADMIN_PASSWORD','test-password'), \
             patch.dict(main.os.environ,{'ADMIN_TRUSTED_PROXY_CIDRS':''}), \
             patch.object(main,'envoyer_code_admin',side_effect=lambda code,ip:codes.append(code)):
            response=Response()
            result=main.connexion_admin_auth(main.AdminConnexion(mot_de_passe='test-password'),request('10.0.0.1'),response)
            self.assertTrue(result['requires_code'])
            jar=SimpleCookie()
            for header in response.headers.getlist('set-cookie'):jar.load(header)
            browser=jar['optiplein_admin_browser']
            self.assertTrue(browser['httponly']);self.assertTrue(browser['secure'])
            cookies='optiplein_admin_browser='+browser.value
            response=Response()
            verified=main.verifier_code_admin(main.AdminCodeConnexion(challenge=result['challenge'],code=codes[0]),request('10.0.0.2',cookies),response)
            self.assertTrue(verified['ok'])
            for header in response.headers.getlist('set-cookie'):jar.load(header)
            cookies+='; optiplein_admin='+jar['optiplein_admin'].value
            main.verifier_admin(request('10.0.0.3',cookies))
            with self.assertRaises(main.HTTPException):
                main.verifier_admin(request('10.0.0.3','optiplein_admin='+jar['optiplein_admin'].value))

if __name__=='__main__':unittest.main()
