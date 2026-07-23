from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, status

from app.core.config import settings
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.stuvia_agent import (
    StuviaAgentRunCreate,
    StuviaAgentRunRead,
    StuviaManualPublishRead,
    StuviaPublisherDocumentPackageRead,
    StuviaPublisherHandoffRead,
)
from app.services import stuvia_agent_service

router = APIRouter()


def require_publisher_handoff_token(authorization: str | None = Header(default=None)) -> None:
    expected = settings.N8N_STUVIA_WEBHOOK_TOKEN.strip()
    if not expected:
        return
    if authorization != f"Bearer {expected}":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Stuvia publisher token")


@router.post("/runs", response_model=StuviaAgentRunRead, status_code=status.HTTP_202_ACCEPTED)
def create_stuvia_agent_run(
    payload: StuviaAgentRunCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    run = stuvia_agent_service.create_stuvia_agent_run(payload, current_user)
    background_tasks.add_task(stuvia_agent_service.run_stuvia_agent, run["run_id"], payload, current_user.id)
    return run


@router.get("/runs/{run_id}", response_model=StuviaAgentRunRead)
def get_stuvia_agent_run(run_id: str, current_user: User = Depends(get_current_user)):
    return stuvia_agent_service.get_stuvia_agent_run(run_id, current_user)


@router.post("/documents/{document_id}/publish", response_model=StuviaManualPublishRead)
def publish_stuvia_document(document_id: str, current_user: User = Depends(get_current_user)):
    return stuvia_agent_service.publish_stuvia_document(document_id, current_user)


@router.post("/publisher/handoff", response_model=StuviaPublisherHandoffRead, include_in_schema=False)
def accept_stuvia_publisher_handoff(
    payload: dict[str, Any],
    _token: None = Depends(require_publisher_handoff_token),
):
    return stuvia_agent_service.accept_stuvia_publisher_handoff(payload)


@router.get("/publisher/documents/{document_id}", response_model=StuviaPublisherDocumentPackageRead, include_in_schema=False)
def publisher_document_package(
    document_id: str,
    tenant_id: str,
    _token: None = Depends(require_publisher_handoff_token),
):
    return stuvia_agent_service.publisher_document_package(document_id, tenant_id)


@router.post("/publisher/results", include_in_schema=False)
def accept_stuvia_publish_results(
    payload: dict[str, Any],
    _token: None = Depends(require_publisher_handoff_token),
):
    return stuvia_agent_service.accept_stuvia_publish_results(payload)
