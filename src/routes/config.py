from fastapi import APIRouter, HTTPException
from src.models import ChannelConfigUpdate, Platform
from src.state import app_state

router = APIRouter()


def _get_channel(canal: str):
    try:
        return Platform(canal)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Canal '{canal}' não encontrado")


@router.patch("/config/{canal}")
async def update_config(canal: str, body: ChannelConfigUpdate):
    platform = _get_channel(canal)
    ch = app_state.get(platform)
    ch.config.webhook_url = body.webhook_url
    ch.config.user_name = body.user_name
    ch.config.identifier = body.identifier
    ch.config.configured = True
    return ch.config.model_dump()


@router.delete("/history/{canal}")
async def clear_history(canal: str):
    platform = _get_channel(canal)
    ch = app_state.get(platform)
    ch.debug.clear()
    if ch.websocket:
        await ch.websocket.send_json({"type": "history_cleared"})
    return {"ok": True}
