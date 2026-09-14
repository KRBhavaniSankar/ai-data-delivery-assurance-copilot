<!--
Sync Impact Report
- Version change: empty file -> 1.0.0
- Modified principles: established the required seven DE-SDD specialization principles
- Added sections: Additional Constraints; Development Workflow and Quality Gates; Governance
- Removed sections: placeholder scaffold content
- Follow-up TODOs: none
-->

# AI-Powered SME Data Delivery Assurance Copilot Constitution

## Core Principles

### I. Requirement and Traceability First
Every data product must originate from an explicit business requirement.
Every significant data element, business rule, transformation, DQ rule and
acceptance criterion must be traceable to the approved requirement.

### II. Explicit Data Semantics and Grain
Every data product must explicitly define business meaning, data entities,
target grain, dimensions, measures, derived metrics, relationships,
assumptions and business rules.
Every derived measure must have an explicit and unambiguous formula.

### III. Source-to-Target Lineage
Every target attribute must have documented source lineage wherever
applicable.
Source column, transformation logic and target column must be traceable.
Derived columns must identify their formula and source columns.
AI may propose lineage, but lineage must remain reviewable.

### IV. Data Quality and Reconciliation by Design
Critical data products must define measurable data quality rules before
implementation.
Applicable dimensions include completeness, uniqueness, validity,
referential integrity, consistency, accuracy, timeliness, volume,
financial/data reconciliation and schema compatibility.
Where applicable, financial or aggregate measures must include reconciliation.

### V. Deterministic Validation Is the Proof
LLM output is a proposal, not proof.
LLMs may interpret requirements, identify ambiguity, recommend sources,
generate mappings, DQ rules, SQL/PySpark and RCA hypotheses.
PASS/FAIL must ultimately be determined by deterministic SQL/PySpark or
equivalent executable validation.

### VI. Human Approval and Controlled Change
Business-significant decisions require human approval.
The approved SDD is the delivery contract for implementation.
Changes to business meaning, grain, business rules, critical mappings or
acceptance criteria require a new SDD version and approval cycle.
AI must not silently alter an approved business specification.

### VII. Reproducibility, Observability and Evidence
Material AI-assisted delivery decisions must be reproducible and auditable.
Where applicable retain requirement/version, SDD version, retrieved
knowledge, metadata used, generated assets, validation rules/results,
RCA evidence, model/version, workflow state, human approval and timestamps.

## Additional Constraints

- The hackathon MVP uses synthetic data only.
- The agreed MVP technology stack must remain within the locked project scope.
- Enterprise integrations are mocked for the MVP.
- Real ADO, enterprise catalogs, enterprise LLM gateways and production
  integrations are future enhancements unless explicitly approved.
- AI-generated specifications, mappings, code, DQ rules and RCA hypotheses
  must conform to structured schemas where applicable.
- Pydantic and/or JSON Schema should be used for machine-readable contracts.
- LLM output must not bypass deterministic validation or human approval gates.
- Do not introduce additional autonomous agents or expand the MVP architecture.

## Development Workflow and Quality Gates

Requirement
→ Understand
→ Clarify ambiguity
→ Discover data
→ Create DE-SDD
→ Human approval
→ Generate engineering assets
→ Generate DQ/reconciliation/tests
→ Implement
→ Deterministic validation
→ PASS

Failure path:

VALIDATION
→ FAIL
→ RCA
→ Evidence-based remediation
→ RETEST
→ VALIDATION

Follow the project implementation discipline:

Goal → Design → Implementation → Test → Verify → Freeze → Next layer

## Governance

- The constitution is the governing principles for the DE-SDD workflow.
- The approved SDD is the delivery contract.
- Constitution amendments require documented rationale and versioning.
- Start this constitution at version 1.0.0.
- Use the actual ratification date when the constitution is finalized.
- Do not introduce unrelated software-development principles that are not
  relevant to Data Engineering or this project.

**Version**: 1.0.0 | **Ratified**: 2026-09-14 | **Last Amended**: 2026-09-14
