from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.document import DocumentStatus
from app.schemas.common import ORMModel, TimestampedSchema
from app.schemas.question_bank import DifficultyMode, GenerationMode, QuestionItem

DocumentType = Literal["Study Notes", "Summary", "Exam Prep", "Question Bank", "Q&A Guide", "Study Guide", "Flashcard Pack"]
TargetPlatform = Literal["Stuvia", "Docsity/DocCity", "Other"]
LengthOption = Literal["Short", "Medium", "Long"]
GenerationJobStatus = Literal["QUEUED", "RUNNING", "COMPLETED", "FAILED"]


class DocumentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    subject: str = Field(min_length=2, max_length=255)
    education_level: str = Field(min_length=2, max_length=120)
    document_type: DocumentType
    target_platform: TargetPlatform
    output_language: str = Field(min_length=2, max_length=80)
    length: LengthOption
    template_id: str | None = None
    question_count: int | None = Field(default=None, ge=1, le=300)
    generation_mode: GenerationMode = "GENERAL_KNOWLEDGE_DRAFT"
    user_instructions: str = Field(default="", max_length=4000)
    source_notes: str = Field(default="", max_length=20000)
    difficulty: DifficultyMode = "Mixed"
    speed_mode: bool = False


class DocumentContent(BaseModel):
    title_page: str = Field(min_length=1, max_length=255)
    introduction: str
    sections: list[dict[str, str]]
    key_points: list[str]
    examples: list[str]
    study_questions: list[str]
    conclusion: str
    metadata: dict = Field(default_factory=dict)
    question_bank: list[QuestionItem] = Field(default_factory=list)


class DocumentVersionRead(ORMModel):
    id: str
    version_number: int
    content: DocumentContent
    created_at: datetime


class DocumentRead(TimestampedSchema):
    id: str
    tenant_id: str
    owner_id: str
    template_id: str | None = None
    title: str
    subject: str
    education_level: str
    document_type: str
    target_platform: str
    output_language: str
    length: str
    status: DocumentStatus
    latest_version: DocumentVersionRead | None = None
    generation_time_seconds: int | None = None


class DashboardStats(BaseModel):
    total_documents: int
    drafts: int
    pdfs_exported: int
    marketplace_ready: int
    ai_credits_used: int


class GenerationJobRead(BaseModel):
    job_id: str
    status: GenerationJobStatus
    stage: str
    stage_label: str
    message: str
    progress: int
    document_id: str | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime
