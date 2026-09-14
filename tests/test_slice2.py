from ai_data_delivery_assurance_copilot.models.contracts import ClarificationAnswer
from ai_data_delivery_assurance_copilot.services.spec_builder import build_desdd
from ai_data_delivery_assurance_copilot.services.discovery import run_discovery


TEXT = """Create a monthly loan portfolio dataset containing outstanding principal, overdue amount, DPD and risk bucket.
The portfolio should contain active loans and exclude closed loans. The dataset should use the latest valid information
and reconcile source balances."""


def approved_sdd():
    answers = [
        ClarificationAnswer(
            requirement_id="REQ-001",
            ambiguity_id="CL-001",
            selected_option="active_on_month_end",
        ),
        ClarificationAnswer(
            requirement_id="REQ-001",
            ambiguity_id="CL-002",
            selected_option="latest_valid_as_of_month_end",
        ),
        ClarificationAnswer(
            requirement_id="REQ-001",
            ambiguity_id="CL-003",
            selected_option="closed_only",
        ),
        ClarificationAnswer(
            requirement_id="REQ-001",
            ambiguity_id="CL-004",
            selected_option="month_end",
        ),
        ClarificationAnswer(
            requirement_id="REQ-001",
            ambiguity_id="CL-005",
            selected_option="business_policy",
        ),
        ClarificationAnswer(
            requirement_id="REQ-001",
            ambiguity_id="CL-006",
            selected_option="loan_count_principal_and_overdue",
        ),
        ClarificationAnswer(
            requirement_id="REQ-001",
            ambiguity_id="CL-007",
            selected_option="business_defined_deadline",
        ),
    ]

    sdd = build_desdd(
        "REQ-001",
        "Monthly Loan Portfolio Analytics Data Product",
        TEXT,
        answers,
    )

    sdd.specification_metadata.status = "APPROVED"

    return sdd


def test_discovery_finds_core_datasets():
    result = run_discovery(approved_sdd())

    names = {dataset.table_name for dataset in result.datasets}

    expected_datasets = {
        "loan_master",
        "loan_daily_balance",
        "customer_master",
        "branch_master",
        "country_master",
        "loan_product_master",
        "reporting_calendar",
    }

    assert len(result.datasets) == 7
    assert expected_datasets.issubset(names)


def test_discovery_produces_evidence_backed_risk_mapping():
    result = run_discovery(approved_sdd())

    mapping = next(
        mapping
        for mapping in result.mappings
        if mapping.target_field == "risk_bucket"
    )

    assert mapping.mapping_type == "DERIVED"
    assert mapping.status == "RESOLVED"
    assert any(
        evidence.evidence_type == "RAG"
        for evidence in mapping.evidence
    )


def test_discovery_covers_target_fields():
    result = run_discovery(approved_sdd())

    targets = {mapping.target_field for mapping in result.mappings}

    assert targets == set(
        approved_sdd().target_data_model.columns
    )


def test_reference_mappings_have_catalog_evidence():
    result = run_discovery(approved_sdd())

    expected_reference_evidence = {
        "country_code": "country_master",
        "branch_id": "branch_master",
        "loan_product_id": "loan_product_master",
    }

    for target_field, reference_table in expected_reference_evidence.items():
        mapping = next(
            mapping
            for mapping in result.mappings
            if mapping.target_field == target_field
        )

        assert mapping.mapping_type == "REFERENCE"
        assert mapping.status == "RESOLVED"

        assert any(
            evidence.evidence_type == "CATALOG"
            and evidence.source == reference_table
            for evidence in mapping.evidence
        )


def test_reporting_month_has_catalog_evidence():
    result = run_discovery(approved_sdd())

    mapping = next(
        mapping
        for mapping in result.mappings
        if mapping.target_field == "reporting_month"
    )

    assert mapping.mapping_type == "REFERENCE"
    assert mapping.status == "RESOLVED"

    assert any(
        evidence.evidence_type == "CATALOG"
        and evidence.source == "reporting_calendar"
        for evidence in mapping.evidence
    )