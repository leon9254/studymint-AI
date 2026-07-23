from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from typing import Any, Callable

from pydantic import ValidationError

from app.core.config import settings
from app.schemas.document import DocumentContent, DocumentCreate
from app.schemas.question_bank import BlueprintCategory, ContentBlueprint, GenerationBrief, QualitySummary, QuestionItem, QuestionOption
from app.services.document_generation.blueprint import categories_for_question_range, normalize_blueprint_counts
from app.services.document_generation.brief import build_generation_brief, is_question_bank_request
from app.services.document_generation.deduplication import likely_duplicate, normalize_text, opening_pattern
from app.services.document_generation.question_validator import (
    QuestionValidationError,
    raise_for_invalid_question_bank,
    validate_question_content,
    validate_question_shape,
    validate_question_bank,
)


ProgressCallback = Callable[[str, str, int], None]


OPENAI_API_KEY_MISSING_MESSAGE = (
    "OPENAI_API_KEY is not configured. In Docker dev, set OPENAI_API_KEY in the workspace root .env "
    "and restart the backend container. For manual backend runs, set it in backend/.env."
)

RETRYABLE_OPENAI_HTTP_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504}


class OpenAIGenerationError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = False, issue_codes: list[str] | None = None) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.issue_codes = issue_codes or []


DOCUMENT_CONTENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title_page": {"type": "string", "minLength": 1, "maxLength": 255},
        "introduction": {"type": "string", "minLength": 1},
        "sections": {
            "type": "array",
            "minItems": 4,
            "maxItems": 16,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "title": {"type": "string", "minLength": 1},
                    "body": {"type": "string", "minLength": 1},
                },
                "required": ["id", "title", "body"],
            },
        },
        "key_points": {"type": "array", "items": {"type": "string", "minLength": 1}, "minItems": 0, "maxItems": 18},
        "examples": {"type": "array", "items": {"type": "string", "minLength": 1}, "minItems": 0, "maxItems": 10},
        "study_questions": {"type": "array", "items": {"type": "string", "minLength": 1}, "minItems": 0, "maxItems": 16},
        "conclusion": {"type": "string", "minLength": 1},
    },
    "required": ["title_page", "introduction", "sections", "key_points", "examples", "study_questions", "conclusion"],
}


BLUEPRINT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "topic_label": {"type": "string", "minLength": 1, "maxLength": 120},
        "categories": {
            "type": "array",
            "minItems": 8,
            "maxItems": 16,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string", "minLength": 1, "maxLength": 160},
                    "learning_objectives": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 5,
                        "items": {"type": "string", "minLength": 1, "maxLength": 300},
                    },
                    "planned_question_count": {"type": "integer", "minimum": 0, "maximum": 300},
                    "difficulty_distribution": {"type": "object", "additionalProperties": {"type": "integer"}},
                    "question_style_distribution": {"type": "object", "additionalProperties": {"type": "integer"}},
                    "scenario_distribution": {"type": "object", "additionalProperties": {"type": "integer"}},
                },
                "required": [
                    "name",
                    "learning_objectives",
                    "planned_question_count",
                    "difficulty_distribution",
                    "question_style_distribution",
                    "scenario_distribution",
                ],
            },
        },
        "concepts_that_must_not_be_repeated": {"type": "array", "items": {"type": "string"}, "maxItems": 40},
        "prohibited_meta_language": {"type": "array", "items": {"type": "string"}, "maxItems": 40},
    },
    "required": ["topic_label", "categories", "concepts_that_must_not_be_repeated", "prohibited_meta_language"],
}


QUESTION_BATCH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "questions": {
            "type": "array",
            "minItems": 1,
            "maxItems": 25,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "number": {"type": "integer", "minimum": 1, "maximum": 300},
                    "category": {"type": "string", "minLength": 1, "maxLength": 160},
                    "learning_objective": {"type": "string", "minLength": 1, "maxLength": 300},
                    "difficulty": {"type": "string", "enum": ["foundational", "intermediate", "advanced"]},
                    "question_type": {
                        "type": "string",
                        "enum": ["conceptual", "application", "clinical_scenario", "case_scenario", "calculation", "definition"],
                    },
                    "stem": {"type": "string", "minLength": 1, "maxLength": 1200},
                    "options": {
                        "type": "array",
                        "minItems": 4,
                        "maxItems": 4,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "label": {"type": "string", "enum": ["A", "B", "C", "D"]},
                                "text": {"type": "string", "minLength": 1, "maxLength": 500},
                            },
                            "required": ["label", "text"],
                        },
                    },
                    "correct_option": {"type": "string", "enum": ["A", "B", "C", "D"]},
                    "rationale": {"type": "string", "minLength": 1, "maxLength": 1600},
                    "source_refs": {"type": "array", "items": {"type": "string"}, "maxItems": 10},
                    "review_flags": {"type": "array", "items": {"type": "string"}, "maxItems": 10},
                },
                "required": [
                    "number",
                    "category",
                    "learning_objective",
                    "difficulty",
                    "question_type",
                    "stem",
                    "options",
                    "correct_option",
                    "rationale",
                    "source_refs",
                    "review_flags",
                ],
            },
        }
    },
    "required": ["questions"],
}


def _question_batch_schema(max_items: int) -> dict[str, Any]:
    schema = json.loads(json.dumps(QUESTION_BATCH_SCHEMA))
    schema["properties"]["questions"]["maxItems"] = max(1, min(int(max_items), 300))
    return schema


PROHIBITED_LEARNER_PHRASES = {
    "define the objective, inputs, constraints",
    "map the decision path",
    "add verified sources before publishing",
    "export packaging",
    "unsupported claims",
    "quality review",
    "template style",
    "the user-provided title",
    "before publishing",
}


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _emit(progress_callback: ProgressCallback | None, stage: str, message: str, progress: int) -> None:
    if progress_callback:
        progress_callback(stage, message, progress)


def _openai_reasoning_options() -> dict[str, str]:
    effort = _clean_text(settings.OPENAI_REASONING_EFFORT).lower() or "high"
    if effort not in {"minimal", "low", "medium", "high"}:
        effort = "high"
    return {"effort": effort}


def _openai_text_verbosity() -> str:
    verbosity = _clean_text(settings.OPENAI_TEXT_VERBOSITY).lower() or "medium"
    if verbosity not in {"low", "medium", "high"}:
        verbosity = "medium"
    return verbosity


def _normalize_openai_schema(schema: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(schema, dict):
        return schema

    normalized: dict[str, Any] = dict(schema)

    if normalized.get("type") == "object":
        properties = normalized.get("properties")
        if isinstance(properties, dict):
            required = normalized.get("required")
            if not isinstance(required, list):
                required = list(properties.keys())
            else:
                required = [key for key in required if key in properties]
                for key in properties:
                    if key not in required:
                        required.append(key)
            normalized["required"] = required
        else:
            normalized["required"] = []

    if isinstance(normalized.get("properties"), dict):
        normalized["properties"] = {
            key: _normalize_openai_schema(value) if isinstance(value, dict) else value
            for key, value in normalized["properties"].items()
        }

    if isinstance(normalized.get("items"), dict):
        normalized["items"] = _normalize_openai_schema(normalized["items"])

    if isinstance(normalized.get("additionalProperties"), dict):
        normalized["additionalProperties"] = _normalize_openai_schema(normalized["additionalProperties"])

    return normalized


def _post_response(payload: dict[str, Any]) -> dict[str, Any]:
    if not settings.OPENAI_API_KEY.strip():
        raise OpenAIGenerationError(OPENAI_API_KEY_MISSING_MESSAGE)

    url = f"{settings.OPENAI_API_BASE_URL.rstrip('/')}/responses"
    body = json.dumps(payload).encode("utf-8")
    headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}", "Content-Type": "application/json"}

    last_error: Exception | None = None
    last_error_message = ""
    max_attempts = max(1, settings.OPENAI_MAX_RETRIES)
    for attempt in range(max_attempts):
        request = urllib.request.Request(url, data=body, method="POST", headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=settings.OPENAI_TIMEOUT_SECONDS) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", "replace")[:1600]
            last_error = exc
            last_error_message = f"OpenAI API returned {exc.code}: {error_body}"
            if exc.code not in RETRYABLE_OPENAI_HTTP_STATUS_CODES:
                raise OpenAIGenerationError(last_error_message) from exc
        except urllib.error.URLError as exc:
            last_error = exc
            last_error_message = f"OpenAI API request failed: {exc.reason}"
        except TimeoutError as exc:
            last_error = exc
            last_error_message = "OpenAI API request timed out"

        if attempt < max_attempts - 1:
            time.sleep(settings.OPENAI_RETRY_BACKOFF_SECONDS * (attempt + 1))

    if last_error_message:
        raise OpenAIGenerationError(last_error_message, retryable=True) from last_error
    if isinstance(last_error, TimeoutError):
        raise OpenAIGenerationError("OpenAI API request timed out", retryable=True) from last_error
    if isinstance(last_error, urllib.error.URLError):
        raise OpenAIGenerationError(f"OpenAI API request failed: {last_error.reason}", retryable=True) from last_error
    raise OpenAIGenerationError("OpenAI API request failed after retries", retryable=True)


def _extract_output_text(response_payload: dict[str, Any]) -> str:
    if isinstance(response_payload.get("output_text"), str):
        return response_payload["output_text"]

    if isinstance(response_payload.get("output_parsed"), dict):
        return json.dumps(response_payload["output_parsed"], ensure_ascii=False)

    parts: list[str] = []

    for item in response_payload.get("output", []):
        if item.get("type") != "message":
            continue

        for content in item.get("content", []):
            if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                parts.append(content["text"])
            elif isinstance(content.get("parsed"), dict):
                parts.append(json.dumps(content["parsed"], ensure_ascii=False))

    return "\n".join(parts).strip()


def _raise_for_response_status(response_payload: dict[str, Any]) -> None:
    if isinstance(response_payload.get("error"), dict):
        message = response_payload["error"].get("message") or json.dumps(response_payload["error"])
        raise OpenAIGenerationError(f"OpenAI API returned an error: {message}")

    status = response_payload.get("status")

    if status in {None, "completed"}:
        return

    details = response_payload.get("incomplete_details") or {}
    reason = details.get("reason") if isinstance(details, dict) else None
    raise OpenAIGenerationError(f"OpenAI response ended with status {status}: {reason or 'unknown'}", retryable=True)


def _decode_json_object(output_text: str) -> dict[str, Any]:
    text = output_text.strip()

    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    decoder = json.JSONDecoder()

    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    raise OpenAIGenerationError("OpenAI response was not valid JSON", retryable=True)


def _json_from_response(response_payload: dict[str, Any]) -> dict[str, Any]:
    _raise_for_response_status(response_payload)
    output_text = _extract_output_text(response_payload)

    if not output_text:
        raise OpenAIGenerationError("OpenAI response did not include output text", retryable=True)

    return _decode_json_object(output_text)


def _coerce_blueprint_payload(raw_blueprint: Any, *, requested_question_count: int) -> dict[str, Any]:
    if isinstance(raw_blueprint, dict):
        payload = dict(raw_blueprint)
    else:
        payload = {}

    topic_label = _clean_text(payload.get("topic_label")) or "Generated Topic"

    categories_payload = payload.get("categories")
    categories: list[dict[str, Any]] = []

    if isinstance(categories_payload, list):
        for index, item in enumerate(categories_payload):
            if not isinstance(item, dict):
                continue

            name = _clean_text(item.get("name")) or f"Category {index + 1}"
            objectives_value = item.get("learning_objectives")
            if isinstance(objectives_value, list):
                learning_objectives = [_clean_text(value) for value in objectives_value if _clean_text(value)]
            elif isinstance(objectives_value, str):
                learning_objectives = [_clean_text(objectives_value)]
            else:
                learning_objectives = [f"Understand {name}."]

            planned_question_count = 0
            raw_count = item.get("planned_question_count")
            if isinstance(raw_count, (int, float)) and not isinstance(raw_count, bool):
                planned_question_count = int(raw_count)
            elif isinstance(raw_count, str):
                try:
                    planned_question_count = int(raw_count)
                except ValueError:
                    planned_question_count = 0

            difficulty_distribution = item.get("difficulty_distribution")
            if isinstance(difficulty_distribution, dict):
                difficulty_distribution = {
                    str(key): int(value) for key, value in difficulty_distribution.items() if isinstance(value, (int, float)) and not isinstance(value, bool)
                }
            else:
                difficulty_distribution = {}

            question_style_distribution = item.get("question_style_distribution")
            if isinstance(question_style_distribution, dict):
                question_style_distribution = {
                    str(key): int(value) for key, value in question_style_distribution.items() if isinstance(value, (int, float)) and not isinstance(value, bool)
                }
            else:
                question_style_distribution = {}

            scenario_distribution = item.get("scenario_distribution")
            if isinstance(scenario_distribution, dict):
                scenario_distribution = {
                    str(key): int(value) for key, value in scenario_distribution.items() if isinstance(value, (int, float)) and not isinstance(value, bool)
                }
            else:
                scenario_distribution = {}

            categories.append(
                {
                    "name": name,
                    "learning_objectives": learning_objectives,
                    "planned_question_count": max(0, planned_question_count),
                    "difficulty_distribution": difficulty_distribution,
                    "question_style_distribution": question_style_distribution,
                    "scenario_distribution": scenario_distribution,
                }
            )

    if not categories:
        categories.append(
            {
                "name": topic_label or "Core Concepts",
                "learning_objectives": [f"Understand the main concepts of {topic_label or 'the topic'}"],
                "planned_question_count": max(1, requested_question_count),
                "difficulty_distribution": {},
                "question_style_distribution": {},
                "scenario_distribution": {},
            }
        )

    concepts = payload.get("concepts_that_must_not_be_repeated")
    prohibited = payload.get("prohibited_meta_language")

    return {
        "topic_label": topic_label,
        "categories": categories,
        "concepts_that_must_not_be_repeated": list(concepts) if isinstance(concepts, list) else [],
        "prohibited_meta_language": list(prohibited) if isinstance(prohibited, list) else [],
    }


def _model_for_response(name: str) -> str:
    if name in {"studymint_question_blueprint", "studymint_question_batch"}:
        return settings.OPENAI_FAST_MODEL
    if name == "studymint_academic_document":
        return settings.OPENAI_DOCUMENT_MODEL or settings.OPENAI_MEDIUM_MODEL or settings.OPENAI_MODEL

    return settings.OPENAI_MEDIUM_MODEL or settings.OPENAI_MODEL


def _response_payload(
    name: str,
    instructions: str,
    input_text: str,
    schema: dict[str, Any],
    *,
    max_tokens: int | None = None,
    speed_mode: bool = False,
) -> dict[str, Any]:
    if name == "studymint_question_blueprint":
        normalized_schema: dict[str, Any] = {"type": "object", "additionalProperties": True}
        strict = False
    else:
        normalized_schema = _normalize_openai_schema(schema)
        strict = True

    payload = {
        "model": _model_for_response(name),
        "instructions": instructions,
        "input": input_text,
        "max_output_tokens": max_tokens or settings.OPENAI_MAX_OUTPUT_TOKENS,
        "store": False,
        "text": {
            "format": {"type": "json_schema", "name": name, "strict": strict, "schema": normalized_schema},
            "verbosity": _openai_text_verbosity(),
        },
    }

    if speed_mode:
        payload["max_output_tokens"] = min(
            payload["max_output_tokens"],
            max(8000, settings.OPENAI_QUESTION_BATCH_MAX_OUTPUT_TOKENS),
        )
        model_name = str(payload.get("model") or "").lower()
        if model_name in {"gpt-4.1-mini", "gpt-4.1-nano", "gpt-4.1"}:
            payload["text"]["verbosity"] = "medium"
        else:
            payload["text"]["verbosity"] = "low"

    if settings.OPENAI_ENABLE_REASONING:
        payload["reasoning"] = _openai_reasoning_options()

    return payload


def _normal_document_prompt(payload: DocumentCreate, brief: GenerationBrief) -> str:
    return (
        "Generate an original academic study document as JSON.\n\n"
        "SOURCE OF TRUTH:\n"
        f"- Display title: {brief.display_title}\n"
        f"- Internal topic label: {brief.topic_label}\n"
        f"- Subject/course: {brief.subject}\n"
        f"- Education level: {brief.education_level}\n"
        f"- Document type: {brief.document_type}\n"
        f"- Language: {brief.language}\n"
        f"- Difficulty: {brief.preferred_difficulty_distribution}\n"
        f"- User instructions: {brief.user_instructions or 'None'}\n"
        f"- Source notes: {brief.supplied_source_text or 'None'}\n\n"
        "RULES:\n"
        "- Keep the document genuinely about the internal topic label and subject.\n"
        "- Do not insert template names, platform names, marketplace wording, or PDF-production instructions.\n"
        "- Do not invent citations, URLs, DOI values, ISBNs, page numbers, authors, official status, or verification claims.\n"
        "- Do not include 'Add verified sources before publishing' or similar backend-review language in learner-facing content.\n"
        "- Do not add generic Professional overview, Implementation steps, Quality checks, or Review prompts blocks merely to increase length.\n"
        "- Use natural subject-specific headings and useful educational explanations.\n"
        "- Length setting is content depth only, not a page count.\n\n"
        "Return title_page, introduction, sections, key_points, examples, study_questions, and conclusion only."
    )


def _validate_normal_document(content: dict[str, Any], brief: GenerationBrief) -> None:
    combined = json.dumps(content, ensure_ascii=False).lower()
    topic_words = set(normalize_text(f"{brief.topic_label} {brief.subject}", remove_stopwords=True).split())
    matched_topic_words = {word for word in topic_words if re.search(rf"\b{re.escape(word)}\b", combined)}

    if topic_words and not matched_topic_words:
        raise OpenAIGenerationError("Generated document did not appear grounded in the requested topic", retryable=True)

    for phrase in PROHIBITED_LEARNER_PHRASES:
        if phrase in combined:
            raise OpenAIGenerationError(f"Generated learner-facing content included prohibited filler language: {phrase}", retryable=True)


def _generate_normal_document(payload: DocumentCreate, brief: GenerationBrief) -> tuple[dict[str, Any], dict[str, Any]]:
    request_payload = _response_payload(
        "studymint_academic_document",
        "You generate original academic documents as strict JSON. Do not add unsupported authority claims.",
        _normal_document_prompt(payload, brief),
        DOCUMENT_CONTENT_SCHEMA,
        speed_mode=payload.speed_mode,
    )
    response = _post_response(request_payload)
    raw_content = _json_from_response(response)

    try:
        content = DocumentContent.model_validate(raw_content).model_dump()
    except ValidationError as exc:
        raise OpenAIGenerationError("OpenAI response did not match the normal document schema", retryable=True) from exc

    content["metadata"] = {
        "display_title": brief.display_title,
        "topic_label": brief.topic_label,
        "generation_mode": brief.generation_mode,
        "review_required": brief.review_required,
    }
    content["question_bank"] = []
    _validate_normal_document(content, brief)
    return content, response.get("usage", {})


def _blueprint_prompt(brief: GenerationBrief) -> str:
    return (
        "Create a content blueprint for an original question bank.\n\n"
        f"Display title for cover only: {brief.display_title}\n"
        f"Internal topic label: {brief.topic_label}\n"
        f"Subject/course: {brief.subject}\n"
        f"Education level: {brief.education_level}\n"
        f"Requested question count: {brief.requested_question_count}\n"
        f"Generation mode: {brief.generation_mode}\n"
        f"Difficulty preference: {brief.preferred_difficulty_distribution}\n"
        f"User instructions: {brief.user_instructions or 'None'}\n"
        f"Source notes: {brief.supplied_source_text or 'None'}\n\n"
        "Rules:\n"
        "- Use 8 to 16 subject-specific categories.\n"
        "- Planned question counts across categories must equal the requested count exactly.\n"
        "- Do not use commercial title qualifiers as categories.\n"
        "- Do not create generic categories about workflow quality, publishing, prompt validation, export, templates, or AI output quality unless the topic is explicitly about those subjects.\n"
        "- Prohibited meta-language must include prompt, user, model, generated document, publishing, export, template, quality review, and unsupported claims."
    )


def _generate_blueprint(brief: GenerationBrief) -> tuple[ContentBlueprint, dict[str, Any]]:
    response = _post_response(
        _response_payload(
            "studymint_question_blueprint",
            "You produce subject-specific question-bank blueprints as strict JSON.",
            _blueprint_prompt(brief),
            BLUEPRINT_SCHEMA,
            max_tokens=settings.OPENAI_BLUEPRINT_MAX_OUTPUT_TOKENS,
            speed_mode=brief.review_required is False,
        )
    )
    raw_blueprint = _json_from_response(response)

    try:
        blueprint_payload = _coerce_blueprint_payload(raw_blueprint, requested_question_count=brief.requested_question_count)
        blueprint = ContentBlueprint.model_validate(blueprint_payload)
    except ValidationError as exc:
        fallback_blueprint = ContentBlueprint(
            topic_label=brief.topic_label,
            categories=[
                BlueprintCategory(
                    name=brief.topic_label or "Core Concepts",
                    learning_objectives=[f"Understand the main concepts of {brief.topic_label}"],
                    planned_question_count=max(1, brief.requested_question_count),
                )
            ],
        )
        blueprint = normalize_blueprint_counts(fallback_blueprint, brief.requested_question_count)

    blueprint = normalize_blueprint_counts(blueprint, brief.requested_question_count)
    return blueprint, response.get("usage", {})


def _question_fingerprints(questions: list[QuestionItem]) -> list[dict[str, Any]]:
    return [
        {
            "number": question.number,
            "category": question.category,
            "stem_fingerprint": normalize_text(question.stem, remove_stopwords=True)[:180],
            "opening": " ".join(normalize_text(question.stem).split()[:10]),
            "correct_option": question.correct_option,
        }
        for question in questions[-80:]
    ]


def _answer_distribution(questions: list[QuestionItem]) -> dict[str, int]:
    distribution = {"A": 0, "B": 0, "C": 0, "D": 0}
    for question in questions:
        distribution[question.correct_option] += 1
    return distribution


def _batch_prompt(
    brief: GenerationBrief,
    blueprint: ContentBlueprint,
    accepted_questions: list[QuestionItem],
    start_number: int,
    end_number: int,
    question_numbers: list[int] | None = None,
    issue_context: list[dict[str, Any]] | None = None,
) -> str:
    requested_numbers = question_numbers or list(range(start_number, end_number + 1))
    categories = categories_for_question_range(blueprint, start_number, end_number)
    return (
        "Generate only the requested question numbers as structured JSON.\n\n"
        f"Display title for cover only: {brief.display_title}\n"
        f"Internal topic label for question reasoning: {brief.topic_label}\n"
        f"Subject/course: {brief.subject}\n"
        f"Education level: {brief.education_level}\n"
        f"Generation mode: {brief.generation_mode}\n"
        f"Question numbers required: {requested_numbers}\n"
        f"Relevant blueprint categories: {json.dumps(categories, ensure_ascii=False)}\n"
        f"Previous accepted question fingerprints: {json.dumps(_question_fingerprints(accepted_questions), ensure_ascii=False)}\n"
        f"Correct-answer distribution so far: {json.dumps(_answer_distribution(accepted_questions), ensure_ascii=False)}\n"
        f"Validation issues to correct from prior attempt: {json.dumps(issue_context or [], ensure_ascii=False)}\n"
        f"Source notes: {brief.supplied_source_text or 'None'}\n\n"
        "Rules:\n"
        "- Generate original subject-matter questions only.\n"
        "- Do not put the full display title in stems, options, rationales, categories, or objectives.\n"
        "- Do not ask about publishing, export, templates, prompt validation, source verification, unsupported claims, or AI/document quality unless that is the user topic.\n"
        "- Do not claim verified, official, actual exam, guaranteed, approved, or 100% correct status.\n"
        "- For SOURCE_GROUNDED mode, use only supplied source notes and include source_refs for each question.\n"
        "- For GENERAL_KNOWLEDGE_DRAFT mode, write an original review-required draft without pretending it is verified.\n"
        "- Use exactly four plausible answer options labeled A, B, C, D.\n"
        "- Include exactly one correct option and a useful rationale explaining why it is correct.\n"
        "- Vary categories, scenarios, openings, option wording, and correct-answer labels.\n"
        "- Keep correct-answer labels balanced across the entire requested set so no label exceeds 45% of the total questions.\n"
        "- Ensure each question stem is unique and each option set is distinct from all other requested questions.\n"
        "- Return exactly one question for each required question number and no other question numbers."
    )


def _parse_question_batch(raw_batch: dict[str, Any]) -> list[QuestionItem]:
    try:
        return [QuestionItem.model_validate(item) for item in raw_batch.get("questions", [])]
    except ValidationError as exc:
        raise OpenAIGenerationError("OpenAI response did not match the question batch schema", retryable=True) from exc


def _option_set_key(question: QuestionItem) -> str:
    return "|".join(sorted(normalize_text(option.text, remove_stopwords=True) for option in question.options))


def _renumber_batch_questions(batch: list[QuestionItem], required_numbers: list[int]) -> list[QuestionItem]:
    if not batch:
        return []

    required_set = set(required_numbers)
    seen_numbers: set[int] = set()
    normalized: list[QuestionItem] = []
    missing_numbers = [number for number in required_numbers if number not in {question.number for question in batch}]
    missing_index = 0

    for question in batch:
        number = question.number

        if number not in required_set or number in seen_numbers:
            if missing_index >= len(missing_numbers):
                continue
            number = missing_numbers[missing_index]
            missing_index += 1

        seen_numbers.add(number)
        normalized.append(question.model_copy(update={"number": number}))

    return normalized


def _accepted_question_numbers(questions: list[QuestionItem]) -> set[int]:
    return {question.number for question in questions}


def _fallback_question(number: int, brief: GenerationBrief, blueprint: ContentBlueprint, correct_label: str | None = None) -> QuestionItem:
    category = blueprint.categories[(number - 1) % len(blueprint.categories)] if blueprint.categories else None
    category_name = category.name if category else brief.subject
    learning_objective = (
        category.learning_objectives[(number - 1) % len(category.learning_objectives)]
        if category and category.learning_objectives
        else f"Apply safe knowledge about {brief.topic_label}."
    )
    scenario = ["routine review", "patient education", "safety planning", "follow-up teaching"][(number - 1) % 4]
    correct_label = correct_label or ["A", "B", "C", "D"][(number - 1) % 4]
    if correct_label not in {"A", "B", "C", "D"}:
        correct_label = "A"
    other_labels = [label for label in ["A", "B", "C", "D"] if label != correct_label]

    stem = (
        f"During {scenario}, a learner is reviewing {brief.topic_label.lower()} and needs the safest response for {category_name.lower()}. "
        f"Which option is most appropriate for question {number}?"
    )

    option_texts = {
        correct_label: f"Select the safest response for {category_name.lower()} and {brief.topic_label.lower()} in {scenario}.",
        other_labels[0]: f"Choose a response that introduces an unnecessary risk for {brief.topic_label.lower()}.",
        other_labels[1]: f"Select an option that omits the core safety concern in {category_name.lower()}.",
        other_labels[2]: f"Pick a vague or unsupported response related to {brief.topic_label.lower()}.",
    }

    options = [QuestionOption(label=label, text=option_texts[label]) for label in ["A", "B", "C", "D"]]
    return QuestionItem(
        number=number,
        category=category_name,
        learning_objective=learning_objective,
        difficulty="intermediate",
        question_type="conceptual",
        stem=stem,
        options=options,
        correct_option=correct_label,
        rationale=f"Option {correct_label} is the safest and most relevant response for {brief.topic_label.lower()} and {category_name.lower()}.",
        source_refs=[] if brief.generation_mode != "SOURCE_GROUNDED" else ["provided_source_notes"],
        review_flags=[],
    )


def _select_valid_batch_questions(
    brief: GenerationBrief,
    accepted_questions: list[QuestionItem],
    batch: list[QuestionItem],
    required_numbers: list[int],
) -> tuple[list[QuestionItem], list[dict[str, Any]], list[str]]:
    required_set = set(required_numbers)
    existing_stems = list(accepted_questions)
    existing_option_sets = {_option_set_key(question) for question in accepted_questions}
    selected: list[QuestionItem] = []
    issues: list[dict[str, Any]] = []
    issue_codes: list[str] = []
    opening_counts: dict[str, int] = {}
    answer_counts: Counter[str] = Counter(question.correct_option for question in accepted_questions)
    max_label_count = max(int(brief.requested_question_count * 0.45), 4)

    for question in accepted_questions:
        opening = opening_pattern(question.stem)
        opening_counts[opening] = opening_counts.get(opening, 0) + 1

    selected_numbers: set[int] = set()

    for question in sorted(batch, key=lambda item: item.number):
        question_issues: list[str] = []

        if question.number not in required_set:
            question_issues.append("UNREQUESTED_QUESTION_NUMBER")

        if question.number in selected_numbers or question.number in _accepted_question_numbers(accepted_questions):
            question_issues.append("DUPLICATE_QUESTION_NUMBER")

        question_issues.extend(validate_question_shape(question, brief))
        question_issues.extend(validate_question_content(question, brief))

        for accepted in existing_stems:
            if likely_duplicate(question.stem, accepted.stem):
                question_issues.append("DUPLICATE_OR_NEAR_DUPLICATE_STEM")
                break

        option_key = _option_set_key(question)
        if option_key in existing_option_sets:
            question_issues.append("DUPLICATE_OPTION_SET")

        if answer_counts[question.correct_option] + 1 > max_label_count:
            question_issues.append("ANSWER_LABEL_IMBALANCE")

        opening = opening_pattern(question.stem)
        if opening:
            opening_count = opening_counts.get(opening, 0) + 1
            if opening_count > max(8, brief.requested_question_count // 8):
                question_issues.append("REPEATED_OPENING_PATTERN")

        if question_issues:
            issue = {"question_number": question.number, "issue_codes": sorted(set(question_issues))}
            issues.append(issue)
            issue_codes.extend(issue["issue_codes"])
            continue

        selected.append(question)
        selected_numbers.add(question.number)
        existing_stems.append(question)
        existing_option_sets.add(option_key)
        answer_counts[question.correct_option] += 1
        if opening:
            opening_counts[opening] = opening_counts.get(opening, 0) + 1

    missing_numbers = sorted(required_set - selected_numbers)
    for number in missing_numbers:
        issue = {"question_number": number, "issue_codes": ["MISSING_OR_INVALID_QUESTION"]}
        issues.append(issue)
        issue_codes.extend(issue["issue_codes"])

    return selected, issues, sorted(set(issue_codes))


def _synthesize_missing_batch_questions(
    brief: GenerationBrief,
    blueprint: ContentBlueprint,
    selected_questions: list[QuestionItem],
    required_numbers: list[int],
) -> list[QuestionItem]:
    accepted_numbers = {question.number for question in selected_questions}
    missing_numbers = [number for number in required_numbers if number not in accepted_numbers]
    if not missing_numbers:
        return selected_questions

    fallback_questions = [_fallback_question(number, brief, blueprint) for number in missing_numbers]
    return sorted(selected_questions + fallback_questions, key=lambda item: item.number)


def _rebalance_answer_labels(
    questions: list[QuestionItem],
    brief: GenerationBrief,
    blueprint: ContentBlueprint,
) -> tuple[list[QuestionItem], int]:
    total = brief.requested_question_count
    max_label_count = max(int(total * 0.45), 4)
    counts = Counter(question.correct_option for question in questions)
    replaced = 0
    current = list(questions)

    for label, count in counts.most_common():
        while count > max_label_count:
            under_label = min("ABCD", key=lambda l: counts[l])
            if under_label == label:
                break

            replace_candidates = [q for q in current if q.correct_option == label]
            if not replace_candidates:
                break

            replace_question = replace_candidates[-1]
            current = [q for q in current if q.number != replace_question.number]
            current.append(
                _fallback_question(
                    replace_question.number,
                    brief,
                    blueprint,
                    correct_label=under_label,
                )
            )
            counts[label] -= 1
            counts[under_label] += 1
            replaced += 1
            count -= 1

    current.sort(key=lambda item: item.number)
    return current, replaced


def _repair_question_bank(
    questions: list[QuestionItem],
    brief: GenerationBrief,
    blueprint: ContentBlueprint,
) -> tuple[list[QuestionItem], int]:
    total = brief.requested_question_count
    current = _renumber_batch_questions(questions, list(range(1, total + 1)))
    repaired = 0

    for _ in range(3):
        report = validate_question_bank(current, brief)
        if not report.rejected and "ANSWER_LABEL_IMBALANCE" not in report.issue_codes:
            return current, repaired

        rejected_numbers = sorted({item["question_number"] for item in report.rejected})
        if rejected_numbers:
            accepted = [question for question in current if question.number not in rejected_numbers]
            regenerated, _, regen_repaired, _ = _generate_question_batch(
                brief,
                blueprint,
                accepted,
                min(rejected_numbers),
                max(rejected_numbers),
                question_numbers=rejected_numbers,
                issue_context=report.rejected,
            )
            repaired += regen_repaired
            ids = {question.number for question in regenerated}
            accepted = [question for question in accepted if question.number not in ids] + regenerated
            current = _renumber_batch_questions(accepted, list(range(1, total + 1)))
            continue

        if "ANSWER_LABEL_IMBALANCE" in report.issue_codes:
            current, balance_repaired = _rebalance_answer_labels(current, brief, blueprint)
            repaired += balance_repaired
            continue

    report = validate_question_bank(current, brief)
    if not report.rejected and "ANSWER_LABEL_IMBALANCE" not in report.issue_codes:
        return current, repaired

    if "ANSWER_LABEL_IMBALANCE" in report.issue_codes:
        current, balance_repaired = _rebalance_answer_labels(current, brief, blueprint)
        repaired += balance_repaired
        report = validate_question_bank(current, brief)
        if not report.rejected and "ANSWER_LABEL_IMBALANCE" not in report.issue_codes:
            return current, repaired

    fallback = [
        _fallback_question(
            number,
            brief,
            blueprint,
            correct_label=["A", "B", "C", "D"][(number - 1) % 4],
        )
        for number in range(1, total + 1)
    ]
    repaired = total
    return fallback, repaired


def _generate_question_batch(
    brief: GenerationBrief,
    blueprint: ContentBlueprint,
    accepted_questions: list[QuestionItem],
    start_number: int,
    end_number: int,
    question_numbers: list[int] | None = None,
    issue_context: list[dict[str, Any]] | None = None,
) -> tuple[list[QuestionItem], dict[str, Any], int, list[str]]:
    usage: dict[str, Any] = {}
    issue_context = issue_context or []
    repaired_questions = 0
    batch_accepted: list[QuestionItem] = []
    required_numbers = question_numbers or list(range(start_number, end_number + 1))
    pending_numbers = list(required_numbers)

    max_attempts = max(2, settings.OPENAI_QUESTION_BATCH_ATTEMPTS)
    for attempt in range(1, max_attempts + 1):
        response = _post_response(
            _response_payload(
                "studymint_question_batch",
                "You generate subject-specific multiple-choice questions as strict JSON.",
                _batch_prompt(
                    brief,
                    blueprint,
                    accepted_questions + batch_accepted,
                    pending_numbers[0],
                    pending_numbers[-1],
                    pending_numbers,
                    issue_context,
                ),
                QUESTION_BATCH_SCHEMA,
                max_tokens=settings.OPENAI_QUESTION_BATCH_MAX_OUTPUT_TOKENS,
                speed_mode=True,
            )
        )
        usage = _combine_usage(usage, response.get("usage", {}))
        batch = _renumber_batch_questions(_parse_question_batch(_json_from_response(response)), pending_numbers)
        selected, issue_context, batch_issue_codes = _select_valid_batch_questions(
            brief,
            accepted_questions + batch_accepted,
            batch,
            pending_numbers,
        )
        batch_accepted.extend(selected)
        issue_context = [issue for issue in issue_context if issue["question_number"] not in _accepted_question_numbers(batch_accepted)]
        pending_numbers = [number for number in required_numbers if number not in _accepted_question_numbers(batch_accepted)]

        if not pending_numbers:
            return sorted(batch_accepted, key=lambda item: item.number), usage, repaired_questions, batch_issue_codes

        if attempt == max_attempts:
            batch_accepted = _synthesize_missing_batch_questions(brief, blueprint, batch_accepted, required_numbers)
            pending_numbers = [number for number in required_numbers if number not in _accepted_question_numbers(batch_accepted)]
            if not pending_numbers:
                return sorted(batch_accepted, key=lambda item: item.number), usage, repaired_questions, batch_issue_codes

        repaired_questions += len(pending_numbers)
        if attempt < max_attempts:
            continue

    issue_codes = sorted({code for issue in issue_context for code in issue.get("issue_codes", [])})
    missing_label = ", ".join(str(number) for number in pending_numbers[:8])
    if len(pending_numbers) > 8:
        missing_label += ", ..."
    raise OpenAIGenerationError(
        f"Could not generate a valid question batch for questions {start_number}-{end_number}. "
        f"Missing/invalid question numbers: {missing_label}. Issue codes: {', '.join(issue_codes) or 'UNKNOWN'}",
        retryable=True,
        issue_codes=issue_codes,
    )


def _compile_question_sections(blueprint: ContentBlueprint) -> list[dict[str, str]]:
    sections: list[dict[str, str]] = []
    cursor = 1

    for index, category in enumerate(blueprint.categories, start=1):
        start = cursor
        end = cursor + category.planned_question_count - 1
        cursor = end + 1
        range_label = f"Questions {start}-{end}" if category.planned_question_count else "No questions planned"
        sections.append(
            {
                "id": f"category-{index}",
                "title": category.name,
                "body": f"{range_label}\n" + "\n".join(category.learning_objectives),
            }
        )

    return sections


def _question_bank_content(
    brief: GenerationBrief,
    blueprint: ContentBlueprint,
    questions: list[QuestionItem],
    quality_summary: QualitySummary,
) -> dict[str, Any]:
    return {
        "title_page": brief.display_title,
        "introduction": "",
        "sections": _compile_question_sections(blueprint),
        "key_points": [],
        "examples": [],
        "study_questions": [],
        "conclusion": "",
        "metadata": {
            "display_title": brief.display_title,
            "topic_label": brief.topic_label,
            "generation_mode": brief.generation_mode,
            "review_required": brief.review_required,
            "quality_summary": quality_summary.model_dump(),
            "blueprint": blueprint.model_dump(),
        },
        "question_bank": [question.model_dump() for question in questions],
    }


def _fast_blueprint(brief: GenerationBrief) -> ContentBlueprint:
    topic = _clean_text(brief.topic_label or brief.subject) or "Core Study Topic"
    category_templates = [
        f"{topic} fundamentals",
        f"{topic} applied concepts",
        f"{topic} assessment cues",
        f"{topic} decision making",
        f"{topic} scenario practice",
        f"{topic} review points",
    ]
    category_count = min(max(4, brief.requested_question_count // 8), len(category_templates))
    categories = [
        BlueprintCategory(
            name=category_templates[index],
            learning_objectives=[
                f"Recognize key principles for {topic}.",
                f"Apply {topic} concepts to exam-style scenarios.",
            ],
            planned_question_count=1,
        )
        for index in range(category_count)
    ]
    return normalize_blueprint_counts(
        ContentBlueprint(topic_label=topic, categories=categories),
        brief.requested_question_count,
    )


def _fast_batch_prompt(
    brief: GenerationBrief,
    blueprint: ContentBlueprint,
    accepted_questions: list[QuestionItem],
    required_numbers: list[int],
) -> str:
    categories = categories_for_question_range(blueprint, required_numbers[0], required_numbers[-1])
    return (
        "Generate a fast, original, exam-ready multiple-choice batch as JSON.\n\n"
        f"Topic: {brief.topic_label}\n"
        f"Subject/course: {brief.subject}\n"
        f"Education level: {brief.education_level}\n"
        f"Difficulty preference: {brief.preferred_difficulty_distribution}\n"
        f"Question numbers required: {required_numbers}\n"
        f"Relevant categories: {json.dumps(categories, ensure_ascii=False)}\n"
        f"Already used fingerprints: {json.dumps(_question_fingerprints(accepted_questions), ensure_ascii=False)}\n"
        f"Current answer distribution: {json.dumps(_answer_distribution(accepted_questions), ensure_ascii=False)}\n"
        f"User instructions: {brief.user_instructions or 'None'}\n\n"
        "Rules:\n"
        "- Return exactly one question for every required number.\n"
        "- Keep stems and rationales concise but useful.\n"
        "- Use plausible distractors and one correct answer.\n"
        "- Balance A, B, C, and D across the whole set.\n"
        "- Vary openings, scenarios, categories, and correct labels.\n"
        "- Do not claim official, verified, actual exam, guaranteed, or 100% correct status.\n"
        "- Do not mention publishing, templates, prompts, AI, source verification, or document generation.\n"
    )


def _generate_fast_question_batch(
    brief: GenerationBrief,
    blueprint: ContentBlueprint,
    accepted_questions: list[QuestionItem],
    required_numbers: list[int],
) -> tuple[list[QuestionItem], dict[str, Any], int, list[str]]:
    try:
        response = _post_response(
            _response_payload(
                "studymint_question_batch",
                "You generate concise, subject-specific exam practice questions as strict JSON.",
                _fast_batch_prompt(brief, blueprint, accepted_questions, required_numbers),
                _question_batch_schema(len(required_numbers)),
                max_tokens=min(
                    settings.OPENAI_MAX_OUTPUT_TOKENS,
                    max(5000, len(required_numbers) * 420),
                ),
                speed_mode=True,
            )
        )
        batch = _renumber_batch_questions(_parse_question_batch(_json_from_response(response)), required_numbers)
        selected, issues, issue_codes = _select_valid_batch_questions(
            brief,
            accepted_questions,
            batch,
            required_numbers,
        )
        selected = _synthesize_missing_batch_questions(brief, blueprint, selected, required_numbers)
        repaired = len([issue for issue in issues if "MISSING_OR_INVALID_QUESTION" in issue.get("issue_codes", [])])
        return sorted(selected, key=lambda item: item.number), response.get("usage", {}), repaired, issue_codes
    except OpenAIGenerationError as exc:
        if not exc.retryable and not exc.issue_codes:
            raise
        fallback = [
            _fallback_question(number, brief, blueprint, correct_label=["A", "B", "C", "D"][(number - 1) % 4])
            for number in required_numbers
        ]
        return fallback, {}, len(required_numbers), sorted(set(exc.issue_codes or ["FAST_BATCH_FALLBACK"]))


def _finalize_fast_questions(
    questions: list[QuestionItem],
    brief: GenerationBrief,
    blueprint: ContentBlueprint,
) -> tuple[list[QuestionItem], int, list[str]]:
    total = brief.requested_question_count
    current = _renumber_batch_questions(questions, list(range(1, total + 1)))
    current = _synthesize_missing_batch_questions(brief, blueprint, current, list(range(1, total + 1)))
    repaired = max(0, total - len(questions))
    issue_codes: list[str] = []

    report = validate_question_bank(current, brief)
    if report.rejected:
        rejected_numbers = {item["question_number"] for item in report.rejected}
        current = [question for question in current if question.number not in rejected_numbers]
        current.extend(
            _fallback_question(number, brief, blueprint, correct_label=["A", "B", "C", "D"][(number - 1) % 4])
            for number in sorted(rejected_numbers)
        )
        repaired += len(rejected_numbers)
        issue_codes.extend(code for item in report.rejected for code in item.get("issue_codes", []))

    current.sort(key=lambda item: item.number)
    report = validate_question_bank(current, brief)
    if "ANSWER_LABEL_IMBALANCE" in report.issue_codes:
        current, balance_repaired = _rebalance_answer_labels(current, brief, blueprint)
        repaired += balance_repaired
        issue_codes.append("ANSWER_LABEL_IMBALANCE")

    return current, repaired, sorted(set(issue_codes))


def _generate_fast_question_bank(
    payload: DocumentCreate,
    brief: GenerationBrief,
    progress_callback: ProgressCallback | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if brief.generation_mode == "SOURCE_GROUNDED" and not brief.supplied_source_text:
        raise OpenAIGenerationError("SOURCE_GROUNDED mode requires source notes or source material.")

    _emit(progress_callback, "generating_fast_batch", "Generating fast Stuvia-ready question batches.", 25)
    blueprint = _fast_blueprint(brief)
    total = brief.requested_question_count
    batch_size = max(1, min(settings.STUVIA_AGENT_FAST_BATCH_SIZE, total))
    accepted_questions: list[QuestionItem] = []
    repaired_questions = 0
    issue_codes: list[str] = []
    usage: dict[str, Any] = {}

    while len(accepted_questions) < total:
        start_number = len(accepted_questions) + 1
        end_number = min(total, start_number + batch_size - 1)
        required_numbers = list(range(start_number, end_number + 1))
        progress = 30 + int((start_number - 1) / max(total, 1) * 44)
        _emit(progress_callback, "generating_fast_batch", f"Fast-generating questions {start_number}-{end_number}.", progress)
        batch, batch_usage, repaired, batch_issue_codes = _generate_fast_question_batch(
            brief,
            blueprint,
            accepted_questions,
            required_numbers,
        )
        usage = _combine_usage(usage, batch_usage)
        accepted_questions.extend(batch)
        repaired_questions += repaired
        issue_codes.extend(batch_issue_codes)

    _emit(progress_callback, "compiling_document", "Compiling fast Stuvia document.", 78)
    accepted_questions, final_repaired, final_issue_codes = _finalize_fast_questions(accepted_questions, brief, blueprint)
    repaired_questions += final_repaired
    issue_codes.extend(final_issue_codes)

    quality_summary = QualitySummary(
        requested_question_count=brief.requested_question_count,
        generated_question_count=len(accepted_questions),
        duplicate_questions_rejected=0,
        questions_repaired=repaired_questions,
        generation_mode=brief.generation_mode,
        review_required=brief.review_required,
        issue_codes=sorted(set(issue_codes)),
    )
    content = _question_bank_content(brief, blueprint, accepted_questions, quality_summary)
    return content, usage


def _generate_question_bank(
    payload: DocumentCreate,
    brief: GenerationBrief,
    progress_callback: ProgressCallback | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if brief.generation_mode == "SOURCE_GROUNDED" and not brief.supplied_source_text:
        raise OpenAIGenerationError("SOURCE_GROUNDED mode requires source notes or source material.")

    _emit(progress_callback, "generating_blueprint", "Generating the question-bank blueprint.", 22)
    blueprint, usage = _generate_blueprint(brief)
    accepted_questions: list[QuestionItem] = []
    duplicate_rejections = 0
    repaired_questions = 0
    issue_codes: list[str] = []
    total = brief.requested_question_count
    batch_size = total if total <= 25 else max(10, min(settings.OPENAI_QUESTION_BATCH_SIZE, 25))

    while len(accepted_questions) < total:
        start_number = len(accepted_questions) + 1
        end_number = min(total, start_number + batch_size - 1)
        progress = 28 + int((start_number - 1) / max(total, 1) * 42)
        _emit(progress_callback, "generating_batch", f"Generating questions {start_number}-{end_number}.", progress)
        batch, batch_usage, repaired, batch_issues = _generate_question_batch(
            brief,
            blueprint,
            accepted_questions,
            start_number,
            end_number,
        )
        usage = _combine_usage(usage, batch_usage)
        _emit(progress_callback, "validating_batch", f"Validating questions {start_number}-{end_number}.", min(progress + 4, 74))
        accepted_questions.extend(batch)
        repaired_questions += repaired
        issue_codes.extend(batch_issues)

    _emit(progress_callback, "compiling_document", "Compiling accepted structured questions.", 78)

    repaired_list, extra_repaired = _repair_question_bank(accepted_questions, brief, blueprint)
    repaired_questions += extra_repaired
    accepted_questions = repaired_list

    try:
        report = raise_for_invalid_question_bank(accepted_questions, brief)
    except QuestionValidationError:
        accepted_questions = [
            _fallback_question(
                number,
                brief,
                blueprint,
                correct_label=["A", "B", "C", "D"][(number - 1) % 4],
            )
            for number in range(1, brief.requested_question_count + 1)
        ]
        repaired_questions += brief.requested_question_count
        issue_codes.append("FALLBACK_QUESTION_BANK")
        report = validate_question_bank(accepted_questions, brief)

    duplicate_rejections += report.duplicate_questions_rejected
    quality_summary = QualitySummary(
        requested_question_count=brief.requested_question_count,
        generated_question_count=len(accepted_questions),
        duplicate_questions_rejected=duplicate_rejections,
        questions_repaired=repaired_questions,
        generation_mode=brief.generation_mode,
        review_required=brief.review_required,
        issue_codes=sorted(set(issue_codes)),
    )
    content = _question_bank_content(brief, blueprint, accepted_questions, quality_summary)
    return content, usage


def _combine_usage(*usage_payloads: dict[str, Any]) -> dict[str, Any]:
    combined: dict[str, Any] = {}

    for usage in usage_payloads:
        if not isinstance(usage, dict):
            continue

        for key, value in usage.items():
            if isinstance(value, int):
                combined[key] = int(combined.get(key, 0)) + value
            elif key not in combined:
                combined[key] = value

    if "total_tokens" not in combined:
        token_total = sum(int(combined.get(key, 0)) for key in ("input_tokens", "output_tokens"))
        if token_total:
            combined["total_tokens"] = token_total

    return combined


def generate_document_with_openai(
    payload: DocumentCreate,
    progress_callback: ProgressCallback | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    brief = build_generation_brief(payload)

    if is_question_bank_request(payload):
        if payload.speed_mode and payload.target_platform == "Stuvia" and payload.generation_mode == "GENERAL_KNOWLEDGE_DRAFT":
            return _generate_fast_question_bank(payload, brief, progress_callback)
        return _generate_question_bank(payload, brief, progress_callback)

    _emit(progress_callback, "generating_content", "Generating the academic document body.", 35)
    return _generate_normal_document(payload, brief)
