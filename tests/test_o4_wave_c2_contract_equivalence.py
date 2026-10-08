"""O4 Wave C2 dual construction (design E6, owner decision D9 evidence).

While the authored ontology still exists, the contract served by the Wave B
model-authority facade (authored YAML as residual provider) must equal the
YAML-free model-built contract except exactly the 2 owner-visible exceptions
and the 5 deprecated aliases, and every raw authored-vs-model difference must
be a classified, pre-existing Wave B reinterpretation. Deleted with the
authored ontology; the committed report
``docs/method-conformance/o4/closure/contract-equivalence.json`` stays.
"""
from __future__ import annotations

import builtins
import pathlib
from dataclasses import replace

import pytest

from de4sdv.semantic.kernel_contract import KernelContract, KernelFileMapping
from scripts import compare_model_contract as cmc

ROOT = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def oracle():
    """Served/authored surfaces computed by the base revision's own code."""
    return cmc._run_oracle(cmc.BASE_REVISION)


@pytest.fixture(scope="module")
def report(oracle):
    return cmc.build_report(ROOT, oracle=oracle)


def test_served_contract_differs_by_exactly_the_exceptions_and_aliases(report):
    served = report["served_contract"]
    assert served["differences"] == sorted(cmc.EXCEPTIONS + cmc.ALIASES)
    assert served["result"] == "EQUAL_EXCEPT_EXPECTED"
    for name in served["differences"]:
        assert "refused" in served["detail"][name]["model"], name
    assert cmc.report_errors(report) == []


def test_every_authored_difference_is_classified(report):
    authored = report["authored_contract"]
    assert authored["unclassified"] == []
    for name in cmc.EXCEPTIONS + cmc.ALIASES:
        assert name in authored["differences"]


def test_model_contract_reads_no_authored_ontology(monkeypatch):
    real_read_text, real_read_bytes, real_open = (
        pathlib.Path.read_text, pathlib.Path.read_bytes, builtins.open)

    def guard(path):
        if "de4sdv-basic-ontology.yaml" in str(path):
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


def test_oracle_ran_on_the_base_revision_with_the_authored_ontology(report):
    assert report["oracle_revision"] == cmc.BASE_REVISION
    assert report["authored_ontology"]["path"] == cmc.ONTOLOGY
    assert len(report["authored_ontology"]["sha256"]) == 64


def test_planted_model_mapping_drift_is_an_unexpected_difference(monkeypatch, oracle):
    from de4sdv.semantic import model_contract

    real = model_contract.load_model_layers

    def drifted(root=model_contract.ROOT):
        records, provisions = real(root)
        changed = []
        for provision in provisions:
            if provision.identity == "Stakeholder" and provision.kind == "class":
                provision = replace(provision, mapping=KernelFileMapping(
                    "textual-notation-of-model/packages/methods/de4sdv/de4sdv_stakeholders.sysml",
                    "part def PlantedStakeholder"))
            changed.append(provision)
        return records, changed

    monkeypatch.setattr(model_contract, "load_model_layers", drifted)
    report = cmc.build_report(ROOT, oracle=oracle)
    assert "Stakeholder" in report["served_contract"]["differences"]
    assert report["served_contract"]["result"] == "UNEXPECTED_DIFFERENCE"
    assert cmc.report_errors(report)
