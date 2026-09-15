from ai_data_delivery_assurance_copilot.models import contracts


def test_cumulative_contract_surface():
    required = [
        "ETLResult", "DataQualityResult", "FunctionalValidationResult",
        "ChangeImpactResult", "DefectInjectionResult", "RCAResult",
        "RemediationResult", "RetestResult",
    ]
    for name in required:
        assert hasattr(contracts, name), name
