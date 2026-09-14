from ai_data_delivery_assurance_copilot.services.analyzer import analyze_requirement
from ai_data_delivery_assurance_copilot.services.spec_builder import build_desdd
from ai_data_delivery_assurance_copilot.models.contracts import ClarificationAnswer

TEXT = """Create a monthly loan portfolio dataset containing outstanding principal, overdue amount, DPD and risk bucket. The portfolio should contain active loans and exclude closed loans. The dataset should use the latest valid information and reconcile source balances."""

def test_analysis_detects_blocking_ambiguities():
    a = analyze_requirement("REQ-001", TEXT)
    ids = {x.ambiguity_id for x in a.ambiguities}
    assert "CL-001" in ids
    assert "CL-002" in ids
    assert a.status == "CLARIFICATION_REQUIRED"

def test_sdd_has_frozen_grain_and_traceability():
    answers=[
      ClarificationAnswer(requirement_id="REQ-001",ambiguity_id="CL-001",selected_option="active_on_month_end"),
      ClarificationAnswer(requirement_id="REQ-001",ambiguity_id="CL-002",selected_option="latest_valid_as_of_month_end"),
      ClarificationAnswer(requirement_id="REQ-001",ambiguity_id="CL-003",selected_option="closed_only"),
      ClarificationAnswer(requirement_id="REQ-001",ambiguity_id="CL-004",selected_option="month_end"),
      ClarificationAnswer(requirement_id="REQ-001",ambiguity_id="CL-005",selected_option="business_policy"),
      ClarificationAnswer(requirement_id="REQ-001",ambiguity_id="CL-006",selected_option="loan_count_principal_and_overdue"),
      ClarificationAnswer(requirement_id="REQ-001",ambiguity_id="CL-007",selected_option="business_defined_deadline"),
    ]
    s=build_desdd("REQ-001","Monthly Loan Portfolio Analytics Data Product",TEXT,answers)
    assert s.specification_metadata.grain == "Loan + Reporting Month"
    assert s.target_data_model.uniqueness == "loan_id + reporting_month"
    assert any("REQ-001" in x for x in s.traceability)
