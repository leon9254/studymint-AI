import enum
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import IdMixin


class PdfExportStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PdfExport(IdMixin, Base):
    __tablename__ = "pdf_exports"

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True, nullable=False)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default=PdfExportStatus.PENDING.value)
    pdf_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    renderer: Mapped[str] = mapped_column(String(80), nullable=False, default="placeholder")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="pdf_exports")
