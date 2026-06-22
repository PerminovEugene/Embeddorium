import hashlib


def sha256_hex(text: str) -> str:
    """Stable content/text fingerprint used for provenance and reuse checks."""
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()
