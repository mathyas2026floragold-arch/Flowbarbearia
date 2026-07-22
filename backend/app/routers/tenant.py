from fastapi import APIRouter,Depends,HTTPException
import re
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from ..dependencies import scoped_db
from ..security import Principal,require
from ..schemas import ServiceIn,StatusIn
from ..config import get_settings
from ..security import webhook_token
from ..services.evolution import create_instance,connect_instance,connection_state,delete_instance
router=APIRouter(prefix="/api/app",tags=["barbershop"])

@router.get("/services")
async def services(p:Principal=Depends(require("owner","manager","barber","receptionist")),db:AsyncSession=Depends(scoped_db)):
 return (await db.execute(text("select id,name,duration_minutes,buffer_minutes,price,return_days from services where active order by name"))).mappings().all()

@router.post("/services",status_code=201)
async def create_service(data:ServiceIn,p:Principal=Depends(require("owner","manager")),db:AsyncSession=Depends(scoped_db)):
 row=(await db.execute(text("insert into services(barbershop_id,name,duration_minutes,buffer_minutes,price,return_days) values(current_setting('app.barbershop_id')::uuid,:n,:d,:b,:p,:r) returning *"),{"n":data.name,"d":data.duration_minutes,"b":data.buffer_minutes,"p":data.price,"r":data.return_days})).mappings().one()
 await db.commit()
 return row

def _instance_key(barbershop_id:str)->str:
 return "barberflow-"+re.sub(r"[^a-zA-Z0-9]","",barbershop_id).lower()

def _provider_state(payload:dict)->str:
 state=(payload.get("instance") or {}).get("state") or payload.get("state") or "offline"
 return "connected" if str(state).lower() in {"open","connected"} else "connecting" if str(state).lower()=="connecting" else "offline"

@router.get("/whatsapp")
async def whatsapp_status(p:Principal=Depends(require("owner","manager","barber","receptionist")),db:AsyncSession=Depends(scoped_db)):
 row=(await db.execute(text("select instance_key,status,phone_number,last_seen_at from whatsapp_connections limit 1"))).mappings().one_or_none()
 if not row: return {"status":"offline","phone_number":None,"last_seen_at":None}
 try:
  provider=await connection_state(row["instance_key"])
  status=_provider_state(provider)
  await db.execute(text("update whatsapp_connections set status=:s,last_seen_at=now() where instance_key=:i"),{"s":status,"i":row["instance_key"]})
  await db.commit()
  return {"status":status,"phone_number":row["phone_number"],"last_seen_at":row["last_seen_at"]}
 except HTTPException:
  return {"status":row["status"],"phone_number":row["phone_number"],"last_seen_at":row["last_seen_at"]}

@router.post("/whatsapp/connect")
async def whatsapp_connect(p:Principal=Depends(require("owner","manager")),db:AsyncSession=Depends(scoped_db)):
 row=(await db.execute(text("select instance_key,status from whatsapp_connections limit 1"))).mappings().one_or_none()
 instance_key=row["instance_key"] if row else _instance_key(p.barbershop_id or "")
 settings=get_settings()
 if not settings.public_api_url: raise HTTPException(503,"PUBLIC_API_URL não configurada")
 if row:
  result=await connect_instance(instance_key)
 else:
  token=webhook_token(instance_key)
  webhook=f"{settings.public_api_url.rstrip('/')}/api/webhooks/evolution?token={token}"
  result=await create_instance(instance_key,webhook)
  await db.execute(text("insert into whatsapp_connections(barbershop_id,instance_key,status) values(current_setting('app.barbershop_id')::uuid,:i,'connecting')"),{"i":instance_key})
  await db.commit()
 qr=result.get("qrcode") or result
 return {"status":"connecting","qrcode":qr.get("base64"),"pairing_code":qr.get("pairingCode")}

@router.delete("/whatsapp",status_code=204)
async def whatsapp_disconnect(p:Principal=Depends(require("owner","manager")),db:AsyncSession=Depends(scoped_db)):
 row=(await db.execute(text("select instance_key from whatsapp_connections limit 1"))).mappings().one_or_none()
 if not row: return None
 await delete_instance(row["instance_key"])
 await db.execute(text("delete from whatsapp_connections where instance_key=:i"),{"i":row["instance_key"]})
 await db.commit()
 return None

@router.patch("/appointments/{appointment_id}/status")
async def set_status(appointment_id:str,data:StatusIn,p:Principal=Depends(require("owner","manager","barber","receptionist")),db:AsyncSession=Depends(scoped_db)):
 if data.status not in {"confirmed","arrived","in_service","completed","cancelled","no_show"}: raise HTTPException(422,"Transição inválida")
 row=(await db.execute(text("select * from complete_or_update_appointment(:id,:status,:actor)"),{"id":appointment_id,"status":data.status,"actor":p.user_id})).mappings().one_or_none()
 if not row: raise HTTPException(404,"Agendamento não encontrado")
 await db.commit()
 return row
