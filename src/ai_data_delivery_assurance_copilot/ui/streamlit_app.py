import requests
import streamlit as st

API = st.sidebar.text_input("FastAPI URL", "http://localhost:8000")

st.set_page_config(page_title="Data Delivery Assurance Copilot", layout="wide")
st.title("AI-Powered Data Delivery Assurance Copilot")
st.caption("Vertical Slice 2 · Requirement → DE-SDD → Data Discovery → Evidence-backed Mapping")

for key, default in [("analysis", None), ("answers", []), ("sdd", None), ("discovery", None), ("synthetic_data", None)]:
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
