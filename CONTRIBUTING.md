# Contributing to DE4SDV

Thank you for your interest in contributing to DE4SDV (Digital Engineering for Software-Defined Vehicle).

DE4SDV is an open-source effort focused on model-based, product-line, and continuously certifiable SDV engineering. We welcome contributions from systems engineers, software engineers, safety/compliance specialists, and documentation contributors.

New here? Start with the [getting started guide](docs/getting-started/README.md) for orientation, then come back here for the contribution workflow.

## Contribution sizes

Use these size classes to keep work reviewable:

- **XS (correction):** Correct one specific model/documentation element (naming, relation, typo, constraint mismatch).
- **S (increment):** Add one focused use-case or documentation/methodology slice.
- **M (capability):** Add a new cross-file capability (traceability rule, simulation integration, evidence mapping, etc.).
- **L (epic):** End-to-end changes spanning model + docs + evidence structures.

## Contribution lanes

Contributors can work in one or more lanes:

- **Modeling** — SysML v2 model additions, corrections, and refactoring
- **Methodology** — process definitions, modeling method guidance
- **Documentation** — tutorials, onboarding, terminology, architecture notes
- **Simulation** — FMU/FMI/SSP examples and interoperability guidance
- **Traceability** — lifecycle links between requirements, model, tests, and evidence
- **Compliance** — safety/security/regulatory evidence structure and quality
- **DevSecOps** — repository checks, CI, automation, policy-as-code notes
- **Community** — issue triage, roadmap grooming, mentoring and onboarding

## Ways to contribute

Contributions are welcome in all of the following areas:

- Documentation improvements (clarity, terminology, tutorials, architecture explanations)
- Examples and reference assets (small, practical, educational examples)
- SysML v2 model patterns and modeling guidance
- Feature model / product-line engineering concepts and assets
- Digital continuity, digital thread, and OSLC-related guidance
- Digital twin concepts and integration ideas
- Simulation interoperability concepts (FMI, FMU, SSP)
- Compliance and standards mapping (including assumptions and traceability)
- Issue triage, bug reports, gap analysis, and proposal discussion

If you are unsure where to start, open an issue and describe your background and interests.

For chat access, see [`COMMUNICATION`](COMMUNICATION.md). Mattermost is
invite-only; request an invite through the **Mattermost invite request** issue
template when real-time coordination would help a contribution.

## Model correction protocol (XS)

When correcting existing model elements:

1. Identify the exact model element(s) and file location.
2. Describe current vs expected state.
3. List impacted artifacts (docs/tests/evidence registers).
4. Apply the smallest focused correction.
5. Verify consistency with terminology and traceability.

## Definition of Done (DoD)

A contribution is done when:

- Clear user/project value is documented.
- Traceability to project goals and impacted artifacts is explicit.
- Terminology is consistent with [`docs/terminology/glossary`](docs/terminology/glossary.md).
- Naming and identifiers follow
  [`docs/naming/naming-conventions.md`](docs/naming/naming-conventions.md)
  (enforced by `scripts/check_naming.py`).
- Relevant docs are updated when assumptions or structure change.
- No secrets or unsupported compliance/certification claims are introduced.
- Repository checks pass.

Lane-specific DoD additions:

- **Modeling:** changed element rationale + impacted links documented.
- **Methodology:** process change includes usage guidance and boundaries.
- **Documentation:** includes examples and avoids ambiguous language.
- **Simulation:** states FMI/FMU/SSP version/tool assumptions.
- **Traceability:** links are bidirectional where applicable.
- **Compliance:** marks evidence as draft/example when not validated.
- **DevSecOps:** CI/check changes include expected outcomes.
- **Community:** issue/PR metadata supports discoverability and onboarding.

## Before you start

Use this rule of thumb:

- Small fixes (typos, broken links, minor docs clarifications): open a PR directly.
- Larger changes (new structure, new methods, major examples, governance/process changes): open an issue first and align before implementation.

For larger work, issue-first discussion helps avoid duplicate effort and keeps contributions aligned with project priorities.

## Issue workflow

Please open an issue when you:

- Propose significant new content or direction
- Identify inconsistencies, conceptual conflicts, or missing decisions
- Want to add a substantial example/model set
- Need clarification on expected scope before implementation

When opening an issue, include:

- Problem statement (what is unclear, missing, or inconsistent)
- Proposed change (what you suggest and why)
- Scope and impacted areas (folders, docs, model areas)
- References (standards, papers, prior issues/PRs) when relevant

Use the issue templates in `.github/ISSUE_TEMPLATE/`. The **Question or
contribution proposal** template is the generic path for questions and
proposals that do not fit the model, simulation, or docs/methodology
templates. For informal questions and early ideas, start in
[GitHub Discussions](https://github.com/de4sdv/DE4SDV/discussions); open an
issue when the topic should be tracked and triaged.

## Pull request workflow

1. Fork the repository and create a focused branch.
2. Keep your change scoped to one concern per PR where possible.
3. Update related documentation when structure, assumptions, or terminology changes.
4. Run repository checks locally:

```bash
python scripts/check_repo.py
python scripts/smoke_test.py
```

For public pull requests, CI runs these repository checks without requiring
licensed tools or repository secrets.

### SysML v2 validation gate

Public CI does not run licensed Syside validation on untrusted pull requests.
For pull requests that create or modify `.sysml` files, use one of two
validation paths:

1. **Local validation, if you have Syside access.** Validate changed `.sysml`
   files with the **Syside Editor VS Code extension** or the repository wrapper
   before submitting or updating a PR:

```bash
python -m pip install sysand==0.1.0
sysand sync
python scripts/validate_sysml.py
```

The lock file resolves the pinned grid-view library used by model-defined
tables and matrices. Do not commit `.sysand/`; commit changes to
`.project.json` and `sysand-lock.toml` when intentionally changing a dependency.

2. **Maintainer-run privileged validation.** If local Syside validation is not
   available, request maintainer-run licensed Syside validation in the PR after
   initial review. Include the branch, tag, or commit SHA to validate and the
   model path if it is not `textual-notation-of-model`.

Local Syside validation is recommended when available, but it is not a
prerequisite for contributing.

Maintainer-run validation uses the `Privileged Syside Validation` workflow. It
requires the `SYSIDE_LICENSE_KEY` repository secret and validates a reviewed
branch, tag, or commit SHA without exposing the key to contributors.
The same workflow exports native SysIDE grid views and publishes their CSV and
reviewer-facing SVG representations with the diagram artifact.
Maintainers run it from GitHub Actions by selecting the workflow, choosing
**Run workflow**, and entering the reviewed `ref` and `model_path`.

5. Open a pull request with:
   - Clear title
   - What changed
   - Why it changed
   - Any linked issue(s)
   - Follow-up work (if intentionally out of scope)

## Documentation contribution guidance

Documentation PRs are highly valued. Please:

- Prefer clarity over jargon
- Define terms when introducing domain-specific language
- Keep terminology consistent with existing docs
- Add cross-links to related sections when useful
- Mark assumptions explicitly, especially for compliance/safety claims

## Model and example contribution guidance

For SysML v2 models, product-line artifacts, simulations, or other technical examples:

- Keep examples minimal, executable/inspectable, and well-scoped
- Explain intent, assumptions, and expected learning outcome
- Use consistent naming and structure with neighboring assets
- Avoid claiming standards compliance without traceable evidence
- Include references when patterns are derived from standards or literature

## Proposal guidance

Any proposal — documentation, modeling, simulation, tooling, or governance —
follows the same generic path:

1. Check [GitHub Discussions](https://github.com/de4sdv/DE4SDV/discussions)
   and existing issues for prior discussion of the topic.
2. Open an issue, using the **Question or contribution proposal** template or
   the specialized template that fits, describing the change and the
   motivation.
3. Discuss alternatives and trade-offs in the issue.
4. After maintainer alignment, implement the agreed slice and open a pull
   request linked to the issue.

For governance/process/architecture decisions, additionally:

- State the impact on repository structure and contributor workflow.
- Wait for maintainer alignment before large implementation work.
- Record the durable outcome in an architecture decision record in
  `docs/architecture-decisions/` when it changes architecture, governance,
  tooling, or contributor workflow.

This project values transparent decisions and explicit rationale.

## Reporting problems and inconsistencies

Please report:

- Broken links, stale references, and contradictory statements
- Inconsistent terminology across folders
- Unclear ownership/approval expectations
- Gaps between vision, structure, and implementation guidance

When possible, provide reproduction steps or exact file references.

## Review and approval expectations

Maintainers review PRs for:

- Relevance to project goals and scope
- Clarity and technical coherence
- Consistency with DE4SDV terminology and structure
- Traceability of significant claims or decisions
- Respectful and constructive collaboration

A PR may receive requests for changes before approval.

## Who can approve and merge

Reviewers and maintainers may approve pull requests; maintainers make merge
decisions, as defined in [`GOVERNANCE`](GOVERNANCE.md) and
[`MAINTAINERS`](MAINTAINERS.md).

The pull request author cannot approve their own pull request; the normal
path always requires an independent review. While the maintainer team is a
single administrator, administrator merges of their own pull requests follow
the documented exception path in [`GOVERNANCE`](GOVERNANCE.md): a recorded
reason in the pull request and a follow-up review task.

Role promotion and authority changes follow the public process in
[`GOVERNANCE`](GOVERNANCE.md).

## What to avoid for now

Please avoid:

- Very large, cross-cutting PRs without prior issue discussion
- Unverifiable compliance/safety/security claims
- Major folder restructuring without consensus
- Generated bulk content with no clear review value
- Scope expansion inside an unrelated PR

## Code of Conduct

By participating in this project, you agree to follow the Code of Conduct:

- [`CODE_OF_CONDUCT`](CODE_OF_CONDUCT.md)

## Thank you

We appreciate every meaningful contribution, from typo fixes to deep technical proposals. Thoughtful collaboration is the fastest path to a strong DE4SDV foundation.
