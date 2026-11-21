"""The staging of the SDV Core interop keeps the services that the guest already carries.

The SDV Core stack config (vsomeip_config.json) is one file for every SOME/IP service the SDV
Core VM consumes. Staging replaces it, so a render that dropped 0x4dee (INC-MW-011's frame service)
or 0x4df0 (INC-DRIVING-001's operational state) would silently unconfigure them. The render must
keep both, unchanged, beside 0x4df1.

The staging is exercised on a synthetic AOSP tree in tmp_path: a few files with the shapes the
script edits (no platform text, no model text). The closed-loop driving bench's own stack-config
template stands in for what its staging (BUILD-PLAN S7) leaves in the tree.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = ROOT.parents[2]
SCRIPT = ROOT / "scripts" / "stage_sdv_core_interop.sh"
RENDER = ROOT / "scripts" / "render_stack_config.py"
TEMPLATE = ROOT / "interop" / "vsomeip_config.json"
CLOSED_LOOP_TEMPLATE = REPO / "implementation" / "closed-loop-driving-bench" / "ivi-observer" / "interop" / "vsomeip_config.json"
IDS = json.loads((ROOT.parent / "interfaces" / "service_ids.json").read_text(encoding="utf-8"))
PLACEHOLDER = "__SCORE_SOMEIP_PEER__"
PEER = "192.168.98.1"  # the model's S-CORE host address on the VXLAN segment
KEPT = [k["service_id"] for k in IDS["icd"]["someip_kept"]]
WARNING = IDS["icd"]["someip_warning_request"]["service_id"]
UNIT = IDS["icd"]["data_tunnel"]["service_unit"]
MESSAGE = IDS["icd"]["data_tunnel"]["message"]
PRIOR_MESSAGE = "de4sdv.driving.v1.DrivingOperationalState"


def _closed_loop_rendered(peer: str = PEER) -> dict:
    """What the closed-loop driving bench's staging writes: its template with the peer, and the
    acceptances of one address merged (written here independently of the scripts under test)."""
    config = json.loads(CLOSED_LOOP_TEMPLATE.read_text(encoding="utf-8").replace(PLACEHOLDER, peer))
    merged: dict[str, dict] = {}
    for acceptance in config["acceptances"]:
        merged.setdefault(acceptance["address"], {"address": acceptance["address"], "reliable": []})[
            "reliable"] += acceptance["reliable"]
    config["acceptances"] = list(merged.values())
    return config


def _env(**extra: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON") and k != "SCORE_SOMEIP_PEER"}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.update(extra)
    return env


def _services(config: dict) -> dict[str, dict]:
    return {s["service"]: s for s in config["services"]}


def test_template_carries_the_closed_loop_services_unchanged() -> None:
    mine = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    theirs = json.loads(CLOSED_LOOP_TEMPLATE.read_text(encoding="utf-8"))
    for service in KEPT:
        assert _services(mine)[service] == _services(theirs)[service]
    for key in ("unicast", "logging", "applications", "routing", "service-discovery"):
        assert mine[key] == theirs[key], key
    for entry in theirs["secure-services"]:
        assert entry in mine["secure-services"]
    for entry in theirs["acceptances"]:
        assert entry in mine["acceptances"]


def test_render_keeps_0x4dee_and_0x4df0_beside_0x4df1(tmp_path: Path) -> None:
    out = tmp_path / "vsomeip_config.json"
    result = subprocess.run(["bash", str(SCRIPT), "render", str(out)], capture_output=True, text=True,
                            env=_env(SCORE_SOMEIP_PEER=PEER, RUN_DIR=str(tmp_path / "run")))
    assert result.returncode == 0, result.stdout + result.stderr
    rendered = json.loads(out.read_text(encoding="utf-8"))
    services = _services(rendered)
    assert sorted(services) == sorted([*KEPT, WARNING])
    staged_before = _closed_loop_rendered()
    for service in KEPT:
        assert services[service] == _services(staged_before)[service]
    assert services[WARNING]["unicast"] == PEER
    assert {s["service"] for s in rendered["secure-services"]} == {*KEPT, WARNING}
    assert PLACEHOLDER not in out.read_text(encoding="utf-8")
    # One acceptance per address, the warning's port among the peer's.
    addresses = [a["address"] for a in rendered["acceptances"]]
    assert len(addresses) == len(set(addresses))
    (peer,) = [a for a in rendered["acceptances"] if a["address"] == PEER]
    assert {"first": "30511", "last": "30511", "type": "secure"} in peer["reliable"]


def test_render_refuses_a_template_without_a_kept_service(tmp_path: Path) -> None:
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    template["services"] = [s for s in template["services"] if s["service"] != "0x4df0"]
    broken = tmp_path / "template.json"
    broken.write_text(json.dumps(template), encoding="utf-8")
    result = subprocess.run(["python3", str(RENDER), "--template", str(broken), "--peer", PEER,
                             "--out", str(tmp_path / "out.json")], capture_output=True, text=True, env=_env())
    assert result.returncode != 0
    assert "lacks 0x4df0" in result.stderr and "Traceback" not in result.stderr
    assert not (tmp_path / "out.json").exists()


def test_render_refuses_to_change_a_service_the_tree_carries(tmp_path: Path) -> None:
    current = _closed_loop_rendered()
    _services(current)["0x4df0"]["reliable"]["port"] = "30599"
    path = tmp_path / "current.json"
    path.write_text(json.dumps(current), encoding="utf-8")
    result = subprocess.run(["python3", str(RENDER), "--template", str(TEMPLATE), "--peer", PEER,
                             "--current", str(path), "--out", str(tmp_path / "out.json")],
                            capture_output=True, text=True, env=_env())
    assert result.returncode != 0
    assert "0x4df0" in result.stderr


def test_render_needs_the_peer(tmp_path: Path) -> None:
    result = subprocess.run(["bash", str(SCRIPT), "render", str(tmp_path / "out.json")],
                            capture_output=True, text=True, env=_env(RUN_DIR=str(tmp_path / "run")))
    assert result.returncode != 0
    assert "SCORE_SOMEIP_PEER" in result.stdout + result.stderr
    assert not (tmp_path / "out.json").exists()


@pytest.fixture()
def tree(tmp_path: Path) -> Path:
    """A synthetic AOSP tree after the earlier increments' staging (BUILD-PLAN S6 and S7)."""
    top = tmp_path / "aosp"
    sdv = top / "system" / "software_defined_vehicle"
    catalog = sdv / "samples" / "some_ip" / "catalog"
    (catalog / "agent").mkdir(parents=True)
    (catalog / "Android.bp").write_text('srcs: ["**/*.proto"]\nsrcs: ["**/*.vsidl"]\n', encoding="utf-8")
    (catalog / "agent" / "broker.vsidl").write_text(
        'package: "com.android.sdv.someip"\n\nservice_bundle {\n  name: "SomeIpBroker"\n\n'
        '  publisher {\n    message: "com.example.SyntheticFrame"\n  }\n'
        f'  publisher {{\n    message: "{PRIOR_MESSAGE}"\n  }}\n}}\n', encoding="utf-8")
    acl = sdv / "samples" / "some_ip" / "config" / "broker_apex" / "someip_acl.textproto"
    acl.parent.mkdir(parents=True)
    acl.write_text('publisher {\n  message: "com.example.SyntheticFrame"\n  topic: "synthetic-frame"\n}\n\n'
                   f'publisher {{\n  message: "{PRIOR_MESSAGE}"\n  topic: "synthetic-state"\n}}\n',
                   encoding="utf-8")
    stack = sdv / "some_ip" / "vsomeip_stack"
    stack.mkdir(parents=True)
    (stack / "Android.bp").write_text('prebuilt_etc {\n    name: "vsomeip_config.json",\n}\n', encoding="utf-8")
    (stack / "vsomeip_config.json").write_text(json.dumps(_closed_loop_rendered(), indent=2) + "\n",
                                               encoding="utf-8")
    return top


def _snapshot(top: Path) -> dict[str, bytes]:
    return {str(p.relative_to(top)): p.read_bytes() for p in sorted(top.rglob("*")) if p.is_file()}


def test_stage_is_idempotent_and_revert_restores_the_tree(tree: Path, tmp_path: Path) -> None:
    env = _env(AOSP_TOP=str(tree), SCORE_SOMEIP_PEER=PEER, RUN_DIR=str(tmp_path / "run"))
    before = _snapshot(tree)
    sdv = tree / "system" / "software_defined_vehicle"
    catalog = sdv / "samples" / "some_ip" / "catalog"
    acl = sdv / "samples" / "some_ip" / "config" / "broker_apex" / "someip_acl.textproto"
    stack = sdv / "some_ip" / "vsomeip_stack" / "vsomeip_config.json"
    for _ in range(2):
        result = subprocess.run(["bash", str(SCRIPT), "stage"], capture_output=True, text=True, env=env)
        assert result.returncode == 0, result.stdout + result.stderr
        staged = catalog / "de4sdv_driver_assistance"
        assert sorted(p.name for p in staged.iterdir()) == [
            "de4sdv_driving_collision_warning_request.proto",
            "de4sdv_driving_collision_warning_request_someip.vsidl"]
        assert not (staged / "Android.bp").exists()
        assert (staged / "de4sdv_driving_collision_warning_request.proto").read_bytes() == (
            ROOT / "contract" / "de4sdv_driving_collision_warning_request.proto").read_bytes()
        broker = (catalog / "agent" / "broker.vsidl").read_text(encoding="utf-8")
        assert broker.count(f'message: "{MESSAGE}"') == 1
        assert broker.count(f'message: "{PRIOR_MESSAGE}"') == 1
        acl_text = acl.read_text(encoding="utf-8")
        assert acl_text.count(f'topic: "{UNIT}"') == 1
        assert acl_text.count(f'message: "{PRIOR_MESSAGE}"') == 1
        assert sorted(_services(json.loads(stack.read_text(encoding="utf-8")))) == sorted([*KEPT, WARNING])
    result = subprocess.run(["bash", str(SCRIPT), "revert"], capture_output=True, text=True, env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert _snapshot(tree) == before


def test_check_refuses_a_catalog_subdirectory_with_its_own_android_bp(tree: Path, tmp_path: Path) -> None:
    staged = tree / "system" / "software_defined_vehicle" / "samples" / "some_ip" / "catalog" / "de4sdv_driver_assistance"
    staged.mkdir()
    (staged / "Android.bp").write_text("// would cut the directory out of the catalog's glob\n", encoding="utf-8")
    result = subprocess.run(["bash", str(SCRIPT), "check"], capture_output=True, text=True,
                            env=_env(AOSP_TOP=str(tree), RUN_DIR=str(tmp_path / "run")))
    assert result.returncode != 0
    assert "Android.bp" in result.stdout + result.stderr


def test_shell_script_has_no_syntax_error() -> None:
    if shutil.which("bash") is None:
        pytest.skip("bash is not installed")
    assert subprocess.run(["bash", "-n", str(SCRIPT)]).returncode == 0
