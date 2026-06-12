from fastapi import HTTPException
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from jose import jwt as jose_jwt

from app.core.config import GOOGLE_CLIENT_IDS

GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


def _get_token_debug_claims(id_token: str) -> dict:
    try:
        headers = jose_jwt.get_unverified_header(id_token)
    except Exception:
        headers = {}

    try:
        claims = jose_jwt.get_unverified_claims(id_token)
    except Exception:
        claims = {}

    return {
        "alg": headers.get("alg"),
        "kid": headers.get("kid"),
        "iss": claims.get("iss"),
        "aud": claims.get("aud"),
    }


def _log_google_token_rejection(reason: str, id_token: str, error: Exception | None = None) -> None:
    debug_claims = _get_token_debug_claims(id_token)
    error_message = f", error={type(error).__name__}: {error}" if error is not None else ""
    print(
        "Google token rejected: "
        f"reason={reason}, "
        f"jwtAlg={debug_claims.get('alg')}, "
        f"jwtKid={debug_claims.get('kid')}, "
        f"jwtIssuer={debug_claims.get('iss')}, "
        f"jwtAudience={debug_claims.get('aud')}, "
        f"configuredAudiences={GOOGLE_CLIENT_IDS}"
        f"{error_message}"
    )


def verify_google_token(id_token: str) -> dict:
    try:
        if not GOOGLE_CLIENT_IDS:
            raise HTTPException(status_code=500, detail="Google client IDs are not configured")

        unverified_claims = jose_jwt.get_unverified_claims(id_token)
        token_audience = unverified_claims.get("aud")

        if token_audience not in GOOGLE_CLIENT_IDS:
            _log_google_token_rejection("invalid_audience", id_token)
            raise HTTPException(status_code=401, detail="Invalid Google token audience")

        payload = google_id_token.verify_oauth2_token(
            id_token,
            google_requests.Request(),
            audience=token_audience,
        )

        if payload.get("iss") not in GOOGLE_ISSUERS:
            _log_google_token_rejection("invalid_issuer", id_token)
            raise HTTPException(status_code=401, detail="Invalid Google token issuer")

        if not payload.get("email_verified", False):
            _log_google_token_rejection("email_not_verified", id_token)
            raise HTTPException(status_code=401, detail="Google email not verified")

        return payload

    except HTTPException:
        raise
    except ValueError as error:
        _log_google_token_rejection("verification_failed", id_token, error)
        raise HTTPException(status_code=401, detail="Invalid Google token")
    except Exception as e:
        print(f"Google auth error: {str(e)}")
        raise HTTPException(status_code=401, detail="Google authentication failed")
