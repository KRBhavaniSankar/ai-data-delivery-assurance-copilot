from ai_data_delivery_assurance_copilot.models.contracts import (
    DESDD,
    DataDiscoveryResult,
    DiscoveredDataset,
    DiscoveredMapping,
    Evidence,
)
from ai_data_delivery_assurance_copilot.services.catalog import load_catalog
from ai_data_delivery_assurance_copilot.services.rag import LocalRAG


TARGETS = {
    "loan_id": (
        "loan_master",
        "loan_id",
        "DIRECT",
        "Direct source field.",
    ),
    "customer_id": (
        "loan_master",
        "customer_id",
        "DIRECT",
        "Direct source field.",
    ),
    "country_code": (
        "customer_master",
        "country_code",
        "REFERENCE",
        "Resolve customer country through approved country reference data.",
    ),
    "branch_id": (
        "loan_master",
        "branch_id",
        "REFERENCE",
        "Resolve branch through approved branch reference data.",
    ),
    "loan_product_id": (
        "loan_master",
        "loan_product_id",
        "REFERENCE",
        "Resolve loan product through approved product reference data.",
    ),
    "reporting_month": (
        "reporting_calendar",
        "reporting_month",
        "REFERENCE",
        "Calendar defines reporting month.",
    ),
    "outstanding_principal": (
        "loan_daily_balance",
        "outstanding_principal",
        "DIRECT",
        "Select month-end balance.",
    ),
    "overdue_amount": (
        "loan_daily_balance",
        "overdue_amount",
        "DIRECT",
        "Select month-end balance.",
    ),
    "dpd": (
        "loan_daily_balance",
        "dpd",
        "DIRECT",
        "Select month-end DPD.",
    ),
    "risk_bucket": (
        "loan_daily_balance",
        "dpd",
        "DERIVED",
        "Derive from approved DPD risk policy.",
    ),
}


# Reference datasets used to validate/enrich reference-style mappings.
REFERENCE_TABLES = {
    "country_code": "country_master",
    "branch_id": "branch_master",
    "loan_product_id": "loan_product_master",
}


def run_discovery(sdd: DESDD) -> DataDiscoveryResult:
    catalog = load_catalog()
    rag = LocalRAG()

    # Datasets required for the approved DE-SDD.
    required_names = {
        "loan_master",
        "loan_daily_balance",
        "customer_master",
        "branch_master",
        "country_master",
        "loan_product_master",
        "reporting_calendar",
    }

    # ------------------------------------------------------------------
    # 1. Discover relevant datasets from the mock catalog
    # ------------------------------------------------------------------
    datasets = []

    for dataset in catalog:
        if dataset.table_name in required_names:
            datasets.append(
                DiscoveredDataset(
                    table_name=dataset.table_name,
                    relevance=dataset.relevance,
                    reason=dataset.description,
                    evidence=[
                        Evidence(
                            evidence_type="CATALOG",
                            source=dataset.table_name,
                            detail=(
                                f"{len(dataset.columns)} columns; "
                                f"primary key {', '.join(dataset.primary_key)}."
                            ),
                        )
                    ],
                )
            )

    # ------------------------------------------------------------------
    # 2. Discover evidence-backed source-to-target mappings
    # ------------------------------------------------------------------
    mappings = []
    unresolved = []

    for target in sdd.target_data_model.columns:
        spec = TARGETS.get(target)

        # No deterministic mapping rule exists.
        if not spec:
            mappings.append(
                DiscoveredMapping(
                    target_field=target,
                    source_expression="UNKNOWN",
                    mapping_type="UNRESOLVED",
                    rule="No catalog or business-rule evidence found.",
                    status="REQUIRES_CLARIFICATION",
                    evidence=[],
                )
            )

            unresolved.append(target)
            continue

        source_table, source_field, mapping_type, rule = spec

        evidence = []

        # --------------------------------------------------------------
        # 2a. Catalog evidence for the primary source field
        # --------------------------------------------------------------
        source_dataset = next(
            (
                dataset
                for dataset in catalog
                if dataset.table_name == source_table
            ),
            None,
        )

        if source_dataset and any(
            column.name == source_field
            for column in source_dataset.columns
        ):
            evidence.append(
                Evidence(
                    evidence_type="CATALOG",
                    source=source_table,
                    detail=(
                        f"Field {source_field} is present in the catalog."
                    ),
                )
            )

        # --------------------------------------------------------------
        # 2b. Explicit reference-dataset evidence
        # --------------------------------------------------------------
        reference_table = REFERENCE_TABLES.get(target)

        if reference_table:
            reference_dataset = next(
                (
                    dataset
                    for dataset in catalog
                    if dataset.table_name == reference_table
                ),
                None,
            )

            if reference_dataset:
                reference_key = (
                    ", ".join(reference_dataset.primary_key)
                    if reference_dataset.primary_key
                    else "reference key"
                )

                evidence.append(
                    Evidence(
                        evidence_type="CATALOG",
                        source=reference_table,
                        detail=(
                            "Reference dataset discovered; "
                            f"primary key {reference_key}."
                        ),
                    )
                )

        # --------------------------------------------------------------
        # 2c. RAG evidence
        # --------------------------------------------------------------
        evidence.extend(
            rag.search(
                f"{target} {source_field} {rule}",
                top_k=2,
            )
        )

        mappings.append(
            DiscoveredMapping(
                target_field=target,
                source_expression=f"{source_table}.{source_field}",
                mapping_type=mapping_type,
                rule=rule,
                status="RESOLVED",
                evidence=evidence,
            )
        )

    # ------------------------------------------------------------------
    # 3. Retrieve broader business / engineering knowledge
    # ------------------------------------------------------------------
    knowledge_hits = rag.search(
        "reporting month month-end risk bucket DPD latest valid monthly snapshot",
        top_k=5,
    )

    # ------------------------------------------------------------------
    # 4. Return structured discovery result
    # ------------------------------------------------------------------
    return DataDiscoveryResult(
        requirement_id="REQ-001",
        sdd_version=sdd.specification_metadata.version,
        datasets=datasets,
        mappings=mappings,
        knowledge_hits=knowledge_hits,
        unresolved_items=sorted(set(unresolved)),
        engine=rag.engine,
    )