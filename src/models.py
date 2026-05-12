from enum import StrEnum
from typing import Literal

from pydantic import BaseModel


class Platform(StrEnum):
    WHATSAPP = "whatsapp"
    INSTAGRAM = "instagram"


class ChannelConfig(BaseModel):
    webhook_url: str = ""
    user_name: str = ""
    identifier: str = ""
    configured: bool = False

    # IDs gerados como mock — usados nos payloads Meta
    waba_id: str = "MOCK_WABA_ID"
    phone_number_id: str = "MOCK_PHONE_NUMBER_ID"
    ig_account_id: str = "MOCK_IG_ACCOUNT_ID"
    ig_page_id: str = "MOCK_IG_PAGE_ID"


class ChannelConfigUpdate(BaseModel):
    webhook_url: str
    user_name: str
    identifier: str
    phone_number_id: str = ""


MediaType = Literal["image", "audio", "video", "document"]


class CallbackPayload(BaseModel):
    type: Literal["text", "image", "audio", "video", "document"] = "text"
    text: str = ""
    caption: str = ""
    filename: str = ""


class DebugEntry(BaseModel):
    direction: Literal["sent", "received", "status", "error"]
    timestamp_ms: int
    http_status: int | None = None
    payload: dict | str
