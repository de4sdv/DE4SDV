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
    # The executor, the current experiment's interpreter and fixture (scoped
    # probes, fresh serialization) and the Gate A experiment (historical
    # replay, prior). PLEML itself comes from the fenced Sysand lock, so the
    # current experiment is checked out without its PLEML submodule.
    assert len(checkouts) == 3
    executor, experiment, gate_a = checkouts
    assert experiment["with"]["ref"] == "69bbe093c179f2121274b9f604c7d6a10de19e77" == runner().CURRENT.revision
    assert gate_a["with"]["ref"] == "6a99626b4af7cd01108f27dac88bf5b55bba207a" == runner().GATE_A.revision
    assert experiment["with"]["path"] == "_ple-experiment" and gate_a["with"]["path"] == "_ple-gate-a"
    assert "submodules" not in experiment["with"]
    assert gate_a["with"]["submodules"] == "recursive"
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


# -- PLEML re-qualification: the experiment identities ------------------------------------
#
# The historical replay (PLE-R) and the prior of the fresh arm stay on the
# Gate A experiment; the scoped probes, the fresh serialization and the scope
# alignment run on the experiment at PLEML 1.1.0, a reviewed child of the one
# at PLEML 1.0.0. These tests read committed data and Git objects only (CI
# fetches the full history and the tags).

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
#: The reviewed change of the experiment at PLEML 1.1.0 against the one at 1.0.0.
REVIEWED_PATHS_1_1_0 = {
    ".github/workflows/privileged-pleml-gate-a.yml", "docs/spikes/pleml-gate-a/README.md",
    "docs/spikes/pleml-gate-a/pleml_gate_a_fixture.sysml", "external/pleml",
    "tests/test_pleml_adapter_rule_api.py", "tests/test_pleml_api_observability.py",
    "tests/test_pleml_group_semantics.py", "tools/pleml_gate_a.py",
}
#: The fixture's two constraint usages, from the PLEML 1.0 form to the 1.1 form.
REVIEWED_FIXTURE_CHANGE_1_1_0 = (
    ["                    in #feature occurrence :>> excluded = (androidSDV);",
     "                    in #feature occurrence :>> requiredFeatures = (diagnostics);"],
    ["                    in occurrence constrainedFeatures = new FeatureOperand(that, androidSDV);",
     "                    in occurrence constrainedFeatures = new FeatureOperand(that, diagnostics);"],
)
#: The kernel feature ``that`` as the serializer names it: the target of the PLEML library's own
#: ``featureConfiguration = that`` reference in the pruning records of the committed Gate A export.
KERNEL_THAT = "dbd75b49-0e57-5cf9-ba35-9f8843b1e657"
#: The verdicts of the five Gate A configurations.
GATE_A_STATUSES = {
    "adapter-required-exactly-one": "derivation-complete", "valid-no-adapter": "derivation-complete",
    "configuration-invalid": "configuration-invalid", "derivation-incomplete": "derivation-incomplete",
    "derivation-ambiguous": "derivation-ambiguous"}


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


def _pleml_1_1_shape(elements, sources, *, operand_a=None, operand_a_target=KERNEL_THAT,
                     look_alike_feature_operand=False, no_owner=None, no_owning_relationship=None):
    """The committed Gate A export with its two constraint usages in the PLEML 1.1 parameter shape.

    Test scaffolding, never a PLEML 1.1.0 serialization or evidence. Each owned
    ``excluded`` or ``requiredFeatures`` role becomes ``in occurrence
    constrainedFeatures = new FeatureOperand(that, <feature>);`` in the shape of
    the official minimal serializer (licensed scratch check run 39151970312),
    and the library gains the ``FeatureOperand`` definition the constructor
    instantiates. Operand A refers to the kernel ``that``, which the bundle
    leaves out: its reference has no target and one pruning record. For the XOR
    usage, ``operand_a`` names a fixture feature instead and ``operand_a_target``
    another left-out target; ``look_alike_feature_operand`` makes the
    constructors instantiate a fixture definition named ``FeatureOperand``.
    ``no_owner`` and ``no_owning_relationship`` name a usage whose owning
    membership loses its owner, or which loses its owning relationship.
    Returns the elements, their source labels and the pruning records.
    """
    import copy

    by_id = {element["@id"]: copy.deepcopy(element) for element in elements}
    labels = dict(sources)

    def owned(owner, kind, member_name=None):
        found = [e for e in by_id.values() if e["@type"] == kind and e.get("owningRelatedElement") == {"@id": owner}
                 and (member_name is None or e.get("memberName") == member_name)]
        assert len(found) == 1, (owner, kind, member_name)
        return found[0]

    def drop(root):
        element = by_id.pop(root)
        del labels[root]
        for item in element.get("ownedRelationship", []) + element.get("ownedRelatedElement", []):
            if item["@id"] in by_id:
                drop(item["@id"])

    def add(identifier, kind, owner=None, member=None, **properties):
        by_id[identifier] = {"@id": identifier, "@type": kind, **properties}
        labels[identifier] = FIXTURE
        if owner is not None:
            by_id[identifier]["owningRelatedElement"] = {"@id": owner}
        if member is not None:
            by_id[identifier]["memberElement"] = {"@id": member}
        return identifier

    def fixture_feature(name):
        found = [i for i, e in by_id.items() if labels[i] == FIXTURE and e.get("declaredName") == name]
        assert len(found) == 1, name
        return found[0]

    library = next(label for label in labels.values() if label.endswith("PLEML.sysml"))
    add("pleml-1.1:FeatureOperand", "OccurrenceDefinition", declaredName="FeatureOperand")
    labels["pleml-1.1:FeatureOperand"] = library
    instantiated = "pleml-1.1:FeatureOperand"
    if look_alike_feature_operand:
        instantiated = add("pleml-1.1:look-alike-FeatureOperand", "OccurrenceDefinition", declaredName="FeatureOperand")
    records = []
    for usage_name, role in (("xorFeatures", "excluded"), ("requiresFeatures", "requiredFeatures")):
        xor = usage_name == "xorFeatures"
        premise = fixture_feature(operand_a) if xor and operand_a is not None else None
        usage = next(i for i, e in by_id.items() if labels[i] == FIXTURE and e["@type"] == "AssertConstraintUsage"
                     and (e.get("declaredName") or e.get("name")) == usage_name)
        legacy = owned(usage, "FeatureMembership", role)
        value = owned(legacy["memberElement"]["@id"], "FeatureValue")
        target = owned(value["memberElement"]["@id"], "Membership")["memberElement"]["@id"]
        drop(legacy["@id"])
        prefix = f"pleml-1.1:{usage_name}"
        parameter = add(f"{prefix}:constrainedFeatures", "OccurrenceUsage", declaredName="constrainedFeatures", direction="in")
        by_id[usage]["ownedRelationship"] = [item for item in by_id[usage]["ownedRelationship"] if item["@id"] in by_id] + [
            {"@id": add(f"{prefix}:parameter", "FeatureMembership", usage, parameter, memberName="constrainedFeatures")}]
        constructor = add(f"{prefix}:constructor", "ConstructorExpression")
        add(f"{prefix}:value", "FeatureValue", parameter, constructor)
        add(f"{prefix}:instantiated", "Membership", constructor, instantiated)
        result = add(f"{prefix}:result", "Feature", direction="out")
        add(f"{prefix}:return", "ReturnParameterMembership", constructor, result)
        for operand, referent in (("operandA", premise), ("operandB", target)):
            argument = add(f"{prefix}:{operand}", "Feature", name=operand, direction="in")
            add(f"{prefix}:{operand}:membership", "ParameterMembership", result, argument, memberName=operand)
            reference = add(f"{prefix}:{operand}:reference", "FeatureReferenceExpression")
            add(f"{prefix}:{operand}:value", "FeatureValue", argument, reference)
            membership = add(f"{prefix}:{operand}:target", "Membership", reference, referent)
            if referent is None:
                records.append({"source_element_id": membership, "property_path": "memberElement",
                                "target_id": operand_a_target if xor else KERNEL_THAT,
                                "uri": "Kernel%20Libraries/Kernel%20Semantic%20Library/Base.kerml"})
        if usage_name == no_owner:
            by_id[by_id[usage]["owningRelationship"]["@id"]].pop("owningRelatedElement")
        if usage_name == no_owning_relationship:
            by_id[usage].pop("owningRelationship")
    return list(by_id.values()), labels, records


def test_the_current_identity_is_pleml_1_1_1_from_the_fenced_lock_and_the_scope_alignment_identity():
    from de4sdv.semantic import ple_scope_alignment as alignment
    from de4sdv.semantic import pleml_package

    r = runner()
    assert r.CURRENT == r.PLEML_1_1_1 not in (r.GATE_A, r.PLEML_1_0_0, r.PLEML_1_1_0)
    assert (r.FROZEN_REVISION, r.PLEML_PIN, r.LIBRARY) == (r.CURRENT.revision, r.CURRENT.pleml_pin, r.CURRENT.library)
    # The library is the byte-checked Sysand package; the pin is its release tag commit.
    assert r.CURRENT.provision == "sysand" and r.PLEML_1_1_0.provision == "submodule"
    assert r.CURRENT.pleml_pin == pleml_package.RELEASE.tag_commit == "b694648cce4b96126eda2de3eb881c54397ae035"
    assert r.CURRENT.library_sha256 == pleml_package.RELEASE.library.sha256
    assert r.PLEML_LIBRARY == ROOT / pleml_package.LIBRARY_PATH
    # Everything else is the experiment at 1.1.0: its interpreter, its fixture and its library label.
    assert r.CURRENT._replace(pleml_pin=r.PLEML_1_1_0.pleml_pin, library_sha256=r.PLEML_1_1_0.library_sha256,
                              provision="submodule") == r.PLEML_1_1_0
    assert r.CURRENT.revision == "69bbe093c179f2121274b9f604c7d6a10de19e77"
    assert r.CURRENT.library == "external/pleml/PLEML.sysml"
    # PLE-S reads the same experiment: one current identity, not two.
    assert (alignment.FROZEN_REVISION, alignment.FROZEN_TAG, alignment.FROZEN_INTERPRETER_SHA256,
            alignment.PLEML_PIN, alignment.LIBRARY_SOURCE) == (
        r.CURRENT.revision, r.CURRENT.tag, r.CURRENT.interpreter_sha256, r.CURRENT.pleml_pin, r.CURRENT.library)
    # The fresh arm verifies the fenced lock and the record it is checked against at the executor revision.
    assert {"de4sdv/semantic/pleml_package.py", (pleml_package.PROJECT / "sysand-lock.toml").as_posix(),
            (pleml_package.PROJECT / ".project.json").as_posix()} <= set(r.EXECUTOR_INPUTS)


def test_the_gate_a_identity_is_the_retained_baseline_identity(tmp_path):
    gate_a = runner().GATE_A
    manifest = json.loads((BASELINE / "manifest.json").read_text())
    _, raw = _committed_export(tmp_path)
    assert manifest["frozen_revision"] == raw["git_commit"] == raw["gate_a_identity"]["git_commit"] == gate_a.revision
    assert raw["gate_a_identity"]["pleml_commit"] == gate_a.pleml_pin == "5f8ab8560219dc24d8ec7ec90d6f0a145896ef8e"
    assert [(entry["path"], entry["sha256"]) for entry in raw["source_manifest"]] == [
        (FIXTURE, gate_a.fixture_sha256), (gate_a.library, gate_a.library_sha256)]


@pytest.mark.parametrize("name", ["GATE_A", "PLEML_1_0_0", "PLEML_1_1_0"])
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


def test_the_pleml_1_1_0_experiment_is_the_reviewed_delta_of_pleml_1_0_0():
    r = runner()
    parent, current = r.PLEML_1_0_0, r.PLEML_1_1_0
    assert _git_object("rev-parse", f"{current.revision}^").decode().strip() == parent.revision
    assert set(_git_object("diff", "--name-only", parent.revision, current.revision).decode().split()) == REVIEWED_PATHS_1_1_0

    def change(path):
        diff = _git_object("diff", "--unified=0", parent.revision, current.revision, "--", path).decode().splitlines()
        return ([line[1:] for line in diff if line.startswith("-") and not line.startswith("---")],
                [line[1:] for line in diff if line.startswith("+") and not line.startswith("+++")])

    assert change(FIXTURE) == REVIEWED_FIXTURE_CHANGE_1_1_0
    # The pin moves, the reader of the 1.0 excluded role goes and one reader of
    # both operands comes in; the source paths and the constraint chain stay.
    removed, added = change("tools/pleml_gate_a.py")
    assert (len(removed), len(added)) == (54, 109)
    assert 'PLEML_PIN = "071a69fdb2ecfa154809913938dfe9ebdf37701b"' in removed
    assert 'PLEML_PIN = "76e2be934453d77c4094141400b8ad8eb90a54a2"' in added
    assert "    def _role_target(owner_id: str, role_name: str) -> str:" in removed
    assert "def _excluded_feature(" in added
    assert not [line for line in removed + added if "PLEML_SOURCE" in line or "def _constraint_chain" in line]


def test_the_pleml_1_1_0_interpreter_reads_the_1_1_shape_as_gate_a_reads_its_export(tmp_path):
    from de4sdv.semantic.ple_qualification import build_case_report

    r = runner()
    gate_a, current = _interpreter_at(r.GATE_A, tmp_path), _interpreter_at(r.PLEML_1_1_0, tmp_path)
    _, raw = _committed_export(tmp_path)
    elements, sources = _elements_and_sources(raw)
    prior = gate_a.build_observability_matrix(elements, sources)
    moved = _moved(sources, r.GATE_A.library, r.PLEML_1_1_0.library)
    shaped, shaped_sources, _ = _pleml_1_1_shape(elements, moved)
    report = build_case_report(current.build_observability_matrix(shaped, shaped_sources), prior)
    assert report["differences"] == []
    assert {case["case"]: (case["status"], case["inadequate_concepts"]) for case in report["cases"]} == GATE_A_CASES
    assert {label: value["status"] for label, value in r.observe(current, shaped)["outcomes"].items()} == GATE_A_STATUSES
    # The 1.0 form is refused: the row names the missing parameter and the verdict refuses.
    flipped = _flipped(current.build_observability_matrix(elements, moved), _adequacy(prior))
    assert list(flipped) == ["Incompatibility constraint"]
    assert "constrainedFeatures" in flipped["Incompatibility constraint"][1]
    with pytest.raises(current.UnsupportedSemanticShape, match="constrainedFeatures"):
        r.observe(current, elements)
    # Operand A must name the owner of the constraint: a foreign feature is refused.
    foreign, _, _ = _pleml_1_1_shape(elements, moved, operand_a="openpilot")
    with pytest.raises(current.UnsupportedSemanticShape, match="operand A"):
        r.observe(current, foreign)


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


@pytest.mark.parametrize("name", ["PLEML_1_0_0", "PLEML_1_1_0"])
def test_the_prior_refuses_an_interpreter_other_than_gate_a(tmp_path, name):
    r = runner()
    current = _interpreter_at(getattr(r, name), tmp_path)
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


@pytest.mark.parametrize("name", ["GATE_A", "PLEML_1_0_0", "PLEML_1_1_0"])
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


def _scratch_sysand_experiment(tmp_path, identity):
    """A scratch ``sysand`` experiment: the identity's interpreter and fixture, no submodule, and a library outside.

    Returns the checkout, the scratch identity (scratch revision and library
    digest) and the library file, laid out where the fenced lock installs it.
    """
    library = tmp_path / "fenced" / ".sysand/lib/mbse4u-pleml_1.1.1/PLEML.sysml"
    library.parent.mkdir(parents=True)
    library.write_text("library package Scratch;\n")
    experiment = tmp_path / "experiment"
    (experiment / "tools").mkdir(parents=True)
    (experiment / "tools/pleml_gate_a.py").write_bytes(_git_object("show", f"{identity.revision}:tools/pleml_gate_a.py"))
    (experiment / FIXTURE).parent.mkdir(parents=True)
    (experiment / FIXTURE).write_bytes(_git_object("show", f"{identity.revision}:{FIXTURE}"))
    _commit(tmp_path, "init", "-q", str(experiment))
    _commit(experiment, "add", ".")
    _commit(experiment, "commit", "-q", "-m", "experiment without its PLEML submodule")
    scratch = identity._replace(revision=_commit(experiment, "rev-parse", "HEAD"),
                                library_sha256=hashlib.sha256(library.read_bytes()).hexdigest())
    return experiment, scratch, library


def test_load_experiment_reads_a_sysand_library_from_outside_the_checkout(tmp_path):
    r = runner()
    experiment, identity, library = _scratch_sysand_experiment(tmp_path, r.PLEML_1_1_1)
    module, manifest, source = r.load_experiment(experiment, identity, library)
    data = library.read_bytes()
    # The manifest the interpreter's own source check would build, the library under its label.
    assert manifest == [
        {"path": FIXTURE, "authority": "fixture", "sha256": identity.fixture_sha256,
         "size": len(_git_object("show", f"{identity.revision}:{FIXTURE}"))},
        {"path": identity.library, "authority": "pinned-dependency", "sha256": identity.library_sha256,
         "size": len(data)}]
    assert module.PLEML_SOURCE.as_posix() == identity.library
    assert source == {"interpreter_revision": identity.revision, "interpreter_sha256": identity.interpreter_sha256,
                      "fixture_sha256": identity.fixture_sha256, "library_sha256": identity.library_sha256,
                      "pleml_pin": identity.pleml_pin,
                      "library_provision": {"provision": "sysand", "package": "pkg:sysand/mbse4u/pleml",
                                            "version": "1.1.1", "tag": "v1.1.1",
                                            "lock": "model-based-product-line-engineering/libraries/pleml/sysand-lock.toml"}}
    for field, value, message in (
            ("revision", "0" * 40, "not the frozen reviewed revision"),
            ("interpreter_sha256", "0" * 64, "differ from the reviewed identity"),
            ("library_sha256", "0" * 64, "differ from the reviewed identity: the PLEML library"),
            ("fixture_sha256", "0" * 64, "differ from the reviewed identity")):
        with pytest.raises(ValueError, match=message):
            r.load_experiment(experiment, identity._replace(**{field: value}), library)


def test_load_experiment_refuses_a_sysand_library_that_is_missing_or_a_symlink(tmp_path):
    r = runner()
    experiment, identity, library = _scratch_sysand_experiment(tmp_path, r.PLEML_1_1_1)
    with pytest.raises(ValueError, match="run `sysand sync` in model-based-product-line-engineering/libraries/pleml"):
        r.load_experiment(experiment, identity, tmp_path / "missing/PLEML.sysml")
    link = tmp_path / "link.sysml"
    link.symlink_to(library)
    with pytest.raises(ValueError, match="not installed as a regular file"):
        r.load_experiment(experiment, identity, link)


def test_serialize_loads_a_sysand_library_and_records_it_under_the_library_label(tmp_path, monkeypatch):
    """A synthetic serializer: the runner's document labelling only, never Syside semantics."""
    from contextlib import contextmanager

    r = runner()
    root = tmp_path / "experiment"
    (root / FIXTURE).parent.mkdir(parents=True)
    (root / FIXTURE).write_text("package Fixture;\n")
    library = tmp_path / "fenced/.sysand/lib/mbse4u-pleml_1.1.1/PLEML.sysml"
    library.parent.mkdir(parents=True)
    library.write_text("library package PLEML;\n")
    loaded = []

    class Document:
        def __init__(self, path):
            self.url, self.root_node = f"file://{path}", Path(path).stem

        @contextmanager
        def lock(self):
            yield self

    class Diagnostics:
        def contains_errors(self, **kwargs):
            return False

    def try_load_model(paths):
        loaded.extend(paths)
        return SimpleNamespace(user_docs=[Document(path) for path in paths]), Diagnostics()

    fake = SimpleNamespace(
        try_load_model=try_load_model, SerializationOptions=SimpleNamespace(minimal=lambda: None),
        json=SimpleNamespace(dumps=lambda node, options: json.dumps(
            [{"@id": f"00000000-0000-5000-8000-{abs(hash(node)) % 10**12:012d}", "@type": "Package"}])))
    real_import = r.importlib.import_module
    monkeypatch.setattr(r.importlib, "import_module", lambda name: fake if name == "syside" else real_import(name))
    monkeypatch.setattr(r.importlib.metadata, "version", lambda name: r.SERIALIZER_VERSION)
    manifest = [{"path": FIXTURE, "authority": "fixture", "sha256": "0" * 64, "size": 1},
                {"path": r.LIBRARY, "authority": "pinned-dependency", "sha256": "0" * 64, "size": 1}]
    bundle, version = r.serialize(root, manifest, "0" * 40, library)
    assert loaded == [root / FIXTURE, library] and version == r.SERIALIZER_VERSION
    assert sorted(bundle.element_sources.values()) == sorted([FIXTURE, r.LIBRARY])


def test_load_experiment_refuses_a_library_beside_the_submodule_of_a_frozen_experiment(tmp_path):
    r = runner()
    experiment, identity = _scratch_experiment(tmp_path, r.PLEML_1_1_0)
    with pytest.raises(ValueError, match="reads its PLEML library from its submodule"):
        r.load_experiment(experiment, identity, experiment / identity.library)


# -- the runner end to end, offline: both arms with scratch experiments --------------------
#
# GATE_A and CURRENT are replaced by scratch experiments that carry the real
# interpreters and fixture. Only Syside and the API are faked: the "fresh
# serialization" is the committed Gate A export with the library label moved to
# the current path and the constraint usages in the PLEML 1.1 shape
# (_pleml_1_1_shape), never a PLEML 1.1.0 serialization or evidence.
# The executor's own source verification is covered by the licensed runs; it is
# switched off here so these tests pin the experiment wiring only.


@dataclasses.dataclass(frozen=True)
class _OfflineImport:
    project_id: str
    commit_id: str
    element_count: int
    internal_reference_count: int
    content_sha256: str


def _offline_runner(tmp_path, monkeypatch, *, move_prior=False, move_library=False, keep_gate_a_label=False,
                    shape=None):
    """The runner with scratch experiments as GATE_A and CURRENT; ``keep_gate_a_label`` leaves the library label unmoved.

    CURRENT is a ``sysand`` experiment, as the real one: its library is a scratch
    file where the fenced lock installs the package, outside its checkout.
    """
    from de4sdv.sysml_api.baseline import BaselineExportBundle, build_export_bundle

    r = runner()
    gate_a_checkout, gate_a = _scratch_experiment(tmp_path / "gate-a", r.GATE_A)
    current_checkout, current, library = _scratch_sysand_experiment(tmp_path / "current", r.PLEML_1_1_1)
    monkeypatch.setattr(r, "GATE_A", gate_a)
    monkeypatch.setattr(r, "CURRENT", current)
    monkeypatch.setattr(r, "PLEML_LIBRARY", library)
    monkeypatch.setattr(r, "EXECUTOR_INPUTS", ())
    _, gate_a_manifest, _ = r.load_experiment(gate_a_checkout, gate_a)
    export_path, raw = _committed_export(tmp_path)
    raw = dict(raw, git_commit=gate_a.revision, source_manifest=gate_a_manifest,
               gate_a_identity=dict(raw["gate_a_identity"], git_commit=gate_a.revision, pleml_commit=gate_a.pleml_pin))
    export_path.write_text(json.dumps(raw))
    seen = {}

    def serialize(root, manifest, revision, library=None):
        seen.update(root=root, revision=revision, manifest=[entry["path"] for entry in manifest], library=library)
        if move_prior:  # the Gate A checkout moves while the fresh arm runs
            interpreter = gate_a_checkout / "tools/pleml_gate_a.py"
            interpreter.write_bytes(interpreter.read_bytes() + b"\n# moved during the run\n")
        if move_library:  # the installed library moves while the fresh arm runs
            library.write_bytes(library.read_bytes() + b"// moved during the run\n")
        documents = {}
        shaped, shaped_sources, records = _pleml_1_1_shape(raw["elements"], raw["element_sources"], **(shape or {}))
        for element in shaped:
            label = shaped_sources[element["@id"]]
            moved = label == gate_a.library and not keep_gate_a_label
            documents.setdefault(current.library if moved else label, []).append(element)
        bundle = build_export_bundle(git_commit=revision, source_documents=documents).to_dict()
        bundle["source_manifest"] = manifest
        # The serializer records what the bundle leaves out: the export's records and the shape's.
        bundle["external_references"] = raw["external_references"] + records + bundle["external_references"]
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
    # The current experiment is the one serialized, at its own revision, with the installed library.
    assert seen["root"] == args.experiment.resolve() and seen["revision"] == current.revision
    assert seen["manifest"] == [FIXTURE, current.library]
    assert seen["library"] == r.PLEML_LIBRARY and not seen["library"].is_relative_to(args.experiment)
    assert json.loads((args.out.parent / "export.json").read_text())["git_commit"] == current.revision
    assert (receipt["binding"]["model_revision"], receipt["binding"]["pleml_pin"]) == (current.revision, current.pleml_pin)
    identity = receipt["source_identity"]
    assert (identity["interpreter_revision"], identity["interpreter_sha256"], identity["pleml_pin"],
            identity["library_sha256"]) == (current.revision, current.interpreter_sha256, current.pleml_pin,
                                            current.library_sha256)
    assert identity["library_provision"]["provision"] == "sysand"
    # The prior is the Gate A experiment's, and the receipt says which interpreter read it.
    assert identity["historical_interpreter"] == {"interpreter_revision": gate_a.revision,
                                                  "interpreter_sha256": gate_a.interpreter_sha256,
                                                  "pleml_pin": gate_a.pleml_pin}
    assert identity["historical_export_revision"] == gate_a.revision
    assert receipt["differences"] == []
    assert {case["case"]: (case["status"], case["inadequate_concepts"]) for case in receipt["cases"]} == GATE_A_CASES
    assert receipt["historical"] is False and receipt["fresh_serialization"] is True and receipt["qualified"] is False


def test_the_fresh_arm_compares_with_the_gate_a_prior_not_with_itself(tmp_path, monkeypatch):
    """Negative control: a serialization that keeps the Gate A library label differs from the prior.

    The current interpreter reads the library at the 1.0.0 and 1.1.0 path, so on
    the Gate A label exactly the two label-bound rows turn inadequate. The differences are
    those two rows only when they are computed against the Gate A prior. The constraint
    operand check refuses this serialization first (the current library document holds
    no FeatureOperand); it is switched off for the second run, which reaches the comparison.
    """
    r, args, _, _, _ = _offline_runner(tmp_path, monkeypatch, keep_gate_a_label=True)
    with pytest.raises(ValueError, match="0 library FeatureOperand"):
        r.run(args)
    monkeypatch.setattr(r, "verify_constraint_operands", lambda bundle, values: {"count": 0, "constraints": []})
    receipt = r.run(SimpleNamespace(**{**vars(args), "out": tmp_path / "compared/receipt.json"}))
    differences = receipt["differences"]
    assert [item["concept"] for item in differences] == LABEL_BOUND_ROWS
    for item in differences:
        assert item["classification"] == "review-required"
        assert item["before"]["api_only_consumption_adequate"] is True
        assert item["after"]["api_only_consumption_adequate"] is False and "found 0" in item["after"]["exact_gap"]


def test_the_fresh_arm_checks_the_constraint_operands_by_identity(tmp_path, monkeypatch):
    """The interpreter reads the operands by shape; the runner checks them by identity."""
    _, raw = _committed_export(tmp_path)
    library_that = [r for r in raw["external_references"] if r["target_id"] == KERNEL_THAT]
    assert len(library_that) == 2 and all(r["uri"].endswith("Kernel%20Semantic%20Library/Base.kerml") for r in library_that)
    r, args, _, _, _ = _offline_runner(tmp_path, monkeypatch, shape={"operand_a": "apollo"})
    operands = r.run(args)["constraint_operands"]
    assert operands["count"] == 2
    assert [(item["name"], item["operand_a"]) for item in operands["constraints"]] == [
        ("requiresFeatures", "that"), ("xorFeatures", "owner")]
    assert {item["feature_operand"] for item in operands["constraints"]} == {"pleml-1.1:FeatureOperand"}


def test_the_operand_check_records_an_empty_pass_as_a_count_of_zero(tmp_path):
    """No constraint usage with a constrainedFeatures parameter is legitimate; the receipt shows it as 0."""
    from de4sdv.sysml_api.baseline import BaselineExportBundle, build_export_bundle

    r = runner()
    _, raw = _committed_export(tmp_path)
    elements, sources = _elements_and_sources(raw)
    shaped, labels, records = _pleml_1_1_shape(elements, _moved(sources, r.GATE_A.library, r.CURRENT.library))
    for element in shaped:
        if element.get("memberName") == "constrainedFeatures":
            element["memberName"] = "renamedParameter"
    documents = {}
    for element in shaped:
        documents.setdefault(labels[element["@id"]], []).append(element)
    bundle = build_export_bundle(git_commit="0" * 40, source_documents=documents).to_dict()
    bundle = BaselineExportBundle.from_dict(dict(bundle, external_references=raw["external_references"] + records))
    assert r.verify_constraint_operands(bundle, list(bundle.elements.values())) == {"count": 0, "constraints": []}


@pytest.mark.parametrize("shape, message", [
    ({"operand_a_target": "00000000-0000-5000-8000-0000000000aa"}, "operand A"),
    ({"operand_a": "openpilot"}, "operand A"),
    ({"look_alike_feature_operand": True}, "FeatureOperand"),
    ({"no_owner": "requiresFeatures"}, "constraint operand check: .* has no owner"),
    ({"no_owning_relationship": "requiresFeatures"}, "constraint operand check: .* has no owning relationship"),
], ids=["left-out-but-not-that", "foreign-feature", "look-alike-FeatureOperand", "ownerless-usage", "malformed-usage"])
def test_the_fresh_arm_refuses_operands_outside_the_library_identities(tmp_path, monkeypatch, shape, message):
    r, args, _, _, _ = _offline_runner(tmp_path, monkeypatch, shape=shape)
    with pytest.raises(ValueError, match=message):
        r.run(args)
    assert not args.out.exists()


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


def test_the_fresh_arm_refuses_when_the_installed_library_moves_during_the_run(tmp_path, monkeypatch):
    r, args, _, _, _ = _offline_runner(tmp_path, monkeypatch, move_library=True)
    with pytest.raises(ValueError, match="differ from the reviewed identity: the PLEML library"):
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
