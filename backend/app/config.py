from functools import lru_cache
from urllib.parse import parse_qsl,urlencode,urlsplit,urlunsplit
from pydantic import field_validator
from pydantic_settings import BaseSettings,SettingsConfigDict

class Settings(BaseSettings):
 environment:str="development"
 database_url:str="postgresql+asyncpg://localhost/postgres"
 supabase_url:str=""
 supabase_jwt_issuer:str=""
 supabase_jwks_url:str=""
 supabase_service_role_key:str=""
 gemini_api_key:str=""
 gemini_model:str="gemini-2.5-flash"
 evolution_api_url:str=""
 evolution_api_key:str=""
 evolution_webhook_secret:str=""
 public_api_url:str=""
 cors_origins:str="http://localhost:5173"
 worker_poll_seconds:int=2
 max_message_attempts:int=5
 model_config=SettingsConfigDict(env_file=".env",extra="ignore")

 @field_validator("database_url",mode="before")
 @classmethod
 def normalize_database_url(cls,value:str)->str:
  """Accept Supabase/Prisma URLs and normalize them for SQLAlchemy asyncpg."""
  url=str(value or "").strip()
  if url.startswith("postgresql://"):
   url="postgresql+asyncpg://"+url.removeprefix("postgresql://")
  elif url.startswith("postgres://"):
   url="postgresql+asyncpg://"+url.removeprefix("postgres://")
  parts=urlsplit(url)
  query=[]
  for key,item in parse_qsl(parts.query,keep_blank_values=True):
   if key=="schema":
    continue
   query.append(("ssl" if key=="sslmode" else key,item))
  return urlunsplit((parts.scheme,parts.netloc,parts.path,urlencode(query),parts.fragment))

 @property
 def auth_issuer(self)->str:
  """Use SUPABASE_URL as the canonical source when it is available."""
  base=self.supabase_url.strip().rstrip("/")
  return f"{base}/auth/v1" if base else self.supabase_jwt_issuer.strip().rstrip("/")

 @property
 def auth_jwks_url(self)->str:
  base=self.supabase_url.strip().rstrip("/")
  if base:
   return f"{base}/auth/v1/.well-known/jwks.json"
  return self.supabase_jwks_url.strip()

@lru_cache
def get_settings():
 return Settings()
