from copy import deepcopy
from ai_data_delivery_assurance_copilot.models.contracts import (
    DESDD,
    ChangeAnalysis,
    ChangeClarification,
    ChangeImpactResult,
    ImpactedArtifact,
)

CHANGE_TEXT = (
    "closed loans should be included if they were active at any point during the "
    "reporting month. Also, please exclude loans with zero outstanding balance."
)


def analyze_change(sdd: DESDD, change_text: str) -> ChangeAnalysis:
    normalized = change_text.lower().strip()
    relevant = "closed" in normalized and "active" in normalized and "zero" in normalized
    if not relevant:
        return ChangeAnalysis(
            requirement_id="REQ-001",
            base_version=sdd.specification_metadata.version,
            change_summary=change_text,
            status="REQUIRES_REVIEW",
            clarification=None,
        )
    return ChangeAnalysis(
        requirement_id="REQ-001",
        base_version=sdd.specification_metadata.version,
        change_summary=change_text,
        status="CLARIFICATION_REQUIRED",
        clarification=ChangeClarification(
            clarification_id="CHG-CL-001",
            question="What does 'active at any point during the reporting month' mean?",
            options=[
                "active_on_month_start",
                "active_on_month_end",
                "active_at_any_point",
            ],
            blocking=True,
            impact=["population", "transformation", "dq", "tests", "reconciliation"],
        ),
    )


def apply_change(sdd: DESDD, selected_option: str) -> ChangeImpactResult:
    if selected_option != "active_at_any_point":
        raise ValueError("This change request requires the PO decision 'active_at_any_point'.")

    new_sdd = deepcopy(sdd)
    new_sdd.specification_metadata.version = "1.1"
    new_sdd.specification_metadata.status = "PENDING_APPROVAL"

    # Preserve the original requirement and append the approved mid-sprint change.
    new_sdd.requirement = list(new_sdd.requirement) + [
        "Change v1.1: include loans active at any point during the reporting month and exclude loans with zero outstanding balance."
    ]

    # Update the affected business rules while keeping the target grain unchanged.
    new_sdd.business_rules = [
        (
            "BR-001: Reporting-period population = loans active at any point during the reporting month "
            "(PO-approved v1.1 change)."
        ),
        (
            "BR-002: A loan closed before month-end is included when it was active at any point during the reporting month."
        ),
        "BR-003: One record per Loan + Reporting Month.",
        "BR-004: Outstanding principal is the latest valid balance as of month-end.",
        "BR-005: Overdue amount is the latest valid amount as of month-end.",
        "BR-006: DPD is the latest valid DPD as of month-end.",
        "BR-007: Risk bucket uses the approved DPD business policy.",
        "BR-008: Exclude loans whose month-end outstanding principal is zero.",
    ]

    new_sdd.transformation_rules = [
        "Select the latest valid balance record as of month-end for each loan.",
        "Determine whether the loan was active at any point during the reporting month using approved start/close dates.",
        "Retain loans active at any point in the reporting month.",
        "Exclude records with zero month-end outstanding principal.",
        "Join approved reference data.",
        "Select reporting-date balances and derive risk bucket.",
        "Produce one record at Loan + Reporting Month grain.",
    ]

    new_sdd.data_quality_rules = [
        "DQ-001: Loan ID non-null.",
        "DQ-002: Reporting month non-null.",
        "DQ-003: Loan + month unique.",
        "DQ-004: Outstanding principal >= 0.",
        "DQ-005: Overdue amount >= 0.",
        "DQ-006: DPD >= 0.",
        "DQ-007: Included loans were active at any point during the reporting month.",
        "DQ-008: Risk bucket populated.",
        "DQ-009: Reference mappings resolve.",
        "DQ-010: No duplicate loan-month records.",
        "DQ-011: Included loans have non-zero outstanding principal at month-end.",
    ]

    new_sdd.test_scenarios = [
        "TC-001: Active loan included.",
        "TC-002: Loan closed before month-end but active earlier in the month is included.",
        "TC-003: Loan with zero month-end outstanding principal is excluded.",
        "TC-004: Month-end balance selected.",
        "TC-005: Latest-valid record selected.",
        "TC-006: Risk bucket derived correctly.",
        "TC-007: Loan + Month uniqueness maintained.",
        "TC-008: Missing reference detected.",
        "TC-009: Source-target reconciliation passes.",
    ]

    new_sdd.open_questions_clarifications = [
        "CHG-CL-001 resolved: active at any point during reporting month.",
        "CHG-001 approved: exclude zero month-end outstanding balance.",
        "CL-005 remains governed by approved business DPD thresholds.",
    ]

    new_sdd.acceptance_criteria = list(new_sdd.acceptance_criteria) + [
        "Approved v1.1 change is reflected consistently in population, transformation, DQ, reconciliation and test artifacts.",
        "All impacted downstream artifacts are identified through traceability before implementation changes are made.",
    ]

    impacts = [
        ImpactedArtifact(artifact_id="BR-001", artifact_type="Business Rule", impact_status="IMPACTED", reason="Active population changes from month-end to any-point-in-month."),
        ImpactedArtifact(artifact_id="BR-002", artifact_type="Business Rule", impact_status="IMPACTED", reason="Closed loans can now be included when active earlier in the month."),
        ImpactedArtifact(artifact_id="BR-008", artifact_type="Business Rule", impact_status="ADDED", reason="Zero month-end outstanding balance is now excluded."),
        ImpactedArtifact(artifact_id="MAP-001", artifact_type="Source-to-Target Mapping", impact_status="REVIEW", reason="Population and balance eligibility logic changes, although target columns remain unchanged."),
        ImpactedArtifact(artifact_id="ETL-001", artifact_type="ETL", impact_status="IMPACTED", reason="Temporal population logic and zero-balance filter must change."),
        ImpactedArtifact(artifact_id="DQ-007", artifact_type="Data Quality", impact_status="IMPACTED", reason="Population validation must use any-point activity."),
        ImpactedArtifact(artifact_id="DQ-011", artifact_type="Data Quality", impact_status="ADDED", reason="Zero-balance exclusion requires a new deterministic DQ rule."),
        ImpactedArtifact(artifact_id="RECON-001", artifact_type="Reconciliation", impact_status="IMPACTED", reason="Eligible loan population definition changes."),
        ImpactedArtifact(artifact_id="RECON-002", artifact_type="Reconciliation", impact_status="REVIEW", reason="Principal reconciliation must use the revised eligible population."),
        ImpactedArtifact(artifact_id="RECON-003", artifact_type="Reconciliation", impact_status="REVIEW", reason="Overdue reconciliation must use the revised eligible population."),
        ImpactedArtifact(artifact_id="TEST-001", artifact_type="Functional Test", impact_status="IMPACTED", reason="Active population expectation changes."),
        ImpactedArtifact(artifact_id="TEST-002", artifact_type="Functional Test", impact_status="IMPACTED", reason="Previously excluded closed-before-month-end loans can now be included."),
        ImpactedArtifact(artifact_id="TEST-003", artifact_type="Functional Test", impact_status="ADDED", reason="Zero-balance exclusion requires explicit test coverage."),
        ImpactedArtifact(artifact_id="SQA-001", artifact_type="SQA", impact_status="IMPACTED", reason="SQA regression coverage must be updated for population and zero-balance behavior."),
        ImpactedArtifact(artifact_id="DASH-001", artifact_type="Reporting Consumer", impact_status="REVIEW", reason="Population may change; dashboard totals and trend continuity require review."),
    ]

    return ChangeImpactResult(
        requirement_id="REQ-001",
        base_version="1.0",
        proposed_version="1.1",
        status="READY_FOR_APPROVAL",
        change_summary=CHANGE_TEXT,
        clarification_decision=selected_option,
        sdd=new_sdd,
        impacted_artifacts=impacts,
    )
