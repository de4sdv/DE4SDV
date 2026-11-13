"""Process handling for the bench runners (abort matrix, soak, startup probe).

The runners start every bench process as the calling, non-root user, with
unlimited core size, each with its own log file; they record the start and
exit times on CLOCK_MONOTONIC and turn cores into gdb backtraces with the
address mappings of the core. They need a shell in which
/opt/ros/humble/setup.bash and then config/ros_environment.sh of the bench
(or of its runtime bundle) were sourced: every ROS 2 process of a run uses
that one environment, and the runners record it.
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
    """True once a JSON line with this event is in the text, with or without spaces after the colon."""
    compiled = re.compile(r'"event"\s*:\s*"' + re.escape(event) + '"')
    return lambda text: compiled.search(text) is not None


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


# The variables that config/ros_environment.sh sets, and the ones a probe case changes.
ENVIRONMENT_KEYS = ("RMW_IMPLEMENTATION", "CYCLONEDDS_URI", "ROS_DOMAIN_ID", "ROS_LOCALHOST_ONLY")


def bench_environment_problems(env: dict[str, str]) -> list[str]:
    """What differs from the environment of config/ros_environment.sh."""
    problems = []
    if env.get("RMW_IMPLEMENTATION") != "rmw_cyclonedds_cpp":
        problems.append(f"RMW_IMPLEMENTATION is {env.get('RMW_IMPLEMENTATION')!r}, not 'rmw_cyclonedds_cpp'")
    uri = env.get("CYCLONEDDS_URI", "")
    if not uri.startswith("file://") or not uri.endswith("/cyclonedds.xml") or not Path(uri[7:]).is_file():
        problems.append(f"CYCLONEDDS_URI {uri!r} names no cyclonedds.xml of the bench")
    if not env.get("ROS_DOMAIN_ID"):
        problems.append("ROS_DOMAIN_ID is not set")
    if "ROS_LOCALHOST_ONLY" in env:
        problems.append("ROS_LOCALHOST_ONLY is set")
    return problems


def bench_environment(extra: dict[str, str] | None = None) -> dict[str, str]:
    """The environment of a bench process: the sourced bench environment, changed only by extra."""
    env = dict(os.environ)
    problems = bench_environment_problems(env)
    if problems:
        raise SystemExit("source /opt/ros/humble/setup.bash and config/ros_environment.sh first: " + "; ".join(problems))
    env.pop("MW_LOG_CONFIG_FILE", None)
    env["RCUTILS_LOGGING_BUFFERED_STREAM"] = "0"
    env["PYTHONUNBUFFERED"] = "1"
    if extra:
        env.update(extra)
    return env


def adapter_environment(bundle: Path, env: dict[str, str]) -> dict[str, str]:
    """The adapter's environment: env and the mw::log configuration of the adapter."""
    return dict(env, MW_LOG_CONFIG_FILE=str(bundle / "config" / "mw_log_adapter.json"))


def environment_record(env: dict[str, str]) -> dict[str, str | None]:
    return {key: env.get(key) for key in ENVIRONMENT_KEYS}


def find_core(core_dir: Path, pid: int) -> Path | None:
    matches = sorted(core_dir.glob(f"core.*.{pid}"))
    return matches[0] if matches else None


def gdb_backtrace(binary: Path, core: Path, out_dir: Path, stem: str) -> tuple[str, str]:
    """Writes <stem>.bt.txt (crashing thread), <stem>.all-threads.txt and <stem>.mappings.txt.

    Returns the backtrace of the crashing thread and the address mappings of
    the core (gdb's info proc mappings), which locate each frame.
    """
    common = ["gdb", "-batch", "-nx", "-iex", "set debuginfod enabled off", "-iex", "set pagination off"]

    def run(command: str, name: str) -> str:
        completed = subprocess.run(common + ["-ex", command, str(binary), str(core)], capture_output=True, text=True,
                                   timeout=180, check=False)
        text = completed.stdout + completed.stderr
        (out_dir / f"{stem}.{name}.txt").write_text(text, encoding="utf-8")
        return text

    backtrace = run("bt", "bt")
    run("thread apply all bt", "all-threads")
    mappings = run("info proc mappings", "mappings")
    return backtrace, mappings


def backtrace_other_cores(core_dir: Path, processes: list["BenchProcess"], out_dir: Path) -> list[dict]:
    """Backtraces of the cores that native bench processes other than the adapter left.

    A core of a Python process (observer, frame source) is listed without a
    backtrace.
    """
    from de4sdv_score_bench.backtrace import frame_text, read_located_frames

    records = []
    for process in processes:
        core = find_core(core_dir, process.pid)
        if core is None:
            continue
        binary = Path(process.argv[0])
        record: dict = {"process": process.name, "core": core.name, "returncode": process.returncode,
                        "named_top_frames": None}
        if binary.is_file() and not binary.name.startswith("python"):
            backtrace, mappings = gdb_backtrace(binary, core, out_dir, f"{process.name}-core")
            frames = read_located_frames(backtrace, mappings)
            record["named_top_frames"] = [frame_text(frame) for frame in frames if frame.function != "??"][:12]
        records.append(record)
    return records


def frame_stream_client_pids(port: int) -> list[int] | None:
    """The processes with an established TCP connection to the frame stream port (ss -tnp); None when ss fails."""
    completed = subprocess.run(["ss", "-H", "-t", "-n", "-p", "state", "established", f"( dport = :{port} )"],
                               capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        return None
    return sorted(int(pid) for pid in re.findall(r"pid=(\d+)", completed.stdout))


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
