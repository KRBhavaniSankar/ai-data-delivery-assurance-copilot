# Slice 5 Sync

Slice 5 demonstrates the controlled failure path:

1. Start from the clean, approved v1.0 baseline.
2. Inject one controlled negative-principal defect into the target.
3. Run deterministic DQ and functional validation.
4. Produce evidence-based RCA from the failed validation evidence.
5. Remediate by rerunning the approved deterministic ETL from clean sources.
6. Retest DQ and functional validation.
7. Expect PASS after remediation.

The LLM is not the authority for PASS/FAIL. RCA explains observed deterministic evidence. No production or enterprise data is used.
