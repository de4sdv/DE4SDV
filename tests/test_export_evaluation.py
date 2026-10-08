"""Input-agnostic increment evaluation: API listing and offline export.

The same revision evaluated through the semantic service (API listing, any
element order) and offline from its export plus validated binding yields the
same canonical projections and the same evaluation key. An export alone is
evaluated as an export snapshot with export-validated kernel identity.
Identity mismatches refuse the evaluation.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from de4sdv.semantic.export_evaluation import (
    EXPORT_SNAPSHOT_SCOPE,
    ExportEvaluationRefused,
    evaluate_export,
)
from increment_model_fixtures import increment_scenario, method_gates
from model_contract_fixtures import binding_dict, model_service, synthetic_identity
from de4sdv.sysml_api.revisions import RevisionBinding
from test_increment_evaluation import P4, synthetic_method
from test_semantic_method_tools import INCREMENT, _Repository

GIT = "c" * 40


def _canonical(response: dict) -> dict:
    payload = copy.deepcopy(response)
    payload.pop("presentation", None)
    payload.pop("service_provenance", None)
    return payload


def _write(tmp_path: Path, scenario, **binding_overrides) -> tuple[Path, Path]:
    export = scenario.builder.export(git_commit=GIT)
    export_path = tmp_path / "export.json"
    export_path.write_text(json.dumps(export))
    document = binding_dict(git_commit=GIT, sysml_project_id="project", sysml_commit_id="commit",
                            kernel_bindings=scenario.builder.bindings, **binding_overrides)
    binding_path = tmp_path / "binding.json"
    binding_path.write_text(json.dumps(document))
    return export_path, binding_path


def _scenario():
    scenario = increment_scenario()
    scenario.builder.kernel_definition("AcceptanceCriterion")
    method_gates(scenario.builder, synthetic_method())
    # Make the model gappy so every projection carries content.
    need = scenario.needs[1]
    builder = scenario.builder
    builder.remove(*[e for e in builder.elements if e.get("@type") == "StakeholderMembership"
                     and e.get("owningRelatedElement", {}).get("@id") == need["@id"]])
    return scenario


def test_api_listing_and_export_evaluate_identically(tmp_path: Path) -> None:
    scenario = _scenario()
    export_path, binding_path = _write(tmp_path, scenario)
    document = json.loads(binding_path.read_text())
    reordered = list(reversed(scenario.builder.elements))
    service = model_service(RevisionBinding.from_dict(document), _Repository(reordered))
    snapshot, offline = evaluate_export(export_path, INCREMENT, binding_path=binding_path)
    assert snapshot.identity_mode == "validated-revision-binding"
    assert offline.evaluation_key == service.increment_evaluation(INCREMENT).evaluation_key
    for api, export in (
        (service.increment_status(increment=INCREMENT), offline.status()),
        (service.method_gaps(increment=INCREMENT), offline.gaps()),
        (service.next_obligation(increment=INCREMENT), offline.next_obligation()),
        (service.next_obligation(P4, increment=INCREMENT), offline.next_obligation(P4)),
    ):
        assert _canonical(api) == _canonical(export)
    assert "presentation" in offline.gaps()
    assert "presentation" not in service.method_gaps(increment=INCREMENT)


def test_an_export_alone_is_evaluated_as_an_export_snapshot(tmp_path: Path) -> None:
    scenario = _scenario()
    export_path, binding_path = _write(tmp_path, scenario)
    _snapshot, bound = evaluate_export(export_path, INCREMENT, binding_path=binding_path)
    snapshot, alone = evaluate_export(export_path, INCREMENT)
    assert snapshot.identity_mode == "export-validated-kernel-bindings"
    assert snapshot.revision.scope == EXPORT_SNAPSHOT_SCOPE
    assert (snapshot.revision.sysml_project_id, snapshot.revision.sysml_commit_id) == ("", "")
    assert alone.evaluation_key != bound.evaluation_key
    states = lambda evaluation: {u.unit_id: (u.verdict or u.state) for u in evaluation.canonical.units}
    assert states(alone) == states(bound)


def test_a_retired_binding_is_refused(tmp_path: Path) -> None:
    scenario = _scenario()
    export_path, binding_path = _write(tmp_path, scenario)
    document = json.loads(binding_path.read_text())
    document["ontology"] = {"path": "retired.yaml", "sha256": "0" * 64}
    binding_path.write_text(json.dumps(document))
    with pytest.raises(ExportEvaluationRefused, match="retired"):
        evaluate_export(export_path, INCREMENT, binding_path=binding_path)


def test_a_binding_of_another_commit_is_refused(tmp_path: Path) -> None:
    scenario = _scenario()
    export_path, binding_path = _write(tmp_path, scenario)
    document = json.loads(binding_path.read_text())
    document["git_commit"] = "d" * 40
    binding_path.write_text(json.dumps(document))
    with pytest.raises(ExportEvaluationRefused, match="different Git/API identity"):
        evaluate_export(export_path, INCREMENT, binding_path=binding_path)


def test_a_binding_of_another_semantic_authority_is_refused(tmp_path: Path) -> None:
    scenario = _scenario()
    export_path, binding_path = _write(
        tmp_path, scenario, semantic_authority=synthetic_identity("other").to_dict())
    with pytest.raises(ExportEvaluationRefused, match="semantic authority"):
        evaluate_export(export_path, INCREMENT, binding_path=binding_path)


def test_command_line_evaluates_and_refuses(tmp_path: Path, capsys) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "evaluate_increment", Path(__file__).resolve().parents[1] / "scripts/evaluate_increment.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    scenario = _scenario()
    export_path, binding_path = _write(tmp_path, scenario)
    output = tmp_path / "result.json"
    code = module.main(["--export", str(export_path), "--binding", str(binding_path),
                        "--increment", INCREMENT, "--query", "next", "--output", str(output)])
    assert code == 0
    report = json.loads(output.read_text())
    assert report["next"]["next"]["gate"] == "needStakeholder"
    assert set(report["timings"]) >= {"load_seconds", "evaluation_seconds", "total_seconds"}
    assert module.main(["--export", str(export_path), "--increment", "not-an-increment"]) == 2
    capsys.readouterr()
