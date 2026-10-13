"""The seven retired or refused names keep their exact refusals.

The authored ontology is gone and the model-built contract never reads it.
Seven former names are answered only with a refusal; each refusal text is
pinned here as served, so a change to a register disposition or a retirement
record shows up as a test failure.
"""
from __future__ import annotations

import builtins
import pathlib

from de4sdv.semantic.kernel_contract import KernelContract

ROOT = pathlib.Path(__file__).resolve().parents[1]
REFUSALS = {
    "IncrementTraceabilityShell": (
        "refused: merged into RequiredTraceChain (register disposition MERGE); "
        "no separate identity is served"),
    "constrainedBy": "retired; use hasRegulatorySource",
    "deployedTo": "retired; use allocatedTo",
    "derivesNeedFromConcern": (
        "refused: removed (register disposition REMOVE, REMOVE_FROM_ONTOLOGY); retired; "
        "historical evidence retained (no migration target)"),
    "realizedBy": "retired; use allocatedTo",
    "validatedBy": "retired; use hasValidationScenario",
    "validatesFitnessForUse": "retired; use validationScenarioFor",
}


def test_live_contract_refuses_the_seven_exactly_as_recorded():
    contract = KernelContract.from_layers(ROOT)
    for name, refusal in REFUSALS.items():
        assert contract.refused[name] == refusal, name
        assert name not in contract.classes and name not in contract.relationships, name


def test_model_contract_reads_no_authored_ontology(monkeypatch):
    assert not (ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml").exists()
    real_read_text, real_read_bytes, real_open = (
        pathlib.Path.read_text, pathlib.Path.read_bytes, builtins.open)

    def guard(path):
        if "de4sdv-basic-ontology" in str(path):
            raise AssertionError(f"model contract read the authored ontology: {path}")

    monkeypatch.setattr(pathlib.Path, "read_text",
                        lambda self, *a, **k: (guard(self), real_read_text(self, *a, **k))[1])
    monkeypatch.setattr(pathlib.Path, "read_bytes",
                        lambda self: (guard(self), real_read_bytes(self))[1])
    monkeypatch.setattr(builtins, "open",
                        lambda file, *a, **k: (guard(file), real_open(file, *a, **k))[1])
    contract = KernelContract.from_layers(ROOT)
    assert contract.identity.id.startswith("sai-")
    assert "IncrementTraceabilityShell" in contract.refused
