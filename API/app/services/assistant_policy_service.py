from typing import Optional

from sqlalchemy.orm import Session

from app.core.deps import is_owner
from app.db.models import User, UserRole

PLAN_LIMITS = {
    "admin": -1,
    "tester": -1,
    "premium": 200,
    "plus": 50,
    "free": 10,
    "anonymous": 5,
}

MESSAGE_LENGTH_LIMITS = {
    "free": 2000,
    "plus": 4000,
    "premium": 8000,
    "anonymous": 2000,
}


def get_user_plan(user_id: Optional[int], db: Session) -> str:
    if user_id is None:
        return "anonymous"

    user = db.query(User).filter(User.id == user_id).first()
    if user and is_owner(user):
        return "admin"

    user_roles = db.query(UserRole).filter(UserRole.user_id == user_id).all()
    roles = [user_role.role_type for user_role in user_roles]

    if "admin" in roles:
        return "admin"
    if "tester" in roles:
        return "tester"
    if "premium" in roles:
        return "premium"
    if "plus" in roles:
        return "plus"
    return "free"


def get_plan_daily_limit(plan: str) -> int:
    return PLAN_LIMITS.get(plan, 3)


def get_plan_message_length_limit(plan: str) -> int:
    return MESSAGE_LENGTH_LIMITS.get(plan, 2000)
