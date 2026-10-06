# O4 owner decisions — October 2026

**Governance record, not semantic authority.** Runtime consumers and
generators must not read this file. It records the owner's answers that shape
the remaining O4 work so they are reviewable in the repository rather than
only in conversation. The 2026-10-02 topic approvals stay in
[approved-semantic-decisions.yaml](approved-semantic-decisions.yaml); this
record does not change or extend that file.

Decider: Orkun Yilmaz.

## 2026-10-05 — finishing the two plans

| # | Decision | Answer |
|---|---|---|
| 1 | Activate `de4sdv.acceptance.maintainer-decision.v1` | Activate as written (#327). |
| 2 | Meaning of "V1 Core delivered" | Checker proven by an honest real 009D disposition plus independent MC-30 agreement; 009D campaign acceptance is a separate later decision (#327). |
| 3 | Delivery gate | Advisory now; required mode is a later decision. |
| 4 | Privileged PLE requalification run | Authorized once on the exact main SHA; evidence only. |
| 5 | Upstream PLEML contact | Contact maintainers; the owner approves the exact text of every message before it is sent. |
| 6 | Authored ontology YAML end state | Delete `approach/framework/ontology/de4sdv-basic-ontology.yaml` at O4 closure, after every consumer reads model authority and CI proves a rebuild without it. No generated YAML copy. |
| 7 | Feature/common-capability disjointness (open decision 14) | Keep the rule; make it model-resident (#328, checked-constraint fallback). |
| 8 | Canonical architecture source (open decision 10) | `instantiatesCanonicalArchitecture` is vocabulary only (#328). |
| D1–D4 | Engineering defaults | Accepted; see [ADR 0020](../../architecture-decisions/0020-give-ontology-definitions-model-resident-kernel-homes.md). |

## 2026-10-06 — O4 wave plan

The remaining O4 work is delivered in three wave pull requests, so that the
post-squash rebind chain is paid as few times as possible:

- **Wave A — model completeness:** every remaining model and admission change.
- **Wave B — model-authority runtime:** consumers read model authority.
- **Wave C — closure:** remove the last YAML readers and delete the YAML.

Decisions for Wave A:

| Topic | Answer |
|---|---|
| ADR 0020 implementation decisions I1–I4 | Accepted. I4 is superseded by the D4 follow-up in Wave A. |
| `MiddlewareAcceptanceCriterion` and `EvidenceContract` | Drop the `EvidenceContract` specialization. The evidence-contract population is exactly the eight AEBS evidence contracts. |
| Decision 9 — product-line configurator authority | Keep the external catalogue authority (ADR 0006). `FeatureConfiguration` and the selection predicates become model-resident vocabulary only, with no configurator authority. Revisit after the PLE migration. |
| Last edit to the authored YAML | One final mechanical `kernel_sync` edit (mappings and exclusions only) is allowed in Wave A. |
| YAML `validation_rules` R001–R010 | Get model homes in Wave A. |
| YAML `pilot_queries` | Move to test fixtures. |

Still open for later waves: the production cutover to a model-authority
bundle with O3 kept as rollback, including the live-API anchor read-back
(decision 13) (Wave B); and freezing the historical O1/O2/O3 records instead
of regenerating them (Wave C).
