import tempfile
import unittest
from pathlib import Path
from admin_auth import AdminAuth, AuthError

class RememberBrowserTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory(); self.addCleanup(self.folder.cleanup)
        self.now=1000000; self.codes=[]
        self.auth=AdminAuth(Path(self.folder.name)/'auth.db','password',lambda:self.now)
    def start(self,browser='browserA',password='password'):
        return self.auth.start(password,'unverified:proxy2',False,lambda code,ip:self.codes.append(code),browser)
    def verify(self,remember=True):
        result=self.start()
        return self.auth.verify(result['challenge'],self.codes[-1],'unverified:proxy3',remember,'browserA')
    def test_remember_survives_logout_restart_and_expires(self):
        token=self.verify(); self.auth.logout(token)
        self.now+=29*86400
        self.auth=AdminAuth(self.auth.path,'password',lambda:self.now)
        result=self.start(); self.assertFalse(result['requires_code'])
        self.auth.validate(result['token'],'unverified:proxy4','browserA')
        self.assertEqual(len(self.codes),1)
        self.now+=86400
        self.assertTrue(self.start()['requires_code'])
    def test_unchecked_new_browser_missing_cookie_and_forget_require_code(self):
        self.verify(False); self.assertTrue(self.start()['requires_code'])
        self.now+=601; token=self.verify()
        self.assertTrue(self.start('browserB')['requires_code'])
        self.assertTrue(self.start(None)['requires_code'])
        self.auth.forget(token); self.now+=601
        self.assertTrue(self.start()['requires_code'])
    def test_password_and_backoff_still_required_for_remembered_browser(self):
        self.verify()
        for _ in range(3):
            with self.assertRaises(AuthError):self.start(password='wrong')
        with self.assertRaises(AuthError) as error:self.start()
        self.assertEqual(error.exception.status,429)
        self.now+=60
        self.assertFalse(self.start()['requires_code'])
    def test_new_verified_ip_still_requires_code(self):
        self.verify()
        result=self.auth.start('password','1.1.1.1',True,lambda code,ip:self.codes.append(code),'browserA')
        self.assertTrue(result['requires_code'])
