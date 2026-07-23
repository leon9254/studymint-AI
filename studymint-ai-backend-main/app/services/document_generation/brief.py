from __future__ import annotations

import re

from app.schemas.document import DocumentCreate
from app.schemas.question_bank import GenerationBrief
from app.services.template_ids import is_question_bank_template


COMMERCIAL_TITLE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:19|20)\d{2}(?:[/\-](?:(?:19|20)?\d{2}))?\b", re.I),
    re.compile(r"\b(?:newest|latest|updated|actual\s+exam|complete|test\s+bank|exam\s+bank)\b", re.I),
    re.compile(r"\b\d+\s+(?:questions?|q(?:uestion)?s?)\b", re.I),
    re.compile(r"\b(?:with\s+)?(?:detailed\s+)?(?:correct\s+)?verified\s+answers?\b", re.I),
    re.compile(r"\b100\s*%\s*(?:correct\s+answers?|correct|guaranteed|pass)\b", re.I),
    re.compile(r"\b(?:guaranteed\s+pass|grade\s+assured|official|certified|endorsed|approved)\b", re.I),
    re.compile(r"\b(?:practice\s+questions?|answers?|rationales?)\b", re.I),
)

COURSE_CODE_PATTERN = re.compile(r"^\s*[A-Z]{2,6}\s*\d{2,5}\b[\s:,-]*", re.I)
FINAL_EXAM_PATTERN = re.compile(r"\b(?:final|midterm|exit|certification|assessment|exam|test|quiz)\b", re.I)

HIGH_RISK_TERMS = {
    "medical",
    "medicine",
    "nursing",
    "clinical",
    "patient",
    "health",
    "healthcare",
    "law",
    "legal",
    "finance",
    "financial",
    "accounting",
}


def is_question_bank_request(payload: DocumentCreate) -> bool:
    if is_question_bank_template(payload.template_id):
        return True

    return payload.document_type in {"Exam Prep", "Question Bank", "Q&A Guide"}


def clean_display_title(title: str) -> str:
    cleaned = " ".join(str(title).split()).strip()
    return cleaned or "Untitled Document"


def concise_topic_label(title: str, subject: str) -> str:
    candidate = clean_display_title(title)
    candidate = COURSE_CODE_PATTERN.sub("", candidate)

    for pattern in COMMERCIAL_TITLE_PATTERNS:
        candidate = pattern.sub(" ", candidate)

    candidate = FINAL_EXAM_PATTERN.sub(" ", candidate)
    candidate = re.sub(r"\([^)]*\)", " ", candidate)
    candidate = re.sub(r"[^A-Za-z0-9&/+\-\s]", " ", candidate)
    candidate = re.sub(r"\s+", " ", candidate).strip(" -:/")

    subject_clean = " ".join(str(subject).split()).strip()

    if subject_clean:
        subject_words = {word.lower() for word in re.findall(r"[A-Za-z][A-Za-z0-9]+", subject_clean)}
        candidate_words = {word.lower() for word in re.findall(r"[A-Za-z][A-Za-z0-9]+", candidate)}

        if subject_words and (not candidate_words or len(subject_words.intersection(candidate_words)) >= min(2, len(subject_words))):
            return subject_clean

    if not candidate or len(candidate.split()) > 7:
        return subject_clean or candidate or "General Study"

    return candidate


def factual_risk_level(payload: DocumentCreate, topic_label: str) -> str:
    combined = f"{payload.title} {payload.subject} {topic_label}".lower()

    if any(term in combined for term in HIGH_RISK_TERMS):
        return "high"

    return "medium"


def requested_question_count(payload: DocumentCreate) -> int:
    if payload.question_count:
        return payload.question_count

    match = re.search(r"\b(\d{1,3})\s+(?:questions?|q(?:uestion)?s?)\b", payload.title, re.I)

    if match:
        return max(1, min(int(match.group(1)), 300))

    return 25


def build_generation_brief(payload: DocumentCreate) -> GenerationBrief:
    display_title = clean_display_title(payload.title)
    topic_label = concise_topic_label(display_title, payload.subject)
    mode = payload.generation_mode
    review_required = mode == "GENERAL_KNOWLEDGE_DRAFT" or factual_risk_level(payload, topic_label) == "high"

    return GenerationBrief(
        display_title=display_title,
        topic_label=topic_label,
        subject=payload.subject,
        education_level=payload.education_level,
        document_type=payload.document_type,
        language=payload.output_language,
        requested_question_count=requested_question_count(payload),
        generation_mode=mode,
        user_instructions=payload.user_instructions.strip(),
        supplied_source_text=payload.source_notes.strip(),
        factual_risk_level=factual_risk_level(payload, topic_label),
        target_learner=payload.education_level,
        preferred_difficulty_distribution=payload.difficulty,
        review_required=review_required,
    )
