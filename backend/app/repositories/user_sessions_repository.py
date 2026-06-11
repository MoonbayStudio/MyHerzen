from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.app.db.models import UserSession


def get_session_by_id(db: Session, session_id: int) -> Optional[UserSession]:
    return db.query(UserSession).filter(UserSession.id == session_id).first()


def get_user_session_by_hash(
    db: Session,
    user_id: int,
    session_token_hash: str,
) -> Optional[UserSession]:
    return db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.session_token_hash == session_token_hash,
    ).first()


def list_user_sessions(db: Session, user_id: int) -> List[UserSession]:
    return db.query(UserSession).filter(
        UserSession.user_id == user_id,
    ).order_by(
        UserSession.last_seen_at.desc(),
        UserSession.id.desc(),
    ).all()


def create_user_session(
    db: Session,
    user_id: int,
    session_token_hash: str,
    created_at: datetime,
) -> UserSession:
    session = UserSession(
        user_id=user_id,
        session_token_hash=session_token_hash,
        created_at=created_at,
        last_seen_at=created_at,
    )
    db.add(session)
    return session


def revoke_session(
    session: UserSession,
    revoked_at: datetime,
) -> None:
    session.revoked_at = revoked_at
