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
