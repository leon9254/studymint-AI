from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_tenant, require_roles
from app.models.tenant import Tenant
from app.models.user import UserRole
from app.schemas.tenant import TenantRead

router = APIRouter()


@router.get("/current", response_model=TenantRead)
def current_tenant(tenant: Tenant = Depends(get_current_tenant)):
    return tenant


@router.get("", response_model=list[TenantRead])
def list_tenants(
    _: object = Depends(require_roles(UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    return list(db.scalars(select(Tenant).order_by(Tenant.created_at.desc())))
