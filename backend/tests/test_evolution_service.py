import pytest
import respx
import httpx
from app.config import get_settings
from app.security import webhook_token, verify_instance_webhook
from app.services.evolution import create_instance, connection_state


@pytest.fixture(autouse=True)
def evolution_env(monkeypatch):
    monkeypatch.setenv("EVOLUTION_API_URL", "https://evolution.example")
    monkeypatch.setenv("EVOLUTION_API_KEY", "global-secret")
    monkeypatch.setenv("EVOLUTION_WEBHOOK_SECRET", "webhook-secret")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
@respx.mock
async def test_create_instance_requests_qr_and_webhook():
    route = respx.post("https://evolution.example/instance/create").mock(
        return_value=httpx.Response(201, json={"qrcode": {"base64": "data:image/png;base64,abc"}})
    )
    result = await create_instance("barberflow-tenant", "https://api.example/webhook")
    request = route.calls[0].request
    assert request.headers["apikey"] == "global-secret"
    assert b'"qrcode":true' in request.content
    assert b'"WHATSAPP-BAILEYS"' in request.content
    assert result["qrcode"]["base64"].startswith("data:image/png")


@pytest.mark.asyncio
@respx.mock
async def test_connection_state_uses_instance_name():
    respx.get("https://evolution.example/instance/connectionState/barberflow-tenant").mock(
        return_value=httpx.Response(200, json={"instance": {"state": "open"}})
    )
    result = await connection_state("barberflow-tenant")
    assert result["instance"]["state"] == "open"


def test_webhook_token_is_bound_to_instance():
    token = webhook_token("tenant-a")
    verify_instance_webhook("tenant-a", token)
    with pytest.raises(Exception):
        verify_instance_webhook("tenant-b", token)
