from sqlalchemy import ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import IdMixin, TimestampMixin


class AIUsageLog(IdMixin, TimestampMixin, Base):
    __tablename__ = "ai_usage_logs"

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    provider: Mapped[str] = mapped_column(String(80), nullable=False, default="mock")
    credits_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    event_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)


class AuditLog(IdMixin, TimestampMixin, Base):
    __tablename__ = "audit_logs"

    tenant_id: Mapped[str | None] = mapped_column(ForeignKey("tenants.id"), index=True, nullable=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    event_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
