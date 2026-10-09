"""INC-AEBS-010, evaluated end to end on a cut of a genuine export.

``fixtures/genuine_export/inc-aebs-010.json.gz`` keeps, unchanged, the
elements of the licensed export of b64a48e0 that INC-AEBS-010's framing and
needs depend on: its framing and needs packages, the package elements of its
other declared packages, the increment workflow, every kernel declaration and
what those reference (``cut_increment_export.py`` beside it states the rule
and records the source export). It is evaluated exactly as
``scripts/evaluate_increment.py`` evaluates an export: kernel identity
validated from the export, every serializer shape the real one.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import subprocess
from pathlib import Path

from de4sdv.semantic import method_evaluator as me
from de4sdv.semantic.export_evaluation import evaluate_export
from increment_model_fixtures import GENUINE_EXPORT

ROOT = Path(__file__).resolve().parents[1]
NEEDS = ["needCorrelatableEvidence", "needFailClosedDegradation", "needLiveVisualizationOnAAOS",
         "needNonInterference", "needPreservedSourceProvenance"]


def test_inc_aebs_010_is_framed_and_next_asks_for_validation_scenarios(tmp_path: Path) -> None:
    export = tmp_path / "export.json"
    export.write_bytes(gzip.decompress(GENUINE_EXPORT.read_bytes()))
    snapshot, evaluation = evaluate_export(export, "INC-AEBS-010")
    assert snapshot.identity_mode == "export-validated-kernel-bindings"
    phases = {phase["phase"]: phase for phase in evaluation.status()["phases"]}
    framing = phases["phase0_incrementFraming"]
    assert (framing["conformance_verdict"], len(framing["gates"])) == (me.VERDICT_PASS, 14)
    assert phases["phase4_needs"]["applicability"] == "declared"  # an optional [0..1] step
    step = evaluation.next_obligation()["next"]
    assert (step["gate"], step["kind"]) == ("needHasValidationScenario", "violation")
    assert [subject["name"] for subject in step["subjects"]] == NEEDS
    assert step["what_to_author"].endswith(
        ": connection <name> : ValidationPlanningAssociation connect needCorrelatableEvidence to <scenario>;")
    needs = {gap["gate"]: len(gap["subjects"]) for gap in evaluation.gaps()["blocking"]
             if gap["phase"] == "phase4_needs"}
    assert needs == {"needHasValidationScenario": 5, "needFramesConcern": 5}


def _stale_sources(manifest) -> list[str]:
    """Model files of the cut whose HEAD blob differs from the export's (libraries are not tracked)."""
    def head_sha256(path: str) -> str:
        shown = subprocess.run(["git", "show", f"HEAD:{path}"], cwd=ROOT, capture_output=True)
        return hashlib.sha256(shown.stdout).hexdigest() if shown.returncode == 0 else ""
    return [entry["path"] for entry in manifest
            if not entry["path"].startswith(".sysand/") and head_sha256(entry["path"]) != entry["sha256"]]


def test_the_cut_matches_the_model_files_at_head() -> None:
    stale = _stale_sources(json.loads(gzip.decompress(GENUINE_EXPORT.read_bytes()))["source_manifest"])
    assert not stale, (f"{stale} changed since the cut; re-cut the fixture with "
                       "tests/fixtures/genuine_export/cut_increment_export.py")
