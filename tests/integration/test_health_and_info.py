import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_health_returns_ok(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_info_has_both_channels(client):
    r = await client.get("/info")
    assert r.status_code == 200
    data = r.json()
    assert "whatsapp" in data["channels"]
    assert "instagram" in data["channels"]


async def test_info_callback_url_format(client):
    r = await client.get("/info")
    wpp = r.json()["channels"]["whatsapp"]
    assert wpp["callback_url"].endswith("/callback/whatsapp")


async def test_info_webhook_verification_url(client):
    r = await client.get("/info")
    wpp = r.json()["channels"]["whatsapp"]
    assert wpp["webhook_verification_url"].endswith("/webhook/whatsapp")
