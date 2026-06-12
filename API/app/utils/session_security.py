import hashlib
from typing import Optional

from backend.app.core.config import JWT_SECRET


_ALLOWED_PLATFORMS = {
    "android": "android",
    "ios": "iOS",
    "macos": "macOS",
    "web": "web",
    "unknown": "unknown",
}


def hash_session_token(token: str) -> str:
    token_material = f"{JWT_SECRET}:{token}"
    return hashlib.sha256(token_material.encode("utf-8")).hexdigest()


def extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        return None
    token = authorization[len(prefix):].strip()
    if not token:
        return None
    return token


def normalize_platform(value: Optional[str]) -> str:
    if not isinstance(value, str):
        return "unknown"
    normalized = value.strip().lower()
    if not normalized:
        return "unknown"
    return _ALLOWED_PLATFORMS.get(normalized, "unknown")


def mask_ip_address(ip_address: Optional[str]) -> Optional[str]:
    if not isinstance(ip_address, str):
        return None
    normalized = ip_address.strip()
    if not normalized:
        return None

    if "." in normalized:
        parts = normalized.split(".")
        if len(parts) == 4:
            return ".".join(parts[:3] + ["*"])

    if ":" in normalized:
        parts = normalized.split(":")
        if len(parts) >= 2:
            return ":".join(parts[:2]) + ":*"

    return "*"
