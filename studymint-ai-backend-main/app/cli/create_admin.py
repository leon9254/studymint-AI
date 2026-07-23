import argparse
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.tenant import Tenant
from app.models.user import User, UserRole

SYSTEM_TENANT_SLUG = "system-admin"


def _get_or_create_system_tenant(db) -> Tenant:
    tenant = db.scalar(select(Tenant).where(Tenant.slug == SYSTEM_TENANT_SLUG))
    if tenant:
        return tenant

    tenant = Tenant(name="System Administration", slug=SYSTEM_TENANT_SLUG, plan="internal")
    db.add(tenant)
    db.flush()
    return tenant


def create_or_update_admin(email: str, full_name: str, password: str) -> User:
    with SessionLocal() as db:
        tenant = _get_or_create_system_tenant(db)
        user = db.scalar(select(User).where(User.email == email))
        if user:
            user.full_name = full_name
            user.hashed_password = get_password_hash(password)
            user.role = UserRole.SUPER_ADMIN.value
            user.is_active = True
            user.email_verified = True
            user.email_verified_at = user.email_verified_at or datetime.now(timezone.utc)
            user.email_verification_token_hash = None
            user.email_verification_expires_at = None
            if not user.tenant_id:
                user.tenant_id = tenant.id
        else:
            user = User(
                tenant_id=tenant.id,
                email=email,
                full_name=full_name,
                hashed_password=get_password_hash(password),
                role=UserRole.SUPER_ADMIN.value,
                is_active=True,
                email_verified=True,
                email_verified_at=datetime.now(timezone.utc),
            )
            db.add(user)

        db.commit()
        db.refresh(user)
        return user


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update a StudyMint AI super admin user.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--full-name", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    user = create_or_update_admin(args.email, args.full_name, args.password)
    print(f"Super admin ready: {user.email}")


if __name__ == "__main__":
    main()
