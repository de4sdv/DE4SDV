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
from tests.pleml_graph_fixtures import (CONFIGURATIONS as CONFIGURATION_DOCUMENT, LIBRARY, MODEL, SCOPE, PlatformLine,
                                        PlemlGraph, synthetic_contract)

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = Path("model-based-product-line-engineering/feature-models/sdv_product_line.yaml")
CONFIGURATIONS = ROOT / "model-based-product-line-engineering/feature-configurations"


@pytest.fixture(autouse=True)
def _the_kernel_contract_maps_the_derivation_classes(monkeypatch):
    """Receipts bind the kernel classes against the tree's contract; the synthetic one maps them as S2k does."""
    monkeypatch.setattr(receipts, "model_contract", lambda root=ROOT: synthetic_contract())


def test_the_kernel_constants_match_the_model_built_contract():
    contract = KernelContract.from_layers(ROOT)
    names = [name for _, name, _ in evaluator.KERNEL.definitions().values()]
    if not any(name in contract.classes for name in names):
        pytest.skip("the S2k kernel classes are not on this base yet (#402)")
    for name in names:
        mapping = contract.mapping(name)
        assert (mapping.file, mapping.declaration) == (evaluator.KERNEL_SOURCE, f"metadata def {name}")


def test_the_library_label_is_the_installed_library_of_the_fenced_project():
    from de4sdv.semantic import pleml_package

    assert evaluator.LIBRARY_SOURCE == pleml_package.LIBRARY_PATH.as_posix()
    assert Path(evaluator.LIBRARY_SOURCE).is_relative_to(pleml_package.PROJECT / ".sysand")


def payload_of(graph: PlemlGraph) -> dict:
    elements, sources = graph.build()
    return receipts.elements_payload(
        elements=elements, element_sources=sources, model_sources=sorted(graph.model_documents), library_source=LIBRARY,
        kernel_source=graph.kernel, serializer={"name": "syside", "version": "0.10.3", "options": "minimal"},
        source_manifest=[{"path": MODEL, "sha256": "0" * 64, "size": 0}])


def write_receipt(tmp_path: Path, graph: PlemlGraph) -> Path:
    payload = payload_of(graph)
    digest = receipts.write_elements(tmp_path / "line.elements.json.xz", payload)
    receipt = receipts.build_receipt(payload, elements_file="line.elements.json.xz", elements_sha256=digest)
    (tmp_path / MODEL).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / MODEL).write_text("synthetic\n")
    receipt["sources"] = payload["source_manifest"] = [
        {"path": MODEL, "sha256": receipts.sha256(b"synthetic\n"), "size": 10}]
    receipts.write_elements(tmp_path / "line.elements.json.xz", payload)
    receipt["elements"]["sha256"] = receipts.sha256((tmp_path / "line.elements.json.xz").read_bytes())
    receipt["elements"]["content_sha256"] = receipts.sha256(receipts.canonical(payload))
    path = tmp_path / "line.receipt.json"
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return path


def platform_line() -> PlatformLine:
    line = PlatformLine()
    line.configure("member", "autoware", "noMiddleware", "linux", "noHypervisor", projection_name="Member")
    line.configure("pair", "openpilot", "androidSDV", "linux", "noHypervisor")
    return line


# -- committed elements and receipts (R13) ------------------------------------------------------


def test_the_elements_file_is_deterministic_and_round_trips(tmp_path):
    payload = payload_of(platform_line().graph)
    first = receipts.write_elements(tmp_path / "a.xz", payload)
    second = receipts.write_elements(tmp_path / "b.xz", copy.deepcopy(payload))
    assert first == second
    assert receipts.read_elements(tmp_path / "a.xz") == payload


def test_a_fresh_receipt_replays_offline(tmp_path):
    receipt = receipts.replay(write_receipt(tmp_path, platform_line().graph), tmp_path)
    verdicts = {item["configuration"]: item["valid"] for item in receipt["evaluation"]["feature_models"][0]["configurations"]}
    assert verdicts == {"member": True, "pair": False}
    assert receipt["qualified"] is False and receipt["native_expression_executed"] is False


def test_a_receipt_with_an_edited_verdict_does_not_reproduce(tmp_path):
    path = write_receipt(tmp_path, platform_line().graph)
    receipt = json.loads(path.read_text())
    receipt["evaluation"]["feature_models"][0]["configurations"][1]["valid"] = True
    path.write_text(json.dumps(receipt))
    with pytest.raises(receipts.StaleReceipt, match="does not reproduce"):
        receipts.replay(path, tmp_path)


def test_edited_elements_are_stale_by_digest(tmp_path):
    path = write_receipt(tmp_path, platform_line().graph)
    payload = receipts.read_elements(tmp_path / "line.elements.json.xz")
    payload["elements"] = payload["elements"][:-1]
    receipts.write_elements(tmp_path / "line.elements.json.xz", payload)
    with pytest.raises(receipts.StaleReceipt, match="differ from the receipt's digest"):
        receipts.replay(path, tmp_path)


def test_a_changed_model_source_makes_the_receipt_stale(tmp_path):
    path = write_receipt(tmp_path, platform_line().graph)
    (tmp_path / MODEL).write_text("edited\n")
    with pytest.raises(receipts.StaleReceipt, match="changed after the serialization"):
        receipts.replay(path, tmp_path)
    (tmp_path / MODEL).unlink()
    with pytest.raises(receipts.StaleReceipt, match="is missing"):
        receipts.replay(path, tmp_path)


def test_another_evaluator_revision_is_refused_and_refreshed_offline(tmp_path, monkeypatch):
    path = write_receipt(tmp_path, platform_line().graph)
    receipt = json.loads(path.read_text())
    receipt["evaluator"]["sha256"] = "f" * 64
    receipt["serializer"]["executor_revision"] = "e" * 40
    path.write_text(json.dumps(receipt))
    with pytest.raises(receipts.StaleReceipt, match="another evaluator revision"):
        receipts.replay(path, tmp_path)
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    assert cli.main(["refresh", str(path)]) == 0
    refreshed = receipts.replay(path, tmp_path)
    assert refreshed["evaluator"]["sha256"] == receipts.evaluator_digest()
    assert refreshed["evaluator"]["refreshed_from"] == "f" * 64
    assert refreshed["serializer"]["executor_revision"] == "e" * 40


def test_a_refresh_never_hides_stale_elements(tmp_path):
    path = write_receipt(tmp_path, platform_line().graph)
    (tmp_path / MODEL).write_text("edited\n")
    with pytest.raises(receipts.StaleReceipt, match="changed after the serialization"):
        receipts.refresh(path, tmp_path)


def test_the_cli_replays_and_reports_stale_receipts(tmp_path, capsys, monkeypatch):
    path = write_receipt(tmp_path, platform_line().graph)
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    assert cli.main(["replay", str(path)]) == 0
    (tmp_path / MODEL).write_text("edited\n")
    assert cli.main(["replay", str(path)]) == 1
    assert "changed after the serialization" in capsys.readouterr().out


def test_a_receipt_with_integrity_errors_fails_the_replay(tmp_path, monkeypatch, capsys):
    line = PlatformLine(rules={})
    line.configure("member", "autoware", "noMiddleware", "linux", "noHypervisor")
    path = write_receipt(tmp_path, line.graph)
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    assert cli.main(["replay", str(path)]) == 1
    assert "has 0 rules and 0 exclusions" in capsys.readouterr().out


# -- the entry point of the licensed authority job ---------------------------------------------

ENVIRONMENTS = "model-based-product-line-engineering/feature-models/synthetic_environments.sysml"
ENVIRONMENT_CONFIGURATIONS = ("model-based-product-line-engineering/feature-configurations/"
                              "synthetic_environment_configurations.sysml")
SERIALIZER = {"name": "syside", "version": "0.10.3", "options": "production export", "executor_revision": "e" * 40}
ROLES = {MODEL: "pleml-feature-model", ENVIRONMENTS: "pleml-feature-model",
         CONFIGURATION_DOCUMENT: "pleml-feature-configuration",
         ENVIRONMENT_CONFIGURATIONS: "pleml-feature-configuration"}


def two_family_graph(*, governed: bool = False, environment_document: str = ENVIRONMENT_CONFIGURATIONS) -> PlemlGraph:
    """The platform line and an environment family, each in its own model and configurations document."""
    graph = PlemlGraph(library=evaluator.LIBRARY_SOURCE)
    line = PlatformLine(graph, governed=governed)
    line.configure("member", "autoware", "noMiddleware", "linux", "noHypervisor", projection_name="Member")
    line.configure("pair", "openpilot", "androidSDV", "linux", "noHypervisor")
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


def bundle_of(graph: PlemlGraph, root: Path, *, uri_prefix: str | None = None) -> BaselineExportBundle:
    """The graph as the authority job's export bundle, its documents written under ``root``."""
    elements, sources = graph.build()
    documents: dict[str, list] = {}
    for element in elements:
        documents.setdefault(sources[element["@id"]], []).append(element)
    if uri_prefix is not None:
        documents = with_resource_uris(documents, uri_prefix)
    bundle = build_export_bundle(git_commit="a" * 40, source_documents=documents)
    manifest = []
    for label in sorted(documents):
        data = f"synthetic {label}\n".encode()
        (root / label).parent.mkdir(parents=True, exist_ok=True)
        (root / label).write_bytes(data)
        manifest.append({"path": label, "authority": ROLES.get(label, "reviewed"), "sha256": receipts.sha256(data),
                         "size": len(data)})
    return dataclasses.replace(bundle, source_manifest=tuple(manifest))


def test_a_licensed_bundle_becomes_one_receipt_per_feature_model(tmp_path):
    graph = two_family_graph()
    root = tmp_path / "tree"
    result = cli.write_receipts(bundle_of(graph, root), tmp_path / "out", serializer=SERIALIZER, root=root)
    assert result["failures"] == []
    assert result["elements"].name == "pleml-feature-models.elements.json.xz"
    assert [path.name for path in result["receipts"]] == ["synthetic_environments.receipt.json",
                                                          "synthetic_feature_model.receipt.json"]
    expected = {item["feature_model"]: item for item in graph.evaluate()["feature_models"]}
    for path, documents in zip(result["receipts"], ([ENVIRONMENT_CONFIGURATIONS, ENVIRONMENTS],
                                                    [CONFIGURATION_DOCUMENT, MODEL])):
        replayed = receipts.replay(path, root)
        assert replayed["model_sources"] == documents
        (model,) = replayed["evaluation"]["feature_models"]
        assert replayed["feature_models"] == [model["feature_model"]]
        assert model == expected[model["feature_model"]]
        assert replayed["serializer"] == {**SERIALIZER, "bundle_git_commit": "a" * 40}
        assert replayed["qualified"] is False and replayed["native_expression_executed"] is False


def test_receipts_do_not_depend_on_the_checkout_or_the_library_location(tmp_path):
    """Two bundles that differ only in the resource paths of their URIs give the same receipts, byte for byte."""
    graph = two_family_graph(governed=True)
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


def test_the_receipts_command_writes_and_compares(tmp_path, monkeypatch, capsys):
    root = tmp_path / "tree"
    bundle = bundle_of(two_family_graph(), root)
    bundle.write(tmp_path / "bundle.json")
    monkeypatch.setattr(cli, "ROOT", root)
    arguments = ["receipts", "--bundle", str(tmp_path / "bundle.json"), "--serializer-version", "0.10.3",
                 "--executor-revision", "e" * 40]
    assert cli.main([*arguments, "--out", str(tmp_path / "first")]) == 0
    assert cli.main([*arguments, "--out", str(tmp_path / "second"), "--compare", str(tmp_path / "first")]) == 0
    edited = json.loads((tmp_path / "first/synthetic_feature_model.receipt.json").read_text())
    edited["elements"]["content_sha256"] = "0" * 64
    (tmp_path / "first/synthetic_feature_model.receipt.json").write_text(json.dumps(edited))
    capsys.readouterr()
    assert cli.main([*arguments, "--out", str(tmp_path / "third"), "--compare", str(tmp_path / "first")]) == 1
    assert "the fresh elements differ from the committed receipt's elements" in capsys.readouterr().out
    assert cli.main([*arguments, "--out", str(root / "inside")]) == 2


def test_a_bundle_whose_library_is_not_the_fenced_package_is_refused(tmp_path):
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
    graph = two_family_graph(environment_document=CONFIGURATION_DOCUMENT)
    with pytest.raises(ValueError, match="each model document belongs to one feature model; shared: "):
        cli.write_receipts(bundle_of(graph, tmp_path / "tree"), tmp_path / "out", serializer=SERIALIZER,
                           root=tmp_path / "tree")


def test_the_receipt_decides_admission_with_the_production_scope_reader(tmp_path, monkeypatch):
    graph = two_family_graph(governed=True)
    calls = []

    def validator(elements, sources):
        calls.append(len(elements))
        return graph.scope_record

    monkeypatch.setattr(receipts, "SCOPE_SOURCE", SCOPE)
    monkeypatch.setattr(receipts, "validate_scope_elements", validator)
    root = tmp_path / "tree"
    result = cli.write_receipts(bundle_of(graph, root), tmp_path / "out", serializer=SERIALIZER, root=root)
    platform = receipts.replay(result["receipts"][1], root)
    admitted = {item["configuration"]: item["admission"]["admitted"]
                for item in platform["evaluation"]["feature_models"][0]["configurations"]}
    assert admitted == {"member": True, "pair": False}
    assert platform["evaluation"]["admission_authority"] == SCOPE and calls


def test_without_the_governed_scope_the_receipt_does_not_decide_admission(tmp_path):
    payload = receipts.payload_from_bundle(bundle_of(two_family_graph(), tmp_path), serializer=SERIALIZER)
    assert receipts.governed_scope(payload) is None
    evaluation = receipts.evaluate_payload(payload)
    assert evaluation["admission_authority"] is None
    assert all(item["admission"]["evaluated"] is False
               for model in evaluation["feature_models"] for item in model["configurations"])


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
