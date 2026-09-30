"""Qualification observations never imply adoption or constraint execution."""
from __future__ import annotations

import importlib

import pytest


def module():
    try:
        return importlib.import_module("de4sdv.semantic.ple_qualification")
    except ModuleNotFoundError:
        pytest.fail("the current-toolchain PLE qualification runner is missing")


def row(concept, *, adequate=True):
    return {
        "concept": concept,
        "object_observable": True,
        "semantic_properties_retained": adequate,
        "provenance_retained": True,
        "api_only_consumption_adequate": adequate,
        "exact_gap": "" if adequate else "shape unsupported",
        "evidence": [{"uuid": "synthetic-id", "metatype": "PartDefinition"}],
    }


def test_six_cases_are_accounted_without_promoting_observation_to_adoption():
    report = module().build_case_report([row("FeatureBinding")], [row("FeatureBinding")])
    assert len(report["cases"]) == 6
    assert len({item["case"] for item in report["cases"]}) == 6
    assert report["adoption_authorized"] is False
    assert report["qualified"] is False
    cases = {item["case"]: item for item in report["cases"]}
    assert cases["xor-counterexample"]["native_expression_executed"] is False
    assert cases["feature-binding"]["multiple_binding_semantics_proven"] is False
    assert cases["binding-time"]["stage_aware_evaluation_proven"] is False


def test_missing_and_duplicate_concepts_refuse_or_remain_explicit_gaps():
    report = module().build_case_report([], [])
    assert all(item["status"] == "gap" for item in report["cases"])
    with pytest.raises(ValueError, match="duplicate"):
        module().build_case_report([row("FeatureBinding"), row("FeatureBinding")], [])


def test_semantic_difference_requires_review_instead_of_inferring_cause():
    report = module().build_case_report([row("FeatureBinding", adequate=False)], [row("FeatureBinding")])
    delta = next(item for item in report["differences"] if item["concept"] == "FeatureBinding")
    assert delta["classification"] == "review-required"
    assert delta["before"]["api_only_consumption_adequate"] is True
    assert delta["after"]["api_only_consumption_adequate"] is False


def test_uuid_changes_are_not_semantic_changes_but_metatype_changes_are():
    before = row("FeatureBinding")
    after = row("FeatureBinding")
    after["evidence"][0]["uuid"] = "fresh-synthetic-id"
    assert module().build_case_report([after], [before])["differences"] == []
    after["evidence"][0]["metatype"] = "Dependency"
    assert module().build_case_report([after], [before])["differences"]


@pytest.mark.parametrize("value", [None, {}, "not-a-matrix", [None], [{"concept": "FeatureBinding"}]])
def test_malformed_matrix_is_refused(value):
    with pytest.raises(ValueError):
        module().build_case_report(value, [])


def test_historical_replay_is_bound_and_cannot_be_called_current(tmp_path):
    import json
    import subprocess
    import sys
    from pathlib import Path

    script = Path(__file__).resolve().parents[1] / "scripts/run_ple_qualification.py"
    assert script.is_file(), "the executable qualification runner is missing"
    historical = Path("/tmp/pleml-gate-a-run-corr/pleml-gate-a-acc7cfbbbe0a0d8b6c04ceaa3ecf23035bbe15ec/de4sdv-pleml-gate-a-export.json")
    frozen = Path("/tmp/de4sdv-pleml-gate-a")
    if not historical.is_file() or not frozen.is_dir():
        pytest.skip("optional retained controller artifact unavailable")
    result = subprocess.run([sys.executable, "-B", str(script), "--experiment", str(frozen),
                             "--historical-export", str(historical), "--out", str(tmp_path / "receipt.json")],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    receipt = json.loads((tmp_path / "receipt.json").read_text())
    assert receipt["historical"] is True
    assert receipt["fresh_serialization"] is False
    assert receipt["qualified"] is False
    assert len(receipt["cases"]) == 6
    assert receipt["source_identity"]["interpreter_revision"] != receipt["source_identity"]["historical_export_revision"]


def test_licensed_workflow_is_qualification_only_and_pins_both_checkouts():
    from pathlib import Path
    import yaml

    root = Path(__file__).resolve().parents[1]
    path = root / ".github/workflows/privileged-ple-qualification.yml"
    assert path.is_file(), "current-toolchain qualification workflow is missing"
    workflow = yaml.safe_load(path.read_text())
    assert workflow["permissions"] == {"contents": "read", "actions": "read"}
    job = workflow["jobs"]["qualify"]
    checkouts = [item for item in job["steps"] if item.get("uses", "").startswith("actions/checkout@")]
    assert len(checkouts) == 2
    assert checkouts[1]["with"]["ref"] == "6a99626b4af7cd01108f27dac88bf5b55bba207a"
    assert checkouts[0]["with"]["persist-credentials"] is False
    runs = "\n".join(item.get("run", "") for item in job["steps"])
    assert "--expected-executor" in runs
    assert "http://127.0.0.1:9000" in runs
    assert "${{ inputs." not in runs
    assert "deploy.py" not in runs
    assert "git push" not in runs
    assert "gh pr merge" not in runs


def runner():
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "scripts/run_ple_qualification.py"
    spec = importlib.util.spec_from_file_location("_test_ple_qualification_runner", path)
    assert spec is not None and spec.loader is not None
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


@pytest.mark.parametrize("values", [[], [{"@id": "different", "@type": "PartDefinition"}],
                                    [{"@id": "synthetic", "@type": "Dependency"}],
                                    [{"@id": "synthetic", "@type": "PartDefinition"}] * 2,
                                    [None]])
def test_api_uuid_metatype_and_population_drift_is_refused(values):
    from types import SimpleNamespace

    bundle = SimpleNamespace(elements={"synthetic": {"@id": "synthetic", "@type": "PartDefinition"}})
    with pytest.raises(ValueError):
        runner().verify_readback(bundle, values)


def test_api_uuid_and_metatype_identity_is_preserved():
    from types import SimpleNamespace

    values = [{"@id": "synthetic", "@type": "PartDefinition"}]
    assert runner().verify_readback(SimpleNamespace(elements={"synthetic": values[0]}), values) == values


@pytest.mark.parametrize("mutation", ["delete", "replace", "dangling", "duplicate", "move"])
def test_final_api_readback_refuses_internal_reference_drift(mutation):
    import copy
    from types import SimpleNamespace

    expected = [
        {"@id": "a", "@type": "PartDefinition", "ownedRelationship": [{"@id": "b"}]},
        {"@id": "b", "@type": "PartUsage"},
        {"@id": "c", "@type": "PartUsage"},
    ]
    actual = copy.deepcopy(expected)
    if mutation == "delete":
        actual[0].pop("ownedRelationship")
    elif mutation == "replace":
        actual[0]["ownedRelationship"] = [{"@id": "c"}]
    elif mutation == "dangling":
        actual[0]["extra"] = {"@id": "missing"}
    elif mutation == "duplicate":
        actual[0]["ownedRelationship"].append({"@id": "b"})
    else:
        actual[0]["nested"] = {"ownedRelationship": actual[0].pop("ownedRelationship")}
    bundle = SimpleNamespace(elements={item["@id"]: item for item in expected})
    with pytest.raises(ValueError, match="reference"):
        runner().verify_readback(bundle, actual)


def test_internal_reference_list_order_is_not_semantic_drift():
    import copy
    from types import SimpleNamespace

    expected = [
        {"@id": "a", "@type": "PartDefinition", "nested": {"member": [{"@id": "b"}, {"@id": "c"}]}},
        {"@id": "b", "@type": "PartUsage"},
        {"@id": "c", "@type": "PartUsage"},
    ]
    actual = copy.deepcopy(expected)
    actual[0]["nested"]["member"].reverse()
    bundle = SimpleNamespace(elements={item["@id"]: item for item in expected})
    assert runner().verify_readback(bundle, actual) == actual


@pytest.mark.parametrize("artifact_id", [9814891861, 123456789])
@pytest.mark.parametrize("run_ids", [(33543909037, 33543909037),
                                    (123456789, 33543909037),
                                    (33543909037, 123456789)])
def test_workflow_origin_refuses_same_name_different_artifact_id(tmp_path, monkeypatch, artifact_id, run_ids):
    import json
    import subprocess
    from pathlib import Path
    import yaml

    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load((root / ".github/workflows/privileged-ple-qualification.yml").read_text())
    step = next(item for item in workflow["jobs"]["qualify"]["steps"] if item.get("id") == "origin")
    code = step["run"].split("python - <<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    revision, frozen = "1" * 40, "6a99626b4af7cd01108f27dac88bf5b55bba207a"
    repository = "de4sdv/DE4SDV"
    run = {"id": run_ids[0], "head_sha": frozen, "status": "completed", "conclusion": "success",
           "event": "pull_request", "path": ".github/workflows/privileged-pleml-gate-a.yml",
           "repository": {"full_name": repository}}
    artifact = {"id": artifact_id, "name": "pleml-gate-a-" + frozen, "expired": False,
                "workflow_run": {"id": run_ids[1], "head_sha": frozen}}

    def output(command, **kwargs):
        if command[0] == "git":
            return revision + "\n"
        value = {"total_count": 1, "artifacts": [artifact]} if "/artifacts?" in command[-1] else run
        return json.dumps(value).encode()

    monkeypatch.setattr(subprocess, "check_output", output)
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SELECTED_REVISION", revision)
    monkeypatch.setenv("GITHUB_REPOSITORY", repository)
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "outputs"))
    if artifact_id != 9814891861 or run_ids != (33543909037, 33543909037):
        with pytest.raises(SystemExit, match="historical"):
            exec(compile(code, "workflow-origin", "exec"), {})
        assert not (tmp_path / "ple-evidence/provider-origin.json").exists()
    else:
        exec(compile(code, "workflow-origin", "exec"), {})
        assert (tmp_path / "outputs").read_text() == "artifact_id=9814891861\n"


@pytest.mark.parametrize("payload", [{"extra": {"@id": "missing"}},
                                   {"extra": {"@id": "b"}},
                                   {"declaredName": "unexpected"}])
def test_readback_refuses_noncanonical_reference_objects(payload):
    import copy
    from types import SimpleNamespace

    expected = [{"@id": "a", "@type": "PartDefinition", "member": [{"@id": "b"}]},
                {"@id": "b", "@type": "PartUsage"}]
    actual = copy.deepcopy(expected)
    actual[0]["member"][0].update(payload)
    bundle = SimpleNamespace(elements={item["@id"]: item for item in expected})
    with pytest.raises(ValueError, match="reference"):
        runner().verify_readback(bundle, actual)
