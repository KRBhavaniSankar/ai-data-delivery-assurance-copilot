import re
from ai_data_delivery_assurance_copilot.models.contracts import RequirementAnalysis, Ambiguity


def analyze_requirement(requirement_id: str, text: str) -> RequirementAnalysis:
    lower = text.lower()
    entities = []
    for term in ["loan", "customer", "country", "branch", "loan product", "reporting month"]:
        if term in lower:
            entities.append(term.title())
    metrics = []
    for term in ["outstanding principal", "overdue amount", "days past due", "dpd", "risk bucket"]:
        if term in lower:
            metrics.append(term.upper() if term == "dpd" else term.title())
    constraints = []
    if "monthly" in lower:
        constraints.append("Monthly reporting")
    if "reconcile" in lower:
        constraints.append("Source-to-target reconciliation required")
    if "active" in lower:
        constraints.append("Loan population constrained by active status")

    ambiguities = []
    candidates = [
        ("CL-001", "What qualifies as an active loan for the reporting month?", ["active_on_month_end", "active_on_month_start", "active_at_any_point"], ["population", "transformation", "dq", "tests"]),
        ("CL-002", "What does latest valid information mean for a reporting month?", ["latest_valid_as_of_month_end", "latest_received_in_month", "latest_available"], ["source_selection", "transformation", "reconciliation"]),
        ("CL-003", "Which loan statuses should be excluded from the reporting population?", ["closed_only", "closed_and_cancelled", "business_defined_statuses"], ["population", "dq", "tests"]),
        ("CL-004", "Which point-in-time should be used for outstanding principal and overdue amount?", ["month_end", "month_start", "monthly_average"], ["mapping", "transformation", "reconciliation"]),
        ("CL-005", "Which DPD thresholds define the risk buckets?", ["business_policy", "0-30_31-60_61-90_gt-90"], ["business_rule", "transformation", "tests"]),
        ("CL-006", "What is the required reconciliation scope?", ["loan_count", "loan_count_and_principal", "loan_count_principal_and_overdue"], ["reconciliation", "acceptance", "tests"]),
        ("CL-007", "What reporting deadline applies to the monthly dataset?", ["business_defined_deadline", "next_business_day", "month_end_plus_one_day"], ["sla", "acceptance", "operations"]),
    ]
    for cid, q, options, impact in candidates:
        trigger_words = {
            "CL-001": ["active"], "CL-002": ["latest valid"], "CL-003": ["exclude", "closed"],
            "CL-004": ["outstanding principal", "overdue amount"], "CL-005": ["risk bucket", "dpd"],
            "CL-006": ["reconcile"], "CL-007": ["timeline", "deadline", "available"]
        }[cid]
        if any(w in lower for w in trigger_words):
            ambiguities.append(Ambiguity(ambiguity_id=cid, question=q, options=options, impact=impact))
    # The reference demo intentionally treats these as ambiguities even when the text hints at them.
    if "latest valid" not in lower:
        ambiguities.append(Ambiguity(ambiguity_id="CL-002", question="What does latest valid information mean for a reporting month?", options=["latest_valid_as_of_month_end", "latest_received_in_month", "latest_available"], impact=["source_selection", "transformation", "reconciliation"]))
    ambiguities = {a.ambiguity_id: a for a in ambiguities}
    ordered = [ambiguities[k] for k in sorted(ambiguities)]
    return RequirementAnalysis(
        requirement_id=requirement_id,
        extracted_entities=entities,
        extracted_metrics=metrics,
        extracted_constraints=constraints,
        ambiguities=ordered,
        status="CLARIFICATION_REQUIRED" if ordered else "READY_FOR_SPEC",
    )
