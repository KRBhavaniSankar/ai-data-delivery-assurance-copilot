# Slice 3B — Deterministic ETL

## Goal
Transform the approved DE-SDD-backed synthetic source datasets into the monthly loan portfolio target using deterministic, testable rules.

## Flow
APPROVED DE-SDD → Synthetic Sources → Deterministic ETL → Monthly Loan Portfolio Target

## Frozen v1.0 rules implemented
- Active loan population is active on month-end.
- Closed loans are excluded.
- Latest valid balance record on or before month-end is selected.
- Customer country is resolved from customer reference data.
- Branch and loan product references must resolve.
- Risk bucket is deterministically derived from approved DPD policy: 0–30=A, 31–60=B, 61–90=C, >90=D.
- Target grain is Loan + Reporting Month.
- No aggregation is introduced because the target grain is already loan-level.

## Output
`data/target/monthly_loan_portfolio.csv`

Expected baseline: 12 target rows across January and February 2025 (5 in January, 7 in February).

## Not implemented here
DQ execution, reconciliation execution, defect injection, RCA, retesting, production deployment.
