import os


def _parse_bool_env(var_name: str, default: bool) -> bool:
    raw_value = os.getenv(var_name)
    if raw_value is None:
        return default

    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False

    return default


def _parse_int_env(var_name: str, default: int) -> int:
    raw_value = os.getenv(var_name)
    if raw_value is None:
        return default

    try:
        return int(raw_value.strip())
    except (TypeError, ValueError):
        return default

APPLE_KEYS_URL = "https://appleid.apple.com/auth/keys"
APPLE_AUDIENCES = [
    "MoonbayStudio.MyHerzen",
    "ru.moonbay.myherzen.web",
    "ru.moonbaystudio.myherzen.web"
]
if os.getenv("APPLE_CLIENT_ID"):
    APPLE_AUDIENCES.append(os.getenv("APPLE_CLIENT_ID"))

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET is not configured")

HERZEN_API_BASE_URL = os.getenv(
    "HERZEN_API_BASE_URL",
    "https://api.herzen.spb.ru"
).rstrip("/")

HERZEN_SCHEDULE_API_PATH = os.getenv(
    "HERZEN_SCHEDULE_API_PATH",
    "/schedule/v1/schedule"
)

FRONTEND_BASE_URL = os.getenv(
    "FRONTEND_BASE_URL",
    "https://myherzen.moonbaystudio.ru"
).rstrip("/")

HERZEN_API_TIMEOUT_SECONDS = 15

ADMIN_EMAILS = os.getenv("ADMIN_EMAILS", "")
ADMIN_EMAIL_SET = {
    email.strip().lower()
    for email in ADMIN_EMAILS.split(",")
    if email.strip()
}

OWNER_EMAILS = os.getenv("OWNER_EMAILS", "")
OWNER_EMAILS_SET = {
    email.strip().lower()
    for email in OWNER_EMAILS.split(",")
    if email.strip()
}

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
INVALID_PASSWORD_LOGIN_DETAIL = "Invalid email or password"
APPLE_RELAY_EMAIL_DOMAIN = "privaterelay.appleid.com"
EMAIL_VERIFICATION_EXPIRES_HOURS = 24

SMTP_HOST = os.getenv("SMTP_HOST", "mail.hosting.reg.ru")
SMTP_PORT = _parse_int_env("SMTP_PORT", 465)
SMTP_USERNAME = os.getenv(
    "SMTP_USERNAME",
    "security@myherzen.moonbaystudio.ru",
)
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_EMAIL = os.getenv(
    "SMTP_FROM_EMAIL",
    "security@myherzen.moonbaystudio.ru",
)
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Мой Герцена")
SMTP_USE_TLS = _parse_bool_env("SMTP_USE_TLS", True)
SMTP_TIMEOUT_SECONDS = _parse_int_env("SMTP_TIMEOUT_SECONDS", 60)
SMTP_FALLBACK_PORTS = [
    int(port.strip())
    for port in os.getenv("SMTP_FALLBACK_PORTS", "587").split(",")
    if port.strip().isdigit()
]
EMAIL_LOGO_PATH = os.getenv("EMAIL_LOGO_PATH", "logomh.png")

GOOGLE_CLIENT_IDS = [
    cid.strip()
    for cid in os.getenv("GOOGLE_CLIENT_IDS", "").split(",")
    if cid.strip()
]
if os.getenv("GOOGLE_WEB_CLIENT_ID"):
    GOOGLE_CLIENT_IDS.append(os.getenv("GOOGLE_WEB_CLIENT_ID"))
if os.getenv("GOOGLE_ANDROID_CLIENT_ID"):
    GOOGLE_CLIENT_IDS.append(os.getenv("GOOGLE_ANDROID_CLIENT_ID"))
if os.getenv("GOOGLE_IOS_CLIENT_ID"):
    GOOGLE_CLIENT_IDS.append(os.getenv("GOOGLE_IOS_CLIENT_ID"))

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
ENABLE_AI_AGENT = _parse_bool_env("ENABLE_AI_AGENT", True)
if ENABLE_AI_AGENT and not OLLAMA_BASE_URL:
    raise RuntimeError("OLLAMA_BASE_URL is not configured")

PELIKASHA_MODEL = os.getenv(
    "PELIKASHA_MODEL",
    "pelikasha:latest"
)
PERSONA_THEME = os.getenv("PERSONA_THEME", "default")
ENABLE_HOMEWORK_MODULE = _parse_bool_env("ENABLE_HOMEWORK_MODULE", True)
ENABLE_ROLE_REQUESTS_MODULE = _parse_bool_env(
    "ENABLE_ROLE_REQUESTS_MODULE",
    True,
)
ENABLE_ADMIN_ROLE_MANAGEMENT_MODULE = _parse_bool_env(
    "ENABLE_ADMIN_ROLE_MANAGEMENT_MODULE",
    True,
)

ROLE_PERMISSIONS = {
    "admin": {
        "manage_roles",
        "unlimited_ai",
    },
    "moderator": {
        "manage_roles",
    },
    "tester": {
        "unlimited_ai",
    },
}
