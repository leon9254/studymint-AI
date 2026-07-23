from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError

from app.core.secret_box import decrypt_secret, encrypt_secret
from app.core.config import settings
from app.schemas.document import DocumentCreate, DocumentRead
from app.schemas.question_bank import ContentBlueprint, GenerationBrief, QuestionItem
from app.schemas.stuvia_agent import StuviaAgentRunCreate
from app.services import openai_client, pdf_renderer, simple_pdf, stuvia_agent_service
from app.services.document_generation.brief import build_generation_brief
from app.services.document_generation.question_validator import validate_question_bank
from app.services.integration_service import filter_new_stuvia_topic_candidates, stuvia_topic_identity_keys
from app.services.openai_client import generate_document_with_openai
from app.services.simple_pdf import render_study_document_pdf


LONG_TITLE = (
    "WEB WOC OSTOMY CARE FINAL EXAM 2026/2027 ACTUAL EXAM COMPLETE 270 QUESTIONS "
    "WITH DETAILED VERIFIED ANSWERS (100% CORRECT ANSWERS)"
)

OSTOMY_CATEGORIES = [
    "Stoma Assessment",
    "Peristomal Skin Care",
    "Pouching Systems",
    "Postoperative Monitoring",
    "Ileostomy Hydration",
    "Colostomy Care",
    "Medication Considerations",
    "Patient Education",
    "Complication Recognition",
    "Psychosocial Adaptation",
    "Nutrition Planning",
    "Escalation and Safety",
]

OPENINGS = [
    "A client asks the nurse how to respond when",
    "During discharge teaching, which nursing action is best when",
    "The nurse is assessing a new ostomy and notes that",
    "A postoperative ostomy client reports concern because",
    "When planning ostomy care, which finding most directly supports",
    "A home-care nurse evaluates pouch fit after",
    "Which teaching point is most appropriate when",
    "The nurse reviews hydration needs after",
    "A client with a colostomy needs guidance because",
    "Which assessment priority applies when",
    "A learner compares ostomy care options after",
    "The care team should escalate concern when",
]

ISSUES = [
    "the pouch seal loosens near a skin fold",
    "the stoma appears dusky rather than moist red",
    "liquid ileostomy output increases over a day",
    "peristomal skin becomes red and painful",
    "the client has difficulty emptying the pouch",
    "odor concerns limit normal social activity",
    "the appliance leaks during routine movement",
    "a medication shell appears in pouch output",
    "the client avoids meals before leaving home",
    "mucocutaneous separation is suspected",
    "skin barrier sizing leaves exposed skin",
    "the client asks when to seek urgent help",
]

PATIENT_CONTEXTS = [
    "a client returning to work",
    "an older adult learning self-care",
    "a postoperative client preparing for discharge",
    "a school nurse supporting an adolescent",
    "a home-health client with limited supplies",
    "a client with a new ileostomy",
    "a client with a descending colostomy",
]

CARE_SETTINGS = [
    "During a morning appliance change",
    "At a follow-up clinic visit",
    "Before discharge teaching",
    "During a home-care assessment",
    "While reviewing pouching technique",
    "After a meal-planning discussion",
    "During postoperative rounds",
    "At a telephone triage call",
    "While teaching skin-barrier sizing",
    "During medication reconciliation",
    "At a psychosocial support visit",
]

ASSESSMENT_PRIORITIES = [
    "stoma color and moisture",
    "peristomal skin exposure",
    "output volume and consistency",
    "hydration status",
    "pouch seal integrity",
    "client return demonstration",
    "need for urgent escalation",
]

TEACHING_NEEDS = [
    "emptying frequency",
    "skin barrier fit",
    "fluid intake planning",
    "odor management",
    "medication absorption",
    "activity adaptation",
    "when to contact the care team",
]

SAFETY_CONCERNS = [
    "skin breakdown",
    "dehydration",
    "ischemia",
    "leakage-related injury",
    "obstruction symptoms",
    "infection risk",
    "delayed complication reporting",
]

STEM_TEMPLATES = [
    "{care_setting}, {patient_context} has {issue}. Which nursing response best addresses {assessment_priority}, {teaching_need}, and {safety_concern} in ostomy care case focus {variant}, barrier pattern {variant_two}, and teaching pathway {variant_three}?",
    "The nurse is planning ostomy teaching for {patient_context} after {issue}. Which action should be prioritized for {assessment_priority} and {safety_concern}?",
    "{patient_context} describes {issue} during an ostomy follow-up. What should the nurse assess first when the teaching need is {teaching_need}?",
    "While focusing on {category}, the care team notes {issue}. Which response best protects the client from {safety_concern}?",
    "{care_setting}, the nurse observes a concern related to {assessment_priority}. Which intervention best supports {patient_context} with ostomy care?",
    "A nursing student reviews {category} for {patient_context}. Which finding related to {issue} requires the most direct nursing response?",
    "When {patient_context} asks about {teaching_need}, which ostomy-care action best addresses {assessment_priority}?",
    "{care_setting}, {patient_context} needs help preventing {safety_concern}. Which option best matches the ostomy-care priority?",
    "The nurse compares possible responses to {issue}. Which choice best integrates {assessment_priority}, {teaching_need}, and safe ostomy management?",
    "{patient_context} is learning to manage an ostomy appliance. Which response is best when {issue} and {safety_concern} are present?",
    "During review of {category}, which nursing action should come first for {patient_context} when {assessment_priority} is abnormal?",
    "{care_setting}, which teaching response is most appropriate for {patient_context} who reports {issue}?",
    "A client scenario includes {issue}, concern for {safety_concern}, and a need for {teaching_need}. Which nursing response is most appropriate?",
    "Which ostomy-care decision best supports {patient_context} when the assessment priority is {assessment_priority}?",
    "The care plan for {patient_context} must address {issue}. Which response best reduces risk for {safety_concern}?",
    "A nurse is evaluating {category} after {patient_context} reports {issue}. Which action best supports safe ostomy care?",
]


def _alpha_token(number: int) -> str:
    letters = []
    value = number

    while value:
        value -= 1
        letters.append(chr(ord("a") + (value % 26)))
        value //= 26

    return "".join(reversed(letters)) or "a"


def _payload(question_count: int = 25, *, document_type: str = "Exam Prep") -> DocumentCreate:
    return DocumentCreate(
        title=LONG_TITLE,
        subject="Ostomy Care",
        education_level="Nursing School",
        document_type=document_type,
        target_platform="Stuvia",
        output_language="English",
        length="Short",
        template_id="exam_bundle_2026" if document_type == "Exam Prep" else "tpl_clean",
        question_count=question_count,
        generation_mode="GENERAL_KNOWLEDGE_DRAFT",
        difficulty="Mixed",
    )


def _option(label: str, text: str) -> dict:
    return {"label": label, "text": text}


def _question(number: int, *, stem: str | None = None, correct: str | None = None) -> dict:
    category = OSTOMY_CATEGORIES[(number - 1) % len(OSTOMY_CATEGORIES)]
    opening = OPENINGS[(number - 1) % len(OPENINGS)]
    issue = ISSUES[(number - 1) % len(ISSUES)]
    variant = f"case{_alpha_token(number)}"
    variant_two = f"barrier{_alpha_token(number + 300)}"
    variant_three = f"teaching{_alpha_token(number + 600)}"
    patient_context = PATIENT_CONTEXTS[(number - 1) % len(PATIENT_CONTEXTS)]
    care_setting = CARE_SETTINGS[(number - 1) % len(CARE_SETTINGS)]
    assessment_priority = ASSESSMENT_PRIORITIES[(number - 1) % len(ASSESSMENT_PRIORITIES)]
    teaching_need = TEACHING_NEEDS[(number - 1) % len(TEACHING_NEEDS)]
    safety_concern = SAFETY_CONCERNS[(number - 1) % len(SAFETY_CONCERNS)]
    answer_label = correct or ["A", "B", "C", "D"][(number - 1) % 4]
    answer_text = f"Assess {assessment_priority} for case focus {variant} and choose an ostomy-care intervention matched to {safety_concern}."
    options = {
        "A": f"Assess {assessment_priority} for case focus {variant} and protect skin integrity while addressing {issue}.",
        "B": f"Ignore {issue} for case focus {variant} until the next scheduled teaching visit.",
        "C": f"Change teaching about {teaching_need} for case focus {variant} without assessing the ostomy appliance.",
        "D": f"Delay ostomy-care assessment for case focus {variant} even if {safety_concern} worsens.",
    }
    options[answer_label] = answer_text
    stem_text = stem or STEM_TEMPLATES[(number - 1) % len(STEM_TEMPLATES)].format(
        care_setting=care_setting,
        patient_context=patient_context,
        issue=issue,
        assessment_priority=assessment_priority,
        teaching_need=teaching_need,
        safety_concern=safety_concern,
        variant=variant,
        variant_two=variant_two,
        variant_three=variant_three,
        category=category.lower(),
    )

    if stem is None and stem_text.endswith("?"):
        stem_text = stem_text[:-1] + f" for case focus {variant}, barrier pattern {variant_two}, and teaching pathway {variant_three}?"

    return {
        "number": number,
        "category": category,
        "learning_objective": f"Select a safe nursing response for {category.lower()}.",
        "difficulty": ["foundational", "intermediate", "advanced"][(number - 1) % 3],
        "question_type": "clinical_scenario",
        "stem": stem_text,
        "options": [_option(label, options[label]) for label in ["A", "B", "C", "D"]],
        "correct_option": answer_label,
        "rationale": (
            f"The best answer links the client's finding to {category.lower()} and prioritizes assessment, "
            f"skin protection, teaching about {teaching_need}, and timely escalation for case focus {variant} when {safety_concern} suggests a complication."
        ),
        "source_refs": [],
        "review_flags": [],
    }


def _topic_word_mismatch_question(number: int) -> dict:
    variant = f"pathway{_alpha_token(number + 900)}"
    focus_options = [
        ("orthostatic dizziness", "standing tolerance", "intake diary", "morning follow-up"),
        ("leg cramping", "electrolyte symptoms", "meal timing", "evening phone call"),
        ("dry mouth", "urine frequency", "fluid replacement", "clinic reassessment"),
        ("lightheadedness", "daily weights", "output log", "home-health visit"),
        ("fatigue", "pulse trend", "salt replacement", "discharge conference"),
        ("weakness", "skin turgor", "drink schedule", "triage review"),
        ("headache", "blood pressure change", "symptom diary", "skills check"),
        ("nausea", "hydration tolerance", "diet review", "same-day callback"),
        ("reduced urine", "mucosal dryness", "oral rehydration", "family teaching"),
        ("tachycardia", "volume status", "laboratory follow-up", "urgent review"),
        ("muscle weakness", "fluid deficit", "medication timing", "nurse-led visit"),
        ("confusion", "safety risk", "rapid escalation", "community follow-up"),
    ]
    symptom, assessment, intervention, setting = focus_options[(number - 1) % len(focus_options)]
    options = {
        "A": f"Assess {assessment}, review the output log, and begin {intervention} planning before completing the {variant} action plan.",
        "B": f"Delay assessment until the next scheduled visit even when {symptom} continues during the {setting}.",
        "C": f"Restrict oral intake immediately without reviewing output volume or symptoms in the {variant} scenario.",
        "D": f"Focus only on written instructions and avoid hands-on reassessment during the {setting}.",
    }

    return {
        "number": number,
        "category": f"Postoperative Hydration {variant}",
        "learning_objective": f"Select a safe nursing response when fluid losses and {symptom} occur in {variant}.",
        "difficulty": "intermediate",
        "question_type": "clinical_scenario",
        "stem": (
            f"During a {setting}, a postoperative client reports {symptom} after repeated watery output and asks about "
            f"{intervention} for the {variant} plan. Which nursing action is the safest priority?"
        ),
        "options": [_option(label, options[label]) for label in ["A", "B", "C", "D"]],
        "correct_option": "A",
        "rationale": (
            f"The safest response links {symptom} to {assessment}, verifies output pattern and symptoms, and then uses "
            f"{intervention} or escalation decisions for the {variant} scenario."
        ),
        "source_refs": [],
        "review_flags": [],
    }


def _question_content(count: int = 20) -> dict:
    return {
        "title_page": "Ostomy Care Practice Questions",
        "introduction": "",
        "sections": [],
        "key_points": [],
        "examples": [],
        "study_questions": [],
        "conclusion": "",
        "metadata": {
            "display_title": "Ostomy Care Practice Questions",
            "topic_label": "Ostomy Care",
            "review_required": True,
        },
        "question_bank": [_question(number) for number in range(1, count + 1)],
    }


def _pdf_text(content: dict, template_id: str | None = "exam_bundle_2026") -> str:
    with TemporaryDirectory() as tmp_dir:
        output_path = Path(tmp_dir) / "sample.pdf"
        render_study_document_pdf(content, template_id, output_path)
        return output_path.read_bytes().decode("latin-1", "ignore")


def _page_count_from_pdf_text(pdf_text: str) -> int:
    match = re.search(r"/Type /Pages /Count (\d+)", pdf_text)
    return int(match.group(1)) if match else 0


def _fake_blueprint(count: int) -> dict:
    base, remainder = divmod(count, 8)
    categories = []

    for index, category in enumerate(OSTOMY_CATEGORIES[:8]):
        categories.append(
            {
                "name": category,
                "learning_objectives": [f"Apply nursing judgment for {category.lower()}."],
                "planned_question_count": base + (1 if index < remainder else 0),
                "difficulty_distribution": {"foundational": 1, "intermediate": 1, "advanced": 1},
                "question_style_distribution": {"clinical_scenario": 1},
                "scenario_distribution": {"routine_care": 1},
            }
        )

    return {
        "topic_label": "Ostomy Care",
        "categories": categories,
        "concepts_that_must_not_be_repeated": ["same pouch leakage scenario"],
        "prohibited_meta_language": ["prompt", "user", "model", "generated document", "publishing", "export", "template"],
    }


def _fake_openai_response(payload: dict) -> dict:
    name = payload["text"]["format"]["name"]

    if name == "studymint_question_blueprint":
        requested = int(re.search(r"Requested question count: (\d+)", payload["input"]).group(1))
        return {"status": "completed", "output_text": __import__("json").dumps(_fake_blueprint(requested)), "usage": {"total_tokens": 10}}

    if name == "studymint_question_batch":
        numbers_text = re.search(r"Question numbers required: (\[[^\]]+\])", payload["input"]).group(1)
        numbers = ast.literal_eval(numbers_text)
        return {
            "status": "completed",
            "output_text": __import__("json").dumps({"questions": [_question(number) for number in numbers]}),
            "usage": {"total_tokens": 10},
        }

    raise AssertionError(f"Unexpected mocked OpenAI schema: {name}")


class GenerationArchitectureTests(unittest.TestCase):
    def test_renderer_purity_does_not_add_question_21(self) -> None:
        pdf_text = _pdf_text(_question_content(20))

        self.assertEqual(len(re.findall(r"Question \d+:", pdf_text)), 20)
        self.assertNotIn("Question 21:", pdf_text)

    def test_short_medium_long_do_not_force_fixed_pages(self) -> None:
        self.assertFalse(hasattr(pdf_renderer, "_target_pages_for_export"))
        self.assertFalse(hasattr(simple_pdf, "_pad_to_target_pages"))

        for _length in ["Short", "Medium", "Long"]:
            pdf_text = _pdf_text(_question_content(4))
            self.assertLess(_page_count_from_pdf_text(pdf_text), 120)

    def test_long_title_isolated_from_question_fields(self) -> None:
        brief = build_generation_brief(_payload(25))
        self.assertEqual(brief.topic_label, "Ostomy Care")
        self.assertEqual(brief.display_title, LONG_TITLE)

        questions = [QuestionItem.model_validate(_question(number)) for number in range(1, 26)]
        report = validate_question_bank(questions, brief)
        combined_questions = " ".join(
            [question.stem for question in questions]
            + [option.text for question in questions for option in question.options]
            + [question.rationale for question in questions]
            + [question.category for question in questions]
        )

        self.assertFalse(report.rejected)
        self.assertNotIn(LONG_TITLE.lower(), combined_questions.lower())

    def test_blueprint_schema_declares_distribution_objects_for_strict_openai_validation(self) -> None:
        category_schema = openai_client.BLUEPRINT_SCHEMA["properties"]["categories"]["items"]
        distribution_fields = [
            "difficulty_distribution",
            "question_style_distribution",
            "scenario_distribution",
        ]

        for field_name in distribution_fields:
            field_schema = category_schema["properties"][field_name]
            self.assertEqual(field_schema["type"], "object")
            self.assertIn("additionalProperties", field_schema)

    def test_blueprint_response_payload_uses_permissive_schema(self) -> None:
        brief = build_generation_brief(_payload(20))
        payload = openai_client._response_payload(
            "studymint_question_blueprint",
            "test",
            openai_client._blueprint_prompt(brief),
            openai_client.BLUEPRINT_SCHEMA,
            max_tokens=8000,
        )

        self.assertFalse(payload["text"]["format"]["strict"])
        self.assertEqual(payload["text"]["format"]["schema"], {"type": "object", "additionalProperties": True})

    def test_question_batch_response_payload_uses_fast_model_without_reasoning(self) -> None:
        payload = openai_client._response_payload(
            "studymint_question_batch",
            "test",
            "Question numbers required: [1]",
            openai_client.QUESTION_BATCH_SCHEMA,
            max_tokens=2000,
        )

        self.assertEqual(payload["model"], settings.OPENAI_FAST_MODEL)
        self.assertNotIn("reasoning", payload)

    def test_document_response_payload_uses_configured_document_model(self) -> None:
        with patch.object(openai_client.settings, "OPENAI_DOCUMENT_MODEL", "gpt-4.1-mini"):
            payload = openai_client._response_payload(
                "studymint_academic_document",
                "test",
                "Generate a document",
                openai_client.DOCUMENT_CONTENT_SCHEMA,
                max_tokens=2000,
            )

        self.assertEqual(payload["model"], "gpt-4.1-mini")

    def test_speed_mode_response_payload_uses_faster_profile(self) -> None:
        payload = openai_client._response_payload(
            "studymint_question_batch",
            "test",
            "Question numbers required: [1]",
            openai_client.QUESTION_BATCH_SCHEMA,
            max_tokens=2000,
            speed_mode=True,
        )

        self.assertEqual(payload["model"], settings.OPENAI_FAST_MODEL)
        self.assertNotIn("reasoning", payload)

    def test_speed_mode_uses_supported_verbosity_for_gpt_4_1_mini(self) -> None:
        with patch.object(openai_client.settings, "OPENAI_FAST_MODEL", "gpt-4.1-mini"):
            payload = openai_client._response_payload(
                "studymint_question_batch",
                "test",
                "Question numbers required: [1]",
                openai_client.QUESTION_BATCH_SCHEMA,
                max_tokens=2000,
                speed_mode=True,
            )

        self.assertEqual(payload["text"]["verbosity"], "medium")

    def test_default_question_batch_size_uses_schema_maximum_for_speed(self) -> None:
        self.assertEqual(settings.OPENAI_QUESTION_BATCH_SIZE, 25)

    def test_dynamic_question_batch_schema_allows_fast_stuvia_batches(self) -> None:
        schema = openai_client._question_batch_schema(30)

        self.assertEqual(schema["properties"]["questions"]["maxItems"], 30)
        self.assertEqual(openai_client.QUESTION_BATCH_SCHEMA["properties"]["questions"]["maxItems"], 25)

    def test_stuvia_speed_mode_uses_fast_question_bank_path(self) -> None:
        payload = DocumentCreate(
            title="Software-Defined Networking Objective Assessment Study Guide",
            subject="Software-Defined Networking",
            education_level="Professional Certification",
            document_type="Question Bank",
            target_platform="Stuvia",
            output_language="English",
            length="Medium",
            question_count=25,
            generation_mode="GENERAL_KNOWLEDGE_DRAFT",
            difficulty="Mixed",
            speed_mode=True,
        )

        with (
            patch.object(openai_client, "_generate_fast_question_bank", return_value=({"title_page": "Fast"}, {})) as fast,
            patch.object(openai_client, "_generate_question_bank") as standard,
        ):
            content, usage = openai_client.generate_document_with_openai(payload)

        self.assertEqual(content["title_page"], "Fast")
        self.assertEqual(usage, {})
        fast.assert_called_once()
        standard.assert_not_called()

    def test_document_read_model_preserves_generation_time(self) -> None:
        document = DocumentRead.model_validate(
            {
                "id": "doc-1",
                "tenant_id": "tenant-1",
                "owner_id": "user-1",
                "title": "Sample",
                "subject": "Biology",
                "education_level": "Undergraduate",
                "document_type": "Study Notes",
                "target_platform": "Stuvia",
                "output_language": "English",
                "length": "Short",
                "status": "READY_FOR_REVIEW",
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
                "generation_time_seconds": 42,
            }
        )

        self.assertEqual(document.generation_time_seconds, 42)

    def test_coerce_blueprint_payload_handles_malformed_openai_output(self) -> None:
        coerced = openai_client._coerce_blueprint_payload(
            {
                "topic_label": "Nursing",
                "categories": [
                    {
                        "name": "Assessment",
                        "learning_objectives": ["Evaluate clients"],
                        "planned_question_count": "5",
                    }
                ],
            },
            requested_question_count=5,
        )

        self.assertEqual(coerced["topic_label"], "Nursing")
        self.assertEqual(coerced["categories"][0]["planned_question_count"], 5)

    def test_synthesize_missing_batch_questions_adds_fallback_questions(self) -> None:
        brief = build_generation_brief(_payload(3))
        blueprint = ContentBlueprint(topic_label="Ostomy Care", categories=[ContentBlueprint.model_fields["categories"].annotation.__args__[0](name="Assessment", learning_objectives=["Assess care"], planned_question_count=3)])
        selected = [QuestionItem.model_validate(_question(1))]
        synthesized = openai_client._synthesize_missing_batch_questions(brief, blueprint, selected, [1, 2, 3])

        self.assertEqual([question.number for question in synthesized], [1, 2, 3])
        self.assertEqual(len(synthesized), 3)
        self.assertIn(synthesized[1].correct_option, {"A", "B", "C", "D"})

    def test_synthesize_missing_batch_questions_produces_valid_fallback_questions(self) -> None:
        brief = build_generation_brief(_payload(4))
        blueprint = ContentBlueprint(topic_label="Ostomy Care", categories=[ContentBlueprint.model_fields["categories"].annotation.__args__[0](name="Assessment", learning_objectives=["Assess care"], planned_question_count=4)])
        selected = [QuestionItem.model_validate(_question(1))]
        synthesized = openai_client._synthesize_missing_batch_questions(brief, blueprint, selected, [1, 2, 3, 4])

        report = validate_question_bank(synthesized, brief)

        self.assertFalse(report.rejected)
        self.assertEqual([question.number for question in synthesized], [1, 2, 3, 4])

    def test_prohibited_generic_filler_is_rejected(self) -> None:
        brief = build_generation_brief(_payload(1))
        bad = QuestionItem.model_validate(
            _question(
                1,
                stem="Which option best helps define the objective, inputs, constraints, and export packaging before publishing?",
            )
        )
        report = validate_question_bank([bad], brief)

        self.assertIn("META_LANGUAGE", report.issue_codes)
        self.assertTrue(report.rejected)

    def test_exact_question_counts_with_mocked_batches(self) -> None:
        for count in [25, 50, 100, 270]:
            with self.subTest(count=count):
                with patch.object(openai_client, "_post_response", side_effect=_fake_openai_response):
                    content, _usage = generate_document_with_openai(_payload(count))

                numbers = [question["number"] for question in content["question_bank"]]
                self.assertEqual(len(numbers), count)
                self.assertEqual(numbers, list(range(1, count + 1)))
                self.assertEqual(content["metadata"]["quality_summary"]["requested_question_count"], count)
                self.assertEqual(content["metadata"]["quality_summary"]["generated_question_count"], count)

    def test_invalid_batch_question_is_repaired_without_discarding_valid_questions(self) -> None:
        batch_calls: list[list[int]] = []

        def fake_response(payload: dict) -> dict:
            name = payload["text"]["format"]["name"]

            if name == "studymint_question_blueprint":
                requested = int(re.search(r"Requested question count: (\d+)", payload["input"]).group(1))
                return {
                    "status": "completed",
                    "output_text": __import__("json").dumps(_fake_blueprint(requested)),
                    "usage": {"total_tokens": 10},
                }

            if name == "studymint_question_batch":
                numbers_text = re.search(r"Question numbers required: (\[[^\]]+\])", payload["input"]).group(1)
                numbers = ast.literal_eval(numbers_text)
                batch_calls.append(numbers)
                questions = [_question(number) for number in numbers]
                if len(batch_calls) == 1:
                    questions[0]["stem"] = "Which template export setting should be selected before publishing the generated document?"
                return {
                    "status": "completed",
                    "output_text": __import__("json").dumps({"questions": questions}),
                    "usage": {"total_tokens": 10},
                }

            raise AssertionError(f"Unexpected mocked OpenAI schema: {name}")

        with patch.object(openai_client, "_post_response", side_effect=fake_response):
            content, _usage = generate_document_with_openai(_payload(25))

        self.assertEqual(batch_calls, [list(range(1, 26)), [1]])
        self.assertEqual([question["number"] for question in content["question_bank"]], list(range(1, 26)))

    def test_duplicate_rejection_detects_near_duplicate_stems(self) -> None:
        brief = build_generation_brief(_payload(2))
        first = QuestionItem.model_validate(_question(1, stem="A client with an ileostomy reports increasing watery output and dizziness. Which nursing action is best?"))
        second = QuestionItem.model_validate(_question(2, stem="A client with an ileostomy reports watery output, dizziness, and weakness. Which nursing action is best?"))
        report = validate_question_bank([first, second], brief)

        self.assertIn("DUPLICATE_OR_NEAR_DUPLICATE_STEM", report.issue_codes)

    def test_topic_relevance_rejects_document_production_questions(self) -> None:
        brief = build_generation_brief(_payload(1))
        bad = QuestionItem.model_validate(
            _question(1, stem="Which template export setting should be selected before publishing the generated document?")
        )
        report = validate_question_bank([bad], brief)

        self.assertIn("META_LANGUAGE", report.issue_codes)
        self.assertTrue(report.rejected)

    def test_topic_word_mismatch_is_not_a_hard_rejection(self) -> None:
        brief = build_generation_brief(_payload(1))
        question = QuestionItem.model_validate(_topic_word_mismatch_question(1))
        report = validate_question_bank([question], brief)

        self.assertFalse(report.rejected)
        self.assertNotIn("TOPIC_DRIFT", report.issue_codes)

    def test_batch_accepts_academic_questions_without_exact_topic_word_overlap(self) -> None:
        batch_calls: list[list[int]] = []

        def fake_response(payload: dict) -> dict:
            name = payload["text"]["format"]["name"]

            if name == "studymint_question_blueprint":
                requested = int(re.search(r"Requested question count: (\d+)", payload["input"]).group(1))
                return {
                    "status": "completed",
                    "output_text": __import__("json").dumps(_fake_blueprint(requested)),
                    "usage": {"total_tokens": 10},
                }

            if name == "studymint_question_batch":
                numbers_text = re.search(r"Question numbers required: (\[[^\]]+\])", payload["input"]).group(1)
                numbers = ast.literal_eval(numbers_text)
                batch_calls.append(numbers)
                questions = [
                    _topic_word_mismatch_question(number) if number in {4, 8, 24} else _question(number)
                    for number in numbers
                ]
                return {
                    "status": "completed",
                    "output_text": __import__("json").dumps({"questions": questions}),
                    "usage": {"total_tokens": 10},
                }

            raise AssertionError(f"Unexpected mocked OpenAI schema: {name}")

        with patch.object(openai_client, "_post_response", side_effect=fake_response):
            content, _usage = generate_document_with_openai(_payload(25))

        self.assertEqual(batch_calls, [list(range(1, 26))])
        self.assertEqual([question["number"] for question in content["question_bank"]], list(range(1, 26)))

    def test_option_and_answer_integrity(self) -> None:
        brief = build_generation_brief(_payload(1))
        raw = _question(1)
        raw["options"][1]["text"] = raw["options"][0]["text"]
        raw["correct_option"] = "E"

        with self.assertRaises(ValidationError):
            QuestionItem.model_validate(raw)

        raw = _question(1)
        raw["options"][1]["text"] = raw["options"][0]["text"]
        raw["correct_option"] = "A"
        report = validate_question_bank([QuestionItem.model_validate(raw)], brief)

        self.assertIn("DUPLICATE_OPTIONS", report.issue_codes)

    def test_pdf_text_quality_title_once_page_numbers_and_smart_quotes(self) -> None:
        content = _question_content(5)
        content["question_bank"][0]["stem"] = "A client\u2019s pouch leaks during teaching. Which response is best?"
        pdf_text = _pdf_text(content)

        self.assertEqual(pdf_text.upper().count("OSTOMY CARE PRACTICE QUESTIONS"), 1)
        self.assertIn("Page 1 of", pdf_text)
        self.assertIn("client's pouch", pdf_text)
        self.assertNotIn("client?s pouch", pdf_text)
        self.assertEqual(len(re.findall(r"Question \d+:", pdf_text)), 5)

    def test_standard_document_renderer_does_not_insert_generic_blocks(self) -> None:
        content = {
            "title_page": "Business Law Study Notes",
            "introduction": "Business law introduces rules that shape commercial obligations.",
            "sections": [
                {
                    "id": "contracts",
                    "title": "Contract Formation",
                    "body": "A valid contract usually depends on offer, acceptance, consideration, and capacity.",
                }
            ],
            "key_points": [],
            "examples": [],
            "study_questions": [],
            "conclusion": "Contract concepts should be reviewed with course materials.",
        }
        pdf_text = _pdf_text(content, "tpl_clean")

        self.assertIn("Contract Formation", pdf_text)
        self.assertNotIn("Professional overview", pdf_text)
        self.assertNotIn("Quality checks", pdf_text)

    def test_stuvia_topic_extractor_ranks_profile_title_signals(self) -> None:
        html = """
        <html>
          <head><title>casewritters - Stuvia</title></head>
          <body>
            <a title="HESI RN Exit Exam 2026 Practice Questions with Rationales">Open</a>
            <h2>NURS 6512 Advanced Health Assessment Final Exam Study Guide</h2>
            <span>Login</span>
          </body>
        </html>
        """
        candidates = stuvia_agent_service._extract_topics_from_html(html)
        ranked = stuvia_agent_service._rank_topics_heuristic(candidates, "https://www.stuvia.com/user/casewritters", 2)

        self.assertEqual(len(ranked), 2)
        self.assertTrue(any("HESI" in item["title"] or "HESI" in item["topic"] for item in ranked))
        self.assertFalse(any(item["topic"].lower() == "login" for item in ranked))

    def test_stuvia_topic_extractor_rejects_viewport_metadata(self) -> None:
        html = """
        <html>
          <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <meta property="og:title" content="NR566 Advanced Pharmacology Week 4 Midterm Study Guide">
          </head>
          <body>
            <h2>NURS 6512 Advanced Health Assessment Final Exam Study Guide</h2>
          </body>
        </html>
        """
        candidates = stuvia_agent_service._extract_topics_from_html(html)

        self.assertFalse(stuvia_agent_service._is_topic_candidate("width=device-width, initial-scale=1.0"))
        self.assertNotIn("width=device-width, initial-scale=1.0", candidates)
        self.assertIn("NR566 Advanced Pharmacology Week 4 Midterm Study Guide", candidates)

    def test_stuvia_cached_topic_filter_rejects_metadata_noise(self) -> None:
        self.assertFalse(
            stuvia_agent_service._valid_stuvia_topic_record(
                {
                    "title": "width=device-width, initial-scale=1.0 Study Guide",
                    "topic": "width=device-width, initial-scale=1.0",
                }
            )
        )
        self.assertFalse(
            stuvia_agent_service._valid_stuvia_topic_record(
                {
                    "title": "© Stuvia International BV 2010-2026 Study Guide",
                    "topic": "© Stuvia International BV",
                }
            )
        )
        self.assertTrue(
            stuvia_agent_service._valid_stuvia_topic_record(
                {
                    "title": "NURS 6512 Advanced Health Assessment Final Exam Study Guide",
                    "topic": "NURS 6512 Advanced Health Assessment",
                }
            )
        )

    def test_stuvia_topic_filter_rejects_social_link_noise(self) -> None:
        self.assertFalse(stuvia_agent_service._is_topic_candidate("TikTok Link"))
        self.assertFalse(stuvia_agent_service._is_topic_candidate("TikTok Link Study Guide"))
        self.assertFalse(stuvia_agent_service._is_topic_candidate("Citation Generator Study Guide"))
        self.assertFalse(stuvia_agent_service._is_topic_candidate("Satisfaction guarantee Study Guide"))
        self.assertFalse(stuvia_agent_service._is_topic_candidate("Frequently asked Questions"))
        self.assertFalse(
            stuvia_agent_service._valid_stuvia_topic_record(
                {
                    "title": "Instagram Link Study Guide",
                    "topic": "Instagram Link",
                }
            )
        )
        self.assertFalse(
            stuvia_agent_service._valid_stuvia_topic_record(
                {
                    "title": "Citation Generator Study Guide",
                    "topic": "Citation Generator",
                }
            )
        )
        self.assertFalse(
            stuvia_agent_service._valid_stuvia_topic_record(
                {
                    "title": "Satisfaction guarantee Study Guide",
                    "topic": "Satisfaction guarantee",
                }
            )
        )
        self.assertFalse(
            stuvia_agent_service._valid_stuvia_topic_record(
                {
                    "title": "Frequently asked Questions",
                    "topic": "Frequently asked",
                }
            )
        )

    def test_stuvia_profile_extractor_prefers_document_links(self) -> None:
        html = """
        <html>
          <body>
            <a href="/doc/123/nr566-advanced-pharmacology-week-4-midterm">NR566 Advanced Pharmacology for Care of the Family Week 4 Midterm</a>
            <a href="/user/casewritters">TikTok Link</a>
            <h2>TikTok Link</h2>
            <p>Follow writer on Instagram Link</p>
          </body>
        </html>
        """
        candidates = stuvia_agent_service._extract_topics_from_html(html, "https://www.stuvia.com/user/casewritters")

        self.assertEqual(candidates, ["NR566 Advanced Pharmacology for Care of the Family Week 4 Midterm"])

    def test_stuvia_profile_extractor_only_uses_document_links(self) -> None:
        html = """
        <html>
          <head>
            <meta property="og:title" content="Citation Generator - Stuvia">
          </head>
          <body>
            <h2>Citation Generator Study Guide</h2>
            <a href="/citation-generator">Citation Generator</a>
            <a href="/login">Login</a>
          </body>
        </html>
        """
        candidates = stuvia_agent_service._extract_topics_from_html(html, "https://www.stuvia.com/user/casewritters")

        self.assertEqual(candidates, [])

    def test_stuvia_scraper_follows_relevant_profile_links(self) -> None:
        pages = {
            "https://www.stuvia.com/user/casewritters": """
                <a href="/doc/123/nr566-advanced-pharmacology-week-4-midterm">NR566 Advanced Pharmacology for Care of the Family Week 4 Midterm</a>
                <a href="https://www.stuvia.com/user/casewritters?page=2">Next</a>
            """,
            "https://www.stuvia.com/doc/123/nr566-advanced-pharmacology-week-4-midterm": """
                <h1>NR566 Advanced Pharmacology for Care of the Family Week 4 Midterm 100 Actual Questions</h1>
            """,
            "https://www.stuvia.com/user/casewritters?page=2": """
                <h2>Citation Generator Study Guide</h2>
                <a href="/doc/456/wgu-psych-d094-objective-assessment">WGU PSYCH D094 Objective Assessment Complete Solutions Latest Update</a>
            """,
            "https://www.stuvia.com/doc/456/wgu-psych-d094-objective-assessment": """
                <h1>WGU PSYCH D094 Objective Assessment Complete Solutions Latest Update</h1>
            """,
        }

        def fake_fetch(url: str) -> str:
            return pages.get(url, "")

        with (
            patch.object(settings, "STUVIA_SCRAPE_PAGE_LIMIT", 4),
            patch.object(stuvia_agent_service, "_fetch_url", side_effect=fake_fetch),
            patch.object(settings, "OPENAI_API_KEY", ""),
        ):
            topics = stuvia_agent_service.discover_stuvia_topics("https://www.stuvia.com/user/casewritters", [], 5)

        joined = " ".join(item["title"] for item in topics)
        self.assertIn("NR566", joined)
        self.assertIn("WGU PSYCH D094", joined)

    def test_stuvia_profile_url_guard_rejects_non_stuvia_hosts(self) -> None:
        with self.assertRaises(HTTPException):
            stuvia_agent_service._validate_stuvia_profile_url("https://example.com/user/casewritters")

    def test_stuvia_agent_openai_preflight_uses_docker_dev_message(self) -> None:
        with patch.object(settings, "OPENAI_API_KEY", ""):
            with self.assertRaises(HTTPException) as context:
                stuvia_agent_service._ensure_generation_configured()

        self.assertEqual(context.exception.status_code, 503)
        self.assertIn("workspace root .env", str(context.exception.detail))

    def test_stuvia_topic_history_only_tracks_successful_generations(self) -> None:
        topics = [
            {
                "title": "HESI RN Exit Exam Practice Question Bank",
                "topic": "HESI RN Exit",
            },
            {
                "title": "NURS 6512 Advanced Health Assessment Study Guide",
                "topic": "NURS 6512 Advanced Health Assessment",
            },
        ]
        listings = [
            {
                "title": "Generated HESI RN Exit Practice Questions",
                "topic": "HESI RN Exit",
                "status": "ready_for_review",
            },
            {
                "title": "NURS 6512 Advanced Health Assessment Study Guide",
                "topic": "NURS 6512 Advanced Health Assessment",
                "status": "failed",
            },
        ]

        selected = stuvia_agent_service._topics_for_successful_listings(topics, listings)

        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["topic"], "HESI RN Exit")

    def test_stuvia_agent_retries_timed_out_generation_before_failing_listing(self) -> None:
        topics = [
            {"title": "Topic A Study Guide", "topic": "Topic A"},
            {"title": "Topic B Study Guide", "topic": "Topic B"},
        ]
        calls: list[tuple[str, int]] = []

        def fake_generate(
            run_id: str,
            payload: StuviaAgentRunCreate,
            user_id: str,
            topic: dict,
            index: int,
            total: int,
            attempt: int = 1,
        ) -> dict:
            calls.append((topic["topic"], attempt))
            if topic["topic"] == "Topic B" and attempt == 1:
                raise HTTPException(status_code=502, detail="OpenAI API request timed out")
            return {
                "title": topic["title"],
                "topic": topic["topic"],
                "document_id": f"doc-{index}",
                "document_url": f"http://localhost/doc-{index}",
                "status": "ready_for_review",
                "attempts": attempt,
            }

        payload = StuviaAgentRunCreate(
            profile_url="https://www.stuvia.com/user/casewritters",
            max_topics=2,
            concurrency=3,
        )

        with (
            patch.object(settings, "STUVIA_AGENT_MAX_CONCURRENCY", 3),
            patch.object(settings, "STUVIA_AGENT_GENERATION_ATTEMPTS", 2),
            patch.object(settings, "STUVIA_AGENT_RECOVERY_CONCURRENCY", 1),
            patch.object(settings, "STUVIA_AGENT_RETRY_BACKOFF_SECONDS", 0),
            patch.object(stuvia_agent_service, "_generate_listing_for_topic", side_effect=fake_generate),
            patch.object(stuvia_agent_service, "_update_run"),
        ):
            listings = stuvia_agent_service._generate_documents("run-1", payload, "user-1", topics)

        self.assertFalse(any(listing["status"] == "failed" for listing in listings))
        self.assertEqual(next(listing for listing in listings if listing["topic"] == "Topic B")["attempts"], 2)
        self.assertIn(("Topic B", 2), calls)

    def test_stuvia_agent_accepts_concurrency_ten(self) -> None:
        payload = StuviaAgentRunCreate(
            profile_url="https://www.stuvia.com/user/casewritters",
            concurrency=10,
        )

        self.assertEqual(payload.concurrency, 10)

    def test_stuvia_document_title_preserves_exact_scraped_title(self) -> None:
        title = stuvia_agent_service._stuvia_document_title(
            "Medical-Surgical Nursing Exam Preparation Resources",
            "12345678-90ab-cdef-1234-567890abcdef",
        )

        self.assertEqual(title, "Medical-Surgical Nursing Exam Preparation Resources")

    def test_stuvia_n8n_handoff_failure_is_not_success(self) -> None:
        review_payload = StuviaAgentRunCreate(
            profile_url="https://www.stuvia.com/user/casewritters",
            publish_mode="n8n_review",
        )
        drafts_payload = StuviaAgentRunCreate(
            profile_url="https://www.stuvia.com/user/casewritters",
            publish_mode="drafts_only",
        )

        self.assertTrue(stuvia_agent_service._n8n_handoff_succeeded(review_payload, "sent:200"))
        self.assertTrue(stuvia_agent_service._n8n_handoff_succeeded(review_payload, "publisher:queued"))
        self.assertTrue(stuvia_agent_service._n8n_handoff_succeeded(drafts_payload, "drafts_only"))
        self.assertFalse(stuvia_agent_service._n8n_handoff_succeeded(review_payload, "failed:HTTP Error 404: Not Found"))
        self.assertIn(
            "publishing workflow failed",
            stuvia_agent_service._n8n_handoff_failure_message(review_payload, "failed:HTTP Error 404: Not Found"),
        )

    def test_stuvia_manual_publish_payload_requests_private_publisher(self) -> None:
        document = SimpleNamespace(
            id="doc-123",
            tenant_id="tenant-123",
            title="Medical-Surgical Nursing Exam Preparation - abc12345",
            subject="Medical-Surgical Nursing",
        )
        connection = {
            "stuvia_credential_name": "Tenant Stuvia Account",
            "browser_publisher_url": "http://stuvia-publisher:8787/publish",
        }

        payload = stuvia_agent_service._manual_publish_payload("manual-run-1", document, connection)

        self.assertEqual(payload["run_id"], "manual-run-1")
        self.assertEqual(payload["publish_mode"], "manual_publish")
        self.assertTrue(payload["manual_publish_requested"])
        self.assertTrue(payload["auto_publish_requested"])
        self.assertFalse(payload["review_required"])
        self.assertIn("/integrations/stuvia/internal-credentials/tenant-123", payload["credential_lookup_url"])
        self.assertEqual(payload["listings"][0]["document_id"], "doc-123")
        self.assertEqual(payload["listings"][0]["status"], "manual_publish_requested")

    def test_stuvia_handoff_preserves_configured_publisher_service_url(self) -> None:
        previous_url = stuvia_agent_service.settings.STUVIA_BROWSER_PUBLISHER_URL
        try:
            stuvia_agent_service.settings.STUVIA_BROWSER_PUBLISHER_URL = ""
            self.assertEqual(
                stuvia_agent_service._configured_browser_publisher_url(
                    {"browser_publisher_url": "http://stuvia-publisher:8787/publish"}
                ),
                "http://stuvia-publisher:8787/publish",
            )
            self.assertEqual(
                stuvia_agent_service._configured_browser_publisher_url(
                    {"browser_publisher_url": "http://backend:8000/api/v1/stuvia-agent/publisher/handoff"}
                ),
                "",
            )
            self.assertEqual(
                stuvia_agent_service._configured_browser_publisher_url(
                    {"browser_publisher_url": "http://localhost:8787/publish"}
                ),
                "",
            )
        finally:
            stuvia_agent_service.settings.STUVIA_BROWSER_PUBLISHER_URL = previous_url

    def test_stuvia_handoff_prefers_backend_publisher_url(self) -> None:
        previous_url = stuvia_agent_service.settings.STUVIA_BROWSER_PUBLISHER_URL
        try:
            stuvia_agent_service.settings.STUVIA_BROWSER_PUBLISHER_URL = "http://stuvia-publisher:8787/publish"
            self.assertEqual(
                stuvia_agent_service._configured_browser_publisher_url(
                    {"browser_publisher_url": "http://localhost:8787/publish"}
                ),
                "http://stuvia-publisher:8787/publish",
            )
        finally:
            stuvia_agent_service.settings.STUVIA_BROWSER_PUBLISHER_URL = previous_url

    def test_stuvia_password_secret_round_trip_is_encrypted(self) -> None:
        encrypted = encrypt_secret("seller-password")

        self.assertNotEqual(encrypted, "seller-password")
        self.assertTrue(encrypted.startswith("fernet:v1:"))
        self.assertEqual(decrypt_secret(encrypted), "seller-password")
        self.assertEqual(decrypt_secret("not-a-valid-token"), "")

    def test_stuvia_direct_publisher_uses_backend_shared_token(self) -> None:
        self.assertEqual(
            stuvia_agent_service._publisher_auth_token({"n8n_webhook_token": "tenant-workflow-token"}),
            settings.N8N_STUVIA_WEBHOOK_TOKEN.strip() or "tenant-workflow-token",
        )

        captured: dict[str, str | int | None] = {}

        class FakeResponse:
            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
                return None

            def read(self) -> bytes:
                return b'{"status":"queued"}'

        def fake_urlopen(request: object, timeout: int) -> FakeResponse:
            captured["authorization"] = request.get_header("Authorization")  # type: ignore[attr-defined]
            captured["timeout"] = timeout
            return FakeResponse()

        with (
            patch.object(settings, "N8N_STUVIA_WEBHOOK_TOKEN", "backend-shared-token"),
            patch.object(stuvia_agent_service.urllib.request, "urlopen", side_effect=fake_urlopen),
        ):
            result = stuvia_agent_service._send_browser_publisher_payload(
                "http://stuvia-publisher:8787/publish/async",
                stuvia_agent_service._publisher_auth_token({"n8n_webhook_token": "tenant-workflow-token"}),
                {"run_id": "run-1", "listings": []},
            )

        self.assertEqual(result, "publisher:queued")
        self.assertEqual(captured["authorization"], "Bearer backend-shared-token")

    def test_stuvia_topic_filter_skips_used_and_duplicate_topics(self) -> None:
        used_keys = stuvia_topic_identity_keys(
            {
                "title": "HESI RN Exit Exam Practice Question Bank",
                "topic": "HESI RN Exit",
            }
        )
        topics = [
            {
                "title": "HESI RN Exit Exam Practice Question Bank",
                "topic": "HESI RN Exit",
            },
            {
                "title": "NURS 6512 Advanced Health Assessment Study Guide",
                "topic": "NURS 6512 Advanced Health Assessment",
            },
            {
                "title": "NURS 6512 Advanced Health Assessment Final Notes",
                "topic": "NURS 6512 Advanced Health Assessment",
            },
        ]

        selected = filter_new_stuvia_topic_candidates(topics, used_keys, 3)

        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["topic"], "NURS 6512 Advanced Health Assessment")

    def test_stuvia_topic_filter_does_not_overblock_broad_topic_labels(self) -> None:
        used_keys = stuvia_topic_identity_keys(
            {
                "title": "Nursing and Healthcare Certification Exam Preparation",
                "topic": "Nursing and Healthcare Certification",
            }
        )
        topics = [
            {
                "title": "Advanced Pharmacology Certification Exam Preparation",
                "topic": "Nursing and Healthcare Certification",
            },
            {
                "title": "Medical-Surgical Nursing Certification Practice Bank",
                "topic": "Nursing and Healthcare Certification",
            },
        ]

        selected = filter_new_stuvia_topic_candidates(topics, used_keys, 2)

        self.assertEqual(len(selected), 2)

    def test_stuvia_agent_preserves_exact_scraped_title(self) -> None:
        scraped_title = "NUR 265 / NUR265 1 ADVANCED CONCEPTS IN MEDICAL-SURGICAL NURSING"
        topics = stuvia_agent_service._rank_topics_heuristic([scraped_title], "https://www.stuvia.com/user/casewritters", 1)

        self.assertEqual(topics[0]["title"], scraped_title)

        version = SimpleNamespace(version_number=1, content={"title_page": "Generated rewrite", "metadata": {}})
        document = SimpleNamespace(id="46110ee6-695f-4047-ac00-04a25ee9c6ac", title="Generated rewrite", versions=[version])
        final_title = stuvia_agent_service._rename_stuvia_document_for_listing(document, topics[0])

        self.assertEqual(final_title, scraped_title)
        self.assertEqual(document.title, scraped_title)
        self.assertEqual(version.content["title_page"], scraped_title)
        self.assertEqual(version.content["metadata"]["stuvia_source_title"], scraped_title)

    def test_stuvia_pdf_filename_uses_first_four_title_words_and_uuid(self) -> None:
        document = SimpleNamespace(
            id="46110ee6-695f-4047-ac00-04a25ee9c6ac",
            title="NUR 265 Advanced Concepts in Medical Surgical Nursing",
        )

        self.assertEqual(
            stuvia_agent_service._document_pdf_filename(document),
            "nur-265-advanced-concepts-46110ee6.pdf",
        )


if __name__ == "__main__":
    unittest.main()
