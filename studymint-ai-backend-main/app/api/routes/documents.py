from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.document import Document
from app.models.user import User
from app.schemas.document import DashboardStats, DocumentCreate, DocumentRead, GenerationJobRead
from app.services import document_service
from app.services import generation_job_service

router = APIRouter()


def _serialize_document(document: Document) -> dict:
    latest = document_service.latest_version(document)
    return {
        "id": document.id,
        "tenant_id": document.tenant_id,
        "owner_id": document.owner_id,
        "template_id": document.template_id,
        "title": document.title,
        "subject": document.subject,
        "education_level": document.education_level,
        "document_type": document.document_type,
        "target_platform": document.target_platform,
        "output_language": document.output_language,
        "length": document.length,
        "status": document.status,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
        "latest_version": latest,
        "generation_time_seconds": document.generation_time_seconds,
    }


@router.get("/stats", response_model=DashboardStats)
def stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return document_service.dashboard_stats(db, current_user)


@router.get("", response_model=list[DocumentRead])
def list_documents(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [_serialize_document(document) for document in document_service.list_documents(db, current_user)]


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def create_document(payload: DocumentCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    document = document_service.create_generated_document(db, payload, current_user)
    return _serialize_document(document)


@router.post("/generation-jobs", response_model=GenerationJobRead, status_code=status.HTTP_202_ACCEPTED)
def create_generation_job(payload: DocumentCreate, background_tasks: BackgroundTasks, current_user: User = Depends(get_current_user)):
    job = generation_job_service.create_generation_job(payload, current_user)
    background_tasks.add_task(generation_job_service.run_generation_job, job["job_id"], payload, current_user.id)
    return job


@router.get("/generation-jobs/{job_id}", response_model=GenerationJobRead)
def get_generation_job(job_id: str, current_user: User = Depends(get_current_user)):
    return generation_job_service.get_generation_job(job_id, current_user)


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    document = document_service.get_document(db, document_id, current_user)
    return _serialize_document(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    document_service.delete_document(db, document_id, current_user)
    return None
