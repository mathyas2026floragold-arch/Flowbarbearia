import json
from fastapi import APIRouter,Request,Header,Depends,HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import session
from ..security import verify_webhook
router=APIRouter(prefix="/api/webhooks",tags=["webhooks"])

@router.post("/evolution",status_code=202)
async def evolution(request:Request,x_evolution_signature:str|None=Header(None),db:AsyncSession=Depends(session)):
 raw=await request.body()
 verify_webhook(raw,x_evolution_signature)
 payload=json.loads(raw)
 tenant=(await db.execute(text("select barbershop_id from whatsapp_connections where instance_key=:i"),{"i":payload.get("instance")})).scalar_one_or_none()
 if not tenant: raise HTTPException(404,"Instância desconhecida")
 await db.execute(text("insert into webhook_events(barbershop_id,provider,event_id,payload) values(:b,'evolution',:e,:p) on conflict(provider,event_id) do nothing"),{"b":tenant,"e":payload.get("eventId") or payload.get("id"),"p":json.dumps(payload)})
 await db.commit()
 return {"accepted":True}
