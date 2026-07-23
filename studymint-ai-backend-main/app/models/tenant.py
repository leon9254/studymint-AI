from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import IdMixin, TimestampMixin


class Tenant(IdMixin, TimestampMixin, Base):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    plan: Mapped[str] = mapped_column(String(80), nullable=False, default="starter")

    users = relationship("User", back_populates="tenant")
    documents = relationship("Document", back_populates="tenant")
