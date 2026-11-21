"""The candidate's visualization recording in the session (the owner's decision of 2026-11-17: keep the DE4SDV
visualization recorder in every run and state its delay), and the series check of the staged facts.

- Each run's S-CORE stop moves the recording into its out folder and writes visualization_recording.json
  (score-path/scripts/stop_score_side.sh). The pack leaves the video on the S-CORE host and lists it with its sha256 in
  out/pack_excluded.tsv; its sidecars (frames.csv, summary.txt) stay in the pack. session.json carries
  score_runs.<run>.visualization_recording {path, sha256, bytes, frames, reason}: the field
  case-evaluators/evidence_record.py reads (benchRecordingArtifact). A run without a record gets the field with a
  named reason, never a failed step.
- fetch_chase.sh --role score fetches the videos after the session from the S-CORE host alone, by the same rules as
  the chase videos' fetch (TERMINATED first, ranges, sha256 against the list, the stop in the trap, a refused start
  retried every 3 min).
- The per-run disk check counts the recording: 0.5 MB/s (the recorder's 4000 kbit/s) beside the Rerun record's
  88 MB/s, over the run's planned running, plus 10 % and 5 GB.
- The staged facts must list every patch of the kit's series for the selected candidate (score-interface/series.sh):
  pin 0001-0003 and 0005, pr427 0001-0005.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tarfile
from pathlib import Path

import pytest

from test_session_dryrun import FAKE, L4, _vp_env, assert_invariants, vp_clone  # noqa: F401 (the stand-in clone)
from test_session_s1 import (FACTS_PIN, FACTS_PR427, SESSION_DIR, _staged, record, s1_run)

FETCH = SESSION_DIR / "fetch_chase.sh"
ONE_RUN = "SC-DRIVING-012@20\tr1\n"
VIS = "out/score_012_20_r1/score_side/visualization/visualization.mkv"


# ───────────── the pack ─────────────


def test_the_pack_leaves_each_visualization_video_on_the_host_and_lists_its_sha256(tmp_path: Path) -> None:
    kit = tmp_path / "home" / "da-kit" / "S1"
    rem = kit / "bench" / "session" / "remote"
    rem.mkdir(parents=True)
    (rem / "host_step.sh").write_bytes((SESSION_DIR / "remote" / "host_step.sh").read_bytes())
    (kit / "session_id").write_text("S1\n")
    vids = {}
    for w, side in (("012_20_r1", True), ("stop", False)):
        d = kit / "out" / f"score_{w}" / "score_side" / "visualization"
        d.mkdir(parents=True)
        data = os.urandom(5000 + len(w))
        (d / "visualization.mkv").write_bytes(data)
        (d / "visualization.mkv.frames.csv").write_text("video_index,frame_id,sim_time_s\n0,1,100.05\n")
        (d / "visualization.mkv.summary.txt").write_text("written=1\n")
        st = (d / "visualization.mkv").stat()
        if side:   # the stop's side file: the pack takes the sha256 from it, as for a chase video
            (d / "visualization.mkv.sha256").write_text("%s %d %d\n" % (hashlib.sha256(data).hexdigest(), len(data),
                                                                        int(st.st_mtime)))
        vids[f"out/score_{w}/score_side/visualization/visualization.mkv"] = data
    p = subprocess.run(["bash", str(rem / "host_step.sh"), "pack"], capture_output=True, text=True,
                       env={**os.environ, "HOME": str(tmp_path / "home")})
    assert p.returncode == 0, p.stderr
    with tarfile.open(kit / "out.tgz") as t:
        names = set(t.getnames())
        listed = t.extractfile("out/pack_excluded.tsv").read().decode()
    assert not [n for n in names if n.endswith("visualization.mkv")], names
    for w in ("012_20_r1", "stop"):
        for side in ("visualization.mkv.frames.csv", "visualization.mkv.summary.txt"):
            assert f"out/score_{w}/score_side/visualization/{side}" in names, (w, side)
    assert sorted(listed.splitlines()) == sorted("%s\t%d\t%s" % (k, len(v), hashlib.sha256(v).hexdigest())
                                                 for k, v in vids.items()), listed
    assert all((kit / k).read_bytes() == v for k, v in vids.items())   # still on the host's disk


# ───────────── session.json ─────────────


def test_session_json_carries_each_runs_visualization_recording(tmp_path: Path) -> None:
    vr = {"path": "/home/x/da-kit/T/" + VIS, "sha256": "ab" * 32, "bytes": 1234567, "frames": 600, "reason": None}
    f = tmp_path / "vr.json"
    f.write_text(json.dumps(vr))
    r = s1_run(tmp_path, "--without-guest-host", "--camcal", "settings", runs=ONE_RUN,
               FAKE_PACK_ADD=f"out/score_012_20_r1/visualization_recording.json={f}")
    assert r.rc == 0, r.log
    runs = record(r)["score_runs"]
    assert runs["012_20_r1"].get("visualization_recording") == vr, runs["012_20_r1"]
    assert "600 frames" in r.log and "ab" * 32 in r.log


def test_a_run_without_a_visualization_record_gets_a_named_reason_and_no_failed_step(tmp_path: Path) -> None:
    r = s1_run(tmp_path, "--without-guest-host", "--camcal", "settings", runs=ONE_RUN)
    assert r.rc == 0, r.log
    rec = record(r)
    assert not rec["failed_step"]
    for run in ("calib_steer", "012_20_r1"):
        vr = rec["score_runs"][run].get("visualization_recording")
        assert isinstance(vr, dict), rec["score_runs"][run]
        assert set(vr) == {"path", "sha256", "bytes", "frames", "reason"}, vr
        assert vr["sha256"] is None and vr["reason"].startswith("no visualization_recording.json"), vr


def test_the_session_names_the_hand_fetch_of_the_visualization_videos(tmp_path: Path) -> None:
    tsv = tmp_path / "excluded.tsv"
    tsv.write_text("%s\t4321\t%s\n" % (VIS, "c" * 64))
    r = s1_run(tmp_path, "--without-guest-host", "--camcal", "settings", runs=ONE_RUN,
               FAKE_PACK_ADD=f"out/pack_excluded.tsv={tsv}")
    assert r.rc == 0, r.log
    assert {"path": VIS, "bytes": 4321, "sha256": "c" * 64} in record(r)["not_fetched_from_hosts"]["score"]
    lines = [ln for ln in r.log.splitlines() if "fetch_chase.sh --role score" in ln]
    assert lines and "visualization" in lines[0], r.log


def test_the_readme_names_the_visualization_fetch_after_an_s1() -> None:
    text = (SESSION_DIR / "README.md").read_text()
    assert "bash session/fetch_chase.sh --role score" in text


# ───────────── V4: the staged facts against the kit's series ─────────────


def _drop(facts: str, prefix: str) -> str:
    return "+".join(x for x in facts.split("+") if not x.startswith(prefix))


@pytest.mark.parametrize("candidate, facts, missing", [
    ("pin", _drop(FACTS_PIN, "0003-"), "0003-de4sdv-headless-display.diff"),
    ("pin", _drop(FACTS_PIN, "0005-"), "0005-de4sdv-warm-start.diff"),
    ("pin", _drop(FACTS_PIN, "0001-"), "0001-de4sdv-visualization-recorder.diff"),
    ("pr427", _drop(FACTS_PR427, "0005-"), "0005-de4sdv-warm-start.diff"),
    ("pr427", _drop(FACTS_PR427, "0002-"), "0002-de4sdv-score-interface.diff"),
    ("pin", "none", "0001-de4sdv-visualization-recorder.diff"),
])
def test_the_staged_facts_must_list_every_patch_of_the_kits_series(tmp_path: Path, candidate: str, facts: str,
                                                                   missing: str) -> None:
    r = s1_run(tmp_path, "--without-guest-host", "--camcal", "settings", "--candidate", candidate, runs=ONE_RUN,
               FAKE_TAIL_ADD="score_start_012_20_r1:" + _staged(facts))
    assert r.rc == 5, r.log
    rec = record(r)
    assert rec["failed_step"] == "score_start_012_20_r1"
    line = [ln for ln in r.log.splitlines() if "lack" in ln and "series" in ln]
    assert line and missing in line[0], r.log
    assert_invariants(r)


# ───────────── fetch_chase.sh --role score ─────────────


VIDEOS = {VIS: os.urandom(2 * 1048576 + 77),
          "out/score_stop/score_side/visualization/visualization.mkv": os.urandom(500000)}


def _incoming(tmp: Path, files: dict[str, bytes], sid: str = "S1V", wrong: str | None = None) -> Path:
    inc = tmp / "ev" / f"incoming_{sid}"
    (inc / "score" / "out").mkdir(parents=True)
    (inc / "score" / "out" / "session_id").write_text(sid + "\n")
    rows = []
    remote = tmp / "remote"
    for rel, data in files.items():
        (remote / rel).parent.mkdir(parents=True, exist_ok=True)
        (remote / rel).write_bytes(data)
        sha = hashlib.sha256(data).hexdigest() if rel != wrong else "0" * 64
        rows.append("%s\t%d\t%s" % (rel, len(data), sha))
    rows.append("out/score_012_20_r1/score_side/vision_pilot/visionpilot.rrd\t99")   # an rrd row: not the fetch's
    (inc / "score" / "out" / "pack_excluded.tsv").write_text("\n".join(rows) + "\n")
    return inc


def _fetch(tmp: Path, inc: Path, units: str = "", **extra: str) -> subprocess.CompletedProcess:
    (tmp / "fake").mkdir(exist_ok=True)
    fb = tmp / "fakebin"
    fb.mkdir(exist_ok=True)
    (fb / "systemctl").write_text("#!/bin/bash\nprintf '%s'\n" % units.replace("%", "%%"))
    (fb / "systemctl").chmod(0o755)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("FAKE_", "DA_"))}
    env.update(FAKE_DIR=str(tmp / "fake"), DA_GCLOUD=str(FAKE), FAKE_REMOTE_FILES=str(tmp / "remote"),
               PATH=f"{fb}:{env['PATH']}", DA_T_RETRY_S="0.2", DA_T_SSH_PAUSE_S="0.1", DA_T_STOP_POLL_S="0.1",
               DA_T_RUNNING_WAIT_S="1", FETCH_RANGE_MIB="1", FETCH_PARALLEL="3")
    env.update(extra)
    return subprocess.run(["bash", str(FETCH), "--dry-run", "--role", "score", str(inc)], env=env,
                          capture_output=True, text=True, timeout=180)


def _calls(tmp: Path) -> list[list[str]]:
    p = tmp / "fake" / "calls.log"
    return [json.loads(x)[1:] for x in p.read_text().splitlines()] if p.exists() else []


def _status(tmp: Path, vm: str = L4) -> str:
    return json.loads((tmp / "fake" / "state.json").read_text())["vm"][vm]


def test_fetch_score_fetches_each_video_by_ranges_checks_its_sha256_and_stops_the_host(tmp_path: Path) -> None:
    inc = _incoming(tmp_path, VIDEOS)
    p = _fetch(tmp_path, inc)
    assert p.returncode == 0, p.stdout + p.stderr
    for rel, data in VIDEOS.items():
        assert (inc / "score" / rel).read_bytes() == data
    calls = _calls(tmp_path)
    start = [i for i, c in enumerate(calls) if c[2:5] == ["compute", "instances", "start"]]
    stop = [i for i, c in enumerate(calls) if c[2:5] == ["compute", "instances", "stop"]]
    dd = [i for i, c in enumerate(calls) if c[2:4] == ["compute", "ssh"] and any(a.startswith("dd if=") for a in c)]
    assert len(start) == 1 and stop and dd and start[0] < dd[0] and dd[-1] < stop[-1]
    assert all(calls[i][5] == L4 for i in start + stop)
    assert all(calls[i][4] == L4 and "--ssh-flag=-T" in calls[i] for i in dd)
    assert len(dd) == 3 + 1   # 1 MiB ranges: 3 of the first video, 1 of the second
    assert _status(tmp_path) == "TERMINATED"
    rec = json.loads((inc / "score" / "fetch_visualization" / "fetch_visualization.json").read_text())
    assert rec["result"] == "ok" and rec["vm_status_after"] == "TERMINATED" and rec["vm"] == L4
    assert {f["path"]: f["result"] for f in rec["files"]} == {k: "ok" for k in VIDEOS}


def test_fetch_score_refuses_a_host_that_is_not_terminated(tmp_path: Path) -> None:
    inc = _incoming(tmp_path, VIDEOS)
    p = _fetch(tmp_path, inc, FAKE_INIT=f"{L4}:RUNNING")
    assert p.returncode == 2 and "TERMINATED" in p.stdout + p.stderr, p.stdout + p.stderr
    assert not [c for c in _calls(tmp_path) if c[2:4] == ["compute", "instances"] and c[4] in ("start", "stop")]
    assert _status(tmp_path) == "RUNNING"


def test_fetch_score_a_sha256_mismatch_fails_keeps_no_file_and_stops_the_host(tmp_path: Path) -> None:
    bad = "out/score_stop/score_side/visualization/visualization.mkv"
    inc = _incoming(tmp_path, VIDEOS, wrong=bad)
    p = _fetch(tmp_path, inc)
    assert p.returncode == 5, p.stdout + p.stderr
    assert not (inc / "score" / bad).exists() and not list((inc / "score").rglob("*.part"))
    assert (inc / "score" / VIS).read_bytes() == VIDEOS[VIS]
    assert _status(tmp_path) == "TERMINATED"


def test_fetch_score_retries_a_capacity_refusal_every_round(tmp_path: Path) -> None:
    inc = _incoming(tmp_path, VIDEOS)
    p = _fetch(tmp_path, inc, FAKE_START=f"{L4}:POOL|POOL|OK")
    assert p.returncode == 0, p.stdout + p.stderr
    assert len([c for c in _calls(tmp_path) if c[2:5] == ["compute", "instances", "start"]]) == 3
    assert p.stdout.count("no capacity") == 2
    assert _status(tmp_path) == "TERMINATED"


def test_fetch_takes_only_its_roles_rows(tmp_path: Path) -> None:
    # a chase video's row in the S-CORE host's list is not the score role's, and an unknown role is refused
    inc = _incoming(tmp_path, VIDEOS)
    with open(inc / "score" / "out" / "pack_excluded.tsv", "a") as f:
        f.write("out/rec_x/chase_view.mp4\t10\t%s\n" % ("d" * 64))
    p = _fetch(tmp_path, inc)
    assert p.returncode == 0, p.stdout + p.stderr
    assert not [c for c in _calls(tmp_path) if any("rec_x" in a for a in c)]
    env = {k: v for k, v in os.environ.items() if not k.startswith(("FAKE_", "DA_"))}
    q = subprocess.run(["bash", str(FETCH), "--dry-run", "--role", "guest", str(inc)], env=env, capture_output=True,
                       text=True, timeout=60)
    assert q.returncode == 2 and "role" in q.stdout + q.stderr, q.stdout + q.stderr
