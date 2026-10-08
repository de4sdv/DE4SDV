"""Ask-viewer deploy workflow: declared authority and rollback (review F1/F2).

The workflow steps are executed for real (bash) with stub ``ssh``/``sudo``/
``docker`` binaries, so the tests observe behavior, not wording:

- F1: a malformed or host-mismatched ``model_authority_bundle_id`` is refused
  BEFORE any host change; the failure rollback brings the ask-viewer back from
  the restored checkout.
- F2: a pre-C2 application revision (its verifier predates the option) skips
  the authority check with a visible warning, and the input is optional.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
WORKFLOW = REPO / ".github" / "workflows" / "deploy-public-ask-viewer.yml"
MAB = "mab-" + "1" * 32
PRECHECK = "Validate the declared semantic authority before any host change"
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


def _workspace(tmp_path: Path, *, c2_verifier: bool, host_env: str | None) -> dict:
    work = tmp_path / "work"
    (work / "deployment" / "scripts").mkdir(parents=True)
    option = f"    parser.add_argument('{OPTION}')\n" if c2_verifier else ""
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
    host_file = tmp_path / "host.env"
    if host_env is not None:
        host_file.write_text(host_env, encoding="utf-8")
    # The stub host answers the remote command by reading the fake env file
    # (the remote command is a grep of /srv/de4sdv/sysml2-api.env).
    _stub(bin_dir, "ssh", (
        f'echo "$@" >> "{ssh_log}"\n'
        f'remote="${{@: -1}}"\n'
        f'remote="${{remote//\\/srv\\/de4sdv\\/sysml2-api.env/{host_file}}}"\n'
        'remote="${remote//sudo /}"\n'
        'bash -c "$remote"\n'
    ))
    output = tmp_path / "github_output"
    output.write_text("", encoding="utf-8")
    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "GITHUB_OUTPUT": str(output),
        "DEPLOY_SSH_HOST": "host.invalid",
        "DEPLOY_SSH_USER": "deploy",
        "DEPLOY_SHA": "a" * 40,
    }
    return {"cwd": work, "env": env, "ssh_log": ssh_log, "output": output}


def _run_step(name: str, ws: dict, bundle_id: str) -> subprocess.CompletedProcess:
    env = {**ws["env"], "MODEL_AUTHORITY_BUNDLE_ID": bundle_id}
    return subprocess.run(["bash", "-e", "-o", "pipefail", "-c", _step(name)["run"]],
                          cwd=ws["cwd"], env=env, capture_output=True, text=True)


# --- F1: refuse early -------------------------------------------------------

def test_precheck_runs_before_any_host_change():
    names = [step.get("name") for step in _steps()]
    assert names.index(PRECHECK) < names.index("Transfer and activate the fail-closed Ask service")
    assert names.index(PRECHECK) < names.index("Create source bundle and root-readable service environment")


@pytest.mark.parametrize("host_env", [
    f"OTHER=1\nDE4SDV_MODEL_AUTHORITY_BUNDLE_ID={MAB}\n",
    f'DE4SDV_MODEL_AUTHORITY_BUNDLE_ID="{MAB}"\n',
    f"DE4SDV_MODEL_AUTHORITY_BUNDLE_ID=mab-{'9' * 32}\nDE4SDV_MODEL_AUTHORITY_BUNDLE_ID={MAB}\n",
])
def test_precheck_accepts_the_host_configured_id(tmp_path, host_env):
    ws = _workspace(tmp_path, c2_verifier=True, host_env=host_env)
    result = _run_step(PRECHECK, ws, MAB)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "authority_check=enforced" in ws["output"].read_text()


@pytest.mark.parametrize("bundle_id", ["", "mab-XYZ", "mab-" + "1" * 31, "legacy", MAB + " "])
def test_precheck_refuses_a_malformed_id_without_touching_the_host(tmp_path, bundle_id):
    ws = _workspace(tmp_path, c2_verifier=True, host_env=f"DE4SDV_MODEL_AUTHORITY_BUNDLE_ID={MAB}\n")
    result = _run_step(PRECHECK, ws, bundle_id)
    assert result.returncode != 0
    assert "::error::" in result.stdout
    assert not ws["ssh_log"].exists(), "no SSH before the format check passes"


@pytest.mark.parametrize("host_env", [
    f"DE4SDV_MODEL_AUTHORITY_BUNDLE_ID=mab-{'2' * 32}\n",   # stale host value
    "DE4SDV_SEMANTIC_AUTHORITY=legacy\n",                     # key missing
    "",                                                         # empty file
])
def test_precheck_refuses_an_id_that_differs_from_the_host(tmp_path, host_env):
    ws = _workspace(tmp_path, c2_verifier=True, host_env=host_env)
    result = _run_step(PRECHECK, ws, MAB)
    assert result.returncode != 0
    assert "::error::" in result.stdout
    assert "DE4SDV_MODEL_AUTHORITY_BUNDLE_ID" in result.stdout


# --- F2: pre-C2 revisions -----------------------------------------------------

def test_the_bundle_id_input_is_optional():
    inputs = _workflow()[True]["workflow_dispatch"]["inputs"]  # YAML 1.1: on -> True
    assert inputs["model_authority_bundle_id"]["required"] is False


@pytest.mark.parametrize("bundle_id", ["", MAB])
def test_precheck_skips_visibly_for_a_pre_c2_verifier(tmp_path, bundle_id):
    ws = _workspace(tmp_path, c2_verifier=False, host_env=None)
    result = _run_step(PRECHECK, ws, bundle_id)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "::warning::pre-C2 verifier: semantic-authority check skipped (input ignored)" in result.stdout
    assert "authority_check=skipped" in ws["output"].read_text()
    assert not ws["ssh_log"].exists()


def test_verify_step_passes_the_id_to_a_c2_verifier(tmp_path):
    ws = _workspace(tmp_path, c2_verifier=True, host_env=None)
    result = _run_step(VERIFY, ws, MAB)
    assert result.returncode == 0, result.stderr
    assert f"{OPTION} {MAB}" in result.stdout
    assert "::warning::" not in result.stdout


def test_verify_step_warns_for_a_pre_c2_verifier(tmp_path):
    ws = _workspace(tmp_path, c2_verifier=False, host_env=None)
    result = _run_step(VERIFY, ws, "")
    assert result.returncode == 0, result.stderr
    assert "::warning::pre-C2 verifier: semantic-authority check skipped (input ignored)" in result.stdout
    assert OPTION not in result.stdout.split("VERIFY-ARGS", 1)[1]


# --- F1: rollback brings the ask-viewer back ------------------------------------

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
