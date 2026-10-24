import tempfile
import unittest
from pathlib import Path
from starlette.requests import Request
from admin_auth import AdminAuth, AuthError, client_identity

class AdminAuthTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.now=10000
        self.auth=AdminAuth(Path(self.tmp.name)/'auth.db','secret-password',lambda:self.now)
        self.codes=[]
    def start(self, ip='8.8.8.8', reliable=True):
        return self.auth.start('secret-password',ip,reliable,lambda code,ip:self.codes.append(code))
    def login(self):
        challenge=self.start()
        return self.auth.verify(challenge['challenge'],self.codes[-1],'8.8.8.8',True)
    def test_first_ip_needs_code_known_ip_password_only(self):
        token=self.login();self.auth.validate(token,'8.8.8.8')
        self.assertFalse(self.start()['requires_code'])
        self.assertTrue(self.start('1.1.1.1')['requires_code'])
    def test_wrong_password_no_mail(self):
        with self.assertRaises(AuthError):self.auth.start('wrong','8.8.8.8',True,lambda *a:self.fail())
    def test_code_one_use_and_ip_bound(self):
        result=self.start();code=self.codes[-1]
        with self.assertRaises(AuthError):self.auth.verify(result['challenge'],code,'1.1.1.1',True)
        self.auth.verify(result['challenge'],code,'8.8.8.8',True)
        with self.assertRaises(AuthError):self.auth.verify(result['challenge'],code,'8.8.8.8',True)
    def test_five_wrong_codes_lock_challenge(self):
        result=self.start();code=self.codes[-1];wrong='111111' if code!='111111' else '222222'
        for _ in range(5):
            with self.assertRaises(AuthError):self.auth.verify(result['challenge'],wrong,'8.8.8.8',True)
        with self.assertRaises(AuthError):self.auth.verify(result['challenge'],code,'8.8.8.8',True)
    def test_expiry(self):
        result=self.start();self.now+=601
        with self.assertRaises(AuthError):self.auth.verify(result['challenge'],self.codes[-1],'8.8.8.8',True)
    def test_session_ip_logout_and_expiry(self):
        token=self.login()
        with self.assertRaises(AuthError):self.auth.validate(token,'1.1.1.1')
        self.auth.logout(token)
        with self.assertRaises(AuthError):self.auth.validate(token,'8.8.8.8')
        token=self.start()['token'];self.now+=8*3600+1
        with self.assertRaises(AuthError):self.auth.validate(token,'8.8.8.8')
    def test_proxy_unknown_never_trusted(self):
        result=self.start('unverified:abc',False)
        self.auth.verify(result['challenge'],self.codes[-1],'unverified:abc',True)
        self.assertTrue(self.start('unverified:abc',False)['requires_code'])
    def test_forget_and_password_rotation(self):
        token=self.login()
        changed=AdminAuth(self.auth.path,'different',lambda:self.now)
        with self.assertRaises(AuthError):changed.validate(token,'8.8.8.8')
        self.auth.forget(token)
        with self.assertRaises(AuthError):self.auth.validate(token,'8.8.8.8')
        self.assertTrue(self.start()['requires_code'])
    def test_failed_mail_not_authorized(self):
        def fail(*a):raise RuntimeError('mail')
        with self.assertRaises(AuthError):self.auth.start('secret-password','8.8.8.8',True,fail)
        self.assertTrue(self.start()['requires_code'])
    def test_proxy_spoofing(self):
        def req(peer,header=''):
            return Request({'type':'http','client':(peer,123),'headers':[(b'x-forwarded-for',header.encode())] if header else []})
        self.assertEqual(client_identity(req('8.8.8.8')),('8.8.8.8',True))
        self.assertFalse(client_identity(req('1.1.1.1','8.8.8.8'))[1])
        self.assertEqual(client_identity(req('10.0.0.2','8.8.8.8, 1.1.1.1'),'10.0.0.0/24'),('1.1.1.1',True))
        self.assertFalse(client_identity(req('127.0.0.1'))[1])
    def test_login_rate_limit(self):
        for _ in range(10):
            with self.assertRaises(AuthError):self.auth.start('wrong','8.8.8.8',True,lambda *a:None)
        with self.assertRaises(AuthError) as error:self.start()
        self.assertEqual(error.exception.status,429)

    def wrong(self, identity='8.8.8.8'):
        with self.assertRaises(AuthError) as raised:
            self.auth.start('wrong', identity, True, lambda *a:self.fail('Email on bad password'))
        return raised.exception

    def test_backoff_doubles_every_three_failures(self):
        for delay in (60, 120, 240, 480, 960):
            self.assertEqual(self.wrong().status, 401)
            self.assertEqual(self.wrong().status, 401)
            error=self.wrong()
            self.assertEqual(error.status, 429)
            self.assertEqual(error.retry_after, delay)
            self.now += delay

    def test_backoff_blocks_correct_password_until_deadline(self):
        for _ in range(3):self.wrong()
        self.now+=30
        with self.assertRaises(AuthError) as raised:self.start()
        self.assertEqual(raised.exception.retry_after,30)
        self.assertEqual(self.codes,[])
        self.now+=30
        self.assertTrue(self.start()['requires_code'])

    def test_backoff_is_durable_and_attempts_do_not_extend_it(self):
        for _ in range(3):self.wrong()
        self.auth=AdminAuth(self.auth.path,'secret-password',lambda:self.now)
        self.now+=10
        self.assertEqual(self.wrong().retry_after,50)
        self.now+=49.5
        self.assertEqual(self.wrong().retry_after,1)
        self.now+=0.5
        self.assertEqual(self.wrong().status,401)

    def test_other_ip_unaffected_and_trusted_ip_exempt(self):
        self.login()
        for _ in range(3):self.wrong()
        self.assertFalse(self.start()['requires_code'])
        for _ in range(3):self.wrong('1.1.1.1')
        self.assertTrue(self.start('9.9.9.9')['requires_code'])

    def test_mfa_success_resets_but_password_alone_does_not(self):
        for _ in range(3):self.wrong()
        self.now+=60
        result=self.start()
        with self.auth.transaction() as db:
            self.assertEqual(self.auth.read(db,'backoff:'+self.auth.digest('8.8.8.8'))['level'],1)
        self.auth.verify(result['challenge'],self.codes[-1],'8.8.8.8',False)
        for _ in range(2):self.wrong()
        self.assertEqual(self.wrong().retry_after,60)

    def test_proxy_change_keeps_browser_challenge_and_session_valid(self):
        browser='browser-secret'
        result=self.auth.start('secret-password','unverified:proxyA',False,
            lambda code,ip:self.codes.append(code),browser)
        token=self.auth.verify(result['challenge'],self.codes[-1],
            'unverified:proxyB',True,browser)
        self.auth.validate(token,'unverified:proxyC',browser)
        # Proxy fallback must never create an IP exemption from 2FA.
        result=self.auth.start('secret-password','unverified:proxyC',False,
            lambda code,ip:self.codes.append(code),browser)
        self.assertTrue(result['requires_code'])

    def test_browser_binding_cannot_be_omitted_or_replaced(self):
        result=self.auth.start('secret-password','unverified:proxyA',False,
            lambda code,ip:self.codes.append(code),'browserA')
        for browser in (None,'browserB'):
            with self.assertRaises(AuthError):
                self.auth.verify(result['challenge'],self.codes[-1],
                    'unverified:proxyA',True,browser)
        token=self.auth.verify(result['challenge'],self.codes[-1],
            'unverified:proxyB',True,'browserA')
        with self.assertRaises(AuthError):self.auth.validate(token,'unverified:proxyB','browserB')
        with self.assertRaises(AuthError):self.auth.validate(token,'8.8.8.8','browserA')
        with self.assertRaises(AuthError):
            self.auth.verify(result['challenge'],self.codes[-1],'unverified:proxyC',True,'browserA')

    def test_reliable_ip_remains_bound_even_with_same_browser(self):
        result=self.auth.start('secret-password','8.8.8.8',True,
            lambda code,ip:self.codes.append(code),'browserA')
        with self.assertRaises(AuthError):
            self.auth.verify(result['challenge'],self.codes[-1],'1.1.1.1',True,'browserA')
        token=self.auth.verify(result['challenge'],self.codes[-1],'8.8.8.8',True,'browserA')
        with self.assertRaises(AuthError):self.auth.validate(token,'1.1.1.1','browserA')

if __name__=='__main__':unittest.main()
