"""Remove ICD v2 records from a copy of a run.

The tests use this to prove the claim of OBSERVABLES.md: a case that needs a
record cannot reach a pass when that record is removed. It edits a copy, never
the fixture. The copy is made with hard links and every edited file is
replaced atomically, so the fixture's bytes are never touched and a run costs
almost nothing to copy.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

# change id -> (whole files/directories to delete, [(file, event or "*", fields)])
RULES: dict[str, tuple[list[str], list[tuple[str, str, list[str] | None]]]] = {
    "C1": ([], [
        ("simulator/world.jsonl", "tick",
         ["sensors", "velocity", "acceleration", "angular_velocity",
          "controlSource", "autopilotEnabled", "trafficManagerEnabled"]),
    ]),
    "C2": (["score/checkpointInputs.jsonl", "score/bundles"], []),
    "C3": ([], [
        ("score/drivingAgent.jsonl", "out.command",
         ["step_capture_sim_ms", "plan_capture_sim_ms"]),
        ("score/actuationAdapter.jsonl", "in.command",
         ["step_capture_sim_ms", "plan_capture_sim_ms"]),
    ]),
    "C4": ([], [
        ("run_record.json", "*", ["campaignId", "runRole", "scenarioVariant",
                                  "inputReplay"]),
    ]),
    "C5": ([], [
        ("guest/observer.jsonl", "rx.health",
         ["last_plan_capture_ms", "step_capture_ms", "last_plan_production_mono_s",
          "last_plan_production_mono_ns"]),
        ("score/statePublisher.jsonl", "out.health",
         ["last_plan_capture_ms", "step_capture_ms", "last_plan_production_mono_s",
          "last_plan_production_mono_ns"]),
    ]),
    "C6": ([], [
        ("guest/observer.jsonl", "rx.health",
         ["checkpoint_expected_sha256", "checkpoint_actual_sha256", "refusal_reason"]),
        ("score/statePublisher.jsonl", "out.health",
         ["checkpoint_expected_sha256", "checkpoint_actual_sha256", "refusal_reason"]),
        ("score/drivingAgent.jsonl", "error", None),
    ]),
    "C7": ([], [
        ("run_record.json", "*", ["checkpointPath", "configurationPath",
                                  "vehicleConfiguration", "navigationMap", "route",
                                  "writtenAtMonoNs", "writtenAtRealNs"]),
    ]),
    "C8": (["bench/injection.jsonl"], []),
    "C9": ([], [
        ("score/drivingAgent.jsonl", "out.plan", ["clocks"]),
        ("score/drivingAgent.jsonl", "in.plan", ["clocks"]),
        ("score/drivingAgent.jsonl", "out.mode", ["clocks"]),
        ("score/drivingAgent.jsonl", "out.command", ["clocks"]),
        ("score/drivingAgent.jsonl", "out.ego_motion_sample", ["clocks"]),
        ("score/drivingAgent.jsonl", "in.route", ["clocks"]),
        ("score/actuationAdapter.jsonl", "in.command", ["clocks"]),
        ("score/actuationAdapter.jsonl", "out.actuation_state", ["clocks"]),
        ("score/actuationAdapter.jsonl", "stop_response.begin", ["clocks"]),
        ("score/statePublisher.jsonl", "out.plan", ["clocks"]),
        ("score/route_provider.jsonl", "out.route_announcement", ["clocks"]),
    ]),
    "C10": ([], [("score/drivingAgent.jsonl", "priming.complete", None)]),
    "C11": (["score/referenceInference.jsonl"], []),
    "C12": ([], [
        ("guest/observer.jsonl", "rx.plan",
         ["plan_producer", "plan_sample_count", "plan_horizon_s"]),
        ("score/statePublisher.jsonl", "out.plan",
         ["plan_producer", "plan_sample_count", "plan_horizon_s"]),
    ]),
}


def _replace(path: Path, text: str) -> None:
    replace_bytes(path, text.encode("utf-8"))


def replace_bytes(path: Path, data: bytes) -> None:
    """Replace a file's content without writing into its inode.

    The fixtures are copied with hard links; an in-place write would edit the
    fixture too. A temp file plus rename breaks the link for this path only.
    """
    fd, tmp = tempfile.mkstemp(dir=str(path.parent))
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)
    os.replace(tmp, path)


def copy_run(run_dir: str | Path, out_dir: str | Path) -> Path:
    src, dst = Path(run_dir), Path(out_dir)
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, copy_function=os.link)
    return dst


def strip_change(run_dir: str | Path, cid: str, out_dir: str | Path) -> Path:
    return strip_changes(run_dir, [cid], out_dir)


def strip_changes(run_dir: str | Path, cids: list[str] | tuple[str, ...],
                  out_dir: str | Path) -> Path:
    """Copy the run and remove the records of every change in `cids`."""
    dst = copy_run(run_dir, out_dir)
    record_touched = False
    for cid in cids:
        if cid not in RULES:
            raise KeyError(f"no strip rule for {cid}")
        files, fields = RULES[cid]
        for rel in files:
            p = dst / rel
            if p.is_dir():
                shutil.rmtree(p)
            elif p.exists():
                p.unlink()
        for rel, event, keys in fields:
            p = dst / rel
            if not p.exists() or p.is_dir():
                continue
            if rel == "run_record.json":
                # a JSON document, not a JSONL file; its identity is the hash of
                # its bytes, so the identity every plan names is repaired below
                doc = json.loads(p.read_text())
                if keys is None:
                    doc = {}
                else:
                    for k in keys:
                        doc.pop(k, None)
                _replace(p, json.dumps(doc, indent=1, sort_keys=True) + "\n")
                record_touched = True
                continue
            lines = []
            for line in p.read_text().splitlines():
                if not line.strip():
                    continue
                rec = json.loads(line)
                if event != "*" and rec.get("event") != event:
                    lines.append(json.dumps(rec, separators=(",", ":")))
                    continue
                if keys is None:
                    continue                    # drop the record
                data = rec.get("data")
                if isinstance(data, dict):
                    for k in keys:
                        data.pop(k, None)
                lines.append(json.dumps(rec, separators=(",", ":")))
            _replace(p, "\n".join(lines) + ("\n" if lines else ""))
    if record_touched:
        _repair_run_identity(dst)
    return dst


def _repair_run_identity(dst: Path) -> None:
    """The run record's identity is the SHA-256 prefix of its bytes; after an
    edit every record that names it must name the new value, or the copy would
    be a record that contradicts itself. Payload records use `runRecord`; the
    decoded operational state uses `run_record`."""
    import hashlib
    ident = hashlib.sha256((dst / "run_record.json").read_bytes()).hexdigest()[:16]
    for p in dst.rglob("*.jsonl"):
        keep = []
        changed = False
        for line in p.read_text().splitlines():
            if not line.strip():
                continue
            if '"runRecord"' not in line and '"run_record"' not in line:
                keep.append(line)
                continue
            rec = json.loads(line)
            data = rec.get("data")
            if isinstance(data, dict):
                touched = False
                for key in ("runRecord", "run_record"):
                    if key in data:
                        data[key] = ident
                        touched = True
                if touched:
                    changed = True
                    keep.append(json.dumps(rec, separators=(",", ":")))
                    continue
            keep.append(line)
        if changed:
            _replace(p, "\n".join(keep) + "\n")
