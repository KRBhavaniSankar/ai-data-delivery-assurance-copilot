from ai_data_delivery_assurance_copilot.models.contracts import DESDD, SpecificationMetadata, Scope, TargetDataModel, ClarificationAnswer


def build_desdd(requirement_id: str, title: str, text: str, answers: list[ClarificationAnswer]) -> DESDD:
    amap = {a.ambiguity_id: a.selected_option for a in answers}
    active = amap.get("CL-001", "active_on_month_end")
    latest = amap.get("CL-002", "latest_valid_as_of_month_end")
    excluded = amap.get("CL-003", "closed_only")
    balance_point = amap.get("CL-004", "month_end")
    risk = amap.get("CL-005", "business_policy")
    recon = amap.get("CL-006", "loan_count_principal_and_overdue")
    deadline = amap.get("CL-007", "business_defined_deadline")
    return DESDD(
        specification_metadata=SpecificationMetadata(specification_id="DE-SDD-LOAN-001", version="1.0", status="PENDING_APPROVAL", domain="Banking Analytics", title=title, grain="Loan + Reporting Month"),
        business_context=["Provide a consistent monthly loan portfolio view for management reporting and portfolio analysis."],
        requirement=[x.strip() for x in text.split("\n") if x.strip()],
        scope=Scope(
            in_scope=["Monthly loan portfolio dataset", "Loan-level reporting", "Outstanding principal", "Overdue amount", "DPD", "Risk bucket", "Country, branch, customer and product dimensions", "DQ and reconciliation"],
            out_of_scope=["Real-time monitoring", "Loan origination", "Credit decisioning", "Predictive risk modelling", "Customer-level target grain"]),
        business_glossary=["Reporting Month: calendar month represented by the dataset.", "Month-end: final reporting date for the calendar month.", "Active Loan: defined by the approved clarification decision.", "DPD: days past due at the reporting point.", "Risk Bucket: classification derived from approved DPD thresholds."],
        data_context=["loan_master", "loan_daily_balance", "customer_master", "branch_master", "country_master", "loan_product_master"],
        target_data_model=TargetDataModel(grain="Loan + Reporting Month", columns=["loan_id", "customer_id", "country_code", "branch_id", "loan_product_id", "reporting_month", "outstanding_principal", "overdue_amount", "dpd", "risk_bucket"], uniqueness="loan_id + reporting_month"),
        source_to_target_mapping=["loan_id ← loan_master.loan_id", "customer_id ← loan_master.customer_id", "country_code ← customer/reference data", "branch_id ← loan_master/reference data", "loan_product_id ← loan_master/reference data", "reporting_month ← reporting calendar", "outstanding_principal ← loan_daily_balance at month-end", "overdue_amount ← loan_daily_balance at month-end", "dpd ← loan_daily_balance at month-end", "risk_bucket ← derived from approved DPD policy"],
        business_rules=[f"BR-001: Active loan population = {active}.", f"BR-002: Exclusion status policy = {excluded}.", "BR-003: One record per Loan + Reporting Month.", f"BR-004: Outstanding principal point-in-time = {balance_point}.", f"BR-005: Overdue amount point-in-time = {balance_point}.", f"BR-006: DPD point-in-time = {balance_point}.", f"BR-007: Risk bucket uses {risk}."],
        transformation_rules=[f"Select {latest} record for each loan/reporting month.", "Determine reporting-period population using approved status logic.", "Join approved reference data.", "Select reporting-date balances and derive risk bucket.", "Aggregate only where target grain requires it."],
        data_quality_rules=["Loan ID non-null", "Reporting month non-null", "Loan + month unique", "Outstanding principal >= 0", "Overdue amount >= 0", "DPD >= 0", "Included loans satisfy active rule", "Risk bucket populated", "Reference mappings resolve", "No duplicate loan-month records"],
        reconciliation_rules=["Eligible loan count source = target", "Outstanding principal sum source = target", "Overdue amount sum source = target"] if recon == "loan_count_principal_and_overdue" else ["Eligible loan count source = target"],
        edge_cases=["Loan opened during month", "Loan closed before month-end", "Missing month-end balance", "Duplicate source record", "Missing reference mapping", "Invalid DPD", "Negative balance", "Late-arriving record"],
        test_scenarios=["Active loan included", "Closed loan excluded", "Month-end balance selected", "Latest-valid record selected", "Risk bucket derived correctly", "Duplicate loan-month rejected", "Missing reference detected", "Source-target reconciliation passes"],
        data_security_sensitivity=["Loan and customer data are sensitive.", "Hackathon uses synthetic data only.", "Access should be limited to authorized users."],
        non_functional_data_requirements=["Refresh frequency: monthly", f"Availability: {deadline}", "Freshness: latest valid month-end information", "Volume: establish during discovery", "Retention: business-defined"],
        dependencies=["Loan source", "Daily balance source", "Customer/branch/country/product reference data", "Risk bucket policy", "Reporting calendar", "DQ and reconciliation execution"],
        assumptions=["Calendar month reporting", "Loan + Reporting Month grain", "Month-end is reporting cutoff", "Approved enterprise definitions are authoritative", "Synthetic data for hackathon"],
        open_questions_clarifications=[f"CL-001 resolved as {active}", f"CL-002 resolved as {latest}", f"CL-003 resolved as {excluded}", f"CL-004 resolved as {balance_point}", "CL-005 requires approved business thresholds" if risk == "business_policy" else f"CL-005 resolved as {risk}"],
        acceptance_criteria=["All required DE-SDD sections populated", "Blocking ambiguities resolved", "Mappings and rules are traceable", "DQ and reconciliation rules defined", "Test scenarios defined", "Security and NFRs documented", "Business owner approval captured before implementation"],
        traceability=["REQ-001 → BR-001..BR-007", "BR → MAP → ETL → DQ → RECON → TEST", "Clarification decisions → affected specification sections"]
    )
