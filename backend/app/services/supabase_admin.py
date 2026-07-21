import httpx
from ..config import get_settings

async def create_owner(email:str,barbershop_id:str):
 s=get_settings()
 async with httpx.AsyncClient(timeout=20) as client:
  response=await client.post(f"{s.supabase_jwt_issuer.rsplit('/auth/v1',1)[0]}/auth/v1/admin/users",headers={"Authorization":f"Bearer {s.supabase_service_role_key}","apikey":s.supabase_service_role_key},json={"email":email,"email_confirm":True,"app_metadata":{"role":"owner","barbershop_id":barbershop_id}})
  response.raise_for_status()
  return response.json()
