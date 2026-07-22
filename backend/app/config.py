from functools import lru_cache
from pydantic_settings import BaseSettings,SettingsConfigDict

class Settings(BaseSettings):
 environment:str="development"
 database_url:str="postgresql+asyncpg://localhost/postgres"
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

@lru_cache
def get_settings():
 return Settings()
