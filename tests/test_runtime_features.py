import os
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET"] = "test_secret"
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
os.environ["OWNER_EMAILS"] = "owner@example.com"

from app.main import (  # noqa: E402
    app,
    Base,
    User,
    UserRole,
    UserSession,
    create_session_token,
    get_db,
)
from app.core.security import hash_password  # noqa: E402
from app.db.models import AuthProvider, GroupMembership, UserSettings  # noqa: E402
from app.services.auth_service import (  # noqa: E402
    apply_apple_email_to_user,
    apply_google_email_to_user,
)
from app.utils.session_security import hash_session_token  # noqa: E402


engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _create_user(db, *, email: str, apple_sub: str) -> User:
    user = User(
        apple_sub=apple_sub,
        email=email,
        apple_email=email,
        contact_email=email,
        contact_email_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _auth_headers_for_user(user_id: int) -> dict:
    token = create_session_token(user_id)
    return {"Authorization": f"Bearer {token}"}


def _create_tracked_session(db, user_id: int):
    token = create_session_token(user_id)
    now = datetime.now(timezone.utc)
    session = UserSession(
        user_id=user_id,
        session_token_hash=hash_session_token(token),
        device_id="test-device",
        platform="web",
        created_at=now,
        last_seen_at=now,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return token, session


def test_patch_me_updates_display_name():
    db = TestingSessionLocal()
    user = _create_user(db, email="profile-user@example.com", apple_sub="profile-user-sub")
    token, _session = _create_tracked_session(db, user.id)

    response = client.patch(
        "/me",
        json={"name": "  New Profile Name  "},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["displayName"] == "New Profile Name"

    db.refresh(user)
    assert user.display_name == "New Profile Name"


def test_patch_me_rejects_short_display_name():
    db = TestingSessionLocal()
    user = _create_user(db, email="short-name@example.com", apple_sub="short-name-sub")
    token, _session = _create_tracked_session(db, user.id)

    response = client.patch(
        "/me",
        json={"name": "A"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Display name is too short"

    db.refresh(user)
    assert user.display_name is None


def test_public_config_only_returns_public_settings():
    db = TestingSessionLocal()
    admin = _create_user(db, email="admin-settings@example.com", apple_sub="admin-settings-sub")
    db.add(UserRole(user_id=admin.id, role_type="admin"))
    db.commit()

    admin_headers = _auth_headers_for_user(admin.id)

    update_response = client.patch(
        "/admin/settings/AI_ENABLED",
        json={"value": False},
        headers=admin_headers,
    )
    assert update_response.status_code == 200

    public_response = client.get("/config/public")
    assert public_response.status_code == 200
    body = public_response.json()

    assert "settings" in body
    assert body["settings"]["AI_ENABLED"] is False
    assert "SCHEDULE_CACHE_TTL_SECONDS" not in body["settings"]


def test_link_google_provider_adds_login_provider(monkeypatch):
    db = TestingSessionLocal()
    user = _create_user(db, email="ios-user@example.com", apple_sub="apple-user-sub")
    token, _session = _create_tracked_session(db, user.id)

    monkeypatch.setattr(
        "app.routers.auth.verify_google_token",
        lambda _id_token: {
            "sub": "google-user-sub",
            "email": "ios-user@example.com",
            "email_verified": True,
            "name": "iOS User",
        },
    )

    response = client.post(
        "/me/providers/google",
        json={
            "idToken": "google-id-token",
            "deviceId": "iphone",
            "platform": "iOS",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["linkedProviders"] == ["apple", "google"]

    provider = db.query(AuthProvider).filter(
        AuthProvider.provider == "google",
        AuthProvider.provider_user_id == "google-user-sub",
    ).first()
    assert provider is not None
    assert provider.user_id == user.id


def test_signup_creates_pending_email_verification(monkeypatch):
    db = TestingSessionLocal()
    sent_codes = []

    monkeypatch.setattr(
        "app.routers.auth.send_email_verification_code",
        lambda email, code: sent_codes.append((email, code)),
    )

    response = client.post(
        "/auth/signup",
        json={
            "email": "signup-user@example.com",
            "password": "Password123",
            "displayName": "Signup User",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "verification_required",
        "email": "signup-user@example.com",
    }
    assert len(sent_codes) == 1
    assert sent_codes[0][0] == "signup-user@example.com"

    user = db.query(User).filter(
        User.pending_contact_email == "signup-user@example.com"
    ).first()
    assert user is not None
    assert user.contact_email is None
    assert user.contact_email_verified is False
    assert user.password_hash is not None


def test_signup_reuses_pending_email_signup(monkeypatch):
    db = TestingSessionLocal()
    sent_codes = []

    monkeypatch.setattr(
        "app.routers.auth.send_email_verification_code",
        lambda email, code: sent_codes.append((email, code)),
    )

    payload = {
        "email": "pending-signup@example.com",
        "password": "Password123",
        "displayName": "Pending Signup",
    }

    first_response = client.post("/auth/signup", json=payload)
    second_response = client.post(
        "/auth/signup",
        json={
            **payload,
            "password": "ChangedPassword123",
            "displayName": "Pending Signup Updated",
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert len(sent_codes) == 2

    users = db.query(User).filter(
        User.pending_contact_email == "pending-signup@example.com"
    ).all()
    assert len(users) == 1
    assert users[0].display_name == "Pending Signup Updated"


def test_signup_verify_activates_email_account(monkeypatch):
    db = TestingSessionLocal()
    sent_codes = []

    monkeypatch.setattr(
        "app.routers.auth.send_email_verification_code",
        lambda email, code: sent_codes.append((email, code)),
    )

    signup_response = client.post(
        "/auth/signup",
        json={
            "email": "verify-signup@example.com",
            "password": "Password123",
            "displayName": "Verify Signup",
        },
    )
    assert signup_response.status_code == 200

    verify_response = client.post(
        "/auth/signup/verify",
        json={
            "email": "verify-signup@example.com",
            "code": sent_codes[0][1],
            "deviceId": "android-device",
            "deviceName": "Pixel",
            "platform": "android",
            "appVersion": "1.0.0",
        },
    )

    assert verify_response.status_code == 200
    body = verify_response.json()
    assert body["user"]["email"] == "verify-signup@example.com"
    assert body["user"]["contactEmailVerified"] is True
    assert body["user"]["linkedProviders"] == []

    user = db.query(User).filter(
        User.contact_email == "verify-signup@example.com"
    ).first()
    assert user is not None
    assert user.pending_contact_email is None


def test_signup_verify_rejects_email_claimed_by_another_user(monkeypatch):
    db = TestingSessionLocal()
    sent_codes = []

    monkeypatch.setattr(
        "app.routers.auth.send_email_verification_code",
        lambda email, code: sent_codes.append((email, code)),
    )

    signup_response = client.post(
        "/auth/signup",
        json={
            "email": "claimed-signup@example.com",
            "password": "Password123",
            "displayName": "Claimed Signup",
        },
    )
    assert signup_response.status_code == 200

    claimed_user = User(
        apple_sub="claimed-signup-other-sub",
        email="claimed-signup@example.com",
        contact_email="claimed-signup@example.com",
        contact_email_verified=True,
    )
    db.add(claimed_user)
    db.commit()

    verify_response = client.post(
        "/auth/signup/verify",
        json={
            "email": "claimed-signup@example.com",
            "code": sent_codes[0][1],
            "deviceId": "android-device",
            "platform": "android",
        },
    )

    assert verify_response.status_code == 400
    assert verify_response.json()["detail"] == "Email is already in use"


def test_password_login_rejects_unverified_contact_email_with_password():
    db = TestingSessionLocal()
    user = _create_user(db, email="password-user@example.com", apple_sub="password-user-sub")
    user.contact_email_verified = False
    user.contact_email_verified_at = None
    user.password_hash = hash_password("Password123")
    db.commit()

    response = client.post(
        "/auth/login",
        json={
            "email": "password-user@example.com",
            "password": "Password123",
            "deviceId": "test-device",
            "platform": "web",
        },
    )

    assert response.status_code == 401


def test_password_login_accepts_verified_contact_email_with_password():
    db = TestingSessionLocal()
    user = _create_user(db, email="verified-user@example.com", apple_sub="verified-user-sub")
    user.password_hash = hash_password("Password123")
    db.commit()

    response = client.post(
        "/auth/login",
        json={
            "email": "verified-user@example.com",
            "password": "Password123",
            "deviceId": "test-device",
            "platform": "web",
        },
    )

    assert response.status_code == 200
    assert response.json()["user"]["id"] == str(user.id)


def test_password_login_tracks_android_session_platform():
    db = TestingSessionLocal()
    user = _create_user(db, email="android-user@example.com", apple_sub="android-user-sub")
    user.password_hash = hash_password("Password123")
    db.commit()

    login_response = client.post(
        "/auth/login",
        json={
            "email": "android-user@example.com",
            "password": "Password123",
            "deviceId": "android-device",
            "deviceName": "Pixel",
            "platform": "android",
            "appVersion": "1.0.0",
        },
    )

    assert login_response.status_code == 200
    token = login_response.json()["token"]

    sessions_response = client.get(
        "/account/sessions",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert sessions_response.status_code == 200
    sessions = sessions_response.json()
    assert sessions[0]["deviceId"] == "android-device"
    assert sessions[0]["deviceName"] == "Pixel"
    assert sessions[0]["platform"] == "android"
    assert sessions[0]["appVersion"] == "1.0.0"
    assert sessions[0]["isCurrent"] is True


def test_password_login_sends_new_device_notification(monkeypatch):
    db = TestingSessionLocal()
    user = _create_user(db, email="security-user@example.com", apple_sub="security-user-sub")
    user.password_hash = hash_password("Password123")
    db.commit()
    _create_tracked_session(db, user.id)
    sent_notifications = []

    monkeypatch.setattr(
        "app.routers.auth.send_new_device_login_notification",
        lambda **kwargs: sent_notifications.append(kwargs),
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "security-user@example.com",
            "password": "Password123",
            "deviceId": "new-device",
            "deviceName": "Pixel",
            "platform": "android",
            "appVersion": "1.0.0",
        },
    )

    assert response.status_code == 200
    assert len(sent_notifications) == 1
    assert sent_notifications[0]["email"] == "security-user@example.com"
    assert sent_notifications[0]["device_name"] == "Pixel"
    assert sent_notifications[0]["platform"] == "android"


def test_password_create_sends_security_notification(monkeypatch):
    db = TestingSessionLocal()
    user = _create_user(db, email="create-password@example.com", apple_sub="create-password-sub")
    token, _session = _create_tracked_session(db, user.id)
    sent_notifications = []

    monkeypatch.setattr(
        "app.routers.auth.send_password_security_notification",
        lambda **kwargs: sent_notifications.append(kwargs),
    )

    response = client.post(
        "/me/password/create",
        json={"password": "Password123"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "password_created"
    assert len(sent_notifications) == 1
    assert sent_notifications[0]["email"] == "create-password@example.com"
    assert sent_notifications[0]["action"] == "created"


def test_password_change_sends_security_notification(monkeypatch):
    db = TestingSessionLocal()
    user = _create_user(db, email="change-password@example.com", apple_sub="change-password-sub")
    user.password_hash = hash_password("OldPassword123")
    db.commit()
    token, _session = _create_tracked_session(db, user.id)
    sent_notifications = []

    monkeypatch.setattr(
        "app.routers.auth.send_password_security_notification",
        lambda **kwargs: sent_notifications.append(kwargs),
    )

    response = client.post(
        "/me/password/change",
        json={
            "currentPassword": "OldPassword123",
            "newPassword": "NewPassword123",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert len(sent_notifications) == 1
    assert sent_notifications[0]["email"] == "change-password@example.com"
    assert sent_notifications[0]["action"] == "changed"


def test_provider_email_contact_verification_rules():
    apple_user = User(apple_sub="apple-contact-rules-sub")
    apply_apple_email_to_user(
        user=apple_user,
        apple_sub="apple-contact-rules-sub",
        apple_email="apple-user@example.com",
    )

    assert apple_user.contact_email == "apple-user@example.com"
    assert apple_user.contact_email_verified is False

    relay_user = User(
        apple_sub="apple-relay-contact-rules-sub",
        contact_email_verified=False,
    )
    apply_apple_email_to_user(
        user=relay_user,
        apple_sub="apple-relay-contact-rules-sub",
        apple_email="user@privaterelay.appleid.com",
    )

    assert relay_user.contact_email is None
    assert relay_user.contact_email_verified is False

    google_user = User(apple_sub="google-contact-rules-sub")
    apply_google_email_to_user(
        user=google_user,
        google_email="google-user@example.com",
    )

    assert google_user.contact_email == "google-user@example.com"
    assert google_user.contact_email_verified is True

    linked_user = User(
        apple_sub="linked-contact-rules-sub",
        contact_email="linked-user@example.com",
        contact_email_verified=False,
    )
    apply_google_email_to_user(
        user=linked_user,
        google_email="linked-user@example.com",
    )

    assert linked_user.contact_email_verified is True


def test_password_reset_confirm_sets_new_password(monkeypatch):
    db = TestingSessionLocal()
    user = _create_user(db, email="reset-user@example.com", apple_sub="reset-user-sub")
    user.password_hash = hash_password("OldPassword123")
    db.commit()
    sent_codes = []

    monkeypatch.setattr(
        "app.routers.auth.send_password_reset_code",
        lambda email, code: sent_codes.append((email, code)),
    )

    request_response = client.post(
        "/auth/password/reset-request",
        json={"email": "reset-user@example.com"},
    )

    assert request_response.status_code == 200
    assert len(sent_codes) == 1
    assert sent_codes[0][0] == "reset-user@example.com"

    confirm_response = client.post(
        "/auth/password/reset-confirm",
        json={
            "code": sent_codes[0][1],
            "newPassword": "NewPassword123",
        },
    )

    assert confirm_response.status_code == 200

    login_response = client.post(
        "/auth/login",
        json={
            "email": "reset-user@example.com",
            "password": "NewPassword123",
            "deviceId": "test-device",
            "platform": "web",
        },
    )

    assert login_response.status_code == 200
    assert login_response.json()["user"]["id"] == str(user.id)


def test_password_reset_request_ignores_unverified_contact_email(monkeypatch):
    db = TestingSessionLocal()
    user = _create_user(db, email="unverified-reset@example.com", apple_sub="unverified-reset-sub")
    user.contact_email_verified = False
    user.contact_email_verified_at = None
    user.password_hash = hash_password("Password123")
    db.commit()
    sent_codes = []

    monkeypatch.setattr(
        "app.routers.auth.send_password_reset_code",
        lambda email, code: sent_codes.append((email, code)),
    )

    response = client.post(
        "/auth/password/reset-request",
        json={"email": "unverified-reset@example.com"},
    )

    assert response.status_code == 200
    assert sent_codes == []

    db.refresh(user)
    assert user.password_reset_token_hash is None


def test_system_notice_returns_highest_active_priority():
    db = TestingSessionLocal()
    admin = _create_user(db, email="admin-notice@example.com", apple_sub="admin-notice-sub")
    db.add(UserRole(user_id=admin.id, role_type="admin"))
    db.commit()

    headers = _auth_headers_for_user(admin.id)

    warning_resp = client.post(
        "/admin/system-notices",
        json={
            "title": "Warning",
            "message": "Low priority",
            "type": "warning",
            "isActive": True,
            "showAs": "banner",
            "dismissible": True,
        },
        headers=headers,
    )
    assert warning_resp.status_code == 200

    critical_resp = client.post(
        "/admin/system-notices",
        json={
            "title": "Critical",
            "message": "High priority",
            "type": "critical",
            "isActive": True,
            "showAs": "modal",
            "dismissible": False,
        },
        headers=headers,
    )
    assert critical_resp.status_code == 200
    critical_id = critical_resp.json()["id"]

    active_resp = client.get("/system/notice")
    assert active_resp.status_code == 200
    active_body = active_resp.json()
    assert active_body["isActive"] is True
    assert active_body["notice"]["type"] == "critical"

    deactivate_resp = client.post(
        f"/admin/system-notices/{critical_id}/deactivate",
        headers=headers,
    )
    assert deactivate_resp.status_code == 200

    active_resp_after = client.get("/system/notice")
    assert active_resp_after.status_code == 200
    active_body_after = active_resp_after.json()
    assert active_body_after["isActive"] is True
    assert active_body_after["notice"]["type"] == "warning"


def test_session_access_control_user_and_admin_paths():
    db = TestingSessionLocal()

    user_one = _create_user(db, email="user-one@example.com", apple_sub="user-one-sub")
    user_two = _create_user(db, email="user-two@example.com", apple_sub="user-two-sub")
    admin = _create_user(db, email="admin-sessions@example.com", apple_sub="admin-sessions-sub")
    db.add(UserRole(user_id=admin.id, role_type="admin"))
    db.commit()

    token_one, own_session = _create_tracked_session(db, user_one.id)
    _, other_user_session = _create_tracked_session(db, user_two.id)

    user_one_headers = {"Authorization": f"Bearer {token_one}"}

    forbidden_revoke = client.delete(
        f"/account/sessions/{other_user_session.id}",
        headers=user_one_headers,
    )
    assert forbidden_revoke.status_code == 404

    own_revoke = client.delete(
        f"/account/sessions/{own_session.id}",
        headers=user_one_headers,
    )
    assert own_revoke.status_code == 200
    assert own_revoke.json()["success"] is True

    admin_headers = _auth_headers_for_user(admin.id)
    admin_list = client.get(
        f"/admin/users/{user_two.id}/sessions",
        headers=admin_headers,
    )
    assert admin_list.status_code == 200
    assert len(admin_list.json()) == 1


def test_moderation_role_requests_include_user_identity_and_requested_role():
    db = TestingSessionLocal()

    requester = _create_user(
        db,
        email="role-requester@example.com",
        apple_sub="role-requester-sub",
    )
    requester.display_name = "Role Requester"
    db.add(
        UserSettings(
            user_id=requester.id,
            selected_group_id=101,
            selected_group_name="ИС-101",
        )
    )
    moderator = _create_user(
        db,
        email="role-moderator@example.com",
        apple_sub="role-moderator-sub",
    )
    db.add(UserRole(user_id=moderator.id, role_type="moderator"))
    db.commit()

    create_response = client.post(
        "/role-requests",
        json={
            "roleType": "group_leader",
            "comment": "Хочу стать старостой",
        },
        headers=_auth_headers_for_user(requester.id),
    )

    assert create_response.status_code == 200
    request_id = create_response.json()["id"]

    response = client.get(
        "/moderation/role-requests",
        headers=_auth_headers_for_user(moderator.id),
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["userName"] == "Role Requester"
    assert body[0]["userEmail"] == "role-requester@example.com"
    assert body[0]["requestedRole"] == "group_leader"
    assert body[0]["roleType"] == "group_leader"
    assert body[0]["groupId"] == 101
    assert body[0]["groupName"] == "ИС-101"
    assert body[0]["comment"] == "Хочу стать старостой"
    assert body[0]["message"] == "Хочу стать старостой"
    assert body[0]["status"] == "pending"
    assert body[0]["createdAt"] is not None

    reject_response = client.post(
        f"/moderation/role-requests/{request_id}/reject",
        json={"comment": "Нужно подтверждение от группы"},
        headers=_auth_headers_for_user(moderator.id),
    )

    assert reject_response.status_code == 200
    rejected_body = reject_response.json()
    assert rejected_body["status"] == "rejected"
    assert rejected_body["comment"] == "Хочу стать старостой"
    assert rejected_body["reviewComment"] == "Нужно подтверждение от группы"

    my_requests_response = client.get(
        "/role-requests/me",
        headers=_auth_headers_for_user(requester.id),
    )

    assert my_requests_response.status_code == 200
    my_request = my_requests_response.json()[0]
    assert my_request["status"] == "rejected"
    assert my_request["reviewComment"] == "Нужно подтверждение от группы"
    assert my_request["groupName"] == "ИС-101"


def test_moderation_can_approve_group_leader_role_request():
    db = TestingSessionLocal()

    requester = _create_user(
        db,
        email="approve-role-requester@example.com",
        apple_sub="approve-role-requester-sub",
    )
    db.add(
        UserSettings(
            user_id=requester.id,
            selected_group_id=202,
            selected_group_name="ИС-202",
        )
    )
    moderator = _create_user(
        db,
        email="approve-role-moderator@example.com",
        apple_sub="approve-role-moderator-sub",
    )
    db.add(UserRole(user_id=moderator.id, role_type="moderator"))
    db.commit()

    create_response = client.post(
        "/role-requests",
        json={"roleType": "group_leader"},
        headers=_auth_headers_for_user(requester.id),
    )
    assert create_response.status_code == 200

    approve_response = client.post(
        f"/moderation/role-requests/{create_response.json()['id']}/approve",
        headers=_auth_headers_for_user(moderator.id),
    )

    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"

    granted_role = db.query(UserRole).filter(
        UserRole.user_id == requester.id,
        UserRole.role_type == "group_leader",
        UserRole.group_id == 202,
    ).first()
    assert granted_role is not None


def test_group_users_include_selected_group_users_and_active_memberships():
    db = TestingSessionLocal()

    first_user = _create_user(
        db,
        email="first-group-user@example.com",
        apple_sub="first-group-user-sub",
    )
    first_user.display_name = "First Group User"
    second_user = _create_user(
        db,
        email="second-group-user@example.com",
        apple_sub="second-group-user-sub",
    )
    second_user.display_name = "Second Group User"
    membership_user = _create_user(
        db,
        email="membership-user@example.com",
        apple_sub="membership-user-sub",
    )
    membership_user.display_name = "Membership User"
    other_group_user = _create_user(
        db,
        email="other-group-user@example.com",
        apple_sub="other-group-user-sub",
    )
    other_group_user.display_name = "Other Group User"

    db.add_all(
        [
            UserSettings(
                user_id=first_user.id,
                selected_group_id=303,
                selected_group_name="ИС-303",
            ),
            UserSettings(
                user_id=second_user.id,
                selected_group_id=303,
                selected_group_name="ИС-303",
            ),
            UserSettings(
                user_id=other_group_user.id,
                selected_group_id=404,
                selected_group_name="ИС-404",
            ),
            GroupMembership(
                user_id=membership_user.id,
                group_id=303,
                role="member",
                status="active",
            ),
        ]
    )
    db.commit()

    response = client.get(
        "/groups/303/users",
        headers=_auth_headers_for_user(first_user.id),
    )

    assert response.status_code == 200
    body = response.json()
    emails = {item["email"] for item in body}

    assert emails == {
        "first-group-user@example.com",
        "second-group-user@example.com",
        "membership-user@example.com",
    }
    assert {item["group_id"] for item in body} == {303}


def test_group_users_rejects_user_from_different_selected_group():
    db = TestingSessionLocal()

    user = _create_user(
        db,
        email="wrong-group-user@example.com",
        apple_sub="wrong-group-user-sub",
    )
    db.add(
        UserSettings(
            user_id=user.id,
            selected_group_id=404,
            selected_group_name="ИС-404",
        )
    )
    db.commit()

    response = client.get(
        "/groups/303/users",
        headers=_auth_headers_for_user(user.id),
    )

    assert response.status_code == 403


def test_settings_rejects_direct_group_change_after_default_group_is_set():
    db = TestingSessionLocal()

    user = _create_user(
        db,
        email="direct-group-change@example.com",
        apple_sub="direct-group-change-sub",
    )
    db.add(
        UserSettings(
            user_id=user.id,
            selected_group_id=303,
            selected_group_name="ИС-303",
        )
    )
    db.commit()

    response = client.put(
        "/settings",
        json={
            "selectedGroupId": 404,
            "selectedGroupName": "ИС-404",
            "scheduleCacheWeeks": 2,
            "liveActivityEnabled": True,
        },
        headers=_auth_headers_for_user(user.id),
    )

    assert response.status_code == 409
    db.refresh(user)
    settings = db.query(UserSettings).filter(UserSettings.user_id == user.id).first()
    assert settings.selected_group_id == 303
    assert settings.selected_group_name == "ИС-303"


def test_group_change_request_moves_user_after_moderator_approval():
    db = TestingSessionLocal()

    requester = _create_user(
        db,
        email="group-change-requester@example.com",
        apple_sub="group-change-requester-sub",
    )
    requester.display_name = "Group Change Requester"
    moderator = _create_user(
        db,
        email="group-change-moderator@example.com",
        apple_sub="group-change-moderator-sub",
    )
    db.add_all(
        [
            UserSettings(
                user_id=requester.id,
                selected_group_id=303,
                selected_group_name="ИС-303",
            ),
            UserRole(user_id=moderator.id, role_type="moderator"),
        ]
    )
    db.commit()

    create_response = client.post(
        "/group-change-requests",
        json={
            "requestedGroupId": 404,
            "requestedGroupName": "ИС-404",
            "comment": "Перевели в другую группу",
        },
        headers=_auth_headers_for_user(requester.id),
    )

    assert create_response.status_code == 200
    request_body = create_response.json()
    assert request_body["status"] == "pending"
    assert request_body["currentGroupId"] == 303
    assert request_body["requestedGroupId"] == 404

    settings = db.query(UserSettings).filter(UserSettings.user_id == requester.id).first()
    assert settings.selected_group_id == 303

    moderation_response = client.get(
        "/moderation/group-change-requests",
        headers=_auth_headers_for_user(moderator.id),
    )

    assert moderation_response.status_code == 200
    moderation_body = moderation_response.json()
    assert len(moderation_body) == 1
    assert moderation_body[0]["userEmail"] == "group-change-requester@example.com"

    approve_response = client.post(
        f"/moderation/group-change-requests/{request_body['id']}/approve",
        headers=_auth_headers_for_user(moderator.id),
    )

    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"

    db.refresh(settings)
    assert settings.selected_group_id == 404
    assert settings.selected_group_name == "ИС-404"

    group_users_response = client.get(
        "/groups/404/users",
        headers=_auth_headers_for_user(requester.id),
    )

    assert group_users_response.status_code == 200
    assert group_users_response.json()[0]["email"] == "group-change-requester@example.com"


def test_group_change_request_rejects_duplicate_pending_request():
    db = TestingSessionLocal()

    user = _create_user(
        db,
        email="duplicate-group-change@example.com",
        apple_sub="duplicate-group-change-sub",
    )
    db.add(
        UserSettings(
            user_id=user.id,
            selected_group_id=303,
            selected_group_name="ИС-303",
        )
    )
    db.commit()

    first_response = client.post(
        "/group-change-requests",
        json={"requestedGroupId": 404, "requestedGroupName": "ИС-404"},
        headers=_auth_headers_for_user(user.id),
    )
    second_response = client.post(
        "/group-change-requests",
        json={"requestedGroupId": 505, "requestedGroupName": "ИС-505"},
        headers=_auth_headers_for_user(user.id),
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 400
