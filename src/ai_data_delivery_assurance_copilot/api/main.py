from fastapi import FastAPI, HTTPException

from ai_data_delivery_assurance_copilot.models.contracts import RequirementInput, ClarificationAnswer, DESDD
from ai_data_delivery_assurance_copilot.services.analyzer import analyze_requirement
from ai_data_delivery_assurance_copilot.services.spec_builder import build_desdd
from ai_data_delivery_assurance_copilot.services.discovery import run_discovery
from ai_data_delivery_assurance_copilot.services.synthetic_data import generate_synthetic_data
from ai_data_delivery_assurance_copilot.services.etl import run_etl
from ai_data_delivery_assurance_copilot.services.validation import run_data_quality_validation
from ai_data_delivery_assurance_copilot.services.functional_tests import run_functional_tests
from ai_data_delivery_assurance_copilot.services.change_impact import analyze_change, apply_change

app = FastAPI(title="AI Data Delivery Assurance Copilot - Slices 1–5", version="0.1.0")

@app.get("/health")
def health():
    return {"status": "ok", "slice": "1-5"}

@app.post("/analyze")
def analyze(req: RequirementInput):
    return analyze_requirement(req.requirement_id, req.business_requirement)

@app.post("/generate-sdd")
def generate_sdd(payload: dict):
    req = RequirementInput.model_validate(payload["requirement"])
    answers = [ClarificationAnswer.model_validate(x) for x in payload.get("answers", [])]
    analysis = analyze_requirement(req.requirement_id, req.business_requirement)
    blocking = {a.ambiguity_id for a in analysis.ambiguities if a.blocking}
    answered = {a.ambiguity_id for a in answers}
    missing = sorted(blocking - answered)
    if missing:
        raise HTTPException(status_code=409, detail={"message": "Blocking clarifications remain", "ambiguity_ids": missing})
    return build_desdd(req.requirement_id, req.title, req.business_requirement, answers)

@app.post("/approve-sdd")
def approve_sdd(payload: dict):
    sdd = payload.get("sdd")
    if not isinstance(sdd, dict):
        raise HTTPException(status_code=400, detail="sdd is required")
    if sdd.get("specification_metadata", {}).get("status") != "PENDING_APPROVAL":
        raise HTTPException(status_code=409, detail="DE-SDD is not pending approval")
    sdd["specification_metadata"]["status"] = "APPROVED"
    return sdd

@app.post("/discover")
def discover(payload: dict):
    try:
        sdd = DESDD.model_validate(payload["sdd"])
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid DE-SDD: {exc}") from exc
    if sdd.specification_metadata.status != "APPROVED":
        raise HTTPException(status_code=409, detail="DE-SDD must be APPROVED before data discovery")
    return run_discovery(sdd)


@app.post("/generate-synthetic-data")
def generate_synthetic(payload: dict):
    try:
        sdd = DESDD.model_validate(payload["sdd"])
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid DE-SDD: {exc}") from exc
    if sdd.specification_metadata.status != "APPROVED":
        raise HTTPException(status_code=409, detail="DE-SDD must be APPROVED before synthetic data generation")
    return generate_synthetic_data(sdd)


@app.post("/run-etl")
def run_deterministic_etl(payload: dict):
    try:
        sdd = DESDD.model_validate(payload["sdd"])
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid DE-SDD: {exc}") from exc
    if sdd.specification_metadata.status != "APPROVED":
        raise HTTPException(status_code=409, detail="DE-SDD must be APPROVED before ETL execution")
    try:
        return run_etl(sdd)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/run-data-quality")
def run_data_quality(payload: dict):
    try:
        sdd = DESDD.model_validate(payload["sdd"])
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid DE-SDD: {exc}") from exc
    if sdd.specification_metadata.status != "APPROVED":
        raise HTTPException(status_code=409, detail="DE-SDD must be APPROVED before validation")
    try:
        return run_data_quality_validation(sdd)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/run-functional-tests")
def run_functional(payload: dict):
    try:
        sdd = DESDD.model_validate(payload["sdd"])
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid DE-SDD: {exc}") from exc
    if sdd.specification_metadata.status != "APPROVED":
        raise HTTPException(status_code=409, detail="DE-SDD must be APPROVED before functional validation")
    try:
        return run_functional_tests(sdd)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/analyze-change")
def analyze_requirement_change(payload: dict):
    try:
        sdd = DESDD.model_validate(payload["sdd"])
        change_text = str(payload["change_text"]).strip()
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid change request: {exc}") from exc
    if sdd.specification_metadata.status != "APPROVED":
        raise HTTPException(status_code=409, detail="DE-SDD must be APPROVED before a mid-sprint change is analyzed")
    return analyze_change(sdd, change_text)


@app.post("/apply-change")
def apply_requirement_change(payload: dict):
    try:
        sdd = DESDD.model_validate(payload["sdd"])
        selected_option = str(payload["selected_option"])
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid change decision: {exc}") from exc
    if sdd.specification_metadata.status != "APPROVED":
        raise HTTPException(status_code=409, detail="DE-SDD must be APPROVED before applying a change")
    try:
        return apply_change(sdd, selected_option)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/inject-defect")
def inject_defect(payload: dict):
    try:
        sdd = DESDD.model_validate(payload["sdd"])
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid DE-SDD: {exc}") from exc
    if sdd.specification_metadata.status != "APPROVED":
        raise HTTPException(status_code=409, detail="DE-SDD must be APPROVED before defect injection")
    try:
        from ai_data_delivery_assurance_copilot.services.defect_rca import inject_controlled_defect
        return inject_controlled_defect(sdd)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/run-rca")
def run_root_cause_analysis(payload: dict):
    try:
        sdd = DESDD.model_validate(payload["sdd"])
        dq_result = payload["dq_result"]
        functional_result = payload["functional_result"]
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid RCA request: {exc}") from exc
    from ai_data_delivery_assurance_copilot.services.defect_rca import run_rca
    return run_rca(sdd, dq_result, functional_result)


@app.post("/remediate")
def remediate_defect(payload: dict):
    try:
        sdd = DESDD.model_validate(payload["sdd"])
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid DE-SDD: {exc}") from exc
    if sdd.specification_metadata.status != "APPROVED":
        raise HTTPException(status_code=409, detail="DE-SDD must be APPROVED before remediation")
    from ai_data_delivery_assurance_copilot.services.defect_rca import remediate
    return remediate(sdd)


@app.post("/retest")
def retest_defect(payload: dict):
    try:
        sdd = DESDD.model_validate(payload["sdd"])
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid DE-SDD: {exc}") from exc
    if sdd.specification_metadata.status != "APPROVED":
        raise HTTPException(status_code=409, detail="DE-SDD must be APPROVED before retest")
    from ai_data_delivery_assurance_copilot.services.defect_rca import retest
    return retest(sdd)
