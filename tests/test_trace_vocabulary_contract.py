"""The trace-vocabulary contract: generated from the model, read by the runtime.

The runtime serves the trace relations and the retired relation names from
the generated ``trace-vocabulary-contract.json`` and never parses SysML text
(ADR 0011). The generator's adversarial reading cases (comments, quoted
tokens, decoys, duplicates) are in ``test_trace_vocabulary_traversal.py``
and ``test_semantic_payload_identity.py``.
"""
from __future__ import annotations

import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest

from de4sdv.semantic import model_contract as mc
from de4sdv.semantic import trace_vocabulary_contract as generator

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DATA = "de4sdv/semantic/contract-data"
KERNEL = "textual-notation-of-model/packages/methods/de4sdv"


def _copy(root: Path, *relatives: str) -> Path:
    for relative in relatives:
        shutil.copytree(ROOT / relative, root / relative)
    return root


def _document() -> dict:
    return json.loads((ROOT / mc.TRACE_CONTRACT_PATH).read_text(encoding="utf-8"))


def _write_document(root: Path, document: dict | str) -> None:
    path = root / mc.TRACE_CONTRACT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document if isinstance(document, str) else json.dumps(document), encoding="utf-8")


def _provisions():
    return mc.load_model_layers(ROOT)[1]


def test_the_committed_contract_matches_regeneration():
    assert generator.run_check_errors(ROOT) == []
    document = _document()
    assert set(document) == {"schema", "warning", "contract"}
    assert document["schema"] == mc.TRACE_CONTRACT_SCHEMA
    contract = document["contract"]
    assert set(contract["relations"]) == {"allocatedTo", "hasValidationScenario", "hasRegulatorySource"}
    assert set(contract["retired"]) == {"realizedBy", "deployedTo", "constrainedBy", "validatedBy",
                                        "validatesFitnessForUse"}
    assert contract["id"] == mc.trace_contract_id(contract)


def test_the_generator_reports_a_missing_or_stale_contract(tmp_path):
    root = _copy(tmp_path, CONTRACT_DATA, KERNEL)
    assert generator.run_check_errors(root) == []
    (root / mc.TRACE_CONTRACT_PATH).unlink()
    errors = generator.run_check_errors(root)
    assert len(errors) == 1 and "missing" in errors[0] and generator.GENERATOR in errors[0]
    document = _document()
    document["contract"]["supersedes"] = "edited by hand"
    document["contract"]["id"] = mc.trace_contract_id(document["contract"])
    _write_document(root, mc.canonical_json(document))
    errors = generator.run_check_errors(root)
    assert len(errors) == 1 and "differs from regeneration" in errors[0]


def test_a_model_change_reaches_the_runtime_only_through_regeneration(tmp_path):
    root = _copy(tmp_path, CONTRACT_DATA, KERNEL)
    model = root / generator.MODEL
    model.write_text(model.read_text(encoding="utf-8").replace(
        'attribute :>> strength = "validation-planning";', 'attribute :>> strength = "planning";'),
        encoding="utf-8")
    # The runtime still serves the committed contract; the gate names the stale file.
    assert mc.load_trace_contract(root)["relations"]["hasValidationScenario"][0]["strength"] == \
        "validation-planning"
    assert any("differs from regeneration" in error for error in generator.run_check_errors(root))
    _write_document(root, mc.canonical_json(generator.build_document(root)))
    assert generator.run_check_errors(root) == []
    assert mc.load_trace_contract(root)["relations"]["hasValidationScenario"][0]["strength"] == "planning"


def test_the_runtime_builds_the_contract_without_any_sysml_source(tmp_path):
    """ADR 0011: the served contract and its identity come from data files only."""
    root = _copy(tmp_path, CONTRACT_DATA)
    assert not list(root.rglob("*.sysml"))
    assert mc.build_model_contract(root).identity == mc.build_model_contract(ROOT).identity
    assert mc.load_trace_contract(root) == mc.load_trace_contract(ROOT)


def test_every_input_of_the_runtime_contract_exists_and_is_data():
    assert mc.TRACE_CONTRACT_INPUTS[0] == mc.TRACE_CONTRACT_PATH
    assert len(set(mc.TRACE_CONTRACT_INPUTS)) == len(mc.TRACE_CONTRACT_INPUTS)
    for relative in mc.TRACE_CONTRACT_INPUTS:
        assert (ROOT / relative).is_file(), relative
        assert relative.startswith(CONTRACT_DATA + "/") and relative.endswith(".json"), relative


def _mutated(mutate):
    """A copy of the committed document with one mutation and a consistent id."""
    document = _document()
    contract = document["contract"]
    mutate(contract)
    if set(mc.TRACE_CONTRACT_FIELDS) <= set(contract):
        contract["id"] = mc.trace_contract_id(contract)
    return document


MALFORMED = {
    "extra field": (lambda c: c.update(policy="serve every name"), "fields must be exactly"),
    "missing field": (lambda c: c.pop("retired"), "fields must be exactly"),
    "unknown mechanism": (lambda c: c["relations"]["allocatedTo"][0].update(mechanism="name-match"),
                          "unsupported mechanism"),
    "row of another predicate": (lambda c: c["relations"]["allocatedTo"][0].update(predicate="hasRegulatorySource"),
                                 "names another predicate"),
    "incomplete row": (lambda c: c["relations"]["allocatedTo"][0].pop("inverse"), "incomplete or malformed"),
    "endpoint class without a pin": (lambda c: c["classes"].pop("Function"), "endpoint class without a pin"),
    "extra class pin": (lambda c: c["classes"].update(Extra={"file": "x.sysml", "declaration": "part def Extra"}),
                        "exactly the endpoint classes"),
    "conflicting rows": (lambda c: c["relations"]["allocatedTo"][1].update(strength="satisfaction"),
                         "conflicting rows"),
    "duplicate row": (lambda c: c["relations"]["allocatedTo"].append(dict(c["relations"]["allocatedTo"][0])),
                      "duplicate row"),
    "carrier pin on an allocation": (
        lambda c: c["carriers"].update(allocatedTo={"file": "x.sysml", "declaration": "connection def X"}),
        "carrier pin exactly when"),
    "carrier pin naming another carrier": (
        lambda c: c["carriers"]["hasRegulatorySource"].update(declaration="connection def Other"),
        "not one of its carriers"),
    "retired name without a reason": (lambda c: c["retired"].update(realizedBy=" "), "has no reason"),
    "retired name still served": (lambda c: c["retired"].update(allocatedTo="retired"),
                                  "overlapping relationship identities"),
    "malformed pin": (lambda c: c["classes"]["Function"].update(declaration="Function"), "malformed declaration"),
}


@pytest.mark.parametrize("case", sorted(MALFORMED))
def test_the_runtime_refuses_a_malformed_contract(tmp_path, case):
    mutate, message = MALFORMED[case]
    _write_document(tmp_path, _mutated(mutate))
    with pytest.raises(mc.ModelAuthorityRefused, match=message):
        mc.load_trace_contract(tmp_path, provisions=_provisions())


def test_the_runtime_refuses_an_id_that_is_not_the_digest_of_the_meaning(tmp_path):
    document = _document()
    document["contract"]["relations"]["allocatedTo"][0]["strength"] = "satisfaction"
    document["contract"]["relations"]["allocatedTo"][1]["strength"] = "satisfaction"
    document["contract"]["relations"]["allocatedTo"][2]["strength"] = "satisfaction"
    _write_document(tmp_path, document)
    with pytest.raises(mc.ModelAuthorityRefused, match="id is not the digest of its meaning"):
        mc.load_trace_contract(tmp_path, provisions=_provisions())


def test_the_runtime_refuses_class_pins_the_layers_do_not_hold(tmp_path):
    document = _document()
    contract = document["contract"]
    contract["classes"]["Function"] = {"file": generator.MODEL, "declaration": "action def OtherFunction"}
    contract["id"] = mc.trace_contract_id(contract)
    _write_document(tmp_path, document)
    with pytest.raises(mc.ModelAuthorityRefused, match="class pins differ from the projection layers: Function"):
        mc.load_trace_contract(tmp_path, provisions=_provisions())


@pytest.mark.parametrize("raw,message", [
    ("{", "unreadable"),
    ('{"schema": "de4sdv.trace-vocabulary-contract/v1", "schema": "x", "warning": "", "contract": {}}',
     "duplicate JSON object key"),
    ('{"schema": "de4sdv.other/v1", "warning": "", "contract": {}}', "malformed"),
    ('{"schema": "de4sdv.trace-vocabulary-contract/v1", "contract": {}}', "malformed"),
])
def test_the_runtime_refuses_an_unreadable_or_foreign_document(tmp_path, raw, message):
    _write_document(tmp_path, raw)
    with pytest.raises(mc.ModelAuthorityRefused, match=message):
        mc.load_trace_contract(tmp_path, provisions=_provisions())


def test_check_repo_runs_the_trace_contract_check_and_fails_when_it_fails():
    import contextlib
    from unittest import mock

    from scripts import check_repo
    from test_retired_semantic_authority import _passing_gate_mocks

    def run(patch):
        with contextlib.ExitStack() as stack:
            for m in _passing_gate_mocks():
                stack.enter_context(m)
            stack.enter_context(patch)
            return check_repo.main()

    calls = []
    assert run(mock.patch.object(generator, "run_check_errors",
                                 side_effect=lambda root: calls.append(root) or [])) == 0
    assert calls, "check_repo did not run the trace-vocabulary contract check"
    assert run(mock.patch.object(generator, "run_check_errors",
                                 return_value=["sentinel trace-contract error"])) == 1


def test_a_tampered_document_is_never_served_by_the_facade(tmp_path):
    from de4sdv.semantic import model_authority_runtime as mar

    root = _copy(tmp_path, CONTRACT_DATA)
    document = _document()
    changed = deepcopy(document)
    changed["contract"]["relations"]["hasRegulatorySource"][0]["strength"] = "compliance"
    _write_document(root, changed)
    with pytest.raises(mc.ModelAuthorityRefused, match="id is not the digest"):
        mar.model_facade(root)
