from datetime import datetime
from typing import Literal

from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.core.config import settings
from app.schemas.document import DifficultyMode, DocumentType, GenerationMode, LengthOption


StuviaAgentStatus = Literal["QUEUED", "RUNNING", "COMPLETED", "FAILED"]
StuviaAgentPublishMode = Literal["drafts_only", "n8n_review", "n8n_auto_publish", "manual_publish"]


class StuviaAgentRunCreate(BaseModel):
    profile_url: str = Field(default=settings.STUVIA_AGENT_DEFAULT_PROFILE_URL, min_length=12, max_length=500)
    manual_topics: list[str] = Field(default_factory=list, max_length=20)
    max_topics: int = Field(default=3, ge=1, le=10)
    question_count: int = Field(default=25, ge=1, le=300)
    concurrency: int = Field(default=3, ge=1, le=10)
    education_level: str = Field(default="Nursing School", min_length=2, max_length=120)
    document_type: DocumentType = "Question Bank"
    output_language: str = Field(default="English", min_length=2, max_length=80)
    length: LengthOption = "Medium"
    template_id: str | None = None
    generation_mode: GenerationMode = "GENERAL_KNOWLEDGE_DRAFT"
    user_instructions: str = Field(default="", max_length=4000)
    source_notes: str = Field(default="", max_length=20000)
    difficulty: DifficultyMode = "Mixed"
    publish_mode: StuviaAgentPublishMode = "drafts_only"
    reset_topic_history: bool = False

    @field_validator("manual_topics")
    @classmethod
    def clean_manual_topics(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()

        for item in value:
            topic = " ".join(str(item or "").split()).strip()
            if not topic:
                continue
            key = topic.lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(topic[:180])

        return cleaned


class StuviaAgentTopic(BaseModel):
    title: str
    topic: str
    source_url: str
    score: float = 0
    reason: str = ""


class StuviaAgentListing(BaseModel):
    title: str
    topic: str
    document_id: str | None = None
    document_url: str | None = None
    status: str
    error: str | None = None
    attempts: int = 1
    publish_status: str | None = None
    stuvia_url: str | None = None


class StuviaAgentRunRead(BaseModel):
    run_id: str
    status: StuviaAgentStatus
    stage: str
    stage_label: str
    message: str
    progress: int
    profile_url: str
    publish_mode: StuviaAgentPublishMode
    topics: list[StuviaAgentTopic]
    listings: list[StuviaAgentListing]
    n8n_status: str | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class StuviaManualPublishRead(BaseModel):
    document_id: str
    status: str
    message: str
    n8n_status: str


class StuviaPublisherHandoffRead(BaseModel):
    ok: bool
    status: str
    run_id: str | None = None
    received_listings: int
    updated_documents: int
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class StuviaPublisherDocumentPackageRead(BaseModel):
    document_id: str
    tenant_id: str
    title: str
    subject: str
    education_level: str
    document_type: str
    output_language: str
    length: str
    template_id: str | None = None
    pdf_url: str
    document_url: str
    introduction: str = ""
    section_titles: list[str] = Field(default_factory=list)
    key_points: list[str] = Field(default_factory=list)
    question_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
