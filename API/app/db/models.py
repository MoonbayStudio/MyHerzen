from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    Text
)
from app.db.session import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    apple_sub = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, nullable=True)
    apple_email = Column(String, nullable=True)
    contact_email = Column(String, nullable=True, index=True)
    contact_email_verified = Column(Boolean, nullable=False, default=False)
    contact_email_verified_at = Column(DateTime, nullable=True)
    pending_contact_email = Column(String, nullable=True)
    pending_contact_email_token_hash = Column(
        String,
        nullable=True,
        index=True
    )
    pending_contact_email_expires_at = Column(DateTime, nullable=True)
    display_name = Column(String, nullable=True)
    password_hash = Column(String, nullable=True)
    password_created_at = Column(DateTime, nullable=True)
    password_updated_at = Column(DateTime, nullable=True)
    last_password_reset_at = Column(DateTime, nullable=True)
    password_reset_token_hash = Column(String, nullable=True, index=True)
    password_reset_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class AuthProvider(Base):
    __tablename__ = "auth_providers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    provider = Column(String, nullable=False, index=True)
    provider_user_id = Column(String, nullable=False, index=True)
    email = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, unique=True, index=True)
    selected_group_id = Column(Integer, nullable=True)
    selected_group_name = Column(Text, nullable=True)
    schedule_cache_weeks = Column(Integer, nullable=False, default=2)
    live_activity_enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class GroupMembership(Base):
    __tablename__ = "group_memberships"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    role = Column(String, nullable=False, default="member") # "member" | "group_leader"
    status = Column(String, nullable=False, default="pending") # "pending" | "active" | "declined" | "removed"
    invited_by_user_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class GroupLeader(Base):
    __tablename__ = "group_leaders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    group_id = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class UserRole(Base):
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    role_type = Column(String, nullable=False, index=True)
    group_id = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    granted_by_user_id = Column(Integer, nullable=True, index=True)

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    daily_limit = Column(Integer, default=10, nullable=False)

class RoleAuditLog(Base):
    __tablename__ = "role_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, nullable=False, index=True)
    target_user_id = Column(Integer, nullable=False, index=True)
    admin_email = Column(String, nullable=True)
    target_email = Column(String, nullable=True)
    role_name = Column(String, nullable=False)
    action = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class RoleRequest(Base):
    __tablename__ = "role_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    user_email = Column(String, nullable=True)
    role_type = Column(String, nullable=False, index=True)
    group_id = Column(Integer, nullable=True, index=True)
    group_name = Column(String, nullable=True)
    comment = Column(Text, nullable=True)
    message = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="pending", index=True)
    moderator_id = Column(Integer, nullable=True, index=True)
    reviewed_by_admin_email = Column(String, nullable=True)
    review_comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    reviewed_at = Column(DateTime, nullable=True)

class Homework(Base):
    __tablename__ = "homework"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, nullable=False, index=True)
    lesson_date = Column(String, nullable=False)
    lesson_time = Column(String, nullable=True)
    subject = Column(String, nullable=False)
    teacher = Column(String, nullable=True)
    room = Column(String, nullable=True)
    text = Column(Text, nullable=False)
    created_by_user_id = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class UsageLimit(Base):
    __tablename__ = "usage_limits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    client_ip = Column(String, nullable=True, index=True)
    date = Column(String, nullable=False, index=True)
    feature = Column(String, nullable=False, index=True)
    used_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class LeaderRequest(Base):
    __tablename__ = "leader_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    group_id = Column(Integer, nullable=False, index=True)
    group_name = Column(String, nullable=True)
    status = Column(String, nullable=False, default="pending", index=True)
    comment = Column(Text, nullable=True)
    moderator_id = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    reviewed_at = Column(DateTime, nullable=True)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key = Column(String, primary_key=True, unique=True, nullable=False)
    value = Column(Text, nullable=False)
    value_type = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, nullable=False, default=False)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_by = Column(Integer, nullable=True, index=True)


class SystemNotice(Base):
    __tablename__ = "system_notices"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String, nullable=False, default="info", index=True)
    is_active = Column(Boolean, nullable=False, default=False, index=True)
    starts_at = Column(DateTime, nullable=True, index=True)
    ends_at = Column(DateTime, nullable=True, index=True)
    show_as = Column(String, nullable=False, default="banner")
    dismissible = Column(Boolean, nullable=False, default=True)
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    created_by = Column(Integer, nullable=True, index=True)


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    session_token_hash = Column(String, nullable=False, index=True)
    device_id = Column(String, nullable=True, index=True)
    device_name = Column(String, nullable=True)
    platform = Column(String, nullable=True, index=True)
    app_version = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    last_seen_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    revoked_at = Column(DateTime, nullable=True, index=True)


class Badge(Base):
    __tablename__ = "badges"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    icon_name = Column(String, nullable=False)
    rarity = Column(String, nullable=False, default="common") # common | rare | epic | legendary
    is_hidden = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class UserBadge(Base):
    __tablename__ = "user_badges"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    badge_id = Column(Integer, nullable=False, index=True)
    granted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    granted_by_user_id = Column(Integer, nullable=True, index=True)
    note = Column(Text, nullable=True)
