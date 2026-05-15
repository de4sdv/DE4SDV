# DE4SDV Governance

## 1. Purpose

This document describes how DE4SDV is maintained, how decisions are made, how contributions are reviewed, and how contributors can grow into more responsible roles over time.

DE4SDV is an open-source project for digitally engineering software-defined vehicle product lines. The project brings together topics such as SysML v2, model-based product line engineering, digital continuity, digital twin readiness, simulation, compliance, DevSecOps, and continuous homologation.

The governance model is intentionally lightweight. It is designed to help the project move forward clearly and collaboratively without adding unnecessary process too early.

For a general project overview, see [[`README.md`](README.md)](README.md).

## 2. Project Status

DE4SDV is currently in an early foundation phase.

At this stage, the main priorities are:

- clarifying the project purpose and scope
- improving the repository structure
- reworking placeholder documentation
- defining contribution workflows
- establishing maintainer responsibilities
- preparing the project for future contributors

The project roadmap should be documented in [[`ROADMAP.md`](ROADMAP.md)](ROADMAP.md).

This governance model may evolve as the project grows, gains contributors, and develops more technical workstreams.

## 3. Maintainers

Maintainers are responsible for guiding the project, reviewing contributions, supporting contributors, and protecting the long-term direction of DE4SDV.

Current maintainers are listed in the repository [[`MAINTAINERS.md`](MAINTAINERS.md)](MAINTAINERS.md).

## 4. Maintainer Responsibilities

Maintainers are expected to:

- review issues and pull requests
- help keep the project scope clear
- support new contributors
- improve and maintain documentation quality
- keep the roadmap realistic and understandable
- record important project decisions
- identify and resolve blockers
- encourage respectful and constructive collaboration
- protect the project from unclear, duplicated, or out-of-scope work

Maintainers do not need to be experts in every DE4SDV topic. Different maintainers may focus on different areas such as governance, documentation, SysML v2, product line engineering, simulation, compliance, or tooling.

## 5. Contribution Model

The detailed contribution model for DE4SDV is still being defined.

Because the project is in an early foundation phase, maintainers first need to clarify:

- what kinds of contributions are accepted
- how contributors should propose larger changes
- how documentation, models, examples, and technical concepts should be reviewed
- when contributors should open an issue before starting work
- how pull requests should be reviewed and approved
- which parts of the repository are ready for external contribution

The contribution workflow will be documented in [[`CONTRIBUTING.md`](CONTRIBUTING.md)](CONTRIBUTING.md).

Until [[`CONTRIBUTING.md`](CONTRIBUTING.md)](CONTRIBUTING.md) is finalized, contributors are encouraged to:

- open an issue before starting larger changes
- keep pull requests small and focused
- explain the purpose of their proposed change
- ask maintainers when unsure where a contribution belongs

Maintainers should avoid presenting unfinished placeholder content as a stable contribution process.

## 6. Decision-Making

Most project decisions should happen openly in GitHub Issues or Pull Requests.

DE4SDV uses a lightweight consensus-based approach.

For small changes, approval from one maintainer is usually enough.

Examples of small changes:

- typo fixes
- small documentation improvements
- link updates
- minor formatting changes
- clarification of existing content

For larger decisions, maintainers should aim for agreement through open discussion.

Examples of larger decisions:

- repository structure changes
- roadmap changes
- governance changes
- major documentation rewrites
- new technical workstreams
- changes to project scope
- contribution process changes

A larger decision should normally follow this process:

1. Open an issue describing the decision needed.
2. Discuss the options and trade-offs.
3. Allow maintainers and contributors to comment.
4. Record the agreed direction in the issue.
5. Create follow-up issues if implementation work is needed.

If there are no major objections after discussion, the proposal may move forward.

## 7. Pull Request Review and Merge Process

The detailed pull request workflow will be defined in [[`CONTRIBUTING.md`](CONTRIBUTING.md)](CONTRIBUTING.md).

Until then, pull requests should be handled with a simple lightweight process.

A pull request may be considered for merge when:

- it aligns with the current project scope
- it has a clear purpose
- it is small enough to review
- it is linked to an issue when appropriate
- open questions have been resolved
- at least one maintainer has reviewed it

Small documentation fixes may be merged after one maintainer review.

Larger changes should usually be linked to an issue before they are merged.

Maintainers may request changes before merging a pull request. This is part of the normal review process and should be handled constructively.

## 8. Recording Decisions

Important decisions should not disappear in private chats or meetings.

Project decisions should be recorded in one of the following places:

- GitHub Issues
- Pull Request discussions
- [[`ROADMAP.md`](ROADMAP.md)](ROADMAP.md)
- [[`GOVERNANCE.md`](GOVERNANCE.md)](GOVERNANCE.md)
- [[`CONTRIBUTING.md`](CONTRIBUTING.md)](CONTRIBUTING.md)
- dedicated decision records, if the project later introduces them

For the early phase of DE4SDV, GitHub Issues are the preferred place to record decisions.

When a decision is made during a meeting, a maintainer should add a short summary as a comment to the relevant issue.

Example:

```markdown
## Decision

The maintainer team agreed to use the proposed repository structure for v0.1.

## Rationale

This structure keeps the foundation simple while leaving room for future technical workstreams.

## Follow-up

- Create implementation issue
- Update README.md
- Review placeholder files
