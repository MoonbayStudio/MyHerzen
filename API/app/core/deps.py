from typing import Optional, Tuple
from fastapi import Header, Depends, HTTPException
from sqlalchemy.orm import Session
from jose import jwt

from app.core.config import (
    JWT_SECRET,
    OWNER_EMAILS_SET,
    ADMIN_EMAIL_SET,
    ROLE_PERMISSIONS,
)
from app.db.session import get_db
from app.db.models import User, UserSettings, UserRole, GroupLeader, GroupMembership
from app.utils.email import normalize_email
from app.utils.session_security import extract_bearer_token
from app.services.user_sessions_service import assert_session_active_for_token


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db)
):
    token = extract_bearer_token(authorization)
    if token is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=["HS256"]
        )

        user_id = payload.get("user_id")

        if user_id is None:
            raise HTTPException(status_code=401, detail="Unauthorized")

        user = db.query(User).filter(User.id == int(user_id)).first()

        if user is None:
            raise HTTPException(status_code=401, detail="Unauthorized")

        assert_session_active_for_token(
            db=db,
            user_id=user.id,
            session_token=token,
        )

        return user

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized")

def get_optional_user(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db)
) -> Optional[User]:
    if not authorization:
        return None
    try:
        return get_current_user(authorization=authorization, db=db)
    except HTTPException:
        return None

def get_user_settings_by_user_id(
    db: Session,
    user_id: int
) -> Optional[UserSettings]:
    return db.query(UserSettings).filter(
        UserSettings.user_id == user_id
    ).first()

def can_access_group(
    db: Session,
    user_id: int,
    group_id: int
) -> bool:
    settings = db.query(UserSettings).filter(
        UserSettings.user_id == user_id,
        UserSettings.selected_group_id == group_id
    ).first()

    if settings is not None:
        return True

    membership = db.query(GroupMembership).filter(
        GroupMembership.user_id == user_id,
        GroupMembership.group_id == group_id,
        GroupMembership.status == "active"
    ).first()

    if membership is not None:
        return True

    return False

def ensure_group_access(
    db: Session,
    user_id: int,
    group_id: int
) -> None:
    if not can_access_group(db=db, user_id=user_id, group_id=group_id):
        raise HTTPException(
            status_code=403,
            detail="Forbidden for this group"
        )

def ensure_group_leader(
    db: Session,
    user_id: int,
    group_id: int
) -> None:
    legacy_leader = db.query(GroupLeader).filter(
        GroupLeader.user_id == user_id,
        GroupLeader.group_id == group_id
    ).first()

    user_role_leader = db.query(UserRole).filter(
        UserRole.user_id == user_id,
        UserRole.role_type == "group_leader",
        UserRole.group_id == group_id
    ).first()

    if legacy_leader is None and user_role_leader is None:
        raise HTTPException(
            status_code=403,
            detail="Only group leader can add homework"
        )

def is_owner(user: User) -> bool:
    candidate_emails = [
        normalize_email(user.contact_email),
        normalize_email(user.email),
        normalize_email(user.apple_email)
    ]
    for normalized_email in candidate_emails:
        if normalized_email is not None and normalized_email in OWNER_EMAILS_SET:
            return True
    return False

def has_permission(user: User, permission_name: str, db: Session) -> bool:
    if is_owner(user):
        return True
    
    if db:
        user_roles = db.query(UserRole).filter(UserRole.user_id == user.id).all()
        for role in user_roles:
            if role.role_type in ROLE_PERMISSIONS:
                if permission_name in ROLE_PERMISSIONS[role.role_type]:
                    return True
    return False

def ensure_permission(db: Session, user: User, permission_name: str) -> None:
    if not has_permission(user, permission_name, db):
        raise HTTPException(status_code=403, detail=f"Permission {permission_name} required")

def get_user_primary_email(user: User) -> Optional[str]:
    return (
        normalize_email(user.contact_email)
        or normalize_email(user.email)
        or normalize_email(user.apple_email)
    )

def is_admin(db: Session, user: User) -> bool:
    if is_owner(user):
        return True

    candidate_emails = [
        normalize_email(user.contact_email),
        normalize_email(user.email),
        normalize_email(user.apple_email)
    ]

    for normalized_email in candidate_emails:
        if normalized_email is None:
            continue

        if normalized_email in ADMIN_EMAIL_SET:
            return True

    if db:
        admin_role = db.query(UserRole).filter(
            UserRole.user_id == user.id,
            UserRole.role_type == "admin"
        ).first()
        if admin_role:
            return True

    return False

def is_moderator(db: Session, user: User) -> bool:
    moderator_role = db.query(UserRole).filter(
        UserRole.user_id == user.id,
        UserRole.role_type == "moderator"
    ).first()

    return moderator_role is not None

def ensure_admin_or_moderator(
    db: Session,
    user: User
) -> Tuple[bool, bool]:
    admin_access = is_admin(db, user)
    moderator_access = is_moderator(db=db, user=user)

    if not admin_access and not moderator_access:
        raise HTTPException(
            status_code=403,
            detail="Moderator or admin access required"
        )

    return admin_access, moderator_access

def has_user_role(
    db: Session,
    user_id: int,
    role_type: str,
    group_id: Optional[int] = None
) -> bool:
    role = db.query(UserRole).filter(
        UserRole.user_id == user_id,
        UserRole.role_type == role_type,
        UserRole.group_id == group_id
    ).first()

    return role is not None

def user_has_group_leader_role(
    db: Session,
    user_id: int,
    group_id: int
) -> bool:
    membership = db.query(GroupMembership).filter(
        GroupMembership.user_id == user_id,
        GroupMembership.group_id == group_id,
        GroupMembership.status == "active",
        GroupMembership.role == "group_leader"
    ).first()
    return membership is not None

def group_has_other_leader(
    db: Session,
    group_id: int,
    exclude_user_id: int
) -> bool:
    user_role_leader = db.query(UserRole).filter(
        UserRole.role_type == "group_leader",
        UserRole.group_id == group_id,
        UserRole.user_id != exclude_user_id
    ).first()

    if user_role_leader is not None:
        return True

    legacy_leader = db.query(GroupLeader).filter(
        GroupLeader.group_id == group_id,
        GroupLeader.user_id != exclude_user_id
    ).first()

    return legacy_leader is not None
