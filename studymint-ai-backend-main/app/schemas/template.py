from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import TimestampedSchema


class TemplateBase(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    description: str
    page_size: str = "A4"
    font_settings: dict[str, Any] = Field(default_factory=dict)
    cover_style: str
    section_style: str
    footer_settings: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class TemplateCreate(TemplateBase):
    tenant_id: str | None = None


class TemplateRead(TemplateBase, TimestampedSchema):
    id: str
    tenant_id: str | None = None
