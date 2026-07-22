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

    event_id = payload.get("eventId") or payload.get("id") or f"{instance}:{event}:{payload.get('date_time')}"
    await db.execute(text(
        "insert into webhook_events(barbershop_id,provider,event_id,payload) values(:tenant,'evolution',:event_id,:payload) on conflict(provider,event_id) do nothing"
    ), {"tenant": tenant, "event_id": event_id, "payload": json.dumps(payload)})
    await db.commit()
    return {"accepted": True}
