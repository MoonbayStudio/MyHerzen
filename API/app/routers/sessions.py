from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, is_admin
from app.db.models import User
from app.db.session import get_db
from app.schemas.sessions import (
    AccountSessionResponse,
    AdminUserSessionResponse,
    LogoutOthersResponse,
    SessionRevokeResponse,
)
from app.utils.session_security import extract_bearer_token
from app.services import user_sessions_service


router = APIRouter()


def _require_admin(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if not is_admin(db, current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/account/sessions", response_model=list[AccountSessionResponse])
def get_account_sessions(
    authorization: str | None = Header(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_token = extract_bearer_token(authorization)
    return user_sessions_service.list_account_sessions(
        db=db,
        user_id=current_user.id,
        current_session_token=current_token,
    )


@router.delete("/account/sessions/{session_id}", response_model=SessionRevokeResponse)
def revoke_account_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    revoked_at = user_sessions_service.revoke_own_session(
        db=db,
        user_id=current_user.id,
        session_id=session_id,
    )
    return {
        "success": True,
        "revokedAt": revoked_at,
    }


@router.post("/account/sessions/logout-others", response_model=LogoutOthersResponse)
def logout_other_sessions(
    authorization: str | None = Header(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_token = extract_bearer_token(authorization)
    revoked_count = user_sessions_service.revoke_other_sessions(
        db=db,
        user_id=current_user.id,
        current_session_token=current_token,
    )
    return {
        "success": True,
        "revokedCount": revoked_count,
        "note": "Existing JWTs may stay valid until expiry for clients without session checks.",
    }


@router.get("/admin/users/{user_id}/sessions", response_model=list[AdminUserSessionResponse])
def admin_get_user_sessions(
    user_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(_require_admin),
):
    _ = admin_user
    return user_sessions_service.list_user_sessions_for_admin(
        db=db,
        user_id=user_id,
    )


@router.post("/admin/sessions/{session_id}/revoke", response_model=SessionRevokeResponse)
def admin_revoke_session(
    session_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(_require_admin),
):
    _ = admin_user
    _, revoked_at = user_sessions_service.revoke_session_by_admin(
        db=db,
        session_id=session_id,
    )
    return {
        "success": True,
        "revokedAt": revoked_at,
    }
