import re
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Any, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.models import User
from app.core.config import (
    APPLE_RELAY_EMAIL_DOMAIN,
    EMAIL_VERIFICATION_EXPIRES_HOURS
)

EMAIL_VERIFICATION_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def normalize_optional_string(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    return str(value).strip() or None

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

def validate_contact_email(value: Any) -> str:
    normalized = normalize_email(value)
    if (
        normalized is None
        or len(normalized) > 254
        or EMAIL_VERIFICATION_PATTERN.fullmatch(normalized) is None
    ):
        raise HTTPException(status_code=400, detail="Invalid email")

    if is_apple_relay_email(normalized):
        raise HTTPException(
            status_code=400,
            detail="Apple relay email cannot be used as contact email"
        )
    return normalized

def hash_contact_email_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def ensure_contact_email_available(db: Session, email: str, user_id: int) -> None:
    existing_user = db.query(User).filter(
        func.lower(User.contact_email) == email,
        User.id != user_id
    ).first()
    if existing_user is not None:
        raise HTTPException(status_code=400, detail="Email is already in use")

def create_pending_contact_email_token(user: User, email: str) -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    user.pending_contact_email = email
    user.pending_contact_email_token_hash = hash_contact_email_token(token)
    user.pending_contact_email_expires_at = now + timedelta(hours=EMAIL_VERIFICATION_EXPIRES_HOURS)
    user.updated_at = now
    return token
