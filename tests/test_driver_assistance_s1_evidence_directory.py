"""INC-DRIVING-002 phase 10, second slice: the evidence directory of the judged session S1.

``implementation/driver-assistance-bench/evidence/s1-20261121T014447Z/`` holds the small records the model's evidence
text is generated from, and the identities of the session tree and the media it leaves outside Git. These pins hold
the directory to what ``tools/refresh_driver_assistance_s1_evidence.py`` writes from those records, so that no value
that comes from a verdict file is copied by hand, and to the README's statements of retention, publication and the
condition of record (the evidence-of-record decision of 2026-11-21).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "implementation" / "driver-assistance-bench" / "evidence" / "s1-20261121T014447Z"
TOOL = ROOT / "tools" / "refresh_driver_assistance_s1_evidence.py"
SESSION = "20261121T014447Z"
FILES = ["README.md", "SHA256SUMS", "VIDEO-EVIDENCE-DISPOSITION.md", "ackermann_gains.json",
         "analysis_039.generator.json", "analysis_039.json", "commanded_deceleration.json", "drop_counts.json", "external-media.json", "records.json", "reproduction_044.json",
         "scenario_digests.json", "session.json", "verdicts.json"]
#: the runs of S1 whose score-interface record the drop counts read: the 14 runs of SC-DRIVING-012 to SC-DRIVING-015, the run that stops
#: the path and the steering calibration run
RUNS = ["012_20_r1", "012_20_r2", "012_42_r1", "012_42_r2", "012_60_r1", "012_60_r2", "013_30_r1", "013_30_r2",
        "013_60_r1", "013_60_r2", "014_30_r1", "014_30_r2", "015_40_r1", "015_40_r2", "calib_steer", "stop"]
MEDIA_SUFFIXES = (".mp4", ".mkv", ".png", ".rrd", ".tgz", ".mov", ".wav")


def _tool():
    spec = importlib.util.spec_from_file_location("refresh_s1", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _json(name: str) -> dict:
    path = EVIDENCE / name
    assert path.is_file(), f"the evidence directory has no {name}"
    return json.loads(path.read_text(encoding="utf-8"))


def _readme() -> str:
    return " ".join((EVIDENCE / "README.md").read_text(encoding="utf-8").split())


def test_the_directory_holds_the_small_records_and_no_media():
    assert EVIDENCE.is_dir(), "no evidence directory of S1"
    assert sorted(p.name for p in EVIDENCE.iterdir()) == FILES
    for path in EVIDENCE.iterdir():
        assert path.stat().st_size < 600_000, f"{path.name} is not well under 1 MB"
        assert path.suffix.lower() not in MEDIA_SUFFIXES, path.name


def test_the_verdicts_the_records_and_the_session_name_one_session_and_one_evaluator_revision():
    verdicts, records, session = _json("verdicts.json"), _json("records.json"), _json("session.json")
    assert verdicts["sessionId"] == records["sessionId"] == session["session_id"] == SESSION
    assert verdicts["evaluatorRevision"] == records["evaluatorRevision"]
    assert verdicts["criteriaRecordIdentity"] == records["criteriaRecordIdentity"]
    assert session["bench_commit"].startswith("508649ba") and session["exit_code"] == 0
    assert sorted(verdicts["cases"]) == sorted(f"VC-DRIVING-0{n}" for n in range(36, 45) if n != 39)
    assert [r["run"] for r in verdicts["runs"]] == list(records["records"])
    reproduction = _json("reproduction_044.json")
    assert isinstance(reproduction["valuesMatch"], bool) and reproduction["sessionId"] == SESSION
    assert "independent" in reproduction["engineer"] and "no access to the lead's notes" in reproduction["engineer"]


def test_the_reduced_analysis_is_the_full_desk_records_reduction():
    full = _json("analysis_039.json")
    assert "findings" in full, "the full desk record, with its findings, is the retained record"
    assert _json("analysis_039.generator.json") == _tool().reduce_analysis(full)


def test_the_checksums_cover_the_session_tree_by_relative_path_and_bind_the_copied_records():
    lines = (EVIDENCE / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    assert len(lines) > 2000, "the whole fetched tree, not a sample"
    entries = dict(reversed(line.split("  ", 1)) for line in lines)
    for line in lines:
        digest, path = line.split("  ", 1)
        assert re.fullmatch(r"[0-9a-f]{64}", digest) and not path.startswith("/") and ".." not in path.split("/")
    assert [line.split("  ", 1)[1] for line in lines] == sorted(entries), "sorted by path"
    for name in ("session.json", "scenario_digests.json"):
        assert entries[name] == hashlib.sha256((EVIDENCE / name).read_bytes()).hexdigest(), \
            f"the committed {name} is the tree's"
    media = _json("external-media.json")
    assert media["published"] is False and media["policy"] == "docs/evidence-management.md"
    assert media["artifacts"], "the manifest lists the recordings"
    for entry in media["artifacts"]:
        assert entries[entry["path"]] == entry["sha256"], entry["path"]
        assert entry["bytes"] > 0 and entry["disposition"] == "observed_bounded"
        assert entry["availability"] == "maintainer_archive"
    kinds = {Path(e["path"]).suffix for e in media["artifacts"]}
    assert {".mp4", ".png", ".tgz"} <= kinds


def test_the_drop_counts_name_each_run_of_s1_and_where_its_images_drop():
    """Each run's drops by where they fall (the correction of 2026-11-21: the distribution, never a rate): 23 or 24
    in the first 5 s after the first image of each of the 14 runs, a few in the last second of its image stream, which
    goes on after the run's last world tick, and the isolated ones in between; and the drops that the evaluators
    count over every run, from the run's first to its last world tick."""
    counts = _json("drop_counts.json")
    assert sorted(counts) == sorted(RUNS)
    for run, count in counts.items():
        assert count["file"] == f"score/out/score_{run}/score_side/run/score/score_interface.jsonl"
        world = f"sim/out/world_{run}/simulator/"
        assert count["runEnd"]["file"] == world + "run_end.json"
        assert count["runEnd"]["tickTimesFile"] == world + "tick_times.csv"
        assert count["wholeRunWindow"]["file"] == world + "world.jsonl"
        assert count["dropped"] == (count["droppedInFirst5s"] + count["droppedAtStreamEnd"]
                                    + len(count["isolatedDropsS"])), run
        assert 0 < count["droppedInFirst5s"] <= count["dropped"] < count["received"], run
        window = count["wholeRunWindow"]
        assert set(window["isolatedDropsS"]) <= set(count["isolatedDropsS"]), run
        assert window["firstTickSimS"] < count["firstImageSimS"] < window["lastTickSimS"], run
    for run in RUNS[:14]:
        count = counts[run]
        assert count["droppedInFirst5s"] in (23, 24), run
        assert count["lastImageSimS"] > count["wholeRunWindow"]["lastTickSimS"], \
            f"{run}: the image stream goes on after the run's last world tick"
        assert count["runEnd"]["ticksAfterRunEnd"] > 0, run
        # the evaluators count the start-up drops and the isolated drops inside the run, and no drop of the end
        assert count["wholeRunWindow"]["dropped"] == count["droppedInFirst5s"] + len(
            count["wholeRunWindow"]["isolatedDropsS"]), run
        assert 2 <= count["droppedAtStreamEnd"] <= 6 and count["streamEndDropsWithinS"] <= 0.6, run
    for run, count in counts.items():
        # the warm start of D-S1-1 ran before the attach in every run, as its Launch Manager log records
        warm = count["warmStart"]
        assert warm["file"] == f"score/out/score_{run}/score_side/state/launch_manager.log", run
        assert (warm["passes"], warm["result"]) == (2, "yes") and warm["ms"] > 0, run


def test_the_readme_table_is_generated_from_the_verdicts():
    tool = _tool()
    text = (EVIDENCE / "README.md").read_text(encoding="utf-8")
    table = tool.verdict_table(_json("verdicts.json"), _json("analysis_039.generator.json"))
    assert f"{tool.BEGIN}\n{table}\n{tool.END}" in text, "regenerate with tools/refresh_driver_assistance_s1_evidence.py"


def test_the_readme_states_the_condition_of_record_retention_and_no_publication():
    readme = _readme()
    for phrase in ("Status: draft. Nothing in this directory or in the session tree is published.",
                   "The results are not shown to the VisionPilot maintainers yet, and the owner approves any text "
                   "before they are.",
                   "S1 is the evidence of record on one condition (the evidence-of-record decision of 2026-11-21): "
                   "the bench files that ran on a host are byte-identical to those that #549 merges.",
                   "git diff --stat 508649ba <merged> -- implementation/driver-assistance-bench",
                   "It must list only files that did not run on a host",
                   "stated at the on-demand rate of the L4 host, 0.806 EUR/h",
                   "The session cost 4.952 EUR (`cost.log` in the session tree).",
                   "The drop rule stands (the drop-rule decision of 2026-11-21).",
                   "they are diagnosis only, never a verdict",
                   "is retained on the maintainer's host, outside Git.",
                   "`sha256sum -c SHA256SUMS`",
                   "None is in Git, none is published, and the location is a maintainer archive, not public "
                   "evidence.",
                   "a fail is a fail of that build there, and no outcome is a statement about compliance, approval "
                   "or on-road behavior.",
                   "python tools/refresh_driver_assistance_s1_evidence.py"):
        assert phrase in readme, phrase
    assert not re.search(r"(?i)\b(?:behaviour|instrument cluster|certified|compliant)\b", readme)
    disposition = " ".join((EVIDENCE / "VIDEO-EVIDENCE-DISPOSITION.md").read_text(encoding="utf-8").split())
    for phrase in ("No recording of the judged session S1 is in Git, and none is published.",
                   "No case reads a recording.", "No publication cut exists.",
                   "A maintainer archive is not public evidence."):
        assert phrase in disposition, phrase


def test_the_readme_states_where_the_images_drop_as_the_evaluators_count_them():
    """The correction of 2026-11-21: the README states the distribution of the drops from drop_counts.json, never a
    rate and no cause, and which of them the evaluators count in a criterion over every run."""
    counts = _json("drop_counts.json")
    judged = [counts[run] for run in RUNS[:14]]
    start = " or ".join(str(n) for n in sorted({c["droppedInFirst5s"] for c in judged}))

    def span(values):
        return f"{min(values)} to {max(values)}"

    readme = _readme()
    for phrase in ("## The dropped images",
                   "the correction of 2026-11-21: the distribution, never a rate",
                   f"Each of the 14 runs of SC-DRIVING-012 to SC-DRIVING-015 drops {start} images in the first 5 s after its first image, "
                   f"{span([c['droppedAtStreamEnd'] for c in judged])} in the last "
                   f"{max(c['streamEndDropsWithinS'] for c in judged):g} s of its image stream, which goes on after the "
                   "run's last world tick until the S-CORE side stops, and "
                   f"{span([len(c['isolatedDropsS']) for c in judged])} isolated images in between.",
                   "The case evaluators at `508649ba` judge a criterion over every run in the window from the run's "
                   "first to its last world tick (`world.jsonl`) and count each `drop.camera_image` whose simulation "
                   "time lies in it (`Run.drops_in` in `runio_da.py`, `whole_run` in `cases_da.py`): "
                   f"{span([c['wholeRunWindow']['dropped'] for c in judged])} in each of the 14 runs, the start-up drops "
                   "and the isolated drops inside the run, and none of the end of the image stream; "
                   f"{counts['stop']['wholeRunWindow']['dropped']} in the run that stops the path.",
                   "The final verdicts come from the case evaluators at `44fe1608` (the evaluatorRevision of "
                   "`verdicts.json`), whose `Run.drops_in` and `whole_run` are those of `508649ba`.",
                   warm_start_sentence(counts),
                   "The records show no cause of the drops."):
        assert phrase in readme, phrase
    assert not re.search(r"\b(?:1|one) (?:camera )?image in 20\b", readme)


def warm_start_sentence(counts: dict) -> str:
    """The warm start of D-S1-1 in every run, as each run's Launch Manager log records it (drop_counts.json)."""
    ms = [c["warmStart"]["ms"] for c in counts.values()]
    return (f"The warm start of D-S1-1 (patch 0005 of the bench) ran before the attach in every run: the Launch "
            f"Manager log of each run records 2 passes with the result yes, in {min(ms):.1f} to {max(ms):.1f} ms "
            "(`score_side/state/launch_manager.log`). It did not keep the first 5 s after the first image free of "
            "dropped images.")


#: the settings of SC-DRIVING-012, both runs of each, in the order of RUNS[:6]
SETTINGS_012 = (20, 42, 60)


def _pairs(values: list, unit: str) -> list[str]:
    """Each setting's two values, as the README states them: '<a> and <b> <unit> at <kmh> km/h'."""
    return [f"{a} and {b} {unit} at {kmh} km/h" for (a, b), kmh in zip(zip(values[0::2], values[1::2]), SETTINGS_012)]


def _ceil1(value: float) -> float:
    """A bound rounded up to one decimal, so that it stays a bound."""
    return math.ceil(round(value, 9) * 10) / 10


def test_the_commanded_deceleration_of_each_run_and_no_run_of_sc_driving_012_stronger_than_0_533():
    """The correction of 2026-11-21, corrected again: the strongest accepted driving command of a run of
    SC-DRIVING-012 is 0.533 m/s² (0.5329731 m/s² in 012_20_r2, which is beyond 0.53), so no text bounds it by 0.53;
    the README states 0.533 and the strongest of each run to two decimals."""
    found = _json("commanded_deceleration.json")
    assert isinstance(found.get("method"), str) and found["method"].strip(), "the file states its method"
    runs = found["runs"]
    assert sorted(runs) == sorted(RUNS)
    for run, entry in runs.items():
        assert entry["file"] == f"score/out/score_{run}/score_side/run/score/actuationAdapter.jsonl"
        assert entry["acceptedCommands"] > 0, run
    strongest = [runs[run]["strongestDecelerationMps2"] for run in RUNS[:6]]
    assert all(isinstance(v, float) and 0 < v <= 0.533 for v in strongest), strongest
    assert f"{max(strongest):.3f}" == "0.533" and runs["012_20_r2"]["strongestDecelerationMps2"] == 0.533
    readme = _readme()
    assert ("In no run of SC-DRIVING-012 did the candidate command a deceleration stronger than 0.533 m/s²: the "
            "strongest driving command that the actuation adapter accepted holds "
            + "; ".join(_pairs([f"{v:.2f}" for v in strongest], "m/s²"))
            + " (rounded to two decimals; `commanded_deceleration.json` holds three).") in readme
    assert "beyond 0.53" not in readme and "no braking" not in readme


def test_the_five_judged_runs_of_sc_driving_012_command_no_deceleration_stronger_than_0_46():
    """The texts that speak of the five judged runs of SC-DRIVING-012 bound their commanded deceleration by 0.46
    m/s², not by 0.533: 0.533 m/s² comes from 012_20_r2, which is not judged. The judged runs are those that
    VC-DRIVING-036 gives a verdict; their strongest accepted command is 0.459 m/s² to three decimals, so the exact
    value is below 0.46, and 0.46 is the tightest bound to two decimals."""
    measured = _json("verdicts.json")["cases"]["VC-DRIVING-036"]["measured"]["runs"]
    judged = [e["run"] for e in measured
              if e["setting"].startswith("SC-DRIVING-012@") and e["outcome"] != "inconclusiveMissingEvidence"]
    assert judged == ["012_20_r1", "012_42_r1", "012_42_r2", "012_60_r1", "012_60_r2"], judged
    runs = _json("commanded_deceleration.json")["runs"]
    strongest = max(runs[run]["strongestDecelerationMps2"] for run in judged)
    assert strongest + 0.0005 < 0.46, f"{strongest}: three decimals bound the exact value by half a unit"
    assert strongest - 0.0005 > 0.45, f"{strongest}: 0.45 would not be a bound, so 0.46 is the tightest"
    assert runs["012_20_r2"]["strongestDecelerationMps2"] > 0.46, "0.533 holds over all six runs only"


def test_the_commanded_decelerations_of_each_run_of_sc_driving_012_would_take_at_most_2_4_kmh_off_its_speed():
    """The deceleration calibration decision of 2026-11-21, as corrected: REQ-DRIVING-037 judges the impact speed, so
    the fails do not rest on the commanded values alone. The commanded decelerations of each run of SC-DRIVING-012,
    fully achieved, would have lowered its speed before the contact by at most 2.4 km/h (2.326 km/h in 012_20_r2),
    so the condition on ASM-DRIVING-005 does not bear on these fails. The speed on the tick before the contact is the
    impact speed and the contact frame that VC-DRIVING-037 measured, a reading of the same records by the case
    evaluators."""
    found = _json("commanded_deceleration.json")
    assert "runs" in found, "commanded_deceleration.json states its runs beside its method"
    contacts = [found["runs"][run].get("beforeContact") for run in RUNS[:6]]
    assert all(isinstance(c, dict) for c in contacts), "each run of SC-DRIVING-012 states its bound"
    assert not any("beforeContact" in found["runs"][run] for run in RUNS[6:])
    measured = {e["run"]: e.get("measured") or {} for e in _json("verdicts.json")["cases"]["VC-DRIVING-037"][
        "measured"]["runs"]}
    limits = {20: 0.0, 42: 0.0, 60: 35.0}     # REQ-DRIVING-037's maximum relative impact speed at each setting
    for run, contact in zip(RUNS[:6], contacts):
        setting = int(run.split("_")[1])
        assert contact["worldFile"] == f"sim/out/world_{run}/simulator/world.jsonl"
        if "impactKmh" in measured.get(run, {}):
            assert contact["contactFrame"] == measured[run]["contactFrame"], run
            assert contact["speedOnTickBeforeContactKmh"] == round(measured[run]["impactKmh"], 3), run
            assert measured[run]["limitKmh"] == limits[setting], run
        assert 0 < contact["lastNegativeCommandBeforeContactS"] <= 1.0, run
        assert contact["speedReductionBoundKmh"] == _ceil1(contact["speedReductionIfAchievedKmh"]), run
        assert contact["speedOnTickBeforeContactKmh"] - contact["speedReductionBoundKmh"] > limits[setting], \
            f"{run}: the commands fully achieved would still leave the contact above the limit"
    bounds = [c["speedReductionBoundKmh"] for c in contacts]
    assert max(bounds) == 2.4 and max(c["speedReductionIfAchievedKmh"] for c in contacts) > 2.3, \
        "2.326 km/h is beyond 2.3, so the bound is 2.4"
    readme = _readme()
    speeds = [f"{c['speedOnTickBeforeContactKmh']:.1f}" for c in contacts]
    last = [f"{c['lastNegativeCommandBeforeContactS']:.1f}" for c in contacts]
    by = [f"{b:.1f} and {d:.1f} km/h from {x} and {y} km/h" for (b, d), (x, y) in zip(
        zip(bounds[0::2], bounds[1::2]), zip(speeds[0::2], speeds[1::2]))]
    for phrase in (
            f"The last command that holds a deceleration came {last[0]} and {last[1]} s before the contact at 20 km/h; "
            f"{last[2]} and {last[3]} s at 42 km/h; {last[4]} and {last[5]} s at 60 km/h.",
            f"The commanded decelerations of each run, fully achieved, would have lowered its speed before the "
            f"contact by at most {max(bounds):.1f} km/h: by at most "
            + "; ".join(f"{t} at {kmh} km/h" for t, kmh in zip(by, SETTINGS_012))
            + " (rounded up to one decimal; `commanded_deceleration.json` states the method).",
            "The condition on ASM-DRIVING-005 concerns how the simulated vehicle achieves a commanded deceleration: "
            "it bears on a pass of VC-DRIVING-036 and VC-DRIVING-037 and does not bear on these fails, since no "
            "calibration of the achieved deceleration turns them into passes (the deceleration calibration decision "
            "of 2026-11-21)."):
        assert phrase in readme, phrase
    assert "which rest on the commanded values" not in readme


def test_the_readme_records_the_open_bench_item_b_1():
    """B1, the bench finding of 2026-11-21: an open bench item for the next session, stated as observed; the bench
    is not changed for S1, since that would void the condition of record."""
    counts = _json("drop_counts.json")
    assert {counts[run]["runEnd"]["ticks"] for run in ("013_30_r2", "013_60_r2")} == {62}
    readme = _readme()
    for phrase in ("## Open bench item B1",
                   "The second runs of SC-DRIVING-013, `013_30_r2` and `013_60_r2`, ended after 62 ticks at the "
                   "speed of the target, with the vehicle at 1.3 km/h and the target at 20 km/h.",
                   "At the first tick of each the target was at rest (8e-08 and 8.5e-05 m/s); in the first runs it "
                   "already moved at 5.2 m/s.",
                   "`_run_loop` in `world-side/da_world_side.py` at `508649ba`",
                   "`013_60_r1` ended in contact with the target but has no functional part: no tick in the band "
                   "with a time to collision of at least 4 s. So SC-DRIVING-013 has one judged run, `013_30_r1`.",
                   "It is not fixed for S1: a fix would change a file that ran in S1 and void the condition of "
                   "record. It is open for the next session (GAP-DRIVING-014)."):
        assert phrase in readme, phrase


def test_the_gains_file_holds_the_gains_of_the_verdicts_and_the_slice_names_it_by_identity():
    """The correction of 2026-11-21: ackermann_gains.json holds the Ackermann gains that the verdicts of
    VC-DRIVING-036 and VC-DRIVING-037 record, in the bytes the refresh writes, and the slice names it by name, file
    and SHA-256 instead of inlining the record."""
    data = (EVIDENCE / "ackermann_gains.json").read_bytes()
    assert data == _tool().gains_file(_json("verdicts.json"))
    slice_text = " ".join(re.sub(r"(?m)^\s*\*\s?", "", (ROOT / "textual-notation-of-model" / "packages" / "features"
                                                        / "driving" / "driver_assistance_verification_evidence.sysml")
                                 .read_text(encoding="utf-8")).split())
    identity = (f"ackermannGains v1 (ackermann_gains.json of the evidence directory, sha256 "
                f"{hashlib.sha256(data).hexdigest()})")
    assert slice_text.count(identity) == 2, "the docs of VC-DRIVING-036 and VC-DRIVING-037"
    assert '"speed_kp"' not in slice_text and "readBackEqual" not in slice_text
