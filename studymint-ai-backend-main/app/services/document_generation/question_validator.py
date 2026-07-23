from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from app.schemas.question_bank import GenerationBrief, QuestionItem
from app.services.document_generation.deduplication import (
    likely_duplicate,
    normalize_text,
    opening_pattern,
)
from app.services.template_ids import QUESTION_BANK_TEMPLATE_IDS


class QuestionValidationError(ValueError):
    def __init__(self, message: str, *, issue_codes: list[str] | None = None) -> None:
        super().__init__(message)
        self.issue_codes = issue_codes or []


@dataclass
class QuestionValidationReport:
    accepted: list[QuestionItem] = field(default_factory=list)
    rejected: list[dict] = field(default_factory=list)
    duplicate_questions_rejected: int = 0
    issue_codes: list[str] = field(default_factory=list)


MARKETPLACE_TERMS = {
    "stuvia",
    "docsity",
    "doccity",
    "marketplace",
    "seller",
    "buyer",
    "listing",
}

META_LANGUAGE_TERMS = {
    "the prompt",
    "the user",
    "the model",
    "generated document",
    "publishing",
    "before publishing",
    "export",
    "template",
    "quality review",
    "source verification",
    "unsupported claims",
    "user-provided title",
    "add verified sources",
}

UNSUPPORTED_AUTHORITY_TERMS = {
    "official",
    "verified",
    "actual exam",
    "guaranteed",
    "100% correct",
    "endorsed",
    "approved",
    "certified",
    "accredited",
}

GENERIC_FILLER_PHRASES = {
    "define the objective inputs constraints",
    "map the decision path",
    "export packaging",
    "template style",
}

FABRICATED_SOURCE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bdoi:\s*\S+", re.I),
    re.compile(r"\bhttps?://\S+", re.I),
    re.compile(r"\bwww\.\S+", re.I),
    re.compile(r"\bISBN(?:-1[03])?:?\s*(?:97[89][-\s]?)?[0-9][0-9\-\s]{8,}[0-9X]\b", re.I),
    re.compile(r"\b(?:page|pages|chapter|figure|table)\s+\d+\b", re.I),
    re.compile(r"\([A-Z][A-Za-z]+(?:\s+et\s+al\.)?,\s*\d{4}\)", re.I),
)


def _combined_question_text(question: QuestionItem) -> str:
    return " ".join(
        [
            question.category,
            question.learning_objective,
            question.stem,
            " ".join(option.text for option in question.options),
            question.rationale,
        ]
    )


def _full_title_occurs(question: QuestionItem, brief: GenerationBrief) -> bool:
    title_key = normalize_text(brief.display_title, remove_stopwords=True)

    if not title_key or len(title_key.split()) < 5:
        return False

    return title_key in normalize_text(_combined_question_text(question), remove_stopwords=True)


def _contains_any(text: str, terms: set[str]) -> str | None:
    lowered = text.lower()

    for term in sorted(terms):
        if term in lowered:
            return term

    return None


def validate_question_shape(question: QuestionItem, brief: GenerationBrief) -> list[str]:
    issues: list[str] = []
    labels = [option.label for option in question.options]

    if labels != ["A", "B", "C", "D"]:
        issues.append("INVALID_OPTION_LABELS")

    option_texts = [normalize_text(option.text, remove_stopwords=True) for option in question.options]

    if len(set(option_texts)) != 4:
        issues.append("DUPLICATE_OPTIONS")

    if question.correct_option not in labels:
        issues.append("INVALID_CORRECT_LABEL")

    stem_words = len(re.findall(r"\b[\w'-]+\b", question.stem))
    rationale_words = len(re.findall(r"\b[\w'-]+\b", question.rationale))

    if stem_words < 6 or stem_words > 100:
        issues.append("STEM_LENGTH_OUT_OF_RANGE")

    if rationale_words < 12 or rationale_words > 180:
        issues.append("RATIONALE_LENGTH_OUT_OF_RANGE")

    selected = next((option.text for option in question.options if option.label == question.correct_option), "")

    if normalize_text(question.rationale, remove_stopwords=True) in {
        normalize_text(question.correct_option, remove_stopwords=True),
        normalize_text(selected, remove_stopwords=True),
    }:
        issues.append("WEAK_RATIONALE")

    if normalize_text(selected, remove_stopwords=True) and normalize_text(selected, remove_stopwords=True) == normalize_text(question.rationale, remove_stopwords=True):
        issues.append("RATIONALE_COPIES_ANSWER")

    return issues


def validate_question_content(question: QuestionItem, brief: GenerationBrief) -> list[str]:
    issues: list[str] = []
    combined = _combined_question_text(question)

    if _full_title_occurs(question, brief):
        issues.append("FULL_DISPLAY_TITLE_IN_QUESTION")

    forbidden = _contains_any(combined, MARKETPLACE_TERMS)

    if forbidden:
        issues.append("MARKETPLACE_LANGUAGE")

    forbidden = _contains_any(combined, META_LANGUAGE_TERMS)

    if forbidden:
        issues.append("META_LANGUAGE")

    forbidden = _contains_any(combined, UNSUPPORTED_AUTHORITY_TERMS)

    if forbidden:
        issues.append("UNSUPPORTED_AUTHORITY_CLAIM")

    for template_id in QUESTION_BANK_TEMPLATE_IDS:
        if template_id and template_id.lower() in combined.lower():
            issues.append("TEMPLATE_METADATA")

    normalized = normalize_text(combined, remove_stopwords=True)

    for phrase in GENERIC_FILLER_PHRASES:
        if phrase in normalized:
            issues.append("GENERIC_FILLER")

    for pattern in FABRICATED_SOURCE_PATTERNS:
        if pattern.search(combined):
            issues.append("FABRICATED_SOURCE_PATTERN")

    if "?" in combined and re.search(r"\b(can|don|won|isn|aren|client|patient)\?t\b", combined, re.I):
        issues.append("MALFORMED_APOSTROPHE")

    if brief.generation_mode == "SOURCE_GROUNDED" and not question.source_refs:
        issues.append("MISSING_SOURCE_REFERENCE")

    return issues


def validate_question_bank(questions: list[QuestionItem], brief: GenerationBrief) -> QuestionValidationReport:
    report = QuestionValidationReport()
    seen_stems: list[QuestionItem] = []
    seen_option_sets: set[str] = set()
    opening_patterns: Counter[str] = Counter()
    answer_labels: Counter[str] = Counter()

    for expected_number, question in enumerate(questions, start=1):
        issues: list[str] = []

        if question.number != expected_number:
            issues.append("NON_SEQUENTIAL_NUMBERING")

        issues.extend(validate_question_shape(question, brief))
        issues.extend(validate_question_content(question, brief))

        stem_key = normalize_text(question.stem, remove_stopwords=True)

        for accepted in seen_stems:
            if likely_duplicate(question.stem, accepted.stem):
                issues.append("DUPLICATE_OR_NEAR_DUPLICATE_STEM")
                break

        option_set_key = "|".join(sorted(normalize_text(option.text, remove_stopwords=True) for option in question.options))

        if option_set_key in seen_option_sets:
            issues.append("DUPLICATE_OPTION_SET")

        opening = opening_pattern(question.stem)
        opening_patterns[opening] += 1

        if opening and opening_patterns[opening] > max(8, len(questions) // 8):
            issues.append("REPEATED_OPENING_PATTERN")

        if issues:
            if any(issue.startswith("DUPLICATE") for issue in issues):
                report.duplicate_questions_rejected += 1
            report.rejected.append({"question_number": question.number, "issue_codes": sorted(set(issues))})
            report.issue_codes.extend(issues)
            continue

        seen_stems.append(question)
        seen_option_sets.add(option_set_key)
        answer_labels[question.correct_option] += 1
        report.accepted.append(question)

    if len(report.accepted) != brief.requested_question_count:
        report.issue_codes.append("QUESTION_COUNT_MISMATCH")

    if answer_labels:
        most_common = answer_labels.most_common(1)[0][1]
        if most_common > max(brief.requested_question_count * 0.45, 4):
            report.issue_codes.append("ANSWER_LABEL_IMBALANCE")

    report.issue_codes = sorted(set(report.issue_codes))
    return report


def raise_for_invalid_question_bank(questions: list[QuestionItem], brief: GenerationBrief) -> QuestionValidationReport:
    report = validate_question_bank(questions, brief)

    if report.rejected or len(report.accepted) != brief.requested_question_count:
        raise QuestionValidationError(
            "Question bank failed deterministic validation",
            issue_codes=report.issue_codes,
        )

    return report
