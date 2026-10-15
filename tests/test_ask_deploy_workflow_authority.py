"""Ask-viewer deploy workflow: no bundle to declare, early refusal, rollback.

The workflow steps are executed for real (bash) with stub ``ssh``/``sudo``/
``docker`` binaries, so the tests observe behavior, not wording:

- the viewer serves the deployment binding's semantic authority after its
  startup check; there is no bundle id input (owner decision 2026-10-11);
- a revision from before that decision (its verifier still takes a bundle
  id) is refused BEFORE any host change, pointing at the rollback tag;
- the verify step passes no bundle id;
- the failure rollback brings the ask-viewer back from the restored checkout;
- the warm-up wait stops at the server's ``error`` state with its reason,
  treats an unreadable probe answer as ``starting``, names the state the
  producer (``ask_model_semantic``) reports after a failed warm-up, and a
  warm-up error rolls the previous checkout back.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
WORKFLOW = REPO / ".github" / "workflows" / "deploy-public-ask-viewer.yml"
GUARD = "Refuse a pre-retirement revision before any host change"
VERIFY = "Verify the public reader path with one live grounded query"
ROLLBACK = "Roll back source, Ask service, and proxy after failure"
OPTION = "--expected-model-authority-bundle-id"
RUN_KEY = "38171819746-1"


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
    assert guard < names.index("Set up SSH with the owner-verified host key")
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

def _remote_script(name: str) -> str:
    run = _step(name)["run"]
    start = run.index("<<'REMOTE'\n") + len("<<'REMOTE'\n")
    return run[start:run.rindex("REMOTE")]


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def test_rollback_restores_the_previous_checkout_and_recreates_the_ask_viewer(tmp_path):
    deploy_dir = tmp_path / "srv"
    repo_dir = deploy_dir / "DE4SDV"
    backup_dir = deploy_dir / f"DE4SDV-ask-backup-{RUN_KEY}"
    for directory, marker in ((repo_dir, "failed"), (backup_dir, "previous")):
        directory.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(directory)], check=True)
        (directory / "marker").write_text(marker)
        (directory / "deployment").mkdir()
        (directory / "deployment/compose.yaml").write_text("services: {}\n")
        _git(directory, "add", ".")
        _git(directory, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", marker)
    previous_sha = _git(backup_dir, "rev-parse", "HEAD")
    failed_sha = _git(repo_dir, "rev-parse", "HEAD")
    activation_marker = deploy_dir / f"DE4SDV-ask-activated-{RUN_KEY}"
    activation_marker.write_text(failed_sha + "\n")
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
    script = _remote_script(ROLLBACK).replace("/srv/de4sdv", str(deploy_dir))
    result = subprocess.run(["bash", "-s", "--", failed_sha, RUN_KEY], input=script, text=True, capture_output=True,
                            env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"})
    assert result.returncode == 0, result.stdout + result.stderr
    assert (repo_dir / "marker").read_text() == "previous"
    assert not backup_dir.exists()
    assert not activation_marker.exists()
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


@pytest.mark.parametrize("backup_kind", ["legacy", "foreign-attempt", "unmarked-attempt", "wrong-sha"])
def test_preflight_refusal_cannot_consume_a_stale_host_backup(tmp_path, backup_kind):
    ws = _workspace(tmp_path, pre_retirement_verifier=True)
    deploy_dir = tmp_path / "srv"
    repo_dir = deploy_dir / "DE4SDV"
    backup_name = {
        "legacy": "DE4SDV-ask-backup",
        "foreign-attempt": "DE4SDV-ask-backup-38171819746-2",
        "unmarked-attempt": f"DE4SDV-ask-backup-{RUN_KEY}",
        "wrong-sha": f"DE4SDV-ask-backup-{RUN_KEY}",
    }[backup_kind]
    backup_dir = deploy_dir / backup_name
    for directory, marker in ((repo_dir, "current-live"), (backup_dir, "stale-previous")):
        directory.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(directory)], check=True)
        (directory / "marker").write_text(marker)
        _git(directory, "add", ".")
        _git(directory, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", marker)
    live_sha = _git(repo_dir, "rev-parse", "HEAD")
    if backup_kind == "foreign-attempt":
        (deploy_dir / "DE4SDV-ask-activated-38171819746-2").write_text(live_sha + "\n")
    elif backup_kind == "wrong-sha":
        (deploy_dir / f"DE4SDV-ask-activated-{RUN_KEY}").write_text("b" * 40 + "\n")
    docker_log = tmp_path / "docker.log"
    bin_dir = tmp_path / "bin"
    _stub(bin_dir, "sudo", 'exec "$@"\n')
    _stub(bin_dir, "docker", f'echo "$*" >> "{docker_log}"\n')

    refused = _run_step(GUARD, ws)
    assert refused.returncode == 1
    assert not ws["ssh_log"].exists()
    # Even if failure cleanup is reached, it must not own another run's backup.
    script = _remote_script(ROLLBACK).replace("/srv/de4sdv", str(deploy_dir))
    cleanup = subprocess.run(
        ["bash", "-s", "--", live_sha, RUN_KEY],
        input=script, text=True, capture_output=True, env=ws["env"],
    )
    assert cleanup.returncode == 0, cleanup.stdout + cleanup.stderr
    assert (repo_dir / "marker").read_text() == "current-live"
    assert (backup_dir / "marker").read_text() == "stale-previous"
    assert not docker_log.exists()


@pytest.mark.parametrize("failure_stage", ["none", "build", "promotion", "warmup"])
def test_activation_creates_owned_recovery_state_and_cleanup_preserves_foreign_backups(tmp_path, failure_stage):
    ws = _workspace(tmp_path, pre_retirement_verifier=False)
    deploy_dir = tmp_path / "srv"
    live = deploy_dir / "DE4SDV"
    candidate = tmp_path / "candidate"
    for directory, marker in ((live, "previous"), (candidate, "candidate")):
        directory.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(directory)], check=True)
        (directory / "marker").write_text(marker)
        (directory / "deployment").mkdir()
        (directory / "deployment/compose.yaml").write_text("services: {}\n")
        _git(directory, "add", ".")
        _git(directory, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", marker)
    previous_sha = _git(live, "rev-parse", "HEAD")
    candidate_sha = _git(candidate, "rev-parse", "HEAD")
    foreign_backup = deploy_dir / "DE4SDV-ask-backup"
    foreign_backup.mkdir()
    (foreign_backup / "marker").write_text("foreign-backup")
    bundle = tmp_path / "source.bundle"
    _git(candidate, "update-ref", "refs/heads/deploy-ask-source", candidate_sha)
    _git(candidate, "bundle", "create", str(bundle), "refs/heads/deploy-ask-source")
    checksum = tmp_path / "source.bundle.sha256"
    checksum.write_text(subprocess.run(["sha256sum", str(bundle)], check=True, capture_output=True, text=True).stdout)
    # Synthetic application env only; no credentials or host files are read.
    ask_env = tmp_path / "application.env"
    ask_env.write_text(f"DE4SDV_APP_GIT_SHA={candidate_sha}\n")
    docker_log = tmp_path / "docker.log"
    bin_dir = tmp_path / "bin"
    # Execute real local commands, except root ownership and injected failure.
    _stub(bin_dir, "sudo", '\n'.join([
        'if [[ "$1" == mv && "$2" == *"DE4SDV-ask-next-"* && "$FAIL_STAGE" == promotion ]]; then',
        '  exit 43',
        'fi',
        'if [[ "$1" == install ]]; then',
        '  shift',
        '  args=()',
        '  while (($#)); do',
        '    case "$1" in',
        '      -o|-g) shift 2 ;;',
        '      *) args+=("$1"); shift ;;',
        '    esac',
        '  done',
        '  exec install "${args[@]}"',
        'fi',
        'exec "$@"',
        '',
    ]))
    _stub(bin_dir, "docker", (
        f'echo "$*" >> "{docker_log}"\n'
        'if [[ "$*" == *"build ask-viewer"* && "$FAIL_STAGE" == build ]]; then exit 42; fi\n'
        'if [[ "$*" == *"exec -T ask-viewer python"* ]]; then\n'
        '  if [[ "$FAIL_STAGE" == warmup ]]; then echo error; else echo ready; fi\n'
        'fi\n'
    ))
    # No real pause between warm-up polls: a wait that misses the error state
    # must fail this test through its probe count, not through the timeout.
    _stub(bin_dir, "sleep", ":\n")
    env = {**ws["env"], "FAIL_STAGE": failure_stage}

    def remote(name):
        script = _remote_script(name).replace("/srv/de4sdv", str(deploy_dir))
        script = script.replace("/tmp/de4sdv-ask-source.bundle.sha256", str(checksum))
        script = script.replace("/tmp/de4sdv-ask-source.bundle", str(bundle))
        script = script.replace("/tmp/ask-viewer.env", str(ask_env))
        return subprocess.run(["bash", "-s", "--", candidate_sha, RUN_KEY], input=script,
                              text=True, capture_output=True, env=env, timeout=30)

    activated = remote("Transfer and activate the fail-closed Ask service")
    assert activated.returncode == {"none": 0, "build": 42, "promotion": 43, "warmup": 1}[failure_stage], activated.stderr
    if failure_stage == "warmup":
        assert "semantic warmup failed" in activated.stderr
        calls = docker_log.read_text().splitlines()
        # Stopped at the first error answer (not after the ~17-minute timeout),
        # before the proxy was validated or recreated.
        assert len([c for c in calls if "exec -T ask-viewer python" in c]) == 1, calls
        assert not any("caddy" in c for c in calls), calls
    backup = deploy_dir / f"DE4SDV-ask-backup-{RUN_KEY}"
    marker = deploy_dir / f"DE4SDV-ask-activated-{RUN_KEY}"
    assert _git(backup, "rev-parse", "HEAD") == previous_sha
    assert marker.read_text() == candidate_sha + "\n"
    if failure_stage == "promotion":
        assert not live.exists()
    else:
        assert _git(live, "rev-parse", "HEAD") == candidate_sha

    cleanup = remote("Remove rollback checkout after successful verification" if failure_stage == "none" else ROLLBACK)
    assert cleanup.returncode == 0, cleanup.stdout + cleanup.stderr
    assert _git(live, "rev-parse", "HEAD") == (candidate_sha if failure_stage == "none" else previous_sha)
    assert not backup.exists()
    assert not marker.exists()
    assert (foreign_backup / "marker").read_text() == "foreign-backup"


def test_rollback_refuses_to_overwrite_a_foreign_live_revision(tmp_path):
    ws = _workspace(tmp_path, pre_retirement_verifier=False)
    deploy_dir = tmp_path / "srv"
    live = deploy_dir / "DE4SDV"
    backup = deploy_dir / f"DE4SDV-ask-backup-{RUN_KEY}"
    for directory in (live, backup):
        directory.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(directory)], check=True)
        (directory / "marker").write_text(directory.name)
        _git(directory, "add", ".")
        _git(directory, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "fixture")
    marker = deploy_dir / f"DE4SDV-ask-activated-{RUN_KEY}"
    marker.write_text("a" * 40 + "\n")
    _stub(tmp_path / "bin", "sudo", 'exec "$@"\n')
    docker_log = tmp_path / "docker.log"
    _stub(tmp_path / "bin", "docker", f'echo "$*" >> "{docker_log}"\n')
    before = (_git(live, "rev-parse", "HEAD"), _git(backup, "rev-parse", "HEAD"))
    result = subprocess.run(["bash", "-s", "--", "a" * 40, RUN_KEY],
                            input=_remote_script(ROLLBACK).replace("/srv/de4sdv", str(deploy_dir)),
                            text=True, capture_output=True, env=ws["env"])
    assert result.returncode == 1
    assert "no longer belongs" in result.stderr
    assert (_git(live, "rev-parse", "HEAD"), _git(backup, "rev-parse", "HEAD")) == before
    assert marker.exists()
    assert not docker_log.exists()


@pytest.mark.parametrize("backup_kind", ["empty-git", "unborn-head", "missing-compose"])
def test_rollback_refuses_damaged_owned_backup_before_any_mutation(tmp_path, backup_kind):
    ws = _workspace(tmp_path, pre_retirement_verifier=False)
    deploy_dir = tmp_path / "srv"
    live = deploy_dir / "DE4SDV"
    backup = deploy_dir / f"DE4SDV-ask-backup-{RUN_KEY}"
    live.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(live)], check=True)
    (live / "marker").write_text("valid-candidate")
    _git(live, "add", ".")
    _git(live, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "candidate")
    live_sha = _git(live, "rev-parse", "HEAD")
    backup.mkdir()
    (backup / "marker").write_text("damaged-backup")
    if backup_kind == "empty-git":
        (backup / ".git").mkdir()
    else:
        subprocess.run(["git", "init", "-q", str(backup)], check=True)
        if backup_kind == "missing-compose":
            _git(backup, "add", ".")
            _git(backup, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "incomplete backup")
    marker = deploy_dir / f"DE4SDV-ask-activated-{RUN_KEY}"
    marker.write_text(live_sha + "\n")
    _stub(tmp_path / "bin", "sudo", 'exec "$@"\n')
    docker_log = tmp_path / "docker.log"
    _stub(tmp_path / "bin", "docker", f'echo "$*" >> "{docker_log}"\n')
    before = {path.relative_to(deploy_dir).as_posix(): path.read_bytes()
              for path in deploy_dir.rglob("*") if path.is_file()}
    result = subprocess.run(
        ["bash", "-s", "--", live_sha, RUN_KEY],
        input=_remote_script(ROLLBACK).replace("/srv/de4sdv", str(deploy_dir)),
        text=True, capture_output=True, env=ws["env"], timeout=30,
    )
    assert result.returncode != 0, result.stdout + result.stderr
    assert _git(live, "rev-parse", "HEAD") == live_sha
    assert {path.relative_to(deploy_dir).as_posix(): path.read_bytes()
            for path in deploy_dir.rglob("*") if path.is_file()} == before
    assert marker.exists() and backup.exists()
    assert not docker_log.exists()


# --- the warm-up wait stops at the server's error state ----------------------

def _warmup_wait() -> str:
    """The activation step's wait for the Ask viewer's semantic warm-up."""
    step = next(step for step in _steps() if "/_ask_warmup" in (step.get("run") or ""))
    remote = _remote_script(step["name"])
    start = remote.index("ready=false")
    end = remote.index("fi\n", remote.index('if [[ "$ready" != true ]]')) + len("fi\n")
    return remote[start:end]


def _serve_warmup(answers: list) -> tuple[ThreadingHTTPServer, list]:
    """A /_ask_warmup stub that answers in order, then repeats the last answer.

    A dict is served as JSON; bytes are served verbatim (a body that is not a
    warm-up state); None closes the connection without any response.
    """
    served: list = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 (http.server API)
            answer = answers[min(len(served), len(answers) - 1)]
            served.append(answer)
            if answer is None:
                return  # HTTP/1.0 handler: the connection closes unanswered
            body = answer if isinstance(answer, bytes) else json.dumps(answer).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, served


def _run_warmup_wait(answers: list) -> tuple[subprocess.CompletedProcess, list]:
    """Run the wait with compose replaced: the workflow's own probe code runs here."""
    server, served = _serve_warmup(answers)
    port = server.server_address[1]
    harness = (
        "set -euo pipefail\n"
        "sleep() { :; }\n"
        "compose() {\n"
        '  local code="${@: -1}"\n'
        f'  "$PY" -c "${{code//127.0.0.1:8787/127.0.0.1:{port}}}"\n'
        "}\n"
        "COMPOSE=(compose)\n" + _warmup_wait() + "echo WAIT-DONE\n")
    try:
        result = subprocess.run(["bash", "-c", harness], text=True, capture_output=True, timeout=120,
                                env={**os.environ, "PY": sys.executable})
    finally:
        server.shutdown()
        server.server_close()
    return result, served


@pytest.mark.parametrize("reason, reported", [
    ("served-model check failed: drift", "semantic warmup error: served-model check failed: drift"),
    (None, "semantic warmup error: no reason reported"),
], ids=["with-reason", "without-reason"])
def test_the_warmup_wait_stops_at_the_servers_error_state_with_its_reason(reason, reported):
    result, served = _run_warmup_wait([{"status": "warming", "error": None},
                                       {"status": "error", "error": reason}])
    assert result.returncode == 1, result.stdout + result.stderr
    assert "semantic warmup failed" in result.stderr
    assert reported in result.stderr
    assert len(served) == 2  # stopped at once, not after the ~17-minute timeout


def test_the_warmup_wait_continues_once_ready():
    result, served = _run_warmup_wait([{"status": "idle", "error": None},
                                       {"status": "warming", "error": None},
                                       {"status": "ready", "error": None}])
    assert result.returncode == 0, result.stderr
    assert "WAIT-DONE" in result.stdout
    assert len(served) == 3


@pytest.mark.parametrize("first_answer", [b"<html>502 Bad Gateway</html>", None],
                         ids=["not-json", "no-response"])
def test_the_warmup_wait_treats_an_unreadable_probe_answer_as_starting(first_answer):
    """The normal first poll after ``up -d``: the viewer does not answer yet."""
    result, served = _run_warmup_wait([first_answer, {"status": "ready", "error": None}])
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Traceback" not in result.stderr
    assert "WAIT-DONE" in result.stdout
    assert len(served) == 2


def test_the_warmup_wait_stops_at_the_state_the_producer_reports_after_a_failed_warmup(monkeypatch):
    """The ``error)`` arm names the producer's terminal state, not a token of
    the workflow's own (its former ``failed)`` arm never matched anything)."""
    monkeypatch.syspath_prepend(str(REPO))
    from tools.sysml_html_viewer import ask_model_semantic as ams

    def refused_runtime():
        raise RuntimeError("served-model check failed: drift")

    monkeypatch.setenv("NOUS_ASK_SEMANTIC", "1")
    monkeypatch.setattr(ams, "_WARM_STATE", {"status": "idle", "error": None})
    monkeypatch.setattr(ams, "_runtime", refused_runtime)
    ams.start_warmup()
    for thread in threading.enumerate():
        if thread.name == "ask-semantic-warmup":
            thread.join(timeout=10)
    terminal = ams.warm_status()["status"]
    assert terminal not in ("idle", "warming"), "the warm-up thread did not finish"
    wait = _warmup_wait()
    assert f'{terminal}) echo "semantic warmup failed" >&2; exit 1 ;;' in wait
    assert "ready) ready=true; break ;;" in wait
