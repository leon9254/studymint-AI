from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.template import Template
from app.services.template_ids import (
    BLUE_CERTIFICATION_ID,
    DEPRECATED_TEMPLATE_IDS,
    MAIN_ID,
    QUESTION_BANK_TEMPLATE_IDS,
)


"""
Default template service.

Critical product rule:
Templates are PDF styling/layout presets only.

They must never be treated as content instructions by the LLM.
The document topic must come only from:
- user document title
- subject/course
- education level
- document type
- output language
- length

Do not use template name, template ID, cover style, section style, target platform,
or marketplace metadata to infer document subject, industry, exam, profession,
institution, country, jurisdiction, or year.
"""


STYLE_ONLY_NOTICE = (
    "This is a visual PDF styling template only. It controls layout, typography, "
    "spacing, cover appearance, section presentation, and footer settings. "
    "It must not be used to infer, change, expand, or specialize the document topic."
)


CONTENT_SOURCE_CONTRACT: dict[str, Any] = {
    "template_role": "visual_style_only",
    "content_source_of_truth": [
        "document_title",
        "subject_or_course",
        "education_level",
        "document_type",
        "output_language",
        "length",
    ],
    "non_content_fields": [
        "template_id",
        "template_name",
        "target_platform",
        "marketplace_metadata",
        "font_settings",
        "cover_style",
        "section_style",
        "footer_settings",
    ],
    "hard_rules": [
        "Never infer topic from template.",
        "Never infer exam, certification, institution, year, profession, or industry from template.",
        "Never insert marketplace/platform names into document body unless the user title asks for them.",
        "Generate a polished title from the user-provided document title only.",
        "Template can only influence visual styling and PDF layout.",
    ],
}


def _style_contract(summary: str) -> dict[str, Any]:
    return {
        "role": "visual_style_only",
        "summary": summary,
        "notice": STYLE_ONLY_NOTICE,
        "content_source_contract": CONTENT_SOURCE_CONTRACT,
        "must_not_infer_topic": True,
        "must_not_add_exam_or_certification": True,
        "must_not_add_industry_or_profession": True,
        "must_not_add_institution_or_year": True,
        "must_not_add_platform_or_marketplace": True,
    }


DEFAULT_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "tpl_clean",
        "name": "Clean Academic Layout",
        "description": (
            "A calm, readable PDF layout for polished study notes, summaries, "
            "learning guides, and structured educational documents. "
            "Style only; content must come from the user's title and subject."
        ),
        "page_size": "A4",
        "font_settings": {
            "heading": "Inter Semibold",
            "body": "Inter",
            "body_size": "11pt",
            "heading_size": "15pt",
            "line_height": "1.5",
            "style_contract": _style_contract(
                "Modern academic layout with generous spacing, readable headings, "
                "balanced margins, simple key-point callouts, and page numbering."
            ),
        },
        "cover_style": (
            "Minimal cover using the polished title derived from the user-provided title only. "
            "Do not add subtitles, platform names, institution names, years, "
            "exam names, or template labels."
        ),
        "section_style": (
            "Numbered headings, clean paragraphs, optional key-point callouts, "
            "examples, and review questions. Do not force exam formatting unless "
            "the user selected an exam-prep document type."
        ),
        "footer_settings": {
            "page_numbers": "true",
            "tenant_branding": "true",
            "style_only": "true",
            "content_boundary": STYLE_ONLY_NOTICE,
        },
        "is_active": True,
    },
    {
        "id": "tpl_exam",
        "name": "Structured Practice Layout",
        "description": (
            "A dense revision PDF layout with question blocks, answers, rationales, "
            "and checkpoints. Style only; it does not define the exam, course, "
            "profession, subject, industry, institution, or year."
        ),
        "page_size": "A4",
        "font_settings": {
            "heading": "Inter Bold",
            "body": "Source Serif",
            "body_size": "11pt",
            "heading_size": "14pt",
            "line_height": "1.35",
            "style_contract": _style_contract(
                "Compact practice-document layout with question blocks, answer labels, "
                "rationale labels, checkpoints, and dense revision spacing."
            ),
        },
        "cover_style": (
            "Course-first cover using the polished title derived from the user-provided title and subject only. "
            "Do not add a fixed exam name, certification, institution, platform, "
            "or year unless it already appears in the user's title."
        ),
        "section_style": (
            "Compact sections, question blocks, answer labels, rationale labels, "
            "and checkpoints. Subject matter must still come only from the user's "
            "title and subject."
        ),
        "footer_settings": {
            "page_numbers": "true",
            "disclaimer": "true",
            "style_only": "true",
            "content_boundary": STYLE_ONLY_NOTICE,
        },
        "is_active": True,
    },
    {
        "id": "tpl_market",
        "name": "Listing Preview Layout",
        "description": (
            "A preview-friendly PDF export layout for clean document packaging. "
            "Style only; it must not add marketplace names, seller claims, "
            "publishing advice, or platform instructions to the document body."
        ),
        "page_size": "US Letter",
        "font_settings": {
            "heading": "Inter Semibold",
            "body": "Inter",
            "body_size": "11pt",
            "heading_size": "15pt",
            "line_height": "1.45",
            "style_contract": _style_contract(
                "Preview-friendly export layout with clear hierarchy, summary panels, "
                "clean spacing, and professional document packaging."
            ),
        },
        "cover_style": (
            "Preview-friendly cover using the polished title derived from the user-provided title only. "
            "Do not include platform names, seller language, upload language, "
            "or marketplace claims."
        ),
        "section_style": (
            "Clear hierarchy with summary panels, digestible sections, examples, "
            "and review questions based only on the user's topic."
        ),
        "footer_settings": {
            "page_numbers": "true",
            "copyright_notice": "true",
            "style_only": "true",
            "content_boundary": STYLE_ONLY_NOTICE,
        },
        "is_active": True,
    },
    {
        "id": BLUE_CERTIFICATION_ID,
        "name": "Blue Certification Test Bank Layout",
        "description": (
            "A style-only PDF layout matching a formal certification test-bank page: "
            "white A4 page, thick double black page border, centered blue underlined "
            "serif title, compact blue underlined section headings, dense Times-style "
            "body text, red answer labels, blue rationale labels, and thin gray dividers. "
            "It does not define or imply the document topic."
        ),
        "page_size": "A4",
        "font_settings": {
            "family": "Times New Roman",
            "fallback_family": "serif",
            "cover_title_size": "13.5pt",
            "body_size": "8.4pt",
            "heading_size": "8.2pt",
            "line_height": "12.25pt",
            "body_color": "#000000",
            "accent_color": "#0B6682",
            "answer_label_color": "#C01818",
            "page_border_color": "#000000",
            "page_border_width": "2.7pt",
            "margins": {
                "top": "0.83in",
                "bottom": "0.72in",
                "left": "0.74in",
                "right": "0.74in",
            },
            "cover_title": {
                "source": "polished_user_document_title_only",
                "alignment": "center",
                "uppercase": True,
                "bold": True,
                "underline": True,
                "color": "#0B6682",
                "size": "13.5pt",
                "must_not_use_fixed_title": True,
            },
            "answer_block": {
                "answer_label": "Answer:",
                "rationale_label": "Rationale:",
                "answer_label_color": "#C01818",
                "rationale_label_color": "#0B6682",
                "label_bold": True,
            },
            "style_contract": _style_contract(
                "Blue certification-style test-bank visual layout with a thick double black page border, "
                "compact Times New Roman typography, centered blue underlined title, blue underlined "
                "section labels, red answer labels, blue rationale labels, and thin gray dividers."
            ),
        },
        "cover_style": (
            "Centered uppercase blue bold underlined title. The title must be derived from the "
            "user-provided document title only. Do not insert any fixed exam title, association, "
            "institution, certification, state, year, edition, or question count unless the user "
            "entered it in the title."
        ),
        "section_style": (
            "Compact certification-style question layout: small blue underlined section headers, "
            "plain black question stems and A/B/C/D options, red Answer: label, blue Rationale: "
            "label, and thin gray horizontal dividers. This is a formatting rule only."
        ),
        "footer_settings": {
            "page_numbers": "false",
            "page_border": "true",
            "page_border_color": "#000000",
            "page_border_width": "2.7pt",
            "page_border_style": "double_black",
            "source_style": "blue_certification_test_bank_reference",
            "style_only": "true",
            "content_boundary": STYLE_ONLY_NOTICE,
            "content_warning": (
                "Do not use this template to infer the document topic. "
                "Content must come only from the user's title and subject."
            ),
        },
        "is_active": True,
    },
    {
        "id": MAIN_ID,
        "name": "Classic Red Exam Bundle Layout",
        "description": (
            "A style-only PDF layout inspired by a classic exam-bundle document: "
            "A4 page size, Times New Roman typography, thick red page border, "
            "centered red underlined cover title, bold section headings, plain "
            "question text, and red answer/rationale blocks. This template does "
            "not define or imply the document topic."
        ),
        "page_size": "A4",
        "font_settings": {
            "family": "Times New Roman",
            "fallback_family": "serif",
            "cover_title_size": "24pt",
            "body_size": "18pt",
            "heading_size": "18pt",
            "line_height": "30pt",
            "body_color": "#000000",
            "accent_color": "#FF0000",
            "page_border_color": "#EE0000",
            "page_border_width": "4.25pt",
            "margins": {
                "top": "0.73in",
                "bottom": "0.76in",
                "left": "0.90in",
                "right": "0.83in",
            },
            "cover_title": {
                "source": "polished_user_document_title_only",
                "alignment": "center",
                "uppercase": True,
                "bold": True,
                "underline": True,
                "color": "#FF0000",
                "size": "24pt",
                "must_not_use_fixed_title": True,
            },
            "answer_block": {
                "answer_label": "Answer:",
                "rationale_label": "Rationale:",
                "label_color": "#FF0000",
                "label_bold": True,
            },
            "style_contract": _style_contract(
                "Classic red-bordered exam-bundle visual style with Times New Roman, "
                "centered red underlined cover title, thick page border, bold headings, plain options, "
                "and red answer/rationale labels."
            ),
        },
        "cover_style": (
            "Centered uppercase red bold underlined cover title. The cover title "
            "must be derived from the user-provided document title only. Do not insert any "
            "fixed title, exam name, institution, platform, marketplace, subtitle, "
            "vendor label, or year unless the user entered it in the title."
        ),
        "section_style": (
            "Question-only layout for generated content: bold black 18pt question headings; "
            "plain A/B/C/D options; red Answer: and Rationale: labels. "
            "This is a formatting rule only, not a content-topic rule."
        ),
        "footer_settings": {
            "page_numbers": "false",
            "page_border": "true",
            "page_border_color": "#EE0000",
            "page_border_width": "4.25pt",
            "source_style": "classic_exam_bundle_reference",
            "style_only": "true",
            "content_boundary": STYLE_ONLY_NOTICE,
            "content_warning": (
                "Do not use this template to infer the document topic. "
                "Content must come only from the user's title and subject."
            ),
        },
        "is_active": True,
    },
]


def _clone_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Return a deep copy so nested JSON fields are not shared or accidentally
    mutated across requests.
    """
    return deepcopy(payload)


def _default_template_payload(template_id: str) -> dict[str, Any] | None:
    for payload in DEFAULT_TEMPLATES:
        if payload["id"] == template_id:
            return _clone_payload(payload)

    return None


def _template_needs_update(template: Template, payload: dict[str, Any]) -> bool:
    for key, value in payload.items():
        if getattr(template, key) != value:
            return True

    return False


def _apply_template_payload(template: Template, payload: dict[str, Any]) -> None:
    for key, value in payload.items():
        if getattr(template, key) != value:
            setattr(template, key, value)


def sync_default_templates(db: Session) -> int:
    """
    Create or update global default templates.

    Returns the number of global template records created or updated.
    Tenant-owned templates are never overwritten.
    """
    changed_records = 0

    for deprecated_id in DEPRECATED_TEMPLATE_IDS:
        deprecated_template = db.get(Template, deprecated_id)
        if deprecated_template is not None and deprecated_template.is_active:
            deprecated_template.is_active = False
            changed_records += 1

    for raw_payload in DEFAULT_TEMPLATES:
        payload = _clone_payload(raw_payload)
        template = db.get(Template, payload["id"])

        if template is None:
            db.add(Template(**payload))
            changed_records += 1
            continue

        # Never overwrite a tenant-owned template with a global default payload.
        if template.tenant_id is not None:
            continue

        if _template_needs_update(template, payload):
            _apply_template_payload(template, payload)
            changed_records += 1

    if changed_records:
        db.flush()

    return changed_records


def ensure_template_reference(db: Session, template_id: str | None, tenant_id: str) -> bool:
    """
    Ensure a requested template is valid for the tenant.

    Valid templates:
    - global templates with tenant_id = None
    - tenant-owned templates with matching tenant_id
    - known default templates that can be restored

    This function intentionally does not create tenant-specific copies of global
    templates. It restores missing global defaults only.
    """
    if not template_id:
        return True

    template = db.get(Template, template_id)

    if template and (template.tenant_id is None or template.tenant_id == tenant_id):
        return True

    payload = _default_template_payload(template_id)

    if payload is None:
        return False

    db.add(Template(**payload))
    db.flush()

    return True


def list_templates(db: Session, tenant_id: str) -> list[Template]:
    """
    List active global templates and active tenant-owned templates.
    """
    if sync_default_templates(db):
        db.commit()

    templates = list(
        db.scalars(
            select(Template)
            .where(
                Template.is_active.is_(True),
                Template.id.in_(QUESTION_BANK_TEMPLATE_IDS),
                or_(
                    Template.tenant_id.is_(None),
                    Template.tenant_id == tenant_id,
                ),
            )
            .order_by(
                Template.tenant_id.isnot(None),
                Template.name.asc(),
            )
        )
    )

    if templates:
        return templates

    # Defensive fallback for tests or unusual in-memory database states.
    now = datetime.now(timezone.utc)

    return [
        Template(**_clone_payload(payload), created_at=now, updated_at=now)
        for payload in DEFAULT_TEMPLATES
        if payload["id"] in QUESTION_BANK_TEMPLATE_IDS
    ]


def get_template_style_context(template: Template | dict[str, Any]) -> dict[str, Any]:
    """
    Return AI-safe template context.

    Use this if the generation service needs template information.
    This deliberately hides topic-leading fields and labels the template as
    visual styling only.

    The generator must not use this context to decide document content.
    """
    if isinstance(template, Template):
        page_size = template.page_size
        font_settings = template.font_settings or {}
        cover_style = template.cover_style
        section_style = template.section_style
        footer_settings = template.footer_settings or {}
    else:
        page_size = str(template.get("page_size", "A4"))
        font_settings = template.get("font_settings") or {}
        cover_style = str(template.get("cover_style", ""))
        section_style = str(template.get("section_style", ""))
        footer_settings = template.get("footer_settings") or {}

    return {
        "template_role": "visual_style_only",
        "style_controls": {
            "page_size": page_size,
            "font_settings": font_settings,
            "cover_style": cover_style,
            "section_style": section_style,
            "footer_settings": footer_settings,
        },
        "content_source_contract": CONTENT_SOURCE_CONTRACT,
        "generator_warning": (
            "Use this template only for PDF appearance. Do not infer topic, "
            "industry, course, exam, certification, institution, platform, "
            "country, jurisdiction, year, or subject from it."
        ),
    }


def get_default_template_style_context(template_id: str) -> dict[str, Any] | None:
    """
    Convenience helper when the generation service only has a template ID.
    """
    payload = _default_template_payload(template_id)

    if payload is None:
        return None

    return get_template_style_context(payload)


def get_forbidden_template_phrases() -> set[str]:
    """
    Return style/template phrases that generated content must not copy.

    This supports backend validation only. These phrases are not used as
    content instructions for the LLM.
    """
    phrases = set(DEPRECATED_TEMPLATE_IDS)

    for payload in DEFAULT_TEMPLATES:
        phrases.add(str(payload["id"]))
        phrases.add(str(payload["name"]))

    phrases.update(
        {
            "Classic Red Exam Bundle",
            "Classic Red Exam Bundle Layout",
            "Blue Certification Test Bank",
            "Blue Certification Test Bank Layout",
            "QSP/QSD CERTIFICATION EXAM",
            "QSP/QSD CERTIFICATION EXAM COMPREHENSIVE TEST BANK",
            "WITH ANSWERS AND RATIONALES California Stormwater Quality Association",
            "California Stormwater Quality Association (CASQA)",
            "HESI Exit Exam Complete Bundle 2026",
            "HESI Exit Exam Complete Bundle 2026/2027",
            "HESI Exit Exam Complete Bundle 2026/2027 Practice Questions & Rationales",
            "HESI EXIT EXAM COMPLETE BUNDLE 2026/2027 - PRACTICE QUESTIONS & RATIONALES",
        }
    )

    return {phrase for phrase in phrases if phrase.strip()}
