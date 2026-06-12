import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import requests
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.core.config import (
    APPLE_KEYS_URL,
    EMAIL_VERIFICATION_EXPIRES_HOURS,
    FRONTEND_BASE_URL,
    RESEND_API_KEY,
    RESEND_API_URL,
    RESEND_FROM_EMAIL,
)
from backend.app.db.models import User
from backend.app.services.user_profile_service import is_apple_relay_email, normalize_email
from backend.app.utils.common import normalize_optional_string
from backend.app.utils.email import EMAIL_VERIFICATION_PATTERN


apple_keys_cache = None


def get_apple_keys():
    global apple_keys_cache

    if apple_keys_cache is None:
        response = requests.get(APPLE_KEYS_URL, timeout=30)
        response.raise_for_status()
        apple_keys_cache = response.json()["keys"]

    return apple_keys_cache


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
            detail="Apple relay email cannot be used as contact email",
        )

    return normalized


def hash_contact_email_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def ensure_contact_email_available(
    db: Session,
    email: str,
    user_id: int,
) -> None:
    existing_user = db.query(User).filter(
        func.lower(User.contact_email) == email,
        User.id != user_id,
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


def apply_apple_email_to_user(
    user: User,
    apple_sub: str,
    apple_email: Optional[str],
) -> None:
    normalized_apple_email = normalize_email(apple_email)

    user.apple_sub = apple_sub

    if normalized_apple_email is None:
        return

    user.apple_email = normalized_apple_email

    if normalize_email(user.email) is None:
        user.email = normalized_apple_email

    if normalize_email(user.contact_email) is None and not is_apple_relay_email(normalized_apple_email):
        user.contact_email = normalized_apple_email
        user.contact_email_verified = False
        user.contact_email_verified_at = None


def apply_google_email_to_user(
    user: User,
    google_email: Optional[str],
) -> None:
    normalized_google_email = normalize_email(google_email)

    if normalized_google_email is None:
        return

    if normalize_email(user.email) is None:
        user.email = normalized_google_email

    if normalize_email(user.contact_email) is None:
        user.contact_email = normalized_google_email
        user.contact_email_verified = True  # Google emails are verified
        user.contact_email_verified_at = datetime.now(timezone.utc)
    elif normalize_email(user.contact_email) == normalized_google_email:
        user.contact_email_verified = True
        user.contact_email_verified_at = datetime.now(timezone.utc)


def clear_pending_contact_email(user: User) -> None:
    user.pending_contact_email = None
    user.pending_contact_email_token_hash = None
    user.pending_contact_email_expires_at = None


def create_pending_email_verification_code(user: User, email: str) -> str:
    code = f"{secrets.randbelow(1000000):06d}"
    now = datetime.now(timezone.utc)

    user.pending_contact_email = email
    user.pending_contact_email_token_hash = hash_contact_email_token(code)
    user.pending_contact_email_expires_at = now + timedelta(minutes=15)
    user.updated_at = now

    return code


def create_password_reset_code(user: User) -> str:
    code = f"{secrets.randbelow(1000000):06d}"
    now = datetime.now(timezone.utc)

    user.password_reset_token_hash = hash_contact_email_token(code)
    user.password_reset_expires_at = now + timedelta(minutes=15)
    user.updated_at = now

    return code


def send_password_reset_code(email: str, code: str) -> None:
    api_key = normalize_optional_string(RESEND_API_KEY)

    if api_key is None:
        print(f"DEV MODE: Password reset code for {email} is {code}", flush=True)
        return

    payload = {
        "from": RESEND_FROM_EMAIL,
        "to": [email],
        "subject": "Сброс пароля MyHerzen",
        "text": f"Код для сброса пароля: {code}\nКод действует 15 минут.",
        "html": f"<p>Код для сброса пароля: <strong>{code}</strong></p><p>Код действует 15 минут.</p>",
    }

    try:
        requests.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
    except requests.RequestException:
        pass


def send_email_verification_code(email: str, code: str) -> None:
    api_key = normalize_optional_string(RESEND_API_KEY)

    if api_key is None:
        print(f"DEV MODE: Verification code for {email} is {code}", flush=True)
        return

    payload = {
        "from": RESEND_FROM_EMAIL,
        "to": [email],
        "subject": "Код подтверждения MyHerzen",
        "text": f"Ваш код подтверждения: {code}\nКод действует 15 минут.",
        "html": f"<p>Ваш код подтверждения: <strong>{code}</strong></p><p>Код действует 15 минут.</p>",
    }

    try:
        response = requests.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=10,
        )
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="Failed to send verification email")

    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail="Failed to send verification email")


def send_contact_email_verification(email: str, token: str) -> None:
    api_key = normalize_optional_string(RESEND_API_KEY)

    if api_key is None:
        raise HTTPException(status_code=500, detail="Email service is not configured")

    verification_link = f"{FRONTEND_BASE_URL}/verify-email?token={token}"

    payload = {
        "from": RESEND_FROM_EMAIL,
        "to": [email],
        "subject": "Подтвердите email в MyHerzen",
        "text": (
            "Подтвердите контактную почту MyHerzen: "
            f"{verification_link}\n\n"
            "Ссылка действует 24 часа."
        ),
        "html": (
            "<p>Подтвердите контактную почту MyHerzen.</p>"
            f'<p><a href="{verification_link}">Подтвердить email</a></p>'
            "<p>Ссылка действует 24 часа.</p>"
        ),
    }

    try:
        response = requests.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=10,
        )
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="Failed to send verification email")

    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail="Failed to send verification email")


def normalize_datetime(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)
