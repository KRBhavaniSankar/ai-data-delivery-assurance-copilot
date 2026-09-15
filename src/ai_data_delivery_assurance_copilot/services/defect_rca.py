from pathlib import Path
import csv
from typing import Any

from ai_data_delivery_assurance_copilot.models.contracts import (
    DESDD,
    DefectInjectionResult,
    RCAResult,
    RemediationResult,
    RetestResult,
)
from ai_data_delivery_assurance_copilot.services.etl import run_etl
from ai_data_delivery_assurance_copilot.services.validation import run_data_quality_validation
from ai_data_delivery_assurance_copilot.services.functional_tests import run_functional_tests

ROOT = Path(__file__).resolve().parents[3]
TARGET = ROOT / "data" / "target" / "monthly_loan_portfolio.csv"
BACKUP = ROOT / "data" / "target" / "monthly_loan_portfolio.baseline.csv"


def inject_controlled_defect(sdd: DESDD) -> DefectInjectionResult:
    if not TARGET.exists():
        raise ValueError("Target dataset does not exist. Run deterministic ETL first.")

    rows = list(csv.DictReader(TARGET.open(newline="")))
    if not rows:
        raise ValueError("Target dataset is empty.")

    # Preserve the clean control copy once. The defect is intentionally introduced
    # into one target value so deterministic DQ can prove the failure.
    if not BACKUP.exists():
        BACKUP.write_text(TARGET.read_text())

    row = next((r for r in rows if r["loan_id"] == "L001" and r["reporting_month"] == "2025-01-01"), rows[0])
    original = row["outstanding_principal"]
    row["outstanding_principal"] = f"-{abs(float(original)):.2f}"

    with TARGET.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    return DefectInjectionResult(
        requirement_id="REQ-001",
        sdd_version=sdd.specification_metadata.version,
        defect_id="DEF-001",
        defect_type="NEGATIVE_PRINCIPAL",
        status="INJECTED",
        target_file=str(TARGET),
        affected_record=f"{row['loan_id']} / {row['reporting_month']}",
        original_value=original,
        corrupted_value=row["outstanding_principal"],
        description="Controlled target corruption: outstanding principal was changed to a negative value.",
    )


def run_rca(sdd: DESDD, dq_result: dict[str, Any], functional_result: dict[str, Any]) -> RCAResult:
    failed_dq = [r for r in dq_result.get("dq_rules", []) if r["status"] == "FAIL"]
    failed_tests = [r for r in functional_result.get("tests", []) if r["status"] == "FAIL"]

    evidence = []
    root_cause = "No deterministic root cause established."
    remediation = "Human review required."

    if any(r["rule_id"] == "DQ-004" for r in failed_dq):
        evidence.append("DQ-004 failed: outstanding principal contains a negative value.")
        evidence.append("Controlled defect record DEF-001 targets L001 / 2025-01-01.")
        evidence.append("Clean baseline value was preserved before corruption for comparison.")
        root_cause = "Target dataset was corrupted after ETL: outstanding principal for the controlled record was changed to a negative value."
        remediation = "Regenerate the target from the approved deterministic ETL using the clean synthetic source data, then rerun DQ, reconciliation and functional tests."

    if failed_tests:
        evidence.append("Functional validation also failed after the target corruption.")

    return RCAResult(
        requirement_id="REQ-001",
        sdd_version=sdd.specification_metadata.version,
        status="ROOT_CAUSE_IDENTIFIED" if evidence else "REQUIRES_HUMAN_REVIEW",
        root_cause=root_cause,
        evidence=evidence,
        remediation=remediation,
        deterministic=True,
    )


def remediate(sdd: DESDD) -> RemediationResult:
    # Re-running the approved deterministic ETL restores the target from clean sources.
    result = run_etl(sdd)
    return RemediationResult(
        requirement_id="REQ-001",
        sdd_version=sdd.specification_metadata.version,
        status="REMEDIATED",
        action="Re-ran deterministic ETL from clean synthetic sources.",
        target_file=result.target_file,
    )


def retest(sdd: DESDD) -> RetestResult:
    dq = run_data_quality_validation(sdd)
    functional = run_functional_tests(sdd)
    status = "PASS" if dq.status == "PASS" and functional.status == "PASS" else "FAIL"
    return RetestResult(
        requirement_id="REQ-001",
        sdd_version=sdd.specification_metadata.version,
        status=status,
        dq_status=dq.status,
        functional_status=functional.status,
        dq_passed=dq.passed_checks,
        dq_total=dq.total_checks,
        functional_passed=functional.passed_tests,
        functional_total=functional.total_tests,
    )
