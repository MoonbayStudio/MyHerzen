import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

import os
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET"] = "test_secret"
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
os.environ["OWNER_EMAILS"] = "owner@example.com"

from app.main import (
    app, Base, get_db, User, Role, UserRole,
    get_user_plan, is_owner, has_permission,
    RoleAuditLog
)

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # Create roles
    roles = [
        Role(name="admin", daily_limit=-1),
        Role(name="tester", daily_limit=-1),
        Role(name="premium", daily_limit=200),
        Role(name="plus", daily_limit=50),
        Role(name="free", daily_limit=10),
    ]
    db.add_all(roles)
    db.commit()
    
    yield
    
    db.close()
    Base.metadata.drop_all(bind=engine)


def _test_user(email: str) -> User:
    return User(apple_sub=f"test-{email}", contact_email=email)


def test_owner_always_admin():
    db = TestingSessionLocal()
    owner = _test_user("owner@example.com")
    normal = _test_user("user@example.com")
    db.add_all([owner, normal])
    db.commit()
    
    assert is_owner(owner) == True
    assert is_owner(normal) == False
    
    assert get_user_plan(owner.id, db) == "admin"
    assert get_user_plan(normal.id, db) == "free"

    # Owner has all permissions implicitly checked via has_permission
    assert has_permission(owner, "manage_roles", db) == True
    assert has_permission(owner, "any_random_perm", db) == True

def test_tester_unlimited():
    db = TestingSessionLocal()
    tester = _test_user("tester@example.com")
    db.add(tester)
    db.commit()
    
    db.add(UserRole(user_id=tester.id, role_type="tester"))
    db.commit()
    
    assert get_user_plan(tester.id, db) == "tester"
    # Wait, testing AI limit logic directly is a bit more complex, but PLAN_LIMITS is imported
    from app.main import PLAN_LIMITS
    assert PLAN_LIMITS[get_user_plan(tester.id, db)] == -1

def test_multiple_roles_highest_priority():
    db = TestingSessionLocal()
    user = _test_user("multi@example.com")
    db.add(user)
    db.commit()
    
    db.add(UserRole(user_id=user.id, role_type="plus"))
    db.add(UserRole(user_id=user.id, role_type="premium"))
    db.commit()
    
    plan = get_user_plan(user.id, db)
    assert plan == "premium"

def test_permission_system_works():
    db = TestingSessionLocal()
    admin = _test_user("admin@example.com")
    tester = _test_user("tester@example.com")
    db.add_all([admin, tester])
    db.commit()
    
    db.add(UserRole(user_id=admin.id, role_type="admin"))
    db.add(UserRole(user_id=tester.id, role_type="tester"))
    db.commit()
    
    assert has_permission(admin, "manage_roles", db) == True
    assert has_permission(tester, "manage_roles", db) == False
    assert has_permission(tester, "unlimited_ai", db) == True

def test_get_admin_users_protected():
    response = client.get("/admin/users")
    assert response.status_code == 401 # Unauthorized because no user is logged in
    
    # We would need to mock current_user for deeper testing, but the endpoint exists and is protected.

# More complex tests involving endpoints would require mocking the auth token, which might be overkill for this script,
# but we can test the specific logic of "invalid role rejected" and "owner cannot be revoked" directly via functions if they were separated.
# Or we can create a mock token.
from app.main import create_session_token

def get_auth_headers(user_id):
    token = create_session_token(user_id)
    return {"Authorization": f"Bearer {token}"}

def test_invalid_role_rejected():
    db = TestingSessionLocal()
    admin = _test_user("admin_reject@example.com")
    target = _test_user("target@example.com")
    db.add_all([admin, target])
    db.commit()
    db.add(UserRole(user_id=admin.id, role_type="admin"))
    db.commit()
    
    headers = get_auth_headers(admin.id)
    response = client.post("/admin/roles/grant", json={"user_id": target.id, "role": "god"}, headers=headers)
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid role"

def test_cannot_revoke_owner():
    db = TestingSessionLocal()
    admin = _test_user("admin_revoke@example.com")
    owner = _test_user("owner@example.com")
    db.add_all([admin, owner])
    db.commit()
    db.add(UserRole(user_id=admin.id, role_type="admin"))
    db.commit()
    
    headers = get_auth_headers(admin.id)
    response = client.post("/admin/roles/revoke", json={"user_id": owner.id, "role": "admin"}, headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Cannot revoke admin role from owner"

def test_cannot_remove_last_admin():
    db = TestingSessionLocal()
    admin = _test_user("last_admin@example.com")
    db.add(admin)
    db.commit()
    db.add(UserRole(user_id=admin.id, role_type="admin"))
    db.commit()
    
    headers = get_auth_headers(admin.id)
    response = client.post("/admin/roles/revoke", json={"user_id": admin.id, "role": "admin"}, headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Cannot revoke admin from yourself as the last admin"
