"""Qualification observations never imply adoption or constraint execution."""
from __future__ import annotations

import dataclasses
import hashlib
import importlib
import importlib.util
import json
import lzma
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

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


def test_licensed_workflow_is_qualification_only_and_pins_every_checkout():
    from pathlib import Path
    import yaml

    root = Path(__file__).resolve().parents[1]
    path = root / ".github/workflows/privileged-ple-qualification.yml"
    assert path.is_file(), "current-toolchain qualification workflow is missing"
    workflow = yaml.safe_load(path.read_text())
    assert workflow["permissions"] == {"contents": "read", "actions": "read"}
    job = workflow["jobs"]["qualify"]
    checkouts = [item for item in job["steps"] if item.get("uses", "").startswith("actions/checkout@")]
    # The executor, the experiment at PLEML 1.0.0 (scoped probes, fresh
    # serialization) and the Gate A experiment (historical replay, prior).
    assert len(checkouts) == 3
    executor, experiment, gate_a = checkouts
    assert experiment["with"]["ref"] == "84673ea2bca0d11b795a34afeb7584081dd24fd2" == runner().CURRENT.revision
    assert gate_a["with"]["ref"] == "6a99626b4af7cd01108f27dac88bf5b55bba207a" == runner().GATE_A.revision
    assert experiment["with"]["path"] == "_ple-experiment" and gate_a["with"]["path"] == "_ple-gate-a"
    for checkout in (experiment, gate_a):
        assert checkout["with"]["submodules"] == "recursive"
    for checkout in checkouts:
        assert checkout["with"]["persist-credentials"] is False
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


def _run_origin_step(tmp_path, monkeypatch, *, run_id=33543909037, tamper=None):
    import json
    import shutil
    import subprocess
    from pathlib import Path
    import yaml

    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load((root / ".github/workflows/privileged-ple-qualification.yml").read_text())
    step = next(item for item in workflow["jobs"]["qualify"]["steps"] if item.get("id") == "origin")
    code = step["run"].split("python - <<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    revision, frozen = "1" * 40, "6a99626b4af7cd01108f27dac88bf5b55bba207a"
    repository = "de4sdv/DE4SDV"
    run = {"id": run_id, "head_sha": frozen, "status": "completed", "conclusion": "success",
           "event": "pull_request", "path": ".github/workflows/privileged-pleml-gate-a.yml",
           "repository": {"full_name": repository}}
    # The step runs in the executor checkout and may only read it: the
    # qualification receipts record its `git status`. Inputs and evidence go
    # to the runner's temporary directory.
    checkout, temp = tmp_path / "checkout", tmp_path / "runner-temp"
    base = checkout / "docs/product-line-engineering/gate-a-baseline"
    shutil.copytree(root / "docs/product-line-engineering/gate-a-baseline", base)
    temp.mkdir()
    if tamper:
        tamper(base)
    calls = []

    def output(command, **kwargs):
        calls.append(command)
        if command[0] == "git":
            return revision + "\n"
        return json.dumps(run).encode()

    monkeypatch.setattr(subprocess, "check_output", output)
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.chdir(checkout)
    monkeypatch.setenv("SELECTED_REVISION", revision)
    monkeypatch.setenv("GITHUB_REPOSITORY", repository)
    monkeypatch.setenv("GITHUB_OUTPUT", str(temp / "outputs"))
    monkeypatch.setenv("RUNNER_TEMP", str(temp))
    before = _tree(checkout)
    try:
        exec(compile(code, "workflow-origin", "exec"), {})
    finally:
        assert _tree(checkout) == before, "the origin step wrote into the executor checkout"
    return calls


def _tree(path):
    return sorted(item.relative_to(path).as_posix() for item in path.rglob("*"))


def test_workflow_origin_materializes_exact_retained_baseline(tmp_path, monkeypatch):
    import hashlib
    import json

    calls = _run_origin_step(tmp_path, monkeypatch)
    temp = tmp_path / "runner-temp"
    export = (temp / "_ple-baseline/de4sdv-pleml-gate-a-export.json").read_bytes()
    assert hashlib.sha256(export).hexdigest() == (
        "cf129d6884dc38555a0a725ad516d06fa6cf1ff2d11d6cda0bb1d5bc1ae51b7d")
    assert (temp / "outputs").read_text() == "artifact_id=9814891861\n"
    origin = json.loads((temp / "ple-evidence/provider-origin.json").read_text())
    assert origin["historical_artifact"]["id"] == 9814891861
    assert origin["historical_artifact"]["export_sha256"].startswith("cf129d68")
    assert origin["historical_artifact"]["retained_copy"] == (
        "docs/product-line-engineering/gate-a-baseline/de4sdv-pleml-gate-a-export.json.xz")
    # The expired provider artifact inventory is no longer consulted.
    assert not any("/artifacts" in str(command[-1]) for command in calls if command[0] == "gh")


@pytest.mark.parametrize("run_id", [123456789])
def test_workflow_origin_refuses_foreign_historical_run(tmp_path, monkeypatch, run_id):
    with pytest.raises(SystemExit, match="historical origin mismatch"):
        _run_origin_step(tmp_path, monkeypatch, run_id=run_id)
    assert not (tmp_path / "runner-temp/ple-evidence/provider-origin.json").exists()
    assert not (tmp_path / "runner-temp/_ple-baseline").exists()


def _flip_byte(base):
    path = base / "de4sdv-pleml-gate-a-export.json.xz"
    data = bytearray(path.read_bytes())
    data[len(data) // 2] ^= 0x01
    path.write_bytes(bytes(data))


def _edit_manifest(field, value):
    def tamper(base):
        import json
        manifest = json.loads((base / "manifest.json").read_text())
        manifest[field] = value
        (base / "manifest.json").write_text(json.dumps(manifest))
    return tamper


def _replace_export(base):
    import json
    import lzma
    import hashlib
    forged = json.dumps({"git_commit": "0" * 40, "elements": []}).encode()
    compressed = lzma.compress(forged)
    (base / "de4sdv-pleml-gate-a-export.json.xz").write_bytes(compressed)
    manifest = json.loads((base / "manifest.json").read_text())
    manifest["compressed_sha256"] = hashlib.sha256(compressed).hexdigest()
    (base / "manifest.json").write_text(json.dumps(manifest))


@pytest.mark.parametrize("tamper,message", [
    (_flip_byte, "digest mismatch"),
    (_edit_manifest("historical_artifact_id", 123456789), "manifest mismatch"),
    (_edit_manifest("historical_run", 123456789), "manifest mismatch"),
    (_edit_manifest("frozen_revision", "0" * 40), "manifest mismatch"),
    (_edit_manifest("export_sha256", "0" * 64), "manifest mismatch"),
    (_replace_export, "manifest mismatch"),
])
def test_workflow_origin_refuses_tampered_retained_baseline(tmp_path, monkeypatch, tamper, message):
    with pytest.raises(SystemExit, match=message):
        _run_origin_step(tmp_path, monkeypatch, tamper=tamper)
    assert not (tmp_path / "runner-temp/ple-evidence/provider-origin.json").exists()
    assert not (tmp_path / "runner-temp/_ple-baseline").exists()


def test_workflow_no_longer_downloads_expired_provider_artifact():
    from pathlib import Path
    import yaml

    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load((root / ".github/workflows/privileged-ple-qualification.yml").read_text())
    steps = workflow["jobs"]["qualify"]["steps"]
    assert not any("download-artifact" in str(item.get("uses", "")) for item in steps)


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


# -- PLEML 1.0.0 re-qualification: two experiment identities ------------------------------
#
# The historical replay (PLE-R) and the prior of the fresh arm stay on the
# Gate A experiment; the scoped probes, the fresh serialization and the scope
# alignment run on the experiment at PLEML 1.0.0. These tests read committed
# data and Git objects only (CI fetches the full history and the tags).

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "docs/product-line-engineering/gate-a-baseline"
FIXTURE = "docs/spikes/pleml-gate-a/pleml_gate_a_fixture.sysml"
#: The case statuses of the Gate A experiment on its own export (run 38780181818).
GATE_A_CASES = {
    "xor-counterexample": ("gap", ["Native constraint expression probe"]),
    "feature-binding": ("observed", []),
    "group-shapes": ("observed", []),
    "binding-time": ("gap", ["Lifecycle metadata"]),
    "serializer-identity": ("gap", [
        "Adapter realization rule", "Common capability outside feature tree", "Feature",
        "Feature configuration", "Feature model", "Feature tree", "Lifecycle metadata",
        "Native constraint expression probe", "Native variation", "Parent/child membership",
        "Selected feature relationship"]),
    "adapter-realization": ("gap", ["Adapter realization rule"]),
}
#: The two rows that read the PLEML library by its source label.
LABEL_BOUND_ROWS = ["Incompatibility constraint", "Requires relationship"]
#: The reviewed change of the experiment at PLEML 1.0.0 against Gate A.
REVIEWED_PATHS = {
    ".github/workflows/privileged-pleml-gate-a.yml", "docs/spikes/pleml-gate-a/README.md",
    "external/pleml", "tests/test_pleml_api_observability.py", "tools/pleml_gate_a.py",
}
REVIEWED_INTERPRETER_CHANGE = (
    ['PLEML_PIN = "5f8ab8560219dc24d8ec7ec90d6f0a145896ef8e"',
     'PLEML_SOURCE = Path("external/pleml/PLEML/PLEML.sysml")',
     '            and element_sources.get(_ref_id(e) or "") == "external/pleml/PLEML/PLEML.sysml"'],
    ['PLEML_PIN = "071a69fdb2ecfa154809913938dfe9ebdf37701b"',
     'PLEML_SOURCE = Path("external/pleml/PLEML.sysml")',
     '            and element_sources.get(_ref_id(e) or "") == PLEML_SOURCE.as_posix()'],
)


def _git_object(*args):
    """A Git object read in this repository; missing history fails in CI and skips elsewhere."""
    result = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, check=False)
    if result.returncode:
        message = f"Git object unavailable ({' '.join(args)}); fetch the full history and the tags"
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail(message)
        pytest.skip(message)
    return result.stdout


def _interpreter_at(identity, directory):
    """tools/pleml_gate_a.py of an identity's revision, imported after its digest is verified."""
    data = _git_object("show", f"{identity.revision}:tools/pleml_gate_a.py")
    assert hashlib.sha256(data).hexdigest() == identity.interpreter_sha256
    path = directory / f"pleml_gate_a_{identity.revision[:12]}.py"
    path.write_bytes(data)
    name = f"_test_ple_interpreter_{identity.revision[:12]}_{directory.name}"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # its dataclasses resolve annotations through sys.modules
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


def _committed_export(directory):
    """The retained Gate A export, decompressed to a file as the workflow materializes it."""
    manifest = json.loads((BASELINE / "manifest.json").read_text())
    data = lzma.decompress((BASELINE / manifest["file"]).read_bytes())
    path = directory / "de4sdv-pleml-gate-a-export.json"
    path.write_bytes(data)
    return path, json.loads(data)


def _elements_and_sources(raw):
    from de4sdv.sysml_api.baseline import BaselineExportBundle

    bundle = BaselineExportBundle.from_dict(raw)
    return list(bundle.elements.values()), dict(bundle.element_sources)


def _moved(sources, old, new):
    assert old in sources.values()
    return {key: (new if value == old else value) for key, value in sources.items()}


def _adequacy(matrix):
    return {row["concept"]: (row["api_only_consumption_adequate"], row["exact_gap"]) for row in matrix}


def _flipped(matrix, baseline):
    adequacy = _adequacy(matrix)
    assert set(adequacy) == set(baseline)
    return {concept: value for concept, value in adequacy.items() if value != baseline[concept]}


def test_the_current_identity_is_pleml_1_0_0_and_the_scope_alignment_identity():
    from de4sdv.semantic import ple_scope_alignment as alignment

    r = runner()
    assert r.CURRENT == r.PLEML_1_0_0 != r.GATE_A
    assert (r.FROZEN_REVISION, r.PLEML_PIN, r.LIBRARY) == (r.CURRENT.revision, r.CURRENT.pleml_pin, r.CURRENT.library)
    assert r.CURRENT.revision == "84673ea2bca0d11b795a34afeb7584081dd24fd2"
    assert r.CURRENT.pleml_pin == "071a69fdb2ecfa154809913938dfe9ebdf37701b"
    assert r.CURRENT.library == "external/pleml/PLEML.sysml"
    # PLE-S reads the same experiment: one current identity, not two.
    assert (alignment.FROZEN_REVISION, alignment.FROZEN_TAG, alignment.FROZEN_INTERPRETER_SHA256,
            alignment.PLEML_PIN, alignment.LIBRARY_SOURCE) == (
        r.CURRENT.revision, r.CURRENT.tag, r.CURRENT.interpreter_sha256, r.CURRENT.pleml_pin, r.CURRENT.library)


def test_the_gate_a_identity_is_the_retained_baseline_identity(tmp_path):
    gate_a = runner().GATE_A
    manifest = json.loads((BASELINE / "manifest.json").read_text())
    _, raw = _committed_export(tmp_path)
    assert manifest["frozen_revision"] == raw["git_commit"] == raw["gate_a_identity"]["git_commit"] == gate_a.revision
    assert raw["gate_a_identity"]["pleml_commit"] == gate_a.pleml_pin == "5f8ab8560219dc24d8ec7ec90d6f0a145896ef8e"
    assert [(entry["path"], entry["sha256"]) for entry in raw["source_manifest"]] == [
        (FIXTURE, gate_a.fixture_sha256), (gate_a.library, gate_a.library_sha256)]


@pytest.mark.parametrize("name", ["GATE_A", "PLEML_1_0_0"])
def test_each_identity_is_its_tagged_revision_with_its_interpreter_fixture_and_pin(name):
    identity = getattr(runner(), name)
    assert _git_object("rev-parse", f"{identity.tag}^{{commit}}").decode().strip() == identity.revision
    gitlink = _git_object("ls-tree", identity.revision, "external/pleml").decode().split()
    assert gitlink[:3] == ["160000", "commit", identity.pleml_pin]
    for path, expected in (("tools/pleml_gate_a.py", identity.interpreter_sha256), (FIXTURE, identity.fixture_sha256)):
        assert hashlib.sha256(_git_object("show", f"{identity.revision}:{path}")).hexdigest() == expected, path


def test_the_pleml_1_0_0_experiment_is_the_reviewed_delta_of_gate_a():
    r = runner()
    gate_a, current = r.GATE_A, r.PLEML_1_0_0
    assert _git_object("rev-parse", f"{current.revision}^").decode().strip() == gate_a.revision
    assert set(_git_object("diff", "--name-only", gate_a.revision, current.revision).decode().split()) == REVIEWED_PATHS
    diff = _git_object("diff", "--unified=0", gate_a.revision, current.revision, "--",
                       "tools/pleml_gate_a.py").decode().splitlines()
    removed = [line[1:] for line in diff if line.startswith("-") and not line.startswith("---")]
    added = [line[1:] for line in diff if line.startswith("+") and not line.startswith("+++")]
    assert (removed, added) == REVIEWED_INTERPRETER_CHANGE
    assert (_git_object("rev-parse", f"{gate_a.revision}:{FIXTURE}")
            == _git_object("rev-parse", f"{current.revision}:{FIXTURE}"))
    assert gate_a.fixture_sha256 == current.fixture_sha256


def test_the_gate_a_interpreter_reproduces_the_gate_a_cases_on_the_committed_export(tmp_path):
    from de4sdv.semantic.ple_qualification import build_case_report

    r = runner()
    gate_a = _interpreter_at(r.GATE_A, tmp_path)
    path, raw = _committed_export(tmp_path)
    prior, revision = r.historical_matrix(path, gate_a, raw["source_manifest"])
    assert revision == r.GATE_A.revision
    report = build_case_report(prior, prior)
    assert {case["case"]: (case["status"], case["inadequate_concepts"]) for case in report["cases"]} == GATE_A_CASES
    assert report["differences"] == [] and report["qualified"] is False
    outcomes = r.observe(gate_a, raw["elements"])["outcomes"]
    assert {label: value["status"] for label, value in outcomes.items()} == {
        "adapter-required-exactly-one": "derivation-complete", "valid-no-adapter": "derivation-complete",
        "configuration-invalid": "configuration-invalid", "derivation-incomplete": "derivation-incomplete",
        "derivation-ambiguous": "derivation-ambiguous"}


def test_the_gate_a_interpreter_cannot_read_the_pleml_1_0_0_library_path(tmp_path):
    """Path coupling: moving only the library label flips the two label-bound rows."""
    r = runner()
    gate_a = _interpreter_at(r.GATE_A, tmp_path)
    _, raw = _committed_export(tmp_path)
    elements, sources = _elements_and_sources(raw)
    baseline = _adequacy(gate_a.build_observability_matrix(elements, sources))
    moved = _moved(sources, r.GATE_A.library, r.PLEML_1_0_0.library)
    flipped = _flipped(gate_a.build_observability_matrix(elements, moved), baseline)
    assert sorted(flipped) == LABEL_BOUND_ROWS
    assert all(adequate is False and "found 0" in gap for adequate, gap in flipped.values())


def test_the_pleml_1_0_0_interpreter_on_the_moved_library_is_the_gate_a_matrix(tmp_path):
    from de4sdv.semantic.ple_qualification import build_case_report

    r = runner()
    gate_a, current = _interpreter_at(r.GATE_A, tmp_path), _interpreter_at(r.PLEML_1_0_0, tmp_path)
    _, raw = _committed_export(tmp_path)
    elements, sources = _elements_and_sources(raw)
    before = gate_a.build_observability_matrix(elements, sources)
    after = current.build_observability_matrix(elements, _moved(sources, r.GATE_A.library, r.PLEML_1_0_0.library))
    # The whole matrix is identical but for the library label: the change is neutral.
    assert json.dumps(after, sort_keys=True).replace(r.PLEML_1_0_0.library, r.GATE_A.library) == json.dumps(
        before, sort_keys=True)
    assert build_case_report(after, before)["differences"] == []
    # And it is bound to the new layout: on the Gate A labels the same two rows flip.
    assert sorted(_flipped(current.build_observability_matrix(elements, sources), _adequacy(before))) == LABEL_BOUND_ROWS


def test_the_prior_refuses_an_interpreter_other_than_gate_a(tmp_path):
    r = runner()
    current = _interpreter_at(r.PLEML_1_0_0, tmp_path)
    path, raw = _committed_export(tmp_path)
    with pytest.raises(ValueError, match="Gate A interpreter"):
        r.historical_matrix(path, current, raw["source_manifest"])


def test_the_prior_refuses_an_export_of_another_revision(tmp_path):
    r = runner()
    gate_a = _interpreter_at(r.GATE_A, tmp_path)
    path, raw = _committed_export(tmp_path)
    forged = dict(raw, git_commit="0" * 40, gate_a_identity=dict(raw["gate_a_identity"], git_commit="0" * 40))
    path.write_text(json.dumps(forged))
    with pytest.raises(ValueError, match="historical source manifest or identity mismatch"):
        r.historical_matrix(path, gate_a, raw["source_manifest"])


def _arguments(tmp_path, **changes):
    values = {"out": tmp_path / "out/receipt.json", "experiment": tmp_path / "experiment",
              "historical_experiment": tmp_path / "gate-a", "historical_export": tmp_path / "export.json",
              "api_url": "http://127.0.0.1:9000", "expected_executor": "a" * 40}
    values.update(changes)
    return SimpleNamespace(**values)


def test_the_fresh_arm_needs_the_gate_a_experiment_for_its_prior(tmp_path):
    args = _arguments(tmp_path, historical_experiment=None)
    with pytest.raises(ValueError, match="--historical-experiment"):
        runner().run(args)
    assert not args.out.parent.exists()


def test_the_historical_replay_reads_only_the_gate_a_experiment(tmp_path):
    args = _arguments(tmp_path, api_url=None)
    with pytest.raises(ValueError, match="--historical-experiment"):
        runner().run(args)
    assert not args.out.parent.exists()


def test_the_runner_parser_accepts_the_gate_a_experiment_of_the_fresh_arm(monkeypatch, tmp_path):
    import argparse

    seen = {}

    def spy(self, args=None, namespace=None):
        seen["namespace"] = argparse.ArgumentParser.parse_known_args(self, args, namespace)[0]
        raise SystemExit(0)

    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", spy)
    monkeypatch.setattr(sys, "argv", ["run_ple_qualification.py", "--experiment", "/tmp/e", "--historical-experiment",
                                      "/tmp/g", "--historical-export", "/tmp/x.json", "--out", "/tmp/r.json"])
    with pytest.raises(SystemExit):
        runner().main()
    assert seen["namespace"].historical_experiment == Path("/tmp/g")


def _commit(path, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                           "-c", "commit.gpgsign=false", "-c", "protocol.file.allow=always", *args],
                          cwd=path, check=True, capture_output=True, text=True).stdout.strip()


def _scratch_experiment(tmp_path, identity, *, extra_library=None):
    """A scratch experiment checkout with an identity's interpreter and fixture and a library submodule.

    Returns the checkout and the identity of the scratch commits (same layout and
    digests, scratch revisions), so load_experiment runs without the network.
    ``extra_library`` adds a second library file at another submodule path.
    """
    library_repository = tmp_path / "library"
    library_path = Path(identity.library).relative_to("external/pleml")
    (library_repository / library_path).parent.mkdir(parents=True)
    (library_repository / library_path).write_text("library package Scratch;\n")
    if extra_library is not None:
        extra = library_repository / Path(extra_library).relative_to("external/pleml")
        extra.parent.mkdir(parents=True, exist_ok=True)
        extra.write_text("library package ScratchElsewhere;\n")
    _commit(tmp_path, "init", "-q", str(library_repository))
    _commit(library_repository, "add", ".")
    _commit(library_repository, "commit", "-q", "-m", "library")
    experiment = tmp_path / "experiment"
    (experiment / "tools").mkdir(parents=True)
    (experiment / "tools/pleml_gate_a.py").write_bytes(_git_object("show", f"{identity.revision}:tools/pleml_gate_a.py"))
    (experiment / FIXTURE).parent.mkdir(parents=True)
    (experiment / FIXTURE).write_bytes(_git_object("show", f"{identity.revision}:{FIXTURE}"))
    _commit(tmp_path, "init", "-q", str(experiment))
    _commit(experiment, "remote", "add", "origin", "https://example.invalid/scratch.git")
    _commit(experiment, "add", ".")
    _commit(experiment, "submodule", "add", "-q", str(library_repository), "external/pleml")
    _commit(experiment, "commit", "-q", "-m", "experiment")
    scratch = identity._replace(
        revision=_commit(experiment, "rev-parse", "HEAD"),
        pleml_pin=_commit(experiment / "external/pleml", "rev-parse", "HEAD"),
        library_sha256=hashlib.sha256((library_repository / library_path).read_bytes()).hexdigest())
    return experiment, scratch


@pytest.mark.parametrize("name", ["GATE_A", "PLEML_1_0_0"])
def test_load_experiment_verifies_the_identity_it_is_given(tmp_path, name):
    r = runner()
    experiment, identity = _scratch_experiment(tmp_path, getattr(r, name))
    module, manifest, source = r.load_experiment(experiment, identity)
    assert [entry["path"] for entry in manifest] == [FIXTURE, identity.library]
    assert module.PLEML_SOURCE.as_posix() == identity.library
    assert source == {"interpreter_revision": identity.revision, "interpreter_sha256": identity.interpreter_sha256,
                      "fixture_sha256": identity.fixture_sha256, "library_sha256": identity.library_sha256,
                      "pleml_pin": identity.pleml_pin}
    for field, value, message in (
            ("revision", "0" * 40, "not the frozen reviewed revision"),
            ("pleml_pin", "0" * 40, "PLEML pin mismatch"),
            ("interpreter_sha256", "0" * 64, "differ from the reviewed identity"),
            ("library_sha256", "0" * 64, "differ from the reviewed identity"),
            ("fixture_sha256", "0" * 64, "differ from the reviewed identity")):
        with pytest.raises(ValueError, match=message):
            r.load_experiment(experiment, identity._replace(**{field: value}))


def test_load_experiment_refuses_an_interpreter_that_reads_another_library_path(tmp_path):
    """The Gate A interpreter in a PLEML 1.0.0 layout reads the old library path, which the identity does not name.

    Both library files exist, so the interpreter's own source check passes and
    only the runner's manifest check can refuse.
    """
    r = runner()
    experiment, identity = _scratch_experiment(tmp_path, r.PLEML_1_0_0, extra_library=r.GATE_A.library)
    gate_a_bytes = _git_object("show", f"{r.GATE_A.revision}:tools/pleml_gate_a.py")
    (experiment / "tools/pleml_gate_a.py").write_bytes(gate_a_bytes)
    _commit(experiment, "commit", "-q", "-am", "gate a interpreter in the 1.0.0 layout")
    mixed = identity._replace(revision=_commit(experiment, "rev-parse", "HEAD"),
                              interpreter_sha256=r.GATE_A.interpreter_sha256)
    with pytest.raises(ValueError, match="the experiment interpreter reads other sources than the reviewed identity"):
        r.load_experiment(experiment, mixed)


# -- the runner end to end, offline: both arms with scratch experiments --------------------
#
# GATE_A and CURRENT are replaced by scratch experiments that carry the real
# interpreters and fixture. Only Syside and the API are faked: the "fresh
# serialization" is the committed Gate A export with the library label moved to
# the 1.0.0 path (label-only), never a PLEML 1.0.0 serialization or evidence.
# The executor's own source verification is covered by the licensed runs; it is
# switched off here so these tests pin the experiment wiring only.


@dataclasses.dataclass(frozen=True)
class _OfflineImport:
    project_id: str
    commit_id: str
    element_count: int
    internal_reference_count: int
    content_sha256: str


def _offline_runner(tmp_path, monkeypatch, *, move_prior=False):
    from de4sdv.sysml_api.baseline import BaselineExportBundle, build_export_bundle

    r = runner()
    gate_a_checkout, gate_a = _scratch_experiment(tmp_path / "gate-a", r.GATE_A)
    current_checkout, current = _scratch_experiment(tmp_path / "current", r.PLEML_1_0_0)
    monkeypatch.setattr(r, "GATE_A", gate_a)
    monkeypatch.setattr(r, "CURRENT", current)
    monkeypatch.setattr(r, "EXECUTOR_INPUTS", ())
    _, gate_a_manifest, _ = r.load_experiment(gate_a_checkout, gate_a)
    export_path, raw = _committed_export(tmp_path)
    raw = dict(raw, git_commit=gate_a.revision, source_manifest=gate_a_manifest,
               gate_a_identity=dict(raw["gate_a_identity"], git_commit=gate_a.revision, pleml_commit=gate_a.pleml_pin))
    export_path.write_text(json.dumps(raw))
    seen = {}

    def serialize(root, manifest, revision):
        seen.update(root=root, revision=revision, manifest=[entry["path"] for entry in manifest])
        if move_prior:  # the Gate A checkout moves while the fresh arm runs
            interpreter = gate_a_checkout / "tools/pleml_gate_a.py"
            interpreter.write_bytes(interpreter.read_bytes() + b"\n# moved during the run\n")
        documents = {}
        for element in raw["elements"]:
            label = raw["element_sources"][element["@id"]]
            documents.setdefault(current.library if label == gate_a.library else label, []).append(element)
        bundle = build_export_bundle(git_commit=revision, source_documents=documents).to_dict()
        bundle["source_manifest"] = manifest
        return BaselineExportBundle.from_dict(bundle), r.SERIALIZER_VERSION

    class Client:
        def __init__(self, url):
            seen["api_url"] = url

        def get_all(self, path):
            return [seen["bundle"].elements[key] for key in sorted(seen["bundle"].elements)]

    def import_baseline(client, bundle, project_name):
        seen["bundle"] = bundle
        return _OfflineImport("offline-project", "offline-commit", len(bundle.elements), 0, "offline")

    monkeypatch.setattr(r, "serialize", serialize)
    monkeypatch.setattr(r, "ApiClient", Client)
    monkeypatch.setattr(r, "import_baseline", import_baseline)
    head = _commit(ROOT, "rev-parse", "HEAD")
    args = SimpleNamespace(out=tmp_path / "out/receipt.json", experiment=current_checkout,
                           historical_experiment=gate_a_checkout, historical_export=export_path,
                           api_url="http://127.0.0.1:9000", expected_executor=head)
    return r, args, gate_a, current, seen


def test_the_fresh_arm_serializes_the_current_experiment_against_the_gate_a_prior(tmp_path, monkeypatch):
    r, args, gate_a, current, seen = _offline_runner(tmp_path, monkeypatch)
    receipt = r.run(args)
    # The current experiment is the one serialized, at its own revision.
    assert seen["root"] == args.experiment.resolve() and seen["revision"] == current.revision
    assert seen["manifest"] == [FIXTURE, current.library]
    assert json.loads((args.out.parent / "export.json").read_text())["git_commit"] == current.revision
    assert (receipt["binding"]["model_revision"], receipt["binding"]["pleml_pin"]) == (current.revision, current.pleml_pin)
    identity = receipt["source_identity"]
    assert (identity["interpreter_revision"], identity["interpreter_sha256"], identity["pleml_pin"],
            identity["library_sha256"]) == (current.revision, current.interpreter_sha256, current.pleml_pin,
                                            current.library_sha256)
    # The prior is the Gate A experiment's, and the receipt says which interpreter read it.
    assert identity["historical_interpreter"] == {"interpreter_revision": gate_a.revision,
                                                  "interpreter_sha256": gate_a.interpreter_sha256,
                                                  "pleml_pin": gate_a.pleml_pin}
    assert identity["historical_export_revision"] == gate_a.revision
    assert receipt["differences"] == []
    assert {case["case"]: (case["status"], case["inadequate_concepts"]) for case in receipt["cases"]} == GATE_A_CASES
    assert receipt["historical"] is False and receipt["fresh_serialization"] is True and receipt["qualified"] is False


def test_the_historical_replay_runs_the_gate_a_experiment_on_its_own_export(tmp_path, monkeypatch):
    r, args, gate_a, current, seen = _offline_runner(tmp_path, monkeypatch)
    replay = SimpleNamespace(out=tmp_path / "replay/historical-replay.json", experiment=args.historical_experiment,
                             historical_experiment=None, historical_export=args.historical_export,
                             api_url=None, expected_executor=None)
    receipt = r.run(replay)
    assert seen == {}, "the historical replay serializes nothing and reaches no API"
    identity = receipt["source_identity"]
    assert (identity["interpreter_revision"], identity["pleml_pin"]) == (gate_a.revision, gate_a.pleml_pin)
    # The historical-replay receipt keeps the shape of run 38780181818.
    assert set(identity) == {"current_lock_sha256", "executor_revision", "executor_source_dirty", "fixture_sha256",
                             "historical_export_revision", "historical_export_sha256", "interpreter_revision",
                             "interpreter_sha256", "library_sha256", "pleml_pin"}
    assert receipt["historical"] is True and receipt["fresh_serialization"] is False
    assert receipt["differences"] == []
    assert {case["case"]: (case["status"], case["inadequate_concepts"]) for case in receipt["cases"]} == GATE_A_CASES


def test_the_fresh_arm_refuses_when_the_gate_a_checkout_moves_during_the_run(tmp_path, monkeypatch):
    r, args, _, _, _ = _offline_runner(tmp_path, monkeypatch, move_prior=True)
    with pytest.raises(ValueError, match="source differs from recorded Git object: tools/pleml_gate_a.py"):
        r.run(args)
    assert not args.out.exists()


@pytest.mark.parametrize("experiment, historical_experiment", [
    ("historical_experiment", "experiment"), ("historical_experiment", "historical_experiment"),
    ("experiment", "experiment")])
def test_the_fresh_arm_refuses_swapped_or_doubled_experiments(tmp_path, monkeypatch, experiment, historical_experiment):
    r, args, _, _, _ = _offline_runner(tmp_path, monkeypatch)
    swapped = SimpleNamespace(**{**vars(args), "experiment": getattr(args, experiment),
                                 "historical_experiment": getattr(args, historical_experiment)})
    with pytest.raises(ValueError, match="not the frozen reviewed revision|requires the Gate A interpreter"):
        r.run(swapped)
    assert not args.out.exists()
