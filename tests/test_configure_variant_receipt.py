"""The configurator's receipt mode (ADR 0022, plan step S4).

The writer of ``tools/configure_variant.py`` generates the projection of one
configuration of a committed PLEML receipt after replaying it offline. The
gate of the step: each of the seven committed projections, which the YAML
path generated, has the same normalised body (plan section 5) as the
receipt's projection of its configuration. The ordering rules of the receipt
content are unit-tested on a synthetic record.
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

from de4sdv.semantic import pleml_receipts as receipts

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/configure_variant.py"
PLE = ROOT / "model-based-product-line-engineering"
RECEIPTS = PLE / "feature-models/receipts"
_SPEC = importlib.util.spec_from_file_location("_configure_variant_receipt_mode", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
configurator = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(configurator)


def _committed_projections() -> dict[str, Path]:
    """Each committed projection by the bill of features its header names."""
    found = {}
    for projection in sorted((PLE / "product-models").glob("*.sysml")):
        match = re.search(r"^ \* Regenerate from: (.+)$", projection.read_text(encoding="utf-8"), re.MULTILINE)
        if match:
            found[match.group(1).strip()] = projection
    return found


PROJECTIONS = _committed_projections()


def _receipt_of(document: str) -> Path:
    [path] = [path for path in sorted(RECEIPTS.glob("*.receipt.json"))
              if document in json.loads(path.read_text(encoding="utf-8"))["model_sources"]]
    return path


def _configuration_of(bill: str) -> str:
    path = Path(bill)
    return path.with_name(path.stem.replace("-", "_") + ".sysml").as_posix()


def _run(*arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *arguments], capture_output=True, text=True, cwd=ROOT,
                          check=False, timeout=120)


def test_seven_committed_projections_are_generated_by_the_yaml_path() -> None:
    assert len(PROJECTIONS) == 7


@pytest.mark.parametrize("bill", sorted(PROJECTIONS), ids=lambda bill: Path(bill).stem)
def test_the_receipt_projection_has_the_committed_body(bill: str, tmp_path: Path) -> None:
    document = _configuration_of(bill)
    receipt = _receipt_of(document)
    output = tmp_path / "projection.sysml"
    result = _run("--receipt", str(receipt), "--configuration", document, "--output", str(output))
    assert result.returncode == 0, result.stderr
    text = output.read_text(encoding="utf-8")
    assert receipts.normalised_body(text) == receipts.normalised_body(PROJECTIONS[bill].read_text(encoding="utf-8"))
    assert f" * Receipt: {receipt.relative_to(ROOT).as_posix()}\n" in text
    assert f" * Feature configuration: {document} (" in text
    assert "projection from PLEML configuration receipt." in text


def test_the_receipt_mode_names_a_configuration_three_ways() -> None:
    receipt = RECEIPTS / "sdv_product_line.receipt.json"
    texts = {name: _run("--receipt", str(receipt), "--configuration", name).stdout
             for name in ("aebsAutowareLinuxLidarCamera", "AEBSAutowareLinuxLidarCamera",
                          "model-based-product-line-engineering/feature-configurations/"
                          "aebs_autoware_linux_lidar_camera.sysml")}
    assert len(set(texts.values())) == 1 and "part def AEBSAutowareLinuxLidarCamera :> SDVPlatformStack {" in (
        next(iter(texts.values())))


def test_the_receipt_mode_refuses_an_invalid_configuration() -> None:
    result = _run("--receipt", str(RECEIPTS / "sdv_product_line.receipt.json"), "--configuration",
                  "invalidSCOREAndroidVariant", "--check-only")
    assert result.returncode == 1
    assert "1 violation(s) in the receipt" in result.stderr and "Traceback" not in result.stderr


def test_the_receipt_mode_checks_without_writing(tmp_path: Path) -> None:
    output = tmp_path / "projection.sysml"
    result = _run("--receipt", str(RECEIPTS / "vehicle_execution_environments.receipt.json"), "--configuration",
                  "nxpZephyrVehicleTargetCandidate", "--check-only", "--output", str(output))
    assert result.returncode == 0 and "the receipt replays" in result.stderr
    assert not output.exists()


def test_the_receipt_mode_refuses_a_receipt_that_does_not_hold(tmp_path: Path) -> None:
    """An edited verdict over the genuine elements does not reproduce; the writer never reads it."""
    shutil.copytree(RECEIPTS, tmp_path / "receipts")
    path = tmp_path / "receipts/vehicle_execution_environments.receipt.json"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    receipt["evaluation"]["feature_models"][0]["configurations"][0]["derived_variants"][0]["variant"] = "other"
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = _run("--receipt", str(path), "--configuration", "nxpZephyrVehicleTargetCandidate")
    assert result.returncode == 2
    assert "the receipt does not hold" in result.stderr and "Traceback" not in result.stderr


def test_the_receipt_mode_refuses_an_unknown_configuration() -> None:
    result = _run("--receipt", str(RECEIPTS / "sdv_product_line.receipt.json"), "--configuration", "noSuchOne")
    assert result.returncode == 2 and "holds 0 configurations named 'noSuchOne'" in result.stderr


@pytest.mark.parametrize("arguments", [
    ("--receipt", "receipt.json"),
    ("--configuration", "aebsAutowareLinuxLidarCamera"),
    ("--receipt", "receipt.json", "--configuration", "x", "--bof", "bill.yaml"),
    ("--receipt", "receipt.json", "--configuration", "x", "--shared-assets-model", "assets.sysml"),
    ("--bof", "bill.yaml"),
])
def test_the_two_modes_take_their_own_arguments(arguments: tuple[str, ...]) -> None:
    result = _run(*arguments)
    assert result.returncode == 2 and "usage:" in result.stderr and "Traceback" not in result.stderr


# -- the receipt content (synthetic record) -----------------------------------------------------------


def _synthetic():
    features = [
        {"path": "stack", "group": None, "members": []},
        {"path": "stack.os", "group": None, "members": ["stack.linux", "stack.qnx"]},
        {"path": "stack.linux", "group": "stack.os", "members": []},
        {"path": "stack.qnx", "group": "stack.os", "members": []},
        {"path": "stack.sensors", "group": None, "members": ["stack.lidar", "stack.radar", "stack.camera"]},
        {"path": "stack.lidar", "group": "stack.sensors", "members": []},
        {"path": "stack.radar", "group": "stack.sensors", "members": []},
        {"path": "stack.camera", "group": "stack.sensors", "members": []},
        {"path": "stack.app", "group": None, "members": ["stack.alpha"]},
        {"path": "stack.alpha", "group": "stack.app", "members": []},
        {"path": "stack.extra", "group": None, "members": []},
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
    writer = {"catalogue_paths": {"stack": "Stack", "stack.os": "Stack.OS", "stack.linux": "Stack.OS.Linux",
                                  "stack.qnx": "Stack.OS.QNX", "stack.sensors": "Stack.Sensors",
                                  "stack.lidar": "Stack.Sensors.LiDAR", "stack.radar": "Stack.Sensors.Radar",
                                  "stack.camera": "Stack.Sensors.Camera", "stack.app": "Stack.App",
                                  "stack.alpha": "Stack.App.Alpha", "stack.extra": "Stack.Extra"},
              "explicit_optional_states": {"stack.extra": "disabled"}}
    return model, configuration, writer


def test_the_receipt_content_orders_as_the_writer_does_for_a_bill_of_features() -> None:
    """Bound variants by the tree order of their groups, derived ones after them; unbound groups, then
    optional features set explicitly, by catalogue path."""
    redefinitions, derived, annotations = configurator.receipt_projection_content(*_synthetic())
    assert redefinitions == [("osPlatform", "qnx"), ("application", "alpha"), ("adapter", "none")]
    assert derived == {"adapter": "D-ASSET-ADAPTER"}
    assert annotations == [("Stack.Sensors", "LiDAR, Camera"), ("Stack.Extra", "disabled")]


def test_the_receipt_content_refuses_a_feature_without_a_catalogue_path() -> None:
    model, configuration, writer = _synthetic()
    del writer["catalogue_paths"]["stack.sensors"]
    with pytest.raises(ValueError, match="no catalogue path for stack.sensors"):
        configurator.receipt_projection_content(model, configuration, writer)
