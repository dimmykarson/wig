import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.settings import settings


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_valid_challenge_returns_200(client):
    r = await client.get("/webhook/whatsapp", params={
        "hub.mode": "subscribe",
        "hub.verify_token": settings.verify_token,
        "hub.challenge": "abc123",
    })
    assert r.status_code == 200
    assert r.text == "abc123"


async def test_wrong_token_returns_403(client):
    r = await client.get("/webhook/whatsapp", params={
        "hub.mode": "subscribe",
        "hub.verify_token": "token-errado",
        "hub.challenge": "abc123",
    })
    assert r.status_code == 403


async def test_wrong_mode_returns_403(client):
    r = await client.get("/webhook/whatsapp", params={
        "hub.mode": "unsubscribe",
        "hub.verify_token": settings.verify_token,
        "hub.challenge": "abc123",
    })
    assert r.status_code == 403


async def test_instagram_channel_also_works(client):
    r = await client.get("/webhook/instagram", params={
        "hub.mode": "subscribe",
        "hub.verify_token": settings.verify_token,
        "hub.challenge": "xyz789",
    })
    assert r.status_code == 200
    assert r.text == "xyz789"


async def test_invalid_channel_returns_404(client):
    r = await client.get("/webhook/telegram", params={
        "hub.mode": "subscribe",
        "hub.verify_token": settings.verify_token,
        "hub.challenge": "abc",
    })
    assert r.status_code == 404
