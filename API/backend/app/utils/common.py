from typing import Any, Optional


def normalize_optional_string(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None

    normalized = value.strip()
    if not normalized:
        return None

    return normalized


def parse_int(value: Any) -> Optional[int]:
    if value is None or isinstance(value, bool):
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None
