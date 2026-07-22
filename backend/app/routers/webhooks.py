import json
from fastapi import APIRouter, Request, Header, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import session
from ..security import verify_webhook, verify_instance_webhook

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/evolution", status_code=202)
async def evolution(request: Request, token: str | None = None,
                    x_evolution_signature: str | None = Header(None),
                    db: AsyncSession = Depends(session)):
    raw = await request.body()
    payload = json.loads(raw)
    instance = payload.get("instance") or (payload.get("data") or {}).get("instance")
    if x_evolution_signature:
        verify_webhook(raw, x_evolution_signature)
    else:
        verify_instance_webhook(instance or "", token)

    tenant = (await db.execute(text(
        "select barbershop_id from whatsapp_connections where instance_key=:instance"
    ), {"instance": instance})).scalar_one_or_none()
    if not tenant:
        raise HTTPException(404, "Instância desconhecida")

    event = str(payload.get("event") or "").lower()
    if "connection" in event:
        data = payload.get("data") or {}
        state = str(data.get("state") or payload.get("state") or "offline").lower()
        status = "connected" if state in {"open", "connected"} else "connecting" if state == "connecting" else "offline"
        phone = data.get("wuid")
        await db.execute(text(
            "update whatsapp_connections set status=:status,phone_number=coalesce(:phone,phone_number),last_seen_at=now() where instance_key=:instance"
        ), {"status": status, "phone": phone, "instance": instance})

    if "messages" in event:
        data = payload.get("data") or {}
        key = data.get("key") or {}
        remote = str(key.get("remoteJid") or data.get("remoteJid") or "")
        phone = remote.split("@")[0]
        message = data.get("message") or {}
        body = message.get("conversation") or (message.get("extendedTextMessage") or {}).get("text")
        if phone and body:
            direction = "outbound" if key.get("fromMe") else "inbound"
            sender = "system" if direction == "outbound" else "customer"
            conversation = (await db.execute(text("""insert into whatsapp_conversations(barbershop_id,phone_e164,status,ai_enabled,last_message_at,unread_count)
             values(:tenant,:phone,'new',true,now(),case when :direction='inbound' then 1 else 0 end)
             on conflict(barbershop_id,phone_e164) do update set last_message_at=now(),updated_at=now(),
             unread_count=whatsapp_conversations.unread_count+case when :direction='inbound' then 1 else 0 end returning id"""),
             {"tenant":tenant,"phone":"+"+phone.lstrip("+"),"direction":direction})).scalar_one()
            provider_id = str(key.get("id") or "") or None
            await db.execute(text("""insert into whatsapp_messages(barbershop_id,conversation_id,direction,sender_type,body,status,provider_id,idempotency_key,sent_at)
             values(:tenant,:conversation,:direction,:sender,:body,'sent',:provider,:idem,now()) on conflict(idempotency_key) do nothing"""),
             {"tenant":tenant,"conversation":conversation,"direction":direction,"sender":sender,"body":body,"provider":provider_id,"idem":("evolution:"+provider_id) if provider_id else None})

    event_id = payload.get("eventId") or payload.get("id") or f"{instance}:{event}:{payload.get('date_time')}"
    await db.execute(text(
        "insert into webhook_events(barbershop_id,provider,event_id,payload) values(:tenant,'evolution',:event_id,:payload) on conflict(provider,event_id) do nothing"
    ), {"tenant": tenant, "event_id": event_id, "payload": json.dumps(payload)})
    await db.commit()
    return {"accepted": True}
