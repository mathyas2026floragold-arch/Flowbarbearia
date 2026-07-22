import httpx
from fastapi import HTTPException
from ..config import get_settings


def _settings():
    settings = get_settings()
    if not settings.evolution_api_url or not settings.evolution_api_key:
        raise HTTPException(503, "Evolution API não configurada")
    return settings


async def _request(method: str, path: str, **kwargs):
    settings = _settings()
    headers = {"apikey": settings.evolution_api_key, **kwargs.pop("headers", {})}
    try:
        async with httpx.AsyncClient(timeout=25) as client:
            response = await client.request(
                method,
                f"{settings.evolution_api_url.rstrip('/')}{path}",
                headers=headers,
                **kwargs,
            )
    except httpx.RequestError as exc:
        raise HTTPException(503, "Evolution API indisponível") from exc
    if response.is_error:
        raise HTTPException(502, response.text[:500] or "Falha na Evolution API")
    return response.json() if response.content else {}


async def create_instance(instance_key: str, webhook_url: str):
    return await _request("POST", "/instance/create", json={
        "instanceName": instance_key,
        "qrcode": True,
        "integration": "WHATSAPP-BAILEYS",
        "webhook": {
            "enabled": True,
            "url": webhook_url,
            "events": ["CONNECTION_UPDATE", "MESSAGES_UPSERT", "SEND_MESSAGE"],
        },
    })


async def connect_instance(instance_key: str):
    return await _request("GET", f"/instance/connect/{instance_key}")


async def connection_state(instance_key: str):
    return await _request("GET", f"/instance/connectionState/{instance_key}")


async def delete_instance(instance_key: str):
    return await _request("DELETE", f"/instance/delete/{instance_key}")


async def send_message(instance_key: str, phone: str, body: str, idempotency_key: str):
    return await _request("POST", f"/message/sendText/{instance_key}",
        headers={"Idempotency-Key": idempotency_key},
        json={"number": phone, "text": body})
