from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user, require_roles
from app.models.user import User, UserRole
from app.schemas.user import UserRead

router = APIRouter()


@router.get("", response_model=list[UserRead])
def list_users(
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    stmt = select(User)
    if current_user.role != UserRole.SUPER_ADMIN.value:
        stmt = stmt.where(User.tenant_id == current_user.tenant_id)
    return list(db.scalars(stmt.order_by(User.created_at.desc())))


@router.get("/me", response_model=UserRead)
def current_user_profile(current_user: User = Depends(get_current_user)):
    return current_user
