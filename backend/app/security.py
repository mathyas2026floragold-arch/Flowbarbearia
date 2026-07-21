import jwt
from dataclasses import dataclass
from fastapi import Depends,HTTPException
from fastapi.security import HTTPAuthorizationCredentials,HTTPBearer
from jwt import PyJWKClient
from .config import get_settings

bearer=HTTPBearer(auto_error=False)
@dataclass(frozen=True)
class Principal:
 user_id:str
 role:str
 barbershop_id:str|None

def _decode(token:str):
 s=get_settings()
 key=PyJWKClient(s.supabase_jwks_url,cache_jwk_set=True,lifespan=300).get_signing_key_from_jwt(token).key
 return jwt.decode(token,key,algorithms=["RS256","ES256"],audience="authenticated",issuer=s.supabase_jwt_issuer,options={"require":["exp","sub"]})

async def principal(c:HTTPAuthorizationCredentials|None=Depends(bearer)):
 if not c: raise HTTPException(401,"Token ausente")
 try: claims=_decode(c.credentials)
 except Exception as e: raise HTTPException(401,"Token inválido") from e
 meta=claims.get("app_metadata",{})
 role=meta.get("role","barbershop_staff")
 tenant=meta.get("barbershop_id")
 if role!="superadmin" and not tenant: raise HTTPException(403,"Usuário sem tenant")
 return Principal(claims["sub"],role,tenant)

def require(*roles):
 async def check(p:Principal=Depends(principal)):
  if p.role not in roles: raise HTTPException(403,"Permissão insuficiente")
  return p
 return check

def verify_webhook(raw:bytes,signature:str|None):
 import hmac,hashlib
 expected=hmac.new(get_settings().evolution_webhook_secret.encode(),raw,hashlib.sha256).hexdigest()
 if not signature or not hmac.compare_digest(expected,signature): raise HTTPException(401,"Webhook inválido")
