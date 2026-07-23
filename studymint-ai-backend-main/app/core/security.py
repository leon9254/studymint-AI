from datetime import datetime, timedelta, timezone
import hashlib
from typing import Any

import bcrypt
from jose import jwt

from app.core.config import settings

ALGORITHM = "HS256"
PASSWORD_HASH_PREFIX = "bcrypt_sha256$"


def _password_digest(password: str) -> bytes:
    return hashlib.sha256(password.encode("utf-8")).digest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if hashed_password.startswith(PASSWORD_HASH_PREFIX):
        bcrypt_hash = hashed_password.removeprefix(PASSWORD_HASH_PREFIX).encode("utf-8")
        return bcrypt.checkpw(_password_digest(plain_password), bcrypt_hash)

    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        return False


def get_password_hash(password: str) -> str:
    bcrypt_hash = bcrypt.hashpw(_password_digest(password), bcrypt.gensalt(rounds=12)).decode("utf-8")
    return f"{PASSWORD_HASH_PREFIX}{bcrypt_hash}"


def create_access_token(subject: str, additional_claims: dict[str, Any] | None = None) -> str:
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + expires_delta
    payload: dict[str, Any] = {"sub": subject, "exp": expire}
    if additional_claims:
        payload.update(additional_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
