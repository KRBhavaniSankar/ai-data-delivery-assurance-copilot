from test_slice3d import approved_sdd
from ai_data_delivery_assurance_copilot.services.synthetic_data import generate_synthetic_data
from ai_data_delivery_assurance_copilot.services.etl import run_etl
from ai_data_delivery_assurance_copilot.services.validation import run_data_quality_validation
from ai_data_delivery_assurance_copilot.services.functional_tests import run_functional_tests
from ai_data_delivery_assurance_copilot.services.defect_rca import (
    inject_controlled_defect,
    run_rca,
    remediate,
    retest,
    BACKUP,
)


def test_controlled_defect_rca_remediation_retest():
    sdd = approved_sdd()
    if BACKUP.exists():
        BACKUP.unlink()

    generate_synthetic_data(sdd)
    run_etl(sdd)

    defect = inject_controlled_defect(sdd)
    assert defect.status == "INJECTED"
    assert defect.defect_type == "NEGATIVE_PRINCIPAL"

    dq = run_data_quality_validation(sdd)
    functional = run_functional_tests(sdd)
    assert dq.status == "FAIL"
    assert functional.status == "FAIL"

    rca = run_rca(sdd, dq.model_dump(), functional.model_dump())
    assert rca.status == "ROOT_CAUSE_IDENTIFIED"
    assert "negative value" in rca.root_cause.lower()
    assert rca.deterministic is True

    remediation = remediate(sdd)
    assert remediation.status == "REMEDIATED"

    result = retest(sdd)
    assert result.status == "PASS"
    assert result.dq_status == "PASS"
    assert result.functional_status == "PASS"
