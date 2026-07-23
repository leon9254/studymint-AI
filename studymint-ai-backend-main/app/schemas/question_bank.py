from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


GenerationMode = Literal["SOURCE_GROUNDED", "GENERAL_KNOWLEDGE_DRAFT"]
DifficultyMode = Literal["Mixed", "Foundational", "Intermediate", "Advanced"]
QuestionType = Literal["conceptual", "application", "clinical_scenario", "case_scenario", "calculation", "definition"]
DifficultyLevel = Literal["foundational", "intermediate", "advanced"]


class QuestionOption(BaseModel):
    label: Literal["A", "B", "C", "D"]
    text: str = Field(min_length=1, max_length=500)


class QuestionItem(BaseModel):
    number: int = Field(ge=1)
    category: str = Field(min_length=1, max_length=160)
    learning_objective: str = Field(min_length=1, max_length=300)
    difficulty: DifficultyLevel = "intermediate"
    question_type: QuestionType = "application"
    stem: str = Field(min_length=1, max_length=1200)
    options: list[QuestionOption] = Field(min_length=4, max_length=4)
    correct_option: Literal["A", "B", "C", "D"]
    rationale: str = Field(min_length=1, max_length=1600)
    source_refs: list[str] = Field(default_factory=list)
    review_flags: list[str] = Field(default_factory=list)


class GenerationBrief(BaseModel):
    display_title: str
    topic_label: str
    subject: str
    education_level: str
    document_type: str
    language: str
    requested_question_count: int
    generation_mode: GenerationMode
    user_instructions: str = ""
    supplied_source_text: str = ""
    factual_risk_level: Literal["low", "medium", "high"]
    target_learner: str
    preferred_difficulty_distribution: DifficultyMode = "Mixed"
    review_required: bool = True


class BlueprintCategory(BaseModel):
    name: str
    learning_objectives: list[str]
    planned_question_count: int = Field(ge=0)
    difficulty_distribution: dict[str, int] = Field(default_factory=dict)
    question_style_distribution: dict[str, int] = Field(default_factory=dict)
    scenario_distribution: dict[str, int] = Field(default_factory=dict)


class ContentBlueprint(BaseModel):
    topic_label: str
    categories: list[BlueprintCategory] = Field(min_length=1, max_length=20)
    concepts_that_must_not_be_repeated: list[str] = Field(default_factory=list)
    prohibited_meta_language: list[str] = Field(default_factory=list)


class QualitySummary(BaseModel):
    requested_question_count: int = 0
    generated_question_count: int = 0
    duplicate_questions_rejected: int = 0
    questions_repaired: int = 0
    generation_mode: GenerationMode = "GENERAL_KNOWLEDGE_DRAFT"
    review_required: bool = True
    issue_codes: list[str] = Field(default_factory=list)
