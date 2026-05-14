# Contributing to DE4SDV

Thank you for your interest in contributing to DE4SDV (Digital Engineering for Software-Defined Vehicle).

DE4SDV is an open-source effort focused on model-based, product-line, and continuously certifiable SDV engineering. We welcome contributions from systems engineers, software engineers, safety/compliance specialists, and documentation contributors.

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

Use issue templates in `.github/ISSUE_TEMPLATE/` when available.

## Pull request workflow

1. Fork the repository and create a focused branch.
2. Keep your change scoped to one concern per PR where possible.
3. Update related documentation when structure, assumptions, or terminology changes.
4. Run repository checks locally:

```bash
python scripts/check_repo.py
python scripts/smoke_test.py
```

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

## Decision proposal guidance

For governance/process/architecture decisions:

- Open an issue first
- Present alternatives and trade-offs
- State impact on repository structure and contributor workflow
- Wait for maintainer alignment before large implementation work

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

At this stage, project maintainers are responsible for final approval and merge decisions.

As governance evolves, additional contributor roles and explicit authority levels may be defined in `GOVERNANCE.md`.

## What to avoid for now

Please avoid:

- Very large, cross-cutting PRs without prior issue discussion
- Unverifiable compliance/safety/security claims
- Major folder restructuring without consensus
- Generated bulk content with no clear review value
- Scope expansion inside an unrelated PR

## Code of Conduct

By participating in this project, you agree to follow the Code of Conduct:

- `CODE_OF_CONDUCT.md`

## Thank you

We appreciate every meaningful contribution, from typo fixes to deep technical proposals. Thoughtful collaboration is the fastest path to a strong DE4SDV foundation.
