from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.dependencies import get_current_tenant
from app.schemas.integration import IntegrationRead, StuviaIntegrationConfigRead, StuviaIntegrationConfigUpdate, StuviaInternalCredentialRead
from app.services.integration_service import get_stuvia_connection, get_stuvia_internal_credentials, list_integrations, update_stuvia_connection

router = APIRouter()


def require_stuvia_internal_token(authorization: str | None = Header(default=None)) -> None:
    expected_token = settings.N8N_STUVIA_WEBHOOK_TOKEN.strip()
    if not expected_token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Internal Stuvia credential endpoint is not enabled")
    if authorization != f"Bearer {expected_token}":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid internal Stuvia credential token")


@router.get("", response_model=list[IntegrationRead])
def integrations(current_tenant=Depends(get_current_tenant), db: Session = Depends(get_db)):
    return list_integrations(db, current_tenant.id)


@router.get("/stuvia", response_model=StuviaIntegrationConfigRead)
def stuvia_connection(current_tenant=Depends(get_current_tenant), db: Session = Depends(get_db)):
    return get_stuvia_connection(db, current_tenant.id)


@router.put("/stuvia", response_model=StuviaIntegrationConfigRead)
def update_stuvia(
    payload: StuviaIntegrationConfigUpdate,
    current_tenant=Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    return update_stuvia_connection(db, current_tenant.id, payload)


@router.get("/stuvia/internal-credentials/{tenant_id}", response_model=StuviaInternalCredentialRead, include_in_schema=False)
def stuvia_internal_credentials(
    tenant_id: str,
    _token: None = Depends(require_stuvia_internal_token),
    db: Session = Depends(get_db),
):
    return get_stuvia_internal_credentials(db, tenant_id)
