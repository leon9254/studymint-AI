from typing import Any

from app.schemas.document import DocumentCreate
from app.services.openai_client import ProgressCallback, generate_document_with_openai


def generate_document_content(
    payload: DocumentCreate,
    progress_callback: ProgressCallback | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    return generate_document_with_openai(payload, progress_callback=progress_callback)
