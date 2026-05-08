import pytest
from src.builders.whatsapp import build_text_payload, build_status_payload
from src.models import ChannelConfig


@pytest.fixture
def config():
    return ChannelConfig(
        webhook_url="http://app/webhook/",
        user_name="João Silva",
        identifier="5586999990000",
        configured=True,
        waba_id="WABA123",
        phone_number_id="PHONE456",
    )


class TestBuildTextPayload:
    def test_object_field(self, config):
        p = build_text_payload(config, "olá", "wamid.HBgLabc123")
        assert p["object"] == "whatsapp_business_account"

    def test_entry_id_is_waba_id(self, config):
        p = build_text_payload(config, "olá", "wamid.HBgLabc123")
        assert p["entry"][0]["id"] == "WABA123"

    def test_field_is_messages(self, config):
        p = build_text_payload(config, "olá", "wamid.HBgLabc123")
        assert p["entry"][0]["changes"][0]["field"] == "messages"

    def test_messaging_product(self, config):
        value = build_text_payload(config, "olá", "wamid.HBgLabc123")["entry"][0]["changes"][0]["value"]
        assert value["messaging_product"] == "whatsapp"

    def test_metadata_fields(self, config):
        value = build_text_payload(config, "olá", "wamid.HBgLabc123")["entry"][0]["changes"][0]["value"]
        assert value["metadata"]["display_phone_number"] == "5586999990000"
        assert value["metadata"]["phone_number_id"] == "PHONE456"

    def test_contact_name_and_wa_id(self, config):
        value = build_text_payload(config, "olá", "wamid.HBgLabc123")["entry"][0]["changes"][0]["value"]
        contact = value["contacts"][0]
        assert contact["profile"]["name"] == "João Silva"
        assert contact["wa_id"] == "5586999990000"

    def test_message_from_and_id(self, config):
        msg = build_text_payload(config, "olá", "wamid.HBgLabc123")["entry"][0]["changes"][0]["value"]["messages"][0]
        assert msg["from"] == "5586999990000"
        assert msg["id"] == "wamid.HBgLabc123"

    def test_message_type_is_text(self, config):
        msg = build_text_payload(config, "olá", "wamid.HBgLabc123")["entry"][0]["changes"][0]["value"]["messages"][0]
        assert msg["type"] == "text"

    def test_message_body(self, config):
        msg = build_text_payload(config, "olá", "wamid.HBgLabc123")["entry"][0]["changes"][0]["value"]["messages"][0]
        assert msg["text"]["body"] == "olá"

    def test_timestamp_is_string(self, config):
        msg = build_text_payload(config, "olá", "wamid.HBgLabc123")["entry"][0]["changes"][0]["value"]["messages"][0]
        assert isinstance(msg["timestamp"], str)
        assert msg["timestamp"].isdigit()


class TestBuildStatusPayload:
    def test_field_is_messages(self, config):
        p = build_status_payload(config, "wamid.HBgLabc123", "delivered")
        assert p["entry"][0]["changes"][0]["field"] == "messages"

    def test_has_statuses_not_messages(self, config):
        value = build_status_payload(config, "wamid.HBgLabc123", "delivered")["entry"][0]["changes"][0]["value"]
        assert "statuses" in value
        assert "messages" not in value

    def test_status_value(self, config):
        value = build_status_payload(config, "wamid.HBgLabc123", "read")["entry"][0]["changes"][0]["value"]
        assert value["statuses"][0]["status"] == "read"

    def test_status_id_matches_wamid(self, config):
        value = build_status_payload(config, "wamid.HBgLabc123", "delivered")["entry"][0]["changes"][0]["value"]
        assert value["statuses"][0]["id"] == "wamid.HBgLabc123"

    def test_has_conversation_field(self, config):
        value = build_status_payload(config, "wamid.HBgLabc123", "delivered")["entry"][0]["changes"][0]["value"]
        assert "conversation" in value["statuses"][0]

    def test_has_pricing_field(self, config):
        value = build_status_payload(config, "wamid.HBgLabc123", "delivered")["entry"][0]["changes"][0]["value"]
        assert "pricing" in value["statuses"][0]

    def test_recipient_id(self, config):
        value = build_status_payload(config, "wamid.HBgLabc123", "delivered")["entry"][0]["changes"][0]["value"]
        assert value["statuses"][0]["recipient_id"] == "5586999990000"
