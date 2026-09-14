from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from ai_data_delivery_assurance_copilot.models.contracts import DESDD, ETLResult
from ai_data_delivery_assurance_copilot.services.synthetic_data import SCHEMAS, validate_synthetic_data

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

RISK_BUCKETS = (
    (0, 30, "A"),
    (31, 60, "B"),
    (61, 90, "C"),
)


def _root() -> Path:
    return Path(__file__).resolve().parents[3]


def _source_dir() -> Path:
    return _root() / "data" / "synthetic"


def _target_dir() -> Path:
    return _root() / "data" / "target"


def _read_csv(dataset_name: str) -> list[dict[str, str]]:
    path = _source_dir() / f"{dataset_name}.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _load_sources() -> dict[str, list[dict[str, str]]]:
    errors = validate_synthetic_data()
    if errors:
        raise ValueError("Synthetic source validation failed: " + "; ".join(errors))
    return {name: _read_csv(name) for name in SCHEMAS}


def _risk_bucket(dpd: int) -> str:
    for lower, upper, bucket in RISK_BUCKETS:
        if lower <= dpd <= upper:
            return bucket
    if dpd > 90:
        return "D"
    raise ValueError(f"Unsupported DPD value: {dpd}")


def _month_end_rows(calendar_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = [row for row in calendar_rows if row["is_month_end"].lower() == "true"]
    return sorted(rows, key=lambda row: row["reporting_month"])


def _latest_balance(
    balances: list[dict[str, str]], loan_id: str, month_end: date
) -> dict[str, str] | None:
    candidates = [
        row
        for row in balances
        if row["loan_id"] == loan_id
        and date.fromisoformat(row["balance_date"]) <= month_end
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda row: date.fromisoformat(row["balance_date"]))


def _decimal(value: str) -> str:
    return str(Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def run_etl(sdd: DESDD) -> ETLResult:
    sources = _load_sources()

    customers = {row["customer_id"]: row for row in sources["customer_master"]}
    branches = {row["branch_id"]: row for row in sources["branch_master"]}
    products = {row["loan_product_id"]: row for row in sources["loan_product_master"]}
    countries = {row["country_code"]: row for row in sources["country_master"]}
    loans = sources["loan_master"]
    balances = sources["loan_daily_balance"]

    output_rows: list[dict[str, str]] = []
    active_counts: dict[str, int] = {}
    months = _month_end_rows(sources["reporting_calendar"])

    for calendar_row in months:
        reporting_month = calendar_row["reporting_month"]
        month_end = date.fromisoformat(calendar_row["month_end_date"])
        active_count = 0

        for loan in loans:
            start_date = date.fromisoformat(loan["loan_start_date"])
            close_date = (
                date.fromisoformat(loan["loan_close_date"])
                if loan["loan_close_date"]
                else None
            )

            # v1.0 business rule: active on month-end and closed loans excluded.
            if loan["loan_status"] != "ACTIVE":
                continue
            if start_date > month_end:
                continue
            if close_date is not None and close_date <= month_end:
                continue

            balance = _latest_balance(balances, loan["loan_id"], month_end)
            if balance is None:
                continue

            customer = customers.get(loan["customer_id"])
            branch = branches.get(loan["branch_id"])
            product = products.get(loan["loan_product_id"])
            if customer is None or branch is None or product is None:
                raise ValueError(f"Missing reference data for loan {loan['loan_id']}")

            country_code = customer["country_code"]
            if country_code not in countries:
                raise ValueError(f"Missing country reference for loan {loan['loan_id']}")

            dpd = int(balance["dpd"])
            output_rows.append(
                {
                    "loan_id": loan["loan_id"],
                    "customer_id": loan["customer_id"],
                    "country_code": country_code,
                    "branch_id": loan["branch_id"],
                    "loan_product_id": loan["loan_product_id"],
                    "reporting_month": reporting_month,
                    "outstanding_principal": _decimal(balance["outstanding_principal"]),
                    "overdue_amount": _decimal(balance["overdue_amount"]),
                    "dpd": str(dpd),
                    "risk_bucket": _risk_bucket(dpd),
                }
            )
            active_count += 1

        active_counts[reporting_month] = active_count

    output_rows.sort(key=lambda row: (row["reporting_month"], row["loan_id"]))

    output_dir = _target_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    target_path = output_dir / "monthly_loan_portfolio.csv"
    with target_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=TARGET_SCHEMA)
        writer.writeheader()
        writer.writerows(output_rows)

    return ETLResult(
        requirement_id="REQ-001",
        sdd_version=sdd.specification_metadata.version,
        status="COMPLETED",
        target_dataset="monthly_loan_portfolio",
        target_file="data/target/monthly_loan_portfolio.csv",
        row_count=len(output_rows),
        reporting_months=[row["reporting_month"] for row in months],
        active_loans_by_month=active_counts,
        transformation_steps=[
            "Read validated synthetic source datasets.",
            "Select reporting month-end dates from reporting_calendar.",
            "Apply active-on-month-end population rule and exclude closed loans.",
            "Select latest valid balance record on or before month-end per loan.",
            "Resolve customer, branch, country and loan-product reference data.",
            "Derive risk_bucket from approved DPD policy.",
            "Produce target grain Loan + Reporting Month.",
        ],
        output_schema=TARGET_SCHEMA,
    )
