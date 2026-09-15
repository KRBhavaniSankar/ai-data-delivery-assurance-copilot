from ai_data_delivery_assurance_copilot.models.contracts import (
    DESDD, SpecificationMetadata, Scope, TargetDataModel,
)
from ai_data_delivery_assurance_copilot.services.change_impact import analyze_change, apply_change


def approved_sdd():
    return DESDD(
        specification_metadata=SpecificationMetadata(
            specification_id="DE-SDD-LOAN-001", version="1.0", status="APPROVED",
            domain="Banking", title="Monthly Loan Portfolio Analytics Data Product",
            grain="Loan + Reporting Month",
        ),
        business_context=["Monthly loan portfolio analytics"],
        requirement=["Create monthly loan portfolio analytics."],
        scope=Scope(in_scope=["Monthly loan portfolio"], out_of_scope=["Real-time monitoring"]),
        business_glossary=["Reporting Month", "Active Loan"],
        data_context=["loan_master", "loan_daily_balance"],
        target_data_model=TargetDataModel(
            grain="Loan + Reporting Month",
            columns=["loan_id", "customer_id", "country_code", "branch_id", "loan_product_id", "reporting_month", "outstanding_principal", "overdue_amount", "dpd", "risk_bucket"],
            uniqueness="loan_id + reporting_month",
        ),
        source_to_target_mapping=["loan_id ← loan_master.loan_id"],
        business_rules=["BR-001: Active on month-end.", "BR-002: Closed loans excluded.", "BR-003: One record per Loan + Reporting Month."],
        transformation_rules=["Select latest valid record as of month-end.", "Filter active loans."],
        data_quality_rules=["DQ-001: Loan ID non-null."],
        reconciliation_rules=["RECON-001: Eligible loan count."],
        edge_cases=["Closed before month-end"],
        test_scenarios=["TC-001: Active loan included.", "TC-002: Closed loan excluded."],
        data_security_sensitivity=["Sensitive loan data"],
        non_functional_data_requirements=["Monthly refresh"],
        dependencies=["Loan source"],
        assumptions=["Calendar month"],
        open_questions_clarifications=["CL-001 resolved as active_on_month_end."],
        acceptance_criteria=["Approved SDD before implementation."],
        traceability=["REQ-001 → BR-001 → ETL-001 → DQ-001 → TEST-001"],
    )


CHANGE = "I just realized closed loans should be included if they were active at any point during the reporting month. Also, please exclude loans with zero outstanding balance."


def test_change_requires_blocking_clarification():
    result = analyze_change(approved_sdd(), CHANGE)
    assert result.status == "CLARIFICATION_REQUIRED"
    assert result.clarification is not None
    assert result.clarification.blocking is True


def test_change_produces_v11_and_impact_graph():
    result = apply_change(approved_sdd(), "active_at_any_point")
    assert result.proposed_version == "1.1"
    assert result.sdd.specification_metadata.version == "1.1"
    assert result.sdd.specification_metadata.status == "PENDING_APPROVAL"
    ids = {item.artifact_id for item in result.impacted_artifacts}
    assert {"ETL-001", "DQ-007", "RECON-001", "TEST-002", "SQA-001"}.issubset(ids)


def test_change_adds_zero_balance_rule_and_test():
    result = apply_change(approved_sdd(), "active_at_any_point")
    assert any("zero" in rule.lower() for rule in result.sdd.data_quality_rules)
    assert any("zero" in test.lower() for test in result.sdd.test_scenarios)


def test_change_keeps_grain_unchanged():
    base = approved_sdd()
    result = apply_change(base, "active_at_any_point")
    assert result.sdd.target_data_model.grain == base.target_data_model.grain
    assert result.sdd.target_data_model.columns == base.target_data_model.columns
