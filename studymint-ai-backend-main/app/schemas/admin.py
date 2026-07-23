from pydantic import BaseModel

from app.schemas.user import UserRead


class AdminOverview(BaseModel):
    users: int
    active_users: int
    unverified_users: int
    admin_users: int
    super_admins: int
    tenants: int
    generated_documents: int
    ai_usage_events: int
    audit_events: int
    recent_users: list[UserRead]
