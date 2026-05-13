import time

from src.models import ChannelConfig


def _entry_base(config: ChannelConfig) -> dict:
    return {"id": config.ig_account_id, "time": int(time.time())}


def _messaging_base(config: ChannelConfig) -> dict:
    return {
        "sender": {"id": config.identifier},
        "recipient": {"id": config.ig_account_id},
        "timestamp": int(time.time()),
    }


def build_text_payload(config: ChannelConfig, text: str, mid: str) -> dict:
    entry = _entry_base(config)
    messaging = _messaging_base(config)
    messaging["message"] = {
        "mid": mid,
        "text": text,
        "attachments": [],
        "is_deleted": False,
        "is_echo": False,
        "is_unsupported": False,
    }
    entry["messaging"] = [messaging]
    return {"object": "instagram", "entry": [entry]}


_IG_TYPE = {"document": "file"}  # WhatsApp "document" → Instagram "file"


def build_media_payload(
    config: ChannelConfig,
    tipo: str,
    url: str,
    mid: str,
    caption: str = "",
) -> dict:
    entry = _entry_base(config)
    messaging = _messaging_base(config)
    ig_type = _IG_TYPE.get(tipo, tipo)
    attachment: dict = {"type": ig_type, "payload": {"url": url}}
    message: dict = {"mid": mid, "attachments": [attachment]}
    if caption:
        message["text"] = caption
    messaging["message"] = message
    entry["messaging"] = [messaging]
    return {"object": "instagram", "entry": [entry]}


def build_delivery_receipt(config: ChannelConfig, mids: list[str], watermark: int) -> dict:
    entry = _entry_base(config)
    messaging = _messaging_base(config)
    messaging["delivery"] = {"mids": mids, "watermark": watermark}
    entry["messaging"] = [messaging]
    return {"object": "instagram", "entry": [entry]}


def build_read_receipt(config: ChannelConfig, watermark: int) -> dict:
    entry = _entry_base(config)
    messaging = _messaging_base(config)
    messaging["read"] = {"watermark": watermark}
    entry["messaging"] = [messaging]
    return {"object": "instagram", "entry": [entry]}
