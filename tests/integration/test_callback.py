import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_callback_whatsapp_returns_ok(client):
    r = await client.post("/callback/whatsapp", json={"text": "olá", "type": "text"})
    assert r.status_code == 200
    assert r.json() == {"ok": True}


async def test_callback_instagram_returns_ok(client):
    r = await client.post("/callback/instagram", json={"text": "oi", "type": "text"})
    assert r.status_code == 200
    assert r.json() == {"ok": True}


async def test_callback_invalid_channel_returns_404(client):
    r = await client.post("/callback/telegram", json={"text": "oi"})
    assert r.status_code == 404


async def test_callback_missing_text_returns_422(client):
    r = await client.post("/callback/whatsapp", json={"type": "text"})
    assert r.status_code == 422


async def test_callback_empty_body_returns_422(client):
    r = await client.post("/callback/whatsapp", json={})
    assert r.status_code == 422
