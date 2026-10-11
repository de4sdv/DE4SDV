"""Ask-viewer deploy workflow: no bundle to declare, early refusal, rollback.

The workflow steps are executed for real (bash) with stub ``ssh``/``sudo``/
``docker`` binaries, so the tests observe behavior, not wording:

- the viewer serves the deployment binding's semantic authority after its
  startup check; there is no bundle id input (owner decision 2026-10-11);
- a revision from before that decision (its verifier still takes a bundle
  id) is refused BEFORE any host change, pointing at the rollback tag;
- the verify step passes no bundle id;
- the failure rollback brings the ask-viewer back from the restored checkout.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
WORKFLOW = REPO / ".github" / "workflows" / "deploy-public-ask-viewer.yml"
GUARD = "Refuse a pre-retirement revision before any host change"
VERIFY = "Verify the public reader path with one live grounded query"
ROLLBACK = "Roll back source, Ask service, and proxy after failure"
OPTION = "--expected-model-authority-bundle-id"


def _workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _steps() -> list[dict]:
    return _workflow()["jobs"]["deploy"]["steps"]


def _step(name: str) -> dict:
    return next(step for step in _steps() if step.get("name") == name)


def _stub(bin_dir: Path, name: str, body: str) -> None:
    path = bin_dir / name
    path.write_text("#!/usr/bin/env bash\n" + body, encoding="utf-8")
    path.chmod(0o755)


def _workspace(tmp_path: Path, *, pre_retirement_verifier: bool) -> dict:
    work = tmp_path / "work"
    (work / "deployment" / "scripts").mkdir(parents=True)
    option = f"    parser.add_argument('{OPTION}')\n" if pre_retirement_verifier else ""
    (work / "deployment" / "scripts" / "verify_public_ask.py").write_text(
        "import sys\n"
        "def main():\n"
        f"{option}"
        "    pass\n"
        "print('VERIFY-ARGS ' + ' '.join(sys.argv[1:]))\n",
        encoding="utf-8",
    )
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    ssh_log = tmp_path / "ssh.log"
    _stub(bin_dir, "ssh", f'echo "$@" >> "{ssh_log}"\n')
    _stub(bin_dir, "python3", 'echo "VERIFY-ARGS $*"\n')
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "DEPLOY_SHA": "a" * 40}
    return {"cwd": work, "env": env, "ssh_log": ssh_log}


def _run_step(name: str, ws: dict) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-e", "-o", "pipefail", "-c", _step(name)["run"]],
                          cwd=ws["cwd"], env=ws["env"], capture_output=True, text=True)


def test_there_is_no_bundle_id_input():
    triggers = _workflow().get("on", _workflow().get(True))
    assert set(triggers["workflow_dispatch"]["inputs"]) == {"git_sha"}
    text = WORKFLOW.read_text(encoding="utf-8")
    for retired in ("model_authority_bundle_id", "MODEL_AUTHORITY_BUNDLE_ID", "sysml2-api.env' || true"):
        assert retired not in text, retired


def test_the_guard_runs_before_any_host_change():
    names = [step.get("name") for step in _steps()]
    guard = names.index(GUARD)
    assert guard < names.index("Create source bundle and root-readable service environment")
    assert guard < names.index("Transfer and activate the fail-closed Ask service")


def test_a_pre_retirement_revision_is_refused_without_touching_the_host(tmp_path):
    ws = _workspace(tmp_path, pre_retirement_verifier=True)
    result = _run_step(GUARD, ws)
    assert result.returncode == 1
    assert "predates the release-ceremony retirement" in result.stdout
    assert "rollback tag" in result.stdout
    assert not ws["ssh_log"].exists()


def test_a_current_revision_passes_the_guard(tmp_path):
    ws = _workspace(tmp_path, pre_retirement_verifier=False)
    result = _run_step(GUARD, ws)
    assert result.returncode == 0, result.stdout + result.stderr


def test_the_verify_step_passes_no_bundle_id(tmp_path):
    ws = _workspace(tmp_path, pre_retirement_verifier=False)
    result = _run_step(VERIFY, ws)
    assert result.returncode == 0, result.stderr
    args = result.stdout.split("VERIFY-ARGS", 1)[1]
    assert "--application-sha " + "a" * 40 in args and "--live-query" in args
    assert OPTION not in args


# --- a failed deploy brings the previous ask-viewer back ---------------------------

def _rollback_remote_script() -> str:
    run = _step(ROLLBACK)["run"]
    start = run.index("<<'REMOTE'\n") + len("<<'REMOTE'\n")
    return run[start:run.rindex("REMOTE")]


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def test_rollback_restores_the_previous_checkout_and_recreates_the_ask_viewer(tmp_path):
    deploy_dir = tmp_path / "srv"
    repo_dir = deploy_dir / "DE4SDV"
    backup_dir = deploy_dir / "DE4SDV-ask-backup"
    for directory, marker in ((repo_dir, "failed"), (backup_dir, "previous")):
        directory.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(directory)], check=True)
        (directory / "marker").write_text(marker)
        _git(directory, "add", ".")
        _git(directory, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", marker)
    previous_sha = _git(backup_dir, "rev-parse", "HEAD")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker_log = tmp_path / "docker.log"
    _stub(bin_dir, "sudo", 'exec "$@"\n')
    # Record argv, the interpolated app SHA and whether stdin is a terminal-free
    # /dev/null (a compose call reading stdin would swallow the streamed script).
    _stub(bin_dir, "docker", (
        f'stdin=$(readlink /proc/$$/fd/0 || true)\n'
        f'echo "SHA=$DE4SDV_APP_GIT_SHA STDIN=$stdin ARGS=$*" >> "{docker_log}"\n'
    ))
    script = _rollback_remote_script().replace("/srv/de4sdv", str(deploy_dir))
    result = subprocess.run(["bash", "-s"], input=script, text=True, capture_output=True,
                            env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"})
    assert result.returncode == 0, result.stdout + result.stderr
    assert (repo_dir / "marker").read_text() == "previous"
    assert not backup_dir.exists()
    calls = docker_log.read_text().splitlines()
    # --build: the deploy path rebuilt the fixed image tag from the failed
    # revision, so the previous image must be rebuilt from the restored checkout.
    up_viewer = [c for c in calls if "up -d --build --no-deps ask-viewer" in c]
    assert len(up_viewer) == 1, calls
    assert f"SHA={previous_sha}" in up_viewer[0]
    assert f"-f {repo_dir}/deployment/compose.yaml" in up_viewer[0]
    assert calls.index(up_viewer[0]) > next(i for i, c in enumerate(calls) if "rm -sf ask-viewer" in c)
    assert calls.index(up_viewer[0]) < next(i for i, c in enumerate(calls) if "caddy" in c)
    for call in calls:
        assert "STDIN=/dev/null" in call, call
