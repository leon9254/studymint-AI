from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import User, UserRole

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive or missing user")
    if not user.email_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email address is not verified")
    return user


def get_current_tenant(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Tenant:
    tenant = db.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant not found")
    return tenant


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in {role.value for role in roles}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return current_user

    return dependency


def ensure_tenant_scope(current_user: User, tenant_id: str) -> None:
    if current_user.role == UserRole.SUPER_ADMIN.value:
        return
    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Outside tenant scope")
