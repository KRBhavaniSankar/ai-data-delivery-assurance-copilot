from pathlib import Path

from ai_data_delivery_assurance_copilot.models.contracts import ClarificationAnswer
from ai_data_delivery_assurance_copilot.services.etl import run_etl
from ai_data_delivery_assurance_copilot.services.spec_builder import build_desdd
from ai_data_delivery_assurance_copilot.services.synthetic_data import generate_synthetic_data
from ai_data_delivery_assurance_copilot.services.validation import run_data_quality_validation


TEXT = """Create a monthly loan portfolio dataset containing outstanding principal, overdue amount, DPD and risk bucket.
The portfolio should contain active loans and exclude closed loans. The dataset should use the latest valid information
and reconcile source balances."""


def approved_sdd():
    answers = [
        ClarificationAnswer(requirement_id="REQ-001", ambiguity_id="CL-001", selected_option="active_on_month_end"),
        ClarificationAnswer(requirement_id="REQ-001", ambiguity_id="CL-002", selected_option="latest_valid_as_of_month_end"),
        ClarificationAnswer(requirement_id="REQ-001", ambiguity_id="CL-003", selected_option="closed_only"),
        ClarificationAnswer(requirement_id="REQ-001", ambiguity_id="CL-004", selected_option="month_end"),
        ClarificationAnswer(requirement_id="REQ-001", ambiguity_id="CL-005", selected_option="business_policy"),
        ClarificationAnswer(requirement_id="REQ-001", ambiguity_id="CL-006", selected_option="loan_count_principal_and_overdue"),
        ClarificationAnswer(requirement_id="REQ-001", ambiguity_id="CL-007", selected_option="business_defined_deadline"),
    ]
    sdd = build_desdd("REQ-001", "Monthly Loan Portfolio Analytics Data Product", TEXT, answers)
    sdd.specification_metadata.status = "APPROVED"
    return sdd


def prepare():
    sdd = approved_sdd()
    generate_synthetic_data(sdd)
    run_etl(sdd)
    return sdd


def test_validation_passes_on_clean_baseline():
    result = run_data_quality_validation(prepare())
    assert result.status == "PASS"
    assert result.failed_checks == 0
    assert result.passed_checks == result.total_checks


def test_all_de_sdd_dq_rules_execute():
    result = run_data_quality_validation(prepare())
    ids = [rule.rule_id for rule in result.dq_rules]
    assert ids == [f"DQ-{i:03d}" for i in range(1, 11)]
    assert all(rule.status == "PASS" for rule in result.dq_rules)


def test_all_reconciliation_rules_pass_for_each_reporting_month():
    result = run_data_quality_validation(prepare())
    assert len(result.reconciliation_rules) == 6
    assert result.total_checks == 16
    assert all(rule.status == "PASS" for rule in result.reconciliation_rules)
    assert all(rule.difference in {"0", "0.00"} for rule in result.reconciliation_rules)


def test_validation_requires_target_output():
    path = Path("data/target/monthly_loan_portfolio.csv")
    if path.exists():
        path.unlink()
    try:
        try:
            run_data_quality_validation(approved_sdd())
            assert False, "Expected missing-target validation error"
        except ValueError as exc:
            assert "Target dataset does not exist" in str(exc)
    finally:
        sdd = approved_sdd()
        generate_synthetic_data(sdd)
        run_etl(sdd)
