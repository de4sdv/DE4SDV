# Ontology

DE4SDV uses ontology work as a semantics layer for the project, not as a
decorative glossary.

The purpose is to make domain concepts, relationships, constraints, and
traceability questions explicit enough that humans, agents, and tools can
inspect them consistently.

## Role in DE4SDV

Ontology work should help DE4SDV answer engineering questions such as:

- Which product-line characteristics are true features and which are common
  capabilities?
- Which member products select a feature?
- Which requirements, architecture elements, and evidence artifacts are affected
  when a feature changes?
- Which lifecycle artifacts are shared asset supersets, product asset instances,
  or variation points?
- Which model quality rules should become validation checks later?

## Relation to the DE4SDV domain-specific language

The ontology layer is a candidate foundation for a DE4SDV domain-specific
language covering product-line concepts, requirements, architecture, assurance
evidence, release/certification impact, and external alignments.

That does not mean DE4SDV has selected a final ontology stack. Current work
should stay stack-neutral unless an explicit architecture decision says
otherwise.

## Current pilot

The first ontology pilot is [`feature-variability-traceability`](pilots/feature-
variability-traceability/).

It tests a narrow slice:

```text
feature
  -> member product applicability
  -> requirement
  -> architecture element
  -> evidence
  -> release/certification impact
```

The pilot uses Markdown, YAML, and Mermaid only. It adds a minimal
`basic-ontology.yaml` vocabulary and a SYSMOD alignment note, but intentionally
does not introduce RDF, SHACL, SPARQL, OML/openCAESAR, SysML v2 mappings, or
generated ontology artifacts.

## Adoption guardrails

- Start from engineering questions, not from tool preference.
- Keep vocabulary, examples, validation rules, and traceability queries
  separate.
- Treat ISO/IEC 26580 product-line terms as source anchors for feature-based PLE
  vocabulary.
- Do not model common product-line capabilities as features.
- Do not introduce external ontology libraries or generated artifacts without
  license and upstream-review notes.
- Do not treat candidate notation examples as adopted DE4SDV practice.
- Do not create project-local SysML v2 DSML keywords for every modeling
  preference. Domain-specific SysML v2 extensions should be standardized with
  collaborators where possible and grounded in semantic model libraries.
