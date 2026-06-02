import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_index_serves_both_channels(client):
    """CA2: a tela dupla (/) continua servindo os dois canais."""
    r = await client.get("/")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    body = r.text
    assert "col-whatsapp" in body
    assert "col-instagram" in body


async def test_whatsapp_page_served(client):
    """CA1: GET /whatsapp serve a página dedicada com 200 text/html."""
    r = await client.get("/whatsapp")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")


async def test_whatsapp_page_has_no_instagram(client):
    """CA4: a página dedicada não contém markup do Instagram."""
    body = (await client.get("/whatsapp")).text
    assert "col-instagram" not in body
    assert 'id="phone-instagram"' not in body
    assert "/ws/whatsapp" in body or "shared.js" in body


async def test_shared_js_served_static(client):
    """CA3: o JS compartilhado é servido como estático."""
    r = await client.get("/static/shared.js")
    assert r.status_code == 200


async def test_shared_css_served_static(client):
    r = await client.get("/static/shared.css")
    assert r.status_code == 200
