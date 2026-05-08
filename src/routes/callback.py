import time
from fastapi import APIRouter, HTTPException
from src.models import CallbackPayload, DebugEntry, Platform
from src.state import app_state

router = APIRouter()


def _get_platform(canal: str) -> Platform:
    try:
        return Platform(canal)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Canal '{canal}' não encontrado")


@router.post("/callback/{canal}")
async def receive_callback(canal: str, body: CallbackPayload):
    platform = _get_platform(canal)
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
            "type": "received",
            "msg_type": body.type,
            "text": body.text,
            "ts": _now_str(),
        })

    return {"ok": True}


def _now_str() -> str:
    import datetime
    return datetime.datetime.now().strftime("%H:%M")
