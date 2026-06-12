from fastapi import HTTPException

from app.core.config import (
    ENABLE_ADMIN_ROLE_MANAGEMENT_MODULE,
    ENABLE_AI_AGENT,
    ENABLE_HOMEWORK_MODULE,
    ENABLE_ROLE_REQUESTS_MODULE,
)

FEATURE_AI_AGENT = "ai_agent"
FEATURE_HOMEWORK = "homework"
FEATURE_ROLE_REQUESTS = "role_requests"
FEATURE_ADMIN_ROLE_MANAGEMENT = "admin_role_management"


_FEATURE_FLAGS = {
    FEATURE_AI_AGENT: ENABLE_AI_AGENT,
    FEATURE_HOMEWORK: ENABLE_HOMEWORK_MODULE,
    FEATURE_ROLE_REQUESTS: ENABLE_ROLE_REQUESTS_MODULE,
    FEATURE_ADMIN_ROLE_MANAGEMENT: ENABLE_ADMIN_ROLE_MANAGEMENT_MODULE,
}


def ensure_feature_enabled(feature_name: str) -> None:
    is_enabled = _FEATURE_FLAGS.get(feature_name, True)
    if is_enabled:
        return

    raise HTTPException(
        status_code=503,
        detail=f"Feature '{feature_name}' is disabled by configuration",
    )


def require_ai_agent_enabled() -> None:
    ensure_feature_enabled(FEATURE_AI_AGENT)


def require_homework_enabled() -> None:
    ensure_feature_enabled(FEATURE_HOMEWORK)


def require_role_requests_enabled() -> None:
    ensure_feature_enabled(FEATURE_ROLE_REQUESTS)


def require_admin_role_management_enabled() -> None:
    ensure_feature_enabled(FEATURE_ADMIN_ROLE_MANAGEMENT)
