# Notation Options

## Decision not made

This pilot does not select a final ontology notation, storage format, reasoner,
or validation stack.

The immediate goal is to make the semantics reviewable by humans and editable by
agents.

## Candidate notations

### Markdown

Best for explaining scope, assumptions, rules, and review questions.

Limits:

- weak machine validation;
- easy to drift from the source model.

### YAML

Best for a small, reviewable source model with stable IDs and trace links.

Limits:

- no native ontology semantics;
- needs schema or custom checks for validation.

### Mermaid

Best for GitHub-rendered diagrams that reviewers can inspect without extra
tooling.

Limits:

- diagram-only; not a semantic source of truth.

### RDF/Turtle plus SHACL/SPARQL

Best for semantic graph experiments, closed-world validation rules, and
traceability/impact queries.

Limits:

- introduces graph tooling and vocabulary design work;
- should not be added until the conceptual slice is accepted.

### OML/openCAESAR

Candidate for a later ontology-based systems engineering workflow because it is
closer to engineering ontology practice than raw RDF alone.

Limits:

- requires tooling evaluation;
- requires license/upstream review before deep adoption or vendoring;
- too heavy for this first PR.

### SysML v2

Best for system model elements such as requirements, architecture, behavior,
interfaces, verification cases, and product configurations.

Limits:

- SysML v2 is not selected here as the ontology notation itself;
- adding `.sysml` artifacts would require SysML validation and would turn this
  PR into a tooling PR.

#### SysML v2 domain-specific modeling path

If DE4SDV later maps this pilot into SysML v2, the preferred path is a
domain model library with explicit semantics, not a SysML v1-style profile or a
collection of decorative stereotypes.

Useful SysML v2 alignment principles for later work:

- define DE4SDV product-line concepts in a domain model library first;
- use semantic metadata and user-defined keywords only as shorthand over those
  library-defined concepts;
- require each semantic keyword or metadata annotation to resolve to a base
  semantic type or accepted upstream library concept;
- avoid project-local keyword proliferation that would make DE4SDV models hard
  to exchange or understand outside one tool setup;
- keep the model readable as plain SysML v2 even when DE4SDV shorthand is used.

For future SysML v2 product-line libraries, define both reusable domain
definitions and reusable base usages where appropriate. Definitions keep the
concepts stable; base usages provide contextual anchors that member-product
models can specialize, redefine, or configure.

## Recommended pilot sequence

1. Use Markdown, YAML, and Mermaid in this PR.
2. If reviewers accept the concept, add RDF/Turtle, SHACL, and SPARQL as a
   follow-up experiment.
3. Evaluate OML/openCAESAR only after the pilot has a clear engineering payoff.
4. Map selected concepts to SysML v2 only after the semantics stabilize.
5. When SysML v2 mapping starts, prefer semantic domain libraries before adding
   user-defined keywords or metadata shorthand.

## Possible future mapping

- **Feature** — DE4SDV-specific product-line concept or library element, not a
  raw SysML v2 feature by default.
- **CommonCapability** — Shared capability or model element common to all member
  products.
- **Requirement** — SysML v2 requirement.
- **ArchitectureElement** — Part, action, port, interface, or other SysML v2
  element depending on the case.
- **EvidenceArtifact** — Verification case result or external evidence
  reference.
- **MemberProduct** — Product configuration or variant model element.
- **VariationPoint** — DE4SDV-specific mapping from feature selections to shared
  asset content.
