from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.db.models import UserSession
from backend.app.repositories import user_sessions_repository
from backend.app.utils.session_security import (
    hash_session_token,
    mask_ip_address,
    normalize_platform,
)


@dataclass
class SessionTrackingInput:
    session_token: str
    device_id: Optional[str] = None
    device_name: Optional[str] = None
    platform: Optional[str] = None
    app_version: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


def _normalize_optional_text(value: Optional[str], max_len: int) -> Optional[str]:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > max_len:
        return normalized[:max_len]
    return normalized


def track_login_session(
    db: Session,
    user_id: int,
    payload: SessionTrackingInput,
) -> UserSession:
    now = datetime.now(timezone.utc)
    session_hash = hash_session_token(payload.session_token)

    existing_session = user_sessions_repository.get_user_session_by_hash(
        db=db,
        user_id=user_id,
        session_token_hash=session_hash,
    )

    if existing_session is None:
        session = user_sessions_repository.create_user_session(
            db=db,
            user_id=user_id,
            session_token_hash=session_hash,
            created_at=now,
        )
    else:
        session = existing_session

    session.device_id = _normalize_optional_text(payload.device_id, 255)
    session.device_name = _normalize_optional_text(payload.device_name, 255)
    session.platform = normalize_platform(payload.platform)
    session.app_version = _normalize_optional_text(payload.app_version, 64)
    session.ip_address = _normalize_optional_text(payload.ip_address, 128)
    session.user_agent = _normalize_optional_text(payload.user_agent, 1024)
    session.last_seen_at = now
    if session.created_at is None:
        session.created_at = now
    if session.revoked_at is not None:
        session.revoked_at = None

    db.commit()
    db.refresh(session)
    return session


def serialize_account_session(
    session: UserSession,
    current_token_hash: Optional[str],
) -> dict[str, Any]:
    return {
        "id": session.id,
        "deviceId": session.device_id,
        "deviceName": session.device_name,
        "platform": session.platform,
        "appVersion": session.app_version,
        "ipAddress": mask_ip_address(session.ip_address),
        "userAgent": session.user_agent,
        "createdAt": session.created_at,
        "lastSeenAt": session.last_seen_at,
        "revokedAt": session.revoked_at,
        "isCurrent": (
            bool(current_token_hash)
            and current_token_hash == session.session_token_hash
            and session.revoked_at is None
        ),
    }


def serialize_admin_session(session: UserSession) -> dict[str, Any]:
    return {
        "id": session.id,
        "userId": session.user_id,
        "deviceId": session.device_id,
        "deviceName": session.device_name,
        "platform": session.platform,
        "appVersion": session.app_version,
        "ipAddress": session.ip_address,
        "userAgent": session.user_agent,
        "createdAt": session.created_at,
        "lastSeenAt": session.last_seen_at,
        "revokedAt": session.revoked_at,
    }


def list_account_sessions(
    db: Session,
    user_id: int,
    current_session_token: Optional[str],
) -> list[dict[str, Any]]:
    current_token_hash = (
        hash_session_token(current_session_token)
        if isinstance(current_session_token, str) and current_session_token.strip()
        else None
    )

    sessions = user_sessions_repository.list_user_sessions(db=db, user_id=user_id)
    return [
        serialize_account_session(session=session, current_token_hash=current_token_hash)
        for session in sessions
    ]


def list_user_sessions_for_admin(db: Session, user_id: int) -> list[dict[str, Any]]:
    sessions = user_sessions_repository.list_user_sessions(db=db, user_id=user_id)
    return [serialize_admin_session(session=session) for session in sessions]


def revoke_own_session(db: Session, user_id: int, session_id: int) -> datetime:
    session = user_sessions_repository.get_session_by_id(db=db, session_id=session_id)
    if session is None or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Session not found")

    revoked_at = datetime.now(timezone.utc)
    user_sessions_repository.revoke_session(session=session, revoked_at=revoked_at)

    # TODO: Stateless JWT tokens are still technically valid until expiry.
    # To enforce hard invalidation, add a token/session denylist check in auth middleware.
    db.commit()
    return revoked_at


def revoke_session_by_admin(db: Session, session_id: int) -> tuple[int, datetime]:
    session = user_sessions_repository.get_session_by_id(db=db, session_id=session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    revoked_at = datetime.now(timezone.utc)
    user_sessions_repository.revoke_session(session=session, revoked_at=revoked_at)

    # TODO: Stateless JWT tokens are still technically valid until expiry.
    # To enforce hard invalidation, add a token/session denylist check in auth middleware.
    db.commit()
    return session.user_id, revoked_at


def revoke_other_sessions(
    db: Session,
    user_id: int,
    current_session_token: Optional[str],
) -> int:
    sessions = user_sessions_repository.list_user_sessions(db=db, user_id=user_id)
    now = datetime.now(timezone.utc)

    current_hash = (
        hash_session_token(current_session_token)
        if isinstance(current_session_token, str) and current_session_token.strip()
        else None
    )

    revoked_count = 0
    for session in sessions:
        if session.revoked_at is not None:
            continue
        if current_hash and session.session_token_hash == current_hash:
            continue
        session.revoked_at = now
        revoked_count += 1

    # TODO: Stateless JWT tokens are still technically valid until expiry.
    # To enforce hard invalidation, add a token/session denylist check in auth middleware.
    db.commit()

    return revoked_count


def assert_session_active_for_token(
    db: Session,
    user_id: int,
    session_token: Optional[str],
) -> None:
    if not isinstance(session_token, str) or not session_token.strip():
        return

    session_hash = hash_session_token(session_token)
    session = user_sessions_repository.get_user_session_by_hash(
        db=db,
        user_id=user_id,
        session_token_hash=session_hash,
    )

    if session is None:
        return

    if session.revoked_at is not None:
        raise HTTPException(status_code=401, detail="Unauthorized")
