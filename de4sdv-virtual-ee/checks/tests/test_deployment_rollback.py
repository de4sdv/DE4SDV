"""update_with_rollback.sh, run for real against inspected local stubs.

Only `vxedge` and `podman` are replaced. The stubs record every call and model
the Podman behaviour the script depends on: `podman container inspect` prints a
JSON array, an unknown name or id fails with exit 125, and `podman exec` runs only
in a running container. The container a successful `vxedge experiment up` creates
gets a fresh id and the `ImageName` vxedge 0.30.0 creates payloads from: the
part's `ref@digest` (vxedge-core `Part::image_ref`).

These tests prove the script's verdict logic, not a live deployment: a real
vxedge daemon, Podman store and zone must be exercised on the testbed.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

CHECKS = Path(__file__).resolve().parents[1]
SCRIPT = CHECKS / "update_with_rollback.sh"
VEHICLE = CHECKS.parent / "vehicle"
ZONE = "vx-zone-rl-payload"
# Native scan receipt: the actual image independently bound to this baseline.
# Keep stubs on that identity when the reviewed payload is rebuilt.
RL_IMAGE = json.loads((CHECKS.parent / "sbom/inventory.json").read_text())["baseline_images"]["zone-ecu"]
OTHER_DIGEST_IMAGE = "localhost:5000/de4sdv/zone-ecu:10@sha256:" + "ab" * 32
FRAME_281 = "  vcan0  281   [8]  00 00 01 00 00 00 00 00"

VXEDGE_STUB = r'''#!/usr/bin/python3
import json, os, sys, uuid
args = sys.argv[1:]
state = os.environ["STUB_STATE"]
with open(os.path.join(state, "calls.log"), "a") as fh:
    fh.write("vxedge " + " ".join(args) + "\n")
if os.environ.get("STUB_FOREIGN") == "1":
    print("ERROR_REASON_WRONG_WORKSPACE: active run belongs to /srv/other/vehicle", file=sys.stderr)
    sys.exit(1)
verb = args[1]
pkg = os.path.basename(args[args.index("--chdir") + 1].rstrip("/"))
cpath = os.path.join(state, "container.json")
apath = os.path.join(state, "active")
active = open(apath).read() if os.path.exists(apath) else None
words = lambda key: os.environ.get(key, "").split()
if verb == "down":
    if active is None:
        sys.exit(0)
    if active != pkg:
        print("ERROR_REASON_WRONG_WORKSPACE", file=sys.stderr)
        sys.exit(1)
    os.remove(apath)
    if os.path.exists(cpath):
        os.remove(cpath)
    sys.exit(0)
if verb == "up":
    if pkg in words("STUB_UP_FAIL"):
        if pkg in words("STUB_FAILED_UP_LEAVES_HEALTHY"):
            c = json.load(open(cpath)) if os.path.exists(cpath) else {
                "Id": "leftover" + "0" * 56, "ImageName": os.environ["STUB_DEFAULT_IMAGE"], "Status": "running"}
            c["healthy"] = True
            json.dump(c, open(cpath, "w"))
        print("ERROR_REASON_NODES_NOT_UP: nodes not up: zone-rl", file=sys.stderr)
        sys.exit(1)
    if pkg in words("STUB_UP_NOOP"):
        sys.exit(0)
    json.dump({
        "Id": uuid.uuid4().hex + uuid.uuid4().hex,
        "ImageName": os.environ.get("STUB_IMAGE_" + pkg, os.environ["STUB_DEFAULT_IMAGE"]),
        "Status": "running",
        "healthy": pkg in words("STUB_HEALTHY"),
    }, open(cpath, "w"))
    open(apath, "w").write(pkg)
    sys.exit(0)
sys.exit(0)
'''

PODMAN_STUB = r'''#!/usr/bin/python3
import json, os, sys
args = sys.argv[1:]
state = os.environ["STUB_STATE"]
with open(os.path.join(state, "calls.log"), "a") as fh:
    fh.write("podman " + " ".join(args) + "\n")
name = "vx-zone-rl-payload"
cpath = os.path.join(state, "container.json")
c = json.load(open(cpath)) if os.path.exists(cpath) else None
if args[:2] == ["container", "inspect"] or args[:1] == ["inspect"]:
    target = args[-1]
    if c is None or target not in (c["Id"], name):
        print("Error: no such container " + target, file=sys.stderr)
        sys.exit(125)
    print(json.dumps([{
        "Id": c["Id"],
        "Name": name,
        "ImageName": c["ImageName"],
        "State": {"Status": c["Status"], "Running": c["Status"] == "running"},
    }], indent=4))
    sys.exit(0)
if args[:1] == ["exec"]:
    target = args[1]
    if c is None or target not in (c["Id"], name) or c["Status"] != "running":
        print('Error: no container with name or ID "%s" found: no such container' % target, file=sys.stderr)
        sys.exit(125)
    if c.get("healthy"):
        print(os.environ["STUB_FRAME"])
        sys.exit(0)
    sys.exit(124)  # candump found nothing; returns at once, the worst case for a deadline
sys.exit(0)
'''


def _package(root: Path, name: str) -> Path:
    pkg = root / name
    pkg.mkdir()
    for f in ("vehicle.yaml", "parts.yaml"):
        shutil.copy(VEHICLE / f, pkg / f)
    return pkg


@pytest.fixture
def bench(tmp_path):
    stubs = tmp_path / "bin"
    stubs.mkdir()
    for name, body in (("vxedge", VXEDGE_STUB), ("podman", PODMAN_STUB)):
        p = stubs / name
        p.write_text(body)
        p.chmod(0o755)
    state = tmp_path / "state"
    state.mkdir()
    pkgs = tmp_path / "pkgs"
    pkgs.mkdir()
    return {
        "state": state,
        "stubs": stubs,
        "candidate": _package(pkgs, "candidate"),
        "fallback": _package(pkgs, "fallback"),
    }


def seed_old_container(bench, healthy=True):
    """An older vehicle's zone with the same name, still running and publishing."""
    (bench["state"] / "container.json").write_text(
        json.dumps({"Id": "0ld" + "0" * 61, "ImageName": RL_IMAGE, "Status": "running", "healthy": healthy})
    )


def run(bench, timeout="2", **env):
    full = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
    full.update(
        PATH=f"{bench['stubs']}:{os.environ['PATH']}",
        STUB_STATE=str(bench["state"]),
        STUB_DEFAULT_IMAGE=RL_IMAGE,
        STUB_FRAME=FRAME_281,
        HEALTH_TIMEOUT=timeout,
        VXEDGE_ENDPOINT="unix:///nonexistent/vxedge.sock",
        PYTHONDONTWRITEBYTECODE="1",
    )
    full.update(env)
    start = time.monotonic()
    res = subprocess.run(
        ["sh", str(SCRIPT), str(bench["candidate"]), str(bench["fallback"])],
        capture_output=True, text=True, env=full, timeout=120,
    )
    res.elapsed = time.monotonic() - start
    res.calls = (bench["state"] / "calls.log").read_text().splitlines()
    return res


def test_foreign_active_workspace_refuses_candidate(bench):
    # R3: every vxedge call fails, but an old vehicle's zone of the same name answers.
    seed_old_container(bench)
    res = run(bench, STUB_FOREIGN="1")
    assert res.returncode == 3, res.stdout + res.stderr
    assert "accepted" not in res.stdout
    assert not [c for c in res.calls if c.startswith("podman exec")], res.calls


def test_stale_same_named_container_is_not_the_candidate(bench):
    # `up` returns success but nothing new was created: the zone that answers is old.
    seed_old_container(bench)
    res = run(bench, STUB_UP_NOOP="candidate fallback")
    assert res.returncode == 3, res.stdout + res.stderr
    assert "accepted" not in res.stdout


def test_candidate_image_must_carry_the_package_digest(bench):
    res = run(
        bench,
        STUB_HEALTHY="candidate fallback",
        STUB_IMAGE_candidate=OTHER_DIGEST_IMAGE,
        STUB_IMAGE_fallback=OTHER_DIGEST_IMAGE,
    )
    assert res.returncode == 3, res.stdout + res.stderr
    assert "accepted" not in res.stdout


def test_immediately_failing_probe_waits_the_real_deadline(bench):
    # R3: the old loop counted 2 s per probe without sleeping and gave up in ~0.04 s.
    res = run(bench, timeout="2")
    assert res.returncode == 3, res.stdout + res.stderr
    assert res.elapsed >= 4.0, f"two 2 s gates finished in {res.elapsed:.3f} s"
    probes = [c for c in res.calls if c.startswith("podman exec")]
    assert 2 <= len(probes) <= 16, probes  # backoff between attempts, not a busy loop


def test_rollback_up_failure_is_failure_even_if_a_zone_answers(bench):
    # The fallback's `up` fails and leaves a publishing zone behind: not a rollback.
    res = run(
        bench,
        STUB_UP_FAIL="fallback",
        STUB_FAILED_UP_LEAVES_HEALTHY="fallback",
    )
    assert res.returncode == 3, res.stdout + res.stderr
    assert "rolled back:" not in res.stdout


def test_candidate_accepted_on_its_own_fresh_container(bench):
    seed_old_container(bench, healthy=False)
    res = run(bench, STUB_HEALTHY="candidate")
    assert res.returncode == 0, res.stdout + res.stderr
    fresh = json.loads((bench["state"] / "container.json").read_text())["Id"]
    probes = [c for c in res.calls if c.startswith("podman exec")]
    assert probes and all(c.split()[2] == fresh for c in probes), probes


def test_unhealthy_candidate_rolls_back_to_fresh_fallback(bench):
    res = run(bench, STUB_HEALTHY="fallback")
    assert res.returncode == 2, res.stdout + res.stderr
    ups = [c for c in res.calls if " up " in c]
    assert [u.split()[-1].rsplit("/", 1)[-1] for u in ups] == ["candidate", "fallback"]
