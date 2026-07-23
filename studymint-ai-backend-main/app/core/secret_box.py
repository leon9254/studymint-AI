import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


_SECRET_PREFIX = "fernet:v1:"


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str) -> str:
    secret = str(value or "")
    if not secret:
        return ""
    token = _fernet().encrypt(secret.encode("utf-8")).decode("ascii")
    return f"{_SECRET_PREFIX}{token}"


def decrypt_secret(value: str) -> str:
    encrypted = str(value or "")
    if not encrypted:
        return ""
    token = encrypted.removeprefix(_SECRET_PREFIX) if encrypted.startswith(_SECRET_PREFIX) else encrypted
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeDecodeError, ValueError):
        return ""
