from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_tenant
from app.models.tenant import Tenant
from app.schemas.template import TemplateRead
from app.services.template_service import list_templates

router = APIRouter()


@router.get("", response_model=list[TemplateRead])
def templates(tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    return list_templates(db, tenant.id)
