"""The parity of the PLEML receipts with the YAML path (ADR 0022, plan step S4).

The parity runs on the committed receipts and the real configurator, as public
CI runs it; the checks of a row beyond its class are unit-tested on synthetic
records.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from de4sdv.semantic import pleml_receipts as receipts
from scripts import check_pleml_parity as parity
from scripts import run_ple_authority as runner

ROOT = Path(__file__).resolve().parents[1]

#: The class of every row, as plan section 5 states it.
EXPECTED_ROWS = {
    "aebs-autoware-linux-lidar-camera.yaml": "equal",
    "apollo-qnx-qvm.yaml": "equal",
    "apple-silicon-macos-candidate.yaml": "equal",
    "example-linux-score-autoware.yaml": "equal",
    "inc-aebs-009a-jetson.yaml": "equal",
    "middleware-autoware-aaos-sdv-reference.yaml": "equal",
    "nxp-zephyr-vehicle-target-candidate.yaml": "equal",
    "fixtures/invalid-score-android.yaml": "both-reject",
    "both-alternatives": "both-reject",
    "no-alternative": "both-reject",
    "ug-09-autosar-acrn": "equal",
    "ug-10-openpilot-no-middleware": "equal",
    "ug-10-radar-only": "equal",
    "ug-10-lidar-only": "equal",
    "ug-10-camera-only": "equal",
    "ug-10-vehicle-target-aebs-false": "not-expressible",
    "catalogue-only-adaptive-cruise-control": "equal",
    "derived-set-mixed": "equal",
    "unsupported-openpilot-android-sdv": "both-reject",
    "unsupported-openpilot-autosar-adaptive": "both-reject",
    "unsupported-apollo-android-sdv": "both-reject",
    "unsupported-apollo-autosar-adaptive": "both-reject",
    "hand-picked-adapter": "both-reject",
    "pair-openpilot-eclipse-score": "equal",
    "pair-apollo-no-middleware": "equal",
}
#: The reason class each rejected row shares between the two sides (plan section 5).
REJECTIONS = {
    "fixtures/invalid-score-android.yaml": ["constraint C001"],
    "both-alternatives": ["upper-bound"],
    "no-alternative": ["lower-bound"],
    "unsupported-openpilot-android-sdv": ["pair-exclusion"],
    "unsupported-openpilot-autosar-adaptive": ["pair-exclusion"],
    "unsupported-apollo-android-sdv": ["pair-exclusion"],
    "unsupported-apollo-autosar-adaptive": ["pair-exclusion"],
    "hand-picked-adapter": ["derived-variant-not-selectable"],
}


@pytest.fixture(scope="module")
def report() -> dict:
    return parity.run(ROOT)


def _rows(report: dict) -> dict[str, dict]:
    return {row["row"]: row for row in report["rows"]}


def test_the_parity_holds_on_the_committed_receipts(report) -> None:
    assert report["failures"] == []
    assert report["histogram"] == parity.EXPECTED == {"equal": 16, "both-reject": 8, "not-expressible": 1,
                                                       "defect": 0}
    assert {row["row"]: row["class"] for row in report["rows"]} == EXPECTED_ROWS
    assert report["native_expression_executed"] is False and report["qualified"] is False


def test_a_rejected_row_shares_its_reason_class(report) -> None:
    rows = _rows(report)
    for row, reasons in REJECTIONS.items():
        assert rows[row]["yaml"]["reasons"] == rows[row]["pleml"]["reasons"] == reasons, row


def test_the_seven_projections_have_one_body_on_all_three_sides(report) -> None:
    """Plan section 5 (R19): the committed file, the YAML path and the receipt."""
    assert len(report["bodies"]) == 7
    assert all(item["equal"] for item in report["bodies"]), report["bodies"]


def test_the_valid_rows_exercise_every_derivation_rule(report) -> None:
    """R10: each of the eight allowed application-middleware pairs is a valid row."""
    rules = {rule for row in report["rows"] if row["pleml"]["valid"] for rule in row["pleml"]["rules"].values()}
    [model] = json.loads((ROOT / parity.RECEIPTS / "sdv_product_line.receipt.json").read_text())["evaluation"][
        "feature_models"]
    assert len(model["derivations"]) == 1
    assert rules == {rule["rule"] for rule in model["derivations"][0]["rules"]}
    assert len(rules) == 8


def test_the_not_expressible_row_compares_its_remainder(report) -> None:
    row = _rows(report)["ug-10-vehicle-target-aebs-false"]
    assert row["yaml"]["reasons"] == ["common-capability-false"] and row["yaml"]["violations"] == 1
    assert row["pleml"]["valid"] is True
    assert row["detail"] == "pinned construct common-capability-false"
    # The remainder restates the standalone member's selection, whose retained admission it compares.
    assert row["admission"]["compared"] is True and row["admission"]["retained"]["admitted"] is True


def test_admission_is_compared_wherever_the_retained_record_holds_a_verdict(report) -> None:
    compared = {row["row"] for row in report["rows"] if row["admission"]["compared"]}
    files = {"aebs-autoware-linux-lidar-camera.yaml", "apollo-qnx-qvm.yaml", "example-linux-score-autoware.yaml",
             "middleware-autoware-aaos-sdv-reference.yaml", "fixtures/invalid-score-android.yaml"}
    assert compared == files | {probe.row for probe in parity.PROBE_ROWS if probe.kind == "frozen"}
    for row in report["rows"]:
        if row["admission"]["compared"]:
            assert row["admission"]["pleml"] == row["admission"]["retained"], row["row"]


def test_the_required_ci_runs_the_parity_once_the_fenced_package_is_installed() -> None:
    """From S4 on, parity gates every step: the required ``checks`` job runs it on every pull request."""
    import yaml

    steps = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))["jobs"]["checks"]["steps"]
    runs = [step.get("run", "") for step in steps]
    [parity_step] = [index for index, run in enumerate(runs) if "scripts/check_pleml_parity.py" in run]
    [package_step] = [index for index, run in enumerate(runs) if "scripts/check_pleml_package.py" in run]
    assert package_step < parity_step
    assert runs[parity_step].strip() == "python scripts/check_pleml_parity.py"
    assert "env" not in steps[parity_step], "the parity needs no licence and no secret"


def test_the_probe_rows_are_the_probes_the_authority_job_serializes() -> None:
    assert tuple(probe.document for probe in parity.PROBE_ROWS) == runner.PARITY_PROBES
    assert len({probe.row for probe in parity.PROBE_ROWS}) == 17
    assert all(probe.kind in {"frozen", "closed-world", "pair"} for probe in parity.PROBE_ROWS)


def test_the_frozen_probes_are_the_generated_rows_of_the_retained_record() -> None:
    """N12: all ten probes are frozen from the retained comparison, independent of the PLE-S receipt."""
    record = parity.load_record(ROOT)
    generated = [case for case, row in record.items() if row["operational_input"]["kind"] == "generated"]
    frozen = [probe for probe in parity.PROBE_ROWS if probe.kind == "frozen"]
    assert [probe.row for probe in frozen] == generated
    assert all(record[probe.row]["operational_input"]["name"] == probe.name for probe in frozen)
    assert receipts.sha256((ROOT / parity.RECORD).read_bytes()) == parity.RECORD_SHA256


def test_a_changed_record_refuses_the_parity(monkeypatch) -> None:
    monkeypatch.setattr(parity, "RECORD_SHA256", "0" * 64)
    with pytest.raises(parity.ParityRefused, match="retained record"):
        parity.load_record(ROOT)


def test_a_receipt_that_does_not_reproduce_refuses_the_parity(tmp_path, monkeypatch) -> None:
    """An edited verdict over the genuine elements is refused by the replay before any row is compared."""
    copied = tmp_path / "receipts"
    shutil.copytree(ROOT / parity.RECEIPTS, copied)
    path = copied / "sdv_product_line.receipt.json"
    receipt = json.loads(path.read_text())
    configuration = receipt["evaluation"]["feature_models"][0]["configurations"][0]
    configuration["valid"] = not configuration["valid"]
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    monkeypatch.setattr(parity, "RECEIPTS", copied)
    configurator = parity.pleml_shadow.load_configurator(ROOT)
    with pytest.raises(parity.ParityRefused, match="do not hold"):
        parity.load_receipts(configurator, ROOT)


# -- the checks of a row beyond its class (synthetic records) ---------------------------------------


def _synthetic(states: dict[str, str]) -> parity.Evaluated:
    features = [
        {"path": "stack", "owner": None, "group": None, "members": [], "multiplicity": {"lower": 1, "upper": 1}},
        {"path": "stack.os", "owner": "stack", "group": None, "members": ["stack.linux", "stack.qnx"],
         "multiplicity": {"lower": 1, "upper": 1}},
        {"path": "stack.linux", "owner": "stack", "group": "stack.os", "members": [],
         "multiplicity": {"lower": 0, "upper": 1}},
        {"path": "stack.qnx", "owner": "stack", "group": "stack.os", "members": [],
         "multiplicity": {"lower": 0, "upper": 1}},
        {"path": "stack.extra", "owner": "stack", "group": None, "members": [],
         "multiplicity": {"lower": 0, "upper": 1}},
    ]
    paths = {"stack": "Stack", "stack.os": "Stack.OS", "stack.linux": "Stack.OS.Linux", "stack.qnx": "Stack.OS.QNX",
             "stack.extra": "Stack.Extra"}
    return parity.Evaluated(Path("receipt.json"), {}, {"features": features}, {"states": states},
                            {"catalogue_paths": paths}, Path("catalogue.yaml"), "assets.sysml")


def test_the_restatement_holds_when_the_configuration_states_the_selection() -> None:
    evaluated = _synthetic({"stack": "enabled", "stack.os": "enabled", "stack.linux": "enabled",
                            "stack.qnx": "omitted", "stack.extra": "disabled"})
    assert parity.restatement_errors({"Stack.OS": "Linux", "Stack.Extra": False, "Common.Thing": True},
                                     evaluated) == []


def test_the_restatement_names_every_difference() -> None:
    evaluated = _synthetic({"stack": "enabled", "stack.os": "enabled", "stack.linux": "omitted",
                            "stack.qnx": "enabled", "stack.extra": "enabled"})
    assert parity.restatement_errors({"Stack.OS": "Linux"}, evaluated) == [
        "Stack.OS: the selection chooses ['Stack.OS.Linux'], the configuration ['Stack.OS.QNX']",
        "Stack.Extra: the configuration sets it, the selection does not",
    ]
    assert parity.restatement_errors({"Stack.OS": "QNX", "Stack.Extra": False}, evaluated) == [
        "Stack.Extra: the selection is False, the configuration enabled"]


def test_a_selected_feature_without_a_catalogue_path_is_a_restatement_error() -> None:
    """A feature the catalogue does not restate cannot be selected on the YAML side, so it is a difference."""
    evaluated = _synthetic({"stack": "enabled", "stack.os": "enabled", "stack.linux": "enabled",
                            "stack.qnx": "omitted", "stack.extra": "omitted"})
    del evaluated.writer["catalogue_paths"]["stack.linux"]
    assert parity.restatement_errors({"Stack.OS": "Linux"}, evaluated) == [
        "Stack.OS: the selection chooses ['Stack.OS.Linux'], the configuration ['stack.linux (no catalogue path)']"]


def test_an_unclassified_configurator_message_refuses_the_parity(monkeypatch, tmp_path) -> None:
    """A rejection outside the reason map is a gap in the parity, never a guessed class (R11)."""
    configurator = parity.pleml_shadow.load_configurator(ROOT)
    fixture = parity.CONFIGURATIONS / "fixtures/invalid-score-android.yaml"
    evaluated = parity.load_receipts(configurator, ROOT)[parity.configuration_of(fixture)]

    def unclassified(messages, selections, catalogue):
        raise ValueError(f"unclassified configurator message: {messages[0]}")

    monkeypatch.setattr(parity, "yaml_reason_keys", unclassified)
    with pytest.raises(parity.ParityRefused, match="the reason map of the parity needs it"):
        parity.yaml_outcome(ROOT / fixture, {}, evaluated, tmp_path, "fixture")


def _configurations() -> list[dict]:
    return [configuration for path in sorted((ROOT / parity.RECEIPTS).glob("*.receipt.json"))
            for model in json.loads(path.read_text(encoding="utf-8"))["evaluation"]["feature_models"]
            for configuration in model["configurations"]]


def test_no_invalid_configuration_of_the_committed_receipts_is_admitted() -> None:
    """Admission requires validity (decision of 2026-10-20). The receipts before the fix admitted the
    invalid hand-picked-adapter probe, whose features alone realize the standalone member."""
    configurations = _configurations()
    invalid = [item for item in configurations if not item["valid"]]
    assert len(invalid) == 8
    assert [item["configuration"] for item in invalid if item["admission"]["admitted"] is not False] == []
    for item in invalid:
        classes = ", ".join(sorted({reason["class"] for reason in item["reasons"]}))
        assert item["admission"]["reasons"][0] == f"invalid configuration: {classes}", item["configuration"]
    [probe] = [item for item in configurations if item["configuration"] == "handPickedAdapterProbe"]
    assert probe["admission"]["reasons"][0] == "invalid configuration: derived-variant-not-selectable"
    assert probe["admission"]["alternative"] == "standalone", "the rest of its admission record is kept"


def test_the_parity_refuses_an_invalid_configuration_that_is_admitted() -> None:
    admitted = {"valid": False, "admission": {"admitted": True, "alternative": "standalone"}}
    assert parity.admission_problems(admitted, None) == [
        "an invalid configuration is admitted (True); admission requires validity"]
    undecided = {"valid": False, "admission": {"admitted": None}}
    assert parity.admission_problems(undecided, None) == [
        "an invalid configuration is admitted (None); admission requires validity"]
    refused = {"valid": False, "admission": {"admitted": False, "alternative": "standalone"}}
    assert parity.admission_problems(refused, {"admitted": False, "alternative": None}) == []
    member = {"valid": True, "admission": {"admitted": True, "alternative": "standalone"}}
    assert parity.admission_problems(member, {"admitted": True, "alternative": "standalone"}) == []
    assert parity.admission_problems(member, {"admitted": False, "alternative": None}) == [
        "admission {'admitted': True, 'alternative': 'standalone'} differs from the retained YAML-era verdict "
        "{'admitted': False, 'alternative': None}"]


def _result(row: str, kind: str, cls: str, valid: bool = True) -> dict:
    return {"row": row, "kind": kind, "class": cls, "detail": "x" if cls == "defect" else "",
            "pleml": {"valid": valid}}


def _gate_inputs(report: dict) -> tuple[list[dict], list[dict]]:
    return ([_result(row["row"], row["kind"], row["class"], row["pleml"]["valid"]) for row in report["rows"]],
            [dict(item) for item in report["bodies"]])


def test_the_gate_holds_only_with_the_plans_histogram_and_seven_equal_bodies(report) -> None:
    results, bodies = _gate_inputs(report)
    assert parity.gate(results, bodies) == (parity.EXPECTED, [])
    # A row that turns into a defect fails twice: as a defect and as the histogram.
    broken = [dict(item, **{"class": "defect", "detail": "x"}) if item["row"] == "ug-10-radar-only" else item
              for item in results]
    histogram, failures = parity.gate(broken, bodies)
    assert histogram["defect"] == 1 and histogram["equal"] == 15
    assert failures[0] == "ug-10-radar-only: defect: x" and "the plan expects" in failures[1]
    # A body that differs fails, and so does a configuration without a parity row.
    differing = [dict(bodies[0], equal=False, pleml_equal=False)] + bodies[1:]
    assert parity.gate(results, differing)[1] == [
        f"{bodies[0]['projection']}: the normalised bodies differ (YAML path equal: True, receipt equal: False)"]
    assert parity.gate(results, bodies, ["new_member.sysml"])[1][0].startswith(
        "configurations without a parity row: ['new_member.sysml']")
    # A committed projection that goes missing fails.
    assert "one per valid bill of features" in parity.gate(results, bodies[1:])[1][0]


def test_the_remainder_drops_only_a_common_capability_set_to_false() -> None:
    catalogue = parity.pleml_shadow.Catalogue(ROOT / "model-based-product-line-engineering/feature-models/"
                                              "sdv_product_line.yaml", ROOT)
    selections = {"Capabilities.ForwardCollisionMitigation.VehicleTargetAEBS": False,
                  "Capabilities.LaneKeepAssist": False, "PlatformStack.OS": "Linux"}
    kept, dropped = parity.remainder(selections, catalogue)
    assert dropped == ["Capabilities.ForwardCollisionMitigation.VehicleTargetAEBS"]
    assert kept == {"Capabilities.LaneKeepAssist": False, "PlatformStack.OS": "Linux"}
