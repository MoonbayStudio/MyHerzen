import bcrypt
from datetime import datetime, timezone, timedelta
from jose import jwt
from fastapi import HTTPException
from backend.app.core.config import (
    JWT_SECRET,
    PASSWORD_MIN_LENGTH,
    PASSWORD_MAX_LENGTH,
)

def create_session_token(user_id: int) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    return jwt.encode(
        {
            "user_id": user_id,
            "exp": expires_at
        },
        JWT_SECRET,
        algorithm="HS256"
    )

def hash_password(password: str) -> str:
    hashed_password = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    )
    return hashed_password.decode("utf-8")

def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8")
        )
    except Exception:
        return False

def validate_password_strength(password: str) -> None:
    if not isinstance(password, str):
        raise HTTPException(
            status_code=400,
            detail="Password is required"
        )
    if not password.strip():
        raise HTTPException(
            status_code=400,
            detail="Password is required"
        )
    password_length = len(password)
    if password_length < PASSWORD_MIN_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at least {PASSWORD_MIN_LENGTH} characters"
        )
    if password_length > PASSWORD_MAX_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at most {PASSWORD_MAX_LENGTH} characters"
        )
    has_letter = any(character.isalpha() for character in password)
    has_number = any(character.isdigit() for character in password)
    if not has_letter or not has_number:
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one letter and one number"
        )
