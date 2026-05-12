import re

from src.builders.ids import generate_mid, generate_wamid


def test_wamid_starts_with_prefix():
    assert generate_wamid().startswith("wamid.HBgL")


def test_wamid_unique():
    assert generate_wamid() != generate_wamid()


def test_wamid_hex_suffix_length():
    wamid = generate_wamid()
    suffix = wamid.removeprefix("wamid.HBgL")
    assert len(suffix) == 16
    assert re.fullmatch(r"[0-9a-f]{16}", suffix)


def test_mid_starts_with_prefix():
    assert generate_mid().startswith("mid.$mock")


def test_mid_unique():
    assert generate_mid() != generate_mid()


def test_mid_hex_suffix_length():
    mid = generate_mid()
    suffix = mid.removeprefix("mid.$mock")
    assert len(suffix) == 16
    assert re.fullmatch(r"[0-9a-f]{16}", suffix)
