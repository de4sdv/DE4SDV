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
from pathlib import Path

from de4sdv.semantic import method_evaluator as me
from de4sdv.semantic.export_evaluation import evaluate_export
from increment_model_fixtures import GENUINE_EXPORT

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
