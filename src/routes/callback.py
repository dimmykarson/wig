import time
from fastapi import APIRouter, HTTPException
from src.models import CallbackPayload, DebugEntry, Platform
from src.state import app_state

router = APIRouter()


def _resolve_platform(canal: str) -> Platform:
    """Aceita o nome da plataforma ('whatsapp'/'instagram') ou o identifier
    configurado no canal (wa_id / IGSID), resolvendo para a plataforma correta."""
    try:
        return Platform(canal)
    except ValueError:
        pass
    for platform in Platform:
        ch = app_state.get(platform)
        if ch.config.identifier == canal:
            return platform
    raise HTTPException(status_code=404, detail=f"Canal com identifier '{canal}' não encontrado")


@router.post("/callback/{canal}")
async def receive_callback(canal: str, body: CallbackPayload):
    platform = _resolve_platform(canal)
    ch = app_state.get(platform)

    entry = DebugEntry(
        direction="received",
        timestamp_ms=int(time.time() * 1000),
        http_status=200,
        payload=body.model_dump(),
    )
    ch.add_debug(entry)

    if ch.websocket:
        await ch.websocket.send_json({
            "type": "debug",
            "direction": entry.direction,
            "payload": entry.payload,
            "http_status": entry.http_status,
            "timestamp_ms": entry.timestamp_ms,
        })
        msg: dict = {
            "type": "received",
            "msg_type": body.type,
            "text": body.text,
            "ts": _now_str(),
        }
        if body.type != "text":
            msg["url"] = body.text
            msg["caption"] = body.caption
            msg["filename"] = body.filename
        await ch.websocket.send_json(msg)

    return {"ok": True}


def _now_str() -> str:
    import datetime
    return datetime.datetime.now().strftime("%H:%M")
