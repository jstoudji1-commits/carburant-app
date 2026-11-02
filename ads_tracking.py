"""Anonymous receipts issued only after a successful, consented validation."""
import hashlib
import hmac
import json
import base64
import secrets
import time

KINDS = ('compte', 'testeur')
CONSENT_COOKIE = 'optiplein_ads_consent'

def receipt_cookie(kind):
    return 'optiplein_ads_validation_' + kind

def encode_receipt(kind, secret):
    body = base64.urlsafe_b64encode(json.dumps({'kind':kind, 'id':secrets.token_urlsafe(24), 'expires':int(time.time())+86400}).encode()).decode().rstrip('=')
    return body + '.' + hmac.new(secret, body.encode(), hashlib.sha256).hexdigest()

def read_receipt(value, secret):
    try:
        body, signature = value.split('.')
        if not hmac.compare_digest(signature, hmac.new(secret, body.encode(), hashlib.sha256).hexdigest()):
            return None
        data = json.loads(base64.urlsafe_b64decode(body + '='*(-len(body)%4)))
        if data['kind'] not in KINDS or data['expires'] <= time.time():
            return None
        return {'kind':data['kind'], 'id':data['id']}
    except (ValueError, TypeError, KeyError):
        return None

def mark_validation(response, request, kind, secret):
    if request.cookies.get(CONSENT_COOKIE) == 'granted':
        response.set_cookie(receipt_cookie(kind), encode_receipt(kind, secret), max_age=86400,
            httponly=True, secure=request.url.scheme == 'https', samesite='lax', path='/api/ads')
    return response
