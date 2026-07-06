# AGENTS.md

Repository-wide instructions for AI coding agents and human contributors using AI tools.

## Project purpose

This repository develops open-source reference assets for systems engineering of Software-Defined Vehicles using SysML v2, MBSE, product-line engineering, digital continuity, digital twins, simulation interoperability, and continuous compliance.

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
- `model-based-product-line-engineering/` — feature models, configurations, shared assets, product models
- `compliance/` — safety, security, UNECE and homologation evidence structure
- `devsecops/` — CI/CD, SBOM, security checks, policy-as-code notes

## Required feedback loop

Before proposing a completed change:

1. Run `python scripts/check_repo.py`
2. Run `python scripts/smoke_test.py`
3. For any change that creates or modifies SysML v2 textual notation, document
   one SysML validation path: local validation evidence from the Syside Editor
   VS Code extension or `python scripts/validate_sysml.py`, or a request for
   maintainer-run privileged Syside validation after review
4. Update relevant files in `docs/` if the change affects
   architecture, workflow, terminology, safety, security, or compliance
   assumptions
5. Include test evidence in the pull request description

## SysML v2 textual notation validation

All generated or modified `.sysml` files under `textual-notation-of-model/`
must be validated before the modeling step is treated as complete.

Use one of the two validation paths:

1. Local validation, if Syside is available, using the Syside Editor VS Code
   extension or the repository wrapper:

```bash
python scripts/validate_sysml.py
```

The wrapper runs Sensmetry SysIDE Modeler CLI validation equivalent to:

```bash
syside check textual-notation-of-model/
```

1. Maintainer-run privileged validation, requested from the pull request after
   initial review. Maintainers run the `Privileged Syside Validation` workflow
   from GitHub Actions with the reviewed branch, tag, or commit SHA and the
   model path to validate.

If validation fails, keep the modeling work in draft state and document the
failure instead of presenting the SysML v2 textual notation as complete.

## Documentation style

- Prefer short, concrete Markdown documents.
- Explain the user problem first, then the technical solution.
- Define domain terms in [`docs/terminology/glossary`](docs/terminology/glossary.md).
- Use Architecture Decision Records in `docs/architecture-decisions/`.
- Avoid inventing compliance claims. Mark evidence as `draft`, `example`, or `not yet validated`.

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
