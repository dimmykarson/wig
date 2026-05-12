import pytest
from httpx import ASGITransport, AsyncClient

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


async def test_callback_text_defaults_when_missing(client):
    # text has a default of "" so omitting it is valid (type still defaults to "text")
    r = await client.post("/callback/whatsapp", json={"type": "text"})
    assert r.status_code == 200


async def test_callback_empty_body_returns_ok(client):
    # all fields have defaults, so empty body is accepted
    r = await client.post("/callback/whatsapp", json={})
    assert r.status_code == 200
