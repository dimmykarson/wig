import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.state import app_state
from src.models import Platform


@pytest.fixture(autouse=True)
def reset_state():
    for ch in app_state.channels.values():
        ch.config.webhook_url = ""
        ch.config.user_name = ""
        ch.config.identifier = ""
        ch.config.configured = False


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_get_config_returns_both_channels(client):
    r = await client.get("/config")
    assert r.status_code == 200
    data = r.json()
    assert "whatsapp" in data
    assert "instagram" in data


async def test_patch_config_whatsapp(client):
    payload = {"webhook_url": "http://app/wpp/", "user_name": "João", "identifier": "5586999990000"}
    r = await client.patch("/config/whatsapp", json=payload)
    assert r.status_code == 200
    assert r.json()["configured"] is True


async def test_patch_config_updates_state(client):
    payload = {"webhook_url": "http://app/ig/", "user_name": "Maria", "identifier": "123456789"}
    await client.patch("/config/instagram", json=payload)
    assert app_state.get(Platform.INSTAGRAM).config.user_name == "Maria"


async def test_patch_config_invalid_channel_returns_404(client):
    r = await client.patch("/config/telegram", json={"webhook_url": "x", "user_name": "x", "identifier": "x"})
    assert r.status_code == 404


async def test_patch_config_missing_field_returns_422(client):
    r = await client.patch("/config/whatsapp", json={"webhook_url": "http://app/"})
    assert r.status_code == 422


async def test_delete_history_returns_ok(client):
    r = await client.delete("/history/whatsapp")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


async def test_delete_history_invalid_channel_returns_404(client):
    r = await client.delete("/history/telegram")
    assert r.status_code == 404
