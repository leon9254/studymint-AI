import re
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.email_service import EmailDeliveryError, send_password_reset_email, send_verification_email


class AuthError(RuntimeError):
    pass


class InvalidCredentialsError(AuthError):
    pass


class EmailNotVerifiedError(AuthError):
    pass


class VerificationError(AuthError):
    pass


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "workspace"


def _workspace_name_for_user(payload: RegisterRequest) -> str:
    if payload.workspace_name:
        return payload.workspace_name

    name = payload.full_name.strip()
    if name:
        return f"{name}'s Workspace"

    email_name = str(payload.email).split("@", 1)[0].replace(".", " ").replace("_", " ").strip()
    return f"{email_name or 'StudyMint'} Workspace"


def _hash_verification_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _verification_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS)


def _password_reset_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)


def _verification_url(token: str) -> str:
    return f"{settings.FRONTEND_PUBLIC_URL.rstrip('/')}/verify-email?token={token}"


def _password_reset_url(token: str) -> str:
    return f"{settings.FRONTEND_PUBLIC_URL.rstrip('/')}/reset-password?token={token}"


def _email_delivery_required() -> bool:
    return settings.ENVIRONMENT.lower() == "production"


def _issue_verification_token(user: User) -> str:
    token = secrets.token_urlsafe(48)
    user.email_verification_token_hash = _hash_verification_token(token)
    user.email_verification_expires_at = _verification_expires_at()
    return token


def _issue_password_reset_token(user: User) -> str:
    token = secrets.token_urlsafe(48)
    user.password_reset_token_hash = _hash_verification_token(token)
    user.password_reset_expires_at = _password_reset_expires_at()
    return token


def authenticate_user(db: Session, payload: LoginRequest) -> User:
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.hashed_password):
        raise InvalidCredentialsError
    if not user.email_verified:
        raise EmailNotVerifiedError
    return user


def register_workspace(db: Session, payload: RegisterRequest) -> User:
    if db.scalar(select(User).where(User.email == str(payload.email))):
        raise AuthError("An account with this email already exists")

    workspace_name = _workspace_name_for_user(payload)
    base_slug = _slugify(workspace_name)
    slug = base_slug
    suffix = 2
    while db.scalar(select(Tenant).where(Tenant.slug == slug)):
        slug = f"{base_slug}-{suffix}"
        suffix += 1

    tenant = Tenant(name=workspace_name, slug=slug, plan="starter")
    db.add(tenant)
    db.flush()

    user = User(
        tenant_id=tenant.id,
        email=str(payload.email),
        full_name=payload.full_name,
        hashed_password=get_password_hash(payload.password),
        role=UserRole.USER.value,
        email_verified=False,
    )
    token = _issue_verification_token(user)
    db.add(user)
    db.flush()
    try:
        send_verification_email(user.email, user.full_name, _verification_url(token))
    except EmailDeliveryError:
        if _email_delivery_required():
            db.rollback()
            raise
        user.email_verified = True
        user.email_verified_at = datetime.now(timezone.utc)
        user.email_verification_token_hash = None
        user.email_verification_expires_at = None
    except Exception:
        db.rollback()
        raise
    db.commit()
    db.refresh(user)
    return user


def resend_verification_email(db: Session, email: str) -> None:
    user = db.scalar(select(User).where(User.email == email))
    if not user or user.email_verified:
        return

    token = _issue_verification_token(user)
    db.commit()
    send_verification_email(user.email, user.full_name, _verification_url(token))


def request_password_reset(db: Session, email: str) -> None:
    user = db.scalar(select(User).where(User.email == email))
    if not user or not user.is_active:
        return

    token = _issue_password_reset_token(user)
    db.flush()
    try:
        send_password_reset_email(user.email, user.full_name, _password_reset_url(token))
    except Exception:
        db.rollback()
        raise
    db.commit()


def reset_password(db: Session, token: str, password: str) -> None:
    token_hash = _hash_verification_token(token)
    user = db.scalar(select(User).where(User.password_reset_token_hash == token_hash))
    if not user or not user.is_active:
        raise VerificationError("Invalid or expired password reset link")

    expires_at = user.password_reset_expires_at
    if not expires_at:
        raise VerificationError("Invalid or expired password reset link")
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise VerificationError("Invalid or expired password reset link")

    user.hashed_password = get_password_hash(password)
    user.password_reset_token_hash = None
    user.password_reset_expires_at = None
    user.email_verified = True
    user.email_verified_at = user.email_verified_at or datetime.now(timezone.utc)
    user.email_verification_token_hash = None
    user.email_verification_expires_at = None
    db.commit()


def verify_email_token(db: Session, token: str) -> User:
    token_hash = _hash_verification_token(token)
    user = db.scalar(select(User).where(User.email_verification_token_hash == token_hash))
    if not user:
        raise VerificationError("Invalid verification link")

    expires_at = user.email_verification_expires_at
    if not expires_at:
        raise VerificationError("Invalid verification link")
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise VerificationError("Verification link has expired")

    user.email_verified = True
    user.email_verified_at = datetime.now(timezone.utc)
    user.email_verification_token_hash = None
    user.email_verification_expires_at = None
    db.commit()
    db.refresh(user)
    return user


def build_registration_response(user: User) -> dict[str, object]:
    if user.email_verified:
        return {
            "message": "Account created successfully. Your account is ready to use. You can sign in now.",
            "email": user.email,
            "requires_email_verification": False,
        }

    return {
        "message": "Account created. Please check your email to verify your account before signing in.",
        "email": user.email,
        "requires_email_verification": True,
    }


def build_auth_response(user: User) -> dict:
    token = create_access_token(subject=user.id, additional_claims={"tenant_id": user.tenant_id, "role": user.role})
    return {"access_token": token, "token_type": "bearer", "user": user}
