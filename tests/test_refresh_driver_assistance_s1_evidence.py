"""The refresh of the INC-DRIVING-002 S1 evidence directory from the evaluators' outputs and the fetched session.

``tools/refresh_driver_assistance_s1_evidence.py`` is the one command that regenerates every committed file whose
content comes from a verdict file, a desk record or the fetched session tree: the copies of the small JSON files, the
generator's reduced copy of the desk analysis of REQ-DRIVING-039, the dropped-image counts of each run, the SHA256SUMS
over the whole fetched tree, the verdict table of the README, and, through the generator, the model's evidence
records and case statuses. These tests run it on small synthetic inputs; the committed directory is pinned by
``test_driver_assistance_s1_evidence_directory.py``.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "refresh_driver_assistance_s1_evidence.py"


def _tool():
    spec = importlib.util.spec_from_file_location("refresh_s1", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


ANALYSIS_KEYS = ["configurationIdentity", "receiptSha256", "modelRevision", "analyzedRealization", "analystIdentity",
                 "claimBoundary"]


def _analysis(**extra) -> dict:
    full = {key: f"value of {key}" for key in ANALYSIS_KEYS}
    full.update({"outcome": "passBoundedVerification", "verdict": "pass", "findings": [{"id": "F1"}],
                 "criterion_items": ["loss"], "reason": None})
    full.update(extra)
    return full


def _verdicts() -> dict:
    run = {"run": "012_20_r1", "setting": "SC-DRIVING-012@20", "repetition": 1, "kind": "run",
           "runIdentity": "SC-DRIVING-012@20/r1"}
    second = {"run": "012_20_r2", "setting": "SC-DRIVING-012@20", "repetition": 2, "kind": "run",
              "runIdentity": "SC-DRIVING-012@20/r2"}
    stop = {"run": "stop", "setting": None, "repetition": None, "kind": "stop", "runIdentity": "stop"}
    cases = {
        "VC-DRIVING-036": {"requirement": "REQ-DRIVING-036", "outcome": "failObservedBehavior", "verdict": "fail",
                           "measured": {"runs": [
                               {"run": "012_20_r1", "outcome": "failObservedBehavior", "measured": {}},
                               {"run": "012_20_r2", "outcome": "inconclusiveMissingEvidence", "measured": {}}]}},
        "VC-DRIVING-037": {"requirement": "REQ-DRIVING-037", "outcome": "failObservedBehavior", "verdict": "fail",
                           "measured": {"runs": [
                               {"run": "012_20_r1", "outcome": "failObservedBehavior",
                                "measured": {"impactKmh": 19.746717, "approachKmh": 20.69}},
                               {"run": "012_20_r2", "outcome": "inconclusiveMissingEvidence", "measured": {}}]}},
        "VC-DRIVING-038": {"requirement": "REQ-DRIVING-038", "outcome": "inconclusiveMissingEvidence",
                           "verdict": "inconclusive",
                           "measured": {"runs": [
                               {"run": "012_20_r1", "outcome": "inconclusiveMissingEvidence", "measured": {}}],
                               "stopClause": {"run": "stop", "outcome": "inconclusiveMissingEvidence"}}},
    }
    return {"sessionId": "20991231T000000Z", "criteriaRecordIdentity": "sha256:c", "evaluatorRevision": "blobs:e",
            "runs": [run, second, stop], "cases": cases}


def test_the_reduced_analysis_keeps_the_six_attributes_the_outcome_and_a_reason_only():
    tool = _tool()
    reduced = tool.reduce_analysis(_analysis())
    assert list(reduced) == ANALYSIS_KEYS + ["outcome"], "no null reason, no findings"
    assert reduced["outcome"] == "passBoundedVerification"
    with_reason = tool.reduce_analysis(_analysis(reason="the record names no analyst"))
    assert with_reason["reason"] == "the record names no analyst"
    missing = _analysis()
    del missing["analystIdentity"]
    assert "analystIdentity" not in tool.reduce_analysis(missing), "a missing attribute stays missing"


def _tick(n: int, t: float, contact: int | None, target: bool = True) -> dict:
    """One tick's data as the world side writes it: the ego vehicle's speed and achieved acceleration, the target's
    speed, the collisions and the target contact. The synthetic contact begins at tick ``contact`` with targetContact
    alone, and the collision follows at the next tick; the ego vehicle runs at 5.5 m/s, 5.0 m/s on the tick before the
    contact and 2.0 m/s from the contact on, and achieves -0.05 m/s² throughout; the target runs at 4.0 m/s. A run
    without a target (``target`` false) has no target key, as the stop run's world record."""
    speed = 5.5 if contact is None or n < contact - 1 else 5.0 if n == contact - 1 else 2.0
    data = {"simTimeS": t, "frame": n, "ego": {"speedMps": speed, "longAccelMps2": -0.05},
            "collisions": [{"type": "collision"}] if contact is not None and n > contact else [],
            "targetContact": contact is not None and n >= contact}
    if target:
        data["target"] = {"speedMps": 4.0}
    return data


def _world(tree: Path, run: str, run_ticks: list[float], settle: int = 10, hold: int = 20,
           reason: str = "contact with the target", contact: int | None = None, target: bool = True) -> None:
    """The world side's files of one run, in the forms it writes them: world.jsonl with its tick lines among other
    lines, run_end.json, and tick_times.csv with every tick of the process (the settle ticks before the run, the run's
    ticks and the ticks it keeps making after the run's end)."""
    sim = tree / "sim" / "out" / f"world_{run}" / "simulator"
    sim.mkdir(parents=True)
    lines = [json.dumps({"event": "start", "data": {}})]
    lines += [json.dumps({"event": "tick", "t_real_ns": n, "data": _tick(n, t, contact, target)})
              for n, t in enumerate(run_ticks)]
    lines.append(json.dumps({"event": "end", "data": {"reason": reason}}))
    (sim / "world.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (sim / "run_end.json").write_text(json.dumps({"endReason": reason, "ticks": len(run_ticks)}), encoding="utf-8")
    step = 0.05
    rows = [run_ticks[0] - step * (settle - k) for k in range(settle)] + run_ticks
    rows += [run_ticks[-1] + step * (k + 1) for k in range(hold)]
    (sim / "tick_times.csv").write_text("sim_time_s,unix_s\n" + "".join(f"{t:.6f},{1000 + t:.6f}\n" for t in rows),
                                        encoding="utf-8")


#: the images of the synthetic run 012_20_r1: every 0.1 s from 10.0 s to 19.9 s, and the drops among them: five in
#: the first 5 s after the first image (one of them 4.9 s after it), one isolated inside the run, one isolated after the run's last tick and
#: three in the last second of the image stream, which goes on after the run's end
IMAGES = [round(10.0 + 0.1 * k, 6) for k in range(100)]
DROPS = [10.0, 10.1, 10.2, 13.0, 14.9, 16.0, 18.5, 19.6, 19.7, 19.8]
RUN_TICKS = [round(9.9 + 0.05 * k, 6) for k in range(143)]          # 9.9 s to 17.0 s
#: the tick of the synthetic run 012_20_r1 at which the contact begins: 16.0 s
CONTACT = 122
#: the stop run's score-interface record, each record with the S-CORE host's monotonic clock (mono_ns) as the interface
#: writes it: images every 0.1 s from 30.0 s to 30.4 s, each followed by a speed reading and a driving command, and two
#: drops; the stop instant of path_stop.json lies 50 ms after the image of 30.2 s and its command, so the newest
#: record before it is of 30.2 s, and the images of 30.3 and 30.4 s (one of them dropped) come after it
STOP_IMAGE_MONO = [10_000_000_000 + 100_000_000 * k for k in range(5)]
STOP_INSTANT_MONO = STOP_IMAGE_MONO[2] + 50_000_000
STOP_EVENTS = ([{"kind": "start", "mono_ns": 9_000_000_000}]
               + [e for k, m in enumerate(STOP_IMAGE_MONO) for e in (
                   {"kind": "in.camera_image", "sim_s": round(30.0 + 0.1 * k, 6), "mono_ns": m},
                   {"kind": "in.vehicle_speed", "sim_s": round(30.0 + 0.1 * k, 6), "mono_ns": m + 2_000_000},
                   {"kind": "out.driving_command", "issueTime_sim_s": round(30.0 + 0.1 * k, 6), "mono_ns": m + 5_000_000})
                   if k <= 2 or e["kind"] == "in.camera_image"]
               + [{"kind": "drop.camera_image", "sim_s": 30.0, "mono_ns": STOP_IMAGE_MONO[1] + 1_000},
                  {"kind": "drop.camera_image", "sim_s": 30.3, "mono_ns": STOP_IMAGE_MONO[4] + 1_000},
                  {"kind": "supervision.stop", "mono_ns": STOP_IMAGE_MONO[4] + 60_000_000}])
#: the driving commands that the actuation adapter of 012_20_r1 receives: issue time, verdict, acceleration. Each
#: accepted command holds until the next accepted one; the rejected one does not interrupt -0.4129, and the last one
#: comes after the contact at 16.0 s
COMMANDS = [(10.0, "accepted", 1.5), (12.0, "accepted", -0.4129), (12.5, "rejected", -3.0), (13.0, "accepted", -0.2),
            (15.0, "accepted", 0.5), (15.5, "accepted", -0.1), (16.5, "accepted", -0.3)]


def _session_tree(root: Path) -> Path:
    tree = root / "incoming_X"
    events = {"012_20_r1": [{"kind": "start"}, {"kind": "in.candidate_record"}]
              + [{"kind": "in.camera_image", "sim_s": t} for t in IMAGES]
              + [{"kind": "drop.camera_image", "sim_s": t} for t in DROPS]
              + [{"kind": "pass.camera_image", "sim_s": t} for t in IMAGES if t not in DROPS]
              + [{"kind": "out.driving_command", "issueTime_sim_s": t} for t in IMAGES[:17]],
              "stop": STOP_EVENTS}
    for run, lines in events.items():
        path = tree / "score" / "out" / f"score_{run}" / "score_side" / "run" / "score" / "score_interface.jsonl"
        path.parent.mkdir(parents=True)
        path.write_text("\n".join(json.dumps(e) for e in lines) + "\n", encoding="utf-8")
    _world(tree, "012_20_r1", RUN_TICKS, contact=CONTACT)
    state = tree / "score" / "out" / "score_012_20_r1" / "score_side" / "state"
    state.mkdir(parents=True)
    (state / "launch_manager.log").write_text(
        "[INFO]  starting\n[INFO]  [DE4SDV] warm start before the attach: 2 passes, result yes, 686.2 ms\n"
        "[INFO]  attached\n", encoding="utf-8")
    _world(tree, "stop", [round(29.9 + 0.05 * k, 6) for k in range(41)], reason="run cap", target=False)
    stop_record = tree / "score" / "out" / "path_stop_stop" / "path_stop.json"
    stop_record.parent.mkdir(parents=True)
    stop_record.write_text(json.dumps({"runTarget": "path_stopped", "stopInstantRealNs": 1_700_000_000_000_000_000,
                                       "stopInstantMonoNs": STOP_INSTANT_MONO, "rc": 0}), encoding="utf-8")
    for run, commands in {"012_20_r1": COMMANDS,
                          "stop": [(30.0, "accepted", 0.5), (30.1, "accepted", 0.00003)]}.items():
        adapter = tree / "score" / "out" / f"score_{run}" / "score_side" / "run" / "score" / "actuationAdapter.jsonl"
        lines = [{"event": "start", "data": {}}, {"event": "out.ackermann_control", "data": {"acceleration": -9.0}}]
        lines += [{"event": "in.driving_command", "data": {"issueTime_sim_s": t, "verdict": verdict, "acceleration": a}}
                  for t, verdict, a in commands]
        adapter.write_text("\n".join(json.dumps(e) for e in lines) + "\n", encoding="utf-8")
    (tree / "session.json").write_text(json.dumps({"session_id": "X"}), encoding="utf-8")
    (tree / "scenario_digests.json").write_text("{}", encoding="utf-8")
    (tree / "sim" / "out" / "chase_view.mp4").write_bytes(b"\x00video")
    return tree


def test_the_drop_counts_state_where_in_each_run_the_images_drop(tmp_path):
    """Each run's dropped images by where they fall: within 5 s of simulation time after its first image, within the
    last second of its image stream, and isolated in between (seconds after the first image); its received images;
    the run's end (run_end.json, and the ticks of tick_times.csv after it); and the drops that the evaluators count
    in a criterion over every run, those whose simulation time lies from the run's first to its last world tick
    (world.jsonl). The other kinds of the record are not counted (the correction of 2026-11-21: the distribution,
    never a rate)."""
    tool = _tool()
    counts = tool.drop_counts(_session_tree(tmp_path))
    assert sorted(counts) == ["012_20_r1", "stop"]
    assert counts["012_20_r1"] == {
        "file": "score/out/score_012_20_r1/score_side/run/score/score_interface.jsonl",
        "received": 100, "dropped": 10, "firstImageSimS": 10.0, "lastImageSimS": 19.9,
        "droppedInFirst5s": 5, "droppedAtStreamEnd": 3, "streamEndDropsWithinS": 0.3, "isolatedDropsS": [6.0, 8.5],
        "runEnd": {"file": "sim/out/world_012_20_r1/simulator/run_end.json", "endReason": "contact with the target",
                   "ticks": 143, "tickTimesFile": "sim/out/world_012_20_r1/simulator/tick_times.csv",
                   "ticksAfterRunEnd": 20, "egoSpeedAtLastTickKmh": 7.2, "targetSpeedAtLastTickKmh": 14.4},
        "wholeRunWindow": {"file": "sim/out/world_012_20_r1/simulator/world.jsonl", "firstTickSimS": 9.9,
                           "lastTickSimS": 17.0, "dropped": 6, "isolatedDropsS": [6.0]},
        "warmStart": {"file": "score/out/score_012_20_r1/score_side/state/launch_manager.log", "passes": 2,
                      "result": "yes", "ms": 686.2},
    }
    stop = counts["stop"]
    assert (stop["dropped"], stop["droppedInFirst5s"], stop["droppedAtStreamEnd"], stop["isolatedDropsS"]) \
        == (2, 2, 0, []), "a drop within 5 s of the first image is a start-up drop, even near the stream's end"
    assert stop["streamEndDropsWithinS"] is None
    assert stop["warmStart"] is None, "a run whose Launch Manager log records no warm start says so"
    assert stop["wholeRunWindow"]["dropped"] == 2 and stop["runEnd"]["endReason"] == "run cap"
    assert stop["runEnd"]["targetSpeedAtLastTickKmh"] is None, "a world record without a target says so"
    assert "stopInstant" not in counts["012_20_r1"], "only the run that stops the path has a stop instant"


def test_the_drop_counts_place_the_stop_instant_of_the_run_that_stops_the_path(tmp_path):
    """Review Q1 of 2026-11-21: the stop instant is that of path_stop.json, which the S-CORE host writes on its own
    monotonic clock, never the time of the last dropped image. The refresh maps it onto the run's score-interface
    record, which the same host writes on the same clock: the stop came at the simulation time of the newest record
    at or before the stop instant; the record gives the last driving command before it, how long the image stream
    goes on after it, the drops after it, and the world ticks that follow it in the whole-run window."""
    tool = _tool()
    tree = _session_tree(tmp_path)
    counts = tool.drop_counts(tree)
    stop = counts["stop"]
    assert "stopInstant" in stop, "the run that stops the path states its stop instant"
    assert stop["stopInstant"] == {
        "file": "score/out/path_stop_stop/path_stop.json", "stopInstantMonoNs": STOP_INSTANT_MONO,
        "simS": 30.2, "lastCommandIssueSimS": 30.2, "imageStreamAfterStopS": 0.2, "droppedAfterStop": 1,
        "ticksAfterStopS": 1.7}
    (tree / "score" / "out" / "path_stop_stop" / "path_stop.json").unlink()
    with pytest.raises(ValueError, match="path_stop.json"):
        tool.drop_counts(tree)


def test_the_drop_counts_refuse_a_run_whose_world_record_disagrees_with_its_end(tmp_path):
    """run_end.json's tick count is the number of world ticks; a run without its world files, or whose counts
    disagree, is refused by name, never counted with a guessed window."""
    tool = _tool()
    tree = _session_tree(tmp_path)
    end = tree / "sim" / "out" / "world_012_20_r1" / "simulator" / "run_end.json"
    end.write_text(json.dumps({"endReason": "contact with the target", "ticks": 142}), encoding="utf-8")
    with pytest.raises(ValueError, match="run_end.json"):
        tool.drop_counts(tree)
    end.unlink()
    with pytest.raises(ValueError, match="run_end.json"):
        tool.drop_counts(tree)


def test_the_commanded_deceleration_is_the_strongest_that_the_adapter_accepted_in_each_run(tmp_path):
    """The correction of 2026-11-21: the strongest commanded deceleration of each run, from the driving commands that
    the actuation adapter accepted (in.driving_command, data.acceleration, verdict accepted); a rejected command and
    the adapter's own control are no commanded deceleration, and a run with none says so."""
    tool = _tool()
    found = tool.commanded_deceleration(_session_tree(tmp_path))
    assert "runs" in found, "the runs of the file stand apart from its method"
    runs = found["runs"]
    assert sorted(runs) == ["012_20_r1", "stop"]
    assert {key: runs["012_20_r1"][key] for key in ("file", "acceptedCommands", "strongestDecelerationMps2")} == {
        "file": "score/out/score_012_20_r1/score_side/run/score/actuationAdapter.jsonl", "acceptedCommands": 6,
        "strongestDecelerationMps2": 0.413}
    assert runs["stop"] == {"file": "score/out/score_stop/score_side/run/score/actuationAdapter.jsonl",
                            "acceptedCommands": 2, "strongestDecelerationMps2": None}, \
        "a run of no setting of SC-DRIVING-012 has no contact to bound"


def test_the_commanded_deceleration_bounds_the_speed_that_it_takes_off_before_the_contact(tmp_path):
    """The deceleration calibration decision of 2026-11-21, as corrected: for each run of SC-DRIVING-012, the
    accepted driving commands, each held from its issueTime_sim_s until the next accepted one, up to the contact (the
    first world tick with a collision or targetContact), integrated over their decelerations as if the vehicle had
    fully achieved them: the speed they would have taken off before the contact, at most. The figures of the
    synthetic run: 0.4129 m/s² for 1.0 s, 0.2 m/s² for 2.0 s and 0.1 m/s² for 0.5 s, 0.8629 m/s or 3.1064 km/h,
    3.2 km/h rounded up to one decimal; the rejected command, the achieved acceleration of the world record (0.05
    m/s² throughout) and the command after the contact take nothing off; the last command with a deceleration before
    the contact comes 0.5 s before it; the speed on the tick before the contact is 5.0 m/s, 18.0 km/h."""
    tool = _tool()
    found = tool.commanded_deceleration(_session_tree(tmp_path))
    assert "runs" in found and "method" in found, "the file states its method beside the runs"
    contact = found["runs"]["012_20_r1"].get("beforeContact")
    assert contact is not None, "a run of SC-DRIVING-012 states what its commands take off before the contact"
    assert contact == {"worldFile": "sim/out/world_012_20_r1/simulator/world.jsonl", "contactFrame": 122,
                       "contactSimS": 16.0, "speedOnTickBeforeContactKmh": 18.0,
                       "lastNegativeCommandBeforeContactS": 0.5, "speedReductionIfAchievedKmh": 3.1064,
                       "speedReductionBoundKmh": 3.2}
    method = " ".join(found["method"].split())
    for phrase in ("SC-DRIVING-012", "first tick", "collisions", "targetContact", "in.driving_command",
                   "accepted", "issueTime_sim_s", "held until the next", "fully achieved", "rounded up to one decimal",
                   "speedOnTickBeforeContactKmh", "lastNegativeCommandBeforeContactS"):
        assert phrase in method, phrase


def test_the_commanded_deceleration_refuses_a_run_of_sc_driving_012_without_a_contact(tmp_path):
    """A run of SC-DRIVING-012 whose world record holds no contact, or no world record, is refused by name: its bound
    is never taken up to a guessed contact."""
    tool = _tool()
    tree = _session_tree(tmp_path)
    world = tree / "sim" / "out" / "world_012_20_r1" / "simulator" / "world.jsonl"
    lines = [json.loads(line) for line in world.read_text(encoding="utf-8").splitlines() if line.strip()]
    for line in lines:
        if line["event"] == "tick":
            line["data"].update(collisions=[], targetContact=False)
    world.write_text("\n".join(json.dumps(line) for line in lines) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="012_20_r1.*contact"):
        tool.commanded_deceleration(tree)
    world.unlink()
    with pytest.raises(ValueError, match="012_20_r1.*world.jsonl"):
        tool.commanded_deceleration(tree)


def test_the_checksums_cover_every_file_of_the_tree_by_its_relative_path(tmp_path):
    tool = _tool()
    tree = _session_tree(tmp_path)
    text = tool.sha256sums(tree)
    lines = text.splitlines()
    files = sorted(p.relative_to(tree).as_posix() for p in tree.rglob("*") if p.is_file())
    assert [line.split("  ", 1)[1] for line in lines] == files
    video = tree / "sim" / "out" / "chase_view.mp4"
    assert f"{hashlib.sha256(video.read_bytes()).hexdigest()}  sim/out/chase_view.mp4" in lines
    assert not any(line.split("  ", 1)[1].startswith("/") for line in lines), "relative paths only"
    assert text.endswith("\n")


def test_the_media_manifest_names_each_recording_of_the_tree_with_its_identity_and_retention(tmp_path):
    tool = _tool()
    tree = _session_tree(tmp_path)
    (tree / "guest" / "out" / "capture_stop").mkdir(parents=True)
    (tree / "guest" / "out" / "capture_stop" / "screencap_start_1.png").write_bytes(b"png")
    manifest = tool.media_manifest(tree)
    video = tree / "sim" / "out" / "chase_view.mp4"
    assert manifest["published"] is False
    paths = [entry["path"] for entry in manifest["artifacts"]]
    assert paths == ["guest/out/capture_stop/screencap_start_1.png", "sim/out/chase_view.mp4"], \
        "every recording, by its path in the session tree, and no record file"
    entry = manifest["artifacts"][1]
    assert entry == {"path": "sim/out/chase_view.mp4", "sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
                     "bytes": video.stat().st_size, "disposition": "observed_bounded",
                     "availability": "maintainer_archive"}


def test_the_verdict_table_is_rendered_from_the_verdicts_and_the_analysis():
    tool = _tool()
    table = tool.verdict_table(_verdicts(), tool.reduce_analysis(_analysis()))
    assert "| VC-DRIVING-036 | REQ-DRIVING-036 | `failObservedBehavior` | fail |" in table
    assert "| VC-DRIVING-038 | REQ-DRIVING-038 | `inconclusiveMissingEvidence` | inconclusive |" in table
    assert "| VC-DRIVING-039 | REQ-DRIVING-039 | `passBoundedVerification` | pass |" in table
    # the runs: one row per run of the verdicts, one column per case, and the impact speed of VC-DRIVING-037
    assert "| SC-DRIVING-012@20/r1 | fail | fail (19.7 km/h) | inconclusive |" in table
    assert "| SC-DRIVING-012@20/r2 | inconclusive | inconclusive | not read |" in table
    assert "| stop | not read | not read | inconclusive (stop clause) |" in table
    assert "evaluatorRevision `blobs:e`" in table and "criteriaRecordIdentity `sha256:c`" in table


def test_the_marked_block_is_replaced_and_nothing_else():
    tool = _tool()
    text = f"head\n{tool.BEGIN}\nold\n{tool.END}\ntail\n"
    assert tool.replace_marked(text, "new") == f"head\n{tool.BEGIN}\nnew\n{tool.END}\ntail\n"
    with pytest.raises(ValueError):
        tool.replace_marked("no markers\n", "new")


def test_the_refresh_writes_every_derived_file_of_the_evidence_directory(tmp_path):
    tool = _tool()
    tree = _session_tree(tmp_path)
    eval_dir = tmp_path / "eval"
    eval_dir.mkdir()
    (eval_dir / "verdicts.json").write_text(json.dumps(_verdicts()), encoding="utf-8")
    (eval_dir / "records.json").write_text(json.dumps({"records": {}}), encoding="utf-8")
    analysis = tmp_path / "analysis_039.json"
    analysis.write_text(json.dumps(_analysis()), encoding="utf-8")
    reproduction = tmp_path / "reproduction_044.json"
    reproduction.write_text(json.dumps({"valuesMatch": True}), encoding="utf-8")
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "README.md").write_text(f"# S1\n\n{tool.BEGIN}\n{tool.END}\n", encoding="utf-8")
    rc = tool.main(["--eval-dir", str(eval_dir), "--analysis-039", str(analysis), "--reproduction-044",
                    str(reproduction), "--session-tree", str(tree), "--evidence-dir", str(evidence),
                    "--no-generate"])
    assert rc == 0
    names = sorted(p.name for p in evidence.iterdir())
    assert names == ["README.md", "SHA256SUMS", "analysis_039.generator.json", "analysis_039.json",
                     "commanded_deceleration.json", "drop_counts.json", "external-media.json", "records.json", "reproduction_044.json",
                     "scenario_digests.json", "session.json", "verdicts.json"]
    assert json.loads((evidence / "external-media.json").read_text()) == tool.media_manifest(tree)
    assert (evidence / "analysis_039.json").read_bytes() == analysis.read_bytes(), "the full desk record, verbatim"
    assert json.loads((evidence / "analysis_039.generator.json").read_text()) == tool.reduce_analysis(_analysis())
    assert (evidence / "verdicts.json").read_bytes() == (eval_dir / "verdicts.json").read_bytes()
    assert "| VC-DRIVING-036 | REQ-DRIVING-036 |" in (evidence / "README.md").read_text()
    assert json.loads((evidence / "drop_counts.json").read_text()) == tool.drop_counts(tree)
    assert json.loads((evidence / "commanded_deceleration.json").read_text()) == tool.commanded_deceleration(tree)
    # a second run changes nothing
    before = {p.name: p.read_bytes() for p in evidence.iterdir()}
    assert tool.main(["--eval-dir", str(eval_dir), "--analysis-039", str(analysis), "--reproduction-044",
                      str(reproduction), "--session-tree", str(tree), "--evidence-dir", str(evidence),
                      "--no-generate"]) == 0
    assert {p.name: p.read_bytes() for p in evidence.iterdir()} == before


def test_the_refresh_writes_the_gains_file_that_the_generator_names(tmp_path):
    """The correction of 2026-11-21: the Ackermann gains of VC-DRIVING-036 and VC-DRIVING-037 go to
    ackermann_gains.json of the evidence directory, in the generator's own bytes, so that the case docs name them by
    identity; cases that disagree on the gains are refused."""
    tool = _tool()
    spec = importlib.util.spec_from_file_location("gen_s1", ROOT / "tools" / "generate_driver_assistance_evidence_text.py")
    gen = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = gen     # the generator's dataclasses look their module up
    spec.loader.exec_module(gen)
    gains = {"requested": [{"file": "session.json", "key": "ackermann_gains", "value": "v1"}], "readBack": []}
    verdicts = _verdicts()
    for vc in ("VC-DRIVING-036", "VC-DRIVING-037"):
        verdicts["cases"][vc]["measured"]["ackermannGains"] = gains
    assert tool.gains_file(verdicts) == gen.gains_record(gains)
    verdicts["cases"]["VC-DRIVING-037"]["measured"]["ackermannGains"] = {"requested": "unrecorded",
                                                                         "readBack": "unrecorded"}
    assert tool.gains_file(verdicts) == gen.gains_record(gains), "an unrecorded case holds no gains to compare"
    assert tool.gains_file(_verdicts()) is None, "no case records gains: no file"
    verdicts["cases"]["VC-DRIVING-037"]["measured"]["ackermannGains"] = {"requested": [], "readBack": []}
    with pytest.raises(ValueError, match="ackermannGains"):
        tool.gains_file(verdicts)
