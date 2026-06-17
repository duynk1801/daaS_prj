"""
JWT token utilities for authentication.

Security rules enforced:
- NEVER hardcode secrets — resolved from env or ephemeral random (see settings.py)
- Algorithm hardcoded to HS256 — NEVER derived from token header
- 'none' algorithm explicitly rejected
- 'exp' claim always set and validated on decode
- Token type ('access' | 'refresh') validated to prevent type confusion attacks
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Literal, Optional

from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError

from app.config.settings import get_settings
from app.shared.exceptions.custom_exceptions import UnauthorizedError

logger = logging.getLogger(__name__)

_settings = get_settings()

# Hardcode algorithm — NEVER read from token header
_ALGORITHM = "HS256"

# Explicitly disallowed algorithms
_DISALLOWED_ALGORITHMS = {"none", "None", "NONE"}


def _get_secret() -> str:
    """Return the JWT secret. Validated at startup via settings validator."""
    return _settings.JWT_SECRET_KEY


def create_access_token(
    subject: str,
    additional_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        subject: The token subject (typically user_id).
        additional_claims: Extra claims to include in the payload.

    Returns:
        Signed JWT string.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=_settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: Dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
        "type": "access",
    }
    if additional_claims:
        # Prevent overwriting security-critical claims
        for key in ("sub", "exp", "iat", "type"):
            additional_claims.pop(key, None)
        payload.update(additional_claims)

    return jwt.encode(payload, _get_secret(), algorithm=_ALGORITHM)


def create_refresh_token(subject: str) -> str:
    """
    Create a signed JWT refresh token with longer expiry.

    Args:
        subject: The token subject (typically user_id).

    Returns:
        Signed JWT string.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=_settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    payload: Dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, _get_secret(), algorithm=_ALGORITHM)


def decode_token(
    token: str,
    expected_type: Literal["access", "refresh"] = "access",
) -> Dict[str, Any]:
    """
    Decode and validate a JWT token.

    Validates:
    - Signature using hardcoded HS256
    - 'exp' claim (raises UnauthorizedError if expired)
    - 'type' claim to prevent access/refresh token confusion

    Args:
        token: The JWT string to decode.
        expected_type: Expected token type ('access' or 'refresh').

    Returns:
        Decoded payload dict.

    Raises:
        UnauthorizedError: If token is invalid, expired, or wrong type.
    """
    # Reject 'none' algorithm attempts
    if token in _DISALLOWED_ALGORITHMS:
        raise UnauthorizedError("Invalid token")

    try:
        payload = jwt.decode(
            token,
            _get_secret(),
            algorithms=[_ALGORITHM],  # Hardcoded — never from token header
            options={"require": ["sub", "exp", "iat", "type"]},
        )
    except ExpiredSignatureError:
        raise UnauthorizedError("Token has expired")
    except JWTError:
        # Generic error — do NOT expose internals to client
        logger.warning("JWT decode failed (invalid token)")
        raise UnauthorizedError("Invalid or malformed token")

    # Validate token type to prevent type-confusion attacks
    if payload.get("type") != expected_type:
        raise UnauthorizedError(f"Expected token type '{expected_type}'")

    return payload


def get_subject(token: str) -> str:
    """
    Extract and validate the subject (user_id) from an access token.

    Args:
        token: JWT access token string.

    Returns:
        The token subject string.

    Raises:
        UnauthorizedError: If token is invalid.
    """
    payload = decode_token(token, expected_type="access")
    subject = payload.get("sub")
    if not subject:
        raise UnauthorizedError("Token missing subject claim")
    return subject
