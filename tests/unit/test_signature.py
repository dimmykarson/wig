import hashlib
import hmac

from src.builders.signature import compute_signature, verify_signature

SECRET = "test-secret"
BODY = b'{"object":"whatsapp_business_account"}'


def test_signature_starts_with_sha256_prefix():
    sig = compute_signature(SECRET, BODY)
    assert sig.startswith("sha256=")


def test_signature_is_valid_hmac():
    sig = compute_signature(SECRET, BODY)
    expected = "sha256=" + hmac.new(SECRET.encode(), BODY, hashlib.sha256).hexdigest()
    assert sig == expected


def test_signature_changes_with_body():
    sig1 = compute_signature(SECRET, BODY)
    sig2 = compute_signature(SECRET, b'{"object":"instagram"}')
    assert sig1 != sig2


def test_signature_changes_with_secret():
    sig1 = compute_signature("secret-a", BODY)
    sig2 = compute_signature("secret-b", BODY)
    assert sig1 != sig2


def test_verify_signature_valid():
    sig = compute_signature(SECRET, BODY)
    assert verify_signature(SECRET, BODY, sig) is True


def test_verify_signature_invalid():
    assert verify_signature(SECRET, BODY, "sha256=invalido") is False


def test_verify_signature_wrong_secret():
    sig = compute_signature(SECRET, BODY)
    assert verify_signature("outro-secret", BODY, sig) is False
