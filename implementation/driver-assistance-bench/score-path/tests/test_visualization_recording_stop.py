"""The candidate's visualization recording at each S-CORE stop (the owner's decision of 2026-11-17: the DE4SDV
visualization recorder in every run of mode full).

The recorder (patch 0001) writes the video named by DE4SDV_VISUALIZATION_RECORD (the Launch Manager configuration:
/tmp/de4sdv-da-bench/run/visualization.mkv) and two sidecars beside it, <video>.frames.csv (one row per encoded
frame, sim_time_s last) and <video>.summary.txt. The stop moves the three into <out>/score_side/visualization/ (a
rename on one filesystem: nothing in the stop path copies the video), takes the video's sha256 (the one SHA256SUMS
holds) and writes <out>/visualization_recording.json {path, sha256, bytes, frames, reason}, which the session reads
into session.json score_runs.<run>.visualization_recording (case-evaluators/evidence_record.py reads that field). A
missing or empty video is recorded with a named reason and never fails the stop, as the chase recorder's own end
is not a failed step. <video>.sha256 ("<sha256> <bytes> <mtime s>") lets the pack list the video with its sha256
without hashing it again (session/remote/host_step.sh).
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS))
import fake_bundle  # noqa: E402

BENCH = TESTS.parents[1]
SCRIPTS = BENCH / "score-path" / "scripts"
START = SCRIPTS / "start_score_side.sh"
STOP = SCRIPTS / "stop_score_side.sh"


@pytest.fixture(scope="module")
def record_driver(tmp_path_factory: pytest.TempPathFactory) -> Path:
    try:
        return fake_bundle.build_record_driver(tmp_path_factory.mktemp("driver"))
    except RuntimeError as error:
        pytest.skip(str(error))


@pytest.fixture()
def bench(tmp_path: Path, record_driver: Path):
    setup = fake_bundle.make_bundle(tmp_path, record_driver)
    yield setup
    subprocess.run(["bash", str(STOP), str(tmp_path / "cleanup")], env=setup["env"], capture_output=True)


def run(script: Path, *args: str, env: dict, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(script), *args], capture_output=True, text=True, env=env, cwd=BENCH,
                          timeout=timeout)


def _start_stop(bench: dict, out: Path, frames: str | None) -> tuple[subprocess.CompletedProcess, int | None]:
    env = dict(bench["env"])
    if frames is not None:
        env["DA_STUB_VP_VISUALIZATION"] = frames
    started = run(START, str(out), "10.164.0.2", env=env)
    assert started.returncode == 0, started.stdout + started.stderr
    return run(STOP, str(out), env=env), None


def test_the_candidates_environment_names_the_video_in_the_stage(bench: dict, tmp_path: Path) -> None:
    out = tmp_path / "out"
    stopped, _ = _start_stop(bench, out, None)
    assert stopped.returncode == 0, stopped.stdout + stopped.stderr
    line = (out / "score_side" / "run" / "score" / "stubs" / "vision_pilot.log").read_text().splitlines()[0]
    assert f"DE4SDV_VISUALIZATION_RECORD={bench['stage']}/run/visualization.mkv" in line, line
    assert f"GST_REGISTRY={bench['stage']}/gst/registry.x86_64.bin" in line, line


def test_the_stop_moves_the_recording_hashes_it_and_records_it(bench: dict, tmp_path: Path) -> None:
    out = tmp_path / "out"
    env = dict(bench["env"], DA_STUB_VP_VISUALIZATION="5")
    assert run(START, str(out), "10.164.0.2", env=env).returncode == 0
    stopped = run(STOP, str(out), env=env)
    assert stopped.returncode == 0, stopped.stdout + stopped.stderr
    staged = bench["stage"] / "run" / "visualization.mkv"
    v = out / "score_side" / "visualization" / "visualization.mkv"
    assert v.is_file(), "the stop moved no visualization.mkv into score_side/visualization/"
    assert not staged.exists(), "the video is still in the stage: copied, not moved"
    for side in ("visualization.mkv.frames.csv", "visualization.mkv.summary.txt"):
        assert (out / "score_side" / "visualization" / side).is_file(), side
        assert not (out / "score_side" / "run" / side).exists(), side   # moved, not collected twice
    assert not (out / "score_side" / "run" / "visualization.mkv").exists()
    data = v.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    f = out / "visualization_recording.json"
    assert f.is_file(), "the stop wrote no visualization_recording.json"
    rec = json.loads(f.read_text())
    assert rec == {"path": str(v), "sha256": sha, "bytes": len(data), "frames": 5, "reason": None}, rec
    sums = dict(reversed(x.split("  ", 1)) for x in (out / "score_side" / "SHA256SUMS").read_text().splitlines())
    assert sums["./visualization/visualization.mkv"] == sha
    assert (v.parent / "visualization.mkv.sha256").read_text().split() == [sha, str(len(data)),
                                                                           str(int(v.stat().st_mtime))]
    assert "VISUALIZATION_RECORDING " in stopped.stdout


def test_the_move_is_a_rename_on_one_filesystem(bench: dict, tmp_path: Path) -> None:
    # nothing in a stop path may scale with the recording's length (bash-session-runner-hardening): the video keeps
    # its inode
    out = tmp_path / "out"
    env = dict(bench["env"], DA_STUB_VP_VISUALIZATION="3")
    assert run(START, str(out), "10.164.0.2", env=env).returncode == 0
    stopped = run(STOP, str(out), env=env)
    assert stopped.returncode == 0, stopped.stdout + stopped.stderr
    # the stub recorder wrote the video's inode beside its log when it closed the video
    ino = out / "score_side" / "run" / "score" / "stubs" / "vision_pilot.vis_inode"
    assert ino.is_file(), "the stub recorder wrote no video (DE4SDV_VISUALIZATION_RECORD not in its environment)"
    v = out / "score_side" / "visualization" / "visualization.mkv"
    assert v.is_file(), "the stop moved no visualization.mkv into score_side/visualization/"
    assert str(os.stat(v).st_ino) == ino.read_text().strip(), "the video was copied, not renamed"


@pytest.mark.parametrize("frames, reason", [(None, "no visualization recording"),
                                            ("0", "empty visualization recording")])
def test_a_missing_or_empty_recording_is_recorded_with_its_reason_and_fails_nothing(bench: dict, tmp_path: Path,
                                                                                    frames, reason) -> None:
    out = tmp_path / "out"
    stopped, _ = _start_stop(bench, out, frames)
    assert stopped.returncode == 0, stopped.stdout + stopped.stderr
    f = out / "visualization_recording.json"
    assert f.is_file(), "the stop wrote no visualization_recording.json"
    rec = json.loads(f.read_text())
    assert rec["sha256"] is None and rec["reason"].startswith(reason), rec
    assert set(rec) == {"path", "sha256", "bytes", "frames", "reason"}
    assert "COLLECTION INCOMPLETE" not in stopped.stdout
    assert (bench["stage"] / "state" / "collected").is_file()


def test_mode_path_writes_no_visualization_record(bench: dict, tmp_path: Path) -> None:
    # p10-1 and p10-3 run the warning path only: no candidate, so no recording and no record of one
    out = tmp_path / "out"
    assert run(START, str(out), "none", env=bench["env"]).returncode == 0
    stopped = run(STOP, str(out), env=bench["env"])
    assert stopped.returncode == 0, stopped.stdout + stopped.stderr
    assert not (out / "visualization_recording.json").exists()
    assert not (out / "score_side" / "visualization").exists()
    assert "VISUALIZATION_RECORDING" not in stopped.stdout
