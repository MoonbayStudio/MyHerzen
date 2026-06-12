import os

import pytest
from fastapi import HTTPException

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET"] = "test_secret"
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"

from app.utils import google_auth  # noqa: E402


def test_verify_google_token_uses_token_audience(monkeypatch):
    verify_calls = []

    monkeypatch.setattr(
        google_auth,
        "GOOGLE_CLIENT_IDS",
        ["web-client-id", "ios-client-id"],
    )
    monkeypatch.setattr(
        google_auth.jose_jwt,
        "get_unverified_claims",
        lambda _token: {
            "aud": "ios-client-id",
            "iss": "https://accounts.google.com",
        },
    )

    def fake_verify(token, request, audience):
        verify_calls.append(
            {
                "token": token,
                "request": request,
                "audience": audience,
            }
        )
        return {
            "sub": "google-sub",
            "email": "user@example.com",
            "email_verified": True,
            "iss": "https://accounts.google.com",
            "aud": "ios-client-id",
        }

    monkeypatch.setattr(
        google_auth.google_id_token,
        "verify_oauth2_token",
        fake_verify,
    )

    payload = google_auth.verify_google_token("id-token")

    assert payload["sub"] == "google-sub"
    assert verify_calls[0]["token"] == "id-token"
    assert verify_calls[0]["audience"] == "ios-client-id"


def test_verify_google_token_rejects_unconfigured_audience(monkeypatch):
    monkeypatch.setattr(google_auth, "GOOGLE_CLIENT_IDS", ["web-client-id"])
    monkeypatch.setattr(
        google_auth.jose_jwt,
        "get_unverified_claims",
        lambda _token: {
            "aud": "ios-client-id",
            "iss": "https://accounts.google.com",
        },
    )
    monkeypatch.setattr(
        google_auth.jose_jwt,
        "get_unverified_header",
        lambda _token: {
            "alg": "RS256",
            "kid": "google-key-id",
        },
    )

    with pytest.raises(HTTPException) as error:
        google_auth.verify_google_token("id-token")

    assert error.value.status_code == 401
    assert error.value.detail == "Invalid Google token audience"
