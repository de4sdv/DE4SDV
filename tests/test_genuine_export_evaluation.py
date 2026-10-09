"""The frozen genuine-export cut: evaluated end to end, and checked against its own records.

``fixtures/genuine_export/inc-aebs-010.json.gz`` is a frozen sample of real
serializer shapes (see the README beside it): a cut of the licensed export of
one revision, kept unchanged. These tests assert outcomes of that frozen cut,
never of the current model. It is evaluated exactly as
``scripts/evaluate_increment.py`` evaluates an export: kernel identity
validated from the export, every serializer shape the real one.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
from pathlib import Path

from de4sdv.semantic import method_evaluator as me
from de4sdv.semantic.export_evaluation import evaluate_export
from increment_model_fixtures import GENUINE_EXPORT

NEEDS = ["needCorrelatableEvidence", "needFailClosedDegradation", "needLiveVisualizationOnAAOS",
         "needNonInterference", "needPreservedSourceProvenance"]


def test_the_frozen_cut_is_framed_and_next_asks_for_validation_scenarios(tmp_path: Path) -> None:
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


def _canonical(value) -> bytes:
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode()


def _inconsistencies(text: bytes) -> list[str]:
    """How the cut's JSON departs from its own records (empty when self-consistent)."""
    cut = json.loads(text)
    found = [] if _canonical(cut) == text else ["the file is not the cut script's canonical serialization"]
    recorded = cut["cut_from"]["content_sha256"]
    found += [f"{part} differ from their recorded sha256" for part in ("elements", "element_sources")
              if hashlib.sha256(_canonical(cut[part])).hexdigest() != recorded[part]]
    if set(cut["element_sources"]) != {element["@id"] for element in cut["elements"]}:
        found.append("the element sources do not cover exactly the elements")
    files = {path for path in cut["element_sources"].values() if not path.startswith("@library/")}
    manifest = {entry["path"]: entry["sha256"] for entry in cut["source_manifest"]}
    if files != set(manifest) or not all(re.fullmatch(r"[0-9a-f]{64}", sha) for sha in manifest.values()):
        found.append(f"the source manifest does not list the source files: {sorted(files ^ set(manifest))}")
    if not re.fullmatch(r"[0-9a-f]{40}", str(cut.get("git_commit"))):
        found.append("no source revision is recorded")
    return found


def test_the_frozen_cut_is_self_consistent() -> None:
    """The cut matches its own records; it is never compared with the model at HEAD."""
    assert _inconsistencies(gzip.decompress(GENUINE_EXPORT.read_bytes())) == []
