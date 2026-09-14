from fastapi import FastAPI, HTTPException

from ai_data_delivery_assurance_copilot.models.contracts import RequirementInput, ClarificationAnswer, DESDD
from ai_data_delivery_assurance_copilot.services.analyzer import analyze_requirement
from ai_data_delivery_assurance_copilot.services.spec_builder import build_desdd
from ai_data_delivery_assurance_copilot.services.discovery import run_discovery
from ai_data_delivery_assurance_copilot.services.synthetic_data import generate_synthetic_data

app = FastAPI(title="AI Data Delivery Assurance Copilot - Slice 2", version="0.1.0")

@app.get("/health")
def health():
    return {"status": "ok", "slice": 2}

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
