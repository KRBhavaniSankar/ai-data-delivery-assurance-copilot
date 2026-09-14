from typing import Literal
from pydantic import BaseModel, Field


class RequirementInput(BaseModel):
    requirement_id: str = "REQ-001"
    title: str
    business_requirement: str


class Ambiguity(BaseModel):
    ambiguity_id: str
    question: str
    impact: list[str]
    blocking: bool = True
    options: list[str] = Field(min_length=2)


class RequirementAnalysis(BaseModel):
    requirement_id: str
    extracted_entities: list[str]
    extracted_metrics: list[str]
    extracted_constraints: list[str]
    ambiguities: list[Ambiguity]
    status: Literal["CLARIFICATION_REQUIRED", "READY_FOR_SPEC"]


class ClarificationAnswer(BaseModel):
    requirement_id: str
    ambiguity_id: str
    selected_option: str
    approved_by: str = "BUSINESS_OWNER"


class ClarificationState(BaseModel):
    answers: list[ClarificationAnswer] = []


class SpecificationMetadata(BaseModel):
    specification_id: str
    version: str
    status: Literal["DRAFT", "PENDING_APPROVAL", "APPROVED"]
    domain: str
    title: str
    grain: str


class Scope(BaseModel):
    in_scope: list[str]
    out_of_scope: list[str]


class TargetDataModel(BaseModel):
    grain: str
    columns: list[str]
    uniqueness: str


class DESDD(BaseModel):
    specification_metadata: SpecificationMetadata
    business_context: list[str]
    requirement: list[str]
    scope: Scope
    business_glossary: list[str]
    data_context: list[str]
    target_data_model: TargetDataModel
    source_to_target_mapping: list[str]
    business_rules: list[str]
    transformation_rules: list[str]
    data_quality_rules: list[str]
    reconciliation_rules: list[str]
    edge_cases: list[str]
    test_scenarios: list[str]
    data_security_sensitivity: list[str]
    non_functional_data_requirements: list[str]
    dependencies: list[str]
    assumptions: list[str]
    open_questions_clarifications: list[str]
    acceptance_criteria: list[str]
    traceability: list[str]
