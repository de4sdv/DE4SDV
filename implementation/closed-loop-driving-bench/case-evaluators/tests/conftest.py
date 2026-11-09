"""Fixtures for the case-evaluator tests.

One synthetic fixture set is built per test session (make_synthetic_run.py) and
every test that needs to break a record copies it with hard links, so a 250 MB
set is never copied in full.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import make_synthetic_run  # noqa: E402

# The run each case is judged on. This is the bench the case documentation
# names, not a convenience: VC-DRIVING-023 is the camera-fault run, VC-DRIVING-028
# the run whose communication is stopped, and so on.
CASE_RUN = {
    "VC-DRIVING-001": "nominal", "VC-DRIVING-002": "nominal",
    "VC-DRIVING-003": "nominal", "VC-DRIVING-004": "nominal",
    "VC-DRIVING-005": "nominal", "VC-DRIVING-006": "nominal",
    "VC-DRIVING-007": "nominal", "VC-DRIVING-008": "nominal",
    "VC-DRIVING-009": "nominal", "VC-DRIVING-010": "nominal",
    "VC-DRIVING-011": "nominal", "VC-DRIVING-012": "nominal",
    "VC-DRIVING-013": "nominal", "VC-DRIVING-014": "comm-stop",
    "VC-DRIVING-015": "nominal", "VC-DRIVING-016": "nominal",
    "VC-DRIVING-017": "nominal", "VC-DRIVING-028": "comm-stop",
    "VC-DRIVING-030": "nominal", "VC-DRIVING-031": "nominal",
    "VC-DRIVING-032": "nominal", "VC-DRIVING-033": "nominal",
    "VC-DRIVING-034": "nominal", "VC-DRIVING-029": "fault-camera_missing",
    "VC-DRIVING-020": "stop-entry10", "VC-DRIVING-021": "stop-entry10",
    "VC-DRIVING-022": "stop-entry10",
    "VC-DRIVING-023": "fault-camera_missing",
    "VC-DRIVING-024": "fault-motion_stale",
    "VC-DRIVING-025": "fault-route_stale",
    "VC-DRIVING-026": "fault-plan_stale",
    "VC-DRIVING-027": "fault-plan_invalid_nan",
    "VC-DRIVING-035": "refusal-mismatch",
}

CAMPAIGN_RUNS = ["aaos-ref1", "aaos-ref2", "aaos-late", "aaos-stopped"]


@pytest.fixture(scope="session")
def fixture_root(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("synthetic-runs")
    make_synthetic_run.build_all(root)
    return root


@pytest.fixture(scope="session")
def run_for(fixture_root):
    def get(name: str):
        from runio import Run
        return Run(fixture_root / name)
    return get


def verdict(run, vc: str):
    import cases
    return cases.evaluate_case(run, vc)


def edit_jsonl(path: Path, event: str, fn) -> int:
    """Apply fn(data) to every record of `event`; fn returns the new data, the
    same data, or None to drop the record. Returns the number of records whose
    content changed (or that were dropped)."""
    out, changed = [], 0
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("event") == event:
            before = json.dumps(rec["data"], sort_keys=True)
            new = fn(rec["data"])
            if new is None:
                changed += 1
                continue
            if json.dumps(new, sort_keys=True) != before:
                changed += 1
            rec["data"] = new
        out.append(json.dumps(rec, separators=(",", ":")))
    import strip
    strip._replace(path, "\n".join(out) + "\n")
    return changed
