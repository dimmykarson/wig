from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from src.models import Platform
from src.settings import settings

router = APIRouter()


def _get_platform(canal: str) -> Platform:
    try:
        return Platform(canal)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Canal '{canal}' não encontrado")


@router.get("/webhook/{canal}", response_class=PlainTextResponse)
async def verify_webhook(
    canal: str,
    hub_mode: str = Query(alias="hub.mode", default=""),
    hub_verify_token: str = Query(alias="hub.verify_token", default=""),
    hub_challenge: str = Query(alias="hub.challenge", default=""),
):
    _get_platform(canal)
    if hub_mode == "subscribe" and hub_verify_token == settings.verify_token:
        return hub_challenge
    raise HTTPException(status_code=403, detail="Forbidden")
