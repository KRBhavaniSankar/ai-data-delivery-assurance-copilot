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

class CatalogColumn(BaseModel):
    name: str
    type: str
    description: str

class CatalogDataset(BaseModel):
    table_name: str
    description: str
    primary_key: list[str]
    columns: list[CatalogColumn]
    relationships: list[str] = []
    sensitivity: str = "Internal"
    relevance: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"

class Evidence(BaseModel):
    evidence_type: Literal["CATALOG", "RAG"]
    source: str
    detail: str

class DiscoveredDataset(BaseModel):
    table_name: str
    relevance: Literal["HIGH", "MEDIUM", "LOW"]
    reason: str
    evidence: list[Evidence]

class DiscoveredMapping(BaseModel):
    target_field: str
    source_expression: str
    mapping_type: Literal["DIRECT", "REFERENCE", "DERIVED", "UNRESOLVED"]
    rule: str
    status: Literal["RESOLVED", "REQUIRES_CLARIFICATION"]
    evidence: list[Evidence]

class DataDiscoveryResult(BaseModel):
    requirement_id: str
    sdd_version: str
    datasets: list[DiscoveredDataset]
    mappings: list[DiscoveredMapping]
    knowledge_hits: list[Evidence]
    unresolved_items: list[str]
    engine: str = "mock-catalog + llamaindex/qdrant"

class SyntheticDatasetSummary(BaseModel):
    dataset_name: str
    file_name: str
    row_count: int
    columns: list[str]


class SyntheticDataResult(BaseModel):
    requirement_id: str
    sdd_version: str
    status: Literal["GENERATED"]
    output_directory: str
    seed: int
    total_rows: int
    datasets: list[SyntheticDatasetSummary]



class ETLResult(BaseModel):
    requirement_id: str
    sdd_version: str
    status: Literal["COMPLETED"]
    target_dataset: str
    target_file: str
    row_count: int
    reporting_months: list[str]
    active_loans_by_month: dict[str, int]
    transformation_steps: list[str]
    output_schema: list[str]

class DQRuleResult(BaseModel):
    rule_id: str
    description: str
    status: Literal["PASS", "FAIL"]
    checked_rows: int
    failed_rows: int
    sample_failures: list[str] = []


class ReconciliationResult(BaseModel):
    rule_id: str
    description: str
    status: Literal["PASS", "FAIL"]
    source_value: str
    target_value: str
    difference: str


class DataQualityResult(BaseModel):
    requirement_id: str
    sdd_version: str
    status: Literal["PASS", "FAIL"]
    target_dataset: str
    dq_rules: list[DQRuleResult]
    reconciliation_rules: list[ReconciliationResult]
    total_checks: int
    passed_checks: int
    failed_checks: int
    engine: str = "deterministic python validator"


class FunctionalTestResult(BaseModel):
    test_id: str
    description: str
    status: Literal["PASS", "FAIL"]
    evidence: str


class FunctionalValidationResult(BaseModel):
    requirement_id: str
    sdd_version: str
    status: Literal["PASS", "FAIL"]
    total_tests: int
    passed_tests: int
    failed_tests: int
    tests: list[FunctionalTestResult]
    engine: str = "deterministic python functional validator"
