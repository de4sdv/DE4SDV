"""O4 Wave C2: the committed pre-deletion contract-equivalence evidence.

Replaces ``tests/test_o4_wave_c2_contract_equivalence.py`` (stage 1), whose
executable comparison needed ``scripts/compare_model_contract.py`` (deleted
with the authored ontology in stage 5; it stays reproducible from the
stage-4 commit recorded as ``model_revision``):

- ``test_served_contract_differs_by_exactly_the_exceptions_and_aliases`` and
  ``test_every_authored_difference_is_classified`` -> the recorded results
  are locked here (exactly 2 refused exceptions + 5 retired names; no
  unclassified authored difference);
- ``test_oracle_ran_on_the_base_revision_with_the_authored_ontology`` -> the
  oracle and model revisions are recorded and are ancestors of HEAD;
- ``test_model_contract_reads_no_authored_ontology`` -> kept below (the file
  is now absent, so the guard also proves no fallback path exists);
- ``test_planted_model_mapping_drift_is_an_unexpected_difference`` -> the
  served refusals of the seven names are re-derived from the live contract
  and must equal the recorded model side.
"""
from __future__ import annotations

import builtins
import json
import pathlib
import subprocess

from de4sdv.semantic.kernel_contract import KernelContract

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/method-conformance/o4/closure/contract-equivalence.json"
SEVEN = ["IncrementTraceabilityShell", "constrainedBy", "deployedTo", "derivesNeedFromConcern",
         "realizedBy", "validatedBy", "validatesFitnessForUse"]


def _evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_recorded_served_contract_differs_by_exactly_seven_identities():
    served = _evidence()["served_contract"]
    assert served["result"] == "EQUAL_EXCEPT_EXPECTED"
    assert sorted(served["differences"]) == SEVEN == sorted(served["expected_differences"])


def test_recorded_authored_differences_are_all_classified():
    authored = _evidence()["authored_contract"]
    assert authored["unclassified"] == []
    assert len(authored["differences"]) == 21
    assert all(entry.get("classification") for entry in authored["differences"].values())


def test_recorded_manifest_held_fields_and_reviewed_definitions_are_equal():
    evidence = _evidence()
    assert evidence["manifest_held_fields"]["unequal"] == []
    assert evidence["batch1_reviewed_definitions"]["unequal"] == []


def test_recorded_revisions_are_ancestors_of_head():
    evidence = _evidence()
    for key in ("oracle_revision", "model_revision"):
        revision = evidence[key]
        assert len(revision) == 40, key
        result = subprocess.run(["git", "merge-base", "--is-ancestor", revision, "HEAD"],
                                cwd=ROOT, capture_output=True)
        assert result.returncode == 0, (key, revision)
    shown = subprocess.run(
        ["git", "cat-file", "-e",
         f"{evidence['model_revision']}:scripts/compare_model_contract.py"], cwd=ROOT)
    assert shown.returncode == 0, "the comparison stays reproducible at model_revision"


def test_live_contract_refuses_the_seven_exactly_as_recorded():
    detail = _evidence()["served_contract"]["detail"]
    contract = KernelContract.from_layers(ROOT)
    for name in SEVEN:
        assert contract.refused[name] == detail[name]["model"]["refused"], name
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
