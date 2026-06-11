from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from backend.app.core.deps import get_current_user, ensure_permission
from backend.app.db.models import User, Badge, UserBadge
from backend.app.db.session import get_db
from backend.app.schemas.admin import GrantBadgeRequest, AdminUserResponse
from backend.app.schemas.user import BadgeResponse
from backend.app.services.user_profile_service import build_user_badges
from backend.app.routers.admin_roles import build_admin_user_response_single

router = APIRouter(prefix="/admin", tags=["admin-badges"])

@router.get("/badges", response_model=List[BadgeResponse])
async def admin_get_all_badges(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ensure_permission(db, current_user, "manage_roles")
    badges = db.query(Badge).all()
    return badges

@router.post("/users/{user_id}/badges", response_model=AdminUserResponse)
async def admin_grant_badge(
    user_id: int,
    data: GrantBadgeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ensure_permission(db, current_user, "manage_roles")

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    badge = db.query(Badge).filter(Badge.code == data.badge_code).first()
    if not badge:
        raise HTTPException(status_code=404, detail="Badge not found")

    existing = db.query(UserBadge).filter(
        UserBadge.user_id == user_id,
        UserBadge.badge_id == badge.id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="User already has this badge")

    user_badge = UserBadge(
        user_id=user_id,
        badge_id=badge.id,
        granted_by_user_id=current_user.id,
        note=data.note
    )
    db.add(user_badge)
    db.commit()

    return build_admin_user_response_single(db, target_user)

@router.delete("/users/{user_id}/badges/{badge_code}", response_model=AdminUserResponse)
async def admin_revoke_badge(
    user_id: int,
    badge_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ensure_permission(db, current_user, "manage_roles")

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    badge = db.query(Badge).filter(Badge.code == badge_code).first()
    if not badge:
        raise HTTPException(status_code=404, detail="Badge not found")

    user_badge = db.query(UserBadge).filter(
        UserBadge.user_id == user_id,
        UserBadge.badge_id == badge.id
    ).first()

    if user_badge:
        db.delete(user_badge)
        db.commit()

    return build_admin_user_response_single(db, target_user)
