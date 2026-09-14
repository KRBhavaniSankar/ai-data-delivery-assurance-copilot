from __future__ import annotations

import csv
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from ai_data_delivery_assurance_copilot.models.contracts import (
    DESDD,
    SyntheticDataResult,
    SyntheticDatasetSummary,
)

SEED = 20260915
DATA_START = date(2025, 1, 1)
DATA_END = date(2025, 2, 28)

SCHEMAS: dict[str, list[str]] = {
    "customer_master": ["customer_id", "country_code"],
    "branch_master": ["branch_id", "country_code"],
    "country_master": ["country_code", "country_name"],
    "loan_product_master": ["loan_product_id", "loan_product_name"],
    "loan_master": [
        "loan_id",
        "customer_id",
        "branch_id",
        "loan_product_id",
        "loan_status",
        "loan_start_date",
        "loan_close_date",
    ],
    "loan_daily_balance": [
        "loan_id",
        "balance_date",
        "outstanding_principal",
        "overdue_amount",
        "dpd",
    ],
    "reporting_calendar": [
        "reporting_month",
        "month_end_date",
        "is_month_end",
    ],
}


LOANS = [
    ("L001", "C001", "B001", "P001", "2024-10-01", ""),
    ("L002", "C002", "B002", "P002", "2024-11-01", "2025-01-15"),
    ("L003", "C003", "B001", "P003", "2025-01-10", ""),
    ("L004", "C004", "B003", "P001", "2025-02-10", ""),
    ("L005", "C005", "B002", "P002", "2024-06-01", "2025-02-28"),
    ("L006", "C006", "B003", "P003", "2024-01-01", "2024-12-31"),
    ("L007", "C007", "B001", "P001", "2024-07-01", ""),
    ("L008", "C008", "B002", "P002", "2025-03-01", ""),
    ("L009", "C009", "B003", "P003", "2024-12-15", "2025-02-10"),
    ("L010", "C010", "B001", "P002", "2025-01-31", ""),
    ("L011", "C011", "B002", "P001", "2024-09-01", ""),
    ("L012", "C012", "B003", "P003", "2025-02-28", ""),
]


def _root() -> Path:
    return Path(__file__).resolve().parents[3]


def _write_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def _months() -> list[tuple[str, date]]:
    return [("2025-01", date(2025, 1, 31)), ("2025-02", date(2025, 2, 28))]


def _decimal(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _build_rows() -> dict[str, list[dict[str, str]]]:
    countries = [
        {"country_code": "IN", "country_name": "India"},
        {"country_code": "SG", "country_name": "Singapore"},
        {"country_code": "HK", "country_name": "Hong Kong"},
    ]
    customer_rows = [
        {"customer_id": f"C{i:03d}", "country_code": ["IN", "SG", "HK"][(i - 1) % 3]}
        for i in range(1, 13)
    ]
    branch_rows = [
        {"branch_id": "B001", "country_code": "IN"},
        {"branch_id": "B002", "country_code": "SG"},
        {"branch_id": "B003", "country_code": "HK"},
    ]
    product_rows = [
        {"loan_product_id": "P001", "loan_product_name": "Term Loan"},
        {"loan_product_id": "P002", "loan_product_name": "Working Capital Loan"},
        {"loan_product_id": "P003", "loan_product_name": "Equipment Loan"},
    ]

    loan_rows = []
    for loan_id, customer_id, branch_id, product_id, start, close in LOANS:
        loan_rows.append(
            {
                "loan_id": loan_id,
                "customer_id": customer_id,
                "branch_id": branch_id,
                "loan_product_id": product_id,
                "loan_status": "CLOSED" if close else "ACTIVE",
                "loan_start_date": start,
                "loan_close_date": close,
            }
        )

    calendar_rows = []
    for reporting_month, month_end in _months():
        calendar_rows.append(
            {
                "reporting_month": reporting_month,
                "month_end_date": month_end.isoformat(),
                "is_month_end": "true",
            }
        )

    balance_rows = []
    base_principal = {loan_id: Decimal(10000 + i * 1250) for i, (loan_id, *_rest) in enumerate(LOANS, 1)}

    for loan_index, (loan_id, _customer_id, _branch_id, _product_id, start_text, close_text) in enumerate(LOANS, 1):
        start = max(date.fromisoformat(start_text), DATA_START)
        close = date.fromisoformat(close_text) if close_text else DATA_END
        end = min(close, DATA_END)
        if start > end:
            continue

        current = start
        while current <= end:
            day_number = (current - DATA_START).days
            principal = base_principal[loan_id] - Decimal(day_number * 7 + loan_index * 13)
            principal = max(principal, Decimal("100.00"))
            dpd = (loan_index * 7 + day_number) % 121
            overdue = min(principal * Decimal("0.08"), Decimal(max(dpd, 0)) * Decimal("12.00"))
            balance_rows.append(
                {
                    "loan_id": loan_id,
                    "balance_date": current.isoformat(),
                    "outstanding_principal": _decimal(principal),
                    "overdue_amount": _decimal(overdue),
                    "dpd": str(dpd),
                }
            )
            current += timedelta(days=1)

    return {
        "customer_master": customer_rows,
        "branch_master": branch_rows,
        "country_master": countries,
        "loan_product_master": product_rows,
        "loan_master": loan_rows,
        "loan_daily_balance": balance_rows,
        "reporting_calendar": calendar_rows,
    }


def generate_synthetic_data(sdd: DESDD) -> SyntheticDataResult:
    output_dir = _root() / "data" / "synthetic"
    rows_by_dataset = _build_rows()
    summaries: list[SyntheticDatasetSummary] = []

    for dataset_name, columns in SCHEMAS.items():
        file_name = f"{dataset_name}.csv"
        row_count = _write_csv(
            output_dir / file_name,
            columns,
            rows_by_dataset[dataset_name],
        )
        summaries.append(
            SyntheticDatasetSummary(
                dataset_name=dataset_name,
                file_name=file_name,
                row_count=row_count,
                columns=columns,
            )
        )

    return SyntheticDataResult(
        requirement_id="REQ-001",
        sdd_version=sdd.specification_metadata.version,
        status="GENERATED",
        output_directory="data/synthetic",
        seed=SEED,
        total_rows=sum(item.row_count for item in summaries),
        datasets=summaries,
    )


def validate_synthetic_data() -> list[str]:
    output_dir = _root() / "data" / "synthetic"
    errors: list[str] = []
    for dataset_name, columns in SCHEMAS.items():
        path = output_dir / f"{dataset_name}.csv"
        if not path.exists():
            errors.append(f"Missing file: {path.name}")
            continue
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != columns:
                errors.append(
                    f"{dataset_name}: expected columns {columns}, got {reader.fieldnames}"
                )
            rows = list(reader)
            if not rows:
                errors.append(f"{dataset_name}: no rows")
    return errors
