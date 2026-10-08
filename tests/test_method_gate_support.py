"""The evaluation engine supports every method gate declared in the model.

A lexical read of the method gates file (test-time only; the runtime reads
gates from the API or an export, never from SysML text) checks that each
gate's predicate is registered, its filter text decodes in that predicate's
grammar, its subject selector is a registered increment selector, and its
applicability is a supported form. A method change the engine cannot
evaluate fails here, in review, instead of as an INVALID_CONTRACT at runtime.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from de4sdv.semantic import method_evaluator as me
from de4sdv.semantic.gate_predicates import GATE_PREDICATES, GATE_SELECTORS
from de4sdv.semantic.gate_reader import _APPLICABILITY
from de4sdv.semantic.increment_scope import INCREMENT_SELECTORS

GATES_FILE = (Path(__file__).resolve().parents[1]
              / "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_gates.sysml")


def _gates() -> dict[str, dict[str, str]]:
    text = re.sub(r"/\*.*?\*/", "", GATES_FILE.read_text(encoding="utf-8"), flags=re.S)
    found = {}
    for match in re.finditer(r"\bitem\s+(\w+)\s*:\s*MethodGate\s*\{(.*?)\n  \}", text, re.S):
        fields = dict(re.findall(r'attribute\s+:>>\s+(\w+)\s*=\s*("(?:[^"\\]|\\.)*"|[^;]*);', match.group(2)))
        found[match.group(1)] = {key: value.strip().strip('"') for key, value in fields.items()}
    return found


pytestmark = pytest.mark.skipif(not GATES_FILE.exists(), reason="the model declares no method gates file")


def test_the_gates_file_declares_gates() -> None:
    assert len(_gates()) >= 20


@pytest.mark.parametrize("name", sorted(_gates()) if GATES_FILE.exists() else [])
def test_every_gate_is_supported_by_the_engine(name: str) -> None:
    gate = _gates()[name]
    assert gate["predicate"] in GATE_PREDICATES.names(), gate["predicate"]
    assert gate["subjectSelector"] in INCREMENT_SELECTORS
    assert gate["subjectSelector"] in GATE_SELECTORS.kinds()
    assert gate["applicability"] in _APPLICABILITY
    spec = me.ObligationSpec(
        obligation_id=name, phase=gate["phase"].split("::")[-1], subject_selector=gate["subjectSelector"],
        selector_kind=gate["subjectSelector"], applicability=gate["applicability"],
        applicability_kind=_APPLICABILITY[gate["applicability"]], minimum_population=1,
        permitted_empty=False, permitted_empty_disposition=None, predicate=gate["predicate"],
        target_filters=(gate["targetFilter"],) if gate["targetFilter"] else (),
        cardinality=(1, 1), required=True, evaluation_source=me.EVALUATION_SOURCE_MODEL,
        attestation_policy_ref="", claim_boundary=gate["claimBoundary"],
    )
    decoded = GATE_PREDICATES.filters(spec)
    assert len(decoded) == len(spec.target_filters)
