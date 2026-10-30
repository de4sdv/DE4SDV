"""Method parity: over the API, each declared increment has the export path's phase 9 and next.

The API service builds its method view from the served corpus and from the export documents that its
revision binding records. The export path builds its view from the export. With the same inputs, the two
give the same answers, except where the revision scope decides. An API revision binding withholds the
checks that read native allocations while the admission of their relation has open obligations
(``increment_workflow.allocations_withheld``): there those checks are method side, with an
``allocation-admission:`` marker. That marker alone is the guard; a ``governed-relation:`` marker is a
relation the method cannot read, which no admission lifts. So parity requires, per declared increment:

- the phase-9 status block of the API evaluation equals the export path's;
- the API's ``next`` equals the export path's, unless the export's ``next`` is a gate that the API
  evaluation withholds in that way.

The release evidence (``scripts/check_release_evidence.py``) runs it over the licensed export of the
release revision, and the full-export test runs it locally. A parity is object-observable evidence on one
export, not a semantic proof.
"""
from __future__ import annotations

from typing import Any, Mapping

from .increment_discovery import declared_increments
from .increment_evaluation import evaluate_increment
from .relation_checks import ALLOCATION_ADMISSION_PREFIX

PARITY_SCHEMA = "de4sdv.method-parity/v1"
#: The phase whose status block must be equal.
PHASE = "phase9_variabilityConfiguration"
#: The marker of a check that an API revision binding withholds (the allocation-admission guard).
WITHHELD_PREFIX = ALLOCATION_ADMISSION_PREFIX
#: Answer fields that name the revision or the service, never the evaluation's content.
REVISION_FIELDS = frozenset({"evaluation_key", "revision", "provenance", "service_provenance"})


def _content(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _content(item) for key, item in value.items() if key not in REVISION_FIELDS}
    if isinstance(value, list):
        return [_content(item) for item in value]
    return value


def _phase(evaluation: Any, phase: str) -> Mapping[str, Any] | None:
    found = [block for block in evaluation.status().get("phases") or () if block.get("phase") == phase]
    return found[0] if found else None


def _summary(block: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if block is None:
        return None
    return {key: block.get(key) for key in ("phase_exit", "conformance_verdict", "evaluation_state")}


def withheld_gates(evaluation: Any) -> set[str]:
    """The gates an evaluation reports as withheld by the allocation guard (a ``governed-relation:``
    marker among the missing inputs of one of their results)."""
    canonical = getattr(evaluation, "canonical", None)
    if canonical is None:
        return set()
    return {result.unit_id for result in canonical.results
            if any(str(item).startswith(WITHHELD_PREFIX) for item in result.missing)}


def increment_parity(increment_id: str, api: Any, export: Any, *, phase: str = PHASE) -> dict[str, Any]:
    """The parity of one increment's API evaluation with its export evaluation."""
    api_phase, export_phase = _content(_phase(api, phase)), _content(_phase(export, phase))
    api_next, export_next = api.next_obligation().get("next"), export.next_obligation().get("next")
    withheld = withheld_gates(api)
    export_gate = (export_next or {}).get("gate")
    next_compared = export_gate is None or export_gate not in withheld
    phase_equal = api_phase == export_phase
    next_equal = _content(api_next) == _content(export_next)
    return {
        "increment": increment_id,
        "phase9_equal": phase_equal,
        "next_equal": next_equal,
        "next_compared": next_compared,
        "api_phase9": _summary(api_phase),
        "export_phase9": _summary(export_phase),
        "api_next": (api_next or {}).get("gate"),
        "export_next": export_gate,
        "withheld_gates": sorted(withheld),
        "passed": phase_equal and (next_equal or not next_compared),
    }


def method_parity(service: Any, export_view: Any, revision: Any) -> dict[str, Any]:
    """Every increment the export declares, evaluated over the API service and over the export path."""
    rows = []
    for identifier in declared_increments(export_view).increment_ids:
        export = evaluate_increment(export_view, identifier, revision=revision)
        api = service.increment_evaluation(identifier)
        rows.append(increment_parity(identifier, api, export))
    return {"schema": PARITY_SCHEMA, "phase": PHASE, "increments": rows,
            "passed": bool(rows) and all(row["passed"] for row in rows)}


__all__ = ["PARITY_SCHEMA", "PHASE", "WITHHELD_PREFIX", "increment_parity", "method_parity", "withheld_gates"]
