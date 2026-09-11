"""Advisory delivery projection for exact-PR readiness (Lane D).

Scope boundary (frozen baseline §13/§16, Increment D):

- the delivery projection composes a **matching canonical conformance result**
  with **live exact-head governance state**. It performs no engineering
  conformance evaluation of its own and never re-derives a model verdict;
- readiness is an observation at one exact observed head/base. The required
  sequence is read head/base -> collect review/CI/policy evidence -> re-read
  head/base -> compare; movement of the head or the relevant base during the
  observation is ``BLOCKED`` with the frozen ``STALE_INPUT`` reason and an
  explicit head-moved/base-moved diagnostic. A successful operational verdict
  is never published from stale evidence;
- unknown, unsupported, unavailable, stale, or unassessed REQUIRED delivery
  obligations block merge readiness. ``unsupported`` is never translated into
  ``PASS``, and a model result is never contaminated by delivery state: the
  conformance summary is echoed unchanged;
- the projection authorizes nothing: no merge, no approval, no branch
  protection or security-setting mutation, no repository write of any kind.
  GitHub/platform merge protection remains authoritative for the actual merge.
  Making any check mandatory is a separate, explicitly authorized operational
  decision outside this module;
- evaluator/independent-review disagreement (MC-30) blocks readiness with an
  explicit investigation reason; a timeout or partial comparison is never
  acceptance.

Delivery blocking vocabulary (separate from the conformance result algebra;
``STALE_INPUT`` is shared because the frozen result-algebra vocabulary itself
assigns it to the delivery projection):

    STALE_INPUT                    delivery input moved / re-read as changed
    MODEL_CONFORMANCE_UNSATISFIED  no matching complete-pass model result for the exact head
    DELIVERY_OBLIGATION_UNSUPPORTED  a required delivery obligation has no supported evaluator
    DELIVERY_OBLIGATION_UNASSESSED   a required delivery obligation was not assessed
    DELIVERY_OBLIGATION_FAILED       an assessed required delivery obligation is not satisfied
    EVIDENCE_UNAVAILABLE           the delivery evidence source was unavailable
    EVALUATION_DISAGREEMENT        cross-check disagreement; investigation required
    AGREEMENT_UNESTABLISHED        cross-check timeout/partial/missing; not acceptance
    TARGET_NOT_OPEN                the PR merge decision is terminal (merged/closed)
    POLICY_REVISION_MISMATCH       observed governance policy revision differs from the required one
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Protocol, Sequence

STALE_INPUT = "STALE_INPUT"
MODEL_CONFORMANCE_UNSATISFIED = "MODEL_CONFORMANCE_UNSATISFIED"
DELIVERY_OBLIGATION_UNSUPPORTED = "DELIVERY_OBLIGATION_UNSUPPORTED"
DELIVERY_OBLIGATION_UNASSESSED = "DELIVERY_OBLIGATION_UNASSESSED"
DELIVERY_OBLIGATION_FAILED = "DELIVERY_OBLIGATION_FAILED"
EVIDENCE_UNAVAILABLE = "EVIDENCE_UNAVAILABLE"
EVALUATION_DISAGREEMENT = "EVALUATION_DISAGREEMENT"
AGREEMENT_UNESTABLISHED = "AGREEMENT_UNESTABLISHED"
TARGET_NOT_OPEN = "TARGET_NOT_OPEN"
POLICY_REVISION_MISMATCH = "POLICY_REVISION_MISMATCH"

DELIVERY_REASONS: frozenset[str] = frozenset(
    {
        STALE_INPUT,
        MODEL_CONFORMANCE_UNSATISFIED,
        DELIVERY_OBLIGATION_UNSUPPORTED,
        DELIVERY_OBLIGATION_UNASSESSED,
        DELIVERY_OBLIGATION_FAILED,
        EVIDENCE_UNAVAILABLE,
        EVALUATION_DISAGREEMENT,
        AGREEMENT_UNESTABLISHED,
        TARGET_NOT_OPEN,
        POLICY_REVISION_MISMATCH,
    }
)

READINESS_READY = "READY"
READINESS_BLOCKED = "BLOCKED"

OBLIGATION_MODEL = "model-conformance"
OBLIGATION_CI = "ci-required-checks"
OBLIGATION_REVIEW = "review-approval"
OBLIGATION_METHOD_CHANGE = "method-change-authorization"
OBLIGATION_CROSS_CHECK = "cross-check-agreement"

_STATE_SATISFIED = "satisfied"
_STATE_FAILED = "failed"
_STATE_UNSUPPORTED = "unsupported"
_STATE_UNASSESSED = "unassessed"
_STATE_NOT_APPLICABLE = "not-applicable"

_MERGE_AUTHORITY = (
    "GitHub platform merge protection remains authoritative for the actual "
    "merge; this projection is advisory and authorizes nothing"
)
_CLAIM_BOUNDARY = (
    "operational readiness observation for the exact observed PR head/base; "
    "not a merge authorization and not an engineering conformance result"
)


class DeliveryEvidenceError(RuntimeError):
    """The delivery evidence source could not produce an observation."""


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DeliveryPolicy:
    """The pinned delivery policy the observation is judged against."""

    policy_id: str
    revision: str
    required_checks: tuple[str, ...]
    required_approvals: int
    require_cross_check: bool = True
    policy_bearing_paths: tuple[str, ...] = ()
    extra_required_obligations: tuple[str, ...] = ()
    advisory: bool = True


@dataclass(frozen=True)
class ConformanceSummary:
    """Read-only composition input: one canonical evaluation's identity.

    Built from the matching canonical result (``from_canonical``); the delivery
    projection never recomputes or alters the model result.
    """

    evaluation_key: str
    method_id: str
    contract_id: str
    contract_digest: str
    policy_bundle_id: str
    git_commit: str
    sysml_project_id: str
    sysml_commit_id: str
    scope: str
    assessment_coverage: str
    evaluation_state: str | None
    conformance_verdict: str | None
    required_units: tuple[str, ...]
    failed_ids: tuple[str, ...]
    indeterminate_ids: tuple[str, ...]
    errored_ids: tuple[str, ...]
    unassessed_ids: tuple[str, ...]

    @classmethod
    def from_canonical(cls, evaluation: Any) -> "ConformanceSummary":
        """Compose the summary from one :class:`CanonicalEvaluation`."""
        method = dict(evaluation.method_identity)
        revision = dict(evaluation.revision_identity)
        return cls(
            evaluation_key=evaluation.evaluation_key,
            method_id=str(method.get("method_id") or ""),
            contract_id=str(method.get("contract_id") or ""),
            contract_digest=str(method.get("contract_digest") or ""),
            policy_bundle_id=str(method.get("policy_bundle_id") or ""),
            git_commit=str(revision.get("git_commit") or ""),
            sysml_project_id=str(revision.get("sysml_project_id") or ""),
            sysml_commit_id=str(revision.get("sysml_commit_id") or ""),
            scope=str(revision.get("scope") or ""),
            assessment_coverage=evaluation.assessment_coverage,
            evaluation_state=evaluation.evaluation_state,
            conformance_verdict=evaluation.conformance_verdict,
            required_units=tuple(evaluation.required_units),
            failed_ids=tuple(evaluation.failed_ids),
            indeterminate_ids=tuple(evaluation.indeterminate_ids),
            errored_ids=tuple(evaluation.errored_ids),
            unassessed_ids=tuple(evaluation.unassessed_ids),
        )

    def as_payload(self) -> dict[str, Any]:
        return {
            "evaluation_key": self.evaluation_key,
            "method_id": self.method_id,
            "contract_id": self.contract_id,
            "contract_digest": self.contract_digest,
            "policy_bundle_id": self.policy_bundle_id,
            "git_commit": self.git_commit,
            "sysml_project_id": self.sysml_project_id,
            "sysml_commit_id": self.sysml_commit_id,
            "scope": self.scope,
            "assessment_coverage": self.assessment_coverage,
            "evaluation_state": self.evaluation_state,
            "conformance_verdict": self.conformance_verdict,
        }


@dataclass(frozen=True)
class CrossCheckRecord:
    """MC-30 cross-check: API/snapshot comparison vs independent review.

    ``parity`` is one of ``agreed`` / ``disagreed`` / ``timeout`` / ``partial``
    / ``not-run``. Only ``agreed`` counts as an established comparison; a
    timeout, partial, or missing comparison is never acceptance.
    """

    parity: str
    parity_detail: str = ""
    evaluator_disposition: str = ""
    independent_disposition: str = ""


class DeliveryEvidenceSource(Protocol):
    """Read-only live-state adapter (GitHub or a test fake)."""

    def read_pull_request(self) -> Mapping[str, Any]:  # pragma: no cover
        ...

    def read_checks(self, head_sha: str) -> Sequence[Mapping[str, Any]]:  # pragma: no cover
        ...

    def read_reviews(self, head_sha: str) -> Sequence[Mapping[str, Any]]:  # pragma: no cover
        ...

    def read_changed_files(self, head_sha: str) -> Sequence[str]:  # pragma: no cover
        ...

    def read_policy_observation(self) -> Mapping[str, Any]:  # pragma: no cover
        ...


# ---------------------------------------------------------------------------
# The projection
# ---------------------------------------------------------------------------


def pr_gate_status(
    *,
    repository: str,
    pr_number: int,
    policy: DeliveryPolicy,
    source: DeliveryEvidenceSource,
    conformance: ConformanceSummary | None,
    cross_check: CrossCheckRecord | None = None,
    observed_at: str | None = None,
) -> dict[str, Any]:
    """Observe the exact PR state and project advisory merge readiness.

    Read only. Never merges, approves, or changes any repository setting; a
    ``READY`` result here does not merge anything and does not override branch
    protection.
    """
    if not str(policy.revision or ""):
        raise ValueError("DeliveryPolicy.revision is required (exact policy identity)")
    if observed_at is None:
        observed_at = datetime.now(timezone.utc).isoformat()

    payload: dict[str, Any] = {
        "query": "pr_gate_status",
        "advisory": bool(policy.advisory),
        "repository": repository,
        "pull_request": pr_number,
        "readiness_target": {"type": "PR_MERGE", "id": f"{repository}#{pr_number}"},
        "readiness": READINESS_BLOCKED,
        "observation": _observation(observed_at),
        "conformance": conformance.as_payload() if conformance is not None else None,
        "policy": {
            "policy_id": policy.policy_id,
            "revision": policy.revision,
            "required_checks": list(policy.required_checks),
            "required_approvals": policy.required_approvals,
            "require_cross_check": policy.require_cross_check,
            "observed_revision": None,
        },
        "obligations": [],
        "supported_obligations": [],
        "unsupported_obligations": [],
        "blocking_reasons": [],
        "blocking_units": [],
        "diagnostics": [],
        "side_effects": "none",
        "merge_authority": _MERGE_AUTHORITY,
        "claim_boundary": _CLAIM_BOUNDARY,
    }
    diagnostics: list[str] = []
    blocking: list[str] = []
    blocking_units: list[str] = []

    # 1. First observation (before any evidence collection).
    try:
        first = source.read_pull_request()
    except DeliveryEvidenceError as error:
        diagnostics.append(f"delivery evidence source unavailable: {error}")
        _finalize(payload, [], [EVIDENCE_UNAVAILABLE], ["evidence-source"], diagnostics)
        return payload
    head_before = str(first.get("head_sha") or "")
    base_before = str(first.get("base_sha") or "")
    payload["observation"].update(
        {"head_sha": head_before or None, "base_sha": base_before or None, "state": first.get("state")}
    )

    # 2. Collect review / CI / policy evidence (bound to the first-observed head).
    try:
        checks = list(source.read_checks(head_before))
        reviews = list(source.read_reviews(head_before))
        changed_files = list(source.read_changed_files(head_before))
        policy_observation = dict(source.read_policy_observation())
    except DeliveryEvidenceError as error:
        diagnostics.append(f"delivery evidence source unavailable during collection: {error}")
        _finalize(payload, [], [EVIDENCE_UNAVAILABLE], ["evidence-source"], diagnostics)
        return payload

    # 3. Re-read the head/base state and compare.
    try:
        second = source.read_pull_request()
    except DeliveryEvidenceError as error:
        diagnostics.append(f"delivery evidence source unavailable during re-read: {error}")
        _finalize(payload, [], [EVIDENCE_UNAVAILABLE], ["evidence-source"], diagnostics)
        return payload
    head_after = str(second.get("head_sha") or "")
    base_after = str(second.get("base_sha") or "")
    head_moved = head_before != head_after
    base_moved = base_before != base_after
    payload["observation"].update(
        {
            "head_sha": head_after or None,
            "base_sha": base_after or None,
            "head_sha_before": head_before or None,
            "base_sha_before": base_before or None,
            "state": second.get("state"),
            "head_moved": head_moved,
            "base_moved": base_moved,
        }
    )
    payload["policy"]["observed_revision"] = policy_observation.get("revision")

    if head_moved or base_moved:
        movement = []
        if head_moved:
            movement.append(f"head moved: {head_before} -> {head_after}")
        if base_moved:
            movement.append(f"base moved: {base_before} -> {base_after}")
        diagnostics.append(
            "delivery input moved during evidence collection; no successful "
            "delivery verdict is published from stale evidence: " + "; ".join(movement)
        )
        units = [name for name, moved in (("head-moved", head_moved), ("base-moved", base_moved)) if moved]
        _finalize(payload, [], [STALE_INPUT], units, diagnostics)
        return payload

    # 4. Conditions independent of the obligation list.
    state = str(second.get("state") or "")
    if state != "open":
        blocking.append(TARGET_NOT_OPEN)
        blocking_units.append("target-not-open")
        diagnostics.append(
            f"the PR merge decision is terminal (state={state!r}); there is no "
            "pending merge decision to assess"
        )
    observed_revision = str(policy_observation.get("revision") or "")
    if observed_revision != str(policy.revision):
        blocking.append(POLICY_REVISION_MISMATCH)
        blocking_units.append("policy-revision")
        diagnostics.append(
            "observed governance policy revision "
            f"{observed_revision!r} differs from the required policy revision "
            f"{policy.revision!r}; the earlier observation is invalidated"
        )

    # 5. Obligations (composed against the final observed exact state).
    obligations: list[dict[str, Any]] = [
        _model_obligation(conformance, head_after),
        _ci_obligation(policy, checks, head_after),
        _review_obligation(policy, reviews, head_after),
        _method_change_obligation(policy, changed_files),
        _cross_check_obligation(policy, cross_check),
    ]
    for name in policy.extra_required_obligations:
        obligations.append(
            _obligation(
                obligation_id=str(name),
                required=True,
                supported=False,
                state=_STATE_UNSUPPORTED,
                reasons=[DELIVERY_OBLIGATION_UNSUPPORTED],
                evidence=None,
                diagnostics=[
                    f"required delivery obligation {name!r} has no supported "
                    "evaluator in this V1 slice; unsupported is never treated as PASS"
                ],
            )
        )
    for obligation in obligations:
        if obligation["required"] and obligation["state"] not in {
            _STATE_SATISFIED,
            _STATE_NOT_APPLICABLE,
        }:
            blocking_units.append(str(obligation["id"]))
            for reason in obligation["reasons"]:
                if reason not in blocking:
                    blocking.append(reason)

    _finalize(payload, obligations, blocking, blocking_units, diagnostics)
    return payload


def _finalize(
    payload: dict[str, Any],
    obligations: Sequence[Mapping[str, Any]],
    blocking: Sequence[str],
    blocking_units: Sequence[str],
    diagnostics: Sequence[str],
) -> None:
    payload["obligations"] = [dict(item) for item in obligations]
    payload["supported_obligations"] = [
        str(item["id"]) for item in obligations if item.get("supported")
    ]
    payload["unsupported_obligations"] = [
        str(item["id"]) for item in obligations if not item.get("supported")
    ]
    payload["blocking_reasons"] = list(dict.fromkeys(blocking))
    payload["blocking_units"] = list(dict.fromkeys(blocking_units))
    payload["diagnostics"] = list(dict.fromkeys(diagnostics))
    payload["readiness"] = (
        READINESS_READY if not payload["blocking_reasons"] else READINESS_BLOCKED
    )


def _observation(observed_at: str) -> dict[str, Any]:
    return {
        "observed_at": observed_at,
        "head_sha": None,
        "base_sha": None,
        "head_sha_before": None,
        "base_sha_before": None,
        "state": None,
        "head_moved": False,
        "base_moved": False,
    }


def _obligation(
    *,
    obligation_id: str,
    required: bool,
    supported: bool,
    state: str,
    reasons: Sequence[str],
    evidence: Any,
    diagnostics: Sequence[str],
) -> dict[str, Any]:
    return {
        "id": obligation_id,
        "required": required,
        "supported": supported,
        "state": state,
        "reasons": list(reasons),
        "evidence": evidence,
        "diagnostics": list(diagnostics),
    }


def _model_obligation(
    conformance: ConformanceSummary | None, head_sha: str
) -> dict[str, Any]:
    if conformance is None:
        return _obligation(
            obligation_id=OBLIGATION_MODEL,
            required=True,
            supported=True,
            state=_STATE_FAILED,
            reasons=[MODEL_CONFORMANCE_UNSATISFIED],
            evidence=None,
            diagnostics=[
                "no canonical conformance result was supplied for the exact "
                "observed head revision"
            ],
        )
    evidence = {
        "evaluation_key": conformance.evaluation_key,
        "git_commit": conformance.git_commit,
        "sysml_project_id": conformance.sysml_project_id,
        "sysml_commit_id": conformance.sysml_commit_id,
        "scope": conformance.scope,
    }
    if conformance.git_commit != head_sha:
        return _obligation(
            obligation_id=OBLIGATION_MODEL,
            required=True,
            supported=True,
            state=_STATE_FAILED,
            reasons=[MODEL_CONFORMANCE_UNSATISFIED],
            evidence=evidence,
            diagnostics=[
                "conformance result revision "
                f"{conformance.git_commit!r} does not match the observed exact "
                f"head {head_sha!r}; stale model results cannot authorize readiness"
            ],
        )
    if not (
        conformance.assessment_coverage == "ASSESSED"
        and conformance.evaluation_state == "COMPLETE"
        and conformance.conformance_verdict == "PASS"
    ):
        return _obligation(
            obligation_id=OBLIGATION_MODEL,
            required=True,
            supported=True,
            state=_STATE_FAILED,
            reasons=[MODEL_CONFORMANCE_UNSATISFIED],
            evidence=evidence,
            diagnostics=[
                "conformance result is "
                f"{conformance.assessment_coverage} / {conformance.evaluation_state} / "
                f"{conformance.conformance_verdict}; PR-merge readiness requires an "
                "assessed, complete PASS for the exact head"
            ],
        )
    return _obligation(
        obligation_id=OBLIGATION_MODEL,
        required=True,
        supported=True,
        state=_STATE_SATISFIED,
        reasons=[],
        evidence=evidence,
        diagnostics=[],
    )


def _ci_obligation(
    policy: DeliveryPolicy, checks: Sequence[Mapping[str, Any]], head_sha: str
) -> dict[str, Any]:
    required = [str(name) for name in policy.required_checks]
    if not required:
        return _obligation(
            obligation_id=OBLIGATION_CI,
            required=True,
            supported=False,
            state=_STATE_UNSUPPORTED,
            reasons=[DELIVERY_OBLIGATION_UNSUPPORTED],
            evidence=None,
            diagnostics=[
                "no required check contexts are declared; an empty required "
                "inventory cannot authorize a merge"
            ],
        )
    bound = [
        run for run in checks if str(run.get("head_sha") or "") == head_sha
    ]
    stale = len(bound) != len(checks)
    evidence: list[dict[str, Any]] = []
    diagnostics: list[str] = []
    if stale:
        diagnostics.append(
            f"{len(checks) - len(bound)} check result(s) are bound to a different "
            "commit and are not usable for the exact observed head"
        )
    failures: list[str] = []
    missing: list[str] = []
    for name in required:
        matching = [run for run in bound if str(run.get("name") or "") == name]
        if not matching:
            missing.append(name)
            continue
        for run in matching:
            evidence.append(
                {
                    "name": name,
                    "status": run.get("status"),
                    "conclusion": run.get("conclusion"),
                    "head_sha": run.get("head_sha"),
                }
            )
        if any(
            str(run.get("status")) != "completed"
            or str(run.get("conclusion")) != "success"
            for run in matching
        ):
            failures.append(name)
    if missing:
        return _obligation(
            obligation_id=OBLIGATION_CI,
            required=True,
            supported=True,
            state=_STATE_UNASSESSED,
            reasons=[DELIVERY_OBLIGATION_UNASSESSED],
            evidence=evidence or None,
            diagnostics=diagnostics
            + [f"required check(s) {missing} have no result bound to the exact head"],
        )
    if failures:
        return _obligation(
            obligation_id=OBLIGATION_CI,
            required=True,
            supported=True,
            state=_STATE_FAILED,
            reasons=[DELIVERY_OBLIGATION_FAILED],
            evidence=evidence,
            diagnostics=diagnostics
            + [f"required check(s) {failures} are not completed-success on the exact head"],
        )
    return _obligation(
        obligation_id=OBLIGATION_CI,
        required=True,
        supported=True,
        state=_STATE_SATISFIED,
        reasons=[],
        evidence=evidence,
        diagnostics=diagnostics,
    )


def _review_obligation(
    policy: DeliveryPolicy, reviews: Sequence[Mapping[str, Any]], head_sha: str
) -> dict[str, Any]:
    required = int(policy.required_approvals)
    if required <= 0:
        return _obligation(
            obligation_id=OBLIGATION_REVIEW,
            required=True,
            supported=True,
            state=_STATE_NOT_APPLICABLE,
            reasons=[],
            evidence=None,
            diagnostics=["no approving reviews are required by the delivery policy"],
        )
    approvals = [
        review
        for review in reviews
        if str(review.get("commit_id") or "") == head_sha
        and str(review.get("state") or "").upper() == "APPROVED"
    ]
    evidence = [
        {
            "reviewer": review.get("reviewer"),
            "state": review.get("state"),
            "commit_id": review.get("commit_id"),
        }
        for review in approvals
    ]
    if len(approvals) >= required:
        return _obligation(
            obligation_id=OBLIGATION_REVIEW,
            required=True,
            supported=True,
            state=_STATE_SATISFIED,
            reasons=[],
            evidence=evidence,
            diagnostics=[],
        )
    return _obligation(
        obligation_id=OBLIGATION_REVIEW,
        required=True,
        supported=True,
        state=_STATE_FAILED,
        reasons=[DELIVERY_OBLIGATION_FAILED],
        evidence=evidence or None,
        diagnostics=[
            f"{len(approvals)} approving review(s) bound to the exact head; "
            f"{required} required. Comments and approvals for other commits do not count"
        ],
    )


def _method_change_obligation(
    policy: DeliveryPolicy, changed_files: Sequence[str]
) -> dict[str, Any]:
    if not policy.policy_bearing_paths:
        return _obligation(
            obligation_id=OBLIGATION_METHOD_CHANGE,
            required=True,
            supported=True,
            state=_STATE_NOT_APPLICABLE,
            reasons=[],
            evidence=None,
            diagnostics=["no policy-bearing closure paths are declared by the policy"],
        )
    touched = [
        str(path)
        for path in changed_files
        if any(
            str(path) == prefix.rstrip("/")
            or str(path).startswith(str(prefix).rstrip("/") + "/")
            for prefix in policy.policy_bearing_paths
        )
    ]
    if not touched:
        return _obligation(
            obligation_id=OBLIGATION_METHOD_CHANGE,
            required=True,
            supported=True,
            state=_STATE_NOT_APPLICABLE,
            reasons=[],
            evidence=None,
            diagnostics=["the observed change does not touch the policy-bearing closure"],
        )
    return _obligation(
        obligation_id=OBLIGATION_METHOD_CHANGE,
        required=True,
        supported=False,
        state=_STATE_UNSUPPORTED,
        reasons=[DELIVERY_OBLIGATION_UNSUPPORTED],
        evidence={"changed_policy_bearing_paths": touched},
        diagnostics=[
            "the change touches the policy-bearing closure "
            f"{touched}; a reviewed method-change authorization is required and "
            "this V1 slice has no supported evaluator for it; unsupported never "
            "becomes PASS"
        ],
    )


def _cross_check_obligation(
    policy: DeliveryPolicy, cross_check: CrossCheckRecord | None
) -> dict[str, Any]:
    if not policy.require_cross_check:
        return _obligation(
            obligation_id=OBLIGATION_CROSS_CHECK,
            required=True,
            supported=True,
            state=_STATE_NOT_APPLICABLE,
            reasons=[],
            evidence=None,
            diagnostics=["the delivery policy does not require a cross-check"],
        )
    if cross_check is None:
        return _obligation(
            obligation_id=OBLIGATION_CROSS_CHECK,
            required=True,
            supported=True,
            state=_STATE_UNASSESSED,
            reasons=[AGREEMENT_UNESTABLISHED],
            evidence=None,
            diagnostics=[
                "no API/snapshot and independent-review comparison was supplied; "
                "an unestablished comparison is not acceptance"
            ],
        )
    evidence = {
        "parity": cross_check.parity,
        "parity_detail": cross_check.parity_detail,
        "evaluator_disposition": cross_check.evaluator_disposition,
        "independent_disposition": cross_check.independent_disposition,
    }
    if cross_check.parity == "agreed":
        return _obligation(
            obligation_id=OBLIGATION_CROSS_CHECK,
            required=True,
            supported=True,
            state=_STATE_SATISFIED,
            reasons=[],
            evidence=evidence,
            diagnostics=[],
        )
    if cross_check.parity == "disagreed":
        return _obligation(
            obligation_id=OBLIGATION_CROSS_CHECK,
            required=True,
            supported=True,
            state=_STATE_FAILED,
            reasons=[EVALUATION_DISAGREEMENT],
            evidence=evidence,
            diagnostics=[
                "the evaluator comparison and the independent review disagree "
                f"({cross_check.evaluator_disposition!r} vs "
                f"{cross_check.independent_disposition!r}); explicit investigation "
                "is required and no winner is selected automatically"
            ],
        )
    return _obligation(
        obligation_id=OBLIGATION_CROSS_CHECK,
        required=True,
        supported=True,
        state=_STATE_FAILED,
        reasons=[AGREEMENT_UNESTABLISHED],
        evidence=evidence,
        diagnostics=[
            f"cross-check status {cross_check.parity!r}: neither a timeout nor a "
            "partial comparison counts as acceptance"
        ],
    )


# ---------------------------------------------------------------------------
# Live adapter: gh CLI (read-only commands only)
# ---------------------------------------------------------------------------


class GhCliDeliverySource:
    """Read-only GitHub delivery-evidence adapter backed by the ``gh`` CLI.

    Every issued command is a read (``gh api`` GET-style requests). This class
    contains no merge, approval, branch-protection, or settings mutation.
    """

    def __init__(
        self,
        *,
        repository: str,
        pr_number: int,
        runner: Callable[..., Any] | None = None,
        timeout: float = 60.0,
    ) -> None:
        self._repository = repository
        self._pr_number = int(pr_number)
        self._runner = runner or subprocess.run
        self._timeout = timeout

    # -- internals ---------------------------------------------------------

    def _run(self, args: Sequence[str]) -> Any:
        command = ["gh", *args]
        try:
            completed = self._runner(
                command, capture_output=True, text=True, timeout=self._timeout
            )
        except Exception as error:  # noqa: BLE001 - evidence failure, never a crash
            raise DeliveryEvidenceError(f"gh invocation failed: {error}") from error
        if completed.returncode != 0:
            detail = (completed.stderr or "").strip() or f"exit {completed.returncode}"
            raise DeliveryEvidenceError(f"gh {' '.join(args)} failed: {detail}")
        return completed.stdout

    def _api_json(self, path: str) -> Any:
        raw = self._run(["api", path])
        try:
            return json.loads(raw)
        except json.JSONDecodeError as error:
            raise DeliveryEvidenceError(
                f"gh api {path} returned unreadable JSON: {error}"
            ) from error

    def _paginated_list(self, path: str, *, max_pages: int = 11) -> list[Any]:
        """Bounded manual pagination (works with older ``gh`` clients).

        Pages are requested explicitly; a short page ends the walk. If the
        page bound is reached without a terminal page, the evidence is
        potentially incomplete and the read fails closed (partial evidence
        must never authorize a verdict).
        """
        items: list[Any] = []
        for page in range(1, max_pages + 1):
            value = self._api_json(f"{path}?per_page=100&page={page}")
            if isinstance(value, list):
                items.extend(value)
                if len(value) < 100:
                    return items
            elif isinstance(value, dict):
                runs = value.get("check_runs") or []
                items.extend(runs)
                total = value.get("total_count")
                if total is not None and len(items) >= int(total):
                    return items
                if not runs or len(runs) < 100:
                    return items
            else:
                raise DeliveryEvidenceError(
                    f"gh api {path}: unexpected page representation"
                )
        raise DeliveryEvidenceError(
            f"gh api {path}: pagination bound reached without a terminal page; "
            "incomplete evidence cannot be used"
        )

    # -- DeliveryEvidenceSource -------------------------------------------

    def read_pull_request(self) -> Mapping[str, Any]:
        value = self._api_json(
            f"repos/{self._repository}/pulls/{self._pr_number}"
        )
        if not isinstance(value, dict):
            raise DeliveryEvidenceError("unexpected pull-request representation")
        return {
            "head_sha": str((value.get("head") or {}).get("sha") or ""),
            "base_sha": str((value.get("base") or {}).get("sha") or ""),
            "state": str(value.get("state") or ""),
            "draft": bool(value.get("draft")),
            "merge_commit_sha": value.get("merge_commit_sha"),
        }

    def read_checks(self, head_sha: str) -> Sequence[Mapping[str, Any]]:
        entries: list[Mapping[str, Any]] = []
        for run in self._paginated_list(
            f"repos/{self._repository}/commits/{head_sha}/check-runs"
        ):
            if not isinstance(run, dict):
                continue
            entries.append(
                {
                    "name": str(run.get("name") or ""),
                    "status": str(run.get("status") or ""),
                    "conclusion": str(run.get("conclusion") or ""),
                    "head_sha": str(run.get("head_sha") or ""),
                }
            )
        return entries

    def read_reviews(self, head_sha: str) -> Sequence[Mapping[str, Any]]:
        entries: list[Mapping[str, Any]] = []
        for review in self._paginated_list(
            f"repos/{self._repository}/pulls/{self._pr_number}/reviews"
        ):
            if not isinstance(review, dict):
                continue
            entries.append(
                {
                    "state": str(review.get("state") or ""),
                    "commit_id": review.get("commit_id"),
                    "reviewer": str((review.get("user") or {}).get("login") or ""),
                    "submitted_at": review.get("submitted_at"),
                }
            )
        return entries

    def read_changed_files(self, head_sha: str) -> Sequence[str]:
        files: list[str] = []
        for value in self._paginated_list(
            f"repos/{self._repository}/pulls/{self._pr_number}/files"
        ):
            if isinstance(value, dict) and value.get("filename"):
                files.append(str(value["filename"]))
        return files

    def read_policy_observation(self) -> Mapping[str, Any]:
        value = self._api_json(
            f"repos/{self._repository}/branches/main/protection"
        )
        if not isinstance(value, dict):
            raise DeliveryEvidenceError("unexpected branch-protection representation")
        required_status = value.get("required_status_checks") or {}
        contexts = sorted(
            str(context) for context in (required_status.get("contexts") or [])
        )
        reviews = value.get("required_pull_request_reviews") or {}
        approvals = int(reviews.get("required_approving_review_count") or 0)
        revision = hashlib.sha256(
            json.dumps(
                {"contexts": contexts, "required_approvals": approvals},
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return {
            "revision": revision,
            "required_checks": contexts,
            "required_approvals": approvals,
            "source": f"branch protection {self._repository}/main",
        }
