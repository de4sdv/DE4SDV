# Glossary

| Term | Working definition |
|---|---|
| SDV | Software-Defined Vehicle; a vehicle whose behavior and value are increasingly defined by software capabilities. |
| MBSE | Model-Based Systems Engineering. |
| SysML v2 | Next-generation Systems Modeling Language and related API concepts. |
| Concern | Any topic of interest for one or more stakeholders, such as functionality, variability, safety, security, compliance, cost, or evolvability; the questions a view must answer. |
| Viewpoint | A convention that frames one or more concerns: the stakeholders it serves and the way views are expressed. In SysML v2, a `viewpoint def` frames `concern usage` elements. |
| View | The result of applying a viewpoint to the model: a scoped selection of model elements that answers the framed concerns. In SysML v2, a `view` selects a `viewpoint` and exposes the elements needed to answer it. |
| Increment | A bounded, reviewable unit of DE4SDV work that answers one engineering question and leaves behind reviewable artifacts; executed through the 13-phase increment workflow. |
| Phase | One step of the 13-phase increment workflow executed inside an increment (0 framing … 12 baseline). Phases are workflow steps; they never receive identifiers and never name enduring model partitions. See [naming conventions](../naming/naming-conventions.md). |
| Record | An identity-bearing artifact tied to a specific increment, verification activity, runtime, configuration, or decision (evidence record, acceptance criterion, baseline, configured projection). Records keep stable lifecycle identities; see [identifier registry](../naming/naming-conventions.md). |
| MBPLE | Model-Based Product Line Engineering. |
| Feature model | A model of common and variable product capabilities. |
| Feature | A distinguishing characteristic that expresses variability among member products in a product line; in DE4SDV a characteristic stays a feature candidate until member-product variability is shown. |
| Common capability | A capability present in all relevant member products; never modeled as a feature unless it distinguishes member products. |
| Acceptance criterion | A condition used to decide whether a verification result, validation result, evidence artifact, or increment output is acceptable for its stated purpose; kernel `requirement def AcceptanceCriterion`. It is a test-verdict criterion, not an acceptance decision: accepting a result is a separate maintainer record. See [ADR 0020](../architecture-decisions/0020-give-ontology-definitions-model-resident-kernel-homes.md). |
| Evidence contract | A requirement usage that defines the bounded observations, acceptance boundary, and retained-evidence obligations for a verification case; kernel `requirement def EvidenceContract`. Planning vocabulary, not proof that a requirement is verified. See [ADR 0020](../architecture-decisions/0020-give-ontology-definitions-model-resident-kernel-homes.md). |
| Feature configuration | A selected set of features and variation choices defining a product variant; in DE4SDV recorded as a Bill-of-Features under `model-based-product-line-engineering/feature-configurations/`. |
| Shared asset | Reusable engineering artifact used across product variants. |
| Product model | Variant-specific system model assembled from shared assets and configuration decisions. |
| Digital thread | Traceability chain across lifecycle artifacts and decisions, including System 1 product-line artifacts, System 2 engineering and evidence artifacts, and System 3 governance decisions. |
| Digital twin | Digital representation synchronized with real-world system data and assumptions; in DE4SDV, a System 2 capability when used to observe, simulate, assess, or predict aspects of System 1. |
| Digital twin boundary | The declared scope of what a digital twin represents, synchronizes with, and provides credible evidence about. |
| OSLC | Open Services for Lifecycle Collaboration. |
| FMU | Functional Mock-up Unit. |
| FMI | Functional Mock-up Interface. |
| SSP | System Structure and Parameterization. |
| Continuous homologation | Continuous preparation and management of compliance evidence throughout engineering changes; this does not imply legal approval or certification. |
| ASELCM | Agile Systems Engineering Life Cycle Management; used in DE4SDV as a three-system reference framing for engineered systems, their life-cycle management systems, and the innovation ecosystems that evolve those management systems. |
| System 1 | The engineered system. In DE4SDV, the configurable SDV product line and configured vehicle/software variants. |
| System 2 | The life-cycle domain system that manages System 1. In DE4SDV, the project-governed model-based life-cycle engineering and assurance system. |
| System 3 | The innovation ecosystem that manages and evolves System 2. In DE4SDV, the open-source governance, standards, methodology, contributor, review, and toolchain ecosystem. |
| Life Cycle Domain System | The environment of engineering, production, operations, sustainment, verification, validation, evidence, and other capabilities responsible for System 1 across its life cycle. |
| Innovation Ecosystem | The environment of organizations, contributors, standards, methods, tools, and governance mechanisms responsible for improving System 2. |
| System of Access | An intermediate medium or mechanism through which an interaction occurs, such as an API, sensor, actuator, connector, network, or user interface. |
| System-to-software signal mapping | An explicit trace from a logical or semantic information item to a software contract field, physical adapter endpoints, transformation, and realization/evidence status; it may remain a candidate or deferred and does not by itself prove runtime interoperability. |
| Consistency management | The work of checking, maintaining, or reconciling consistency among requirements, designs, models, variants, simulations, evidence, baselines, stakeholder needs, and real-world behavior. |
| Credibility assessment | Structured assessment of how much confidence can be placed in a model, simulation, digital twin, or evidence artifact for a declared purpose and scope. |
| Evidence support citation | A versioned artifact cited as support for an exact scoped claim, with rationale and known limitations; association or citation alone does not establish adequacy, satisfaction or acceptance. |
| Scoped V&V activity | One verification or validation activity with a declared lifecycle subject, configuration, conditions, comparison basis, criteria, responsible actor and retained results. It is not restricted to requirements. |
| VVStatus | The adopted mixed progress/outcome vocabulary for a V&V activity. `Completed` is not automatic PASS, and `CompletedUnsuccessful` means the activity could not complete. Artifact maturity and designated-authority acceptance remain separate. |
| Evidence-set adequacy | A proportionate assessment of retained evidence as a set for an exact claim and scope, against agreed criteria with justified coverage, confidence and rigor. Known limits, contrary results and gaps stay visible; this is separate from authority acceptance. |
| Role-aware scope | A subject identity, configuration identity and set of condition identities, with those roles preserved. Reordering conditions does not change scope; exchanging identities between roles does. |
| Scoped trace obligation | A governed approved-method obligation applicable to the increment's declared scope, phases and completion claim, discharged by the increment's native model relationships (typing, subject and stakeholder membership, connections, framed concerns) rather than category labels, parallel reference slots or a candidate-chosen easier checklist. |
| Imminent collision risk | AEBS term of art: forward collision risk judged by controlled non-activation and activation criteria to require warning or braking intervention within a bounded time window; in DE4SDV draft requirements the criteria and window remain declared gaps (for example `GAP-AEBS-REQ-002`, `GAP-AEBS-REQ-005`) rather than invented thresholds. |
