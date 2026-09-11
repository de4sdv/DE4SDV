"""Lane D: advisory delivery projection — acceptance matrix (MC-24, MC-25, MC-30).

Covers the D-owned delivery cases plus the adversarial set required by the
Lane D brief:

- exact-head READY only with every required delivery input satisfied;
- model PASS/FAIL/INDETERMINATE results stay scoped; unsupported required
  delivery obligations block full readiness (MC-25);
- head/base movement during evidence collection is BLOCKED + STALE_INPUT with
  explicit head-moved/base-moved detail; stale CI/review evidence can never
  authorize READY (MC-24);
- required policy change invalidates earlier observations;
- service unavailability is BLOCKED/unknown, never READY;
- evaluator/independent-review disagreement (and timeout/partial outcomes)
  block readiness with an explicit investigation reason (MC-30);
- readiness always names the exact PR target; the projection performs no
  merge/write side effect and never authorizes a merge by itself.

In-memory fakes only; the live adapter is exercised with a captured-call fake
runner (no network).
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from de4sdv.semantic import delivery_gate as dg

REPO = "de4sdv/DE4SDV"
PR = 245
HEAD_A = "a" * 40
HEAD_B = "b" * 40
BASE_A = "1" * 40
BASE_B = "2" * 40


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


def pr_state(*, head: str, base: str, state: str = "open", draft: bool = False) -> dict:
    return {
        "head_sha": head,
        "base_sha": base,
        "state": state,
        "draft": draft,
        "merge_commit_sha": None,
    }


def check_run(name: str, head_sha: str, conclusion: str = "success", status: str = "completed") -> dict:
    return {"name": name, "status": status, "conclusion": conclusion, "head_sha": head_sha}


def review(
    state: str,
    commit_id: str,
    reviewer: str = "maintainer",
    submitted_at: str | None = None,
) -> dict:
    return {
        "state": state,
        "commit_id": commit_id,
        "reviewer": reviewer,
        "submitted_at": submitted_at,
    }


class FakeDeliverySource:
    """Scripted read-only delivery-evidence source."""

    def __init__(
        self,
        *,
        pr_reads,
        checks=(),
        reviews=(),
        changed_files=(),
        policy=None,
        raise_on_checks=None,
        raise_on_policy=None,
    ) -> None:
        self.pr_reads = list(pr_reads)
        self.checks = list(checks)
        self.reviews = list(reviews)
        self.changed_files = list(changed_files)
        self.policy = policy if policy is not None else {"revision": "p1", "required_checks": ["checks"], "required_approvals": 1}
        self.raise_on_checks = raise_on_checks
        self.raise_on_policy = raise_on_policy
        self.read_calls: list[str] = []

    def read_pull_request(self):
        self.read_calls.append("pull_request")
        result = self.pr_reads.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    def read_checks(self, head_sha: str):
        self.read_calls.append(f"checks:{head_sha}")
        if self.raise_on_checks is not None:
            raise self.raise_on_checks
        return list(self.checks)

    def read_reviews(self, head_sha: str):
        self.read_calls.append(f"reviews:{head_sha}")
        return list(self.reviews)

    def read_changed_files(self, head_sha: str):
        self.read_calls.append(f"changed_files:{head_sha}")
        return list(self.changed_files)

    def read_policy_observation(self):
        self.read_calls.append("policy")
        if self.raise_on_policy is not None:
            raise self.raise_on_policy
        return dict(self.policy)


def make_policy(**overrides) -> dg.DeliveryPolicy:
    values = dict(
        policy_id="de4sdv.delivery.advisory.v1",
        revision="p1",
        required_checks=("checks",),
        required_approvals=1,
        require_cross_check=True,
        policy_bearing_paths=(),
        extra_required_obligations=(),
    )
    values.update(overrides)
    return dg.DeliveryPolicy(**values)


def make_conformance(
    *,
    git_commit: str = HEAD_A,
    coverage: str = "ASSESSED",
    state: str | None = "COMPLETE",
    verdict: str | None = "PASS",
) -> dg.ConformanceSummary:
    return dg.ConformanceSummary(
        evaluation_key="k" * 64,
        method_id="de4sdv.method-conformance.pilot.009d.v1",
        contract_id="INC-AEBS-009D",
        contract_digest="c" * 64,
        policy_bundle_id="de4sdv.acceptance.maintainer-decision.v1",
        git_commit=git_commit,
        sysml_project_id="proj",
        sysml_commit_id="commit",
        scope="candidate",
        assessment_coverage=coverage,
        evaluation_state=state,
        conformance_verdict=verdict,
        required_units=("PC-1", "PC-2"),
        failed_ids=(),
        indeterminate_ids=(),
        errored_ids=(),
        unassessed_ids=(),
    )


def agreed_cross_check() -> dg.CrossCheckRecord:
    return dg.CrossCheckRecord(
        parity="agreed",
        parity_detail="API/snapshot canonical payloads identical",
        evaluator_disposition="ASSESSED / INDETERMINATE / null",
        independent_disposition="ASSESSED / INDETERMINATE / null",
        evaluation_key="k" * 64,
        git_commit=HEAD_A,
    )


def make_cross_check(**overrides) -> dg.CrossCheckRecord:
    values = dict(
        parity="agreed",
        parity_detail="API/snapshot canonical payloads identical",
        evaluator_disposition="ASSESSED / INDETERMINATE / null",
        independent_disposition="ASSESSED / INDETERMINATE / null",
        evaluation_key="k" * 64,
        git_commit=HEAD_A,
        contract_digest="",
    )
    values.update(overrides)
    return dg.CrossCheckRecord(**values)


def ready_source() -> FakeDeliverySource:
    return FakeDeliverySource(
        pr_reads=[pr_state(head=HEAD_A, base=BASE_A), pr_state(head=HEAD_A, base=BASE_A)],
        checks=[check_run("checks", HEAD_A)],
        reviews=[review("APPROVED", HEAD_A)],
        changed_files=["docs/readme.md"],
    )


def run_gate(source: FakeDeliverySource, **overrides) -> dict:
    values = dict(
        repository=REPO,
        pr_number=PR,
        policy=make_policy(),
        source=source,
        conformance=make_conformance(),
        cross_check=agreed_cross_check(),
        observed_at="2026-09-11T12:00:00+00:00",
    )
    values.update(overrides)
    return dg.pr_gate_status(**values)


def blocking_reasons(payload: dict) -> list[str]:
    return payload["blocking_reasons"]


# ---------------------------------------------------------------------------
# READY case and readiness target
# ---------------------------------------------------------------------------


def test_exact_head_ready_when_all_required_inputs_satisfied() -> None:
    payload = run_gate(ready_source())
    assert payload["readiness"] == "READY"
    assert blocking_reasons(payload) == []
    assert payload["readiness_target"] == {"type": "PR_MERGE", "id": f"{REPO}#{PR}"}
    assert payload["advisory"] is True
    assert payload["side_effects"] == "none"
    obligations = {item["id"]: item for item in payload["obligations"]}
    assert obligations["model-conformance"]["state"] == "satisfied"
    assert obligations["ci-required-checks"]["state"] == "satisfied"
    assert obligations["review-approval"]["state"] == "satisfied"
    assert obligations["method-change-authorization"]["state"] == "not-applicable"
    assert obligations["cross-check-agreement"]["state"] == "satisfied"
    assert payload["observation"]["head_sha"] == HEAD_A
    assert payload["observation"]["base_sha"] == BASE_A
    assert payload["observation"]["observed_at"] == "2026-09-11T12:00:00+00:00"


def test_readiness_names_exact_pr_target() -> None:
    payload = run_gate(ready_source(), pr_number=245)
    assert payload["readiness_target"]["type"] == "PR_MERGE"
    assert payload["readiness_target"]["id"].endswith("#245")
    # An observation never promises future readiness; the boundary is explicit.
    assert "claim_boundary" in payload
    assert "merge" in payload["merge_authority"]
    assert "advisory" in payload["merge_authority"]


# ---------------------------------------------------------------------------
# MC-25: model result stays scoped; unsupported delivery obligations block
# ---------------------------------------------------------------------------


def test_model_pass_stays_scoped_when_required_obligation_unsupported() -> None:
    source = ready_source()
    policy = make_policy(extra_required_obligations=("cla-signature",))
    conformance = make_conformance()
    payload = run_gate(source, policy=policy, conformance=conformance)
    assert payload["readiness"] == "BLOCKED"
    assert "DELIVERY_OBLIGATION_UNSUPPORTED" in blocking_reasons(payload)
    # The model result is echoed unchanged and remains scoped.
    assert payload["conformance"] == {
        "evaluation_key": conformance.evaluation_key,
        "method_id": conformance.method_id,
        "contract_id": conformance.contract_id,
        "contract_digest": conformance.contract_digest,
        "policy_bundle_id": conformance.policy_bundle_id,
        "git_commit": HEAD_A,
        "sysml_project_id": "proj",
        "sysml_commit_id": "commit",
        "scope": "candidate",
        "assessment_coverage": "ASSESSED",
        "evaluation_state": "COMPLETE",
        "conformance_verdict": "PASS",
    }
    obligations = {item["id"]: item for item in payload["obligations"]}
    assert obligations["cla-signature"]["state"] == "unsupported"
    assert "cla-signature" in payload["unsupported_obligations"]
    assert "model-conformance" in payload["supported_obligations"]


def test_model_fail_remains_blocked() -> None:
    payload = run_gate(
        ready_source(),
        conformance=make_conformance(state="COMPLETE", verdict="FAIL"),
    )
    assert payload["readiness"] == "BLOCKED"
    assert "MODEL_CONFORMANCE_UNSATISFIED" in blocking_reasons(payload)
    obligations = {item["id"]: item for item in payload["obligations"]}
    assert obligations["model-conformance"]["state"] == "failed"
    assert payload["conformance"]["conformance_verdict"] == "FAIL"


def test_model_indeterminate_remains_blocked() -> None:
    payload = run_gate(
        ready_source(),
        conformance=make_conformance(state="INDETERMINATE", verdict=None),
    )
    assert payload["readiness"] == "BLOCKED"
    assert "MODEL_CONFORMANCE_UNSATISFIED" in blocking_reasons(payload)


def test_missing_model_result_blocks() -> None:
    payload = run_gate(ready_source(), conformance=None)
    assert payload["readiness"] == "BLOCKED"
    assert "MODEL_CONFORMANCE_UNSATISFIED" in blocking_reasons(payload)
    assert payload["conformance"] is None


def test_model_result_for_other_revision_blocks() -> None:
    payload = run_gate(ready_source(), conformance=make_conformance(git_commit=HEAD_B))
    assert payload["readiness"] == "BLOCKED"
    obligations = {item["id"]: item for item in payload["obligations"]}
    assert obligations["model-conformance"]["state"] == "failed"
    assert "MODEL_RESULT_MISMATCH" in obligations["model-conformance"]["diagnostics"][0] or (
        "does not match" in " ".join(obligations["model-conformance"]["diagnostics"])
    )


# ---------------------------------------------------------------------------
# MC-24: exact-head race protection and stale evidence
# ---------------------------------------------------------------------------


def test_head_moved_during_evidence_collection_blocks_stale() -> None:
    source = FakeDeliverySource(
        pr_reads=[pr_state(head=HEAD_A, base=BASE_A), pr_state(head=HEAD_B, base=BASE_A)],
        checks=[check_run("checks", HEAD_A)],
        reviews=[review("APPROVED", HEAD_A)],
    )
    payload = run_gate(source)
    assert payload["readiness"] == "BLOCKED"
    assert "STALE_INPUT" in blocking_reasons(payload)
    assert payload["observation"]["head_moved"] is True
    assert payload["observation"]["base_moved"] is False
    assert payload["observation"]["head_sha"] == HEAD_B
    assert payload["observation"]["head_sha_before"] == HEAD_A
    diagnostics = " ".join(payload["diagnostics"])
    assert HEAD_A in diagnostics and HEAD_B in diagnostics
    # No successful delivery verdict was published from stale evidence.
    assert payload["obligations"] == []


def test_base_moved_during_evidence_collection_blocks_stale() -> None:
    source = FakeDeliverySource(
        pr_reads=[pr_state(head=HEAD_A, base=BASE_A), pr_state(head=HEAD_A, base=BASE_B)],
        checks=[check_run("checks", HEAD_A)],
        reviews=[review("APPROVED", HEAD_A)],
    )
    payload = run_gate(source)
    assert payload["readiness"] == "BLOCKED"
    assert "STALE_INPUT" in blocking_reasons(payload)
    assert payload["observation"]["base_moved"] is True
    assert payload["observation"]["head_moved"] is False


def test_stale_ci_evidence_cannot_authorize_ready() -> None:
    source = FakeDeliverySource(
        pr_reads=[pr_state(head=HEAD_A, base=BASE_A), pr_state(head=HEAD_A, base=BASE_A)],
        checks=[check_run("checks", HEAD_B)],  # bound to a previous head
        reviews=[review("APPROVED", HEAD_A)],
    )
    payload = run_gate(source)
    assert payload["readiness"] == "BLOCKED"
    obligations = {item["id"]: item for item in payload["obligations"]}
    assert obligations["ci-required-checks"]["state"] in {"unassessed", "failed"}
    assert "DELIVERY_OBLIGATION_UNASSESSED" in blocking_reasons(payload) or (
        "DELIVERY_OBLIGATION_FAILED" in blocking_reasons(payload)
    )


def test_stale_review_evidence_cannot_authorize_ready() -> None:
    source = FakeDeliverySource(
        pr_reads=[pr_state(head=HEAD_A, base=BASE_A), pr_state(head=HEAD_A, base=BASE_A)],
        checks=[check_run("checks", HEAD_A)],
        reviews=[review("APPROVED", HEAD_B)],  # approval bound to a previous head
    )
    payload = run_gate(source)
    assert payload["readiness"] == "BLOCKED"
    obligations = {item["id"]: item for item in payload["obligations"]}
    assert obligations["review-approval"]["state"] == "failed"
    assert "DELIVERY_OBLIGATION_FAILED" in blocking_reasons(payload)


def test_required_check_failed_blocks() -> None:
    source = FakeDeliverySource(
        pr_reads=[pr_state(head=HEAD_A, base=BASE_A), pr_state(head=HEAD_A, base=BASE_A)],
        checks=[check_run("checks", HEAD_A, conclusion="failure")],
        reviews=[review("APPROVED", HEAD_A)],
    )
    payload = run_gate(source)
    assert payload["readiness"] == "BLOCKED"
    obligations = {item["id"]: item for item in payload["obligations"]}
    assert obligations["ci-required-checks"]["state"] == "failed"


def test_unknown_required_check_obligation_blocks() -> None:
    source = FakeDeliverySource(
        pr_reads=[pr_state(head=HEAD_A, base=BASE_A), pr_state(head=HEAD_A, base=BASE_A)],
        checks=[],
        reviews=[review("APPROVED", HEAD_A)],
    )
    payload = run_gate(source)
    assert payload["readiness"] == "BLOCKED"
    assert "DELIVERY_OBLIGATION_UNASSESSED" in blocking_reasons(payload)


# ---------------------------------------------------------------------------
# Policy revision and terminal targets
# ---------------------------------------------------------------------------


def test_policy_change_invalidates_earlier_observation() -> None:
    source = ready_source()
    source.policy = {"revision": "p2", "required_checks": ["checks"], "required_approvals": 1}
    payload = run_gate(source)
    assert payload["readiness"] == "BLOCKED"
    assert "POLICY_REVISION_MISMATCH" in blocking_reasons(payload)
    assert payload["policy"]["revision"] == "p1"
    assert payload["policy"]["observed_revision"] == "p2"


def test_policy_revision_is_required() -> None:
    with pytest.raises(ValueError, match="revision"):
        run_gate(ready_source(), policy=make_policy(revision=""))


def test_terminal_target_is_blocked_not_open() -> None:
    source = FakeDeliverySource(
        pr_reads=[
            pr_state(head=HEAD_A, base=BASE_A, state="merged"),
            pr_state(head=HEAD_A, base=BASE_A, state="merged"),
        ],
        checks=[check_run("checks", HEAD_A)],
        reviews=[review("APPROVED", HEAD_A)],
    )
    payload = run_gate(source)
    assert payload["readiness"] == "BLOCKED"
    assert "TARGET_NOT_OPEN" in blocking_reasons(payload)
    assert payload["observation"]["state"] == "merged"


# ---------------------------------------------------------------------------
# Service unavailability
# ---------------------------------------------------------------------------


def test_service_unavailable_never_ready() -> None:
    source = FakeDeliverySource(
        pr_reads=[dg.DeliveryEvidenceError("gh: API rate limited")],
    )
    payload = run_gate(source)
    assert payload["readiness"] == "BLOCKED"
    assert "EVIDENCE_UNAVAILABLE" in blocking_reasons(payload)
    assert payload["observation"]["head_sha"] is None
    assert payload["obligations"] == []


def test_evidence_collection_failure_never_ready() -> None:
    source = FakeDeliverySource(
        pr_reads=[pr_state(head=HEAD_A, base=BASE_A), pr_state(head=HEAD_A, base=BASE_A)],
        checks=[],
        reviews=[],
        raise_on_checks=dg.DeliveryEvidenceError("check-runs endpoint unavailable"),
    )
    payload = run_gate(source)
    assert payload["readiness"] == "BLOCKED"
    assert "EVIDENCE_UNAVAILABLE" in blocking_reasons(payload)


# ---------------------------------------------------------------------------
# MC-30: disagreement handling
# ---------------------------------------------------------------------------


def test_disagreement_blocks_with_investigation_reason() -> None:
    cross = dg.CrossCheckRecord(
        parity="disagreed",
        parity_detail="API/snapshot payloads differ in PC-009D-SCOPE-EQUALITY",
        evaluator_disposition="ASSESSED / INDETERMINATE / null",
        independent_disposition="COMPLETE / FAIL",
        evaluation_key="k" * 64,
        git_commit=HEAD_A,
    )
    payload = run_gate(ready_source(), cross_check=cross)
    assert payload["readiness"] == "BLOCKED"
    assert "EVALUATION_DISAGREEMENT" in blocking_reasons(payload)
    obligations = {item["id"]: item for item in payload["obligations"]}
    assert obligations["cross-check-agreement"]["state"] == "failed"
    assert any(
        "investigation" in item.lower()
        for item in obligations["cross-check-agreement"]["diagnostics"]
    )


def test_timeout_or_partial_never_counts_as_acceptance() -> None:
    for parity in ("timeout", "partial", "not-run"):
        payload = run_gate(
            ready_source(),
            cross_check=make_cross_check(parity=parity),
        )
        assert payload["readiness"] == "BLOCKED"
        assert "AGREEMENT_UNESTABLISHED" in blocking_reasons(payload)


def test_missing_cross_check_when_required_blocks() -> None:
    payload = run_gate(ready_source(), cross_check=None)
    assert payload["readiness"] == "BLOCKED"
    assert "AGREEMENT_UNESTABLISHED" in blocking_reasons(payload)


def test_cross_check_not_required_when_policy_says_so() -> None:
    payload = run_gate(
        ready_source(), policy=make_policy(require_cross_check=False), cross_check=None
    )
    assert payload["readiness"] == "READY"


# ---------------------------------------------------------------------------
# Method-change authorization (policy-bearing closure guard)
# ---------------------------------------------------------------------------


def test_policy_bearing_change_requires_authorization_support() -> None:
    source = FakeDeliverySource(
        pr_reads=[pr_state(head=HEAD_A, base=BASE_A), pr_state(head=HEAD_A, base=BASE_A)],
        checks=[check_run("checks", HEAD_A)],
        reviews=[review("APPROVED", HEAD_A)],
        changed_files=["de4sdv/semantic/method_evaluator.py", "docs/readme.md"],
    )
    policy = make_policy(policy_bearing_paths=("de4sdv/semantic/",))
    payload = run_gate(source, policy=policy)
    assert payload["readiness"] == "BLOCKED"
    obligations = {item["id"]: item for item in payload["obligations"]}
    assert obligations["method-change-authorization"]["state"] == "unsupported"
    assert "DELIVERY_OBLIGATION_UNSUPPORTED" in blocking_reasons(payload)


# ---------------------------------------------------------------------------
# Read-only boundary
# ---------------------------------------------------------------------------


def test_gate_payload_is_advisory_only() -> None:
    payload = run_gate(ready_source())
    assert payload["advisory"] is True
    assert payload["side_effects"] == "none"
    assert "merge" in payload["merge_authority"]
    assert payload["query"] == "pr_gate_status"


def test_delivery_reason_vocabulary_is_finite() -> None:
    assert dg.DELIVERY_REASONS == frozenset(
        {
            "STALE_INPUT",
            "MODEL_CONFORMANCE_UNSATISFIED",
            "DELIVERY_OBLIGATION_UNSUPPORTED",
            "DELIVERY_OBLIGATION_UNASSESSED",
            "DELIVERY_OBLIGATION_FAILED",
            "EVIDENCE_UNAVAILABLE",
            "EVALUATION_DISAGREEMENT",
            "AGREEMENT_UNESTABLISHED",
            "TARGET_NOT_OPEN",
            "TARGET_NOT_READY",
            "POLICY_REVISION_MISMATCH",
        }
    )


# ---------------------------------------------------------------------------
# R2: cross-check evidence bound to the exact evaluation/head
# ---------------------------------------------------------------------------


def test_r2_agreement_bound_to_exact_evaluation_and_head_satisfied() -> None:
    payload = run_gate(ready_source(), cross_check=make_cross_check())
    assert payload["readiness"] == "READY"
    obligations = {item["id"]: item for item in payload["obligations"]}
    assert obligations["cross-check-agreement"]["state"] == "satisfied"


def test_r2_agreement_for_previous_head_blocks() -> None:
    payload = run_gate(
        ready_source(), cross_check=make_cross_check(git_commit=HEAD_B)
    )
    assert payload["readiness"] == "BLOCKED"
    assert "AGREEMENT_UNESTABLISHED" in blocking_reasons(payload)
    obligations = {item["id"]: item for item in payload["obligations"]}
    assert obligations["cross-check-agreement"]["state"] == "failed"
    assert any(
        "foreign comparison" in diagnostic
        for diagnostic in obligations["cross-check-agreement"]["diagnostics"]
    )


def test_r2_agreement_with_foreign_evaluation_key_blocks() -> None:
    payload = run_gate(
        ready_source(), cross_check=make_cross_check(evaluation_key="x" * 64)
    )
    assert payload["readiness"] == "BLOCKED"
    assert "AGREEMENT_UNESTABLISHED" in blocking_reasons(payload)


def test_r2_missing_cross_check_identity_blocks() -> None:
    for record in (
        make_cross_check(evaluation_key=""),
        make_cross_check(git_commit=""),
    ):
        payload = run_gate(ready_source(), cross_check=record)
        assert payload["readiness"] == "BLOCKED"
        assert "AGREEMENT_UNESTABLISHED" in blocking_reasons(payload)
        obligations = {item["id"]: item for item in payload["obligations"]}
        assert obligations["cross-check-agreement"]["state"] == "unassessed"


def test_r2_foreign_contract_digest_blocks() -> None:
    payload = run_gate(
        ready_source(), cross_check=make_cross_check(contract_digest="d" * 64)
    )
    assert payload["readiness"] == "BLOCKED"
    assert "AGREEMENT_UNESTABLISHED" in blocking_reasons(payload)


# ---------------------------------------------------------------------------
# R3: a Draft PR never projects READY
# ---------------------------------------------------------------------------


def test_r3_draft_pr_never_ready() -> None:
    source = FakeDeliverySource(
        pr_reads=[
            pr_state(head=HEAD_A, base=BASE_A, draft=True),
            pr_state(head=HEAD_A, base=BASE_A, draft=True),
        ],
        checks=[check_run("checks", HEAD_A)],
        reviews=[review("APPROVED", HEAD_A)],
    )
    payload = run_gate(source)
    assert payload["readiness"] == "BLOCKED"
    assert "TARGET_NOT_READY" in blocking_reasons(payload)
    assert "TARGET_NOT_OPEN" not in blocking_reasons(payload)
    assert payload["observation"]["draft"] is True
    assert payload["observation"]["draft_moved"] is False


def test_r3_same_pr_after_undraft_ready() -> None:
    # ready_source() is not a draft; all obligations satisfied -> READY.
    payload = run_gate(ready_source())
    assert payload["readiness"] == "READY"
    assert "TARGET_NOT_READY" not in blocking_reasons(payload)
    assert payload["observation"]["draft"] is False


def test_r3_draft_change_during_observation_blocks() -> None:
    source = FakeDeliverySource(
        pr_reads=[
            pr_state(head=HEAD_A, base=BASE_A, draft=True),
            pr_state(head=HEAD_A, base=BASE_A, draft=False),
        ],
        checks=[check_run("checks", HEAD_A)],
        reviews=[review("APPROVED", HEAD_A)],
    )
    payload = run_gate(source)
    assert payload["readiness"] == "BLOCKED"
    assert "STALE_INPUT" in blocking_reasons(payload)
    assert payload["observation"]["draft_moved"] is True
    assert payload["observation"]["draft"] is False
    assert payload["observation"]["draft_before"] is True
    assert payload["obligations"] == []


# ---------------------------------------------------------------------------
# R4: distinct effective approvers, not approval records
# ---------------------------------------------------------------------------


def _review_source(reviews: list[dict]) -> FakeDeliverySource:
    return FakeDeliverySource(
        pr_reads=[pr_state(head=HEAD_A, base=BASE_A), pr_state(head=HEAD_A, base=BASE_A)],
        checks=[check_run("checks", HEAD_A)],
        reviews=reviews,
    )


def test_r4_same_reviewer_double_approval_counts_once() -> None:
    source = _review_source(
        [
            review("APPROVED", HEAD_A, "alice", "2026-09-11T10:00:00Z"),
            review("APPROVED", HEAD_A, "alice", "2026-09-11T11:00:00Z"),
        ]
    )
    payload = run_gate(source, policy=make_policy(required_approvals=2))
    assert payload["readiness"] == "BLOCKED"
    obligations = {item["id"]: item for item in payload["obligations"]}
    assert obligations["review-approval"]["state"] == "failed"
    # evidence lists the one counted distinct reviewer
    assert len(obligations["review-approval"]["evidence"]) == 1


def test_r4_two_distinct_reviewers_satisfy() -> None:
    source = _review_source(
        [
            review("APPROVED", HEAD_A, "alice", "2026-09-11T10:00:00Z"),
            review("APPROVED", HEAD_A, "bob", "2026-09-11T11:00:00Z"),
        ]
    )
    payload = run_gate(source, policy=make_policy(required_approvals=2))
    assert payload["readiness"] == "READY"


def test_r4_old_head_plus_exact_head_approval_from_same_user_counts_once() -> None:
    source = _review_source(
        [
            review("APPROVED", HEAD_B, "alice", "2026-09-11T10:00:00Z"),
            review("APPROVED", HEAD_A, "alice", "2026-09-11T11:00:00Z"),
        ]
    )
    payload = run_gate(source, policy=make_policy(required_approvals=2))
    assert payload["readiness"] == "BLOCKED"
    obligations = {item["id"]: item for item in payload["obligations"]}
    assert len(obligations["review-approval"]["evidence"]) == 1
    assert obligations["review-approval"]["evidence"][0]["commit_id"] == HEAD_A


def test_r4_changes_requested_supersedes_exact_head_approval() -> None:
    source = _review_source(
        [
            review("APPROVED", HEAD_A, "alice", "2026-09-11T10:00:00Z"),
            review("CHANGES_REQUESTED", HEAD_A, "alice", "2026-09-11T11:00:00Z"),
        ]
    )
    payload = run_gate(source)
    assert payload["readiness"] == "BLOCKED"
    obligations = {item["id"]: item for item in payload["obligations"]}
    assert obligations["review-approval"]["state"] == "failed"


def test_r4_dismissed_approval_not_counted() -> None:
    source = _review_source(
        [
            review("APPROVED", HEAD_A, "alice", "2026-09-11T10:00:00Z"),
            review("DISMISSED", HEAD_A, "alice", "2026-09-11T11:00:00Z"),
        ]
    )
    payload = run_gate(source)
    assert payload["readiness"] == "BLOCKED"
    obligations = {item["id"]: item for item in payload["obligations"]}
    assert obligations["review-approval"]["state"] == "failed"


def test_r4_later_comment_does_not_revoke_approval() -> None:
    # GitHub review semantics: a COMMENTED record is not a decision state and
    # does not supersede an earlier APPROVED decision from the same reviewer.
    source = _review_source(
        [
            review("APPROVED", HEAD_A, "alice", "2026-09-11T10:00:00Z"),
            review("COMMENTED", HEAD_A, "alice", "2026-09-11T11:00:00Z"),
        ]
    )
    payload = run_gate(source)
    assert payload["readiness"] == "READY"


# ---------------------------------------------------------------------------
# gh CLI adapter: read-only commands, correct mapping, unavailability
# ---------------------------------------------------------------------------


class FakeRunner:
    def __init__(self, responses) -> None:
        self.responses = list(responses)
        self.commands: list[list[str]] = []

    def __call__(self, command, **kwargs):
        self.commands.append(list(command))
        status, stdout = self.responses.pop(0)
        return SimpleNamespace(returncode=status, stdout=stdout, stderr="")


def test_gh_source_maps_pr_state_and_checks() -> None:
    runner = FakeRunner(
        [
            (0, json.dumps({"head": {"sha": HEAD_A}, "base": {"sha": BASE_A}, "state": "open", "draft": True, "merge_commit_sha": None})),
            (0, json.dumps({"total_count": 1, "check_runs": [check_run("checks", HEAD_A)]})),
            (0, json.dumps([{"state": "APPROVED", "commit_id": HEAD_A, "user": {"login": "maintainer"}, "submitted_at": "2026-09-11T10:00:00Z"}])),
            (0, json.dumps([{"filename": "docs/x.md"}])),
            (0, json.dumps({"required_status_checks": {"contexts": ["checks"]}, "required_pull_request_reviews": {"required_approving_review_count": 1}})),
        ]
    )
    source = dg.GhCliDeliverySource(repository=REPO, pr_number=PR, runner=runner)
    assert source.read_pull_request()["head_sha"] == HEAD_A
    assert source.read_checks(HEAD_A) == [check_run("checks", HEAD_A)]
    assert source.read_reviews(HEAD_A) == [
        {
            "state": "APPROVED",
            "commit_id": HEAD_A,
            "reviewer": "maintainer",
            "submitted_at": "2026-09-11T10:00:00Z",
        }
    ]
    assert source.read_changed_files(HEAD_A) == ["docs/x.md"]
    policy = source.read_policy_observation()
    assert policy["required_checks"] == ["checks"]
    assert policy["required_approvals"] == 1
    assert len(policy["revision"]) == 64
    # Every issued command is read-only.
    for command in runner.commands:
        assert command[0] == "gh"
        assert command[1] == "api"
        assert "--method" not in command
        assert "DELETE" not in command and "PATCH" not in command and "PUT" not in command
        assert "merge" not in command


def test_gh_pagination_fails_closed_when_incomplete() -> None:
    # Full pages forever and no terminal page within the bound -> never used.
    full_page = json.dumps([{"state": "COMMENTED", "commit_id": HEAD_A}] * 100)
    runner = FakeRunner([(0, full_page)] * 11)
    source = dg.GhCliDeliverySource(repository=REPO, pr_number=PR, runner=runner)
    with pytest.raises(dg.DeliveryEvidenceError, match="pagination"):
        source.read_reviews(HEAD_A)


def test_gh_check_runs_pagination_uses_total_count() -> None:
    page_one = {"total_count": 150, "check_runs": [check_run(f"job-{i}", HEAD_A) for i in range(100)]}
    page_two = {"total_count": 150, "check_runs": [check_run(f"job-{i}", HEAD_A) for i in range(100, 150)]}
    runner = FakeRunner([(0, json.dumps(page_one)), (0, json.dumps(page_two))])
    source = dg.GhCliDeliverySource(repository=REPO, pr_number=PR, runner=runner)
    entries = source.read_checks(HEAD_A)
    assert len(entries) == 150
    assert runner.commands[0][2].endswith("per_page=100&page=1")
    assert runner.commands[1][2].endswith("per_page=100&page=2")


def test_gh_source_unavailable_raises_evidence_error() -> None:
    runner = FakeRunner([(1, ""), (1, "")])
    source = dg.GhCliDeliverySource(repository=REPO, pr_number=PR, runner=runner)
    with pytest.raises(dg.DeliveryEvidenceError):
        source.read_pull_request()
    with pytest.raises(dg.DeliveryEvidenceError):
        source.read_checks(HEAD_A)


def test_gh_source_policy_revision_changes_with_requirements() -> None:
    def make(required: list[str], approvals: int) -> str:
        runner = FakeRunner(
            [
                (0, json.dumps({"required_status_checks": {"contexts": required}, "required_pull_request_reviews": {"required_approving_review_count": approvals}})),
            ]
        )
        source = dg.GhCliDeliverySource(repository=REPO, pr_number=PR, runner=runner)
        return source.read_policy_observation()["revision"]

    first = make(["checks"], 1)
    second = make(["checks", "licensed-validation"], 1)
    third = make(["checks"], 2)
    assert first != second != third != first


# ---------------------------------------------------------------------------
# Composition from a real canonical evaluation
# ---------------------------------------------------------------------------


def test_conformance_summary_from_canonical_evaluation() -> None:
    from de4sdv.semantic import method_evaluator as me

    contract = me.MethodContract(
        method_id="de4sdv.test",
        contract_id="INC-X",
        phase="phase10_vvEvidence",
        obligations=(
            me.ObligationSpec(
                obligation_id="PC-X",
                phase="phase10_vvEvidence",
                subject_selector="scope usages",
                selector_kind=me.SELECTOR_SCOPE_USAGES,
                applicability="(no applicability condition)",
                applicability_kind="unconditional",
                minimum_population=0,
                permitted_empty=False,
                permitted_empty_disposition=None,
                predicate="binding-resolution",
                target_filters=(),
                cardinality=(0, 0),
                required=True,
                evaluation_source="pinned-model-record",
                attestation_policy_ref="",
                claim_boundary="test",
            ),
        ),
    )
    context = me.EvaluationContext(
        revision=me.RevisionIdentity(git_commit=HEAD_A, sysml_project_id="p", sysml_commit_id="c", scope="candidate"),
        elements=(),
        scope=me.DeclaredEvaluationScope(
            scope_id="PSC-X",
            increment_id="INC-X",
            usage_ids=(),
            contribution_ids=frozenset(),
            profiles=(),
        ),
        usage_bindings={},
        pilot_scope_declared=True,
    )
    evaluation = me.MethodEvaluator(contract).evaluate(context)
    summary = dg.ConformanceSummary.from_canonical(evaluation)
    assert summary.evaluation_key == evaluation.evaluation_key
    assert summary.git_commit == HEAD_A
    assert summary.assessment_coverage == evaluation.assessment_coverage
    assert summary.evaluation_state == evaluation.evaluation_state
    assert summary.conformance_verdict == evaluation.conformance_verdict
