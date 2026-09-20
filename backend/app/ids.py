import re
import secrets


def new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6)}"


def slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return s or "item"
