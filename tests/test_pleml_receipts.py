"""Receipts, offline replay and the parity primitives of the PLEML evaluation (plan step S2).

The parity rows run the unchanged configurator on probes generated in a
temporary directory (never committed) and set each beside the evaluation of
the same statement in the synthetic platform line, so the reason map and the
row classes are shown against today's configurator.
"""
from __future__ import annotations

import ast
import copy
import dataclasses
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from de4sdv.semantic import pleml_configuration as evaluator
from de4sdv.semantic import pleml_receipts as receipts
from de4sdv.semantic.kernel_contract import KernelContract
from de4sdv.sysml_api.baseline import BaselineExportBundle, build_export_bundle
from scripts import run_pleml_configuration_evaluation as cli
from tests.pleml_graph_fixtures import (CONFIGURATIONS as CONFIGURATION_DIRECTORY, GOVERNED_SETS, LIBRARY, MODEL,
                                        SCOPE, PlatformLine, PlemlGraph, synthetic_contract)

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = Path("model-based-product-line-engineering/feature-models/sdv_product_line.yaml")
CONFIGURATIONS = ROOT / "model-based-product-line-engineering/feature-configurations"


ENVIRONMENTS = "model-based-product-line-engineering/feature-models/synthetic_environments.sysml"
ENVIRONMENT_CONFIGURATION = f"{CONFIGURATION_DIRECTORY}/synthetic_candidate.sysml"
MEMBER, PAIR = f"{CONFIGURATION_DIRECTORY}/synthetic_member.sysml", f"{CONFIGURATION_DIRECTORY}/synthetic_pair.sysml"
SERIALIZER = {"name": "syside", "version": "0.10.3", "options": "production export", "executor_revision": "e" * 40}
ELEMENTS = "pleml-feature-models.elements.json.xz"
PLATFORM_RECEIPT = "synthetic_feature_model.receipt.json"
#: The stand-in bytes of every document of a synthetic bundle, the library among them.
SYNTHETIC_LIBRARY = {"package": "pkg:sysand/mbse4u/pleml", "version": "1.1.1", "tag_commit": "b" * 40,
                     "path": evaluator.LIBRARY_SOURCE,
                     "sha256": receipts.sha256(f"synthetic {evaluator.LIBRARY_SOURCE}\n".encode())}


def synthetic_scope_validator(elements, sources):
    """The production scope validator's record, read from the synthetic scope document by its element names."""
    named = {element.get("declaredName"): element["@id"] for element in elements
             if sources.get(element["@id"]) == SCOPE and element.get("@type") == "PartUsage"}
    record = {"schema": evaluator.SCOPE_SCHEMA, "scope_source": SCOPE}
    for key, names in GOVERNED_SETS.items():
        members = {name: named[name] for name in names}
        if key == "alternatives":
            record["vehicle_platform_integration_mode"] = {"alternatives": members}
        else:
            record[key] = members
    return record


@pytest.fixture(autouse=True)
def _synthetic_authorities(monkeypatch):
    """The synthetic stand-ins of what a receipt binds: the kernel contract, the governed scope, the library."""
    monkeypatch.setattr(receipts, "model_contract", lambda root=ROOT: synthetic_contract())
    monkeypatch.setattr(receipts, "SCOPE_SOURCE", SCOPE)
    monkeypatch.setattr(receipts, "validate_scope_elements", synthetic_scope_validator)
    monkeypatch.setattr(receipts, "pinned_library", lambda: dict(SYNTHETIC_LIBRARY))


def test_the_kernel_constants_match_the_model_built_contract():
    contract = KernelContract.from_layers(ROOT)
    names = [name for _, name, _ in evaluator.KERNEL.definitions().values()]
    if not any(name in contract.classes for name in names):
        pytest.skip("the S2k kernel classes are not on this base yet (#402)")
    for name in names:
        mapping = contract.mapping(name)
        assert (mapping.file, mapping.declaration) == (evaluator.KERNEL_SOURCE, f"metadata def {name}")


def test_the_library_label_is_the_installed_library_of_the_production_lock():
    from de4sdv.semantic import pleml_package

    assert evaluator.LIBRARY_SOURCE == pleml_package.LIBRARY_PATH.as_posix()
    assert Path(evaluator.LIBRARY_SOURCE).is_relative_to(pleml_package.PROJECT / ".sysand")


def test_a_receipt_binds_the_pinned_release_of_the_production_lock(monkeypatch):
    from de4sdv.semantic import pleml_package

    monkeypatch.undo()
    assert receipts.pinned_library() == {
        "package": pleml_package.PACKAGE, "version": pleml_package.RELEASE.version,
        "tag_commit": pleml_package.RELEASE.tag_commit, "path": evaluator.LIBRARY_SOURCE,
        "sha256": pleml_package.RELEASE.library.sha256}


# -- the synthetic authority bundle ----------------------------------------------------------------


def role(label: str) -> str:
    """The manifest role the authority job gives a document."""
    if label in (MODEL, ENVIRONMENTS):
        return "pleml-feature-model"
    return "pleml-feature-configuration" if label.startswith(CONFIGURATION_DIRECTORY) else "reviewed"


def platform_line(*, governed: bool = True) -> PlatformLine:
    line = PlatformLine(PlemlGraph(library=evaluator.LIBRARY_SOURCE), governed=governed)
    line.configure("member", "autoware", "noMiddleware", "linux", "noHypervisor", projection_name="Member",
                   description="The standalone member.")
    line.configure("pair", "openpilot", "androidSDV", "linux", "noHypervisor")
    return line


def two_family_graph(*, governed: bool = True, environment_document: str = ENVIRONMENT_CONFIGURATION) -> PlemlGraph:
    """The platform line and an environment family, each with its own model and configuration documents."""
    graph = platform_line(governed=governed).graph
    graph.model_document(ENVIRONMENTS, "SyntheticEnvironments")
    tree = graph.tree_definition("EnvironmentTree")
    compute = graph.feature(tree, "compute", (1, 1))
    board = graph.feature(tree, "board", (0, 1), subsets=compute)
    model = graph.feature_model("EnvironmentFeatureModel", tree_definition=tree)
    graph.select(graph.configuration(model, "candidate", tree, document=environment_document), board)
    return graph


def with_resource_uris(documents: dict[str, list], prefix: str) -> dict[str, list]:
    """The documents as the serializer writes them: a cross-document reference carries ``@uri``.

    The resource path of the URI depends on the runner's checkout and on where
    the library is provisioned; ``prefix`` stands for that environment.
    """
    where = {element["@id"]: label for label, values in documents.items() for element in values}
    outside = "_syside/sysml.library/Kernel%20Libraries/Kernel%20Semantic%20Library/Base.kerml"

    def visit(value, document):
        if isinstance(value, dict):
            if "@id" in value and "@type" not in value:
                target = where.get(value["@id"], outside)
                return value if target == document else {**value, "@uri": f"{prefix}{target}#{value['@id']}"}
            return {key: visit(item, document) for key, item in value.items()}
        if isinstance(value, list):
            return [visit(item, document) for item in value]
        return value

    return {label: [visit(element, label) for element in values] for label, values in documents.items()}


def bundle_of(graph: PlemlGraph, root: Path, *, uri_prefix: str | None = None,
              git_commit: str = "a" * 40) -> BaselineExportBundle:
    """The graph as the authority job's export bundle, its documents written under ``root``."""
    elements, sources = graph.build()
    documents: dict[str, list] = {}
    for element in elements:
        documents.setdefault(sources[element["@id"]], []).append(element)
    if uri_prefix is not None:
        documents = with_resource_uris(documents, uri_prefix)
    bundle = build_export_bundle(git_commit=git_commit, source_documents=documents)
    manifest = []
    for label in sorted(documents):
        data = f"synthetic {label}\n".encode()
        (root / label).parent.mkdir(parents=True, exist_ok=True)
        (root / label).write_bytes(data)
        manifest.append({"path": label, "authority": role(label), "sha256": receipts.sha256(data),
                         "size": len(data)})
    return dataclasses.replace(bundle, source_manifest=tuple(manifest))


def write_receipt(tmp_path: Path, graph: PlemlGraph | None = None) -> Path:
    """The platform line's receipt, written by the entry point from a synthetic bundle; sources under tmp_path."""
    graph = graph or platform_line().graph
    result = cli.write_receipts(bundle_of(graph, tmp_path), tmp_path / "receipts", serializer=SERIALIZER,
                                root=tmp_path)
    return next(path for path in result["receipts"] if path.name == PLATFORM_RECEIPT)


def with_catalogue(root: Path) -> None:
    """Today's catalogue and configurator under ``root``, the YAML with the platform model's file stem."""
    for relative in (Path("tools/configure_variant.py"),):
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).write_bytes((ROOT / relative).read_bytes())
    (root / MODEL).parent.mkdir(parents=True, exist_ok=True)
    (root / MODEL).with_suffix(".yaml").write_bytes((ROOT / CATALOGUE).read_bytes())


# -- committed elements and receipts (R13) ------------------------------------------------------


def test_the_elements_file_is_deterministic_and_round_trips(tmp_path):
    payload = receipts.payload_from_bundle(bundle_of(platform_line().graph, tmp_path), serializer=SERIALIZER)
    first = receipts.write_elements(tmp_path / "a.xz", payload)
    second = receipts.write_elements(tmp_path / "b.xz", copy.deepcopy(payload))
    assert first == second
    assert receipts.read_elements(tmp_path / "a.xz") == payload
    assert "executor_revision" not in json.dumps(payload) and "bundle_git_commit" not in json.dumps(payload)


def test_a_fresh_receipt_replays_offline(tmp_path):
    receipt = receipts.replay(write_receipt(tmp_path), tmp_path)
    configurations = receipt["evaluation"]["feature_models"][0]["configurations"]
    assert {item["configuration"]: (item["valid"], item["admission"]["admitted"]) for item in configurations} == {
        "member": (True, True), "pair": (False, False)}
    assert receipt["qualified"] is False and receipt["native_expression_executed"] is False
    assert receipt["provenance"] == {"executor_revision": "e" * 40, "bundle_git_commit": "a" * 40}
    assert receipt["library"] == SYNTHETIC_LIBRARY


def test_a_receipt_with_an_edited_verdict_does_not_reproduce(tmp_path):
    path = write_receipt(tmp_path)
    receipt = json.loads(path.read_text())
    receipt["evaluation"]["feature_models"][0]["configurations"][1]["valid"] = True
    path.write_text(json.dumps(receipt))
    with pytest.raises(receipts.StaleReceipt, match="does not reproduce"):
        receipts.replay(path, tmp_path)


def test_edited_elements_are_stale_by_digest(tmp_path):
    path = write_receipt(tmp_path)
    payload = receipts.read_elements(path.parent / ELEMENTS)
    payload["elements"] = payload["elements"][:-1]
    receipts.write_elements(path.parent / ELEMENTS, payload)
    with pytest.raises(receipts.StaleReceipt, match="differ from the receipt's digest"):
        receipts.replay(path, tmp_path)


def test_an_edit_that_changes_no_verdict_still_fails_the_replay(tmp_path):
    """The elements are bound by digest, so even a verdict-neutral edit (a doc body) is refused (R9)."""
    path = write_receipt(tmp_path)
    payload = receipts.read_elements(path.parent / ELEMENTS)
    documentation = next(item for item in payload["elements"] if item["@type"] == "Documentation")
    documentation["body"] = "An edited description."
    receipts.write_elements(path.parent / ELEMENTS, payload)
    with pytest.raises(receipts.StaleReceipt, match="differ from the receipt's digest"):
        receipts.replay(path, tmp_path)


def test_a_changed_model_source_makes_the_receipt_stale(tmp_path):
    path = write_receipt(tmp_path)
    (tmp_path / MODEL).write_text("edited\n")
    with pytest.raises(receipts.StaleReceipt, match="changed after the serialization"):
        receipts.replay(path, tmp_path)
    (tmp_path / MODEL).unlink()
    with pytest.raises(receipts.StaleReceipt, match="is missing"):
        receipts.replay(path, tmp_path)


def test_a_receipt_without_its_pinned_library_is_stale(tmp_path):
    """The library is never exempt: removed, the receipt refuses to replay (R4)."""
    path = write_receipt(tmp_path)
    (tmp_path / evaluator.LIBRARY_SOURCE).unlink()
    with pytest.raises(receipts.StaleReceipt, match=r"the pinned PLEML library .*PLEML.sysml is missing; run sysand "
                                                    "sync at the repository root"):
        receipts.replay(path, tmp_path)


def test_a_receipt_of_another_pin_is_stale(tmp_path, monkeypatch):
    """A re-pin of the pinned package makes every receipt stale, whatever the installed files hold (R4)."""
    path = write_receipt(tmp_path)
    monkeypatch.setattr(receipts, "pinned_library", lambda: {**SYNTHETIC_LIBRARY, "version": "1.1.2",
                                                             "sha256": "c" * 64})
    with pytest.raises(receipts.StaleReceipt, match="the receipt binds PLEML 1.1.1 at .*, and the production lock "
                                                    "pins 1.1.2"):
        receipts.replay(path, tmp_path)


def test_a_bundle_with_another_library_than_the_pinned_one_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(receipts, "pinned_library", lambda: {**SYNTHETIC_LIBRARY, "sha256": "c" * 64})
    with pytest.raises(ValueError, match="the bundle's PLEML library is not the pinned 1.1.1"):
        receipts.payload_from_bundle(bundle_of(platform_line().graph, tmp_path), serializer=SERIALIZER)


def neutral_change(module: str) -> dict:
    """The code identity after a comment-only change to ``module``: other bytes, the same behaviour."""
    modules = dict(receipts.evaluator_identity()["modules"])
    modules[module] = receipts.sha256((ROOT / module).read_bytes() + b"\n# a comment-only change\n")
    return {"modules": modules, "sha256": receipts.sha256(receipts.canonical(modules))}


def changed_evaluation(monkeypatch) -> None:
    """An evaluator change that changes the output: every evaluation reports another binding-time scope."""
    original = evaluator.evaluate

    def changed(*arguments, **options):
        return {**original(*arguments, **options), "binding_time_scope": "Production"}

    monkeypatch.setattr(evaluator, "evaluate", changed)


def test_a_neutral_code_change_replays_green(tmp_path, monkeypatch, capsys):
    """Reproduction decides; the code record is provenance (R14), and it holds the PLEML-owned code only (R16)."""
    path = write_receipt(tmp_path)
    assert "de4sdv/sysml_api/baseline.py" not in receipts.EVALUATOR_MODULES  # a comment there changes nothing
    assert receipts.replay_committed(path.parent, tmp_path) == []
    identity = neutral_change("de4sdv/semantic/pleml_configuration.py")
    monkeypatch.setattr(receipts, "evaluator_identity", lambda: identity)
    assert receipts.replay_committed(path.parent, tmp_path) == []
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    capsys.readouterr()
    assert cli.main(["replay", str(path)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["failures"] == [] and output["advisories"] == [
        f"{path}: evaluated by other code (changed: de4sdv/semantic/pleml_configuration.py); the evaluation and "
        "the shadow reproduce, so the receipt holds"]


def test_an_evaluation_change_fails_the_replay_until_a_refresh(tmp_path, monkeypatch):
    path = write_receipt(tmp_path)
    changed_evaluation(monkeypatch)
    assert receipts.replay_committed(path.parent, tmp_path) == [
        f"{path}: the committed evaluation does not reproduce from the committed elements"]
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    assert cli.main(["refresh", *(str(item) for item in sorted(path.parent.glob("*.receipt.json")))]) == 0
    assert receipts.replay_committed(path.parent, tmp_path) == []
    refreshed = json.loads(path.read_text())
    assert refreshed["evaluation"]["binding_time_scope"] == "Production"
    assert refreshed["provenance"] == {"executor_revision": "e" * 40, "bundle_git_commit": "a" * 40}


def test_a_shadow_change_fails_the_replay(tmp_path, monkeypatch):
    """A configurator change that changes the shadow fails as the shadow not reproducing."""
    root = tmp_path / "tree"
    with_catalogue(root)
    result = cli.write_receipts(bundle_of(two_family_graph(), root), tmp_path / "out", serializer=SERIALIZER,
                                root=root)
    assert receipts.replay_committed(tmp_path / "out", root) == []
    monkeypatch.setattr(cli.Catalogue, "paths", lambda self: {})
    failures = receipts.replay_committed(tmp_path / "out", root)
    assert failures == [f"{tmp_path / 'out' / PLATFORM_RECEIPT}: the shadow checks of the receipt do not reproduce"]
    assert result["failures"] == []


def test_the_replay_function_reports_failures_as_a_list(tmp_path, monkeypatch):
    """``replay_committed`` is the authority job's replay: an empty list when every receipt holds."""
    path = write_receipt(tmp_path)
    assert receipts.replay_committed(path.parent, tmp_path) == []
    assert receipts.replay_committed(tmp_path / "missing", tmp_path) == [f"{tmp_path / 'missing'}: no committed receipt"]
    receipt = json.loads(path.read_text())
    receipt["evaluation"]["feature_models"][0]["configurations"][0]["valid"] = False
    path.write_text(json.dumps(receipt))
    assert receipts.replay_committed(path.parent, tmp_path) == [
        f"{path}: the committed evaluation does not reproduce from the committed elements"]
    monkeypatch.setattr(receipts, "pinned_library", lambda: {**SYNTHETIC_LIBRARY, "version": "1.1.2",
                                                             "sha256": "c" * 64})
    (failure,) = receipts.replay_committed(path.parent, tmp_path)
    assert failure.startswith(f"{path}: the receipt binds PLEML 1.1.1") and "the production lock pins 1.1.2" in failure


def test_the_code_identity_records_the_pleml_code_an_evaluation_imports():
    """The provenance record lists the PLEML-owned modules an evaluation, its CLI and the shadow import.

    Shared production modules stay outside it, so an unrelated change to one of them, even a new import,
    never touches the record or this test (R16).
    """
    probe = (
        "import sys\n"
        "from pathlib import Path\n"
        f"ROOT = Path({str(ROOT)!r})\n"
        "sys.path.insert(0, str(ROOT))\n"
        "from scripts import run_pleml_configuration_evaluation as cli\n"
        "from de4sdv.semantic import pleml_configuration as evaluator, pleml_receipts as receipts\n"
        "evaluator.kernel_bindings(receipts.model_contract(ROOT), [], {})\n"
        "cli.load_configurator(ROOT)\n"
        "print('\\n'.join(sorted({Path(module.__file__).resolve().relative_to(ROOT).as_posix()\n"
        "    for module in list(sys.modules.values()) if getattr(module, '__file__', None)\n"
        "    and Path(module.__file__).resolve().is_relative_to(ROOT)})))\n")
    result = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, check=True, cwd=ROOT)
    imported = set(result.stdout.split())
    owned = {path for path in imported if re.fullmatch(r"de4sdv/semantic/pleml_\w+\.py", path)
             or path in {"scripts/run_pleml_configuration_evaluation.py", "tools/configure_variant.py"}}
    assert "de4sdv/semantic/validation.py" in imported  # a shared module the evaluation imports, never recorded
    assert owned == set(receipts.EVALUATOR_MODULES)
    assert list(receipts.evaluator_identity()["modules"]) == list(receipts.EVALUATOR_MODULES)


# -- refresh announces and guards verdict changes (R15) ----------------------------------------


def without_xor(monkeypatch) -> None:
    """The review's plant: the configuration no longer applies XOR constraints; the agreement still sees them."""
    original = evaluator._Configuration.decide

    def decide(self):
        saved = self.model.constraints
        self.model.constraints = [item for item in saved if item.kind != "xor"]
        try:
            return original(self)
        finally:
            self.model.constraints = saved

    monkeypatch.setattr(evaluator._Configuration, "decide", decide)


def flip_fixture(tmp_path: Path) -> Path:
    """A receipt with the standalone member and an S-CORE-on-Android fixture, invalid on C001 alone."""
    line = platform_line()
    line.configure("invalidScoreAndroid", "autoware", "eclipseSCORE", "android", "noHypervisor")
    return write_receipt(tmp_path, line.graph)


def test_a_refresh_that_flips_a_verdict_is_refused_unless_accepted(tmp_path, monkeypatch, capsys):
    path = flip_fixture(tmp_path)
    committed = path.read_bytes()
    decided = {item["configuration"]: item["valid"]
               for item in json.loads(committed)["evaluation"]["feature_models"][0]["configurations"]}
    assert decided["invalidScoreAndroid"] is False
    without_xor(monkeypatch)
    assert receipts.replay_committed(path.parent, tmp_path) == [
        f"{path}: the committed evaluation does not reproduce from the committed elements"]
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    capsys.readouterr()
    assert cli.main(["refresh", str(path)]) == 1
    refused = json.loads(capsys.readouterr().out)
    expected = [
        f"{PLATFORM_RECEIPT}: SDVProductLineFeatureModel/invalidScoreAndroid: valid False -> True",
        f"{PLATFORM_RECEIPT}: SDVProductLineFeatureModel/invalidScoreAndroid: reasons ['constraint C001'] -> []",
        f"{PLATFORM_RECEIPT}: SDVProductLineFeatureModel/invalidScoreAndroid: derived variants {{}} -> "
        "{'applicationMiddlewareAdapter': 'autowareToSCORE', 'hypervisor': 'none', 'middleware': 'eclipseSCORE', "
        "'osPlatform': 'android', 'vehicleApplication': 'autoware'}",
        f"{PLATFORM_RECEIPT}: SDVProductLineFeatureModel/pair: reasons ['pair-exclusion'] -> ['derivation-no-rule']"]
    assert refused == {"receipts": [str(path)], "verdict_changes": expected, "written": False}
    assert path.read_bytes() == committed
    with pytest.raises(receipts.VerdictChanges, match="valid False -> True"):
        receipts.refresh(path, tmp_path)
    assert path.read_bytes() == committed
    assert cli.main(["refresh", "--accept-verdict-changes", str(path)]) == 0
    accepted = json.loads(capsys.readouterr().out)
    assert accepted == {"receipts": [str(path)], "verdict_changes": expected, "written": True}
    assert receipts.replay_committed(path.parent, tmp_path) == []


def test_a_neutral_refresh_writes_without_the_flag(tmp_path, monkeypatch, capsys):
    path = flip_fixture(tmp_path)
    changed_evaluation(monkeypatch)  # the output changes, no decision does
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    capsys.readouterr()
    assert cli.main(["refresh", str(path)]) == 0
    assert json.loads(capsys.readouterr().out) == {"receipts": [str(path)], "verdict_changes": [], "written": True}
    assert receipts.replay_committed(path.parent, tmp_path) == []


def test_a_refresh_never_hides_stale_elements(tmp_path):
    path = write_receipt(tmp_path)
    (tmp_path / MODEL).write_text("edited\n")
    with pytest.raises(receipts.StaleReceipt, match="changed after the serialization"):
        receipts.refresh(path, tmp_path)


def test_the_cli_replays_and_reports_stale_receipts(tmp_path, capsys, monkeypatch):
    path = write_receipt(tmp_path)
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    assert cli.main(["replay", str(path)]) == 0
    (tmp_path / MODEL).write_text("edited\n")
    assert cli.main(["replay", str(path)]) == 1
    assert "changed after the serialization" in capsys.readouterr().out


def test_a_receipt_with_integrity_errors_fails_the_replay(tmp_path, monkeypatch, capsys):
    line = PlatformLine(PlemlGraph(library=evaluator.LIBRARY_SOURCE), rules={}, governed=True)
    line.configure("member", "autoware", "noMiddleware", "linux", "noHypervisor")
    path = write_receipt(tmp_path, line.graph)
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    assert cli.main(["replay", str(path)]) == 1
    assert "has 0 rules and 0 exclusions" in capsys.readouterr().out


# -- the entry point of the licensed authority job ---------------------------------------------


def test_a_licensed_bundle_becomes_one_receipt_per_feature_model(tmp_path):
    graph = two_family_graph()
    root = tmp_path / "tree"
    result = cli.write_receipts(bundle_of(graph, root), tmp_path / "out", serializer=SERIALIZER, root=root)
    assert result["failures"] == []
    assert result["elements"].name == ELEMENTS
    assert [path.name for path in result["receipts"]] == ["synthetic_environments.receipt.json", PLATFORM_RECEIPT]
    expected = {item["feature_model"]: item for item in graph.evaluate()["feature_models"]}
    for path, documents in zip(result["receipts"], ([ENVIRONMENT_CONFIGURATION, ENVIRONMENTS],
                                                    [MEMBER, PAIR, MODEL])):
        replayed = receipts.replay(path, root)
        assert replayed["model_sources"] == documents
        (model,) = replayed["evaluation"]["feature_models"]
        assert replayed["feature_models"] == [model["feature_model"]]
        assert model == expected[model["feature_model"]]
        assert replayed["serializer"] == {key: SERIALIZER[key] for key in ("name", "version", "options")}
        assert replayed["provenance"] == {"executor_revision": "e" * 40, "bundle_git_commit": "a" * 40}
        assert replayed["qualified"] is False and replayed["native_expression_executed"] is False


def test_receipts_do_not_depend_on_the_checkout_or_the_library_location(tmp_path):
    """Two bundles that differ only in the resource paths of their URIs give the same receipts, byte for byte."""
    graph = two_family_graph()
    root = tmp_path / "tree"
    runner = bundle_of(graph, root, uri_prefix="../../DE4SDV/DE4SDV/")
    local = bundle_of(graph, root, uri_prefix="../_ple-experiment/")
    assert runner.external_references != local.external_references
    assert {item["uri"].split("#")[0] for item in runner.external_references} != {
        item["uri"].split("#")[0] for item in local.external_references}
    first = cli.write_receipts(runner, tmp_path / "runner", serializer=SERIALIZER, root=root)
    second = cli.write_receipts(local, tmp_path / "local", serializer=SERIALIZER, root=root)
    assert first["elements"].read_bytes() == second["elements"].read_bytes()
    for one, other in zip(first["receipts"], second["receipts"], strict=True):
        assert one.name == other.name and one.read_bytes() == other.read_bytes()
        assert receipts.replay(one, root)["evaluation"] == receipts.replay(other, root)["evaluation"]
    payload = receipts.read_elements(first["elements"])
    assert all("@uri" not in json.dumps(element) for element in payload["elements"])
    assert payload["external_references"] and all(
        set(item) == {"source_element_id", "property_path", "target_id"} for item in payload["external_references"])


def test_a_bundle_element_with_a_resource_uri_is_refused(tmp_path):
    bundle = bundle_of(two_family_graph(), tmp_path)
    element = next(iter(bundle.elements.values()))
    elements = {**bundle.elements, element["@id"]: {**element, "owner": {"@id": element["@id"], "@uri": "../x#y"}}}
    with pytest.raises(ValueError, match="carries a resource URI"):
        receipts.payload_from_bundle(dataclasses.replace(bundle, elements=elements), serializer=SERIALIZER)


def test_the_receipts_compare_equal_across_commits_and_runs(tmp_path):
    """Run provenance stays out of the elements: another executor revision and bundle commit compare equal (R3)."""
    graph = two_family_graph()
    root = tmp_path / "tree"
    first = cli.write_receipts(bundle_of(graph, root), tmp_path / "first", serializer=SERIALIZER, root=root)
    second = cli.write_receipts(bundle_of(graph, root, git_commit="b" * 40), tmp_path / "second",
                                serializer={**SERIALIZER, "executor_revision": "f" * 40}, root=root)
    assert first["elements"].read_bytes() == second["elements"].read_bytes()
    assert receipts.compare_with_committed(second["receipts"], tmp_path / "first") == []
    assert json.loads(second["receipts"][1].read_text())["provenance"] == {"executor_revision": "f" * 40,
                                                                          "bundle_git_commit": "b" * 40}
    other = two_family_graph()
    other.documentation(other.model_documents and next(
        item["@id"] for item in other.elements if item.get("declaredName") == "EnvironmentTree"), "Edited.")
    third = cli.write_receipts(bundle_of(other, root), tmp_path / "third", serializer=SERIALIZER, root=root)
    assert receipts.compare_with_committed(third["receipts"], tmp_path / "first") == [
        f"{name}: the committed elements differ from the fresh serialization"
        for name in ("synthetic_environments.receipt.json", PLATFORM_RECEIPT)]
    (tmp_path / "first" / PLATFORM_RECEIPT).unlink()
    assert receipts.compare_with_committed(second["receipts"], tmp_path / "first") == [
        f"{PLATFORM_RECEIPT}: not committed; commit the fresh receipts and their elements"]


def test_the_receipts_command_writes_and_compares(tmp_path, monkeypatch, capsys):
    root = tmp_path / "tree"
    bundle = bundle_of(two_family_graph(), root)
    bundle.write(tmp_path / "bundle.json")
    monkeypatch.setattr(cli, "ROOT", root)
    arguments = ["receipts", "--bundle", str(tmp_path / "bundle.json"), "--serializer-version", "0.10.3"]
    assert cli.main([*arguments, "--executor-revision", "e" * 40, "--out", str(tmp_path / "first")]) == 0
    assert cli.main([*arguments, "--executor-revision", "f" * 40, "--out", str(tmp_path / "second"),
                     "--compare", str(tmp_path / "first")]) == 0
    edited = receipts.read_elements(tmp_path / "first" / ELEMENTS)
    edited["elements"] = edited["elements"][:-1]
    receipts.write_elements(tmp_path / "first" / ELEMENTS, edited)
    capsys.readouterr()
    assert cli.main([*arguments, "--executor-revision", "e" * 40, "--out", str(tmp_path / "third"),
                     "--compare", str(tmp_path / "first")]) == 1
    assert "the committed elements differ from the fresh serialization" in capsys.readouterr().out
    assert cli.main([*arguments, "--executor-revision", "e" * 40, "--out", str(root / "inside")]) == 2


def test_refreshed_receipts_replay_with_their_own_shadow(tmp_path, monkeypatch):
    """After an output-changing evaluator change, refresh then replay passes; each shadow covers its own tree (R2)."""
    root = tmp_path / "tree"
    with_catalogue(root)
    monkeypatch.setattr(cli, "ROOT", root)
    result = cli.write_receipts(bundle_of(two_family_graph(), root), tmp_path / "out", serializer=SERIALIZER,
                                root=root)
    shadows = {path.name: json.loads(path.read_text())["shadow"] for path in result["receipts"]}
    assert [item["tree"] for item in shadows[PLATFORM_RECEIPT]["feature_models"]] == ["SDVProductLineFeatureTree"]
    assert shadows["synthetic_environments.receipt.json"] == {}
    changed_evaluation(monkeypatch)
    paths = [str(path) for path in result["receipts"]]
    assert cli.main(["replay", *paths]) == 1
    assert cli.main(["refresh", *paths]) == 0
    assert cli.main(["replay", *paths]) == 0
    assert {path.name: json.loads(path.read_text())["shadow"] for path in result["receipts"]} == shadows


def test_a_refresh_refused_for_one_receipt_writes_none(tmp_path, monkeypatch):
    root = tmp_path / "tree"
    monkeypatch.setattr(cli, "ROOT", root)
    result = cli.write_receipts(bundle_of(two_family_graph(), root), tmp_path / "out", serializer=SERIALIZER,
                                root=root)
    before = {path: path.read_bytes() for path in result["receipts"]}
    for path in result["receipts"]:
        receipt = json.loads(path.read_text())
        receipt["evaluator"]["sha256"] = "f" * 64
        if path.name == PLATFORM_RECEIPT:  # the second receipt is refused; the first alone would refresh
            receipt["elements"]["content_sha256"] = "0" * 64
        path.write_text(json.dumps(receipt))
    edited = {path: path.read_bytes() for path in result["receipts"]}
    assert [path.name for path in result["receipts"]][-1] == PLATFORM_RECEIPT
    assert cli.main(["refresh", *(str(path) for path in result["receipts"])]) == 2
    assert {path: path.read_bytes() for path in result["receipts"]} == edited != before


def test_a_bundle_whose_library_is_not_the_pinned_package_is_refused(tmp_path):
    graph = PlemlGraph()
    PlatformLine(graph).configure("member", "autoware", "noMiddleware", "linux", "noHypervisor")
    with pytest.raises(ValueError, match="carries no PLEML library at .*mbse4u-pleml_1.1.1/PLEML.sysml.*"
                                         "external/pleml/PLEML.sysml"):
        receipts.payload_from_bundle(bundle_of(graph, tmp_path), serializer=SERIALIZER)


def test_a_bundle_document_outside_its_manifest_is_refused(tmp_path):
    bundle = bundle_of(two_family_graph(), tmp_path)
    bundle = dataclasses.replace(bundle, source_manifest=tuple(item for item in bundle.source_manifest
                                                               if item["path"] != ENVIRONMENTS))
    with pytest.raises(ValueError, match="must name each of its documents once"):
        receipts.payload_from_bundle(bundle, serializer=SERIALIZER)


def test_a_document_shared_by_two_feature_models_is_refused(tmp_path):
    graph = two_family_graph(environment_document=MEMBER)
    with pytest.raises(evaluator.PlemlShapeError, match="holds 2 configurations; a configuration typed by its tree "
                                                        "definition has a file of its own"):
        cli.write_receipts(bundle_of(graph, tmp_path / "tree"), tmp_path / "out", serializer=SERIALIZER,
                           root=tmp_path / "tree")


def test_the_receipt_decides_admission_with_the_production_scope_reader(tmp_path, monkeypatch):
    graph = two_family_graph()
    calls = []

    def validator(elements, sources):
        calls.append(len(elements))
        return synthetic_scope_validator(elements, sources)

    monkeypatch.setattr(receipts, "validate_scope_elements", validator)
    root = tmp_path / "tree"
    result = cli.write_receipts(bundle_of(graph, root), tmp_path / "out", serializer=SERIALIZER, root=root)
    platform = receipts.replay(result["receipts"][1], root)
    admitted = {item["configuration"]: item["admission"]["admitted"]
                for item in platform["evaluation"]["feature_models"][0]["configurations"]}
    assert admitted == {"member": True, "pair": False}
    assert platform["evaluation"]["admission_authority"] == SCOPE and calls


def test_a_bundle_without_the_governed_scope_is_refused(tmp_path):
    """Admission is a receipt field: without the scope, no receipt is written (R5)."""
    graph = two_family_graph(governed=False)
    payload = receipts.payload_from_bundle(bundle_of(graph, tmp_path / "tree"), serializer=SERIALIZER)
    assert receipts.governed_scope(payload) is None
    with pytest.raises(ValueError, match="the bundle carries no governed scope; every receipt records the "
                                         "admission"):
        cli.write_receipts(bundle_of(graph, tmp_path / "tree"), tmp_path / "out", serializer=SERIALIZER,
                           root=tmp_path / "tree")
    assert not (tmp_path / "out").exists()


# -- writer inputs and the normalised body (R19) -------------------------------------------------


def test_the_normalised_body_drops_the_header_and_the_derivation_source():
    projection = (ROOT / "model-based-product-line-engineering/product-models/aebs_autoware_linux_lidar_camera.sysml").read_text()
    body = receipts.normalised_body(projection)
    assert not body.startswith("/*") and "SHA-256" not in body
    assert "   * Derived platform-stack projection from <configuration source>." in body
    assert "part :>> applicationMiddlewareAdapter = applicationMiddlewareAdapter::none;" in body
    other = projection.replace("Feature model SHA-256: ", "Feature model SHA-256: 0").replace(
        "projection from Bill-of-Features.", "projection from a receipt.")
    assert receipts.normalised_body(other) == body


def test_the_normalisation_touches_only_the_writers_derivation_source_line():
    """Review round 1 of S4, R6: a description line of the same shape stays part of the body, and a
    projection without the derivation-source line where the writer puts it is refused."""
    projection = (ROOT / "model-based-product-line-engineering/product-models/aebs_autoware_linux_lidar_camera.sysml"
                  ).read_text()
    autoware, apollo = (projection.replace("AEBS reference member product.",
                                           f"Derived platform-stack projection from the {member} member.")
                        for member in ("Autoware", "Apollo"))
    assert receipts.normalised_body(autoware) != receipts.normalised_body(apollo)
    assert "   * Derived platform-stack projection from the Autoware member." in receipts.normalised_body(autoware)
    moved = projection.replace("   * Derived platform-stack projection from Bill-of-Features.\n", "")
    with pytest.raises(ValueError, match="derivation-source line"):
        receipts.normalised_body(moved)


def test_the_description_is_folded_as_the_yaml_writer_receives_it():
    bof = yaml.safe_load((CONFIGURATIONS / "aebs-autoware-linux-lidar-camera.yaml").read_text())
    doc_body = ("AEBS reference member product.\nAutoware on Linux, single-domain (no middleware, no hypervisor).\n"
                "LiDAR + camera perception, IMU + wheel odometry common.\n"
                "Vehicle-target AEBS only (no pedestrian/bicycle detection).")
    assert receipts.fold_description(doc_body) == bof["description"].strip()
    assert receipts.fold_description("First.\n\nSecond paragraph\ncontinues.") == "First.\nSecond paragraph continues."


def test_the_writer_inputs_carry_explicit_states_and_catalogue_paths():
    line = PlatformLine()
    line.configure("member", "autoware", "noMiddleware", "linux", "noHypervisor", disabled=("pedestrianDetection",),
                   projection_name="Member", description="One\nline.")
    model = line.graph.evaluate()["feature_models"][0]
    catalogue = cli.Catalogue(ROOT / CATALOGUE)
    inputs = receipts.writer_inputs(model["configurations"][0], model["features"], catalogue.paths())
    assert inputs["projection_name"] == "Member" and inputs["description"] == "One line."
    assert inputs["explicit_optional_states"] == {"capabilities.pedestrianDetection": "disabled"}
    assert inputs["catalogue_paths"]["capabilities.pedestrianDetection"] == \
        "Capabilities.ForwardCollisionMitigation.PedestrianDetection"
    assert inputs["catalogue_paths"]["platformStack.noMiddleware"] == "PlatformStack.Middleware.None"


# -- the shadow checks against today's catalogue (R9, R10) --------------------------------------


def test_the_catalogue_allowed_lists_include_the_dropped_c002():
    lists = {item["id"]: item for item in cli.Catalogue(ROOT / CATALOGUE).allowed_lists()}
    assert sorted(lists) == ["C001", "C002", "C003"]
    assert lists["C001"]["allowed"] == ["F-PLATFORM-OS-LINUX", "F-PLATFORM-OS-QNX"]
    assert len(lists["C002"]["allowed"]) == 3


def test_the_exclusions_equal_the_complements_and_drift_fails():
    catalogue = cli.Catalogue(ROOT / CATALOGUE)
    model = PlatformLine().graph.evaluate()["feature_models"][0]
    assert cli.complement_errors(model, catalogue.allowed_lists()) == []
    drifted = PlatformLine()
    f = drifted.features
    f["zephyr"] = drifted.graph.feature(f["platformStack"], "zephyr", (0, 1), subsets=f["os"], short="F-PLATFORM-OS-ZEPHYR")
    errors = cli.complement_errors(drifted.graph.evaluate()["feature_models"][0], catalogue.allowed_lists())
    assert {error.split(":")[0] for error in errors} == {"C001", "C002", "C003"}


def test_the_rule_table_equals_the_catalogue_row_by_row():
    catalogue = cli.Catalogue(ROOT / CATALOGUE)
    assert cli.rule_table_errors(PlatformLine().graph.evaluate()["feature_models"][0], catalogue) == []
    from tests.pleml_graph_fixtures import ADAPTER_RULES
    wrong = dict(ADAPTER_RULES)
    wrong[("apollo", "eclipseSCORE")] = "openpilotToSCORE"
    errors = cli.rule_table_errors(PlatformLine(rules=wrong).graph.evaluate()["feature_models"][0], catalogue)
    assert errors == ["D-ASSET-APPLICATION-MIDDLEWARE-ADAPTER: rule ['F-PLATFORM-MIDDLEWARE-ECLIPSE-SCORE', "
                      "'F-PLATFORM-VEHICLE-APPLICATION-APOLLO'] yields openpilotToSCORE in the model and "
                      "apolloToSCORE in the catalogue"]


# -- the reason map against the configurator (R11) -------------------------------------------------


def _templates() -> list[str]:
    """Every rejection the configurator can print, rendered with placeholder values."""
    source = (ROOT / "tools/configure_variant.py").read_text()
    values = {"label": "derived_asset_selections[0]", "rule_label": "derived_asset_selections[0].rules[0]",
              "status": "inspected", "cid": "C001", "variation_error": "Mapped SysML variation 'x' was not found",
              "package_error": "SysML package 'x' was not found", "stack_error": "SysML part def 'x' was not found",
              "len(matches)": "2"}

    def render(node: ast.AST) -> str:
        if isinstance(node, ast.Constant):
            return str(node.value)
        if isinstance(node, ast.JoinedStr):
            return "".join(str(part.value) if isinstance(part, ast.Constant)
                           else values.get(ast.unparse(part.value), "x") for part in node.values)
        if isinstance(node, ast.BinOp):
            return render(node.left) + "x"
        raise AssertionError(ast.unparse(node))

    messages = []
    for node in ast.walk(ast.parse(source)):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "append"
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "errors"):
            messages.append(render(node.args[0]))
        if isinstance(node, ast.Return) and isinstance(node.value, ast.List):
            messages += [render(item) for item in node.value.elts if isinstance(item, ast.JoinedStr)]
    return messages + ["Error reading input: x", "Error parsing YAML: x"]


def test_every_configurator_rejection_has_a_reason_class():
    catalogue = cli.Catalogue(ROOT / CATALOGUE)
    templates = _templates()
    assert len(templates) >= 100
    for message in templates:
        keys, counted = cli.yaml_reason_keys([message], {}, catalogue)
        assert counted == 1 and len(keys) <= 1, message
        assert len(cli.yaml_reasons([message], {}, catalogue)) == 1, message


def test_a_configurator_rejection_names_its_location():
    """Review round 1 of S4, R2: each counted rejection keeps the group, the pair of choices or the derived
    variation it names, so the parity compares the reasons as a multiset with their locations."""
    catalogue = cli.Catalogue(ROOT / CATALOGUE)
    selections = {"PlatformStack.VehicleApplication": "Openpilot", "PlatformStack.Middleware": "AndroidSDV"}
    messages = [
        "'PlatformStack.OS': '['Android', 'Linux']' is not a valid XOR choice. Valid: ['Linux', 'Android', 'QNX']",
        "Mandatory alternative group 'PlatformStack.Hypervisor' has no selection",
        "[C001] requires: 'PlatformStack.OS in [Linux, QNX]' is not satisfied when 'PlatformStack.Middleware == "
        "EclipseSCORE' holds.",
        "Derived asset 'D-ASSET-APPLICATION-MIDDLEWARE-ADAPTER' for 'SDVPlatformStack.applicationMiddlewareAdapter' "
        "has no rule matching PlatformStack.VehicleApplication='Openpilot', PlatformStack.Middleware='AndroidSDV'",
        "Unknown feature path in selections: 'PlatformStack.ApplicationMiddlewareAdapter'",
        "Mandatory feature not selected: 'Capabilities.ForwardCollisionMitigation.VehicleTargetAEBS'",
    ]
    assert cli.yaml_reasons(messages, selections, catalogue) == [
        {"class": "upper-bound", "constraint": None, "location": ["PlatformStack.OS"]},
        {"class": "lower-bound", "constraint": None, "location": ["PlatformStack.Hypervisor"]},
        {"class": "constraint", "constraint": "C001", "location": None},
        {"class": "pair-exclusion", "constraint": None,
         "location": ["PlatformStack.Middleware.AndroidSDV", "PlatformStack.VehicleApplication.Openpilot"]},
        {"class": "derived-variant-not-selectable", "constraint": None, "location": ["applicationmiddlewareadapter"]},
        {"class": "common-capability-false", "constraint": None,
         "location": ["Capabilities.ForwardCollisionMitigation.VehicleTargetAEBS"]},
    ]
    assert cli.yaml_reason_keys(messages, selections, catalogue) == ({
        ("upper-bound", None), ("lower-bound", None), ("constraint", "C001"), ("pair-exclusion", None),
        ("derived-variant-not-selectable", None), ("common-capability-false", None)}, 6)


def run_configurator(tmp_path: Path, name: str, selections: dict) -> dict:
    template = yaml.safe_load((CONFIGURATIONS / "aebs-autoware-linux-lidar-camera.yaml").read_text())
    data = {"name": "ParityProbe", "description": template["description"], "selections": selections}
    bof, output = tmp_path / f"{name}.yaml", tmp_path / f"{name}.sysml"
    bof.write_text(yaml.safe_dump(data, sort_keys=False))
    result = subprocess.run([sys.executable, str(ROOT / "tools/configure_variant.py"), "--feature-model",
                             str(ROOT / CATALOGUE), "--bof", str(bof), "--output", str(output)],
                            capture_output=True, text=True, cwd=ROOT, check=False, timeout=60)
    messages = [match.group(1).strip() for match in map(re.compile(r"^\s+[•-] (.+)$").match,
                                                         result.stderr.splitlines()) if match]
    keys, counted = cli.yaml_reason_keys(messages, selections, cli.Catalogue(ROOT / CATALOGUE))
    derived = dict(re.findall(r"^\s*part :>> (\w+) = \w+::(\w+);", output.read_text(), re.M)) if output.exists() else {}
    return {"valid": result.returncode == 0, "keys": keys, "violations": counted, "derived_variants": derived}


NAMES = {"Autoware": "autoware", "Openpilot": "openpilot", "Apollo": "apollo", "EclipseSCORE": "eclipseSCORE",
         "AndroidSDV": "androidSDV", "AUTOSARAdaptive": "autosarAdaptive", "None": None, "Linux": "linux",
         "Android": "android", "QNX": "qnx", "QVM": "qvm", "ACRN": "acrn", "KVM": "kvm"}


def pleml_outcome(application, middleware, os, hypervisor, sensors, *, hand_picked=False) -> dict:
    line = PlatformLine()

    def name(value, none):
        return [NAMES[item] or none for item in value] if isinstance(value, list) else (
            () if value is None else NAMES[value] or none)

    probe = line.configure("probe", name(application, None), name(middleware, "noMiddleware"), name(os, None),
                           name(hypervisor, "noHypervisor"), [item.lower() if item != "LiDAR" else "lidar"
                                                              for item in sensors])
    if hand_picked:
        adapter = line.graph.own(probe, "FeatureMembership", "ReferenceUsage", member_name="adapter",
                                 declaredName="adapter")
        line.graph.reference_value(adapter, [line.variations["applicationMiddlewareAdapter"]["none"]])
    (item,) = line.graph.evaluate()["feature_models"][0]["configurations"]
    return {"valid": item["valid"], "keys": receipts.reason_keys(item),
            "derived_variants": {variant["variation"]: variant["variant"] for variant in item["derived_variants"]}}


ROWS = [
    ("member", ("Autoware", "None", "Linux", "None"), {}, "equal"),
    ("aaos-member", ("Autoware", "AndroidSDV", "Android", "KVM"), {}, "equal"),
    ("score-example", ("Autoware", "EclipseSCORE", "Linux", "None"), {}, "equal"),
    ("apollo-qnx-qvm", ("Apollo", "EclipseSCORE", "QNX", "QVM"), {}, "equal"),
    ("openpilot-score", ("Openpilot", "EclipseSCORE", "Linux", "None"), {}, "equal"),
    ("apollo-none", ("Apollo", "None", "Linux", "None"), {}, "equal"),
    ("fixture-c001", ("Autoware", "EclipseSCORE", "Android", "None"), {}, "both-reject"),
    ("both-alternatives", ("Autoware", ["AndroidSDV", "None"], ["Android", "Linux"], ["KVM", "None"]), {}, "both-reject"),
    ("no-alternative", ("Autoware", None, None, None), {}, "both-reject"),
    ("pair-openpilot-android", ("Openpilot", "AndroidSDV", "Linux", "None"), {}, "both-reject"),
    ("pair-openpilot-autosar", ("Openpilot", "AUTOSARAdaptive", "Linux", "None"), {}, "both-reject"),
    ("pair-apollo-android", ("Apollo", "AndroidSDV", "Linux", "None"), {}, "both-reject"),
    ("pair-apollo-autosar", ("Apollo", "AUTOSARAdaptive", "Linux", "None"), {}, "both-reject"),
    ("hand-picked-adapter", ("Autoware", "None", "Linux", "None"),
     {"PlatformStack.ApplicationMiddlewareAdapter": "none"}, "both-reject"),
    ("ug-10-vehicle-target-aebs-false", ("Autoware", "None", "Linux", "None"),
     {"Capabilities.ForwardCollisionMitigation.VehicleTargetAEBS": False}, "not-expressible"),
    ("vehicle-target-aebs-false-elsewhere", ("Autoware", "None", "Linux", "None"),
     {"Capabilities.ForwardCollisionMitigation.VehicleTargetAEBS": False}, "defect"),
]


@pytest.mark.parametrize(("row", "choices", "extra", "expected"), ROWS, ids=[row[0] for row in ROWS])
def test_a_parity_row_classifies_as_the_plan_expects(tmp_path, row, choices, extra, expected):
    application, middleware, os, hypervisor = choices
    selections = {"PlatformStack.VehicleApplication": application, "PlatformStack.Middleware": middleware,
                  "PlatformStack.OS": os, "PlatformStack.Hypervisor": hypervisor,
                  "SensingBoundary.PerceptionSensors": ["LiDAR", "Camera"]}
    selections = {key: value for key, value in selections.items() if value is not None}
    remainder_yaml = run_configurator(tmp_path, f"{row}-remainder", dict(selections))
    selections.update(extra)
    yaml_side = run_configurator(tmp_path, row, selections)
    pleml = pleml_outcome(application, middleware, os, hypervisor, ["LiDAR", "Camera"],
                          hand_picked="PlatformStack.ApplicationMiddlewareAdapter" in extra)
    result = receipts.classify_row(row, yaml_side, pleml, yaml_remainder=remainder_yaml)
    assert result["class"] == expected, (result, yaml_side, pleml)


def _rejected(*reasons: tuple) -> dict:
    return {"valid": False, "keys": {(item[0], item[1]) for item in reasons}, "derived_variants": {},
            "reasons": list(reasons)}


def test_a_both_reject_row_compares_the_reasons_in_count_and_location():
    """Review round 1 of S4, R2: the same classes are not enough. With the reasons of both sides given, a
    count or a location that differs is a defect."""
    groups = ("PlatformStack.Hypervisor", "PlatformStack.Middleware", "PlatformStack.OS")
    three = _rejected(*(("upper-bound", None, (group,)) for group in groups))
    assert receipts.classify_row("both-alternatives", three, three) == {"class": "both-reject", "detail": ""}
    # A count mismatch: three upper bounds on one side, one on the other.
    one = _rejected(("upper-bound", None, ("PlatformStack.OS",)))
    count = receipts.classify_row("both-alternatives", three, one)
    assert count["class"] == "defect" and count["detail"].startswith("the reasons differ in count or location")
    # A location mismatch: a pair exclusion of another pair.
    openpilot = _rejected(("pair-exclusion", None,
                           ("PlatformStack.Middleware.AndroidSDV", "PlatformStack.VehicleApplication.Openpilot")))
    apollo = _rejected(("pair-exclusion", None,
                        ("PlatformStack.Middleware.AndroidSDV", "PlatformStack.VehicleApplication.Apollo")))
    location = receipts.classify_row("unsupported-openpilot-android-sdv", openpilot, apollo)
    assert location["class"] == "defect" and "VehicleApplication.Apollo" in location["detail"]
    # Without the reasons, the classes alone decide, as before.
    bare = [{key: value for key, value in side.items() if key != "reasons"} for side in (openpilot, apollo)]
    assert receipts.classify_row("unsupported-openpilot-android-sdv", *bare)["class"] == "both-reject"


# -- evidence records (plan section 4) --------------------------------------------------------------


@pytest.mark.parametrize("record", [
    {"status": "planned", "artifacts": []},
    {"status": "inspected", "artifacts": []},
    {"status": "inspected", "artifacts": [{"id": "EVID-X-1", "path": "README.md"}]},
    {"status": "inspected", "artifacts": [{"id": "evid-x", "path": "README.md"}]},
    {"status": "inspected", "artifacts": [{"id": "EVID-X", "path": "README.md"}, {"id": "EVID-X", "path": "README.md"}]},
    {"status": "inspected", "artifacts": [{"id": "EVID-X", "path": "/etc/hostname"}]},
    {"status": "inspected", "artifacts": [{"id": "EVID-X", "path": "../outside.md"}]},
    {"status": "inspected", "artifacts": [{"id": "EVID-X", "path": ".git/config"}]},
    {"status": "inspected", "artifacts": [{"id": "EVID-X", "path": "docs/does-not-exist.md"}]},
    {"status": "unknown", "artifacts": []},
    {"status": "planned", "artifacts": [{"id": "EVID-X"}]},
    {"status": "planned", "extra": 1},
])
def test_the_evidence_record_check_keeps_the_configurator_rules(record):
    configurator = cli.load_configurator()
    bof = {"name": "Probe", "selections": {}, "evidence": record}
    shape = [error for error in configurator.validate_document_shapes({"root": {"name": "r"}}, bof) if "evidence" in error]
    expected = bool(shape or configurator.validate_bof_evidence(bof))
    assert bool(receipts.evidence_record_errors(record)) == expected


def test_the_evidence_record_check_refuses_symbolic_links(tmp_path):
    (tmp_path / "real.md").write_text("x")
    (tmp_path / "link").symlink_to(tmp_path)
    errors = receipts.evidence_record_errors({"status": "inspected", "artifacts": [{"id": "EVID-X", "path": "link/real.md"}]},
                                             tmp_path)
    assert errors == ["evidence artifact path 'link/real.md' must not traverse symbolic links"]


def test_the_kernel_classes_bind_on_a_genuine_export_through_the_model_built_contract():
    """Real serializer output of the S2k kernel binds as ingestion binds it; no name is matched."""
    import gzip

    export = json.loads(gzip.decompress((ROOT / "tests/fixtures/genuine_export/inc-aebs-010.json.gz").read_bytes()))
    contract = KernelContract.from_layers(ROOT)
    names = [name for _, name, _ in evaluator.KERNEL.definitions().values()]
    if not all(name in contract.classes for name in names):
        pytest.skip("the S2k kernel classes are not on this base yet (#402)")
    bindings = evaluator.kernel_bindings(contract, export["elements"], export["element_sources"])
    assert sorted(bindings) == sorted(names)
    by_id = {element["@id"]: element for element in export["elements"]}
    for name, identifier in bindings.items():
        assert by_id[identifier]["@type"] == "MetadataDefinition" and by_id[identifier]["declaredName"] == name
        assert export["element_sources"][identifier] == evaluator.KERNEL_SOURCE
