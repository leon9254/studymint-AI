from datetime import datetime

from app.models.pdf_export import PdfExportStatus
from app.schemas.common import ORMModel


class PdfExportRead(ORMModel):
    id: str
    tenant_id: str
    document_id: str
    status: PdfExportStatus
    pdf_url: str | None
    renderer: str
    created_at: datetime
