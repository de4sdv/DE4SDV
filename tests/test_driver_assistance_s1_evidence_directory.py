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
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "implementation" / "driver-assistance-bench" / "evidence" / "s1-20261121T014447Z"
TOOL = ROOT / "tools" / "refresh_driver_assistance_s1_evidence.py"
SESSION = "20261121T014447Z"
FILES = ["README.md", "SHA256SUMS", "VIDEO-EVIDENCE-DISPOSITION.md", "analysis_039.generator.json",
         "analysis_039.json", "drop_counts.json", "external-media.json", "records.json", "reproduction_044.json",
         "scenario_digests.json", "session.json", "verdicts.json"]
#: the runs of S1 whose score-interface record the drop counts read: the fourteen judged runs, the run that stops
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


def test_the_drop_counts_name_each_run_of_s1():
    counts = _json("drop_counts.json")
    assert sorted(counts) == sorted(RUNS)
    for run, count in counts.items():
        assert count["file"] == f"score/out/score_{run}/score_side/run/score/score_interface.jsonl"
        assert 0 < count["droppedInFirst5s"] <= count["dropped"] < count["received"], run


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
