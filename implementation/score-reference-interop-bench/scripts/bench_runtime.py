"""Process handling for the bench runners (abort matrix, soak, RMW probe).

The runners start every bench process as the calling, non-root user, with
unlimited core size, each with its own log file; they record the start and
exit times on CLOCK_MONOTONIC and turn cores into gdb backtraces. They need a
shell in which /opt/ros/humble/setup.bash was sourced.
"""

from __future__ import annotations

import glob
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import subprocess
import threading
import time
from typing import Callable

SECOND_NS = 1_000_000_000


def monotonic_ns() -> int:
    return time.monotonic_ns()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _unlimited_core() -> None:
    resource.setrlimit(resource.RLIMIT_CORE, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))


class BenchProcess:
    """One child process with a log file and a recorded exit time."""

    def __init__(self, name: str, argv: list[str], log_path: Path, env: dict[str, str] | None = None,
                 cwd: Path | None = None) -> None:
        self.name = name
        self.argv = argv
        self.log_path = log_path
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self._log = log_path.open("ab")
        self.start_monotonic_ns = monotonic_ns()
        self.popen = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=self._log,
            stderr=subprocess.STDOUT,
            env=env,
            cwd=str(cwd) if cwd else None,
            preexec_fn=_unlimited_core,
        )
        self.pid = self.popen.pid
        self.exit_monotonic_ns: int | None = None
        self._waiter = threading.Thread(target=self._wait, daemon=True)
        self._waiter.start()

    def _wait(self) -> None:
        self.popen.wait()
        self.exit_monotonic_ns = monotonic_ns()
        self._log.flush()

    @property
    def returncode(self) -> int | None:
        return self.popen.returncode if self.exit_monotonic_ns is not None else None

    def alive(self) -> bool:
        return self.exit_monotonic_ns is None and self.popen.poll() is None

    def log_text(self) -> str:
        try:
            return self.log_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    def wait_for(self, predicate: Callable[[str], bool], timeout_s: float) -> bool:
        """Waits until predicate(log text) holds or the process ends or time runs out."""
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if predicate(self.log_text()):
                return True
            if not self.alive():
                return predicate(self.log_text())
            time.sleep(0.05)
        return predicate(self.log_text())

    def wait_exit(self, timeout_s: float) -> bool:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if not self.alive():
                self._waiter.join(timeout=1.0)
                return True
            time.sleep(0.05)
        return False

    def stop(self, timeout_s: float = 10.0, sig: int = signal.SIGTERM) -> int | None:
        """Sends sig, waits, kills after the timeout; returns the return code."""
        if self.alive():
            try:
                self.popen.send_signal(sig)
            except ProcessLookupError:
                pass
            if not self.wait_exit(timeout_s):
                self.popen.kill()
                self.wait_exit(5.0)
        self._waiter.join(timeout=2.0)
        self._log.close()
        return self.popen.returncode


def json_event_predicate(event: str) -> Callable[[str], bool]:
    marker = f'"event":"{event}"'
    return lambda text: marker in text


def regex_predicate(pattern: str) -> Callable[[str], bool]:
    compiled = re.compile(pattern)
    return lambda text: compiled.search(text) is not None


def clean_lola_state(record: list[str]) -> None:
    """Removes the LoLa shared memory and discovery files and vsomeip sockets of this user.

    Called only while no mw::com or vsomeip process of the bench runs.
    """
    uid = os.getuid()
    candidates = glob.glob("/dev/shm/lola-*") + glob.glob("/tmp/vsomeip*") + ["/tmp/mw_com_lola"]
    for path in candidates:
        try:
            if not os.path.lexists(path) or os.lstat(path).st_uid != uid:
                continue
            if os.path.isdir(path) and not os.path.islink(path):
                shutil.rmtree(path)
            else:
                os.unlink(path)
            record.append(path)
        except OSError as error:
            record.append(f"{path}: {error}")


def ros_environment(rmw: str, localhost_only: bool, extra: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ)
    env["RMW_IMPLEMENTATION"] = rmw
    env["ROS_DOMAIN_ID"] = env.get("ROS_DOMAIN_ID", "42")
    if localhost_only:
        env["ROS_LOCALHOST_ONLY"] = "1"
    else:
        env.pop("ROS_LOCALHOST_ONLY", None)
    env.pop("FASTRTPS_DEFAULT_PROFILES_FILE", None)
    env.pop("DE4SDV_ADAPTER_FAULT_HOOK", None)
    env["RCUTILS_LOGGING_BUFFERED_STREAM"] = "0"
    env["PYTHONUNBUFFERED"] = "1"
    if extra:
        env.update(extra)
    return env


def find_core(core_dir: Path, pid: int) -> Path | None:
    matches = sorted(core_dir.glob(f"core.*.{pid}"))
    return matches[0] if matches else None


def gdb_backtrace(binary: Path, core: Path, out_dir: Path, stem: str) -> str:
    """Writes <stem>.bt.txt (crashing thread) and <stem>.all-threads.txt; returns the first."""
    common = ["gdb", "-batch", "-nx", "-iex", "set debuginfod enabled off", "-iex", "set pagination off"]
    crashing = subprocess.run(common + ["-ex", "bt", str(binary), str(core)], capture_output=True, text=True,
                              timeout=180, check=False)
    text = crashing.stdout + crashing.stderr
    (out_dir / f"{stem}.bt.txt").write_text(text, encoding="utf-8")
    threads = subprocess.run(common + ["-ex", "thread apply all bt", str(binary), str(core)], capture_output=True,
                             text=True, timeout=180, check=False)
    (out_dir / f"{stem}.all-threads.txt").write_text(threads.stdout + threads.stderr, encoding="utf-8")
    return text


def run_command(argv: list[str], env: dict[str, str], timeout_s: float) -> dict:
    """Runs a command to completion or timeout; returns times, return code and output."""
    start = monotonic_ns()
    timed_out = False
    try:
        completed = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=timeout_s, check=False)
        returncode: int | None = completed.returncode
        output = completed.stdout + completed.stderr
    except subprocess.TimeoutExpired as expired:
        timed_out = True
        returncode = None

        def _text(value: object) -> str:
            if isinstance(value, bytes):
                return value.decode("utf-8", errors="replace")
            return value if isinstance(value, str) else ""

        output = _text(expired.stdout) + _text(expired.stderr)
    return {
        "argv": argv,
        "start_monotonic_ns": start,
        "end_monotonic_ns": monotonic_ns(),
        "returncode": returncode,
        "timed_out": timed_out,
        "output": output,
    }


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def nm_dynamic_line(binary: Path, symbol: str) -> str:
    result = subprocess.run(["nm", "-D", "--defined-only", str(binary)], capture_output=True, text=True,
                            check=False)
    lines = [line for line in result.stdout.splitlines() if line.endswith(f" {symbol}")]
    return lines[0] if lines else "not exported"
