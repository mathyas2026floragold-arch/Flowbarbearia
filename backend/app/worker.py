import asyncio,json
from datetime import datetime,timezone
from sqlalchemy import text
from .db import Session
from .config import get_settings
from .services.evolution import send_message

async def claim(db):
 return (await db.execute(text("update scheduled_messages set status='processing',locked_at=now() where id=(select id from scheduled_messages where status in ('pending','retry') and send_at<=now() and attempts<:max order by send_at for update skip locked limit 1) returning *"),{"max":get_settings().max_message_attempts})).mappings().one_or_none()
async def work():
 while True:
  async with Session() as db:
   item=await claim(db)
   if not item: await db.rollback();await asyncio.sleep(get_settings().worker_poll_seconds);continue
   await db.commit()
  try:
   async with Session() as db:
    target=(await db.execute(text("select c.phone_e164,c.barbershop_id,w.instance_key from customers c join whatsapp_connections w on w.barbershop_id=c.barbershop_id join barbershops b on b.id=c.barbershop_id where c.id=:c and not c.do_not_contact and w.status='connected' and b.status in('trial','active') and barbershop_has_access(b.id)"),{"c":item["customer_id"]})).mappings().one_or_none()
   if not target: raise RuntimeError("Cliente bloqueado ou WhatsApp offline")
   result=await send_message(target["instance_key"],target["phone_e164"],item["body"],item["idempotency_key"])
   async with Session() as db:
    provider_id=str(result.get("key",{}).get("id",""))
    await db.execute(text("update scheduled_messages set status='sent',sent_at=now(),provider_id=:p where id=:id"),{"p":provider_id,"id":item["id"]})
    conversation=(await db.execute(text("""insert into whatsapp_conversations(barbershop_id,phone_e164,status,ai_enabled,last_message_at)
     values(:tenant,:phone,'ai',true,now()) on conflict(barbershop_id,phone_e164) do update set last_message_at=now(),updated_at=now() returning id"""),{"tenant":target["barbershop_id"],"phone":target["phone_e164"]})).scalar_one()
    await db.execute(text("""insert into whatsapp_messages(barbershop_id,conversation_id,appointment_id,direction,sender_type,body,status,provider_id,idempotency_key,sent_at)
     values(:tenant,:conversation,:appointment,'outbound','system',:body,'sent',:provider,:idem,now()) on conflict(idempotency_key) do nothing"""),{"tenant":target["barbershop_id"],"conversation":conversation,"appointment":item["appointment_id"],"body":item["body"],"provider":provider_id,"idem":item["idempotency_key"]})
    await db.commit()
  except Exception as e:
   async with Session() as db:
    await db.execute(text("update scheduled_messages set attempts=attempts+1,status=case when attempts+1>=:max then 'dead' else 'retry' end,next_retry_at=now()+(interval '1 minute'*power(2,attempts)),send_at=now()+(interval '1 minute'*power(2,attempts)),last_error=:e where id=:id"),{"max":get_settings().max_message_attempts,"e":str(e)[:1000],"id":item["id"]});await db.commit()
if __name__=="__main__": asyncio.run(work())
