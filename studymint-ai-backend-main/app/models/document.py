import enum
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import IdMixin, TimestampMixin


class DocumentStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    GENERATING = "GENERATING"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    PDF_READY = "PDF_READY"
    MARKETPLACE_READY = "MARKETPLACE_READY"
    ARCHIVED = "ARCHIVED"


class Document(IdMixin, TimestampMixin, Base):
    __tablename__ = "documents"

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True, nullable=False)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    template_id: Mapped[str | None] = mapped_column(ForeignKey("templates.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    education_level: Mapped[str] = mapped_column(String(120), nullable=False)
    document_type: Mapped[str] = mapped_column(String(80), nullable=False)
    target_platform: Mapped[str] = mapped_column(String(80), nullable=False)
    output_language: Mapped[str] = mapped_column(String(80), nullable=False)
    length: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(60), nullable=False, default=DocumentStatus.DRAFT.value)
    generation_time_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    tenant = relationship("Tenant", back_populates="documents")
    owner = relationship("User", back_populates="documents")
    versions = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan", order_by="DocumentVersion.version_number")
    pdf_exports = relationship("PdfExport", back_populates="document", cascade="all, delete-orphan")


class DocumentVersion(IdMixin, Base):
    __tablename__ = "document_versions"

    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True, nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    document = relationship("Document", back_populates="versions")
