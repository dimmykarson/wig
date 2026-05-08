import asyncio
import datetime
import json
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from src.builders.ids import generate_mid, generate_wamid
from src.builders.instagram import (
    build_delivery_receipt,
    build_read_receipt,
    build_text_payload as ig_text,
)
from src.builders.signature import compute_signature
from src.builders.whatsapp import (
    build_status_payload,
    build_text_payload as wpp_text,
)
from src.models import DebugEntry, Platform
from src.persistence import load_config
from src.routes.callback import router as callback_router
from src.routes.config import router as config_router
from src.routes.health import router as health_router
from src.routes.info import router as info_router
from src.routes.webhook import router as webhook_router
from src.settings import settings
from src.state import app_state

logging.basicConfig(level=settings.log_level)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app):
    data = load_config()
    for platform in Platform:
        saved = data.get(platform.value)
        if saved:
            ch = app_state.get(platform)
            ch.config.webhook_url = saved.get("webhook_url", "")
            ch.config.user_name = saved.get("user_name", "")
            ch.config.identifier = saved.get("identifier", "")
            ch.config.configured = bool(ch.config.webhook_url)
            log.info("Config restaurada para %s", platform.value)
    yield


app = FastAPI(title="wig — WhatsApp & Instagram Mock", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(info_router)
app.include_router(config_router)
app.include_router(webhook_router)
app.include_router(callback_router)


# ── WebSocket ──────────────────────────────────────────────────────────────────

@app.websocket("/ws/{canal}")
async def websocket_endpoint(websocket: WebSocket, canal: str):
    try:
        platform = Platform(canal)
    except ValueError:
        await websocket.close(code=4004)
        return

    ch = app_state.get(platform)
    await websocket.accept()
    ch.websocket = websocket
    log.info("WS conectado: %s", canal)

    try:
        while True:
            data = await websocket.receive_json()
            text = data.get("text", "").strip()
            if not text:
                continue
            await _handle_outgoing(platform, text)
    except WebSocketDisconnect:
        ch.websocket = None
        log.info("WS desconectado: %s", canal)


async def _handle_outgoing(platform: Platform, text: str) -> None:
    ch = app_state.get(platform)
    now = datetime.datetime.now().strftime("%H:%M")
    ts_ms = int(time.time() * 1000)

    if not ch.config.configured:
        await ch.websocket.send_json({"type": "error", "text": "Canal não configurado"})
        return

    if platform == Platform.WHATSAPP:
        msg_id = generate_wamid()
        payload = wpp_text(ch.config, text, msg_id)
    else:
        msg_id = generate_mid()
        payload = ig_text(ch.config, text, msg_id)

    body = json.dumps(payload).encode()
    signature = compute_signature(settings.app_secret, body)

    await ch.websocket.send_json({"type": "sent", "text": text, "ts": now})

    http_status = None
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                ch.config.webhook_url,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Hub-Signature-256": signature,
                },
                timeout=10.0,
            )
        http_status = resp.status_code
        if resp.status_code >= 400:
            await ch.websocket.send_json({
                "type": "error",
                "text": f"Webhook retornou {resp.status_code}",
            })
    except Exception as exc:
        await ch.websocket.send_json({"type": "error", "text": str(exc)})

    ch.add_debug(DebugEntry(
        direction="sent",
        timestamp_ms=ts_ms,
        http_status=http_status,
        payload=payload,
    ))

    asyncio.create_task(_simulate_status(platform, msg_id))


async def _simulate_status(platform: Platform, msg_id: str) -> None:
    ch = app_state.get(platform)
    cfg = ch.config
    delivered_s = settings.status_delivered_delay_ms / 1000
    read_s = settings.status_read_delay_ms / 1000

    await asyncio.sleep(delivered_s)
    watermark = int(time.time())

    if platform == Platform.WHATSAPP:
        delivered_payload = build_status_payload(cfg, msg_id, "delivered")
    else:
        delivered_payload = build_delivery_receipt(cfg, [msg_id], watermark)

    ch.add_debug(DebugEntry(direction="status", timestamp_ms=int(time.time() * 1000), payload=delivered_payload))
    if ch.websocket:
        await ch.websocket.send_json({"type": "status", "status": "delivered"})

    await asyncio.sleep(read_s - delivered_s)
    watermark = int(time.time())

    if platform == Platform.WHATSAPP:
        read_payload = build_status_payload(cfg, msg_id, "read")
    else:
        read_payload = build_read_receipt(cfg, watermark)

    ch.add_debug(DebugEntry(direction="status", timestamp_ms=int(time.time() * 1000), payload=read_payload))
    if ch.websocket:
        await ch.websocket.send_json({"type": "status", "status": "read"})


# ── UI ─────────────────────────────────────────────────────────────────────────

_UI_FILE = Path(__file__).parent.parent / "ui" / "index.html"


@app.get("/", response_class=HTMLResponse)
async def ui():
    return HTMLResponse(_UI_FILE.read_text(encoding="utf-8"))
