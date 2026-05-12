import time
from src.models import ChannelConfig


def build_text_payload(config: ChannelConfig, text: str, wamid: str) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": config.waba_id,
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": config.identifier,
                        "phone_number_id": config.phone_number_id,
                    },
                    "contacts": [{
                        "profile": {"name": config.user_name},
                        "wa_id": config.identifier,
                    }],
                    "messages": [{
                        "from": config.identifier,
                        "id": wamid,
                        "timestamp": str(int(time.time())),
                        "type": "text",
                        "text": {"body": text},
                    }],
                },
                "field": "messages",
            }],
        }],
    }


def build_media_payload(
    config: ChannelConfig,
    tipo: str,
    url: str,
    wamid: str,
    caption: str = "",
    filename: str = "",
    mime: str = "",
) -> dict:
    # Use the last path segment of the URL as id so CSA can fetch it from the
    # mock's /media/{name} endpoint — matches the real WhatsApp Cloud API format.
    media_id = url.rstrip("/").rsplit("/", 1)[-1]
    media_obj: dict = {"id": media_id}
    if mime:
        media_obj["mime_type"] = mime
    if caption and tipo in {"image", "video", "document"}:
        media_obj["caption"] = caption
    if filename and tipo == "document":
        media_obj["filename"] = filename
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": config.waba_id,
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": config.identifier,
                        "phone_number_id": config.phone_number_id,
                    },
                    "contacts": [{
                        "profile": {"name": config.user_name},
                        "wa_id": config.identifier,
                    }],
                    "messages": [{
                        "from": config.identifier,
                        "id": wamid,
                        "timestamp": str(int(time.time())),
                        "type": tipo,
                        tipo: media_obj,
                    }],
                },
                "field": "messages",
            }],
        }],
    }


def build_status_payload(config: ChannelConfig, wamid: str, status: str) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": config.waba_id,
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": config.identifier,
                        "phone_number_id": config.phone_number_id,
                    },
                    "statuses": [{
                        "id": wamid,
                        "recipient_id": config.identifier,
                        "status": status,
                        "timestamp": str(int(time.time())),
                        "conversation": {
                            "id": "MOCK_CONV_ID",
                            "origin": {"type": "service"},
                        },
                        "pricing": {
                            "billable": False,
                            "pricing_model": "CBP",
                            "category": "service",
                        },
                    }],
                },
                "field": "messages",
            }],
        }],
    }
