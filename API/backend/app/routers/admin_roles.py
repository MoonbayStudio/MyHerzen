from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case
from sqlalchemy.orm import Session

from backend.app.core.deps import (
    ensure_permission,
    get_current_user,
    get_user_primary_email,
    is_owner,
)
from backend.app.core.features import require_admin_role_management_enabled
from backend.app.db.models import GroupLeader, RoleAuditLog, RoleRequest, UsageLimit, User, UserRole
from backend.app.db.session import get_db
from backend.app.schemas.admin import AdminUserResponse, GrantRoleRequest, RevokeRoleRequest
from backend.app.schemas.roles import AdminRoleRequestResponse, RoleRequestReviewRequest
from backend.app.schemas.user import PendingRoleRequestBadge
from backend.app.services.assistant_policy_service import PLAN_LIMITS
from backend.app.services.roles_service import (
    admin_role_request_to_response,
    build_user_roles,
    get_valid_role_names,
    grant_role_internal,
    subscription_role_request_query,
)
from backend.app.services.user_profile_service import (
    build_user_badges,
    build_user_response,
)
from backend.app.utils.common import normalize_optional_string
from backend.app.utils.email import normalize_email


router = APIRouter(dependencies=[Depends(require_admin_role_management_enabled)])


def build_admin_user_response_single(db: Session, user: User) -> AdminUserResponse:
    roles_for_user = build_user_roles(db=db, user=user)
    badges_for_user = build_user_badges(db=db, user_id=user.id)

    tier = "free"
    role_types = [role["type"] for role in roles_for_user]
    if "admin" in role_types:
        tier = "admin"
    elif "tester" in role_types:
        tier = "tester"
    elif "premium" in role_types:
        tier = "premium"
    elif "plus" in role_types:
        tier = "plus"

    limit = PLAN_LIMITS.get(tier, 10)
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    usage_record = db.query(UsageLimit).filter(
        UsageLimit.user_id == user.id,
        UsageLimit.date == today_str,
        UsageLimit.feature == "assistant_chat",
    ).first()
    used_count = usage_record.used_count if usage_record else 0
    remaining = max(0, limit - used_count) if limit != -1 else -1

    email = (
        normalize_email(user.contact_email)
        or normalize_email(user.email)
        or normalize_email(user.apple_email)
    )

    pending_role_requests = subscription_role_request_query(db).filter(
        RoleRequest.user_id == user.id,
        RoleRequest.status == "pending",
    ).all()
    pending_badges = [
        PendingRoleRequestBadge(
            id=str(role_request.id),
            requestedRole=role_request.role_type,
            createdAt=role_request.created_at,
        )
        for role_request in pending_role_requests
    ]

    return AdminUserResponse(
        id=str(user.id),
        email=email,
        name=user.display_name,
        roles=roles_for_user,
        badges=badges_for_user,
        remainingToday=remaining,
        tier=tier,
        pendingRoleRequests=pending_badges,
    )


@router.post("/admin/roles/grant", response_model=AdminUserResponse)
async def grant_role(
    data: GrantRoleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_permission(db, current_user, "manage_roles")

    requested_role = data.role.strip().lower()
    valid_roles = get_valid_role_names(db)

    if requested_role not in valid_roles:
        raise HTTPException(status_code=400, detail="Invalid role")

    target_user = db.query(User).filter(User.id == data.user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    existing_role = db.query(UserRole).filter(
        UserRole.user_id == data.user_id,
        UserRole.role_type == requested_role,
    ).first()

    if not existing_role:
        grant_role_internal(
            db=db,
            admin_user=current_user,
            target_user=target_user,
            role_name=requested_role,
        )
        db.commit()

    return build_admin_user_response_single(db, target_user)


@router.post("/admin/roles/revoke", response_model=AdminUserResponse)
async def revoke_role(
    data: RevokeRoleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_permission(db, current_user, "manage_roles")

    requested_role = data.role.strip().lower()
    valid_roles = get_valid_role_names(db)

    if requested_role not in valid_roles:
        raise HTTPException(status_code=400, detail="Invalid role")

    target_user = db.query(User).filter(User.id == data.user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if is_owner(target_user) and requested_role == "admin":
        raise HTTPException(
            status_code=403,
            detail="Cannot revoke admin role from owner",
        )

    role = db.query(UserRole).filter(
        UserRole.user_id == data.user_id,
        UserRole.role_type == requested_role,
    ).first()

    if role:
        if requested_role == "admin":
            admin_count = db.query(UserRole).filter(UserRole.role_type == "admin").count()
            if admin_count <= 1:
                if current_user.id == data.user_id:
                    raise HTTPException(
                        status_code=403,
                        detail="Cannot revoke admin from yourself as the last admin",
                    )
                raise HTTPException(status_code=400, detail="Cannot remove the last admin")

        db.delete(role)

        audit_log = RoleAuditLog(
            admin_id=current_user.id,
            target_user_id=data.user_id,
            admin_email=current_user.email
            or current_user.apple_email
            or current_user.contact_email,
            target_email=target_user.email
            or target_user.apple_email
            or target_user.contact_email,
            role_name=requested_role,
            action="revoked",
        )
        db.add(audit_log)

        db.commit()

    return build_admin_user_response_single(db, target_user)


@router.get("/admin/role-requests", response_model=List[AdminRoleRequestResponse])
async def admin_get_role_requests(
    status: str = Query(default="pending"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_permission(db, current_user, "manage_roles")

    allowed_statuses = {"pending", "approved", "rejected", "cancelled", "all"}
    normalized_status = status.strip().lower()

    if normalized_status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Invalid status filter")

    query = subscription_role_request_query(db)

    if normalized_status != "all":
        query = query.filter(RoleRequest.status == normalized_status)

    role_requests = query.order_by(
        case((RoleRequest.status == "pending", 0), else_=1),
        RoleRequest.created_at.desc(),
        RoleRequest.id.desc(),
    ).all()

    if not role_requests:
        return []

    users_by_id = {
        user.id: user
        for user in db.query(User).filter(
            User.id.in_({role_request.user_id for role_request in role_requests})
        ).all()
    }

    return [
        admin_role_request_to_response(
            role_request,
            user=users_by_id.get(role_request.user_id),
        )
        for role_request in role_requests
    ]


@router.post(
    "/admin/role-requests/{request_id}/approve",
    response_model=AdminRoleRequestResponse,
)
async def admin_approve_role_request(
    request_id: int,
    data: Optional[RoleRequestReviewRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_permission(db, current_user, "manage_roles")

    review_data = data or RoleRequestReviewRequest()

    role_request = subscription_role_request_query(db).filter(
        RoleRequest.id == request_id
    ).first()

    if role_request is None:
        raise HTTPException(status_code=404, detail="Role request not found")

    if role_request.status != "pending":
        raise HTTPException(status_code=400, detail="Request is not pending")

    valid_roles = get_valid_role_names(db)
    if role_request.role_type not in valid_roles:
        raise HTTPException(status_code=400, detail="Invalid role")

    target_user = db.query(User).filter(User.id == role_request.user_id).first()
    if target_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    grant_role_internal(
        db=db,
        admin_user=current_user,
        target_user=target_user,
        role_name=role_request.role_type,
    )

    now = datetime.now(timezone.utc)
    role_request.status = "approved"
    role_request.reviewed_at = now
    role_request.moderator_id = current_user.id
    role_request.reviewed_by_admin_email = get_user_primary_email(current_user)
    role_request.review_comment = normalize_optional_string(review_data.comment)

    db.commit()
    db.refresh(role_request)

    return admin_role_request_to_response(role_request, user=target_user)


@router.post(
    "/admin/role-requests/{request_id}/reject",
    response_model=AdminRoleRequestResponse,
)
async def admin_reject_role_request(
    request_id: int,
    data: Optional[RoleRequestReviewRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_permission(db, current_user, "manage_roles")

    review_data = data or RoleRequestReviewRequest()

    role_request = subscription_role_request_query(db).filter(
        RoleRequest.id == request_id
    ).first()

    if role_request is None:
        raise HTTPException(status_code=404, detail="Role request not found")

    if role_request.status != "pending":
        raise HTTPException(status_code=400, detail="Request is not pending")

    now = datetime.now(timezone.utc)
    role_request.status = "rejected"
    role_request.reviewed_at = now
    role_request.moderator_id = current_user.id
    role_request.reviewed_by_admin_email = get_user_primary_email(current_user)
    role_request.review_comment = normalize_optional_string(review_data.comment)

    db.commit()
    db.refresh(role_request)

    target_user = db.query(User).filter(User.id == role_request.user_id).first()
    return admin_role_request_to_response(role_request, user=target_user)


@router.get("/admin/users", response_model=List[AdminUserResponse])
async def admin_get_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_permission(db, current_user, "manage_roles")

    users = db.query(User).all()
    user_responses = []

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    all_user_roles = db.query(UserRole).all()
    user_roles_by_user = {}
    for user_role in all_user_roles:
        user_roles_by_user.setdefault(user_role.user_id, []).append(user_role)

    all_legacy_leaders = db.query(GroupLeader).all()
    legacy_leaders_by_user = {}
    for legacy_leader in all_legacy_leaders:
        legacy_leaders_by_user.setdefault(legacy_leader.user_id, []).append(legacy_leader)

    all_usages = db.query(UsageLimit).filter(
        UsageLimit.date == today_str,
        UsageLimit.feature == "assistant_chat",
    ).all()
    usage_by_user = {usage.user_id: usage.used_count for usage in all_usages}

    pending_role_requests = subscription_role_request_query(db).filter(
        RoleRequest.status == "pending"
    ).order_by(
        RoleRequest.created_at.desc(),
        RoleRequest.id.desc(),
    ).all()
    pending_requests_by_user: Dict[int, List[RoleRequest]] = {}
    for role_request in pending_role_requests:
        pending_requests_by_user.setdefault(role_request.user_id, []).append(role_request)

    for user in users:
        roles_for_user = build_user_roles(
            db=db,
            user=user,
            prefetched_user_roles=user_roles_by_user.get(user.id, []),
            prefetched_legacy_leaders=legacy_leaders_by_user.get(user.id, []),
        )

        tier = "free"
        role_types = [role["type"] for role in roles_for_user]
        if "admin" in role_types:
            tier = "admin"
        elif "tester" in role_types:
            tier = "tester"
        elif "premium" in role_types:
            tier = "premium"
        elif "plus" in role_types:
            tier = "plus"

        limit = PLAN_LIMITS.get(tier, 10)
        used_count = usage_by_user.get(user.id, 0)
        remaining = max(0, limit - used_count) if limit != -1 else -1

        email = (
            normalize_email(user.contact_email)
            or normalize_email(user.email)
            or normalize_email(user.apple_email)
        )

        pending_badges = [
            PendingRoleRequestBadge(
                id=str(role_request.id),
                requestedRole=role_request.role_type,
                createdAt=role_request.created_at,
            )
            for role_request in pending_requests_by_user.get(user.id, [])
        ]

        user_responses.append(
            AdminUserResponse(
                id=str(user.id),
                email=email,
                name=user.display_name,
                roles=roles_for_user,
                badges=build_user_badges(db=db, user_id=user.id),
                remainingToday=remaining,
                tier=tier,
                pendingRoleRequests=pending_badges,
            )
        )

    tier_order = {"admin": 0, "tester": 1, "premium": 2, "plus": 3, "free": 4}
    user_responses.sort(key=lambda item: tier_order.get(item.tier, 99))

    return user_responses
