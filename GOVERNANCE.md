# DE4SDV Governance

## 1. Purpose

This document describes how DE4SDV is maintained, how decisions are made, how contributions are reviewed, and how contributors can grow into more responsible roles over time.

DE4SDV is an open-source project for digitally engineering software-defined vehicle product lines. The project brings together topics such as SysML v2, model-based product-line engineering, digital continuity, digital twin readiness, simulation, compliance, DevSecOps, and continuous homologation.

The governance model is intentionally lightweight. It is designed to help the project move forward clearly and collaboratively without adding unnecessary process too early.

For a general project overview, see [README](README.md).

## 2. Project Status

DE4SDV has moved beyond its initial repository-foundation phase. It is building
a first reviewable engineering baseline around four outcomes:

- contributor-ready scope, workflows, and review paths
- a traceable SysML v2 and product-line systems-engineering backbone
- executable, bounded validation evidence for selected increments
- reproducible baseline, deployment, and release controls

The project roadmap is documented in [ROADMAP](ROADMAP.md).

This governance model may evolve as the project grows, gains contributors, and develops more technical workstreams.

## 3. Maintainers

Maintainers are responsible for guiding the project, reviewing contributions, supporting contributors, and protecting the long-term direction of DE4SDV.

Current maintainers, their areas of responsibility, and their authority are listed in the repository [MAINTAINERS](MAINTAINERS.md).

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

Maintainers do not need to be experts in every DE4SDV topic. Different maintainers may focus on different areas such as governance, documentation, SysML v2, product-line engineering, simulation, compliance, or tooling.

## 5. Roles and Promotion

DE4SDV defines four contributor roles. Roles describe earned trust and authority; they are separate from GitHub's technical permission levels, although each role normally corresponds to a repository permission level.

### Contributor

Everyone who opens an issue, a discussion, or a pull request is a contributor. No special access is required. Contributors:

- follow [CONTRIBUTING](CONTRIBUTING.md)
- can comment on issues, discussions, and pull requests
- can informally review changes, but their reviews do not count as approvals

### Reviewer

A reviewer is a contributor who has demonstrated reliable, constructive work in one or more contribution lanes and has been granted repository write access so that formal GitHub approvals count.

Reviewers:

- can approve pull requests (never their own)
- can triage issues and apply labels
- are expected to review changes in their familiar lanes before maintainer review

Promotion to reviewer requires:

- a track record of merged contributions, typically several, in at least one lane
- consistent and constructive comments on other contributors' work
- a nomination in a public issue by a maintainer, agreed by the lead maintainer

### Maintainer

A maintainer is a reviewer with merge authority and responsibility for the health of one or more project areas (for example governance, documentation, SysML v2 modeling, simulation, compliance, or tooling).

Maintainers:

- approve and merge other contributors' pull requests after the required checks pass
- run privileged maintenance workflows, such as licensed SysML validation
- triage proposals and decide what is in scope
- mentor contributors and reviewers

Promotion to maintainer requires:

- a nomination in a public issue by an existing maintainer
- demonstrated judgment across reviews, not only strong authorship
- agreement of the lead maintainer

### Lead maintainer (repository administrator)

The lead maintainer holds administrator access to the repository and is accountable for the project as a whole. Currently this is the project founder, operating through the `@de4sdv` account (see [MAINTAINERS](MAINTAINERS.md)).

The lead maintainer:

- administers repository settings, branch protection, and secrets
- makes final calls when maintainers disagree
- appoints and, in exceptional cases, revokes reviewer and maintainer roles
- is the fallback approver for urgent maintenance

### Revocation

Roles are earned trust. A role can be revoked by the lead maintainer after a public issue documents the reason. Inactivity alone downgrades a contributor to the previous role and is not treated as a failure.

## 6. Contribution Model

The contribution model is defined in [CONTRIBUTING](CONTRIBUTING.md).

It defines contribution sizes (XS, S, M, L), contribution lanes (modeling, methodology, documentation, simulation, traceability, compliance, DevSecOps, community), the issue templates used for proposals, and a generic proposal path for questions and proposals that do not fit a specialized template.

In summary, contributors should:

- open an issue before starting larger changes
- keep pull requests small and focused
- explain the purpose of their proposed change
- ask maintainers when unsure where a contribution belongs

Maintainers should avoid presenting unfinished placeholder content as a stable contribution process.

## 7. Decision-Making

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

## 8. Pull Request Review and Merge Process

The contribution-side workflow (branching, checks, and validation paths) is defined in [CONTRIBUTING](CONTRIBUTING.md). This section defines who reviews and who merges.

### Normal path

The normal path for every pull request is:

1. The author opens a pull request with a clear purpose and, when appropriate, a linked issue.
2. The required repository checks run on the pull request.
3. A reviewer or maintainer who is **not the author** reviews and approves the pull request. Self-approval is not accepted; GitHub also prevents an author from approving their own pull request.
4. A maintainer merges the pull request after approval and green checks.

Branch protection on `main` enforces parts of this path mechanically:

- direct pushes to `main` are rejected for contributors without administrator
  bypass; project policy requires administrators to use pull requests too
- at least one approving review is required
- required status checks must be up to date with the base branch
- the history is kept linear; pull requests are squash-merged as one commit
- force pushes and branch deletion are disabled
- approving reviews are dismissed when new commits are pushed

Currently, requiring conversations to be resolved and re-approval after the last push are not enforced by branch protection. Maintainers should still ask for unresolved review threads to be addressed and for re-review after substantial new commits.

### Exceptional administrator merges (temporary)

While the maintainer team consists of a single administrator (see [MAINTAINERS](MAINTAINERS.md)), work authored by that administrator cannot always receive an independent approval before merge. Administrator bypass of branch protection is enabled. Rather than pretending otherwise, this governance defines a bounded exception.

The lead maintainer may merge their own pull request using administrator privileges, bypassing the review requirement, only when all of the following hold:

- the change is small, well-understood, and low-risk, or it unblocks CI, deployment, or repository infrastructure;
- the required local checks have been run and passed, including `check_repo`, `smoke_test`, and any focused tests for the change;
- the pull request body records that the merge is an administrator exception,
  why waiting for independent review would cause disproportionate harm, and
  the exact-head validation evidence;
- a follow-up review task is created, as an issue or a pull request comment, so the change receives independent review once another maintainer or reviewer is available.

The exception does not authorize changes to credentials, permissions, or
security settings without explicit project-owner approval.

This exception is temporary. It is expected to narrow as reviewers and maintainers are promoted, and it should become unnecessary once independent review is routinely available.

It must not be used to bypass disagreement, to rush scope changes, or to merge large or risky changes without review. Such changes wait for review.

## 9. Recording Decisions

Important decisions should not disappear in private chats or meetings.

Project decisions should be recorded in one of the following places:

- GitHub Issues
- Pull Request discussions
- architecture decision records in `docs/architecture-decisions/`
- [ROADMAP](ROADMAP.md)
- [GOVERNANCE](GOVERNANCE.md)
- [CONTRIBUTING](CONTRIBUTING.md)

Decisions that change architecture, governance, tooling, or contributor workflow should be captured as an architecture decision record (ADR). For the early phase of DE4SDV, GitHub Issues are the preferred place for working decisions, with durable outcomes promoted into ADRs.

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
```
