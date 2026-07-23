from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.models.user import User, UserRole
from app.schemas.document import DocumentCreate
from app.services.document_service import create_generated_document


STAGE_LABELS = {
    "queued": "Queued",
    "validating_template": "Template sync",
    "generating_blueprint": "Generating blueprint",
    "generating_batch": "Generating batch",
    "validating_batch": "Validating batch",
    "repairing_questions": "Repairing questions",
    "compiling_document": "Compiling document",
    "generating_content": "AI generation",
    "extracting_content": "Content extraction",
    "saving_document": "Saving",
    "preview_ready": "Preview ready",
    "failed": "Failed",
}


@dataclass
class GenerationJob:
    job_id: str
    tenant_id: str
    user_id: str
    status: str
    stage: str
    stage_label: str
    message: str
    progress: int
    document_id: str | None
    error: str | None
    created_at: datetime
    updated_at: datetime


_jobs: dict[str, GenerationJob] = {}
_jobs_lock = Lock()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _public_job(job: GenerationJob) -> dict:
    return {
        "job_id": job.job_id,
        "status": job.status,
        "stage": job.stage,
        "stage_label": job.stage_label,
        "message": job.message,
        "progress": job.progress,
        "document_id": job.document_id,
        "error": job.error,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


def _update_job(job_id: str, *, status: str | None = None, stage: str | None = None, message: str | None = None, progress: int | None = None, document_id: str | None = None, error: str | None = None) -> None:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return
        if status is not None:
            job.status = status
        if stage is not None:
            job.stage = stage
            job.stage_label = STAGE_LABELS.get(stage, stage.replace("_", " ").title())
        if message is not None:
            job.message = message
        if progress is not None:
            job.progress = max(0, min(100, progress))
        if document_id is not None:
            job.document_id = document_id
        if error is not None:
            job.error = error
        job.updated_at = _now()


def create_generation_job(payload: DocumentCreate, user: User) -> dict:
    now = _now()
    job = GenerationJob(
        job_id=str(uuid4()),
        tenant_id=user.tenant_id,
        user_id=user.id,
        status="QUEUED",
        stage="queued",
        stage_label=STAGE_LABELS["queued"],
        message="Generation request received by the backend.",
        progress=5,
        document_id=None,
        error=None,
        created_at=now,
        updated_at=now,
    )
    with _jobs_lock:
        _jobs[job.job_id] = job
    return _public_job(job)


def get_generation_job(job_id: str, user: User) -> dict:
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation job not found")
    if user.role != UserRole.SUPER_ADMIN.value and (job.tenant_id != user.tenant_id or job.user_id != user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation job not found")
    return _public_job(job)


def run_generation_job(job_id: str, payload: DocumentCreate, user_id: str) -> None:
    _update_job(job_id, status="RUNNING", stage="validating_template", message="Starting template validation.", progress=10)

    with SessionLocal() as db:
        user = db.get(User, user_id)
        if not user:
            _update_job(job_id, status="FAILED", stage="failed", message="The requesting user no longer exists.", progress=100, error="User not found")
            return

        def progress_callback(stage: str, message: str, progress: int) -> None:
            _update_job(job_id, status="RUNNING", stage=stage, message=message, progress=progress)

        try:
            document = create_generated_document(db, payload, user, progress_callback=progress_callback)
        except HTTPException as exc:
            db.rollback()
            detail = exc.detail if isinstance(exc.detail, str) else "Document generation failed"
            _update_job(job_id, status="FAILED", stage="failed", message=detail, error=detail)
        except SQLAlchemyError as exc:
            db.rollback()
            message = "Document generation failed while saving to the database. Run migrations and try again."
            _update_job(job_id, status="FAILED", stage="failed", message=message, error=message)
        except Exception as exc:
            db.rollback()
            message = f"Document generation failed: {exc}"
            _update_job(job_id, status="FAILED", stage="failed", message=message, error=message)
        else:
            _update_job(job_id, status="COMPLETED", stage="preview_ready", message="Generation complete. Preview is ready.", progress=100, document_id=document.id)
