"""R2/R8 in the run scripts: required steps propagate, identity binds the run.

The real checks/run_demo.sh and checks/run_backbone.sh run from a committed
scratch checkout against tests/fakebench.py (podman, vxedge, sudo, client,
UDS tool). Nothing here touches a container or a vehicle.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
CHECKS = TESTS.parent
SCOPE_SRC = CHECKS.parent
FAKE = TESTS / "fakebench.py"
PY = "/usr/bin/python3"
GIT_ENV = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid",
    "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
}


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True,
                          env={**os.environ, **GIT_ENV}).stdout.strip()


@pytest.fixture
def bench(tmp_path):
    top = tmp_path / "repo"
    top.mkdir()
    shutil.copytree(SCOPE_SRC, top / "de4sdv-virtual-ee",
                    ignore=shutil.ignore_patterns("results", "__pycache__", ".pytest_cache", "ota-store"))
    (top / ".gitignore").write_text("__pycache__/\n*.py[cod]\n")
    git(top, "init", "-q", "-b", "main")
    git(top, "add", "-A")
    git(top, "commit", "-q", "-m", "fixture")
    scope = top / "de4sdv-virtual-ee"
    (scope / "vehicle/ota-store").mkdir()
    (scope / "vehicle/ota-store/root.json").write_text("{}\n")  # runtime state, untracked

    bindir = tmp_path / "bin"
    bindir.mkdir()
    for tool in ("podman", "vxedge", "sudo", "sleep", "tcpdump", "vxota", "client", "uds"):
        path = bindir / tool
        path.write_text(f'#!/bin/sh\nexec {PY} {FAKE} {tool} "$@"\n')
        path.chmod(0o755)
    state = tmp_path / "state"
    state.mkdir()
    uds_tool = tmp_path / "udsTool.py"
    uds_tool.write_text("# fake UdsTool\n")
    uds_cfg = tmp_path / "canConfig.json"
    uds_cfg.write_text("{}\n")
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
    env.update(GIT_ENV)
    env.update(
        PATH=f"{bindir}:/usr/bin:/bin",
        PYTHONDONTWRITEBYTECODE="1",
        FAKE_STATE=str(state),
        VXEDGE_ENDPOINT="unix:///fake/vxedge.sock",
        HOST_PY=PY,
        CLIENT_PY=str(bindir / "client"),
        UDS_PY=str(bindir / "uds"),
        UDS_TOOL=str(uds_tool),
        UDS_CFG=str(uds_cfg),
    )
    return {"top": top, "scope": scope, "state": state, "env": env, "tmp": tmp_path}


def run_script(bench, name: str, **fault) -> subprocess.CompletedProcess:
    env = {**bench["env"], **{k: str(v) for k, v in fault.items()}}
    return subprocess.run(["bash", str(bench["scope"] / "checks" / name), "--duration", "1"],
                          capture_output=True, text=True, env=env, timeout=240)


def calls(bench) -> list[list[str]]:
    path = bench["state"] / "calls"
    return [json.loads(ln) for ln in path.read_text().splitlines()] if path.exists() else []


def provisioned(bench) -> bool:
    return any(c[:3] == ["vxedge", "experiment", "up"] for c in calls(bench))


def archives(bench) -> list[Path]:
    results = bench["scope"] / "results"
    return sorted(p for p in results.iterdir() if p.is_dir()) if results.exists() else []


def check_archive(bench, archive: Path) -> subprocess.CompletedProcess:
    return subprocess.run([PY, str(CHECKS / "run_identity.py"), "check-archive", "--repo", str(bench["top"]),
                           str(archive)], capture_output=True, text=True, env=bench["env"])


# --- run_demo.sh ------------------------------------------------------------------


def test_demo_passes_on_a_working_bench_with_a_full_identity(bench):
    proc = run_script(bench, "run_demo.sh")
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-3000:]
    [archive] = archives(bench)
    manifest = json.loads((archive / "manifest.json").read_text())
    head = git(bench["top"], "rev-parse", "HEAD")
    assert manifest["git_head"] == head and manifest["git_sha"] == head
    assert manifest["git_tree"] == git(bench["top"], "rev-parse", "HEAD^{tree}")
    assert archive.name.endswith(head[:12])
    assert json.loads((archive / "identity-after.json").read_text())["matches"] is True
    summary = json.loads((archive / "summary.json").read_text())
    assert summary["scenario"] == "alternating-8" and summary["verdict"]["pass"] is True
    assert len((archive / "commands.jsonl").read_text().splitlines()) == 16
    proc = check_archive(bench, archive)
    assert proc.returncode == 0, proc.stderr


def test_demo_refuses_a_dirty_scope_before_provisioning(bench):
    (bench["scope"] / "vehicle/parts.yaml").write_text("# local edit\n")
    proc = run_script(bench, "run_demo.sh")
    assert proc.returncode != 0, "a dirty checkout ran"
    assert "vehicle/parts.yaml" in proc.stderr
    assert not provisioned(bench)


def test_demo_refuses_a_gitless_copy_with_a_git_sha(bench):
    shutil.rmtree(bench["top"] / ".git")
    (bench["scope"] / ".git-sha").write_text("5495a2de\n")
    proc = run_script(bench, "run_demo.sh")
    assert proc.returncode != 0, "a .git-sha copy ran as provenance"
    assert "not a git checkout" in proc.stderr
    assert not provisioned(bench)


def test_demo_fails_when_an_input_changes_during_the_run(bench):
    proc = run_script(bench, "run_demo.sh", FAKE_MUTATE_ON_UP=bench["scope"] / "vehicle/vehicle.yaml")
    assert proc.returncode != 0, "a mid-run input change passed"
    assert "vehicle/vehicle.yaml" in proc.stdout + proc.stderr
    [archive] = archives(bench)
    assert json.loads((archive / "identity-after.json").read_text())["matches"] is False


@pytest.mark.parametrize("capture", ["demo-fl", "demo-gwr"])
def test_demo_fails_when_a_capture_copy_fails(bench, capture):
    proc = run_script(bench, "run_demo.sh", FAKE_COPY_FAIL=capture)
    assert proc.returncode != 0, f"a failed copy of {capture} passed"
    assert "capture copy failed" in proc.stdout + proc.stderr and capture in proc.stdout + proc.stderr


def test_demo_fails_when_a_capture_process_fails(bench):
    proc = run_script(bench, "run_demo.sh", FAKE_CAPTURE_RC=1)
    assert proc.returncode != 0, "candump failing in every zone passed"
    assert "capture" in proc.stdout + proc.stderr and "exited 1" in proc.stdout + proc.stderr


def test_demo_stops_when_priming_fails(bench):
    proc = run_script(bench, "run_demo.sh", FAKE_PRIME_FAIL=1)
    assert proc.returncode != 0, "a run whose priming failed went on"
    assert "prime" in proc.stderr
    assert not (bench["state"] / "driven.jsonl").exists()


def test_demo_fails_when_the_uds_tool_fails(bench):
    proc = run_script(bench, "run_demo.sh", FAKE_UDS_RC=3)
    assert proc.returncode != 0, "a failing UdsTool passed"
    assert "UdsTool exited 3" in proc.stdout + proc.stderr


def test_demo_refuses_a_missing_uds_tool(bench):
    proc = run_script(bench, "run_demo.sh", UDS_TOOL=bench["tmp"] / "absent.py")
    assert proc.returncode != 0, "a run without its diagnostic tool passed"
    assert "uds_tool" in proc.stderr
    assert not provisioned(bench)


# --- run_backbone.sh --------------------------------------------------------------


def test_backbone_passes_on_a_working_bench_with_a_full_identity(bench):
    proc = run_script(bench, "run_backbone.sh")
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-3000:]
    [archive] = archives(bench)
    manifest = json.loads((archive / "manifest.json").read_text())
    assert manifest["git_head"] == git(bench["top"], "rev-parse", "HEAD")
    assert json.loads((archive / "identity-after.json").read_text())["matches"] is True
    proc = check_archive(bench, archive)
    assert proc.returncode == 0, proc.stderr


def test_backbone_refuses_a_dirty_scope_before_provisioning(bench):
    (bench["scope"] / "checks/backbone_measure.py").write_text("print('ok')\n")
    proc = run_script(bench, "run_backbone.sh")
    assert proc.returncode != 0
    assert "checks/backbone_measure.py" in proc.stderr
    assert not provisioned(bench)


def test_backbone_fails_when_an_input_changes_during_the_run(bench):
    proc = run_script(bench, "run_backbone.sh", FAKE_MUTATE_ON_UP=bench["scope"] / "vehicle/parts.yaml")
    assert proc.returncode != 0
    assert "vehicle/parts.yaml" in proc.stdout + proc.stderr


def test_backbone_fails_when_a_log_cannot_be_collected(bench):
    proc = run_script(bench, "run_backbone.sh", FAKE_LOGS_FAIL="vx-zone-fl-payload")
    assert proc.returncode != 0
    assert "provider log" in proc.stdout + proc.stderr


def test_old_archives_are_left_byte_identical_by_the_scripts():
    """The scripts write a new archive per run; nothing in results/ is rewritten."""
    digests = {str(p.relative_to(SCOPE_SRC)): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in sorted((SCOPE_SRC / "results").rglob("*")) if p.is_file()}
    committed = git(SCOPE_SRC, "ls-files", "-s", "results")
    assert committed  # results are tracked
    for line in committed.splitlines():
        meta, path = line.split("\t", 1)
        blob = meta.split()[1]
        disk = SCOPE_SRC / path
        data = disk.read_bytes()
        assert hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest() == blob, path
    assert digests
