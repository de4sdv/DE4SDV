#!/usr/bin/env python3
"""Refresh the INC-DRIVING-002 S1 evidence directory from the evaluators' outputs and the fetched session.

One command regenerates every committed file of
``implementation/driver-assistance-bench/evidence/s1-20261121T014447Z/`` whose content comes from a verdict file, a
desk record or the fetched session tree, and then the model text that the evidence generator writes from them:

- ``verdicts.json`` and ``records.json``, copied from ``--eval-dir`` (the case evaluators' outputs);
- ``analysis_039.json``, the full desk record of the analysis of REQ-DRIVING-039, copied verbatim, and
  ``analysis_039.generator.json``, its reduction to the keys the generator reads (the six attributes of
  ``RetainedCommandFormAnalysis``, the outcome and a reason when there is one);
- ``reproduction_044.json``, the desk reproduction of the candidate identity, copied verbatim;
- ``session.json`` and ``scenario_digests.json``, copied from the session tree;
- ``drop_counts.json``, where the camera images of each run drop, from the run's score-interface record and the
  world side's files of the run: in the first 5 s after its first image, at the end of its image stream and in
  between, the run's end with the speeds at its last tick, the drops of its whole-run window, the warm start that
  the run's Launch Manager log records, and for the run that stops the path its stop instant (``path_stop.json``);
- ``ackermann_gains.json``, the Ackermann gains that VC-DRIVING-036 and VC-DRIVING-037 record, which the
  generator names by identity instead of copying them into the model;
- ``commanded_deceleration.json``, the strongest deceleration among the driving commands that the actuation adapter
  of each run accepted, and for each run of SC-DRIVING-012 the speed that those commands, fully achieved, would have
  taken off before the contact with the target, at most, with the method stated in the file;
- ``SHA256SUMS``, the SHA-256 of every file of the session tree, by its path relative to the tree, and
  ``external-media.json``, the recordings and archives of the tree with their identity and retention;
- the verdict table of ``README.md``, between its two markers;
- with no ``--no-generate``: ``tools/generate_driver_assistance_evidence_text.py`` on the copied files.

The session tree and its media stay outside Git. Exit 0 on success, 2 on bad arguments, 3 when an input is missing
or the generator refuses.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EVIDENCE = REPO / "implementation" / "driver-assistance-bench" / "evidence" / "s1-20261121T014447Z"
GENERATOR = REPO / "tools" / "generate_driver_assistance_evidence_text.py"

BEGIN = "<!-- BEGIN generated verdict table: tools/refresh_driver_assistance_s1_evidence.py -->"
END = "<!-- END generated verdict table -->"

ANALYSIS_KEYS = ("configurationIdentity", "receiptSha256", "modelRevision", "analyzedRealization", "analystIdentity",
                 "claimBoundary")
#: the cases in the order of their numbers; VC-DRIVING-039 reads the desk analysis and no run
CASES = tuple(f"VC-DRIVING-0{n}" for n in range(36, 45))
ANALYSIS_CASE = "VC-DRIVING-039"
#: the verdict of each outcome literal, as MapAssistanceEvidenceOutcomeToVerdict maps it
VERDICTS = {"passBoundedVerification": "pass", "passBoundedValidation": "pass", "failObservedBehavior": "fail",
            "errorEvidence": "error"}
SCORE_INTERFACE = "score/out/score_{run}/score_side/run/score/score_interface.jsonl"
WORLD_DIR = "sim/out/world_{run}/simulator"
ACTUATION_ADAPTER = "score/out/score_{run}/score_side/run/score/actuationAdapter.jsonl"
LAUNCH_MANAGER_LOG = "score/out/score_{run}/score_side/state/launch_manager.log"
#: the stop instant of a run that stops the path, which the S-CORE host writes on its own monotonic clock
PATH_STOP = "score/out/path_stop_{run}/path_stop.json"
#: the label of the run that stops the path
STOP_RUN = "stop"
#: the line of the warm start of D-S1-1 (patch 0005 of the bench) in a run's Launch Manager log
WARM_START = re.compile(r"\[DE4SDV\] warm start before the attach: (\d+) passes, result (\w+), ([0-9.]+) ms")
#: the start-up drops: within this many seconds of simulation time after a run's first image
START_S = 5.0
#: the drops at the end of a run's image stream: within this many seconds before its last image
STREAM_END_S = 1.0
#: the recordings and archives of a session tree: kept outside Git, listed by external-media.json
MEDIA_SUFFIXES = (".mp4", ".mkv", ".png", ".rrd", ".tgz")


def reduce_analysis(full: dict) -> dict:
    """The keys of the desk analysis that the generator reads, in its order; any other key is left out."""
    reduced = {key: full[key] for key in ANALYSIS_KEYS if key in full}
    reduced["outcome"] = full["outcome"]
    if isinstance(full.get("reason"), str) and full["reason"].strip():
        reduced["reason"] = full["reason"]
    return reduced


def _world_span(tree: Path, run: str) -> dict:
    """The run's end and its whole-run window from the world side's files: run_end.json (the end reason and the
    number of run ticks), world.jsonl (the run's ticks, the window that a criterion over every run judges, first to
    last tick, and the vehicle's and the target's speed at the last tick, km/h, None where the tick has no target)
    and tick_times.csv (every tick of the process: the ticks it makes after the run's end)."""
    sim = Path(tree) / WORLD_DIR.format(run=run)
    end_path, world_path, times_path = sim / "run_end.json", sim / "world.jsonl", sim / "tick_times.csv"
    if not end_path.is_file():
        raise ValueError(f"run {run}: no {end_path.relative_to(tree).as_posix()} (the run's end, run_end.json)")
    end = json.loads(end_path.read_text(encoding="utf-8"))
    ticks, data = [], []
    if world_path.is_file():
        for line in world_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                event = json.loads(line)
                if event.get("event") == "tick":
                    ticks.append(float(event["data"]["simTimeS"]))
                    data.append(event["data"])
    ticks.sort()
    if not ticks or end.get("ticks") != len(ticks):
        raise ValueError(f"run {run}: run_end.json gives {end.get('ticks')!r} ticks and world.jsonl {len(ticks)}")
    if not times_path.is_file():
        raise ValueError(f"run {run}: no {times_path.relative_to(tree).as_posix()} beside run_end.json")
    rows = [float(line.split(",", 1)[0]) for line in times_path.read_text(encoding="utf-8").splitlines()[1:]
            if line.strip()]
    last = [k for k, t in enumerate(rows) if abs(t - ticks[-1]) < 1e-5]
    if len(last) != 1:
        raise ValueError(f"run {run}: the run's last tick {ticks[-1]} is not one row of tick_times.csv beside "
                         "run_end.json")
    final = max(data, key=lambda d: float(d["simTimeS"]))
    target = (final.get("target") or {}).get("speedMps")
    return {"runEnd": {"file": end_path.relative_to(tree).as_posix(), "endReason": end.get("endReason"),
                       "ticks": end.get("ticks"), "tickTimesFile": times_path.relative_to(tree).as_posix(),
                       "ticksAfterRunEnd": len(rows) - 1 - last[0],
                       "egoSpeedAtLastTickKmh": round(float(final["ego"]["speedMps"]) * 3.6, 3),
                       "targetSpeedAtLastTickKmh": round(float(target) * 3.6, 3) if target is not None else None},
            "window": (ticks[0], ticks[-1]), "worldFile": world_path.relative_to(tree).as_posix()}


def warm_start(tree: Path, run: str) -> dict | None:
    """The warm start of D-S1-1 as the run's Launch Manager log records it, or None when the log records none."""
    path = Path(tree) / LAUNCH_MANAGER_LOG.format(run=run)
    if not path.is_file():
        return None
    found = WARM_START.findall(path.read_text(encoding="utf-8", errors="replace"))
    if not found:
        return None
    if len(found) != 1:
        raise ValueError(f"run {run}: {len(found)} warm-start lines in {path.relative_to(tree).as_posix()}")
    passes, result, ms = found[0]
    return {"file": path.relative_to(tree).as_posix(), "passes": int(passes), "result": result, "ms": float(ms)}


def stop_instant(tree: Path, run: str, events: list[dict], last_image: float, last_tick: float) -> dict | None:
    """The stop instant of a run that stops the path, from its path_stop.json, which the S-CORE host writes on its own
    monotonic clock (stopInstantMonoNs), mapped onto the run's score-interface record, which the same host writes on
    the same clock (mono_ns): the stop came at the simulation time of the newest record at or before the stop
    instant (simS); lastCommandIssueSimS is the issue time of the last driving command before it; the image stream
    goes on imageStreamAfterStopS after it, with droppedAfterStop drops; and ticksAfterStopS of the whole-run window
    follow it. None for a run without a path_stop.json; refused for the run that stops the path without one."""
    path = Path(tree) / PATH_STOP.format(run=run)
    if not path.is_file():
        if run == STOP_RUN:
            raise ValueError(f"run {run}: no {PATH_STOP.format(run=run)} (the stop instant of the run that stops "
                             "the path)")
        return None
    mono = int(json.loads(path.read_text(encoding="utf-8"))["stopInstantMonoNs"])
    before = [e for e in events if "sim_s" in e and "mono_ns" in e and int(e["mono_ns"]) <= mono]
    commands = [e for e in events if e.get("kind") == "out.driving_command" and "mono_ns" in e
                and int(e["mono_ns"]) <= mono]
    if not before:
        raise ValueError(f"run {run}: no record of its score-interface record at or before the stop instant of "
                         f"{PATH_STOP.format(run=run)}")
    sim = float(max(before, key=lambda e: int(e["mono_ns"]))["sim_s"])
    command = max(commands, key=lambda e: int(e["mono_ns"])) if commands else None
    return {"file": PATH_STOP.format(run=run), "stopInstantMonoNs": mono, "simS": round(sim, 3),
            "lastCommandIssueSimS": round(float(command["issueTime_sim_s"]), 3) if command else None,
            "imageStreamAfterStopS": round(last_image - sim, 3),
            "droppedAfterStop": sum(1 for e in events if e.get("kind") == "drop.camera_image" and "mono_ns" in e
                                    and int(e["mono_ns"]) > mono),
            "ticksAfterStopS": round(last_tick - sim, 3)}


def drop_counts(tree: Path) -> dict:
    """Run label -> where its camera images drop, in its score-interface record: within 5 s of simulation time after
    its first received image, within the last second of its image stream, and isolated in between (seconds after the
    first image); its received images; its end; and the drops of its whole-run window, those whose simulation time
    lies from its first to its last world tick (the window of a criterion over every run, as the case evaluators'
    ``Run.drops_in`` counts it, 1e-6 s at each edge)."""
    counts = {}
    for path in sorted(Path(tree).glob(SCORE_INTERFACE.format(run="*"))):
        run = path.relative_to(tree).parts[2][len("score_"):]
        drops, received, events = [], [], []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            events.append(event)
            if event.get("kind") == "drop.camera_image":
                drops.append(float(event["sim_s"]))
            elif event.get("kind") == "in.camera_image":
                received.append(float(event["sim_s"]))
        if not received:
            raise ValueError(f"run {run}: no in.camera_image in {path.relative_to(tree).as_posix()}")
        drops.sort()
        first, last = min(received), max(received)
        start = [t for t in drops if t - first < START_S]
        end = [t for t in drops if t - first >= START_S and last - t < STREAM_END_S]
        isolated = [t for t in drops if t - first >= START_S and last - t >= STREAM_END_S]
        span = _world_span(tree, run)
        w0, w1 = span["window"]
        inside = [t for t in drops if w0 - 1e-6 <= t <= w1 + 1e-6]
        counts[run] = {
            "file": path.relative_to(tree).as_posix(), "received": len(received), "dropped": len(drops),
            "firstImageSimS": round(first, 3), "lastImageSimS": round(last, 3),
            "droppedInFirst5s": len(start), "droppedAtStreamEnd": len(end),
            "streamEndDropsWithinS": round(max(last - t for t in end), 3) if end else None,
            "isolatedDropsS": [round(t - first, 3) for t in isolated],
            "runEnd": span["runEnd"],
            "wholeRunWindow": {"file": span["worldFile"], "firstTickSimS": round(w0, 3), "lastTickSimS": round(w1, 3),
                               "dropped": len(inside),
                               "isolatedDropsS": [round(t - first, 3) for t in isolated if t in inside]},
            "warmStart": warm_start(tree, run),
        }
        stop = stop_instant(tree, run, events, last, w1)
        if stop is not None:
            counts[run]["stopInstant"] = stop
    return counts


#: how commanded_deceleration.json bounds, for each run of SC-DRIVING-012, what the commanded decelerations could
#: have taken off the speed before the contact
CONTACT_METHOD = (
    "strongestDecelerationMps2 is the strongest deceleration among the driving commands that the actuation adapter "
    "accepted (in.driving_command with verdict accepted in actuationAdapter.jsonl), in m/s², rounded to three "
    "decimals. For each run of SC-DRIVING-012, beforeContact: the contact is the first tick of the run's world.jsonl "
    "whose collisions is not empty or whose targetContact is true (contactFrame, contactSimS); "
    "speedOnTickBeforeContactKmh is ego.speedMps on the tick before it, in km/h. Each accepted command is held until "
    "the next accepted command, from its issueTime_sim_s on, and the last one before the contact until the contact; "
    "speedReductionIfAchievedKmh integrates the decelerations of these commands (their negative accelerations only) "
    "up to the contact, as if the vehicle had fully achieved them, in km/h, rounded to four decimals, and "
    "speedReductionBoundKmh is that integral rounded up to one decimal, so that it stays a bound on what the "
    "commanded decelerations could have taken off the speed before the contact. "
    "lastNegativeCommandBeforeContactS is the time from the issueTime_sim_s of the last accepted command before the "
    "contact that holds a deceleration to the contact, in seconds of simulation time (null when no such command "
    "comes before the contact).")
#: the runs whose commanded decelerations are bounded up to the contact with the stationary target
CONTACT_RUNS = "012_"


def _contact(tree: Path, run: str, commands: list[tuple[float, float]]) -> dict:
    """The bound of one run of SC-DRIVING-012, from its world.jsonl and its accepted commands (issue time,
    acceleration), as CONTACT_METHOD states it; refused when the run has no world record or no contact."""
    path = Path(tree) / WORLD_DIR.format(run=run) / "world.jsonl"
    if not path.is_file():
        raise ValueError(f"run {run}: no {path.relative_to(tree).as_posix()} to find the contact in")
    ticks = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            event = json.loads(line)
            if event.get("event") == "tick":
                ticks.append(event["data"])
    ticks.sort(key=lambda data: float(data["simTimeS"]))
    k = next((i for i, data in enumerate(ticks) if data.get("collisions") or data.get("targetContact")), None)
    if k is None or k == 0:
        raise ValueError(f"run {run}: no contact after the first tick of {path.relative_to(tree).as_posix()}")
    contact = float(ticks[k]["simTimeS"])
    before = sorted((t, a) for t, a in commands if t < contact)
    reduction = 0.0
    for i, (t, a) in enumerate(before):
        until = before[i + 1][0] if i + 1 < len(before) else contact
        if a < 0:
            reduction += -a * (until - t)
    negative = [t for t, a in before if a < 0]
    kmh = reduction * 3.6
    return {"worldFile": path.relative_to(tree).as_posix(), "contactFrame": ticks[k].get("frame"),
            "contactSimS": round(contact, 3),
            "speedOnTickBeforeContactKmh": round(float(ticks[k - 1]["ego"]["speedMps"]) * 3.6, 3),
            "lastNegativeCommandBeforeContactS": round(contact - negative[-1], 3) if negative else None,
            "speedReductionIfAchievedKmh": round(kmh, 4),
            "speedReductionBoundKmh": math.ceil(round(kmh, 9) * 10) / 10}


def commanded_deceleration(tree: Path) -> dict:
    """The method (CONTACT_METHOD) and, by run label, the driving commands that the actuation adapter accepted
    (in.driving_command with verdict accepted), the strongest deceleration among them, m/s² (None when no accepted
    command decelerates), and for a run of SC-DRIVING-012 its bound up to the contact (beforeContact)."""
    found = {}
    for path in sorted(Path(tree).glob(ACTUATION_ADAPTER.format(run="*"))):
        run = path.relative_to(tree).parts[2][len("score_"):]
        accepted = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            data = event.get("data") or {}
            if event.get("event") == "in.driving_command" and data.get("verdict") == "accepted":
                accepted.append((float(data["issueTime_sim_s"]), float(data["acceleration"])))
        decelerations = [-a for _, a in accepted if a < 0]
        found[run] = {"file": path.relative_to(tree).as_posix(), "acceptedCommands": len(accepted),
                      "strongestDecelerationMps2": round(max(decelerations), 3) if decelerations else None}
        if run.startswith(CONTACT_RUNS):
            found[run]["beforeContact"] = _contact(tree, run, accepted)
    return {"method": CONTACT_METHOD, "runs": found}


def _generator():
    """The evidence generator as a module, for the bytes of the gains file it names."""
    spec = importlib.util.spec_from_file_location("generate_driver_assistance_evidence_text", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(spec.name, module)
    spec.loader.exec_module(module)
    return module


def gains_file(verdicts: dict) -> bytes | None:
    """The bytes of ackermann_gains.json: the Ackermann gains that the cases record, in the generator's form; None
    when no case records gains; refused when two cases record different gains."""
    generator = _generator()
    found = {}
    for vc, case in sorted(verdicts["cases"].items()):
        gains = (case.get("measured") or {}).get("ackermannGains")
        if generator.gains_recorded(gains):
            found[vc] = generator.gains_record(gains)
    if len(set(found.values())) > 1:
        raise ValueError(f"the cases {', '.join(found)} record different ackermannGains")
    return next(iter(found.values()), None)


def sha256sums(tree: Path) -> str:
    """``sha256sum``'s format over every file of the tree, by relative path, sorted."""
    lines = []
    for path in sorted((p for p in Path(tree).rglob("*") if p.is_file()), key=lambda p: p.relative_to(tree).as_posix()):
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        lines.append(f"{digest.hexdigest()}  {path.relative_to(tree).as_posix()}")
    return "\n".join(lines) + "\n"


def media_manifest(tree: Path) -> dict:
    """The recordings of the session tree, each by its path in the tree, with its SHA-256, size and retention."""
    artifacts = []
    for path in sorted((p for p in Path(tree).rglob("*") if p.is_file() and p.suffix.lower() in MEDIA_SUFFIXES),
                       key=lambda p: p.relative_to(tree).as_posix()):
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        artifacts.append({"path": path.relative_to(tree).as_posix(), "sha256": digest.hexdigest(),
                          "bytes": path.stat().st_size, "disposition": "observed_bounded",
                          "availability": "maintainer_archive"})
    return {"schema": "de4sdv.external-evidence-media.v1", "policy": "docs/evidence-management.md",
            "published": False, "artifacts": artifacts}


def _short(outcome: str) -> str:
    return VERDICTS.get(outcome, "inconclusive")


def verdict_table(verdicts: dict, analysis: dict | None) -> str:
    """The case table and the run table, from the verdicts and the reduced desk analysis."""
    cases = verdicts["cases"]
    lines = [f"Session `{verdicts['sessionId']}`, criteriaRecordIdentity `{verdicts['criteriaRecordIdentity']}`, "
             f"evaluatorRevision `{verdicts['evaluatorRevision']}`.", "",
             "| Case | Requirement | Outcome | Verdict |", "|---|---|---|---|"]
    for vc in CASES:
        requirement = "REQ-" + vc[3:]
        if vc == ANALYSIS_CASE:
            if analysis is not None:
                lines.append(f"| {vc} | {requirement} | `{analysis['outcome']}` | {_short(analysis['outcome'])} |")
            continue
        if vc in cases:
            case = cases[vc]
            lines.append(f"| {vc} | {requirement} | `{case['outcome']}` | {case['verdict']} |")
    read = [vc for vc in CASES if vc in cases]
    lines += ["", "| Run | " + " | ".join(read) + " |", "|---|" + "---|" * len(read)]
    for run in verdicts["runs"]:
        cells = []
        for vc in read:
            measured = cases[vc].get("measured") or {}
            entry = next((e for e in measured.get("runs") or [] if e["run"] == run["run"]), None)
            stop = measured.get("stopClause")
            if entry is not None:
                cell = _short(entry["outcome"])
                impact = (entry.get("measured") or {}).get("impactKmh")
                if isinstance(impact, (int, float)) and not isinstance(impact, bool):
                    cell += f" ({impact:.1f} km/h)"
            elif isinstance(stop, dict) and stop.get("run") == run["run"]:
                cell = f"{_short(stop['outcome'])} (stop clause)"
            else:
                cell = "not read"
            cells.append(cell)
        lines.append(f"| {run['runIdentity']} | " + " | ".join(cells) + " |")
    lines += ["", "The impact speed in brackets is the relative impact speed that VC-DRIVING-037 measured. "
              "An outcome of a case over a run is that run's part of the case; the case's own outcome is in the "
              "first table."]
    return "\n".join(lines)


def replace_marked(text: str, block: str) -> str:
    """Replace what lies between the two markers; refuse a text without exactly one pair."""
    if text.count(BEGIN) != 1 or text.count(END) != 1 or text.index(BEGIN) > text.index(END):
        raise ValueError("the text has no single pair of verdict-table markers")
    head, rest = text.split(BEGIN, 1)
    _, tail = rest.split(END, 1)
    return f"{head}{BEGIN}\n{block}\n{END}{tail}"


def _write(path: Path, data: bytes) -> None:
    if not path.exists() or path.read_bytes() != data:
        path.write_bytes(data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--eval-dir", required=True, type=Path, help="holds verdicts.json and records.json")
    parser.add_argument("--analysis-039", required=True, type=Path, help="the full desk record of REQ-DRIVING-039")
    parser.add_argument("--reproduction-044", required=True, type=Path, help="the desk reproduction of 044")
    parser.add_argument("--session-tree", required=True, type=Path, help="the fetched session tree")
    parser.add_argument("--evidence-dir", type=Path, default=EVIDENCE)
    parser.add_argument("--no-generate", action="store_true", help="do not run the evidence generator")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    sources = {"verdicts.json": args.eval_dir / "verdicts.json", "records.json": args.eval_dir / "records.json",
               "analysis_039.json": args.analysis_039, "reproduction_044.json": args.reproduction_044,
               "session.json": args.session_tree / "session.json",
               "scenario_digests.json": args.session_tree / "scenario_digests.json"}
    for name, source in sources.items():
        if not source.is_file():
            print(f"refused: {name}: no file {source}", file=sys.stderr)
            return 3
    out = args.evidence_dir
    readme = out / "README.md"
    if not readme.is_file():
        print(f"refused: no {readme}", file=sys.stderr)
        return 3
    try:
        drops = drop_counts(args.session_tree)
    except ValueError as exc:
        print(f"refused: drop_counts.json: {exc}", file=sys.stderr)
        return 3
    try:
        decelerations = commanded_deceleration(args.session_tree)
    except ValueError as exc:
        print(f"refused: commanded_deceleration.json: {exc}", file=sys.stderr)
        return 3
    for name, source in sources.items():
        _write(out / name, source.read_bytes())
    full = json.loads(args.analysis_039.read_text(encoding="utf-8"))
    reduced = reduce_analysis(full)
    _write(out / "analysis_039.generator.json",
           (json.dumps(reduced, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    _write(out / "drop_counts.json", (json.dumps(drops, indent=2) + "\n").encode("utf-8"))
    _write(out / "commanded_deceleration.json",
           (json.dumps(decelerations, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    _write(out / "SHA256SUMS", sha256sums(args.session_tree).encode("utf-8"))
    _write(out / "external-media.json",
           (json.dumps(media_manifest(args.session_tree), indent=2) + "\n").encode("utf-8"))
    verdicts = json.loads((out / "verdicts.json").read_text(encoding="utf-8"))
    try:
        gains = gains_file(verdicts)
    except ValueError as exc:
        print(f"refused: ackermann_gains.json: {exc}", file=sys.stderr)
        return 3
    if gains is not None:
        _write(out / "ackermann_gains.json", gains)
    try:
        text = replace_marked(readme.read_text(encoding="utf-8"), verdict_table(verdicts, reduced))
    except ValueError as exc:
        print(f"refused: {readme}: {exc}", file=sys.stderr)
        return 3
    _write(readme, text.encode("utf-8"))
    if args.no_generate:
        return 0
    command = [sys.executable, str(GENERATOR), "--verdicts", str(out / "verdicts.json"), "--records",
               str(out / "records.json"), "--analysis-039", str(out / "analysis_039.generator.json")]
    rc = subprocess.run(command, check=False).returncode
    return 0 if rc == 0 else 3


if __name__ == "__main__":
    sys.exit(main())
