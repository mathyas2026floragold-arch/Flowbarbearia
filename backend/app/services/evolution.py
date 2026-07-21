import httpx
from ..config import get_settings
async def send_message(instance_key:str,phone:str,body:str,idempotency_key:str):
 s=get_settings()
 async with httpx.AsyncClient(timeout=20) as client:
  r=await client.post(f"{s.evolution_api_url}/message/sendText/{instance_key}",headers={"apikey":s.evolution_api_key,"Idempotency-Key":idempotency_key},json={"number":phone,"text":body})
  r.raise_for_status()
  return r.json()
