from ai_data_delivery_assurance_copilot.models.contracts import ClarificationAnswer
from ai_data_delivery_assurance_copilot.services.etl import run_etl
from ai_data_delivery_assurance_copilot.services.functional_tests import run_functional_tests
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


def prepare():
    sdd = approved_sdd()
    generate_synthetic_data(sdd)
    run_etl(sdd)
    return sdd


def test_all_de_sdd_functional_tests_pass():
    result = run_functional_tests(prepare())
    assert result.status == "PASS"
    assert result.total_tests == 8
    assert result.passed_tests == 8
    assert result.failed_tests == 0


def test_functional_test_ids_match_de_sdd_scenarios():
    result = run_functional_tests(prepare())
    assert [test.test_id for test in result.tests] == [f"TC-{i:03d}" for i in range(1, 9)]
    assert all(test.status == "PASS" for test in result.tests)
