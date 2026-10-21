"""The configurator, the product-model projection writer of the PLEML receipts (ADR 0022).

The writer of ``tools/configure_variant.py`` generates the projection of one
configuration of a committed PLEML receipt after replaying it offline. Each of
the seven committed projections regenerates from its receipt byte for byte.
The ordering and labelling rules of the receipt content are unit-tested on a
synthetic record, and the provenance helpers of the writer on synthetic
files.
"""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/configure_variant.py"
PLE = ROOT / "model-based-product-line-engineering"
RECEIPTS = PLE / "feature-models/receipts"
_SPEC = importlib.util.spec_from_file_location("_configure_variant_receipt_mode", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
configurator = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(configurator)


def _committed_projections() -> dict[str, Path]:
    """Each committed projection by the feature configuration its header names."""
    found = {}
    for projection in sorted((PLE / "product-models").glob("*.sysml")):
        match = re.search(r"^ \* Feature configuration: (\S+) \(", projection.read_text(encoding="utf-8"), re.MULTILINE)
        if match:
            found[match[1]] = projection
    return found


PROJECTIONS = _committed_projections()


def _receipt_of(document: str) -> Path:
    [path] = [path for path in sorted(RECEIPTS.glob("*.receipt.json"))
              if document in json.loads(path.read_text(encoding="utf-8"))["model_sources"]]
    return path


def _run(*arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *arguments], capture_output=True, text=True, cwd=ROOT,
                          check=False, timeout=120)


def test_seven_committed_projections_name_their_configuration() -> None:
    from scripts import run_ple_authority as runner

    assert sorted(PROJECTIONS) == sorted(runner.CONFIGURATIONS)


@pytest.mark.parametrize("document", sorted(PROJECTIONS), ids=lambda document: Path(document).stem)
def test_each_committed_projection_regenerates_from_its_receipt(document: str, tmp_path: Path) -> None:
    receipt = _receipt_of(document)
    output = tmp_path / "projection.sysml"
    result = _run("--receipt", str(receipt), "--configuration", document, "--output", str(output))
    assert result.returncode == 0, result.stderr
    text = output.read_text(encoding="utf-8")
    assert text == PROJECTIONS[document].read_text(encoding="utf-8")
    assert f" * Receipt: {receipt.relative_to(ROOT).as_posix()}\n" in text
    assert f" * Feature configuration: {document} (" in text
    assert "projection from PLEML configuration receipt." in text


def test_the_configurator_names_a_configuration_three_ways() -> None:
    receipt = RECEIPTS / "sdv_product_line.receipt.json"
    texts = {name: _run("--receipt", str(receipt), "--configuration", name).stdout
             for name in ("aebsAutowareLinuxLidarCamera", "AEBSAutowareLinuxLidarCamera",
                          "model-based-product-line-engineering/feature-configurations/"
                          "aebs_autoware_linux_lidar_camera.sysml")}
    assert len(set(texts.values())) == 1 and "part def AEBSAutowareLinuxLidarCamera :> SDVPlatformStack {" in (
        next(iter(texts.values())))


def test_the_configurator_refuses_an_invalid_configuration() -> None:
    result = _run("--receipt", str(RECEIPTS / "sdv_product_line.receipt.json"), "--configuration",
                  "invalidSCOREAndroidVariant", "--check-only")
    assert result.returncode == 1
    assert "1 violation(s) in the receipt" in result.stderr and "Traceback" not in result.stderr


def test_the_configurator_projects_exactly_the_member_configurations() -> None:
    """The receipts evaluate the member configurations, the invalid fixture and the
    probes; the configurator projects only a configuration of the served model,
    one per committed projection, and never a fixture (#411 R5)."""
    from scripts import run_ple_authority as runner

    sources = {configuration["source"]
               for path in sorted(RECEIPTS.glob("*.receipt.json"))
               for model in json.loads(path.read_text(encoding="utf-8"))["evaluation"]["feature_models"]
               for configuration in model["configurations"]}
    served = {source for source in sources if configurator.served_configuration({"source": source})}
    assert served == set(runner.CONFIGURATIONS) == set(PROJECTIONS)
    assert sources - served == set(runner.FIXTURES)
    assert len(served) == 7 and len(runner.FIXTURES) == 18


@pytest.mark.parametrize("name", ["radarOnlySensingProbe", "invalidSCOREAndroidVariant"])
def test_the_configurator_never_projects_a_fixture(name: str, tmp_path: Path) -> None:
    output = tmp_path / "projection.sysml"
    result = _run("--receipt", str(RECEIPTS / "sdv_product_line.receipt.json"), "--configuration", name,
                  "--output", str(output))
    assert result.returncode == 2, result.stderr
    assert f"'{name}' is a fixture of the receipt" in result.stderr and "Traceback" not in result.stderr
    assert not output.exists()


def test_the_configurator_checks_a_fixture_without_projecting_it() -> None:
    result = _run("--receipt", str(RECEIPTS / "sdv_product_line.receipt.json"), "--configuration",
                  "radarOnlySensingProbe", "--check-only")
    assert result.returncode == 0 and "the receipt replays" in result.stderr
    assert result.stdout == ""


def test_the_configurator_checks_without_writing(tmp_path: Path) -> None:
    output = tmp_path / "projection.sysml"
    result = _run("--receipt", str(RECEIPTS / "vehicle_execution_environments.receipt.json"), "--configuration",
                  "nxpZephyrVehicleTargetCandidate", "--check-only", "--output", str(output))
    assert result.returncode == 0 and "the receipt replays" in result.stderr
    assert not output.exists()


def test_the_configurator_refuses_a_receipt_that_does_not_hold(tmp_path: Path) -> None:
    """An edited verdict over the genuine elements does not reproduce; the writer never reads it."""
    shutil.copytree(RECEIPTS, tmp_path / "receipts")
    path = tmp_path / "receipts/vehicle_execution_environments.receipt.json"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    receipt["evaluation"]["feature_models"][0]["configurations"][0]["derived_variants"][0]["variant"] = "other"
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = _run("--receipt", str(path), "--configuration", "nxpZephyrVehicleTargetCandidate")
    assert result.returncode == 2
    assert "the receipt does not hold" in result.stderr and "Traceback" not in result.stderr


def test_the_configurator_refuses_an_unknown_configuration() -> None:
    result = _run("--receipt", str(RECEIPTS / "sdv_product_line.receipt.json"), "--configuration", "noSuchOne")
    assert result.returncode == 2 and "holds 0 configurations named 'noSuchOne'" in result.stderr


@pytest.mark.parametrize("arguments", [
    ("--receipt", "receipt.json"),
    ("--configuration", "aebsAutowareLinuxLidarCamera"),
    ("--receipt", "receipt.json", "--configuration", "x", "--bof", "bill.yaml"),
    ("--receipt", "receipt.json", "--configuration", "x", "--feature-model", "catalogue.yaml"),
    ("--receipt", "receipt.json", "--configuration", "x", "--shared-assets-model", "assets.sysml"),
    ("--bof", "bill.yaml"),
])
def test_the_configurator_takes_a_receipt_and_a_configuration_only(arguments: tuple[str, ...]) -> None:
    """The YAML path retired at S7: a catalogue or a Bill-of-Features is a usage error."""
    result = _run(*arguments)
    assert result.returncode == 2 and "usage:" in result.stderr and "Traceback" not in result.stderr


# -- the receipt content (synthetic record) -----------------------------------------------------------


def _synthetic():
    features = [
        {"path": "stack", "name": "stack", "group": None, "members": []},
        {"path": "stack.os", "name": "os", "group": None, "members": ["stack.linux", "stack.qnx"]},
        {"path": "stack.linux", "name": "linux", "group": "stack.os", "members": []},
        {"path": "stack.qnx", "name": "qnx", "group": "stack.os", "members": []},
        {"path": "stack.sensors", "name": "sensors", "group": None,
         "members": ["stack.lidar", "stack.radar", "stack.camera"]},
        {"path": "stack.lidar", "name": "lidar", "group": "stack.sensors", "members": []},
        {"path": "stack.radar", "name": "radar", "group": "stack.sensors", "members": []},
        {"path": "stack.camera", "name": "camera", "group": "stack.sensors", "members": []},
        {"path": "stack.app", "name": "app", "group": None, "members": ["stack.alpha"]},
        {"path": "stack.alpha", "name": "alpha", "group": "stack.app", "members": []},
        {"path": "stack.extra", "name": "extra", "group": None, "members": []},
    ]
    model = {
        "features": features,
        "bindings": [{"binding": "osLinux", "feature": "stack.linux"}, {"binding": "osQNX", "feature": "stack.qnx"},
                     {"binding": "appAlpha", "feature": "stack.alpha"}],
        "derivations": [{"derivation": "adapterDerivation", "short_name": "D-ASSET-ADAPTER", "element_id": "d"}],
    }
    configuration = {
        "states": {"stack": "enabled", "stack.os": "enabled", "stack.linux": "omitted", "stack.qnx": "enabled",
                   "stack.sensors": "implied", "stack.lidar": "enabled", "stack.radar": "omitted",
                   "stack.camera": "enabled", "stack.app": "enabled", "stack.alpha": "enabled",
                   "stack.extra": "disabled"},
        # Sorted by variation, as the evaluator records them.
        "derived_variants": [
            {"variation": "adapter", "variant": "none", "rule": "r", "derivation": "D-ASSET-ADAPTER"},
            {"variation": "application", "variant": "alpha", "binding": "appAlpha"},
            {"variation": "osPlatform", "variant": "qnx", "binding": "osQNX"},
        ],
    }
    writer = {"explicit_optional_states": {"stack.extra": "disabled"}}
    return model, configuration, writer


def test_the_receipt_content_orders_the_variants_and_the_selections_outside_the_projection() -> None:
    """Bound variants by the tree order of their groups, derived ones after them; unbound groups, then
    optional features set explicitly, each labelled by its PLEML feature path and its members by name."""
    redefinitions, derived, annotations = configurator.receipt_projection_content(*_synthetic())
    assert redefinitions == [("osPlatform", "qnx"), ("application", "alpha"), ("adapter", "none")]
    assert derived == {"adapter": "D-ASSET-ADAPTER"}
    assert annotations == [("stack.sensors", "lidar, camera"), ("stack.extra", "disabled")]


def test_the_selections_outside_a_committed_projection_are_feature_paths_of_its_receipt() -> None:
    """Each label line of a committed projection names a feature of its receipt's feature model."""
    for document, projection in PROJECTIONS.items():
        receipt = json.loads(_receipt_of(document).read_text(encoding="utf-8"))
        [model] = [model for model in receipt["evaluation"]["feature_models"]
                   if document in {item["source"] for item in model["configurations"]}]
        paths = {feature["path"] for feature in model["features"]}
        text = projection.read_text(encoding="utf-8")
        block = text.split("Feature selections outside this projection (not resolved in SysML):\n", 1)
        if len(block) == 1:
            continue
        labels = re.findall(r"^   \*   (\S+) = ", block[1].split("   */", 1)[0], re.MULTILINE)
        assert labels and set(labels) <= paths, (document, set(labels) - paths)


# -- the provenance helpers of the writer ------------------------------------------------------------


def test_comment_data_cannot_close_the_generated_comment() -> None:
    """The writer escapes the description, the label, the source and the selections it prints; the
    provenance lines arrive escaped from the caller (``receipt_projection``)."""
    assert configurator.sysml_comment_text("safe */ } part def Injected {} /* trailing\x01") == (
        "safe * / } part def Injected {} / * trailing?")
    text = configurator.render_projection(
        "SafeVariant", "safe */\n} part def Injected {}\n/* trailing",
        {"package": "P", "owner": "Owner", "label": "platform-*/stack"}, [("part", "variant")], {"part": "D-*/"},
        [("group */", "a */ b")], ["provenance"], "source */")
    assert "safe * /" in text and "/ * trailing" in text and "platform-* /stack" in text
    assert "group * / = a * / b" in text and "variant (derived by D-* /)" in text and "from source * /." in text
    assert text.count("*/") == 2, text


def test_a_shared_asset_inside_the_repository_is_identified_by_its_bytes() -> None:
    path = ROOT / "textual-notation-of-model/packages/architecture/sdv_platform_stack.sysml"
    blob = subprocess.check_output(["git", "-C", str(ROOT), "hash-object", "--stdin"],
                                   input=path.read_bytes()).decode().strip()
    assert configurator.shared_asset_baseline(path) == (
        f"git-blob:{blob}:textual-notation-of-model/packages/architecture/sdv_platform_stack.sysml "
        "(content-addressed)")
    assert configurator.provenance_path(path) == "textual-notation-of-model/packages/architecture/sdv_platform_stack.sysml"


def test_a_shared_asset_outside_the_repository_has_no_repository_baseline(tmp_path: Path) -> None:
    path = tmp_path / "source*" / "stack.sysml"
    path.parent.mkdir()
    path.write_text("package P {}\n", encoding="utf-8")
    assert configurator.shared_asset_baseline(path) == f"external:{path.resolve()} (content hash authoritative)"
    assert configurator.provenance_path(path) == str(path.resolve())
    assert "source* /stack.sysml" in configurator.sysml_comment_text(configurator.provenance_path(path))
