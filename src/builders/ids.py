import uuid


def generate_wamid() -> str:
    return f"wamid.HBgL{uuid.uuid4().hex[:16]}"


def generate_mid() -> str:
    return f"mid.$mock{uuid.uuid4().hex[:16]}"
