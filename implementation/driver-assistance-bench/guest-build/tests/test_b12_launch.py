"""Stand-in runs of b12_launch.sh, the detached launcher of B12 on the guest host (review R3).

A tar made with git archive from a throwaway repository holding this folder's
implementation/driver-assistance-bench, launched against the stand-in guest host of
test_guest_build_run.py. They show: the tar's sha256 and commit id are checked before anything is
extracted, the extraction goes into a fresh ~/da-b12-<sha> (an existing one is refused), the run is
detached (setsid nohup: its own session, no systemd unit) and ends with one result line, a failure
stops the guests, abort stops them through the script's own signal path, and the logs come back as a
.tgz with its sha256.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import tarfile
import time
from pathlib import Path

import pytest

from test_guest_build_run import Host
from test_guest_build_script import DA

LAUNCH = DA / "guest-build" / "b12_launch.sh"
needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="no git")


def make_tar(tmp: Path) -> tuple[Path, str]:
    repo = tmp / "repo"
    shutil.copytree(DA, repo / "implementation" / "driver-assistance-bench",
                    ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "run"))
    git = ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    subprocess.run([*git, "init", "-q"], check=True)
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "commit", "-q", "-m", "t"], check=True)
    sha = subprocess.run([*git, "rev-parse", "--short=8", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    upload = tmp / "upload"
    upload.mkdir()
    tar = upload / f"da-b12-{sha}.tar.gz"
    subprocess.run([*git, "archive", "--format=tar.gz", "-o", str(tar), sha, "implementation/driver-assistance-bench"],
                   check=True)
    subprocess.run(f"sha256sum {tar.name} > {tar.name}.sha256", shell=True, cwd=upload, check=True)
    launcher = upload / "b12_launch.sh"
    launcher.write_bytes(subprocess.run([*git, "show", f"{sha}:implementation/driver-assistance-bench/guest-build/b12_launch.sh"],
                                        check=True, capture_output=True).stdout)
    return tar, sha


class Launch:
    def __init__(self, tmp: Path):
        self.host = Host(tmp)
        self.tar, self.sha = make_tar(tmp)
        self.launcher = self.tar.parent / "b12_launch.sh"
        self.pids: list[int] = []

    def env(self, **extra: str) -> dict:
        env = self.host.env()
        del env["B12_DIR"]
        env.update(extra)
        return env

    def call(self, *args: str, **extra: str) -> subprocess.CompletedProcess:
        ran = subprocess.run(["bash", str(self.launcher), *args], capture_output=True, text=True,
                             env=self.env(**extra), timeout=120)
        state = self.host.tmp / "b12-launch" / "last-run"
        if state.exists():
            pid = int(next(l for l in state.read_text().splitlines() if l.startswith("pid=")).split("=")[1])
            if pid not in self.pids:
                self.pids.append(pid)
        return ran

    def run_dir(self) -> Path:
        state = (self.host.tmp / "b12-launch" / "last-run").read_text()
        return Path(next(l for l in state.splitlines() if l.startswith("run_dir=")).split("=", 1)[1])

    def wait_result(self, timeout: float = 240) -> str:
        out = self.run_dir() / "b12-all.out"
        deadline = time.time() + timeout
        while time.time() < deadline:
            text = out.read_text() if out.exists() else ""
            if "B12 RESULT:" in text:
                return next(l for l in text.splitlines() if "B12 RESULT:" in l)
            time.sleep(0.5)
        raise AssertionError(out.read_text()[-3000:] if out.exists() else "no output")

    def cleanup(self) -> None:
        for pid in self.pids:  # only the sessions this test started
            try:
                os.killpg(pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass


@pytest.fixture
def launch(tmp_path):
    item = Launch(tmp_path)
    yield item
    item.cleanup()


@needs_git
def test_a_detached_run_passes_with_one_result_line_and_records(launch):
    ran = launch.call("start", str(launch.tar))
    assert ran.returncode == 0, ran.stdout + ran.stderr
    assert f"the tar is commit {launch.sha}" in ran.stdout
    dest = launch.host.tmp / f"da-b12-{launch.sha}"
    assert (dest / "implementation" / "driver-assistance-bench" / "guest-build" / "build_guests_incremental.sh").is_file()
    result = launch.wait_result()
    assert "B12 RESULT: PASSED rc=0; guests: stopped; crosvm left: 0" in result, result
    assert "selinux: SELinux core Enforcing, IVI Enforcing; IVI_PERMISSIVE=0" in result
    run_dir = launch.run_dir()
    assert run_dir.parent == launch.host.ab and run_dir.name.startswith("b12-") and launch.sha in run_dir.name
    check = subprocess.run(["sha256sum", "-c", "b12-records.tgz.sha256"], cwd=run_dir, capture_output=True, text=True)
    assert check.returncode == 0, check.stdout + check.stderr
    names = tarfile.open(run_dir / "b12-records.tgz").getnames()
    assert any(n.endswith("b12-summary.txt") for n in names) and any(n.startswith("logs") for n in names)
    status = launch.call("status")
    assert "B12 RESULT: PASSED" in status.stdout
    # the run had its own session: setsid, not a systemd unit
    assert not any("systemd-run" in line for line in LAUNCH.read_text().splitlines() if not line.lstrip().startswith("#"))
    # a second start of the same tar is refused: the extraction must be fresh
    again = launch.call("start", str(launch.tar))
    assert again.returncode != 0 and "extract into a fresh directory" in again.stdout


@needs_git
def test_a_tar_whose_sha256_does_not_match_is_not_extracted(launch):
    with launch.tar.open("ab") as f:
        f.write(b"\0")
    ran = launch.call("start", str(launch.tar))
    assert ran.returncode != 0 and "sha256 does not match" in ran.stdout
    assert not (launch.host.tmp / f"da-b12-{launch.sha}").exists()


@needs_git
def test_a_failed_run_stops_the_guests_and_says_so(launch):
    ran = launch.call("start", str(launch.tar), FAKE_FAIL_PUSH="*.apk")
    assert ran.returncode == 0, ran.stdout + ran.stderr
    result = launch.wait_result()
    assert "B12 RESULT: FAILED rc=1; guests: stopped; crosvm left: 0" in result, result
    assert launch.host.cvd_stops()[:2] == ["cvd --group_name=cvd_1 stop", "cvd --group_name=cvd_2 stop"]


@needs_git
def test_abort_ends_the_run_through_the_guest_stop(launch):
    ran = launch.call("start", str(launch.tar), FAKE_HANG="remount")
    assert ran.returncode == 0, ran.stdout + ran.stderr
    deadline = time.time() + 200
    while not any(line.endswith(" remount") for line in launch.host.calls_lines()):
        assert time.time() < deadline
        time.sleep(0.3)
    aborted = launch.call("abort")
    assert aborted.returncode == 0, aborted.stdout + aborted.stderr
    result = launch.wait_result()
    assert "B12 RESULT: FAILED rc=143; guests: stopped" in result, result
    assert launch.host.cvd_stops()[:2] == ["cvd --group_name=cvd_1 stop", "cvd --group_name=cvd_2 stop"]


@needs_git
def test_the_rerun_command_of_an_enforcing_failure_is_the_launchers_own(launch):
    launch.host.logcat.write_text("")
    launch.call("start", str(launch.tar))
    result = launch.wait_result()
    assert "FAILED" in result
    text = (launch.run_dir() / "b12-all.out").read_text()
    line = next(l for l in text.splitlines() if "the rerun command:" in l)
    assert line.endswith(f"the rerun command: IVI_PERMISSIVE=1 B12_RERUN=2 bash {launch.launcher} start {launch.tar}"), line
