import csv
from pathlib import Path

from ai_data_delivery_assurance_copilot.models.contracts import ClarificationAnswer
from ai_data_delivery_assurance_copilot.services.etl import TARGET_SCHEMA, run_etl
from ai_data_delivery_assurance_copilot.services.spec_builder import build_desdd
from ai_data_delivery_assurance_copilot.services.synthetic_data import generate_synthetic_data


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


def read_target():
    path = Path("data/target/monthly_loan_portfolio.csv")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_etl_creates_expected_target_schema_and_row_count():
    sdd = approved_sdd()
    generate_synthetic_data(sdd)
    result = run_etl(sdd)
    assert result.status == "COMPLETED"
    assert result.row_count == 12
    assert result.output_schema == TARGET_SCHEMA
    assert Path(result.target_file).exists()


def test_etl_preserves_loan_month_grain():
    generate_synthetic_data(approved_sdd())
    run_etl(approved_sdd())
    rows = read_target()
    keys = [(row["loan_id"], row["reporting_month"]) for row in rows]
    assert len(keys) == len(set(keys))


def test_etl_excludes_closed_and_future_loans():
    generate_synthetic_data(approved_sdd())
    run_etl(approved_sdd())
    rows = read_target()
    loan_ids = {row["loan_id"] for row in rows}
    assert "L002" not in loan_ids
    assert "L005" not in loan_ids
    assert "L006" not in loan_ids
    assert "L009" not in loan_ids
    assert "L008" not in loan_ids


def test_etl_selects_month_end_and_derives_risk_bucket():
    generate_synthetic_data(approved_sdd())
    run_etl(approved_sdd())
    rows = read_target()
    jan_l001 = next(row for row in rows if row["loan_id"] == "L001" and row["reporting_month"] == "2025-01")
    assert jan_l001["reporting_month"] == "2025-01"
    assert jan_l001["outstanding_principal"] == "11027.00"
    assert int(jan_l001["dpd"]) >= 0
    assert jan_l001["risk_bucket"] in {"A", "B", "C", "D"}


def test_etl_includes_loans_opened_during_reporting_month_when_active_at_month_end():
    generate_synthetic_data(approved_sdd())
    run_etl(approved_sdd())
    rows = read_target()
    keys = {(row["loan_id"], row["reporting_month"]) for row in rows}
    assert ("L003", "2025-01") in keys
    assert ("L010", "2025-01") in keys
    assert ("L004", "2025-02") in keys
    assert ("L012", "2025-02") in keys
    assert ("L004", "2025-01") not in keys


def test_etl_is_reproducible():
    sdd = approved_sdd()
    generate_synthetic_data(sdd)
    run_etl(sdd)
    first = Path("data/target/monthly_loan_portfolio.csv").read_bytes()
    run_etl(sdd)
    second = Path("data/target/monthly_loan_portfolio.csv").read_bytes()
    assert first == second
