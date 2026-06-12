from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from sqlalchemy.orm import Session

from backend.app.core.deps import get_user_primary_email, has_user_role, is_admin
from backend.app.db.models import (
    GroupLeader,
    Role,
    RoleAuditLog,
    RoleRequest,
    User,
    UserRole,
)
from backend.app.utils.common import normalize_optional_string

SUPPORTED_ROLE_TYPES = {
    "group_leader",
    "moderator",
}

SYSTEM_ROLE_NAMES = {
    "admin",
    "tester",
    "premium",
    "plus",
    "free",
    "group_leader",
    "moderator",
}


ROLE_TITLES = {
    "admin": "Админ",
    "moderator": "Модератор",
    "tester": "Тестировщик",
    "group_leader": "Староста",
    "premium": "Premium",
    "plus": "Plus",
    "student": "Студент",
}


def normalize_role_type(value: str) -> str:
    normalized = normalize_optional_string(value)
    if normalized is None:
        return ""
    return normalized.lower()


def get_valid_role_names(db: Session) -> set[str]:
    db_roles = {role_name for role_name, in db.query(Role.name).all()}
    return db_roles | SYSTEM_ROLE_NAMES


def subscription_role_request_query(db: Session):
    return db.query(RoleRequest).filter(RoleRequest.role_type.notin_(SUPPORTED_ROLE_TYPES))


def grant_role_internal(
    db: Session,
    admin_user: User,
    target_user: User,
    role_name: str,
) -> bool:
    existing_role = db.query(UserRole).filter(
        UserRole.user_id == target_user.id,
        UserRole.role_type == role_name,
    ).first()

    if existing_role:
        return False

    db.add(
        UserRole(
            user_id=target_user.id,
            role_type=role_name,
            granted_by_user_id=admin_user.id,
        )
    )
    db.add(
        RoleAuditLog(
            admin_id=admin_user.id,
            target_user_id=target_user.id,
            admin_email=get_user_primary_email(admin_user),
            target_email=get_user_primary_email(target_user),
            role_name=role_name,
            action="granted",
        )
    )
    return True


def ensure_user_role_exists(
    db: Session,
    user_id: int,
    role_type: str,
    group_id: Optional[int],
    granted_by_user_id: Optional[int],
) -> None:
    if has_user_role(db=db, user_id=user_id, role_type=role_type, group_id=group_id):
        return

    db.add(
        UserRole(
            user_id=user_id,
            role_type=role_type,
            group_id=group_id,
            created_at=datetime.now(timezone.utc),
            granted_by_user_id=granted_by_user_id,
        )
    )


def build_user_roles(
    db: Session,
    user: User,
    prefetched_user_roles: Optional[List[UserRole]] = None,
    prefetched_legacy_leaders: Optional[List[GroupLeader]] = None,
) -> List[Dict[str, Any]]:
    roles: List[Dict[str, Any]] = []

    if is_admin(db, user):
        roles.append({"type": "admin", "title": "Админ"})

    seen_group_ids: Set[int] = set()
    other_roles: Set[str] = set()

    if prefetched_user_roles is not None:
        user_roles = prefetched_user_roles
    else:
        user_roles = db.query(UserRole).filter(UserRole.user_id == user.id).all()

    for user_role in user_roles:
        if user_role.role_type == "group_leader" and user_role.group_id is not None:
            seen_group_ids.add(user_role.group_id)
        elif user_role.role_type != "admin":
            other_roles.add(user_role.role_type)

    if prefetched_legacy_leaders is not None:
        legacy_group_leaders = prefetched_legacy_leaders
    else:
        legacy_group_leaders = db.query(GroupLeader).filter(GroupLeader.user_id == user.id).all()

    for group_leader in legacy_group_leaders:
        seen_group_ids.add(group_leader.group_id)

    for group_id in sorted(seen_group_ids):
        roles.append({"type": "group_leader", "title": "Староста", "groupId": group_id})

    for role_type in sorted(other_roles):
        title = ROLE_TITLES.get(role_type, role_type.capitalize())
        roles.append({"type": role_type, "title": title})

    if not roles:
        roles.append({"type": "student", "title": "Студент"})

    return roles


def me_role_request_to_response(role_request: RoleRequest) -> Dict[str, Any]:
    return {
        "id": str(role_request.id),
        "roleType": role_request.role_type,
        "requestedRole": role_request.role_type,
        "message": role_request.message or role_request.comment,
        "groupId": role_request.group_id,
        "groupName": role_request.group_name,
        "status": role_request.status,
        "createdAt": role_request.created_at,
        "reviewedAt": role_request.reviewed_at,
        "reviewComment": role_request.review_comment,
    }


def admin_role_request_to_response(
    role_request: RoleRequest,
    user: Optional[User] = None,
) -> Dict[str, Any]:
    user_email = role_request.user_email
    if user is not None:
        user_email = get_user_primary_email(user) or user_email

    return {
        "id": str(role_request.id),
        "userId": str(role_request.user_id),
        "userName": user.display_name if user is not None else None,
        "userEmail": user_email,
        "roleType": role_request.role_type,
        "requestedRole": role_request.role_type,
        "message": role_request.message or role_request.comment,
        "groupId": role_request.group_id,
        "groupName": role_request.group_name,
        "status": role_request.status,
        "createdAt": role_request.created_at,
        "reviewedAt": role_request.reviewed_at,
        "reviewedByAdminEmail": role_request.reviewed_by_admin_email,
        "reviewComment": role_request.review_comment,
    }


def leader_request_to_response(leader_request) -> Dict[str, Any]:
    return {
        "id": leader_request.id,
        "userId": leader_request.user_id,
        "groupId": leader_request.group_id,
        "groupName": leader_request.group_name,
        "status": leader_request.status,
        "comment": leader_request.comment,
        "moderatorId": leader_request.moderator_id,
        "createdAt": leader_request.created_at,
        "reviewedAt": leader_request.reviewed_at,
    }


def role_request_to_response(
    role_request: RoleRequest,
    user: Optional[User] = None,
) -> Dict[str, Any]:
    user_email = role_request.user_email
    if user is not None:
        user_email = get_user_primary_email(user) or user_email

    return {
        "id": role_request.id,
        "userId": role_request.user_id,
        "userName": user.display_name if user is not None else None,
        "userEmail": user_email,
        "roleType": role_request.role_type,
        "requestedRole": role_request.role_type,
        "groupId": role_request.group_id,
        "groupName": role_request.group_name,
        "message": role_request.message or role_request.comment,
        "comment": role_request.comment,
        "status": role_request.status,
        "moderatorId": role_request.moderator_id,
        "createdAt": role_request.created_at,
        "reviewedAt": role_request.reviewed_at,
        "reviewedByAdminEmail": role_request.reviewed_by_admin_email,
        "reviewComment": role_request.review_comment,
    }
