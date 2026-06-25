from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timezone
from app.db.session import get_db
from app.db.models import (
    GroupChangeRequest,
    GroupLeader,
    GroupMembership,
    Homework,
    User,
    UserRole,
    UserSettings,
)
from app.core.features import require_homework_enabled
from app.core.deps import (
    get_current_user, is_admin, is_moderator, can_access_group,
    user_has_group_leader_role, ensure_group_access,
    ensure_admin_or_moderator, get_user_primary_email
)
from app.schemas.group import (
    GroupChangeRequestCreate,
    GroupChangeRequestResponse,
    GroupChangeRequestReview,
    GroupInviteRequest,
)
from app.schemas.homework import HomeworkCreateRequest, HomeworkOptionResponse, HomeworkUpdateRequest
from app.services.assistant_policy_service import get_user_plan
from app.services.homework_service import build_homework_options, homework_to_response
from app.services.roles_service import build_user_roles
from app.services.user_profile_service import build_user_badges
from app.utils.common import normalize_optional_string
from app.utils.email import normalize_email

router = APIRouter()



def check_group_view_access(db, user, group_id: int) -> bool:
    if is_admin(db, user) or is_moderator(db, user):
        return True
    return can_access_group(db, user.id, group_id)

def ensure_group_view_access(db, user, group_id: int):
    if not check_group_view_access(db, user, group_id):
         raise HTTPException(status_code=403, detail="Forbidden for this group")

def check_group_edit_access(db, user, group_id: int) -> bool:
    if is_admin(db, user) or is_moderator(db, user):
        return True
    return user_has_group_leader_role(db, user.id, group_id)

def ensure_group_edit_access(db, user, group_id: int):
    if not check_group_edit_access(db, user, group_id):
         raise HTTPException(status_code=403, detail="Only group leader or admin can modify homework")

def ensure_no_active_membership(db, user_id: int):
    active = db.query(GroupMembership).filter(
        GroupMembership.user_id == user_id,
        GroupMembership.status == "active"
    ).first()
    if active:
        raise HTTPException(status_code=400, detail="User already has an active membership in a group")

def membership_to_response(m: GroupMembership):
    return {
        "id": m.id,
        "group_id": m.group_id,
        "user_id": m.user_id,
        "role": m.role,
        "status": m.status,
        "invited_by_user_id": m.invited_by_user_id,
        "created_at": m.created_at,
        "updated_at": m.updated_at
    }


def group_change_request_to_response(
    request: GroupChangeRequest,
    target_user: Optional[User] = None,
):
    return {
        "id": request.id,
        "userId": request.user_id,
        "userName": target_user.display_name if target_user is not None else None,
        "userEmail": (
            get_user_primary_email(target_user)
            if target_user is not None
            else request.user_email
        ),
        "currentGroupId": request.current_group_id,
        "currentGroupName": request.current_group_name,
        "requestedGroupId": request.requested_group_id,
        "requestedGroupName": request.requested_group_name,
        "comment": request.comment,
        "status": request.status,
        "moderatorId": request.moderator_id,
        "reviewedByAdminEmail": request.reviewed_by_admin_email,
        "reviewComment": request.review_comment,
        "createdAt": request.created_at,
        "reviewedAt": request.reviewed_at,
    }


def get_user_settings(db: Session, user_id: int) -> Optional[UserSettings]:
    return db.query(UserSettings).filter(UserSettings.user_id == user_id).first()

@router.get("/groups/{group_id}/members")
def get_group_members(
    group_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ensure_group_edit_access(db, user, group_id)
    
    memberships = db.query(GroupMembership).filter(
        GroupMembership.group_id == group_id,
        GroupMembership.status.in_(["active", "pending"])
    ).all()
    
    return [membership_to_response(m) for m in memberships]

@router.post("/groups/{group_id}/join-request")
def create_join_request(
    group_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ensure_no_active_membership(db, user.id)
    
    existing = db.query(GroupMembership).filter(
        GroupMembership.group_id == group_id,
        GroupMembership.user_id == user.id,
        GroupMembership.status == "pending"
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Join request already exists")
        
    m = GroupMembership(
        group_id=group_id,
        user_id=user.id,
        role="member",
        status="pending"
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return membership_to_response(m)

@router.post("/groups/{group_id}/memberships/{membership_id}/approve")
def approve_membership(
    group_id: int,
    membership_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ensure_group_edit_access(db, user, group_id)
    
    m = db.query(GroupMembership).filter(
        GroupMembership.id == membership_id,
        GroupMembership.group_id == group_id
    ).first()
    
    if not m:
        raise HTTPException(status_code=404, detail="Membership not found")
        
    if m.status != "pending":
        raise HTTPException(status_code=400, detail="Membership is not pending")
        
    ensure_no_active_membership(db, m.user_id)
    
    m.status = "active"
    m.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(m)
    return membership_to_response(m)

@router.post("/groups/{group_id}/memberships/{membership_id}/decline")
def decline_membership(
    group_id: int,
    membership_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ensure_group_edit_access(db, user, group_id)
    
    m = db.query(GroupMembership).filter(
        GroupMembership.id == membership_id,
        GroupMembership.group_id == group_id
    ).first()
    
    if not m:
        raise HTTPException(status_code=404, detail="Membership not found")
        
    if m.status != "pending":
        raise HTTPException(status_code=400, detail="Membership is not pending")
        
    m.status = "declined"
    m.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(m)
    return membership_to_response(m)

@router.post("/groups/{group_id}/invites")
def invite_user(
    group_id: int,
    data: GroupInviteRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ensure_group_edit_access(db, user, group_id)
    
    if data.role != "member" and not (is_admin(db, user) or is_moderator(db, user)):
        raise HTTPException(status_code=403, detail="Group leaders can only invite members")
        
    ensure_no_active_membership(db, data.user_id)
    
    existing = db.query(GroupMembership).filter(
        GroupMembership.group_id == group_id,
        GroupMembership.user_id == data.user_id,
        GroupMembership.status == "pending"
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Invite or join request already exists")
        
    m = GroupMembership(
        group_id=group_id,
        user_id=data.user_id,
        role=data.role,
        status="pending",
        invited_by_user_id=user.id
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return membership_to_response(m)

@router.post("/group-invites/{membership_id}/accept")
def accept_invite(
    membership_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    m = db.query(GroupMembership).filter(
        GroupMembership.id == membership_id,
        GroupMembership.user_id == user.id,
        GroupMembership.status == "pending",
        GroupMembership.invited_by_user_id.isnot(None)
    ).first()
    
    if not m:
        raise HTTPException(status_code=404, detail="Invite not found")
        
    ensure_no_active_membership(db, user.id)
    
    m.status = "active"
    m.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(m)
    return membership_to_response(m)

@router.post("/group-invites/{membership_id}/decline")
def decline_invite(
    membership_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    m = db.query(GroupMembership).filter(
        GroupMembership.id == membership_id,
        GroupMembership.user_id == user.id,
        GroupMembership.status == "pending",
        GroupMembership.invited_by_user_id.isnot(None)
    ).first()
    
    if not m:
        raise HTTPException(status_code=404, detail="Invite not found")
        
    m.status = "declined"
    m.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(m)
    return membership_to_response(m)


@router.post(
    "/group-change-requests",
    response_model=GroupChangeRequestResponse,
)
def create_group_change_request(
    data: GroupChangeRequestCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    settings = get_user_settings(db=db, user_id=user.id)
    if settings is None or settings.selected_group_id is None:
        raise HTTPException(
            status_code=400,
            detail="Set the initial default group through settings first",
        )

    requested_group_name = normalize_optional_string(data.requestedGroupName)
    current_group_name = normalize_optional_string(settings.selected_group_name)

    if settings.selected_group_id == data.requestedGroupId:
        if requested_group_name is None or requested_group_name == current_group_name:
            raise HTTPException(status_code=400, detail="This group is already selected")

    existing_pending = db.query(GroupChangeRequest).filter(
        GroupChangeRequest.user_id == user.id,
        GroupChangeRequest.status == "pending",
    ).first()
    if existing_pending is not None:
        raise HTTPException(status_code=400, detail="Pending group change request already exists")

    request = GroupChangeRequest(
        user_id=user.id,
        user_email=get_user_primary_email(user),
        current_group_id=settings.selected_group_id,
        current_group_name=current_group_name,
        requested_group_id=data.requestedGroupId,
        requested_group_name=requested_group_name,
        comment=normalize_optional_string(data.comment),
        status="pending",
        created_at=datetime.now(timezone.utc),
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return group_change_request_to_response(request=request, target_user=user)


@router.get(
    "/group-change-requests/me",
    response_model=list[GroupChangeRequestResponse],
)
def get_my_group_change_requests(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    requests = db.query(GroupChangeRequest).filter(
        GroupChangeRequest.user_id == user.id
    ).order_by(
        GroupChangeRequest.created_at.desc(),
        GroupChangeRequest.id.desc(),
    ).all()

    return [
        group_change_request_to_response(request=request, target_user=user)
        for request in requests
    ]


@router.post(
    "/group-change-requests/{request_id}/cancel",
    response_model=GroupChangeRequestResponse,
)
def cancel_group_change_request(
    request_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    request = db.query(GroupChangeRequest).filter(
        GroupChangeRequest.id == request_id,
        GroupChangeRequest.user_id == user.id,
    ).first()

    if request is None:
        raise HTTPException(status_code=404, detail="Group change request not found")

    if request.status != "pending":
        raise HTTPException(
            status_code=400,
            detail="Only pending requests can be cancelled",
        )

    request.status = "cancelled"
    db.commit()
    db.refresh(request)

    return group_change_request_to_response(request=request, target_user=user)


@router.get(
    "/moderation/group-change-requests",
    response_model=list[GroupChangeRequestResponse],
)
def get_moderation_group_change_requests(
    status: str = Query(default="pending"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_admin_or_moderator(db=db, user=user)

    allowed_statuses = {"pending", "approved", "rejected", "cancelled", "all"}
    normalized_status = status.strip().lower()
    if normalized_status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Invalid status filter")

    query = db.query(GroupChangeRequest)
    if normalized_status != "all":
        query = query.filter(GroupChangeRequest.status == normalized_status)

    requests = query.order_by(
        GroupChangeRequest.created_at.desc(),
        GroupChangeRequest.id.desc(),
    ).all()

    if not requests:
        return []

    users_by_id = {
        target.id: target
        for target in db.query(User).filter(
            User.id.in_({request.user_id for request in requests})
        ).all()
    }

    return [
        group_change_request_to_response(
            request=request,
            target_user=users_by_id.get(request.user_id),
        )
        for request in requests
    ]


@router.post(
    "/moderation/group-change-requests/{request_id}/approve",
    response_model=GroupChangeRequestResponse,
)
def approve_group_change_request(
    request_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_admin_or_moderator(db=db, user=user)

    request = db.query(GroupChangeRequest).filter(
        GroupChangeRequest.id == request_id,
        GroupChangeRequest.status == "pending",
    ).first()
    if request is None:
        raise HTTPException(status_code=404, detail="Pending group change request not found")

    target_user = db.query(User).filter(User.id == request.user_id).first()
    if target_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    settings = get_user_settings(db=db, user_id=request.user_id)
    if settings is None:
        settings = UserSettings(user_id=request.user_id)
        db.add(settings)

    settings.selected_group_id = request.requested_group_id
    settings.selected_group_name = request.requested_group_name
    settings.updated_at = datetime.now(timezone.utc)

    request.status = "approved"
    request.moderator_id = user.id
    request.reviewed_by_admin_email = get_user_primary_email(user)
    request.reviewed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(request)
    return group_change_request_to_response(request=request, target_user=target_user)


@router.post(
    "/moderation/group-change-requests/{request_id}/reject",
    response_model=GroupChangeRequestResponse,
)
def reject_group_change_request(
    request_id: int,
    data: Optional[GroupChangeRequestReview] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_admin_or_moderator(db=db, user=user)

    request = db.query(GroupChangeRequest).filter(
        GroupChangeRequest.id == request_id,
        GroupChangeRequest.status == "pending",
    ).first()
    if request is None:
        raise HTTPException(status_code=404, detail="Pending group change request not found")

    target_user = db.query(User).filter(User.id == request.user_id).first()
    review_data = data or GroupChangeRequestReview()

    request.status = "rejected"
    request.moderator_id = user.id
    request.reviewed_by_admin_email = get_user_primary_email(user)
    request.review_comment = normalize_optional_string(review_data.comment)
    request.reviewed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(request)
    return group_change_request_to_response(request=request, target_user=target_user)


@router.get("/groups/{group_id}/users")
def get_group_users(
    group_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ensure_group_view_access(db, user, group_id)
    
    memberships = db.query(GroupMembership).filter(
        GroupMembership.group_id == group_id,
        GroupMembership.status == "active"
    ).all()

    selected_group_settings = db.query(UserSettings).filter(
        UserSettings.selected_group_id == group_id
    ).all()

    group_user_ids = {m.user_id for m in memberships}
    group_user_ids.update(settings.user_id for settings in selected_group_settings)
    if not group_user_ids:
        return []
        
    users = db.query(User).filter(User.id.in_(group_user_ids)).all()
    
    result = []
    for u in users:
        tier = get_user_plan(u.id, db)
        u_roles = build_user_roles(db, u)
        
        email = normalize_email(u.contact_email) or normalize_email(u.email) or normalize_email(u.apple_email)
        
        result.append({
            "id": str(u.id),
            "name": u.display_name or "Неизвестный",
            "email": email,
            "group_id": group_id,
            "roles": u_roles,
            "badges": build_user_badges(db, u.id),
            "tier": tier
        })
    return result

@router.post("/admin/users/{user_id}/group")
def admin_set_user_group(
    user_id: int,
    group_id: int,
    admin_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not is_admin(db, admin_user):
        raise HTTPException(status_code=403, detail="Admin access required")
        
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Deactivate existing active memberships
    db.query(GroupMembership).filter(
        GroupMembership.user_id == user_id,
        GroupMembership.status == "active"
    ).update({"status": "removed"})
    
    m = db.query(GroupMembership).filter(
        GroupMembership.user_id == user_id,
        GroupMembership.group_id == group_id,
    ).first()
    
    if m:
        m.status = "active"
        m.updated_at = datetime.now(timezone.utc)
    else:
        m = GroupMembership(
            group_id=group_id,
            user_id=user_id,
            role="member",
            status="active"
        )
        db.add(m)
        
    db.commit()
    return {"success": True, "groupId": group_id}

@router.get("/groups/{group_id}/homeworks")
def get_homeworks(
    group_id: int,
    date: Optional[str] = Query(None),
    _: None = Depends(require_homework_enabled),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ensure_group_view_access(db, user, group_id)
    
    query = db.query(Homework).filter(Homework.group_id == group_id)
    if date:
        query = query.filter(Homework.lesson_date == date)
        
    homeworks = query.order_by(Homework.created_at.desc()).all()
    return [homework_to_response(hw) for hw in homeworks]

@router.get("/groups/{group_id}/homeworks/lesson")
def get_homework_by_lesson(
    group_id: int,
    date: str = Query(...),
    time: Optional[str] = Query(None),
    subject: str = Query(...),
    _: None = Depends(require_homework_enabled),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ensure_group_view_access(db, user, group_id)
    
    query = db.query(Homework).filter(
        Homework.group_id == group_id,
        Homework.lesson_date == date,
        Homework.subject == subject
    )
    if time:
        query = query.filter(Homework.lesson_time == time)
        
    hw = query.first()
    if not hw:
        raise HTTPException(status_code=404, detail="Homework not found")
        
    return homework_to_response(hw)

@router.post("/groups/{group_id}/homeworks")
def create_homework(
    group_id: int,
    data: HomeworkCreateRequest,
    _: None = Depends(require_homework_enabled),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ensure_group_edit_access(db, user, group_id)
    
    if not data.lesson_date or not data.subject:
         raise HTTPException(status_code=400, detail="lesson_date and subject are required")
         
    hw = Homework(
        group_id=group_id,
        lesson_date=data.lesson_date,
        lesson_time=data.lesson_time,
        subject=data.subject,
        teacher=data.teacher,
        room=data.room,
        text=data.text,
        created_by_user_id=user.id
    )
    db.add(hw)
    db.commit()
    db.refresh(hw)
    return homework_to_response(hw)

@router.patch("/groups/{group_id}/homeworks/{homework_id}")
def update_homework(
    group_id: int,
    homework_id: int,
    data: HomeworkUpdateRequest,
    _: None = Depends(require_homework_enabled),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ensure_group_edit_access(db, user, group_id)
    
    hw = db.query(Homework).filter(Homework.id == homework_id, Homework.group_id == group_id).first()
    if not hw:
        raise HTTPException(status_code=404, detail="Homework not found")
        
    if data.lesson_date is not None:
        hw.lesson_date = data.lesson_date
    if data.lesson_time is not None:
        hw.lesson_time = data.lesson_time
    if data.subject is not None:
        hw.subject = data.subject
    if data.teacher is not None:
        hw.teacher = data.teacher
    if data.room is not None:
        hw.room = data.room
    if data.text is not None:
        hw.text = data.text
        
    hw.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(hw)
    return homework_to_response(hw)

@router.delete("/groups/{group_id}/homeworks/{homework_id}")
def delete_homework(
    group_id: int,
    homework_id: int,
    _: None = Depends(require_homework_enabled),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ensure_group_edit_access(db, user, group_id)
    
    hw = db.query(Homework).filter(Homework.id == homework_id, Homework.group_id == group_id).first()
    if not hw:
        raise HTTPException(status_code=404, detail="Homework not found")
        
    db.delete(hw)
    db.commit()
    return {"success": True}


@router.get(
    "/groups/{group_id}/homework-options",
    response_model=list[HomeworkOptionResponse],
)
async def get_group_homework_options(
    group_id: int,
    _: None = Depends(require_homework_enabled),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_group_access(db=db, user_id=current_user.id, group_id=group_id)
    return build_homework_options(group_id=group_id)
