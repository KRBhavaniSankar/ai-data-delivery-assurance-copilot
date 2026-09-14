import requests
import streamlit as st

API = st.sidebar.text_input("FastAPI URL", "http://localhost:8000")

st.set_page_config(page_title="Data Delivery Assurance Copilot", layout="wide")
st.title("AI-Powered Data Delivery Assurance Copilot")
st.caption("Vertical Slice 2 · Requirement → DE-SDD → Data Discovery → Evidence-backed Mapping")

for key, default in [("analysis", None), ("answers", []), ("sdd", None), ("discovery", None), ("synthetic_data", None), ("etl_result", None), ("dq_result", None), ("functional_result", None)]:
    if key not in st.session_state:
        st.session_state[key] = default

progress = 0.2
if st.session_state.analysis:
    progress = 0.45
if st.session_state.sdd:
    progress = 0.7
if st.session_state.discovery:
    progress = 0.85
if st.session_state.synthetic_data:
    progress = 1.0
st.progress(progress)

with st.expander("1 · Business Requirement", expanded=not bool(st.session_state.analysis)):
    title = st.text_input("Requirement title", "Monthly Loan Portfolio Analytics Data Product")
    default = 'Create a monthly loan portfolio dataset containing Loan, Customer, Country, Branch, Loan Product, Reporting Month, Outstanding Principal, Overdue Amount, Days Past Due (DPD), and Risk Bucket.\nThe dataset should represent the latest valid information available for each reporting month.\nThe portfolio should contain active loans and should exclude loans that are no longer relevant to the reporting period.\nOutstanding principal and overdue amounts should represent balances applicable to the reporting month.\nDPD should represent delinquency position for the reporting period.\nLoans should be classified into appropriate risk buckets based on DPD.\nThe data should support aggregation by Country, Branch, Loan Product, Customer, Reporting Month.\nResulting portfolio balances should reconcile with corresponding source loan information.\nDataset should be refreshed monthly and available for management reporting within agreed reporting timeline.'
    text = st.text_area("Business requirement", default, height=260)
    if st.button("Analyze Requirement", type="primary"):
        r = requests.post(f"{API}/analyze", json={"requirement_id":"REQ-001","title":title,"business_requirement":text}, timeout=60)
        r.raise_for_status()
        st.session_state.analysis = r.json()
        st.session_state.title = title
        st.session_state.text = text
        st.session_state.answers = []
        st.session_state.sdd = None
        st.session_state.discovery = None
        st.session_state.synthetic_data = None
        st.session_state.etl_result = None
        st.session_state.dq_result = None
        st.session_state.functional_result = None
        st.rerun()

if st.session_state.analysis:
    a = st.session_state.analysis
    st.subheader("2 · Requirement Analysis")
    c1, c2, c3 = st.columns(3)
    c1.metric("Entities", len(a["extracted_entities"]))
    c2.metric("Metrics", len(a["extracted_metrics"]))
    c3.metric("Ambiguities", len(a["ambiguities"]))
    st.write("**Entities:**", ", ".join(a["extracted_entities"]))
    st.write("**Metrics:**", ", ".join(a["extracted_metrics"]))
    st.write("**Constraints:**", ", ".join(a["extracted_constraints"]))

    ambiguities = a["ambiguities"]
    idx = len(st.session_state.answers)
    if idx < len(ambiguities):
        amb = ambiguities[idx]
        labels = {
            "active_on_month_end":"Active on month-end",
            "active_on_month_start":"Active on month-start",
            "active_at_any_point":"Active at any point during month",
            "latest_valid_as_of_month_end":"Latest valid as of month-end",
            "latest_received_in_month":"Latest received in month",
            "latest_available":"Latest available",
            "closed_only":"Closed only",
            "closed_and_cancelled":"Closed and cancelled",
            "business_defined_statuses":"Business-defined statuses",
            "month_end":"Month-end",
            "month_start":"Month-start",
            "monthly_average":"Monthly average",
            "business_policy":"Approved business policy",
            "0-30_31-60_61-90_gt-90":"0–30 / 31–60 / 61–90 / >90",
            "loan_count":"Loan count",
            "loan_count_and_principal":"Loan count + principal",
            "loan_count_principal_and_overdue":"Loan count + principal + overdue",
            "business_defined_deadline":"Business-defined deadline",
            "next_business_day":"Next business day",
            "month_end_plus_one_day":"Month-end + 1 day",
        }
        st.subheader("3 · Clarification Required")
        st.info(f"**Question {idx+1} of {len(ambiguities)}**\n\n{amb['question']}")
        selected = st.radio("Select PO decision", amb["options"], format_func=lambda x: labels.get(x, x))
        if st.button("Record Decision & Continue", type="primary"):
            st.session_state.answers.append({
                "requirement_id":"REQ-001",
                "ambiguity_id":amb["ambiguity_id"],
                "selected_option":selected,
                "approved_by":"BUSINESS_OWNER"
            })
            st.rerun()
    else:
        st.success("All blocking clarifications resolved. Ready to generate DE-SDD.")
        if st.button("Generate DE-SDD v1.0", type="primary"):
            payload = {
                "requirement": {
                    "requirement_id":"REQ-001",
                    "title":st.session_state.title,
                    "business_requirement":st.session_state.text
                },
                "answers":st.session_state.answers
            }
            r = requests.post(f"{API}/generate-sdd", json=payload, timeout=60)
            r.raise_for_status()
            st.session_state.sdd = r.json()
            st.session_state.discovery = None
            st.rerun()

if st.session_state.sdd:
    s = st.session_state.sdd
    st.subheader("4 · DE-SDD v1.0")
    status = s["specification_metadata"]["status"]
    if status == "APPROVED":
        st.success("APPROVED — DE-SDD is now the delivery contract.")
    else:
        st.warning("PENDING APPROVAL — human approval is required before downstream implementation.")

    meta = s["specification_metadata"]
    st.write(f"**{meta['specification_id']}** · v{meta['version']} · Grain: **{meta['grain']}**")
    sections = [
        ("Business Context", s["business_context"]),
        ("Scope", s["scope"]),
        ("Target Data Model", s["target_data_model"]),
        ("Source-to-Target Mapping", s["source_to_target_mapping"]),
        ("Business Rules", s["business_rules"]),
        ("Transformation Rules", s["transformation_rules"]),
        ("DQ Rules", s["data_quality_rules"]),
        ("Reconciliation", s["reconciliation_rules"]),
        ("Tests", s["test_scenarios"]),
        ("Acceptance Criteria", s["acceptance_criteria"]),
        ("Traceability", s["traceability"]),
        ("Open Questions / Clarifications", s["open_questions_clarifications"]),
    ]
    for name, content in sections:
        with st.expander(name):
            st.write(content)

    c1, c2 = st.columns(2)
    if status != "APPROVED":
        if c1.button("Request Changes"):
            st.warning("Change workflow remains deferred to Vertical Slice 4.")
        if c2.button("Approve DE-SDD", type="primary"):
            r = requests.post(f"{API}/approve-sdd", json={"sdd": s}, timeout=60)
            r.raise_for_status()
            st.session_state.sdd = r.json()
            st.rerun()

if st.session_state.sdd and st.session_state.sdd["specification_metadata"]["status"] == "APPROVED":
    st.subheader("5 · Data Discovery")
    st.caption("Mock Catalog + RAG evidence are used to discover source datasets and validate mappings.")

    if not st.session_state.discovery:
        if st.button("Run Data Discovery", type="primary"):
            r = requests.post(f"{API}/discover", json={"sdd": st.session_state.sdd}, timeout=120)
            r.raise_for_status()
            st.session_state.discovery = r.json()
            st.rerun()

    if st.session_state.discovery:
        d = st.session_state.discovery
        st.success(f"Discovery completed · Engine: {d['engine']}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Datasets", len(d["datasets"]))
        c2.metric("Mappings", len(d["mappings"]))
        c3.metric("Unresolved", len(d["unresolved_items"]))

        with st.expander("Discovered Datasets", expanded=True):
            for dataset in d["datasets"]:
                st.markdown(f"**{dataset['table_name']}** · {dataset['relevance']}")
                st.caption(dataset["reason"])
                for ev in dataset["evidence"]:
                    st.write(f"• {ev['evidence_type']}: `{ev['source']}` — {ev['detail']}")

        with st.expander("Business / Engineering Knowledge Retrieved", expanded=True):
            for ev in d["knowledge_hits"]:
                st.write(f"**{ev['source']}**")
                st.caption(ev["detail"])

        with st.expander("Evidence-backed Source-to-Target Mapping", expanded=True):
            for m in d["mappings"]:
                badge = "✓" if m["status"] == "RESOLVED" else "⚠"
                st.markdown(f"### {badge} `{m['target_field']}`")
                st.write(f"**Source:** `{m['source_expression']}`")
                st.write(f"**Type:** {m['mapping_type']}")
                st.write(f"**Rule:** {m['rule']}")
                for ev in m["evidence"]:
                    st.write(f"• **{ev['evidence_type']}** — `{ev['source']}`: {ev['detail']}")

        if d["unresolved_items"]:
            st.warning("Clarification required for: " + ", ".join(d["unresolved_items"]))
        else:
            st.success("All target fields have evidence-backed discovery results.")


if st.session_state.discovery and not st.session_state.synthetic_data:
    st.subheader("6 · Synthetic Source Data")
    st.caption("Deterministic, synthetic source datasets are generated from the approved DE-SDD context. No intentional defects are introduced in Slice 3A.")
    if st.button("Generate Synthetic Source Data", type="primary"):
        r = requests.post(
            f"{API}/generate-synthetic-data",
            json={"sdd": st.session_state.sdd},
            timeout=60,
        )
        r.raise_for_status()
        st.session_state.synthetic_data = r.json()
        st.rerun()

if st.session_state.synthetic_data:
    d = st.session_state.synthetic_data
    st.subheader("6 · Synthetic Source Data")
    st.success(f"Synthetic baseline generated · Seed: {d['seed']} · Total rows: {d['total_rows']}")
    st.caption("Baseline is intentionally defect-free. Defect injection belongs to the later validation/RCA slice.")

    c1, c2 = st.columns(2)
    c1.metric("Datasets", len(d["datasets"]))
    c2.metric("Total Rows", d["total_rows"])

    with st.expander("Synthetic Dataset Inventory", expanded=True):
        for item in d["datasets"]:
            st.markdown(f"**{item['dataset_name']}** · `{item['file_name']}` · {item['row_count']} rows")
            st.caption("Columns: " + ", ".join(item["columns"]))

    st.info("Slice 3A complete: APPROVED DE-SDD → deterministic synthetic source data. ETL, DQ, reconciliation and executable validation remain the next Slice 3 stages.")


if st.session_state.synthetic_data and not st.session_state.etl_result:
    st.subheader("7 · Deterministic ETL")
    st.caption("The approved DE-SDD and discovered mappings drive a deterministic transformation from synthetic source data to the monthly loan portfolio target.")
    if st.button("Run Deterministic ETL", type="primary"):
        r = requests.post(
            f"{API}/run-etl",
            json={"sdd": st.session_state.sdd},
            timeout=60,
        )
        r.raise_for_status()
        st.session_state.etl_result = r.json()
        st.rerun()

if st.session_state.etl_result:
    e = st.session_state.etl_result
    st.subheader("7 · Deterministic ETL")
    st.success(f"ETL completed · Target: {e['target_dataset']} · Rows: {e['row_count']}")

    c1, c2, c3 = st.columns(3)
    c1.metric("Target Rows", e["row_count"])
    c2.metric("Reporting Months", len(e["reporting_months"]))
    c3.metric("Target Grain", "Loan + Month")

    with st.expander("Transformation Contract", expanded=True):
        for step in e["transformation_steps"]:
            st.write("✓", step)

    with st.expander("Target Dataset", expanded=True):
        st.write(f"**File:** `{e['target_file']}`")
        st.write("**Schema:**", ", ".join(e["output_schema"]))
        st.write("**Rows by reporting month:**")
        st.json(e["active_loans_by_month"])

    st.info("Slice 3B complete: synthetic source data → deterministic ETL → monthly loan portfolio target. DQ and reconciliation remain the next stage.")


if st.session_state.etl_result and not st.session_state.dq_result:
    st.subheader("8 · Data Quality & Reconciliation")
    st.caption("Deterministic validation executes the approved DE-SDD DQ and reconciliation rules. The validator is the authority for PASS/FAIL; no LLM is used to determine the result.")
    if st.button("Run DQ & Reconciliation", type="primary"):
        r = requests.post(
            f"{API}/run-data-quality",
            json={"sdd": st.session_state.sdd},
            timeout=60,
        )
        r.raise_for_status()
        st.session_state.dq_result = r.json()
        st.rerun()

if st.session_state.dq_result:
    v = st.session_state.dq_result
    st.subheader("8 · Data Quality & Reconciliation")
    if v["status"] == "PASS":
        st.success(f"VALIDATION PASS · {v['passed_checks']} / {v['total_checks']} checks passed")
    else:
        st.error(f"VALIDATION FAIL · {v['failed_checks']} / {v['total_checks']} checks failed")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Checks", v["total_checks"])
    c2.metric("Passed", v["passed_checks"])
    c3.metric("Failed", v["failed_checks"])
    c4.metric("Engine", "Deterministic")

    with st.expander("DQ Rule Results", expanded=True):
        for rule in v["dq_rules"]:
            badge = "✓" if rule["status"] == "PASS" else "✗"
            st.markdown(f"**{badge} {rule['rule_id']}** · {rule['description']}")
            st.write(f"Checked: {rule['checked_rows']} · Failed: {rule['failed_rows']}")
            if rule["sample_failures"]:
                st.warning("Sample failures: " + ", ".join(rule["sample_failures"]))

    with st.expander("Reconciliation Results", expanded=True):
        for rule in v["reconciliation_rules"]:
            badge = "✓" if rule["status"] == "PASS" else "✗"
            st.markdown(f"**{badge} {rule['rule_id']}** · {rule['description']}")
            st.write(f"Source: `{rule['source_value']}` · Target: `{rule['target_value']}` · Difference: `{rule['difference']}`")

    st.info("Slice 3C complete: target dataset → DQ rules + source/target reconciliation → deterministic PASS/FAIL. Functional test execution is the next stage.")


if st.session_state.dq_result and not st.session_state.functional_result:
    st.subheader("9 · Functional Test Execution")
    st.caption("The approved DE-SDD test scenarios are executed against the deterministic target. PASS/FAIL is computed by the functional validation engine; no LLM is used as the authority.")
    if st.button("Run Functional Tests", type="primary"):
        r = requests.post(
            f"{API}/run-functional-tests",
            json={"sdd": st.session_state.sdd},
            timeout=60,
        )
        r.raise_for_status()
        st.session_state.functional_result = r.json()
        st.rerun()

if st.session_state.functional_result:
    f = st.session_state.functional_result
    st.subheader("9 · Functional Test Execution")
    if f["status"] == "PASS":
        st.success(f"FUNCTIONAL VALIDATION PASS · {f['passed_tests']} / {f['total_tests']} tests passed")
    else:
        st.error(f"FUNCTIONAL VALIDATION FAIL · {f['failed_tests']} / {f['total_tests']} tests failed")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Tests", f["total_tests"])
    c2.metric("Passed", f["passed_tests"])
    c3.metric("Failed", f["failed_tests"])
    c4.metric("Engine", "Deterministic")

    with st.expander("DE-SDD Test Results", expanded=True):
        for test in f["tests"]:
            badge = "✓" if test["status"] == "PASS" else "✗"
            st.markdown(f"**{badge} {test['test_id']}** · {test['description']}")
            st.caption(test["evidence"])

    if f["status"] == "PASS" and st.session_state.dq_result["status"] == "PASS":
        st.success("OVERALL DELIVERY VALIDATION: PASS — DQ, reconciliation and functional tests all passed.")
        st.info("Clean baseline is now frozen. Intentional defect injection, RCA and retest remain deferred to the later RCA/chaos slice.")
    else:
        st.warning("Overall delivery validation remains FAIL until all deterministic gates pass.")
