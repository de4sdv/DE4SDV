"""The second caller of the B12 script: the session's guest prepare (session/remote/guest_prepare.sh).

That caller creates the guests fresh itself (launch_two_vms.sh down, up), runs no `boot`, and calls
`install`, then `verify`, directly from an SSH step, possibly on a later UTC day than the `ivi` build,
with its own B12_DIR per session and IVI_PERMISSIVE passed through. These tests pin that interface on
the stand-in guest host of test_guest_build_run.py, and the refusal of the 2026-11-17 kit's own
logs/ and identity/ folders.
"""

from __future__ import annotations

import subprocess

import pytest

from test_guest_build_run import Host
from test_guest_build_script import SCRIPT


def step(host: Host, name: str, b12_dir, **extra: str) -> subprocess.CompletedProcess:
    env = {**host.env(), "B12_DIR": str(b12_dir), **extra}
    env.pop("GUESTS", None)  # the caller sets no GUESTS: install and verify do not read it
    return subprocess.run(["bash", str(SCRIPT), name], capture_output=True, text=True, env=env, timeout=300)


@pytest.mark.parametrize("variable, value", [
    ("LOGS", "{ab}/logs"),
    ("IDENT", "{ab}/identity"),
    ("IDENT", "{ab}/identity/session-1"),
    ("B12_DIR", "{ab}/identity"),
    ("B12_DIR", "{ab}"),            # its logs/ would be the kit's
    ("LOGS", "{ab}/b12-x/../logs"),
])
def test_the_kits_logs_and_identity_are_refused(tmp_path, variable, value):
    host = Host(tmp_path)
    ran = step(host, "install", host.ab / "b12-session", **{variable: value.format(ab=host.ab)})
    assert ran.returncode == 2, ran.stdout + ran.stderr
    assert "inside the 2026-11-17 kit's logs/ or identity/" in ran.stdout
    assert not (host.ab / "logs").exists() and not (host.ab / "identity").exists()
    assert host.calls_lines() == []


def test_install_then_verify_on_guests_booted_by_the_session_with_its_own_b12_dir(tmp_path):
    host = Host(tmp_path)
    build_day = host.ab / "b12-20261119"
    assert step(host, "ivi", build_day).returncode == 0
    host.calls.write_text("")
    session = host.ab / "sessions" / "s-20261120-1" / "b12"
    for name in ("install", "verify"):
        ran = step(host, name, session)
        assert ran.returncode == 0, name + "\n" + ran.stdout[-3000:] + ran.stderr
    # what the caller collects, under its B12_DIR
    for rel in ("logs/b12-install.log", "logs/b12-verify.log", "identity/ivi-warning-app-identity.txt",
                "identity/b12-app-logcat.txt", "identity/b12-summary.txt", "work/app-verify.out"):
        assert (session / rel).is_file(), rel
    summary = (session / "identity" / "b12-summary.txt").read_text()
    assert "install: apk sha256" in summary and "SELinux core Enforcing, IVI Enforcing" in summary
    # it creates, removes or stops no guest: that is the session's
    assert not any(line.startswith(("launch", "cvd")) for line in host.calls_lines()), host.calls_lines()
    assert not any(line.endswith("setenforce 0") for line in host.calls_lines())


def test_verify_alone_passes_ivi_permissive_through(tmp_path):
    host = Host(tmp_path)
    step(host, "ivi", host.ab / "b12-build")
    session = host.ab / "b12-session"
    assert step(host, "install", session).returncode == 0
    ran = step(host, "verify", session, IVI_PERMISSIVE="1")
    assert ran.returncode == 0, ran.stdout[-3000:]
    assert any(line.endswith("shell setenforce 0") for line in host.calls_lines())
    assert "conditional on a permissive IVI" in (session / "identity" / "b12-summary.txt").read_text()


def test_verify_alone_under_enforcing_prints_a_verify_rerun_or_the_callers_command(tmp_path):
    host = Host(tmp_path)
    step(host, "ivi", host.ab / "b12-build")
    session = host.ab / "b12-session"
    assert step(host, "install", session).returncode == 0
    host.logcat.write_text("")
    ran = step(host, "verify", session)
    assert ran.returncode == 1
    line = next(l for l in ran.stdout.splitlines() if "the rerun command:" in l)
    assert line.endswith(f"IVI_PERMISSIVE=1 B12_DIR={session} ./build_guests_incremental.sh verify"), line
    ran = step(host, "verify", session, B12_RERUN_CMD="da_session.sh --permissive-ivi")
    assert ran.returncode == 1
    assert "the rerun command: da_session.sh --permissive-ivi" in ran.stdout
    assert not any(line.endswith("setenforce 0") for line in host.calls_lines())


def test_install_without_a_built_apk_fails_with_status_1(tmp_path):
    host = Host(tmp_path)
    ran = step(host, "install", host.ab / "b12-session")
    assert ran.returncode == 1
    assert "build first" in ran.stdout
