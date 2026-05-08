import pytest
from src.builders.instagram import build_text_payload, build_delivery_receipt, build_read_receipt
from src.models import ChannelConfig


@pytest.fixture
def config():
    return ChannelConfig(
        webhook_url="http://app/webhook/",
        user_name="Maria",
        identifier="123456789",
        configured=True,
        ig_account_id="IG_ACCOUNT_001",
        ig_page_id="IG_PAGE_001",
    )


class TestBuildTextPayload:
    def test_object_is_instagram(self, config):
        p = build_text_payload(config, "oi", "mid.$mock1234")
        assert p["object"] == "instagram"

    def test_entry_id_is_ig_account(self, config):
        p = build_text_payload(config, "oi", "mid.$mock1234")
        assert p["entry"][0]["id"] == "IG_ACCOUNT_001"

    def test_has_messaging_not_changes(self, config):
        entry = build_text_payload(config, "oi", "mid.$mock1234")["entry"][0]
        assert "messaging" in entry
        assert "changes" not in entry

    def test_sender_id_is_identifier(self, config):
        messaging = build_text_payload(config, "oi", "mid.$mock1234")["entry"][0]["messaging"][0]
        assert messaging["sender"]["id"] == "123456789"

    def test_recipient_id_is_ig_account(self, config):
        messaging = build_text_payload(config, "oi", "mid.$mock1234")["entry"][0]["messaging"][0]
        assert messaging["recipient"]["id"] == "IG_ACCOUNT_001"

    def test_message_mid(self, config):
        messaging = build_text_payload(config, "oi", "mid.$mock1234")["entry"][0]["messaging"][0]
        assert messaging["message"]["mid"] == "mid.$mock1234"

    def test_message_text(self, config):
        messaging = build_text_payload(config, "oi", "mid.$mock1234")["entry"][0]["messaging"][0]
        assert messaging["message"]["text"] == "oi"

    def test_message_flags(self, config):
        msg = build_text_payload(config, "oi", "mid.$mock1234")["entry"][0]["messaging"][0]["message"]
        assert msg["is_deleted"] is False
        assert msg["is_echo"] is False
        assert msg["is_unsupported"] is False

    def test_timestamp_is_int(self, config):
        messaging = build_text_payload(config, "oi", "mid.$mock1234")["entry"][0]["messaging"][0]
        assert isinstance(messaging["timestamp"], int)

    def test_entry_time_is_int(self, config):
        entry = build_text_payload(config, "oi", "mid.$mock1234")["entry"][0]
        assert isinstance(entry["time"], int)


class TestBuildDeliveryReceipt:
    def test_object_is_instagram(self, config):
        p = build_delivery_receipt(config, ["mid.$mock1234"], 1746700000)
        assert p["object"] == "instagram"

    def test_has_delivery_key(self, config):
        messaging = build_delivery_receipt(config, ["mid.$mock1234"], 1746700000)["entry"][0]["messaging"][0]
        assert "delivery" in messaging

    def test_delivery_mids(self, config):
        messaging = build_delivery_receipt(config, ["mid.$mock1234"], 1746700000)["entry"][0]["messaging"][0]
        assert messaging["delivery"]["mids"] == ["mid.$mock1234"]

    def test_delivery_watermark(self, config):
        messaging = build_delivery_receipt(config, ["mid.$mock1234"], 1746700000)["entry"][0]["messaging"][0]
        assert messaging["delivery"]["watermark"] == 1746700000


class TestBuildReadReceipt:
    def test_has_read_key(self, config):
        messaging = build_read_receipt(config, 1746700000)["entry"][0]["messaging"][0]
        assert "read" in messaging

    def test_read_watermark(self, config):
        messaging = build_read_receipt(config, 1746700000)["entry"][0]["messaging"][0]
        assert messaging["read"]["watermark"] == 1746700000

    def test_no_message_key(self, config):
        messaging = build_read_receipt(config, 1746700000)["entry"][0]["messaging"][0]
        assert "message" not in messaging
