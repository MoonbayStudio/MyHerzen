from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.deps import (
    ensure_admin_or_moderator,
    ensure_permission,
    get_current_user,
    get_user_primary_email,
    get_user_settings_by_user_id,
    group_has_other_leader,
    has_user_role,
    user_has_group_leader_role,
)
from backend.app.core.features import require_role_requests_enabled
from backend.app.db.models import GroupLeader, LeaderRequest, RoleRequest, User
from backend.app.db.session import get_db
from backend.app.schemas.roles import (
    LeaderRequestCreateRequest,
    LeaderRequestRejectRequest,
    LeaderRequestResponse,
    MeRoleRequestCreateRequest,
    MeRoleRequestResponse,
    RoleRequestCreateRequest,
    RoleRequestRejectRequest,
    RoleRequestResponse,
)
from backend.app.services.roles_service import (
    ensure_user_role_exists,
    get_valid_role_names,
    leader_request_to_response,
    me_role_request_to_response,
    normalize_role_type,
    role_request_to_response,
    subscription_role_request_query,
)
from backend.app.utils.common import normalize_optional_string


router = APIRouter(dependencies=[Depends(require_role_requests_enabled)])


@router.post("/role-requests", response_model=RoleRequestResponse)
async def create_role_request(
    data: RoleRequestCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role_type = normalize_role_type(data.roleType)

    valid_roles = get_valid_role_names(db)
    if role_type not in valid_roles:
        raise HTTPException(status_code=400, detail="Invalid roleType")

    if role_type == "admin":
        raise HTTPException(status_code=400, detail="Cannot request admin role")

    settings = get_user_settings_by_user_id(db=db, user_id=current_user.id)
    selected_group_id = settings.selected_group_id if settings is not None else None
    selected_group_name = (
        normalize_optional_string(settings.selected_group_name)
        if settings is not None
        else None
    )

    role_group_id: Optional[int] = data.groupId or selected_group_id
    role_group_name: Optional[str] = normalize_optional_string(data.groupName)
    role_comment = normalize_optional_string(data.comment)

    if role_group_name is None:
        role_group_name = selected_group_name

    if role_type == "group_leader":
        if role_group_id is None:
            raise HTTPException(
                status_code=400,
                detail="groupId is required for group_leader request",
            )

        if selected_group_id != role_group_id:
            raise HTTPException(
                status_code=403,
                detail="You can request group_leader only for selected group",
            )

        if user_has_group_leader_role(
            db=db,
            user_id=current_user.id,
            group_id=role_group_id,
        ):
            raise HTTPException(
                status_code=400,
                detail="User is already group leader for this group",
            )

    if role_type == "moderator":
        if has_user_role(
            db=db,
            user_id=current_user.id,
            role_type="moderator",
            group_id=None,
        ):
            raise HTTPException(status_code=400, detail="User is already moderator")
    elif role_type != "group_leader" and has_user_role(
        db=db,
        user_id=current_user.id,
        role_type=role_type,
        group_id=None,
    ):
        raise HTTPException(status_code=400, detail="User already has this role")

    duplicate_query = db.query(RoleRequest).filter(
        RoleRequest.user_id == current_user.id,
        RoleRequest.role_type == role_type,
        RoleRequest.status == "pending",
    )

    if role_type == "group_leader":
        duplicate_query = duplicate_query.filter(RoleRequest.group_id == role_group_id)

    duplicate_pending = duplicate_query.first()

    if duplicate_pending is not None:
        raise HTTPException(status_code=400, detail="Pending role request already exists")

    role_request = RoleRequest(
        user_id=current_user.id,
        user_email=get_user_primary_email(current_user),
        role_type=role_type,
        group_id=role_group_id,
        group_name=role_group_name,
        comment=role_comment,
        message=role_comment,
        status="pending",
        created_at=datetime.now(timezone.utc),
    )

    db.add(role_request)
    db.commit()
    db.refresh(role_request)

    return role_request_to_response(role_request, user=current_user)


@router.get("/role-requests/me", response_model=List[RoleRequestResponse])
async def get_my_role_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role_requests = db.query(RoleRequest).filter(
        RoleRequest.user_id == current_user.id
    ).order_by(
        RoleRequest.created_at.desc(),
        RoleRequest.id.desc(),
    ).all()

    return [
        role_request_to_response(role_request, user=current_user)
        for role_request in role_requests
    ]


@router.post("/me/role-requests", response_model=MeRoleRequestResponse)
async def create_my_role_request(
    data: MeRoleRequestCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    valid_roles = get_valid_role_names(db)

    if data.role not in valid_roles:
        raise HTTPException(status_code=400, detail="Invalid role")

    if data.role == "admin":
        raise HTTPException(status_code=400, detail="Cannot request admin role")

    if has_user_role(
        db=db,
        user_id=current_user.id,
        role_type=data.role,
        group_id=None,
    ):
        raise HTTPException(status_code=400, detail="Already has this role")

    duplicate_pending = subscription_role_request_query(db).filter(
        RoleRequest.user_id == current_user.id,
        RoleRequest.role_type == data.role,
        RoleRequest.status == "pending",
    ).first()

    if duplicate_pending is not None:
        raise HTTPException(status_code=400, detail="Request already pending")

    settings = get_user_settings_by_user_id(db=db, user_id=current_user.id)
    group_name = (
        normalize_optional_string(settings.selected_group_name)
        if settings is not None
        else None
    )

    role_request = RoleRequest(
        user_id=current_user.id,
        user_email=get_user_primary_email(current_user),
        role_type=data.role,
        group_id=settings.selected_group_id if settings is not None else None,
        group_name=group_name,
        message=normalize_optional_string(data.message),
        status="pending",
        created_at=datetime.now(timezone.utc),
    )

    db.add(role_request)
    db.commit()
    db.refresh(role_request)

    return me_role_request_to_response(role_request)


@router.get("/me/role-requests", response_model=List[MeRoleRequestResponse])
async def get_my_subscription_role_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role_requests = subscription_role_request_query(db).filter(
        RoleRequest.user_id == current_user.id
    ).order_by(
        RoleRequest.created_at.desc(),
        RoleRequest.id.desc(),
    ).all()

    return [me_role_request_to_response(role_request) for role_request in role_requests]


@router.post("/me/role-requests/{request_id}/cancel", response_model=MeRoleRequestResponse)
async def cancel_my_role_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role_request = subscription_role_request_query(db).filter(
        RoleRequest.id == request_id,
        RoleRequest.user_id == current_user.id,
    ).first()

    if role_request is None:
        raise HTTPException(status_code=404, detail="Role request not found")

    if role_request.status != "pending":
        raise HTTPException(
            status_code=400,
            detail="Only pending requests can be cancelled",
        )

    role_request.status = "cancelled"
    db.commit()
    db.refresh(role_request)

    return me_role_request_to_response(role_request)


@router.get("/moderation/role-requests", response_model=List[RoleRequestResponse])
async def get_pending_role_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_admin_or_moderator(db=db, user=current_user)

    role_requests = db.query(RoleRequest).filter(
        RoleRequest.status == "pending"
    ).order_by(
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
        role_request_to_response(
            role_request,
            user=users_by_id.get(role_request.user_id),
        )
        for role_request in role_requests
    ]


@router.post(
    "/moderation/role-requests/{request_id}/approve",
    response_model=RoleRequestResponse,
)
async def approve_role_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    admin_access, _ = ensure_admin_or_moderator(db=db, user=current_user)

    role_request = db.query(RoleRequest).filter(
        RoleRequest.id == request_id,
        RoleRequest.status == "pending",
    ).first()

    if role_request is None:
        raise HTTPException(status_code=404, detail="Pending role request not found")

    role_type = normalize_role_type(role_request.role_type)

    if role_type == "moderator" and not admin_access:
        raise HTTPException(
            status_code=403,
            detail="Only admin can approve moderator requests",
        )

    target_user = db.query(User).filter(User.id == role_request.user_id).first()
    if target_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.now(timezone.utc)

    if role_type == "group_leader":
        if role_request.group_id is None:
            raise HTTPException(
                status_code=400,
                detail="group_leader request must contain groupId",
            )

        if group_has_other_leader(
            db=db,
            group_id=role_request.group_id,
            exclude_user_id=role_request.user_id,
        ):
            raise HTTPException(status_code=400, detail="Group already has a leader")

        ensure_user_role_exists(
            db=db,
            user_id=role_request.user_id,
            role_type="group_leader",
            group_id=role_request.group_id,
            granted_by_user_id=current_user.id,
        )

        legacy_leader = db.query(GroupLeader).filter(
            GroupLeader.user_id == role_request.user_id,
            GroupLeader.group_id == role_request.group_id,
        ).first()

        if legacy_leader is None:
            db.add(
                GroupLeader(
                    user_id=role_request.user_id,
                    group_id=role_request.group_id,
                    created_at=now,
                )
            )

    elif role_type == "moderator":
        ensure_user_role_exists(
            db=db,
            user_id=role_request.user_id,
            role_type="moderator",
            group_id=None,
            granted_by_user_id=current_user.id,
        )
    else:
        valid_roles = get_valid_role_names(db)
        if role_type not in valid_roles or role_type == "admin":
            raise HTTPException(status_code=400, detail="Invalid roleType")

        ensure_user_role_exists(
            db=db,
            user_id=role_request.user_id,
            role_type=role_type,
            group_id=None,
            granted_by_user_id=current_user.id,
        )

    role_request.status = "approved"
    role_request.moderator_id = current_user.id
    role_request.reviewed_at = now
    role_request.reviewed_by_admin_email = get_user_primary_email(current_user)

    db.commit()
    db.refresh(role_request)

    return role_request_to_response(role_request, user=target_user)


@router.post(
    "/moderation/role-requests/{request_id}/reject",
    response_model=RoleRequestResponse,
)
async def reject_role_request(
    request_id: int,
    data: Optional[RoleRequestRejectRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    admin_access, _ = ensure_admin_or_moderator(db=db, user=current_user)
    review_data = data or RoleRequestRejectRequest()

    role_request = db.query(RoleRequest).filter(
        RoleRequest.id == request_id,
        RoleRequest.status == "pending",
    ).first()

    if role_request is None:
        raise HTTPException(status_code=404, detail="Pending role request not found")

    role_type = normalize_role_type(role_request.role_type)

    if role_type == "moderator" and not admin_access:
        raise HTTPException(
            status_code=403,
            detail="Only admin can reject moderator requests",
        )

    target_user = db.query(User).filter(User.id == role_request.user_id).first()

    role_request.status = "rejected"
    role_request.moderator_id = current_user.id
    role_request.reviewed_at = datetime.now(timezone.utc)
    role_request.reviewed_by_admin_email = get_user_primary_email(current_user)
    role_request.review_comment = normalize_optional_string(review_data.comment)

    db.commit()
    db.refresh(role_request)

    return role_request_to_response(role_request, user=target_user)


@router.post("/leader-requests", response_model=LeaderRequestResponse)
async def create_leader_request(
    data: LeaderRequestCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    settings = get_user_settings_by_user_id(db=db, user_id=current_user.id)

    if settings is None or settings.selected_group_id != data.groupId:
        raise HTTPException(
            status_code=403,
            detail="You can request leadership only for your selected group",
        )

    existing_leader = db.query(GroupLeader).filter(
        GroupLeader.user_id == current_user.id,
        GroupLeader.group_id == data.groupId,
    ).first()

    if existing_leader is not None:
        raise HTTPException(
            status_code=400,
            detail="You are already a leader of this group",
        )

    pending_request = db.query(LeaderRequest).filter(
        LeaderRequest.user_id == current_user.id,
        LeaderRequest.group_id == data.groupId,
        LeaderRequest.status == "pending",
    ).first()

    if pending_request is not None:
        raise HTTPException(
            status_code=400,
            detail="Pending request already exists for this group",
        )

    group_name = normalize_optional_string(data.groupName)
    if group_name is None:
        group_name = normalize_optional_string(settings.selected_group_name)

    now = datetime.now(timezone.utc)
    request_comment = normalize_optional_string(data.comment)

    leader_request = LeaderRequest(
        user_id=current_user.id,
        group_id=data.groupId,
        group_name=group_name,
        status="pending",
        comment=request_comment,
        created_at=now,
    )

    db.add(leader_request)
    db.commit()
    db.refresh(leader_request)

    return leader_request_to_response(leader_request)


@router.get("/leader-requests/me", response_model=List[LeaderRequestResponse])
async def get_my_leader_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    leader_requests = db.query(LeaderRequest).filter(
        LeaderRequest.user_id == current_user.id
    ).order_by(
        LeaderRequest.created_at.desc(),
        LeaderRequest.id.desc(),
    ).all()

    return [leader_request_to_response(leader_request) for leader_request in leader_requests]


@router.get("/moderation/leader-requests", response_model=List[LeaderRequestResponse])
async def get_pending_leader_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_permission(db, current_user, "manage_roles")

    leader_requests = db.query(LeaderRequest).filter(
        LeaderRequest.status == "pending"
    ).order_by(
        LeaderRequest.created_at.desc(),
        LeaderRequest.id.desc(),
    ).all()

    return [leader_request_to_response(leader_request) for leader_request in leader_requests]


@router.post(
    "/moderation/leader-requests/{request_id}/approve",
    response_model=LeaderRequestResponse,
)
async def approve_leader_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_permission(db, current_user, "manage_roles")

    leader_request = db.query(LeaderRequest).filter(
        LeaderRequest.id == request_id,
        LeaderRequest.status == "pending",
    ).first()

    if leader_request is None:
        raise HTTPException(status_code=404, detail="Pending request not found")

    now = datetime.now(timezone.utc)
    existing_leader = db.query(GroupLeader).filter(
        GroupLeader.user_id == leader_request.user_id,
        GroupLeader.group_id == leader_request.group_id,
    ).first()

    if existing_leader is None:
        db.add(
            GroupLeader(
                user_id=leader_request.user_id,
                group_id=leader_request.group_id,
                created_at=now,
            )
        )

    leader_request.status = "approved"
    leader_request.moderator_id = current_user.id
    leader_request.reviewed_at = now

    db.commit()
    db.refresh(leader_request)

    return leader_request_to_response(leader_request)


@router.post(
    "/moderation/leader-requests/{request_id}/reject",
    response_model=LeaderRequestResponse,
)
async def reject_leader_request(
    request_id: int,
    data: LeaderRequestRejectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_permission(db, current_user, "manage_roles")

    leader_request = db.query(LeaderRequest).filter(
        LeaderRequest.id == request_id,
        LeaderRequest.status == "pending",
    ).first()

    if leader_request is None:
        raise HTTPException(status_code=404, detail="Pending request not found")

    leader_request.status = "rejected"
    leader_request.moderator_id = current_user.id
    leader_request.reviewed_at = datetime.now(timezone.utc)

    if data.comment is not None:
        leader_request.comment = normalize_optional_string(data.comment)

    db.commit()
    db.refresh(leader_request)

    return leader_request_to_response(leader_request)
