from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.pdf_export import PdfExportRead
from app.services.document_service import get_document
from app.services.pdf_renderer import render_pdf_export

router = APIRouter()


@router.post("/documents/{document_id}", response_model=PdfExportRead)
def create_pdf_export(document_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    document = get_document(db, document_id, current_user)
    return render_pdf_export(db, document, current_user)
