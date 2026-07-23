from app.schemas.common import TimestampedSchema


class TenantRead(TimestampedSchema):
    id: str
    name: str
    slug: str
    plan: str
