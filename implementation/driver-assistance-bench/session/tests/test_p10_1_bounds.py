"""Static checks of the p10-1 step's bounds (review of the p10-1 session at 58f0039c, V4 and V5)."""

from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SESSION_DIR = HERE.parent
BENCH = SESSION_DIR.parent
ENTRYPOINTS = SESSION_DIR / "entrypoints.env"
CHECK = BENCH / "score-build" / "scripts" / "p10_1_check.sh"


def _default(path: Path, name: str) -> float:
    m = re.search(r': "\$\{%s:=([0-9.]+)\}"' % re.escape(name), path.read_text())
    assert m, (path.name, name)
    return float(m.group(1))


def _session(name: str) -> float:
    m = re.search(r"(?:^|[ ;])%s=([0-9.]+)" % re.escape(name), (SESSION_DIR / "da_session.sh").read_text(), re.M)
    assert m, name
    return float(m.group(1))


def _entry_scripts() -> list[Path]:
    """Every ENTRY_* default of entrypoints.env that is a shell script, and the library its S-CORE entries source."""
    out = []
    for rel in re.findall(r': "\$\{ENTRY_[A-Z0-9_]+:?=([^}]+)\}"', ENTRYPOINTS.read_text()):
        p = BENCH / rel
        if p.suffix == ".sh":
            assert p.is_file(), rel
            out.append(p)
    out.append(BENCH / "score-path" / "scripts" / "lib_score_side.sh")
    return out


def _timeout_calls(path: Path) -> list[str]:
    calls = []
    for line in path.read_text().splitlines():
        code = "" if line.lstrip().startswith("#") else line
        if re.search(r"(^|[\s;({|&])timeout\s", code):
            calls.append(code.strip())
    return calls


def test_every_bound_in_an_entry_script_stays_in_the_steps_process_group() -> None:
    # V4 (T1/T7): GNU timeout without --foreground moves its command into a new process group, which the step's
    # group TERM does not reach. Every ENTRY_* script a remote step runs, not only session/remote; guest_up's launch
    # is the one exception (run in the background, the TERM forwarded: test_remote_scripts.py)
    files = _entry_scripts()
    assert CHECK in files and len(files) >= 15
    bad = [(f.name, c) for f in files for c in _timeout_calls(f)
           if "timeout --foreground " not in c and not (f.name == "guest_up.sh" and c.endswith("& LP=$!"))]
    assert not bad, bad


def test_the_checks_external_calls_are_bounded() -> None:
    # V4: a hung ort_cuda_check or late-subscriber probe held the step until the cap (V1's path)
    text = CHECK.read_text()
    statements = text.replace("\\\n", " ").splitlines()   # continuation lines joined
    calls = [line.strip() for line in statements if re.search(r'"\$probe"\s+--wait-s|"\$ort" "\$weights', line)]
    assert len(calls) == 2, calls
    assert all("timeout --foreground " in c for c in calls), calls
    assert re.search(r'timeout --foreground [0-9]+ bash -c "</dev/tcp/\$carla/2000"', text)
    # the cut handler's own stop is bounded too, and runs where a second TERM to the step cannot cut it
    assert re.search(r'setsid -w timeout --foreground "\$DA_P10_1_CUT_STOP_S" bash "\$SP/stop_score_side.sh"', text)


def check_worst_case_s() -> float:
    """The p10-1 check's longest run from its own defaults (each bound it waits for, run to its end)."""
    start = _default(BENCH / "score-path" / "scripts" / "start_score_side.sh", "DA_START_TIMEOUT_S")
    stop_wait = _default(BENCH / "score-path" / "scripts" / "stop_score_side.sh", "DA_STOP_TIMEOUT_S")
    stop = stop_wait + 7 * 2 + 30       # + the left-over sweep (7 names, 2 s each) + the collection (allowance)
    staging = 60                        # stage_score_side.py: a copy of the bundle (allowance, no own bound)
    inject = 5 + 1 + 2 + 30             # lead-in, the 3-send plan, tail (inject_warning_requests.sh) + start-up
    part1 = staging + start + _default(CHECK, "DA_P10_1_PROBE_TIMEOUT_S") + inject + _default(CHECK, "DA_P10_1_C5_WAIT_S") + stop
    part2 = 3 * _default(CHECK, "DA_P10_1_ORT_TIMEOUT_S")
    part3 = (10 + staging + start + _default(CHECK, "DA_P10_1_SUPERVISED_WAIT_S") + _default(CHECK, "DA_P10_1_ALIVE_HOLD_S")
             + _default(CHECK, "DA_P10_1_STALL_HOLD_S") + stop)
    return part1 + part2 + part3


def test_the_p10_1_time_out_covers_the_check_and_ends_a_hung_check_before_the_cap() -> None:
    # V5: T_P10_1 was 5400 s, longer than the cap allows for both hosts (5316 s), so a hung check always ended
    # through the cap. It must cover the check's worst case with a margin, and the session must reach the step's
    # own time-out, its TERM wait and the pre-stop phase before the cap, with every step before it at its bound
    worst = check_worst_case_s()
    t = _session("T_P10_1")
    assert worst * 1.1 <= t <= worst * 1.5, (worst, t)
    hosts = (SESSION_DIR / "hosts.env").read_text()
    rate = sum(float(re.search(r'%s:=([0-9.]+)' % n, hosts).group(1)) for n in ("SIM_EUR_H", "SCORE_EUR_H"))
    cap = float(re.search(r'CAP_EUR_P10_1:=([0-9.]+)', hosts).group(1))
    cap_s = cap / rate * 3600
    assert round(cap_s) == 5316                                   # EUR 3.50 at 1.887 + 0.483 EUR/h
    before = _session("T_SIM_SETUP") + 60 + _session("T_WARMUP") + _session("T_READY")   # 60: the port test's call
    term_wait = _session("STEP_TERM_POLLS") * _session("POLL_S")
    assert before + t + term_wait < cap_s, (before, t, term_wait, cap_s)
    # P1: past the step's time-out the stops and fetches may run into the cap; the trap's pre-stop phase then holds
    # each at its bound (p10-1's budget, test_session_dryrun.py test_p1_...), and the safety net fires after it:
    # (CAP_S + that budget) / 60 + SAFETY_MARGIN_MIN, counted from the arming
    text = (SESSION_DIR / "da_session.sh").read_text()
    assert "gmin=$(( (CAP_S + PRESTOP_S) / 60 + SAFETY_MARGIN_MIN ))" in text
    assert "PRESTOP_S=$PRE_SUM" in text
    # the world holds longer than the check may run (RELEASE_WAIT_S = T_P10_1 + T_STEP)
    assert "RELEASE_WAIT_S=$(( T_P10_1 + T_STEP ))" in (SESSION_DIR / "da_session.sh").read_text()
