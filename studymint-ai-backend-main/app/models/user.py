import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import IdMixin, TimestampMixin


class UserRole(str, enum.Enum):
    USER = "USER"
    TENANT_ADMIN = "TENANT_ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"


class User(IdMixin, TimestampMixin, Base):
    __tablename__ = "users"

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(40), nullable=False, default=UserRole.USER.value)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    email_verification_token_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    email_verification_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_reset_token_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    password_reset_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant = relationship("Tenant", back_populates="users")
    documents = relationship("Document", back_populates="owner")
