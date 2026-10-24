"""Admin authentication: one-use email challenges and IP-bound revocable sessions."""
import hashlib
import hmac
import ipaddress
import json
import math
import secrets
import sqlite3
import time
from contextlib import contextmanager


class AuthError(Exception):
    def __init__(self, message, status=401, retry_after=None):
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after


def client_identity(request, trusted_cidrs=''):
    peer = request.client.host if request.client else ''
    forwarded = ','.join(request.headers.getlist('x-forwarded-for'))
    networks = [ipaddress.ip_network(x.strip()) for x in trusted_cidrs.split(',') if x.strip()]
    def trusted(value):
        return any(value in network for network in networks)
    try:
        address = ipaddress.ip_address(peer)
        if forwarded:
            if not trusted(address):
                raise ValueError('Proxy non verifie')
            for value in reversed(forwarded.split(',')):
                address = ipaddress.ip_address(value.strip())
                if not trusted(address):
                    break
        if not address.is_global:
            raise ValueError('Adresse publique non determinee')
        return str(address), True
    except ValueError:
        # Never remember a shared proxy/local IP as an administrator's usual IP.
        fingerprint = hashlib.sha256((peer + '|' + forwarded).encode()).hexdigest()
        return 'unverified:' + fingerprint, False


class AdminAuth:
    def __init__(self, path, password, now=time.time):
        self.path, self.password, self.now = path, password, now

    def digest(self, value):
        return hmac.new(self.password.encode(), value.encode(), hashlib.sha256).hexdigest()

    @contextmanager
    def transaction(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=10)
        try:
            db.execute('CREATE TABLE IF NOT EXISTS auth (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def read(self, db, key):
        row = db.execute('SELECT value FROM auth WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else {}

    def write(self, db, key, value):
        db.execute('INSERT OR REPLACE INTO auth VALUES (?,?)', (key, json.dumps(value)))

    def rate(self, identity, action, maximum, window):
        blocked = False
        with self.transaction() as db:
            key = 'rate:' + action + ':' + self.digest(identity)
            recent = [t for t in self.read(db, key).get('times', []) if t > self.now()-window]
            blocked = len(recent) >= maximum
            if not blocked:
                self.write(db, key, {'times': recent + [self.now()]})
        if blocked:
            raise AuthError('Trop de tentatives. Reessayez plus tard.', 429)

    def session(self, db, identity, browser=None):
        token = secrets.token_urlsafe(32)
        self.write(db, 'session:' + self.digest(token), {'identity': self.digest(identity), 'browser': self.digest(browser) if browser else None, 'expires': self.now()+8*3600})
        return token

    def start(self, supplied, identity, reliable, send, browser=None):
        if not self.password:
            raise AuthError('Mot de passe administrateur non configure.', 503)
        self.rate('global', 'login', 100, 600)
        error = None
        known_ip = False
        with self.transaction() as db:
            known = self.read(db, 'trusted:' + self.digest(identity))
            known_ip = reliable and known.get('expires', 0) > self.now()
            key = 'backoff:' + self.digest(identity)
            state = self.read(db, key)
            remaining = math.ceil(state.get('until', 0) - self.now())
            if not known_ip and remaining > 0:
                error = AuthError('Connexion temporairement bloquee. Reessayez dans '
                                  + str(remaining) + ' secondes.', 429, remaining)
            elif not hmac.compare_digest(supplied, self.password):
                error = AuthError('Identifiants incorrects.')
                if not known_ip:
                    failures = state.get('failures', 0) + 1
                    level = state.get('level', 0)
                    if failures >= 3:
                        delay = 60 * (2 ** level)
                        state = {'failures': 0, 'level': level + 1, 'until': self.now() + delay}
                        error = AuthError('Trois mots de passe incorrects. Reessayez dans '
                                          + str(delay) + ' secondes.', 429, delay)
                    else:
                        state['failures'] = failures
                    self.write(db, key, state)
        # Raise only after committing: failed attempts and deadlines must persist.
        if known_ip:
            self.rate(identity, 'login', 10, 600)
        if error:
            raise error
        if known_ip:
            with self.transaction() as db:
                return {'token': self.session(db, identity), 'requires_code': False}
        self.rate('global', 'email', 10, 600)
        self.rate(identity, 'email', 3, 600)
        challenge = secrets.token_urlsafe(32)
        code = str(secrets.randbelow(1000000)).zfill(6)
        with self.transaction() as db:
            self.write(db, 'challenge:' + self.digest(challenge), {
                'identity': self.digest(identity), 'reliable': reliable,
                'browser': self.digest(browser) if browser and not reliable else None,
                'code': self.digest(challenge + ':' + code), 'expires': self.now()+600, 'attempts': 0,
            })
        try:
            send(code, identity if reliable else 'Adresse non verifiee (proxy)')
        except Exception as error:
            with self.transaction() as db:
                db.execute('DELETE FROM auth WHERE key=?', ('challenge:' + self.digest(challenge),))
            raise AuthError("Impossible d'envoyer le code. Reessayez plus tard.", 503) from error
        return {'challenge': challenge, 'requires_code': True, 'ip_verified': reliable}

    def verify(self, challenge, code, identity, remember, browser=None):
        self.rate('global', 'code', 100, 600)
        self.rate(identity, 'code', 20, 600)
        token = None
        with self.transaction() as db:
            key = 'challenge:' + self.digest(challenge)
            data = self.read(db, key)
            same_client = (
                bool(browser) and identity.startswith('unverified:')
                and hmac.compare_digest(data['browser'], self.digest(browser))
            ) if data.get('browser') else data.get('identity') == self.digest(identity)
            if same_client and data.get('expires', 0) > self.now() and data.get('attempts', 5) < 5:
                data['attempts'] += 1
                self.write(db, key, data)
                if hmac.compare_digest(data['code'], self.digest(challenge + ':' + code)):
                    db.execute('DELETE FROM auth WHERE key=?', (key,))
                    if remember and data.get('reliable'):
                        self.write(db, 'trusted:' + self.digest(identity), {'expires': self.now()+30*86400})
                    db.execute('DELETE FROM auth WHERE key=?', ('backoff:' + data['identity'],))
                    token = self.session(db, identity, browser if data.get('browser') else None)
        if not token:
            raise AuthError('Code invalide ou expire. Demandez un nouveau code.')
        return token

    def validate(self, token, identity, browser=None):
        if not token or not self.password:
            raise AuthError('Connexion administrateur requise.')
        with self.transaction() as db:
            data = self.read(db, 'session:' + self.digest(token))
        same_client = (
            bool(browser) and identity.startswith('unverified:')
            and hmac.compare_digest(data['browser'], self.digest(browser))
        ) if data.get('browser') else data.get('identity') == self.digest(identity)
        if data.get('expires', 0) <= self.now() or not same_client:
            raise AuthError('Session expiree ou adresse reseau modifiee. Reconnectez-vous.')

    def logout(self, token):
        with self.transaction() as db:
            db.execute('DELETE FROM auth WHERE key=?', ('session:' + self.digest(token),))

    def forget(self, token):
        with self.transaction() as db:
            db.execute("DELETE FROM auth WHERE key LIKE 'trusted:%' OR key LIKE 'challenge:%' OR key LIKE 'session:%'")
