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
    build_media_payload as wpp_media,
    build_status_payload,
    build_text_payload as wpp_text,
)
from src.models import DebugEntry, Platform
from src.persistence import load_config
from src.routes.callback import router as callback_router
from src.routes.config import router as config_router
from src.routes.health import router as health_router
from src.routes.info import router as info_router
from src.routes.media import router as media_router
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
            if saved.get("phone_number_id"):
                ch.config.phone_number_id = saved["phone_number_id"]
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
app.include_router(media_router)


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
            try:
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=settings.ws_inactivity_timeout_s,
                )
            except TimeoutError:
                log.info(
                    "WS inativo por %ss — fechando: %s", settings.ws_inactivity_timeout_s, canal
                )
                await websocket.close(code=1001)
                ch.websocket = None
                return
            text = data.get("text", "").strip()
            media_type = data.get("media_type", "")
            media_url = data.get("url", "")
            if media_type and media_url:
                await _handle_outgoing_media(platform, media_type, media_url,
                                             data.get("caption", ""),
                                             data.get("filename", ""),
                                             data.get("mime", ""))
            elif text:
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

    await _push_debug(ch, DebugEntry(
        direction="sent",
        timestamp_ms=ts_ms,
        http_status=http_status,
        payload=payload,
    ))

    asyncio.create_task(_simulate_status(platform, msg_id))


async def _handle_outgoing_media(
    platform: Platform,
    media_type: str,
    url: str,
    caption: str = "",
    filename: str = "",
    mime: str = "",
) -> None:
    ch = app_state.get(platform)
    now = datetime.datetime.now().strftime("%H:%M")
    ts_ms = int(time.time() * 1000)

    if not ch.config.configured:
        await ch.websocket.send_json({"type": "error", "text": "Canal não configurado"})
        return

    msg_id = generate_wamid()
    payload = wpp_media(ch.config, media_type, url, msg_id, caption, filename, mime)

    body = json.dumps(payload).encode()
    signature = compute_signature(settings.app_secret, body)

    display_text = caption or filename or url
    await ch.websocket.send_json({
        "type": "sent",
        "msg_type": media_type,
        "text": display_text,
        "url": url,
        "caption": caption,
        "filename": filename,
        "ts": now,
    })

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

    await _push_debug(ch, DebugEntry(
        direction="sent",
        timestamp_ms=ts_ms,
        http_status=http_status,
        payload=payload,
    ))

    asyncio.create_task(_simulate_status(platform, msg_id))


async def _push_debug(ch, entry: DebugEntry) -> None:
    ch.add_debug(entry)
    if ch.websocket:
        try:
            await ch.websocket.send_json({
                "type": "debug",
                "direction": entry.direction,
                "payload": entry.payload,
                "http_status": entry.http_status,
                "timestamp_ms": entry.timestamp_ms,
            })
        except Exception:
            pass


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

    ts = int(time.time() * 1000)
    entry = DebugEntry(direction="status", timestamp_ms=ts, payload=delivered_payload)
    await _push_debug(ch, entry)
    if ch.websocket:
        await ch.websocket.send_json({"type": "status", "status": "delivered"})

    await asyncio.sleep(read_s - delivered_s)
    watermark = int(time.time())

    if platform == Platform.WHATSAPP:
        read_payload = build_status_payload(cfg, msg_id, "read")
    else:
        read_payload = build_read_receipt(cfg, watermark)

    ts = int(time.time() * 1000)
    entry = DebugEntry(direction="status", timestamp_ms=ts, payload=read_payload)
    await _push_debug(ch, entry)
    if ch.websocket:
        await ch.websocket.send_json({"type": "status", "status": "read"})


# ── UI ─────────────────────────────────────────────────────────────────────────

_UI_FILE = Path(__file__).parent.parent / "ui" / "index.html"


@app.get("/", response_class=HTMLResponse)
async def ui():
    return HTMLResponse(_UI_FILE.read_text(encoding="utf-8"))
