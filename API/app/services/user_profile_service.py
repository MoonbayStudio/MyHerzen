from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.core.config import APPLE_RELAY_EMAIL_DOMAIN
from app.db.models import AuthProvider, UsageLimit, User, Badge, UserBadge, UserSettings
from app.services.assistant_policy_service import PLAN_LIMITS, get_user_plan
from app.services.roles_service import build_user_roles
from app.utils.common import normalize_optional_string


def normalize_email(value: Any) -> Optional[str]:
    normalized = normalize_optional_string(value)
    if normalized is None:
        return None
    return normalized.lower()


def is_apple_relay_email(email: Optional[str]) -> bool:
    normalized = normalize_email(email)
    if normalized is None:
        return False
    return normalized.endswith(APPLE_RELAY_EMAIL_DOMAIN)


def user_has_password(user: User) -> bool:
    return normalize_optional_string(user.password_hash) is not None


def build_user_badges(db: Session, user_id: int) -> list:
    badges = (
        db.query(Badge)
        .join(UserBadge, UserBadge.badge_id == Badge.id)
        .filter(UserBadge.user_id == user_id)
        .all()
    )
    return [
        {
            "code": badge.code,
            "title": badge.title,
            "description": badge.description,
            "icon_name": badge.icon_name,
            "rarity": badge.rarity,
        }
        for badge in badges
    ]


def build_user_response(db: Session, user: User) -> Dict[str, Any]:
    apple_email = normalize_email(user.apple_email)
    contact_email = normalize_email(user.contact_email)
    legacy_email = normalize_email(user.email)
    linked_providers = set()

    if user.apple_sub:
        linked_providers.add("apple")

    for provider_name in db.query(AuthProvider.provider).filter(
        AuthProvider.user_id == user.id,
    ).all():
        normalized_provider = normalize_optional_string(provider_name[0])
        if normalized_provider is not None:
            linked_providers.add(normalized_provider.lower())

    tier = get_user_plan(user.id, db)
    limit = PLAN_LIMITS.get(tier, 10)
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    usage_record = db.query(UsageLimit).filter(
        UsageLimit.user_id == user.id,
        UsageLimit.date == today_str,
        UsageLimit.feature == "assistant_chat",
    ).first()

    used_count = usage_record.used_count if usage_record else 0
    remaining_today = max(0, limit - used_count) if limit != -1 else -1

    settings = db.query(UserSettings).filter(UserSettings.user_id == user.id).first()
    schedule_cache_weeks = settings.schedule_cache_weeks if settings else 2
    live_activity_enabled = settings.live_activity_enabled if settings else True

    response = {
        "id": str(user.id),
        "displayName": user.display_name,
        "email": contact_email or legacy_email,
        "appleEmail": apple_email,
        "contactEmail": contact_email,
        "contactEmailVerified": bool(user.contact_email_verified)
        if contact_email is not None
        else False,
        "pendingContactEmail": normalize_email(user.pending_contact_email),
        "needsContactEmail": contact_email is None,
        "isAppleRelayEmail": is_apple_relay_email(apple_email or legacy_email),
        "roles": build_user_roles(db=db, user=user),
        "badges": build_user_badges(db=db, user_id=user.id),
        "tier": tier,
        "remainingToday": remaining_today,
        "scheduleCacheWeeks": schedule_cache_weeks,
        "liveActivityEnabled": live_activity_enabled,
        "hasPassword": user_has_password(user),
        "emailVerified": bool(user.contact_email_verified)
        if contact_email is not None
        else False,
        "pendingEmail": normalize_email(user.pending_contact_email),
        "linkedProviders": sorted(linked_providers),
    }

    import json

    print(
        f"DEBUG PROFILE [user={user.id}]: tier={tier}, roles={json.dumps(response['roles'], ensure_ascii=False)}"
    )
    print(f"DEBUG PROFILE JSON: {json.dumps(response, ensure_ascii=False)}")

    return response
