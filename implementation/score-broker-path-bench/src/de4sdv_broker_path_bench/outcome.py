"""Outcome vocabulary of the evaluators.

The names are the literals of MiddlewareEvidenceOutcome of INC-MW-010
(middleware_verification_evidence.sysml). The verdict follows
MapEvidenceOutcomeToVerdict of the same slice: the one pass outcome this bench
emits (passBoundedVerification) gives pass, failObservedBehavior gives fail,
errorEvidence gives error, and every other outcome gives inconclusive. The
vocabulary also holds passBoundedValidation, which the verification cases do
not use.

Precedence (VC-MW-015): a failure dominates only when its evidence does
not depend on an inconclusive condition. A finding may name the code of a
condition it depends on; when that condition is itself inconclusive in the
same result, the dependent failure is downgraded to inconclusive. So a
clock-dependent or capture-dependent failure cannot turn missing evidence
into a fail.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

PASS = "passBoundedVerification"
FAIL = "failObservedBehavior"
INCONCLUSIVE = "inconclusiveMissingEvidence"
BLOCKED = "blockedTargetRuntime"
ERROR = "errorEvidence"

OUTCOMES = (PASS, FAIL, INCONCLUSIVE, BLOCKED, ERROR)


def verdict(outcome: str) -> str:
    """MapEvidenceOutcomeToVerdict of INC-MW-010."""
    if outcome not in OUTCOMES:
        raise ValueError(f"unknown outcome {outcome!r}")
    if outcome == PASS:
        return "pass"
    if outcome == FAIL:
        return "fail"
    if outcome == ERROR:
        return "error"
    return "inconclusive"


@dataclass(frozen=True)
class Finding:
    """One observation of an evaluator and the outcome it forces.

    ``depends_on`` names the code of a condition this finding relies on. A
    FAIL with a ``depends_on`` whose condition is inconclusive in the same
    result is not a dominating failure; it becomes missing evidence.
    """

    code: str
    outcome: str
    message: str
    depends_on: str | None = None

    def as_dict(self) -> dict[str, str]:
        out = {"code": self.code, "outcome": self.outcome, "message": self.message}
        if self.depends_on:
            out["depends_on"] = self.depends_on
        return out


@dataclass
class CaseResult:
    """The result of one evaluator over one run directory."""

    case: str
    run_id: str
    findings: list[Finding] = field(default_factory=list)
    measurements: dict[str, Any] = field(default_factory=dict)

    def add(self, code: str, outcome: str, message: str, depends_on: str | None = None) -> None:
        if outcome not in OUTCOMES:
            raise ValueError(f"unknown outcome {outcome!r}")
        self.findings.append(Finding(code, outcome, message, depends_on))

    @property
    def outcome(self) -> str:
        if any(finding.outcome == ERROR for finding in self.findings):
            return ERROR
        inconclusive_codes = {finding.code for finding in self.findings if finding.outcome == INCONCLUSIVE}
        dominating_fail = False
        suppressed_fail = False
        for finding in self.findings:
            if finding.outcome != FAIL:
                continue
            if finding.depends_on and finding.depends_on in inconclusive_codes:
                suppressed_fail = True  # the condition it rests on is itself inconclusive
            else:
                dominating_fail = True
        if dominating_fail:
            return FAIL
        if suppressed_fail or any(finding.outcome in (INCONCLUSIVE, BLOCKED) for finding in self.findings):
            return INCONCLUSIVE
        if any(finding.outcome == PASS for finding in self.findings):
            return PASS
        return INCONCLUSIVE  # no finding at all is no evidence of a pass

    def as_dict(self) -> dict[str, Any]:
        return {
            "case": self.case,
            "run_id": self.run_id,
            "outcome": self.outcome,
            "verdict": verdict(self.outcome),
            "findings": [finding.as_dict() for finding in self.findings],
            "measurements": self.measurements,
        }
