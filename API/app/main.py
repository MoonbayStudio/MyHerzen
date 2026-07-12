from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import CORS_ORIGINS
from app.core.deps import has_permission, is_owner
from app.core.rate_limit import limiter
from app.core.security import create_session_token
from app.db.models import Role, RoleAuditLog, User, UserRole, UserSession
from app.db.session import Base, engine, get_db
from app.routers import (
    account,
    admin_roles,
    admin_badges,
    assistant,
    auth,
    groups,
    role_requests,
    runtime_settings,
    sessions,
    system_notices,
)
from app.services.schema_bootstrap_service import ensure_runtime_feature_tables
from app.services.assistant_policy_service import PLAN_LIMITS, get_user_plan


app = FastAPI(
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    lambda request, exc: JSONResponse(
        status_code=429,
        content={"detail": "Too many requests"},
    ),
)
app.add_middleware(SlowAPIMiddleware)


@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/health")
def health():
    return {"status": "healthy"}


ensure_runtime_feature_tables(engine)

app.include_router(account.router)
app.include_router(admin_roles.router)
app.include_router(admin_badges.router)
app.include_router(assistant.router)
app.include_router(auth.router)
app.include_router(groups.router)
app.include_router(role_requests.router)
app.include_router(runtime_settings.router)
app.include_router(system_notices.router)
app.include_router(sessions.router)
