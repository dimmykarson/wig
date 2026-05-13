import pytest

from src.builders.instagram import (
    build_delivery_receipt,
    build_media_payload,
    build_read_receipt,
    build_text_payload,
)
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


def _messaging(payload):
    return payload["entry"][0]["messaging"][0]


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
        m = _messaging(build_text_payload(config, "oi", "mid.$mock1234"))
        assert m["sender"]["id"] == "123456789"

    def test_recipient_id_is_ig_account(self, config):
        m = _messaging(build_text_payload(config, "oi", "mid.$mock1234"))
        assert m["recipient"]["id"] == "IG_ACCOUNT_001"

    def test_message_mid(self, config):
        m = _messaging(build_text_payload(config, "oi", "mid.$mock1234"))
        assert m["message"]["mid"] == "mid.$mock1234"

    def test_message_text(self, config):
        m = _messaging(build_text_payload(config, "oi", "mid.$mock1234"))
        assert m["message"]["text"] == "oi"

    def test_message_flags(self, config):
        msg = _messaging(build_text_payload(config, "oi", "mid.$mock1234"))["message"]
        assert msg["is_deleted"] is False
        assert msg["is_echo"] is False
        assert msg["is_unsupported"] is False

    def test_timestamp_is_int(self, config):
        m = _messaging(build_text_payload(config, "oi", "mid.$mock1234"))
        assert isinstance(m["timestamp"], int)

    def test_entry_time_is_int(self, config):
        entry = build_text_payload(config, "oi", "mid.$mock1234")["entry"][0]
        assert isinstance(entry["time"], int)


class TestBuildDeliveryReceipt:
    def test_object_is_instagram(self, config):
        p = build_delivery_receipt(config, ["mid.$mock1234"], 1746700000)
        assert p["object"] == "instagram"

    def test_has_delivery_key(self, config):
        m = _messaging(build_delivery_receipt(config, ["mid.$mock1234"], 1746700000))
        assert "delivery" in m

    def test_delivery_mids(self, config):
        m = _messaging(build_delivery_receipt(config, ["mid.$mock1234"], 1746700000))
        assert m["delivery"]["mids"] == ["mid.$mock1234"]

    def test_delivery_watermark(self, config):
        m = _messaging(build_delivery_receipt(config, ["mid.$mock1234"], 1746700000))
        assert m["delivery"]["watermark"] == 1746700000


class TestBuildMediaPayload:
    def test_object_is_instagram(self, config):
        p = build_media_payload(config, "image", "http://mock/img.jpg", "mid.$m1")
        assert p["object"] == "instagram"

    def test_attachment_type_image(self, config):
        m = _messaging(build_media_payload(config, "image", "http://mock/img.jpg", "mid.$m1"))
        assert m["message"]["attachments"][0]["type"] == "image"

    def test_attachment_url(self, config):
        m = _messaging(build_media_payload(config, "image", "http://mock/img.jpg", "mid.$m1"))
        assert m["message"]["attachments"][0]["payload"]["url"] == "http://mock/img.jpg"

    def test_document_maps_to_file(self, config):
        m = _messaging(build_media_payload(config, "document", "http://mock/f.pdf", "mid.$m2"))
        assert m["message"]["attachments"][0]["type"] == "file"

    def test_audio_type(self, config):
        m = _messaging(build_media_payload(config, "audio", "http://mock/a.ogg", "mid.$m3"))
        assert m["message"]["attachments"][0]["type"] == "audio"

    def test_caption_added_as_text(self, config):
        m = _messaging(
            build_media_payload(config, "image", "http://mock/img.jpg", "mid.$m4", caption="oi")
        )
        assert m["message"].get("text") == "oi"

    def test_no_caption_no_text_key(self, config):
        m = _messaging(build_media_payload(config, "image", "http://mock/img.jpg", "mid.$m5"))
        assert "text" not in m["message"]

    def test_mid_is_set(self, config):
        m = _messaging(build_media_payload(config, "image", "http://mock/img.jpg", "mid.$m6"))
        assert m["message"]["mid"] == "mid.$m6"


class TestBuildReadReceipt:
    def test_has_read_key(self, config):
        m = _messaging(build_read_receipt(config, 1746700000))
        assert "read" in m

    def test_read_watermark(self, config):
        m = _messaging(build_read_receipt(config, 1746700000))
        assert m["read"]["watermark"] == 1746700000

    def test_no_message_key(self, config):
        m = _messaging(build_read_receipt(config, 1746700000))
        assert "message" not in m
