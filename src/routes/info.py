from fastapi import APIRouter
from src.settings import settings
from src.state import app_state
from src.models import Platform

router = APIRouter()


@router.get("/settings-info")
async def settings_info():
    return {
        "verify_token": settings.verify_token,
        "app_secret": settings.app_secret,
    }


@router.get("/info")
async def info():
    base = settings.mock_base_url.rstrip("/")
    channels = {}
    for platform in Platform:
        ch = app_state.get(platform)
        channels[platform.value] = {
            "callback_url": f"{base}/callback/{platform.value}",
            "webhook_verification_url": f"{base}/webhook/{platform.value}",
            "websocket_url": f"{base.replace('http', 'ws')}/ws/{platform.value}",
            "configured": ch.config.configured,
            "connected": ch.connected,
        }
    return {"base_url": base, "channels": channels}


@router.get("/config")
async def get_config():
    return {
        p.value: app_state.get(p).config.model_dump()
        for p in Platform
    }
