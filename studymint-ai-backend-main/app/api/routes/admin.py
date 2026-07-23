from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import require_roles
from app.models.audit import AIUsageLog, AuditLog
from app.models.document import Document
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.schemas.admin import AdminOverview

router = APIRouter()


@router.get("/overview", response_model=AdminOverview)
def overview(
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    tenant_filter = [] if current_user.role == UserRole.SUPER_ADMIN.value else [Tenant.id == current_user.tenant_id]
    document_filter = [] if current_user.role == UserRole.SUPER_ADMIN.value else [Document.tenant_id == current_user.tenant_id]
    user_filter = [] if current_user.role == UserRole.SUPER_ADMIN.value else [User.tenant_id == current_user.tenant_id]
    log_filter = [] if current_user.role == UserRole.SUPER_ADMIN.value else [AIUsageLog.tenant_id == current_user.tenant_id]
    audit_filter = [] if current_user.role == UserRole.SUPER_ADMIN.value else [AuditLog.tenant_id == current_user.tenant_id]

    return AdminOverview(
        users=db.scalar(select(func.count(User.id)).where(*user_filter)) or 0,
        active_users=db.scalar(select(func.count(User.id)).where(User.is_active.is_(True), *user_filter)) or 0,
        unverified_users=db.scalar(select(func.count(User.id)).where(User.email_verified.is_(False), *user_filter)) or 0,
        admin_users=db.scalar(
            select(func.count(User.id)).where(User.role.in_([UserRole.TENANT_ADMIN.value, UserRole.SUPER_ADMIN.value]), *user_filter)
        )
        or 0,
        super_admins=db.scalar(select(func.count(User.id)).where(User.role == UserRole.SUPER_ADMIN.value, *user_filter)) or 0,
        tenants=db.scalar(select(func.count(Tenant.id)).where(*tenant_filter)) or 0,
        generated_documents=db.scalar(select(func.count(Document.id)).where(*document_filter)) or 0,
        ai_usage_events=db.scalar(select(func.count(AIUsageLog.id)).where(*log_filter)) or 0,
        audit_events=db.scalar(select(func.count(AuditLog.id)).where(*audit_filter)) or 0,
        recent_users=list(db.scalars(select(User).where(*user_filter).order_by(User.created_at.desc()).limit(6))),
    )
