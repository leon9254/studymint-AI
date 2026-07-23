from datetime import datetime, timezone
from collections.abc import Callable

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.audit import AIUsageLog, AuditLog
from app.models.document import Document, DocumentStatus, DocumentVersion
from app.models.pdf_export import PdfExport, PdfExportStatus
from app.models.user import User, UserRole
from app.schemas.document import DashboardStats, DocumentCreate
from app.services.document_generator import generate_document_content
from app.services.openai_client import OpenAIGenerationError
from app.services.template_service import ensure_template_reference


GenerationProgressCallback = Callable[[str, str, int], None]


def _emit_progress(callback: GenerationProgressCallback | None, stage: str, message: str, progress: int) -> None:
    if callback:
        callback(stage, message, progress)


def _document_query_for_user(db: Session, user: User):
    stmt = select(Document).options(selectinload(Document.versions))
    if user.role != UserRole.SUPER_ADMIN.value:
        stmt = stmt.where(Document.tenant_id == user.tenant_id)
    return stmt


def list_documents(db: Session, user: User) -> list[Document]:
    return list(db.scalars(_document_query_for_user(db, user).order_by(Document.updated_at.desc())).unique())


def get_document(db: Session, document_id: str, user: User) -> Document:
    stmt = _document_query_for_user(db, user).where(Document.id == document_id)
    document = db.scalar(stmt)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


def create_generated_document(db: Session, payload: DocumentCreate, user: User, progress_callback: GenerationProgressCallback | None = None) -> Document:
    start_time = datetime.now(timezone.utc)
    _emit_progress(progress_callback, "validating_template", "Validating the selected template and workspace access.", 12)
    if not ensure_template_reference(db, payload.template_id, user.tenant_id):
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Selected template is not available")

    try:
        _emit_progress(progress_callback, "generating_content", "Generating original document content with OpenAI.", 18)
        generated_content, usage = generate_document_content(payload, progress_callback=progress_callback)
    except OpenAIGenerationError as exc:
        db.rollback()
        detail = str(exc)
        if exc.issue_codes and "Issue codes:" not in detail:
            detail = f"{detail} Issue codes: {', '.join(exc.issue_codes)}"
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail) from exc

    _emit_progress(progress_callback, "extracting_content", "Extracting and validating structured content for preview.", 82)
    polished_title = str(generated_content.get("title_page") or payload.title)
    generation_time_seconds = int((datetime.now(timezone.utc) - start_time).total_seconds())
    document = Document(
        tenant_id=user.tenant_id,
        owner_id=user.id,
        title=polished_title,
        subject=payload.subject,
        education_level=payload.education_level,
        document_type=payload.document_type,
        target_platform=payload.target_platform,
        output_language=payload.output_language,
        length=payload.length,
        template_id=payload.template_id,
        status=DocumentStatus.GENERATING.value,
        generation_time_seconds=generation_time_seconds,
    )
    _emit_progress(progress_callback, "saving_document", "Saving the document, preview version, and usage log.", 90)
    db.add(document)
    db.flush()

    version = DocumentVersion(
        document_id=document.id,
        tenant_id=user.tenant_id,
        version_number=1,
        content=generated_content,
        created_by_id=user.id,
        created_at=datetime.now(timezone.utc),
    )
    document.status = DocumentStatus.READY_FOR_REVIEW.value
    db.add(version)
    credits_used = int(usage.get("total_tokens") or 0)
    db.add(
        AIUsageLog(
            tenant_id=user.tenant_id,
            user_id=user.id,
            document_id=document.id,
            provider="openai",
            credits_used=credits_used,
            event_metadata={"workflow": "initial_generation", "usage": usage},
        )
    )
    db.add(AuditLog(tenant_id=user.tenant_id, user_id=user.id, action="document.generated", resource_type="document", resource_id=document.id, event_metadata={"provider": "openai"}))
    db.commit()
    _emit_progress(progress_callback, "preview_ready", "Generation complete. Preview is ready.", 100)
    return get_document(db, document.id, user)


def delete_document(db: Session, document_id: str, user: User) -> None:
    document = get_document(db, document_id, user)
    db.delete(document)
    db.add(AuditLog(tenant_id=document.tenant_id, user_id=user.id, action="document.deleted", resource_type="document", resource_id=document.id, event_metadata={}))
    db.commit()


def dashboard_stats(db: Session, user: User) -> DashboardStats:
    base = select(Document)
    if user.role != UserRole.SUPER_ADMIN.value:
        base = base.where(Document.tenant_id == user.tenant_id)

    documents = list(db.scalars(base))
    tenant_filter = [] if user.role == UserRole.SUPER_ADMIN.value else [AIUsageLog.tenant_id == user.tenant_id]
    credits = db.scalar(select(func.coalesce(func.sum(AIUsageLog.credits_used), 0)).where(*tenant_filter))
    exported = db.scalar(
        select(func.count(PdfExport.id)).join(Document).where(
            PdfExport.status == PdfExportStatus.COMPLETED.value,
            *( [] if user.role == UserRole.SUPER_ADMIN.value else [Document.tenant_id == user.tenant_id] ),
        )
    )
    return DashboardStats(
        total_documents=len(documents),
        drafts=sum(1 for document in documents if document.status == DocumentStatus.DRAFT.value),
        pdfs_exported=exported or 0,
        marketplace_ready=sum(1 for document in documents if document.status == DocumentStatus.MARKETPLACE_READY.value),
        ai_credits_used=credits or 0,
    )


def latest_version(document: Document) -> DocumentVersion | None:
    if not document.versions:
        return None
    return sorted(document.versions, key=lambda version: version.version_number)[-1]
