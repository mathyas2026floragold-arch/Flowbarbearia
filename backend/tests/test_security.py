import hashlib,hmac,pytest
from fastapi import HTTPException
from app.config import Settings
from app.security import verify_webhook
def test_signed_webhook():
 raw=b'{"eventId":"one"}';sig=hmac.new(b"test-secret",raw,hashlib.sha256).hexdigest();verify_webhook(raw,sig)
def test_rejects_invalid_webhook():
 with pytest.raises(HTTPException): verify_webhook(b"{}","wrong")

def test_supabase_url_is_canonical_for_jwt_configuration():
 settings=Settings(
  supabase_url="https://project.supabase.co/",
  supabase_jwt_issuer="https://incorrect.example/auth/v1",
  supabase_jwks_url="https://incorrect.example/jwks.json",
 )
 assert settings.auth_issuer=="https://project.supabase.co/auth/v1"
 assert settings.auth_jwks_url=="https://project.supabase.co/auth/v1/.well-known/jwks.json"

def test_explicit_jwt_configuration_remains_supported():
 settings=Settings(
  supabase_url="",
  supabase_jwt_issuer="https://project.supabase.co/auth/v1/",
  supabase_jwks_url="https://project.supabase.co/auth/v1/.well-known/jwks.json",
 )
 assert settings.auth_issuer=="https://project.supabase.co/auth/v1"
 assert settings.auth_jwks_url.endswith("/.well-known/jwks.json")
