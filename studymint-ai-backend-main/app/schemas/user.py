from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole
from app.schemas.common import ORMModel


class UserRead(ORMModel):
    id: str
    tenant_id: str
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    email_verified: bool
    created_at: datetime


class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.USER
