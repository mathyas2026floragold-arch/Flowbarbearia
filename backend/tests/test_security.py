import hashlib,hmac,pytest
from fastapi import HTTPException
from app.security import verify_webhook
def test_signed_webhook():
 raw=b'{"eventId":"one"}';sig=hmac.new(b"test-secret",raw,hashlib.sha256).hexdigest();verify_webhook(raw,sig)
def test_rejects_invalid_webhook():
 with pytest.raises(HTTPException): verify_webhook(b"{}","wrong")
