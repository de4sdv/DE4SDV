"""The closure findings R1-R7 of the review of 1bfbd6b4 (phase10/REVIEW-CLOSURE-p10-2-1bfbd6b4.md), as dry runs.

The review's repro tests (RA, RA2, RA3, RB, RC, RD, RE) are ported here with the expected outcome of the fix; its
wrapper is tests/flip_gcloud.sh. Each test runs the real da_session.sh (or chase_recorder.py, fetch_owed.sh) against
the stateful fake gcloud of test_session_dryrun.py.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from test_session_dryrun import (G4, HERE, L4, MIB, OWED, RANGED, DD, Run, _dd, _ranges_tsv, _watch_lists,  # noqa: F401
                                 _vp_env, assert_invariants, finish, popen, run, vp_clone, wait_for_call)

FLIP = str(HERE / "flip_gcloud.sh")
BENCH = HERE.parent.parent
FETCH_OWED = HERE.parent / "fetch_owed.sh"


def _rec(r: Run) -> dict:
    return json.loads((r.incoming / "session.json").read_text())


def _pack(tmp: Path, vm: str = G4) -> tuple[str, int]:
    """The sha256 and size of the host's last pack in the fake (the file its dd ranges read)."""
    b = (tmp / "fake" / f"{vm}_out.tgz").read_bytes()
    return hashlib.sha256(b).hexdigest(), len(b)


def _wait_file(path: Path, text: str, timeout: float = 60) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists() and text in path.read_text():
            return
        time.sleep(0.05)
    raise AssertionError(f"{text!r} not in {path}")


# ───────────── R1: the host watch's TERM never costs another host its fetch ─────────────

def test_r1_ra_a_healthy_hosts_fetch_cut_by_the_watchs_term_for_another_host_is_fetched_again_in_its_slot(
        tmp_path: Path) -> None:
    # RA, the order of 20261120T092051Z: every run done, the G4's ranged fetch under way, the L4 preempted meanwhile
    # (here at the G4's first range read); the watch reads the L4 lost and TERMs main in the middle of the G4's fetch
    r = run(tmp_path, "p10-1", DA_GCLOUD=FLIP, FLIP_VM=L4, FLIP_ON="dd if=", FAKE_SLOW_FETCH=f"{G4}:4",
            DA_T_HOST_WATCH_S="0.5", **RANGED)
    rec = _rec(r)
    assert r.rc == 3, r.log
    assert rec["ended_by"] == "host lost: score (TERMINATED)", rec["ended_by"]
    assert rec["hosts_lost"]["score"]["detected_by"] == "host watch", rec["hosts_lost"]
    assert rec["fetched"] == ["sim"] and rec["not_fetched"] == [f"score: {OWED}"], (rec["fetched"], rec["not_fetched"])
    assert rec["fetch"]["sim"]["result"] == "ok", rec["fetch"]
    assert (r.incoming / "sim" / "out" / "session_id").read_text().strip() == "T"
    assert (r.incoming / "sim" / "out.tgz").read_bytes() == (tmp_path / "fake" / f"{G4}_out.tgz").read_bytes()
    assert f"the fetch from {G4} was interrupted: not fetched" not in r.log
    assert f"the fetch from {G4} was cut by the host watch's TERM for the loss of score" in r.log, r.log
    # two packs (the cut fetch and the trap's), and every range read before the G4's stop
    assert len(r.ssh(G4, "host_step.sh pack")) == 2
    assert max(_dd(r)) < r.stops(G4)[0]
    assert_invariants(r)


def test_r1_ra3_the_watch_skips_a_loss_main_already_named_and_the_abort_fetch_runs_whole(tmp_path: Path) -> None:
    # RA3: main's own poll names the S-CORE host lost and fetches the G4 in abort; the watch reads the same loss
    # during that fetch, and must neither TERM main nor name it again
    # the watch reads the L4 RUNNING until main's own HOST LOST line, then its loss (no race of who reads it first)
    r = run(tmp_path, "p10-1", DA_GCLOUD=FLIP, LIST_RUNNING=L4,
            LIST_RUNNING_UNTIL=f"{tmp_path}/ev/incoming_T/session.log|HOST LOST: {L4}",
            FAKE_LOST_AFTER=f"{L4}:start p10_1", FAKE_SLOW_FETCH=f"{G4}:8", DA_T_HOST_WATCH_S="3", **RANGED)
    rec = _rec(r)
    assert r.rc == 3, r.log
    assert rec["ended_by"] == "host lost: score (TERMINATED)" and rec["failed_step"] == "p10_1", rec
    assert rec["hosts_lost"]["score"]["detected_by"] == "a poll on its host", rec["hosts_lost"]
    # the row's preempted_at is filled in after GCP's operations read (R4: the row is written before it)
    assert re.match(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$", rec["hosts_lost"]["score"]["preempted_at"] or ""), \
        rec["hosts_lost"]
    assert rec["fetched"] == ["sim"] and rec["fetch"]["sim"]["result"] == "ok", rec
    # the watch did read during the fetch, after the loss, and skipped the known loss
    lost_at = r.ssh(L4, "start p10_1")[0]
    first_dd = min(_dd(r))
    assert [i for i in _watch_lists(r) if i > first_dd], "no watch read during the fetch"
    assert lost_at < first_dd
    assert "in the host watch" not in r.log and "interrupted" not in r.log, r.log
    assert_invariants(r)


def test_r1_ra2_a_loss_main_named_with_a_fast_watch_still_fetches_the_simulator_host(tmp_path: Path) -> None:
    # RA2: the same with a watch of 0.5 s (main or the watch may read the loss first)
    r = run(tmp_path, "p10-1", FAKE_LOST_AFTER=f"{L4}:start p10_1", FAKE_SLOW_FETCH=f"{G4}:4",
            DA_T_HOST_WATCH_S="0.5", **RANGED)
    rec = _rec(r)
    assert r.rc == 3, r.log
    assert rec["ended_by"] == "host lost: score (TERMINATED)", rec["ended_by"]
    assert "score" in rec["hosts_lost"] and rec["fetched"] == ["sim"], rec
    assert_invariants(r)


# ───────────── R2: an over-budget pack is a designed outcome, a fetch owed ─────────────

def test_r2_a_pack_over_the_fetch_budget_is_skipped_at_once_and_named_as_a_fetch_owed(tmp_path: Path) -> None:
    # the budget scaled to 2 + 3 = 5 s: the 3.5 MiB pack needs 64 s at 1 MB/s. S1's 2.2 GB pack needs 2260 s of 420 s
    t0 = time.monotonic()
    r = run(tmp_path, "p10-1", DA_T_TRAP_PACK_S="2", DA_T_TRAP_SCP_S="3", **RANGED)
    took = time.monotonic() - t0
    rec = _rec(r)
    assert r.rc == 5 and rec["ended_by"] == "fetch", r.log
    assert not _dd(r), "a range was read although the pack is over the budget"
    sha, size = _pack(tmp_path)
    assert rec["not_fetched"] == [f"sim: ~/da-kit/T/out.tgz sha256 {sha} {size} B (fetch owed)"], rec["not_fetched"]
    f = rec["fetch"]["sim"]
    assert f["result"].startswith("skipped") and f["sha256"] == sha and f["bytes"] == size, f
    assert f"fetch owed: see the README, \"A fetch owed\"" in r.log, r.log
    assert took < 40, took
    assert_invariants(r)


def test_r2_rc_a_failed_ranged_fetch_keeps_its_whole_ranges_and_names_the_fetch_owed(tmp_path: Path) -> None:
    # RC with the bound inside the budget: range 3 fails its 3 tries on a RUNNING host; ranges 0-2 came whole
    r = run(tmp_path, "p10-1", FAKE_RANGE_SHORT="3:9", **RANGED)
    rec = _rec(r)
    assert r.rc == 5 and rec["ended_by"] == "fetch" and rec["hosts_lost"] == {}, r.log
    d = r.incoming / "sim" / ".ranges"
    assert d.is_dir(), "the whole ranges already read were deleted"
    data = (tmp_path / "fake" / f"{G4}_out.tgz").read_bytes()
    for i in range(3):
        assert (d / f"p{i:06d}").read_bytes() == data[i * MIB:(i + 1) * MIB], i
    assert not (d / "p000003").exists()
    sha, size = _pack(tmp_path)
    assert (d / "pack").read_text().split() == [sha, str(size), "1"]
    assert rec["not_fetched"] == [f"sim: ~/da-kit/T/out.tgz sha256 {sha} {size} B (fetch owed; 3 of 4 ranges whole "
                                  "in sim/.ranges)"], rec["not_fetched"]
    assert_invariants(r)


def _fake_systemctl(tmp: Path, units: str = "") -> Path:
    b = tmp / "sysbin"
    b.mkdir(exist_ok=True)
    (b / "systemctl").write_text("#!/bin/bash\nprintf '%s' \"$FAKE_UNITS\"\n")
    (b / "systemctl").chmod(0o755)
    return b


def _fetch_owed(tmp: Path, r: Run, units: str = "", **extra: str) -> subprocess.CompletedProcess:
    b = _fake_systemctl(tmp)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("PYTHON", "FAKE_"))}
    env.update(FAKE_DIR=str(tmp / "fake"), FETCH_OWED_GCLOUD=str(HERE / "fake_gcloud.py"), FETCH_OWED_PAUSE_S="0.1",
               FETCH_OWED_SSH_PAUSE_S="0.1", FETCH_RANGE_MIB="1", FAKE_UNITS=units, PATH=f"{b}:{env['PATH']}", **extra)
    return subprocess.run(["bash", str(FETCH_OWED), str(r.incoming)], env=env, capture_output=True, text=True,
                          timeout=120)


def test_r2_the_hand_fetch_reads_an_owed_pack_on_a_started_simulator_host_and_stops_it(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-1", DA_T_TRAP_PACK_S="2", DA_T_TRAP_SCP_S="3", **RANGED)
    assert r.rc == 5, r.log
    n0 = len(r.calls)
    p = _fetch_owed(tmp_path, r)
    assert p.returncode == 0, p.stdout + p.stderr
    after = Run(tmp_path)
    new = after.calls[n0:]
    sha, size = _pack(tmp_path)
    assert (r.incoming / "sim" / "out.tgz").read_bytes() == (tmp_path / "fake" / f"{G4}_out.tgz").read_bytes()
    assert (r.incoming / "sim" / "out" / "session_id").read_text().strip() == "T"
    reads = sorted(int(DD.match(c[c.index("--command") + 1]).group(1)) for c in new if "--command" in c
                   and DD.match(c[c.index("--command") + 1]))
    assert reads == [0, 1, 2, 3], reads
    starts = [i for i, c in enumerate(new) if c[2:5] == ["compute", "instances", "start"] and c[5] == G4]
    stops = [i for i, c in enumerate(new) if c[2:5] == ["compute", "instances", "stop"] and c[5] == G4]
    assert len(starts) == 1 and stops and stops[-1] > max(i for i, c in enumerate(new) if "--command" in c)
    assert after.state[G4] == "TERMINATED" and after.state[L4] == "TERMINATED"
    assert "SHA OK" in p.stdout and "after: TERMINATED" in p.stdout, p.stdout
    got = json.loads((r.incoming / "sim" / "fetch_owed.json").read_text())
    assert got["sha256"] == sha and got["bytes"] == size and got["result"] == "ok", got


def test_r2_the_hand_fetch_reads_only_the_ranges_the_session_did_not_keep(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-1", FAKE_RANGE_SHORT="3:9", **RANGED)
    assert r.rc == 5, r.log
    n0 = len(r.calls)
    p = _fetch_owed(tmp_path, r)
    assert p.returncode == 0, p.stdout + p.stderr
    new = Run(tmp_path).calls[n0:]
    reads = [int(DD.match(c[c.index("--command") + 1]).group(1)) for c in new if "--command" in c
             and DD.match(c[c.index("--command") + 1])]
    assert reads == [3], reads
    assert (r.incoming / "sim" / "out.tgz").read_bytes() == (tmp_path / "fake" / f"{G4}_out.tgz").read_bytes()


def test_r2_the_hand_fetch_fails_on_a_sha256_other_than_the_sessions(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-1", DA_T_TRAP_PACK_S="2", DA_T_TRAP_SCP_S="3", **RANGED)
    assert r.rc == 5, r.log
    sha, _ = _pack(tmp_path)
    p = _fetch_owed(tmp_path, r, FETCH_OWED_SHA="0" * 64)
    assert p.returncode == 5 and "SHA MISMATCH" in p.stdout and "after: TERMINATED" in p.stdout, p.stdout + p.stderr
    assert json.loads((r.incoming / "sim" / "fetch_owed.json").read_text())["result"] == f"sha256 {sha}"
    assert not (r.incoming / "sim" / "out").exists()


@pytest.mark.parametrize("why", ["running", "unit"])
def test_r2_the_hand_fetch_refuses_a_running_simulator_host_or_an_active_session(tmp_path: Path, why: str) -> None:
    r = run(tmp_path, "p10-1", DA_T_TRAP_PACK_S="2", DA_T_TRAP_SCP_S="3", **RANGED)
    assert r.rc == 5, r.log
    if why == "running":
        st = json.loads((tmp_path / "fake" / "state.json").read_text())
        st["vm"][G4] = "RUNNING"
        (tmp_path / "fake" / "state.json").write_text(json.dumps(st))
    n0 = len(r.calls)
    p = _fetch_owed(tmp_path, r, units="da-session-X.scope loaded active running\n" if why == "unit" else "")
    assert p.returncode == 2 and "refused" in p.stdout, p.stdout + p.stderr
    new = Run(tmp_path).calls[n0:]
    assert not [c for c in new if c[2:5] in (["compute", "instances", "start"], ["compute", "instances", "stop"])]


def test_r2_the_readme_says_what_to_do_with_a_fetch_owed() -> None:
    text = (HERE.parent / "README.md").read_text()
    sec = text.split("### A fetch owed", 1)[1].split("\n## ", 1)[0].split("\n### ", 1)[0]
    for word in ("fetch_owed.sh", "not_fetched", "fetch.sim", "TERMINATED", "da-session-", "sha256", ".ranges",
                 "37 min", "EUR 1.3", "before any run", "3 min"):
        assert word in sec, word


# ───────────── R3: the trap's ranged fetch has its slot, not TRAP_SCP_S ─────────────

def test_r3_rb_the_traps_ranged_fetch_is_bounded_by_its_slot_and_says_so(tmp_path: Path) -> None:
    # the planning rate scaled so that the pack needs between 300 s (TRAP_SCP_S) and 420 s (the slot)
    p = popen(tmp_path, "p10-1", DA_T_FETCH_PLAN_BPS="11000", FAKE_HANG_STEP="p10_1:60", **RANGED)
    wait_for_call(tmp_path, lambda c: c[2:4] == ["compute", "ssh"] and any("status p10_1" in a for a in c))
    os.kill(p.pid, signal.SIGTERM)   # the main process only (systemctl --user kill --kill-who=main -s TERM)
    r = finish(tmp_path, p)
    assert r.rc == 143, r.log
    sha, size = _pack(tmp_path)
    b0 = 60 + -(-size // 11000)
    assert 300 < b0 <= 420, b0
    lines = [x for x in r.log.splitlines() if f"fetch of {G4} by ranges" in x]
    assert len(lines) == 1, lines
    assert f"bound {b0} s" in lines[0] and "fetch budget of a host: 420 s" in lines[0], lines[0]
    assert "cut to its slot's time left in the exit trap" in lines[0], lines[0]
    trap = [x for x in r.log.splitlines() if f"fetching {G4} before its stop" in x]
    assert len(trap) == 1 and "copy at most" not in trap[0] and "ranges" in trap[0], trap
    rec = _rec(r)
    assert rec["fetch"]["sim"]["bound_s"] == b0 and rec["fetch"]["sim"]["result"] == "ok", rec["fetch"]
    assert "sim" in rec["fetched"]
    assert_invariants(r)


def test_r3_the_traps_ranged_bound_is_cut_to_the_slots_time_left_after_the_pack(tmp_path: Path) -> None:
    # the fetch budget of a host scaled to 30 + 45 = 75 s; the 3.5 MiB pack needs 64 s; its pack call takes 20 s in the
    # trap, so 55 s of the slot are left: the bound is that, not 64 s and not TRAP_SCP_S (45 s)
    p = popen(tmp_path, "p10-1", DA_GCLOUD=FLIP, SLOW_PACK=f"{G4}:20", DA_T_TRAP_PACK_S="30", DA_T_TRAP_SCP_S="45",
              FAKE_HANG_STEP="p10_1:60", **RANGED)
    wait_for_call(tmp_path, lambda c: c[2:4] == ["compute", "ssh"] and any("status p10_1" in a for a in c))
    os.kill(p.pid, signal.SIGTERM)
    r = finish(tmp_path, p, timeout=150)
    assert r.rc == 143, r.log
    (line,) = [x for x in r.log.splitlines() if f"fetch of {G4} by ranges" in x]
    bound = int(re.search(r"; bound (\d+) s", line).group(1))
    assert 50 <= bound <= 55, line
    assert "plus the pack at 1000000 B/s: 64 s" in line and "cut to its slot's time left in the exit trap" in line
    assert _rec(r)["fetch"]["sim"]["result"] == "ok"
    assert_invariants(r)


def test_r3_the_main_paths_ranged_bound_keeps_its_label(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-1", DA_T_FETCH_PLAN_BPS="11000", **RANGED)
    assert r.rc == 0, r.log
    _, size = _pack(tmp_path)
    (line,) = [x for x in r.log.splitlines() if f"fetch of {G4} by ranges" in x]
    assert f"bound {60 + -(-size // 11000)} s" in line and "fetch budget of a host: 420 s)" in line, line
    assert "slot" not in line


# ───────────── R4: hosts_lost and ended_by survive a TERM ─────────────

def test_r4_a_watch_term_for_a_second_host_keeps_the_first_loss_and_its_row(tmp_path: Path) -> None:
    # main names the S-CORE host lost; during that loss's operations read (slowed) the G4 is lost too, and the watch
    # TERMs main for it. ended_by stays the first loss, and the first loss's row is in hosts_lost
    # the watch never reads the L4's loss (main names it), only the G4's
    r = run(tmp_path, "p10-1", DA_GCLOUD=FLIP, FLIP_VM=G4, FLIP_ON="operations list", SLOW_OPS="3", LIST_RUNNING=L4,
            FAKE_LOST_AFTER=f"{L4}:start p10_1", DA_T_HOST_WATCH_S="0.5", **RANGED)
    rec = _rec(r)
    assert r.rc == 3, r.log
    assert rec["ended_by"] == "host lost: score (TERMINATED)", rec["ended_by"]
    assert set(rec["hosts_lost"]) == {"score", "sim"}, rec["hosts_lost"]
    assert rec["hosts_lost"]["score"]["detected_by"] == "a poll on its host"
    assert rec["hosts_lost"]["sim"]["detected_by"] == "host watch"
    assert_invariants(r)


def test_r4_the_hosts_lost_row_is_written_before_the_operations_read(tmp_path: Path) -> None:
    # an operator's TERM while host_lost reads GCP's operations: the row is there, its preempted_at not yet
    p = popen(tmp_path, "p10-1", DA_GCLOUD=FLIP, SLOW_OPS="20", FAKE_LOST_AFTER=f"{L4}:start p10_1",
              DA_T_HOST_WATCH_S="600")
    _wait_file(tmp_path / "ev" / "incoming_T" / "commands.log", "compute operations list")
    time.sleep(0.3)
    os.kill(p.pid, signal.SIGTERM)
    r = finish(tmp_path, p)
    rec = _rec(r)
    assert "score" in rec["hosts_lost"], rec["hosts_lost"]
    lost = rec["hosts_lost"]["score"]
    assert lost["status"] == "TERMINATED" and lost["detected_by"] == "a poll on its host", lost
    assert f"p10-1 host lost: score (TERMINATED" in r.log
    assert_invariants(r)


def test_r4_re_the_watch_never_drops_the_row_of_a_loss_main_is_naming(tmp_path: Path) -> None:
    # RE as the review ran it: the operations read slowed, the watch at 0.5 s
    r = run(tmp_path, "p10-1", DA_GCLOUD=FLIP, SLOW_OPS="3", FAKE_LOST_AFTER=f"{L4}:start p10_1",
            DA_T_HOST_WATCH_S="0.5")
    rec = _rec(r)
    assert r.rc == 3, r.log
    assert "score" in rec["hosts_lost"], rec["hosts_lost"]
    assert rec["ended_by"] == "host lost: score (TERMINATED)", rec["ended_by"]
    assert "p10-1 host lost: score" in r.log
    assert_invariants(r)


# ───────────── R5: after a signal or the cap, hosts_lost and not_fetched first ─────────────

def test_r5_rd_a_loss_found_in_the_trap_after_an_operator_term_keeps_the_signal_and_names_the_loss(
        tmp_path: Path) -> None:
    # RD (a guard: this held at 1bfbd6b4): the README now says to read hosts_lost and not_fetched first
    p = popen(tmp_path, "p10-1", DA_GCLOUD=FLIP, FLIP_VM=L4, FAKE_HANG_STEP="p10_1:60", DA_T_HOST_WATCH_S="600")
    wait_for_call(tmp_path, lambda c: c[2:4] == ["compute", "ssh"] and any("status p10_1" in a for a in c))
    (tmp_path / "fake" / "flip").write_text("")
    time.sleep(0.3)
    os.kill(p.pid, signal.SIGTERM)
    r = finish(tmp_path, p)
    rec = _rec(r)
    assert r.rc == 143 and rec["ended_by"] == "signal TERM", (r.rc, rec["ended_by"])
    assert "score" in rec["hosts_lost"] and f"score: {OWED}" in rec["not_fetched"], rec
    assert_invariants(r)


def test_r5_the_readme_says_to_read_hosts_lost_and_not_fetched_first() -> None:
    text = re.sub(r"\s+", " ", (HERE.parent / "README.md").read_text())
    assert ("after a signal or the cap, `exit_code` and `ended_by` stay the signal's or the cap's; a host found lost "
            "in the trap is in `hosts_lost` and `not_fetched`: read those two first") in text


def test_r1_r5_the_readme_says_the_trap_fetches_a_cut_healthy_host_again() -> None:
    text = re.sub(r"\s+", " ", (HERE.parent / "README.md").read_text())
    assert "fetches every other host, stops every VM" not in text
    assert "a healthy host whose fetch that TERM cut is fetched again in its slot" in text
    assert "skips a role the session has already named lost" in text


# ───────────── R6: the fetch's time, in the durations and in the cap ─────────────

def test_r6_the_readme_durations_count_the_ranged_fetch_and_the_cap_includes_it() -> None:
    text = (HERE.parent / "README.md").read_text()
    sec = text.split("## Durations and costs", 1)[1].split("\n## ", 1)[0]
    flat = re.sub(r"\s+", " ", sec)
    assert "the fetch and the stops 2-5 min" not in flat
    assert "the fetch 5-7 min" in flat and "inside the cap" in flat, flat
    fetch = re.sub(r"\s+", " ", text.split("### The evidence fetch", 1)[1].split("\n## ", 1)[0])
    assert "in the exit trap `TRAP_SCP_S`" not in fetch


def test_r6_the_preflight_line_says_the_cap_includes_the_fetch(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-1")
    assert r.rc == 0, r.log
    m = re.search(r"the cap of [0-9.]+ EUR is \d+ s of all of them, the fetch at the end included \(a host by "
                  r"ranges up to (\d+) s, a host by scp up to (\d+) s\)", r.log)
    assert m and m.groups() == ("420", "1200"), r.log


# ───────────── R7 (T2): the recorder listens before the world starts ─────────────

def _recorder(tmp: Path, *extra: str, **env: str) -> tuple[subprocess.CompletedProcess, Path]:
    out = tmp / "rec"
    e = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
    e.update(PYTHONPATH=str(BENCH / "recording" / "tests" / "fake_carla"), FAKE_CARLA_FRAMES="5", **env)
    p = subprocess.run([sys.executable, "-B", str(BENCH / "recording" / "chase_recorder.py"), "--out", str(out),
                        "--width", "64", "--height", "36", "--encoder", "libx264", *extra], env=e,
                       capture_output=True, text=True, timeout=120)
    return p, out


def test_r7_the_recorder_writes_listening_with_the_hero_list_it_took(tmp_path: Path) -> None:
    # the hero appears 2 s after the world answers: the list the recorder took is empty, and it attaches to the hero
    p, out = _recorder(tmp_path, "--max-s", "30", FAKE_HERO_AFTER_S="2")
    assert p.returncode == 0, p.stdout + p.stderr
    lis = json.loads((out / "listening").read_text())
    assert lis["pre_existing_heroes"] == [] and isinstance(lis["unix_s"], float), lis
    assert json.loads((out / "summary.json").read_text())["ego_id"] == 77


def test_r7_a_hero_already_there_is_in_the_listening_list(tmp_path: Path) -> None:
    # the hero is there before the recorder lists: it is in the list (written after the list was taken)
    p, out = _recorder(tmp_path / "a", "--max-s", "3", FAKE_HERO_AFTER_S="0")
    assert json.loads((out / "listening").read_text())["pre_existing_heroes"] == [77], p.stdout + p.stderr


def test_r7_no_listening_file_without_a_simulator(tmp_path: Path) -> None:
    p, out = _recorder(tmp_path, "--sim-wait-s", "1", FAKE_CARLA_LOAD_S="60")
    assert p.returncode == 1 and not (out / "listening").exists()


def test_r7_each_recorded_run_waits_for_its_recorders_listening_file_before_its_world_starts(
        tmp_path: Path) -> None:
    r = run(tmp_path, "p10-2", "--without-guest-host")
    assert r.rc == 0, r.log
    for w in ("run1", "run2"):
        rec_start = r.ssh(G4, f"host_step.sh start rec_{w} ")[0]
        listen = r.ssh(G4, f"test -e $HOME/da-kit/T/out/rec_{w}/listening")
        world = r.ssh(G4, f"host_step.sh start world_{w} ")[0]
        assert listen and rec_start < listen[0] and listen[-1] < world, (rec_start, listen, world)
        assert f"the chase recorder of {w} listens" in r.log
    assert not r.ssh(G4, "rec_calib_steer/listening")
    assert not [s for s in r.sequence() if "listening" in s], r.sequence()


def test_r7_the_wait_for_listening_is_bounded_and_the_run_goes_on(tmp_path: Path) -> None:
    t0 = time.monotonic()
    r = run(tmp_path, "p10-2", "--without-guest-host", FAKE_NO_FILE="rec_run1/listening", DA_T_T_REC_LISTEN="2")
    assert r.rc == 0, r.log
    assert time.monotonic() - t0 < 100
    assert "WARNING no listening file of the chase recorder of run1 after 2 s" in r.log, r.log
    world = r.ssh(G4, "host_step.sh start world_run1 ")[0]
    assert r.ssh(G4, "rec_run1/listening")[-1] < world


def test_r7_a_recorder_that_ended_before_listening_lets_the_run_go_on_at_once(tmp_path: Path) -> None:
    t0 = time.monotonic()
    r = run(tmp_path, "p10-2", "--without-guest-host", DA_GCLOUD=FLIP, NO_LISTEN="rec_run1/listening")
    assert r.rc == 0, r.log
    assert time.monotonic() - t0 < 100   # never the 150 s bound
    assert "WARNING the chase recorder of run1 ended (rc 1) before its listening file" in r.log, r.log
    assert "the chase recorder of run2 listens" in r.log
