"""Outcome vocabulary of the evaluators.

The names are the literals of MiddlewareEvidenceOutcome of INC-MW-010
(middleware_verification_evidence.sysml). The verdict follows
MapEvidenceOutcomeToVerdict of the same slice: both pass outcomes give pass,
failObservedBehavior gives fail, errorEvidence gives error, and every other
outcome gives inconclusive.
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

#: Combination order: the strongest finding decides. Evidence that is itself
#: wrong (ERROR) makes any other finding unreliable. An observed failure
#: (FAIL) is not hidden by missing evidence elsewhere.
_PRECEDENCE = (ERROR, FAIL, BLOCKED, INCONCLUSIVE, PASS)


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
    """One observation of an evaluator and the outcome it forces."""

    code: str
    outcome: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "outcome": self.outcome, "message": self.message}


@dataclass
class CaseResult:
    """The result of one evaluator over one run directory."""

    case: str
    run_id: str
    findings: list[Finding] = field(default_factory=list)
    measurements: dict[str, Any] = field(default_factory=dict)

    def add(self, code: str, outcome: str, message: str) -> None:
        if outcome not in OUTCOMES:
            raise ValueError(f"unknown outcome {outcome!r}")
        self.findings.append(Finding(code, outcome, message))

    @property
    def outcome(self) -> str:
        present = {finding.outcome for finding in self.findings}
        for candidate in _PRECEDENCE:
            if candidate in present:
                return candidate
        # No finding at all is no evidence of a pass.
        return INCONCLUSIVE

    def as_dict(self) -> dict[str, Any]:
        return {
            "case": self.case,
            "run_id": self.run_id,
            "outcome": self.outcome,
            "verdict": verdict(self.outcome),
            "findings": [finding.as_dict() for finding in self.findings],
            "measurements": self.measurements,
        }
