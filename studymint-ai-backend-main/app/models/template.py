from sqlalchemy import Boolean, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import IdMixin, TimestampMixin


class Template(IdMixin, TimestampMixin, Base):
    __tablename__ = "templates"

    tenant_id: Mapped[str | None] = mapped_column(ForeignKey("tenants.id"), index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    page_size: Mapped[str] = mapped_column(String(40), nullable=False, default="A4")
    font_settings: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    cover_style: Mapped[str] = mapped_column(Text, nullable=False)
    section_style: Mapped[str] = mapped_column(Text, nullable=False)
    footer_settings: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
