"""set_ivi_clock.sh on stubs: the step has to land, and the script has to prove it.

`toybox sntp -s` on the sdv_ivi_cf image prints the offset, exits 0 and leaves
the clock where it was, so a set built on it reports success while the window
runs on the guest's free-running drift. These tests run the real script with a
fake adb that models a guest clock: `sntp -s` is the no-op it is on the image,
`sntp -q` measures, and `date -s @<epoch>` moves the clock. They check that the
script steps with date, that the second exchange decides the outcome, and that a
step which does not land fails instead of passing.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
SCRIPT = BENCH / "scripts" / "set_ivi_clock.sh"

# A guest clock modelled as a skew against the host: guest_now = host_now + skew,
# so the SNTP offset (host - guest) is -skew. The step arrives as one guest shell
# command (`date -s @$(awk ... n + o ...)`), exactly as the script sends it. The
# guest takes LATENCY_S between its clock read and its set (16 ms on the bench
# guest), so the target has to carry that duration; without it the skew lands
# LATENCY_S behind and retries never converge. NOOP_STEP models a date that
# cannot set the clock, which the script must catch rather than report as a set.
FAKE_ADB = r'''#!/usr/bin/env python3
import os, re, sys, time

state = os.environ["FAKE_STATE"]
LATENCY_S = float(os.environ.get("FAKE_LATENCY_S", "0.016"))
def path(name): return os.path.join(state, name)
def read_skew():
    try:
        with open(path("skew")) as handle: return float(handle.read())
    except (OSError, ValueError):
        return 0.1836
def write_skew(value):
    with open(path("skew"), "w") as handle: handle.write(repr(value))
def log_call(line):
    with open(path("calls.log"), "a") as handle: handle.write(line + "\n")

args = sys.argv[1:]
if args[:1] == ["-s"]:
    args = args[2:]
if not args:
    sys.exit(0)
command, rest = args[0], args[1:]

if command in ("connect", "root", "wait-for-device", "remount"):
    sys.exit(0)
if command == "shell":
    line = " ".join(rest)
    if "command -v awk" in line:
        print("/system/bin/awk")
    elif line.startswith("t0=$(date +%s.%N)"):
        print("%.6f" % LATENCY_S)                     # the guest's read-to-set chain
    elif line.startswith("toybox sntp -q"):
        print("2026-10-31 23:00:00.000000000 +0000 offset %.9f secs" % -read_skew())
    elif line.startswith("toybox sntp -s"):
        log_call("sntp -s")          # the image's no-op, recorded so a test can forbid it
    elif line.startswith("date +%s.%N"):
        print("%.9f" % (time.time() + read_skew()))
    elif "toybox date -s @" in line:
        match = re.search(r"-v o=(-?[0-9.]+)", line)
        if not match:
            log_call("date -s unparsed: " + line)
            sys.exit(1)
        target_offset = float(match.group(1))
        log_call("date -s " + match.group(1))
        read_at = time.time()                          # the guest read, before its awk starts
        target = read_at + read_skew() + target_offset
        if os.environ.get("NOOP_STEP") != "1":
            time.sleep(LATENCY_S)                      # awk and date start in between
            write_skew(target - time.time())
    sys.exit(0)
sys.exit(0)
'''


def setup(tmp_path: Path) -> dict:
    bindir = tmp_path / "bin"
    bindir.mkdir()
    adb = bindir / "adb"
    adb.write_text(FAKE_ADB)
    adb.chmod(0o755)
    (tmp_path / "skew").write_text("0.1836")     # the guest starts 183.6 ms ahead of the host
    return {**os.environ, "ADB": str(adb), "FAKE_STATE": str(tmp_path), "RUN_DIR": str(tmp_path / "run"),
            "IVI_ADB": "0.0.0.0:6522", "SNTP_SERVER": "192.168.98.1", "HOST_ADDR": "192.168.98.1"}


def run(tmp_path: Path, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    environment = setup(tmp_path) if env is None else env
    return subprocess.run(["bash", str(SCRIPT), *args], capture_output=True, text=True, env=environment,
                          cwd=str(BENCH), timeout=120)


def skew(tmp_path: Path) -> float:
    return float((tmp_path / "skew").read_text())


def test_set_steps_the_clock_with_date_and_verifies_with_a_second_exchange(tmp_path):
    result = run(tmp_path, "set")

    assert result.returncode == 0, result.stdout + result.stderr
    assert abs(skew(tmp_path)) < 0.010, "the step did not land"
    assert "stepped by -0.183600000" in result.stdout
    assert "holds" in result.stdout and "bound 5 ms" in result.stdout
    calls = (tmp_path / "calls.log").read_text()
    assert "date -s" in calls
    assert "sntp -s" not in calls, "the set must not be built on the image's no-op sntp -s"


def test_set_fails_when_the_step_does_not_land(tmp_path):
    environment = setup(tmp_path)
    environment["NOOP_STEP"] = "1"
    result = run(tmp_path, "set", env=environment)

    assert result.returncode != 0, "a step that did not land must fail the set"
    assert abs(skew(tmp_path)) > 0.100, "the fake clock should be untouched"
    assert "still" in result.stdout or "ERROR" in result.stdout


def test_set_carries_the_guest_latency_into_the_target(tmp_path):
    # A guest whose read-to-set chain costs 50 ms: a step that ignores that lands
    # 50 ms behind every time and never converges, so this only passes when the
    # target carries the measured chain duration.
    environment = setup(tmp_path)
    environment["FAKE_LATENCY_S"] = "0.050"
    result = run(tmp_path, "set", env=environment)

    assert result.returncode == 0, result.stdout + result.stderr
    assert abs(skew(tmp_path)) < 0.010, "the compensation did not carry the latency"


def test_set_reports_a_missing_offset_instead_of_pretending(tmp_path):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    adb = bindir / "adb"
    adb.write_text("#!/usr/bin/env bash\nexit 0\n")   # every guest call prints nothing
    adb.chmod(0o755)
    environment = {**os.environ, "ADB": str(adb), "FAKE_STATE": str(tmp_path),
                   "RUN_DIR": str(tmp_path / "run"), "IVI_ADB": "0.0.0.0:6522",
                   "SNTP_SERVER": "192.168.98.1", "HOST_ADDR": "192.168.98.1"}
    result = run(tmp_path, "set", env=environment)

    assert result.returncode != 0
    assert "no awk" in result.stdout or "printed no offset" in result.stdout
