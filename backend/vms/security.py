"""Password hashing (argon2), JWT access tokens, and API-key hashing."""

import hashlib
import hmac
import logging
import secrets
import time
from datetime import UTC, datetime, timedelta
from functools import lru_cache

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from vms.config import get_settings

log = logging.getLogger(__name__)
_hasher = PasswordHasher()
_ALGORITHM = "HS256"
API_KEY_PREFIX = "vms_"
MIN_PASSWORD_LENGTH = 8
MIN_SECRET_LENGTH = 32


class InsecureConfigError(RuntimeError):
    pass


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    if not password_hash:
        return False
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


@lru_cache
def jwt_secret() -> str:
    settings = get_settings()
    if settings.env != "dev" and len(settings.jwt_secret or "") < MIN_SECRET_LENGTH:
        raise InsecureConfigError(
            f"VMS_JWT_SECRET must be at least {MIN_SECRET_LENGTH} characters "
            f"when VMS_ENV={settings.env!r}."
        )
    if settings.jwt_secret:
        return settings.jwt_secret
    log.warning("VMS_JWT_SECRET is not set: using a random per-process secret (dev only).")
    return secrets.token_urlsafe(48)


def create_access_token(user_id: int, *, ttl: timedelta | None = None) -> str:
    now = datetime.now(UTC)
    ttl = ttl if ttl is not None else timedelta(hours=get_settings().jwt_ttl_hours)
    payload = {"sub": str(user_id), "iat": now, "exp": now + ttl}
    return jwt.encode(payload, jwt_secret(), algorithm=_ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """The user id, or None if the token is invalid or expired."""
    try:
        payload = jwt.decode(
            token, jwt_secret(), algorithms=[_ALGORITHM], options={"require": ["sub", "exp"]}
        )
        return int(payload["sub"])
    except (jwt.PyJWTError, ValueError):
        return None


def new_api_key() -> str:
    return API_KEY_PREFIX + secrets.token_urlsafe(32)


def hash_api_key(key: str) -> str:
    # Keys are long and random, so a fast hash is enough (and allows lookup by hash).
    return hashlib.sha256(key.encode()).hexdigest()


def _media_sig(path: str, exp: int) -> str:
    msg = f"{path}\n{exp}".encode()
    return hmac.new(jwt_secret().encode(), msg, hashlib.sha256).hexdigest()


def sign_media_url(path: str, *, ttl_s: int | None = None) -> str:
    """`path?exp=…&sig=…`: lets `<video>`/`<img>` tags (which can't send headers) load media."""
    ttl_s = ttl_s if ttl_s is not None else get_settings().media_url_ttl_s
    exp = int(time.time()) + ttl_s
    return f"{path}?exp={exp}&sig={_media_sig(path, exp)}"


def verify_media_signature(path: str, exp: int | None, sig: str | None) -> bool:
    if exp is None or not sig or exp < time.time():
        return False
    return hmac.compare_digest(_media_sig(path, exp), sig)
