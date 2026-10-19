# AGENTS.md

Repository-wide instructions for AI coding agents and human contributors using AI tools.

## Project purpose

This repository develops open-source reference assets for the systems engineering of Software-Defined Vehicles. It uses SysML v2, MBSE, product-line engineering, digital continuity, digital twins, simulation interoperability, and continuous compliance.

## Commands agents can run

```bash
python scripts/check_repo.py
python scripts/smoke_test.py
python scripts/validate_sysml.py
```

Optional when available:

```bash
npx markdownlint "**/*.md"
```

## Project structure

- `docs/` — human-facing documentation
- `implementation/` — reference implementation code
- `textual-notation-of-model/` — system model assets
- `sysmlv2-api/` — SysML v2 API integration assets
- `simulation/` — FMU/FMI/SSP integration assets
- `model-based-product-line-engineering/` — feature models, configurations, shared assets, product models, the governed product-line scope
- `compliance/` — safety, security, UNECE and homologation evidence structure
- `devsecops/` — CI/CD, SBOM, security checks, policy-as-code notes

## Required feedback loop

Before proposing a completed change:

1. Run `python scripts/check_repo.py`
2. Run `python scripts/smoke_test.py`
3. If the change creates or modifies SysML v2 textual notation, document one
   SysML validation path:
   - local validation evidence from the Syside Editor VS Code extension or
     `python scripts/validate_sysml.py`, or
   - the licensed CI validation described under "SysML v2 textual notation
     validation". It runs automatically for pull requests that a maintainer
     opens from a branch of this repository. For other pull requests, ask a
     maintainer to run it after initial review.
4. Update relevant files in `docs/` if the change affects
   architecture, workflow, terminology, safety, security, or compliance
   assumptions
5. Include test evidence in the pull request description

## Ontology and kernel-vocabulary alignment

The SysML method kernel (`textual-notation-of-model/packages/methods/de4sdv/`)
is the semantic authority. Its vocabulary reaches consumers through
model-generated projection layers, from which the runtime builds the kernel
contract (`KernelContract.from_layers`, `de4sdv/semantic/model_contract.py`).
The authored basic ontology YAML was deleted in O4 Wave C2; there is no
second semantic authority and no generated YAML copy. Do not weaken or bypass
these gates to make a change pass:

- **Kernel accounting** — the model-projection coverage gate
  (`de4sdv/semantic/model_projection_coverage.py`, run by `check_repo.py` and
  `scripts/check_model_projection_coverage.py`). The equation is a disjoint
  union:

  ```text
  governed kernel declarations
  = model-projected declarations (class pins and relationship-carrier pins)
  + kernel-internal declarations (each with a reason)
  ```

  Kernel-internal declarations are listed in
  `de4sdv/semantic/contract-data/kernel-internal-declarations.yaml` (owner
  decision D3), the only home of that list. Any residual (a retained O4
  register row or a governed declaration without a model provider) fails the
  gate regardless of the baseline.
- **Mapping direction** — `scripts/check_model_sync.py` sync point 5
  (`[ONTOLOGY-KERNEL]` errors). Every class of the model-built kernel contract
  has one well-formed mapping. Every file mapping resolves in its kernel file.
- **R003 groundings** — sync point 6 reads them from
  `constraint ontologyRuleR003` in `de4sdv_ontology_validation_rules.sysml`;
  keep their text format exact.

When a change touches the method kernel:

- Classify every new declaration in a kernel file in the same commit. This
  applies to `part def`, `requirement def`, `enum def` and every other `def`
  kind. Either project the declaration through a model-generated layer, or
  list it as kernel-internal with a non-empty reason in the manifest above.
  Unclassified declarations fail CI.
- Renaming or removing a kernel declaration requires updating its projection
  or kernel-internal entry in the same commit; stale entries fail the gate.
- The projection files are generated from the current sources. If
  `check_repo.py` reports one as stale or missing, regenerate it with its
  generator, as described in
  [`docs/guides/generated-semantic-assets.md`](docs/guides/generated-semantic-assets.md).
  Never hand-edit the JSON. Commit the output together with the source change.
  A model change is one commit and can be squash-merged. Never split it into
  a source commit and a regeneration commit.
- Kernel-internal entries must stay inside the governed directory and must
  not also be projected (as a class pin or a relationship-carrier pin).
- Do not re-declare class-mapped kernel names as local `def`s inside feature
  slices; specialize or import the kernel declarations instead.

The historical records the runtime still serves are frozen; never regenerate
or edit them. See
[`de4sdv/semantic/contract-data/frozen-records.md`](de4sdv/semantic/contract-data/frozen-records.md).
The other historical records are archived at the `release-2026-10-11` tag.

## Model elements earn their place

Two rules for every model change, applied by authors and reviewers alike:

- **Method types come from the kernel.** Types for method concepts come only
  from the ontology and the method kernel. These types say what an increment,
  a scope item, an assumption, a gap, a need, a requirement, a feature
  candidate or an operational context is. A slice may specialize a kernel
  definition. It must do so where the method asks for it: an increment's own
  definition specializes `EngineeringIncrement`. A slice never declares a
  method concept with no kernel base. A new method concept goes through an
  ontology or method pull request first. A domain definition specializes a
  kernel base where one exists.
- **An element earns its place** only if at least one of these is true:
  - (a) a method gate requires it;
  - (b) something consumes it: a trace, a typing, a later phase, or a view
    that frames a concern that a reviewer needs;
  - (c) it carries a decision, assumption or gap that a later phase acts on.

  A doc-only restatement fails all three. Reviewers judge necessity, not only
  correctness.

Rule 11 of the
[increment workflow](methodologies/sysmod-sysmlv2/increment-workflow.md#method-rules-and-the-increment-workflow-model)
states the advisory, never blocking report of the elements that fail (a)
and (b).

## SysML v2 textual notation validation

All generated or modified `.sysml` files under `textual-notation-of-model/`,
`model-based-product-line-engineering/product-models/` and
`model-based-product-line-engineering/scoping/` must be validated before the
modeling step is treated as complete.

Use one of the two validation paths:

1. Local validation, if Syside is available, using the Syside Editor VS Code
   extension or the repository wrapper:

```bash
python scripts/validate_sysml.py
```

The wrapper validates the three model roots together, equivalent to:

```bash
syside check \
  textual-notation-of-model \
  model-based-product-line-engineering/product-models \
  model-based-product-line-engineering/scoping
```

1. Licensed validation in CI. The `Privileged Syside Validation` workflow runs
   on pushes to `main` that change model files. It also runs on such pull
   requests when they come from a branch of this repository and a maintainer
   opened them. For any other pull request, a maintainer runs the workflow from GitHub
   Actions after initial review, with the reviewed branch, tag, or commit SHA.

If validation fails, keep the modeling work in draft state and document the
failure instead of presenting the SysML v2 textual notation as complete.

## Documentation style

- Prefer short, concrete Markdown documents.
- Explain the user problem first, then the technical solution.
- Define domain terms in [`docs/terminology/glossary`](docs/terminology/glossary.md).
- Use Architecture Decision Records in `docs/architecture-decisions/`.
- Avoid inventing compliance claims. Mark evidence as `draft`, `example`, or `not yet validated`.

Write prose 80% of the way to ASD-STE100 (Simplified Technical English). This
applies to documentation, model `doc` comments and pull request descriptions:

- Keep a sentence to 25 words or fewer, and a step to 20 words or fewer.
- Give each sentence one topic. Use a list for a series of items, conditions
  or steps.
- Write a procedure as commands, one action per step. Put a condition before
  its action.
- Use active voice when you know the actor. Do not invent an actor to make a
  sentence active.
- Use the terms of the glossary, the method kernel and SysML v2 exactly, each
  with one meaning. Do not replace them with synonyms or simpler words. For
  example, `NOT_APPLICABLE` is a check verdict, so do not write "not
  applicable" for a condition that is not met.
- Keep open lists open: keep "such as", "for example" and "something".
- Do not apply the STE dictionary. Do not claim that a text conforms to
  ASD-STE100.

When you rewrite existing text, keep every fact, condition, exception and
qualifier. When you split a sentence, carry each condition into every part
that it governs, for example "In that case, …". Compare each rewrite with the
original.

Apply the style to new and changed text. Do not apply it to frozen records or
accepted ADRs. Change generated text through its generator. Do not rewrite
requirement statements to apply this section. They keep their own quality
rules.

## Boundaries

Always:
- Keep specs and docs synchronized with changes.
- Preserve traceability between features, product models, safety/security concerns, and compliance evidence.
- Prefer small, reviewable pull requests.

Ask first:
- Adding external dependencies
- Changing repository structure
- Changing license, governance, or security policy
- Introducing generated model artifacts larger than a small example
- Making claims about compliance, certification, or regulatory approval

Never:
- Commit secrets, credentials, tokens, private keys, or customer data
- Modify generated/vendor files unless explicitly requested
- Delete failing tests to make CI pass
- Present examples as certified or homologated artifacts
- Treat AI-generated safety/security analysis as final expert approval

## Domain-specific expectations

- Safety work should distinguish hazard analysis, risk assessment, safety requirements, and verification evidence.
- Security work should distinguish threat modeling, vulnerability management, SBOM, dependency review, and incident handling.
- Product line engineering work should link feature models, configurations, shared assets, and product models.
- Digital continuity work should preserve traceability across lifecycle artifacts.
- Simulation work should state assumptions about FMI/FMU/SSP versions and tool compatibility.

## Tool-specific files

[`CLAUDE`](CLAUDE.md), `.cursorrules`, [`.github/copilot-instructions`](.github/copilot-instructions.md), and `.cursor/rules/*.mdc` should reference this file as the source of truth to avoid duplicated instructions.
