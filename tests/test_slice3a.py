from pathlib import Path

from ai_data_delivery_assurance_copilot.models.contracts import ClarificationAnswer
from ai_data_delivery_assurance_copilot.services.spec_builder import build_desdd
from ai_data_delivery_assurance_copilot.services.synthetic_data import (
    SCHEMAS,
    generate_synthetic_data,
    validate_synthetic_data,
)


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
    sdd = build_desdd(
        "REQ-001",
        "Monthly Loan Portfolio Analytics Data Product",
        TEXT,
        answers,
    )
    sdd.specification_metadata.status = "APPROVED"
    return sdd


def test_synthetic_generation_creates_all_catalog_datasets():
    result = generate_synthetic_data(approved_sdd())
    names = {item.dataset_name for item in result.datasets}
    assert names == set(SCHEMAS)
    assert len(result.datasets) == 7
    assert result.total_rows > 0


def test_synthetic_data_is_schema_valid():
    generate_synthetic_data(approved_sdd())
    assert validate_synthetic_data() == []


def test_synthetic_generation_is_deterministic():
    first = generate_synthetic_data(approved_sdd())
    output_dir = Path(first.output_directory)
    assert first.seed == 20260915
    first_bytes = {
        item.file_name: (output_dir / item.file_name).read_bytes()
        for item in first.datasets
    }

    second = generate_synthetic_data(approved_sdd())
    second_bytes = {
        item.file_name: (output_dir / item.file_name).read_bytes()
        for item in second.datasets
    }

    assert first_bytes == second_bytes


def test_synthetic_dataset_supports_required_lifecycle_scenarios():
    generate_synthetic_data(approved_sdd())
    import csv

    path = Path("data/synthetic/loan_master.csv")
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert any(row["loan_status"] == "CLOSED" for row in rows)
    assert any(row["loan_status"] == "ACTIVE" for row in rows)
    assert any(row["loan_start_date"].startswith("2025-01") for row in rows)
    assert any(row["loan_start_date"].startswith("2025-02") for row in rows)
