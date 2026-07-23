from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import IdMixin, TimestampMixin


class IntegrationConfig(IdMixin, TimestampMixin, Base):
    __tablename__ = "integration_configs"

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="COMING_SOON")
    settings: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
