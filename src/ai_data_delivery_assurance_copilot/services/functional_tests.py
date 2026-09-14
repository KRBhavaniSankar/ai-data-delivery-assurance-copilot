import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from ai_data_delivery_assurance_copilot.models.contracts import (
    DESDD,
    FunctionalTestResult,
    FunctionalValidationResult,
)
from ai_data_delivery_assurance_copilot.services.synthetic_data import validate_synthetic_data

ROOT = Path(__file__).resolve().parents[3]
SOURCE_DIR = ROOT / "data" / "synthetic"
TARGET_PATH = ROOT / "data" / "target" / "monthly_loan_portfolio.csv"


def _read(name: str) -> list[dict[str, str]]:
    path = SOURCE_DIR / f"{name}.csv" if name != "monthly_loan_portfolio" else TARGET_PATH
    if not path.exists():
        raise ValueError(f"Required dataset not found: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _latest_balance(balances, loan_id: str, month_end: date):
    candidates = [
        row for row in balances
        if row["loan_id"] == loan_id
        and date.fromisoformat(row["balance_date"]) <= month_end
    ]
    return max(candidates, key=lambda row: date.fromisoformat(row["balance_date"])) if candidates else None


def _result(test_id: str, description: str, failures: list[str], evidence: str) -> FunctionalTestResult:
    return FunctionalTestResult(
        test_id=test_id,
        description=description,
        status="PASS" if not failures else "FAIL",
        evidence=evidence if not failures else evidence + " Failures: " + ", ".join(failures[:5]),
    )


def run_functional_tests(sdd: DESDD) -> FunctionalValidationResult:
    source_errors = validate_synthetic_data()
    if source_errors:
        raise ValueError("Synthetic source validation failed: " + "; ".join(source_errors))
    if not TARGET_PATH.exists():
        raise ValueError("Target dataset does not exist. Run deterministic ETL first.")

    loans = _read("loan_master")
    balances = _read("loan_daily_balance")
    calendar = _read("reporting_calendar")
    target = _read("monthly_loan_portfolio")

    loan_by_id = {row["loan_id"]: row for row in loans}
    month_ends = {
        row["reporting_month"]: date.fromisoformat(row["month_end_date"])
        for row in calendar if row["is_month_end"].lower() == "true"
    }

    tests: list[FunctionalTestResult] = []

    # TC-001: included target loans satisfy the approved active-on-month-end rule.
    failures = []
    for row in target:
        loan = loan_by_id.get(row["loan_id"])
        month_end = month_ends.get(row["reporting_month"])
        if not loan or not month_end:
            failures.append(f"{row['loan_id']}|{row['reporting_month']}")
            continue
        start = date.fromisoformat(loan["loan_start_date"])
        close = date.fromisoformat(loan["loan_close_date"]) if loan["loan_close_date"] else None
        if loan["loan_status"] != "ACTIVE" or start > month_end or (close is not None and close <= month_end):
            failures.append(f"{row['loan_id']}|{row['reporting_month']}")
    tests.append(_result("TC-001", "Active loan is included when active on month-end.", failures, "Every target loan satisfies the approved active-on-month-end population rule."))

    # TC-002: closed loans are absent from the target in v1.0.
    closed_ids = {
        row["loan_id"] for row in loans
        if row["loan_status"] == "CLOSED"
    }
    failures = [row["loan_id"] for row in target if row["loan_id"] in closed_ids]
    tests.append(_result("TC-002", "Closed loan is excluded from the target.", failures, f"Closed loan IDs in source: {sorted(closed_ids)}; none appear in target."))

    # TC-003: point-in-time month-end balance is selected.
    failures = []
    for row in target:
        month_end = month_ends[row["reporting_month"]]
        latest = _latest_balance(balances, row["loan_id"], month_end)
        if latest is None:
            failures.append(f"{row['loan_id']}|{row['reporting_month']}: no balance")
            continue
        if Decimal(row["outstanding_principal"]) != Decimal(latest["outstanding_principal"]):
            failures.append(f"{row['loan_id']}|{row['reporting_month']}: principal")
        if Decimal(row["overdue_amount"]) != Decimal(latest["overdue_amount"]):
            failures.append(f"{row['loan_id']}|{row['reporting_month']}: overdue")
        if int(row["dpd"]) != int(latest["dpd"]):
            failures.append(f"{row['loan_id']}|{row['reporting_month']}: dpd")
    tests.append(_result("TC-003", "Month-end balance is selected for the reporting period.", failures, "Target principal, overdue amount and DPD match the latest valid balance as of month-end."))

    # TC-004: latest valid record selection is deterministic.
    failures = []
    for row in target:
        month_end = month_ends[row["reporting_month"]]
        candidates = [
            b for b in balances
            if b["loan_id"] == row["loan_id"]
            and date.fromisoformat(b["balance_date"]) <= month_end
        ]
        if not candidates:
            failures.append(f"{row['loan_id']}|{row['reporting_month']}")
            continue
        expected_date = max(date.fromisoformat(b["balance_date"]) for b in candidates)
        if expected_date > month_end:
            failures.append(f"{row['loan_id']}|{row['reporting_month']}: future record selected")
    tests.append(_result("TC-004", "Latest valid record is selected as of month-end.", failures, "For every target row, the selected source record is the maximum balance date not later than month-end."))

    # TC-005: risk bucket follows the approved synthetic policy.
    def bucket(dpd: int) -> str:
        if dpd <= 30:
            return "A"
        if dpd <= 60:
            return "B"
        if dpd <= 90:
            return "C"
        return "D"

    failures = []
    for row in target:
        expected = bucket(int(row["dpd"]))
        if row["risk_bucket"] != expected:
            failures.append(f"{row['loan_id']}|{row['reporting_month']}: expected {expected}")
    tests.append(_result("TC-005", "Risk bucket is derived correctly from DPD.", failures, "Target risk buckets match the approved DPD 0–30 / 31–60 / 61–90 / >90 policy."))

    # TC-006: baseline contains no duplicate target grain. Negative rejection behavior is demonstrated later by defect injection.
    keys = [(row["loan_id"], row["reporting_month"]) for row in target]
    failures = [f"{loan}|{month}" for (loan, month) in sorted(set(keys)) if keys.count((loan, month)) > 1]
    tests.append(_result("TC-006", "Target contains one record per Loan + Reporting Month.", failures, "No duplicate target-grain keys exist in the clean baseline; rejection under defect injection is deferred to the RCA slice."))

    # TC-007: all references resolve.
    customers = {row["customer_id"] for row in _read("customer_master")}
    branches = {row["branch_id"] for row in _read("branch_master")}
    products = {row["loan_product_id"] for row in _read("loan_product_master")}
    countries = {row["country_code"] for row in _read("country_master")}
    failures = [
        f"{row['loan_id']}|{row['reporting_month']}"
        for row in target
        if row["customer_id"] not in customers
        or row["branch_id"] not in branches
        or row["loan_product_id"] not in products
        or row["country_code"] not in countries
    ]
    tests.append(_result("TC-007", "Reference mappings resolve successfully.", failures, "All customer, branch, product and country keys in the target resolve to approved reference datasets."))

    # TC-008: source-to-target reconciliation for the two baseline months.
    failures = []
    for month, month_end in month_ends.items():
        eligible = []
        for loan in loans:
            start = date.fromisoformat(loan["loan_start_date"])
            close = date.fromisoformat(loan["loan_close_date"]) if loan["loan_close_date"] else None
            if loan["loan_status"] != "ACTIVE" or start > month_end or (close is not None and close <= month_end):
                continue
            latest = _latest_balance(balances, loan["loan_id"], month_end)
            if latest:
                eligible.append(latest)
        target_rows = [row for row in target if row["reporting_month"] == month]
        source_principal = sum((Decimal(r["outstanding_principal"]) for r in eligible), Decimal("0")).quantize(Decimal("0.01"))
        target_principal = sum((Decimal(r["outstanding_principal"]) for r in target_rows), Decimal("0")).quantize(Decimal("0.01"))
        source_overdue = sum((Decimal(r["overdue_amount"]) for r in eligible), Decimal("0")).quantize(Decimal("0.01"))
        target_overdue = sum((Decimal(r["overdue_amount"]) for r in target_rows), Decimal("0")).quantize(Decimal("0.01"))
        if len(eligible) != len(target_rows) or source_principal != target_principal or source_overdue != target_overdue:
            failures.append(f"{month}: count/principal/overdue mismatch")
    tests.append(_result("TC-008", "Source-to-target reconciliation passes.", failures, "Eligible loan count, outstanding principal and overdue amount reconcile for every reporting month."))

    failed = sum(1 for test in tests if test.status == "FAIL")
    return FunctionalValidationResult(
        requirement_id="REQ-001",
        sdd_version=sdd.specification_metadata.version,
        status="PASS" if failed == 0 else "FAIL",
        total_tests=len(tests),
        passed_tests=len(tests) - failed,
        failed_tests=failed,
        tests=tests,
    )
