from fastapi import APIRouter,Depends,HTTPException
import re
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from ..dependencies import scoped_db
from ..security import Principal,require
from ..schemas import ServiceIn,StatusIn,BarberIn,AISettingsIn
from ..config import get_settings
from ..security import webhook_token
from ..services.evolution import create_instance,connect_instance,connection_state,delete_instance
router=APIRouter(prefix="/api/app",tags=["barbershop"])

@router.get("/dashboard")
async def dashboard(p:Principal=Depends(require("owner","manager","barber","receptionist")),db:AsyncSession=Depends(scoped_db)):
 return (await db.execute(text("""select
  (select count(*) from appointments where starts_at::date=(now() at time zone 'America/Fortaleza')::date and status not in('cancelled','no_show')) appointments_today,
  (select count(*) from appointments where starts_at>=date_trunc('week',now()) and starts_at<date_trunc('week',now())+interval '7 days') appointments_week,
  (select count(*) from customers) customers,
  (select count(*) from scheduled_messages where status in('pending','retry')) automations_pending,
  (select status from whatsapp_connections limit 1) whatsapp_status,
  (select json_build_object('status',s.status,'expires_at',s.expires_at) from subscriptions s where s.barbershop_id=current_setting('app.barbershop_id')::uuid order by created_at desc limit 1) subscription"""))).mappings().one()

@router.get("/profile")
async def profile(p:Principal=Depends(require("owner","manager","barber","receptionist")),db:AsyncSession=Depends(scoped_db)):
 return (await db.execute(text("select id,name,slug,status,timezone,settings from barbershops where id=current_setting('app.barbershop_id')::uuid"))).mappings().one()

@router.get("/services")
async def services(p:Principal=Depends(require("owner","manager","barber","receptionist")),db:AsyncSession=Depends(scoped_db)):
 return (await db.execute(text("select id,name,duration_minutes,buffer_minutes,price,return_days from services where active order by name"))).mappings().all()

@router.post("/services",status_code=201)
async def create_service(data:ServiceIn,p:Principal=Depends(require("owner","manager")),db:AsyncSession=Depends(scoped_db)):
 row=(await db.execute(text("insert into services(barbershop_id,name,duration_minutes,buffer_minutes,price,return_days) values(current_setting('app.barbershop_id')::uuid,:n,:d,:b,:p,:r) returning *"),{"n":data.name,"d":data.duration_minutes,"b":data.buffer_minutes,"p":data.price,"r":data.return_days})).mappings().one()
 await db.commit()
 return row

@router.get("/barbers")
async def barbers(p:Principal=Depends(require("owner","manager","barber","receptionist")),db:AsyncSession=Depends(scoped_db)):
 return (await db.execute(text("select id,display_name,active,public,user_id from barbers order by display_name"))).mappings().all()

@router.post("/barbers",status_code=201)
async def create_barber(data:BarberIn,p:Principal=Depends(require("owner","manager")),db:AsyncSession=Depends(scoped_db)):
 row=(await db.execute(text("insert into barbers(barbershop_id,display_name,active,public) values(current_setting('app.barbershop_id')::uuid,:n,:a,:v) returning *"),{"n":data.display_name,"a":data.active,"v":data.public})).mappings().one()
 await db.commit();return row

@router.get("/clients")
async def clients(search:str|None=None,p:Principal=Depends(require("owner","manager","barber","receptionist")),db:AsyncSession=Depends(scoped_db)):
 return (await db.execute(text("""select c.id,c.name,c.phone_e164,c.do_not_contact,c.notes,
  count(a.id) visits,max(a.starts_at) last_appointment,
  max(a.starts_at) filter(where a.starts_at>now() and a.status not in('cancelled','no_show')) next_appointment
  from customers c left join appointments a on a.customer_id=c.id
  where (:q is null or c.name ilike '%'||:q||'%' or c.phone_e164 like '%'||:q||'%')
  group by c.id order by max(a.starts_at) desc nulls last,c.name limit 200"""),{"q":search})).mappings().all()

@router.get("/appointments")
async def appointments(day:str|None=None,barber_id:str|None=None,status:str|None=None,p:Principal=Depends(require("owner","manager","barber","receptionist")),db:AsyncSession=Depends(scoped_db)):
 return (await db.execute(text("""select a.id,a.starts_at,a.ends_at,a.status,a.source,c.name customer_name,c.phone_e164,
  s.name service_name,s.price,br.display_name barber_name from appointments a join customers c on c.id=a.customer_id
  join services s on s.id=a.service_id join barbers br on br.id=a.barber_id
  where (:day is null or a.starts_at::date=cast(:day as date)) and (:barber is null or a.barber_id=cast(:barber as uuid))
  and (:status is null or a.status::text=:status) order by a.starts_at limit 500"""),{"day":day,"barber":barber_id,"status":status})).mappings().all()

@router.get("/ai-settings")
async def ai_settings(p:Principal=Depends(require("owner","manager")),db:AsyncSession=Depends(scoped_db)):
 row=(await db.execute(text("select assistant_name,tone,instructions,enabled,handoff_message from ai_settings limit 1"))).mappings().one_or_none()
 return row or {"assistant_name":"Luna","tone":"natural","instructions":"","enabled":True,"handoff_message":None}

@router.put("/ai-settings")
async def save_ai_settings(data:AISettingsIn,p:Principal=Depends(require("owner","manager")),db:AsyncSession=Depends(scoped_db)):
 row=(await db.execute(text("""insert into ai_settings(barbershop_id,assistant_name,tone,instructions,enabled)
  values(current_setting('app.barbershop_id')::uuid,:n,:t,:i,:e) on conflict(barbershop_id) do update
  set assistant_name=excluded.assistant_name,tone=excluded.tone,instructions=excluded.instructions,enabled=excluded.enabled,updated_at=now() returning *"""),{"n":data.assistant_name,"t":data.tone,"i":data.instructions,"e":data.enabled})).mappings().one()
 await db.commit();return row

@router.get("/conversations")
async def conversations(p:Principal=Depends(require("owner","manager","receptionist")),db:AsyncSession=Depends(scoped_db)):
 return (await db.execute(text("select id,phone_e164,status,ai_enabled,last_message_at,unread_count,assigned_user_id from whatsapp_conversations order by last_message_at desc nulls last limit 200"))).mappings().all()

@router.patch("/conversations/{conversation_id}/mode")
async def conversation_mode(conversation_id:str,human:bool,p:Principal=Depends(require("owner","manager","receptionist")),db:AsyncSession=Depends(scoped_db)):
 row=(await db.execute(text("update whatsapp_conversations set ai_enabled=:ai,status=case when :human then 'human' else 'ai' end,assigned_user_id=case when :human then :u else null end,updated_at=now() where id=:id returning *"),{"ai":not human,"human":human,"u":p.user_id,"id":conversation_id})).mappings().one_or_none()
 if not row: raise HTTPException(404,"Conversa não encontrada")
 await db.commit();return row

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
