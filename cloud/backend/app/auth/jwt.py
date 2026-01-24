"""
JWT Token Handling
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

import jwt
from jwt.exceptions import InvalidTokenError

from app.config import get_settings

settings = get_settings()


def create_access_token(
    user_id: UUID,
    email: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a new access token."""
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )

    payload = {
        "sub": str(user_id),
        "email": email,
        "type": "access",
        "exp": expire,
        "iat": datetime.utcnow(),
    }

    return jwt.encode(
        payload,
        settings.secret_key,
        algorithm=settings.jwt_algorithm
    )


def create_refresh_token(
    user_id: UUID,
    email: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a new refresh token."""
    expire = datetime.utcnow() + (
        expires_delta or timedelta(days=settings.refresh_token_expire_days)
    )

    payload = {
        "sub": str(user_id),
        "email": email,
        "type": "refresh",
        "exp": expire,
        "iat": datetime.utcnow(),
    }

    return jwt.encode(
        payload,
        settings.secret_key,
        algorithm=settings.jwt_algorithm
    )


def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
    """
    Verify a JWT token and return the payload.

    Returns None if token is invalid.
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm]
        )

        # Verify token type
        if payload.get("type") != token_type:
            return None

        return payload

    except InvalidTokenError:
        return None
