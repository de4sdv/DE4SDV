"""Supervision tests for the gateway entrypoint (review finding R7).

The real `gateway/entrypoint.sh` runs under `/bin/sh`: dash, as in the
Debian-based image, which holds the script to POSIX shell. `ip` and
`python` are fakes on PATH: each fake child logs that it started, logs a SIGTERM
it receives, and can be told to exit early, so the tests see what the
entrypoint does with its children without vcan, root or python-can.

Run:  python -m pytest de4sdv-virtual-ee/checks/tests/test_runtime_gateway_entrypoint.py
"""

from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path

import pytest

ENTRYPOINT = Path(__file__).resolve().parents[2] / "gateway" / "entrypoint.sh"

FAKE_IP = """#!/bin/sh
exit 0
"""

FAKE_PYTHON = """#!/bin/sh
case "$*" in
  *bridge.py*vcan-front*) role=bridge-front ;;
  *bridge.py*vcan-rear*) role=bridge-rear ;;
  *router.py*) role=router ;;
  *) role=unknown ;;
esac
echo "$role $$" >> "$FAKE_LOG/started"
trap 'echo "$role" >> "$FAKE_LOG/terminated"; exit 0' TERM
if [ "$role" = "${FAKE_DIE:-}" ]; then
  sleep 0.5
  echo "$role failing"
  exit 3
fi
while :; do sleep 0.1; done
"""

# busybox sh is not used: its standalone shell runs its own `ip` applet in place
# of the fake on PATH, so it would test the harness, not the entrypoint.
SHELLS = [["/bin/sh"]]
SHELL_IDS = [" ".join(Path(part).name for part in shell) for shell in SHELLS]


def alive(pid: int) -> bool:
    try:
        state = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0]
    except (FileNotFoundError, ProcessLookupError):
        return False
    return state != "Z"


class Gateway:
    def __init__(self, tmp_path: Path, shell: list[str], die: str = "") -> None:
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        for name, text in (("ip", FAKE_IP), ("python", FAKE_PYTHON)):
            path = bin_dir / name
            path.write_text(text)
            path.chmod(0o755)
        self.log = tmp_path / "log"
        self.log.mkdir()
        env = {
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "FAKE_LOG": str(self.log),
            "FAKE_DIE": die,
            "GW_FRONT_PEER": "10.100.0.11",
            "GW_REAR_PEER": "10.100.0.13",
            "TMPDIR": str(tmp_path),
        }
        self.proc = subprocess.Popen(
            [*shell, str(ENTRYPOINT)], env=env, start_new_session=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )

    def lines(self, name: str) -> list[str]:
        path = self.log / name
        return path.read_text().split("\n")[:-1] if path.exists() else []

    def children(self) -> dict[str, int]:
        return {role: int(pid) for role, pid in (line.split() for line in self.lines("started"))}

    def wait_for_children(self, n: int = 3, timeout: float = 5.0) -> None:
        deadline = time.monotonic() + timeout
        while len(self.children()) < n and time.monotonic() < deadline:
            time.sleep(0.05)

    def finish(self, timeout: float) -> int | None:
        """The entrypoint's exit status, or None if it is still running."""
        try:
            return self.proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            return None

    def cleanup(self) -> str:
        """Kill whatever is left; return everything the entrypoint printed."""
        for pid in self.children().values():
            if alive(pid):
                os.kill(pid, signal.SIGKILL)
        try:
            os.killpg(self.proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        return self.proc.communicate()[0]


def survivors(gateway: Gateway, grace: float = 2.0) -> list[str]:
    deadline = time.monotonic() + grace
    while time.monotonic() < deadline:
        left = [role for role, pid in gateway.children().items() if alive(pid)]
        if not left:
            return []
        time.sleep(0.05)
    return left


@pytest.mark.parametrize("shell", SHELLS, ids=SHELL_IDS)
@pytest.mark.parametrize("die", ["bridge-front", "bridge-rear", "router"])
def test_a_child_that_exits_takes_the_gateway_down_with_a_failure_status(tmp_path, shell, die):
    gateway = Gateway(tmp_path, shell, die=die)
    rc, left = None, None
    try:
        gateway.wait_for_children()
        rc = gateway.finish(timeout=6)
        left = survivors(gateway)
    finally:
        out = gateway.cleanup()

    assert rc is not None, f"gateway still running 6 s after {die} exited"
    assert rc != 0, out
    assert left == [], f"{left} outlived the gateway:\n{out}"


@pytest.mark.parametrize("shell", SHELLS, ids=SHELL_IDS)
def test_sigterm_stops_every_child_and_the_gateway_exits_cleanly(tmp_path, shell):
    gateway = Gateway(tmp_path, shell)
    rc, left = None, None
    try:
        gateway.wait_for_children()
        time.sleep(1.2)  # past the entrypoint's start-up pause
        gateway.proc.send_signal(signal.SIGTERM)
        rc = gateway.finish(timeout=5)
        left = survivors(gateway)
        terminated = sorted(gateway.lines("terminated"))
    finally:
        out = gateway.cleanup()

    assert rc == 0, out
    assert terminated == ["bridge-front", "bridge-rear", "router"], out
    assert left == [], out
