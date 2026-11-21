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
  between, the run's end, and the drops of its whole-run window;
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
import json
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
    last tick) and tick_times.csv (every tick of the process: the ticks it makes after the run's end)."""
    sim = Path(tree) / WORLD_DIR.format(run=run)
    end_path, world_path, times_path = sim / "run_end.json", sim / "world.jsonl", sim / "tick_times.csv"
    if not end_path.is_file():
        raise ValueError(f"run {run}: no {end_path.relative_to(tree).as_posix()} (the run's end, run_end.json)")
    end = json.loads(end_path.read_text(encoding="utf-8"))
    ticks = []
    if world_path.is_file():
        for line in world_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                event = json.loads(line)
                if event.get("event") == "tick":
                    ticks.append(float(event["data"]["simTimeS"]))
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
    return {"runEnd": {"file": end_path.relative_to(tree).as_posix(), "endReason": end.get("endReason"),
                       "ticks": end.get("ticks"), "tickTimesFile": times_path.relative_to(tree).as_posix(),
                       "ticksAfterRunEnd": len(rows) - 1 - last[0]},
            "window": (ticks[0], ticks[-1]), "worldFile": world_path.relative_to(tree).as_posix()}


def drop_counts(tree: Path) -> dict:
    """Run label -> where its camera images drop, in its score-interface record: within 5 s of simulation time after
    its first received image, within the last second of its image stream, and isolated in between (seconds after the
    first image); its received images; its end; and the drops of its whole-run window, those whose simulation time
    lies from its first to its last world tick (the window of a criterion over every run, as the case evaluators'
    ``Run.drops_in`` counts it, 1e-6 s at each edge)."""
    counts = {}
    for path in sorted(Path(tree).glob(SCORE_INTERFACE.format(run="*"))):
        run = path.relative_to(tree).parts[2][len("score_"):]
        drops, received = [], []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
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
        }
    return counts


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
    for name, source in sources.items():
        _write(out / name, source.read_bytes())
    full = json.loads(args.analysis_039.read_text(encoding="utf-8"))
    reduced = reduce_analysis(full)
    _write(out / "analysis_039.generator.json",
           (json.dumps(reduced, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    _write(out / "drop_counts.json", (json.dumps(drops, indent=2) + "\n").encode("utf-8"))
    _write(out / "SHA256SUMS", sha256sums(args.session_tree).encode("utf-8"))
    _write(out / "external-media.json",
           (json.dumps(media_manifest(args.session_tree), indent=2) + "\n").encode("utf-8"))
    verdicts = json.loads((out / "verdicts.json").read_text(encoding="utf-8"))
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
