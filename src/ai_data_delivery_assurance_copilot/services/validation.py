import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from ai_data_delivery_assurance_copilot.models.contracts import (
    DESDD,
    DQRuleResult,
    DataQualityResult,
    ReconciliationResult,
)
from ai_data_delivery_assurance_copilot.services.synthetic_data import validate_synthetic_data

TARGET_SCHEMA = [
    "loan_id",
    "customer_id",
    "country_code",
    "branch_id",
    "loan_product_id",
    "reporting_month",
    "outstanding_principal",
    "overdue_amount",
    "dpd",
    "risk_bucket",
]

ROOT = Path(__file__).resolve().parents[3]
SOURCE_DIR = ROOT / "data" / "synthetic"
TARGET_PATH = ROOT / "data" / "target" / "monthly_loan_portfolio.csv"


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise ValueError(f"Required dataset not found: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _sources() -> dict[str, list[dict[str, str]]]:
    errors = validate_synthetic_data()
    if errors:
        raise ValueError("Synthetic source validation failed: " + "; ".join(errors))
    names = [
        "loan_master",
        "loan_daily_balance",
        "customer_master",
        "branch_master",
        "country_master",
        "loan_product_master",
        "reporting_calendar",
    ]
    return {name: _read_csv(SOURCE_DIR / f"{name}.csv") for name in names}


def _target() -> list[dict[str, str]]:
    rows = _read_csv(TARGET_PATH)
    if rows and list(rows[0].keys()) != TARGET_SCHEMA:
        raise ValueError("Target schema does not match the approved DE-SDD target schema")
    return rows


def _rule(rule_id: str, description: str, checked: int, failures: list[str]) -> DQRuleResult:
    return DQRuleResult(
        rule_id=rule_id,
        description=description,
        status="PASS" if not failures else "FAIL",
        checked_rows=checked,
        failed_rows=len(failures),
        sample_failures=failures[:5],
    )


def _latest_balance(
    balances: list[dict[str, str]], loan_id: str, month_end: date
) -> dict[str, str] | None:
    candidates = [
        row
        for row in balances
        if row["loan_id"] == loan_id
        and date.fromisoformat(row["balance_date"]) <= month_end
    ]
    return max(candidates, key=lambda row: date.fromisoformat(row["balance_date"])) if candidates else None


def _source_reconciliation(sources: dict[str, list[dict[str, str]]]):
    loans = sources["loan_master"]
    balances = sources["loan_daily_balance"]
    calendar = [
        row for row in sources["reporting_calendar"]
        if row["is_month_end"].lower() == "true"
    ]

    expected: dict[str, tuple[int, Decimal, Decimal]] = {}
    for cal in calendar:
        month = cal["reporting_month"]
        month_end = date.fromisoformat(cal["month_end_date"])
        count = 0
        principal = Decimal("0")
        overdue = Decimal("0")
        for loan in loans:
            start = date.fromisoformat(loan["loan_start_date"])
            close = date.fromisoformat(loan["loan_close_date"]) if loan["loan_close_date"] else None
            if loan["loan_status"] != "ACTIVE" or start > month_end or (close is not None and close <= month_end):
                continue
            balance = _latest_balance(balances, loan["loan_id"], month_end)
            if balance is None:
                continue
            count += 1
            principal += Decimal(balance["outstanding_principal"])
            overdue += Decimal(balance["overdue_amount"])
        expected[month] = (count, principal.quantize(Decimal("0.01")), overdue.quantize(Decimal("0.01")))
    return expected


def run_data_quality_validation(sdd: DESDD) -> DataQualityResult:
    sources = _sources()
    if not TARGET_PATH.exists():
        raise ValueError("Target dataset does not exist. Run deterministic ETL first.")
    target = _target()

    customers = {r["customer_id"]: r for r in sources["customer_master"]}
    branches = {r["branch_id"] for r in sources["branch_master"]}
    products = {r["loan_product_id"] for r in sources["loan_product_master"]}
    countries = {r["country_code"] for r in sources["country_master"]}
    loans = {r["loan_id"]: r for r in sources["loan_master"]}
    month_ends = {r["reporting_month"]: date.fromisoformat(r["month_end_date"]) for r in sources["reporting_calendar"] if r["is_month_end"].lower() == "true"}

    dq: list[DQRuleResult] = []

    dq.append(_rule("DQ-001", "Loan ID is non-null.", len(target), [f"row {i}" for i, r in enumerate(target, 1) if not r["loan_id"].strip()]))
    dq.append(_rule("DQ-002", "Reporting month is non-null.", len(target), [f"row {i}" for i, r in enumerate(target, 1) if not r["reporting_month"].strip()]))

    keys = [(r["loan_id"], r["reporting_month"]) for r in target]
    duplicate_keys = {key for key in keys if keys.count(key) > 1}
    dq.append(_rule("DQ-003", "Loan + Reporting Month is unique.", len(target), [f"{k[0]}|{k[1]}" for k in sorted(duplicate_keys)]))
    dq.append(_rule("DQ-004", "Outstanding principal is non-negative.", len(target), [f"{r['loan_id']}|{r['reporting_month']}" for r in target if Decimal(r["outstanding_principal"]) < 0]))
    dq.append(_rule("DQ-005", "Overdue amount is non-negative.", len(target), [f"{r['loan_id']}|{r['reporting_month']}" for r in target if Decimal(r["overdue_amount"]) < 0]))
    dq.append(_rule("DQ-006", "DPD is non-negative.", len(target), [f"{r['loan_id']}|{r['reporting_month']}" for r in target if int(r["dpd"]) < 0]))

    active_failures = []
    for r in target:
        loan = loans.get(r["loan_id"])
        month_end = month_ends.get(r["reporting_month"])
        if loan is None or month_end is None:
            active_failures.append(f"{r['loan_id']}|{r['reporting_month']}")
            continue
        start = date.fromisoformat(loan["loan_start_date"])
        close = date.fromisoformat(loan["loan_close_date"]) if loan["loan_close_date"] else None
        if loan["loan_status"] != "ACTIVE" or start > month_end or (close is not None and close <= month_end):
            active_failures.append(f"{r['loan_id']}|{r['reporting_month']}")
    dq.append(_rule("DQ-007", "Included loans satisfy the active-on-month-end rule.", len(target), active_failures))
    dq.append(_rule("DQ-008", "Risk bucket is populated.", len(target), [f"{r['loan_id']}|{r['reporting_month']}" for r in target if not r["risk_bucket"].strip()]))

    ref_failures = []
    for r in target:
        if (
            r["customer_id"] not in customers
            or r["branch_id"] not in branches
            or r["loan_product_id"] not in products
            or r["country_code"] not in countries
        ):
            ref_failures.append(f"{r['loan_id']}|{r['reporting_month']}")
    dq.append(_rule("DQ-009", "Customer, branch, product and country reference mappings resolve.", len(target), ref_failures))
    dq.append(_rule("DQ-010", "No duplicate Loan + Reporting Month records exist.", len(target), [f"{k[0]}|{k[1]}" for k in sorted(duplicate_keys)]))

    expected = _source_reconciliation(sources)
    recon: list[ReconciliationResult] = []
    for month, (source_count, source_principal, source_overdue) in expected.items():
        target_rows = [r for r in target if r["reporting_month"] == month]
        target_count = len(target_rows)
        target_principal = sum((Decimal(r["outstanding_principal"]) for r in target_rows), Decimal("0")).quantize(Decimal("0.01"))
        target_overdue = sum((Decimal(r["overdue_amount"]) for r in target_rows), Decimal("0")).quantize(Decimal("0.01"))
        recon.extend([
            ReconciliationResult(rule_id="RECON-001", description=f"Eligible loan count source = target for {month}.", status="PASS" if source_count == target_count else "FAIL", source_value=str(source_count), target_value=str(target_count), difference=str(source_count - target_count)),
            ReconciliationResult(rule_id="RECON-002", description=f"Outstanding principal source = target for {month}.", status="PASS" if source_principal == target_principal else "FAIL", source_value=f"{source_principal:.2f}", target_value=f"{target_principal:.2f}", difference=f"{source_principal - target_principal:.2f}"),
            ReconciliationResult(rule_id="RECON-003", description=f"Overdue amount source = target for {month}.", status="PASS" if source_overdue == target_overdue else "FAIL", source_value=f"{source_overdue:.2f}", target_value=f"{target_overdue:.2f}", difference=f"{source_overdue - target_overdue:.2f}"),
        ])

    all_checks = len(dq) + len(recon)
    failed = sum(1 for r in dq if r.status == "FAIL") + sum(1 for r in recon if r.status == "FAIL")
    return DataQualityResult(
        requirement_id="REQ-001",
        sdd_version=sdd.specification_metadata.version,
        status="PASS" if failed == 0 else "FAIL",
        target_dataset="monthly_loan_portfolio",
        dq_rules=dq,
        reconciliation_rules=recon,
        total_checks=all_checks,
        passed_checks=all_checks - failed,
        failed_checks=failed,
    )
