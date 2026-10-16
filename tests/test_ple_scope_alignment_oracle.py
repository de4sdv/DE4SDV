"""The PLE-S comparison oracle (UG-09, UG-10, UG-14) over the retained receipt.

The oracle runs the unchanged configurator on the committed configurations and
on generated probes, and derives ``admitted-by-governed-scope`` from the
serialized PLE-S receipt and governed-scope validation of the retained
licensed run. These tests assert sets of cases and classifications, never
counts; they fail, never skip, when a retained input is missing; and they
prove that admission moves with the governed scope (a synthetic
reclassification changes the verdict) and that a changed derivation or a
missing correspondence is a defect that exits non-zero.
"""

from __future__ import annotations

import copy
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from scripts import compare_ple_scope_alignment as oracle

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/product-line-engineering/ple-s-scope-alignment-evidence"
RECEIPT = EVIDENCE / "receipt.json"
GOVERNED = EVIDENCE / "governed-scope-validation.json"
RETAINED = EVIDENCE / "comparison.json"
MANIFEST = EVIDENCE / "manifest.json"
README = EVIDENCE / "README.md"
DOC = ROOT / "docs/product-line-engineering/ple-s-scope-alignment.md"
CORRESPONDENCE = ROOT / oracle.CORRESPONDENCE
EXECUTOR = "7e895252ce2b3b3d5d404d2176cc7872b7f671e3"
MERGE = "606141c80ad83b320a88fd2644f23558cf4fdb8b"
RUN_ID = "38788579272"
ARTIFACT = f"ple-scope-alignment-{EXECUTOR}-{RUN_ID}"
CASES = {
    "standalone-member", "aaos-integrated-member", "both-alternatives", "no-alternative",
    "ug-09-eclipse-score", "ug-09-apollo-qnx-qvm", "ug-10-openpilot-no-middleware", "ug-10-radar-only",
    "both-axes-negative",
}
HEX64 = re.compile(r"[0-9a-f]{64}")


@pytest.mark.parametrize("path", [RECEIPT, GOVERNED, RETAINED, MANIFEST, README, DOC, CORRESPONDENCE,
                                  ROOT / oracle.CATALOGUE, ROOT / oracle.CONFIGURATOR, ROOT / oracle.SHARED_ASSETS])
def test_every_retained_and_operational_input_is_present(path: Path) -> None:
    assert path.is_file(), f"missing input: {path.relative_to(ROOT)}"


@pytest.fixture(scope="module")
def evidence():
    return oracle.load_evidence(RECEIPT, GOVERNED, evidence="retained", run_id=RUN_ID, artifact=ARTIFACT)


@pytest.fixture(scope="module")
def comparison(evidence):
    return oracle.run_oracle(evidence)


def _rows(comparison) -> dict[str, dict]:
    return {row["case"]: row for row in comparison["rows"]}


def _blocking_governed(row) -> set[str]:
    """Governed elements that block admission: inadmissible classifications of selected items."""
    names = set()
    for record in row["admitted_by_governed_scope"]["selections"]:
        if not record["selected"] or record["unclassified"]:
            continue
        kinds = {kind["kind"] for kind in record["classifications"]}
        if kinds & oracle.ADMISSIBLE:
            continue
        names |= {kind["governed"] for kind in record["classifications"] if kind["kind"] in oracle.INADMISSIBLE}
    return names


# -- the table -------------------------------------------------------------------------


def test_every_case_of_the_design_is_classified_and_nothing_is_a_defect(comparison) -> None:
    rows = _rows(comparison)
    assert set(rows) == CASES
    assert {row["class"] for row in rows.values()} <= set(oracle.CLASSES)
    assert comparison["summary"]["defects"] == [] and comparison["summary"]["unclassified"] == []
    assert comparison["summary"]["exit_code"] == 0
    assert {name for name, cases in comparison["summary"]["classes"].items() if cases} == {
        "equal", "intentional-scope", "intentional-representation", "not-expressible-under-tool"}
    for row in rows.values():
        assert row["class_reason"]
        assert row["configuration_valid_under_current_tool"]["exit_code"] in (0, 1)
        assert row["ple_s"]["summary"]
    assert comparison["qualified"] is False and comparison["adoption_authorized"] is False
    assert comparison["authority_activation_authorized"] is False


def test_the_two_fields_are_reported_separately(comparison) -> None:
    rows = _rows(comparison)
    valid = {case for case, row in rows.items() if row["configuration_valid_under_current_tool"]["valid"]}
    admitted = {case for case, row in rows.items() if row["admitted_by_governed_scope"]["admitted"]}
    assert valid == {"standalone-member", "aaos-integrated-member", "ug-09-eclipse-score", "ug-09-apollo-qnx-qvm",
                     "ug-10-openpilot-no-middleware", "ug-10-radar-only"}
    assert admitted == {"standalone-member", "aaos-integrated-member"}
    assert valid - admitted == {"ug-09-eclipse-score", "ug-09-apollo-qnx-qvm",
                               "ug-10-openpilot-no-middleware", "ug-10-radar-only"}
    assert {case for case in CASES if case not in valid and case not in admitted} == {
        "both-alternatives", "no-alternative", "both-axes-negative"}


# -- UG-09: tool validity stays distinct from governed admission ------------------------


def test_ug09_the_configurator_accepts_reference_only_alternatives_the_scope_does_not_admit(comparison, evidence) -> None:
    rows = _rows(comparison)
    reference_only = evidence["governed"]["reference_only"]
    expected = {"ug-09-eclipse-score": {"eclipseSCORE"},
                "ug-09-apollo-qnx-qvm": {"apollo", "eclipseSCORE", "qnxQVM", "sensingVariability"}}
    for case, names in expected.items():
        row = rows[case]
        assert row["configuration_valid_under_current_tool"]["valid"] is True
        assert row["admitted_by_governed_scope"]["admitted"] is False
        assert row["class"] == "intentional-scope"
        assert _blocking_governed(row) == names
        assert row["ple_s"]["configuration"] is None
        assert row["comparison"]["ple_s_expected"] is None and row["comparison"]["tool_selected"]
    # The reference-only classification is read from the serialized governed scope, element id included.
    score = rows["ug-09-eclipse-score"]
    [record] = [r for r in score["admitted_by_governed_scope"]["selections"] if r["node"] == "F-PLATFORM-MIDDLEWARE-ECLIPSE-SCORE"]
    [kind] = record["classifications"]
    assert kind["kind"] == "reference-only" and kind["governed_id"] == reference_only["eclipseSCORE"]
    assert kind["source"].startswith("governed-scope-validation:reference_only[eclipseSCORE]")
    assert record["catalogue_role"] == "feature"
    apollo = rows["ug-09-apollo-qnx-qvm"]
    assert {r["node"] for r in apollo["admitted_by_governed_scope"]["selections"] if "reference-only" in
            {k["kind"] for k in r["classifications"]}} == {
        "F-PLATFORM-VEHICLE-APPLICATION-APOLLO", "F-PLATFORM-MIDDLEWARE-ECLIPSE-SCORE",
        "F-PLATFORM-OS-QNX", "F-PLATFORM-HYPERVISOR-QVM"}


# -- UG-10: common content mapped as a distinguishing feature ---------------------------


def test_ug10_common_content_mapped_as_features_is_rejected_within_the_governed_portfolio(comparison, evidence) -> None:
    rows = _rows(comparison)
    deferred = evidence["governed"]["deferred"]
    openpilot = rows["ug-10-openpilot-no-middleware"]
    assert openpilot["configuration_valid_under_current_tool"]["valid"] is True
    assert openpilot["class"] == "intentional-scope"
    assert _blocking_governed(openpilot) == {"openpilot"}
    assert openpilot["admitted_by_governed_scope"]["unrepresented_common_assets"] == ["autowareApplication"]
    [application] = [r for r in openpilot["admitted_by_governed_scope"]["selections"]
                     if r["node"] == "F-PLATFORM-VEHICLE-APPLICATION-OPENPILOT"]
    assert application["group"]["catalogue_role"] == "feature"
    assert {(k["kind"], k["governed"], k["governed_id"]) for k in application["group"]["classifications"]} == {
        ("deferred", "drivingStackVariability", deferred["drivingStackVariability"])}
    assert openpilot["operational_input"]["kind"] == "generated"
    assert openpilot["operational_input"]["selections"]["PlatformStack.Middleware"] == "None"

    radar = rows["ug-10-radar-only"]
    assert radar["configuration_valid_under_current_tool"]["valid"] is True
    assert radar["class"] == "intentional-scope"
    assert _blocking_governed(radar) == {"sensingVariability"}
    assert radar["admitted_by_governed_scope"]["unrepresented_common_assets"] == ["currentSensingBaseline"]
    [sensor] = [r for r in radar["admitted_by_governed_scope"]["selections"] if r["node"] == "F-SENSING-PERCEPTION-RADAR"]
    assert sensor["catalogue_role"] == "feature"
    assert {(k["kind"], k["governed_id"]) for k in sensor["classifications"]} == {("deferred", deferred["sensingVariability"])}
    assert radar["operational_input"]["selections"]["SensingBoundary.PerceptionSensors"] == ["Radar"]


def test_common_content_of_the_members_is_classified_common_by_the_governed_scope(comparison, evidence) -> None:
    rows = _rows(comparison)
    common = evidence["governed"]["common_core"]
    for case in ("standalone-member", "aaos-integrated-member"):
        selections = rows[case]["admitted_by_governed_scope"]["selections"]
        by_node = {r["node"]: r for r in selections if r["selected"]}
        assert {k["governed_id"] for k in by_node["F-PLATFORM-VEHICLE-APPLICATION-AUTOWARE"]["classifications"]} == {
            common["autowareApplication"]}
        assert {k["governed_id"] for k in by_node["C-CAPABILITY-AEBS-VEHICLE-TARGET"]["classifications"]} == {
            common["vehicleTargetAEBS"]}
        assert {k["governed_id"] for n in ("F-SENSING-PERCEPTION-LIDAR", "F-SENSING-PERCEPTION-CAMERA")
                for k in by_node[n]["classifications"]} == {common["currentSensingBaseline"]}
        statuses = {item["asset"]: item["status"] for item in rows[case]["admitted_by_governed_scope"]["common_assets"]}
        assert statuses["protectedEmergencyCommandPathIndependence"] == "outside the catalogue's selection surface"
        assert statuses["vehicleTargetAEBS"] == "represented"


# -- UG-14: every difference classified, provenance carried -----------------------------


def test_ug14_the_members_derive_the_same_assets_on_both_paths(comparison) -> None:
    rows = _rows(comparison)
    for case, alternative in (("standalone-member", "standalone"), ("aaos-integrated-member", "aaosIntegrated")):
        row = rows[case]
        assert row["admitted_by_governed_scope"]["implied_alternative"] == alternative
        assert row["ple_s"]["status"] == "configuration-valid" and row["ple_s"]["role"] == "member"
        assert row["comparison"]["tool_selected"] == row["comparison"]["ple_s_expected"]
        assert set(row["comparison"]["tool_selected"]) == {
            "vehicleApplication", "middleware", "osPlatform", "hypervisor", "applicationMiddlewareAdapter"}
        assert row["comparison"]["differing"] == []
    assert rows["standalone-member"]["class"] == "equal"
    assert rows["aaos-integrated-member"]["class"] == "intentional-representation"


def test_ug14_the_known_representation_difference_manifests_only_where_the_runtime_is_unrepresented(comparison) -> None:
    rows = _rows(comparison)
    standalone = {d["common_asset"]: d for d in rows["standalone-member"]["comparison"]["representation_differences"]}
    integrated = {d["common_asset"]: d for d in rows["aaos-integrated-member"]["comparison"]["representation_differences"]}
    assert set(standalone) == set(integrated) == {"linuxROS2AutowareRuntime"}
    assert standalone["linuxROS2AutowareRuntime"]["manifests"] is False
    assert standalone["linuxROS2AutowareRuntime"]["represented_by"] == ["F-PLATFORM-OS-LINUX"]
    difference = integrated["linuxROS2AutowareRuntime"]
    assert difference["manifests"] is True and difference["represented_by"] == []
    assert difference["classification"] == "intentional-representation" and difference["variation"] == "osPlatform"
    assert "INC-MW-011" in difference["disposition"] and "INC-MW-011" in rows["aaos-integrated-member"]["class_reason"]
    # The difference is owned elsewhere; the oracle neither widens PLE-S nor calls it a model increment candidate.
    assert "candidate" not in rows["aaos-integrated-member"]["class_reason"]


def test_ug14_every_row_carries_the_projection_digests_and_the_receipt_identity(comparison) -> None:
    catalogue = oracle.sha256_of(ROOT / oracle.CATALOGUE)
    shared = oracle.sha256_of(ROOT / oracle.SHARED_ASSETS)
    for row in comparison["rows"]:
        provenance = row["provenance"]
        for key in ("feature_model_sha256", "bill_of_features_sha256", "shared_assets_sha256"):
            assert HEX64.fullmatch(provenance[key]), (row["case"], key)
        assert provenance["feature_model_sha256"] == catalogue
        assert provenance["shared_assets_sha256"] == shared
        assert provenance["bill_of_features_sha256"] == row["operational_input"]["sha256"]
        assert provenance["shared_assets_source_baseline"].startswith("git-blob:")
        valid = row["configuration_valid_under_current_tool"]["valid"]
        assert provenance["digest_origin"] == ("projection header" if valid
                                               else "computed by the oracle (the tool generated no projection)")
        receipt = provenance["ple_s_receipt"]
        assert receipt["executor_revision"] == EXECUTOR and receipt["run_id"] == RUN_ID
        assert receipt["artifact"] == ARTIFACT and receipt["evidence"] == "retained"
        assert HEX64.fullmatch(receipt["receipt_sha256"]) and HEX64.fullmatch(receipt["model_sha256"])
        assert receipt["pleml_pin"] == "5f8ab8560219dc24d8ec7ec90d6f0a145896ef8e"
        assert (receipt["configuration_element_id"] is None) == (row["ple_s"]["configuration"] is None)


def test_the_receipt_identity_is_bound_to_the_tree_content(comparison, evidence) -> None:
    identity = comparison["ple_s"]
    assert identity["model_sha256"] == oracle.sha256_of(ROOT / oracle.MODEL)
    assert identity["evaluator_sha256"] == oracle.sha256_of(ROOT / oracle.EVALUATOR)
    assert identity["governed_scope_sha256"] == oracle.sha256_of(ROOT / oracle.SCOPE)
    assert identity["shared_assets_sha256"] == oracle.sha256_of(ROOT / oracle.SHARED_ASSETS)
    assert identity["interpreter_revision"] == "6a99626b4af7cd01108f27dac88bf5b55bba207a"
    assert identity["executor_inputs_matching_tree"][oracle.MODEL.as_posix()] is True
    assert identity["qualified"] is False and identity["expectation_matches"] is True


# -- the probes: recorded, not asserted in advance ------------------------------------


def test_both_alternatives_has_no_scalar_encoding_and_the_tool_refuses_the_list(comparison) -> None:
    row = _rows(comparison)["both-alternatives"]
    encoding = row["operational_input"]["encoding"]
    assert encoding["expressible"] is False
    assert sorted(encoding["selected_alternatives"]) == ["aaosIntegrated", "standalone"]
    assert {key: sorted(value) for key, value in encoding["selections"].items()} == {
        "PlatformStack.Middleware": ["AndroidSDV", "None"], "PlatformStack.OS": ["Android", "Linux"],
        "PlatformStack.Hypervisor": ["KVM", "None"]}
    tool = row["configuration_valid_under_current_tool"]
    assert tool["valid"] is False and tool["exit_code"] == 1
    assert any("not a valid XOR choice" in message for message in tool["messages"])
    assert row["ple_s"]["violated_bound"] == "upper" and row["ple_s"]["status"] == "configuration-invalid"
    assert row["class"] == "not-expressible-under-tool"
    assert row["comparison"]["tool_selected"] is None and row["comparison"]["ple_s_expected"] is None


def test_no_alternative_is_recorded_as_the_tool_and_the_scope_answer_it(comparison) -> None:
    row = _rows(comparison)["no-alternative"]
    encoding = row["operational_input"]["encoding"]
    assert encoding["expressible"] is True and encoding["selected_alternatives"] == []
    assert set(encoding["removed"]) == {"PlatformStack.Middleware", "PlatformStack.OS", "PlatformStack.Hypervisor"}
    assert "PlatformStack.VehicleApplication" in row["operational_input"]["selections"]
    tool = row["configuration_valid_under_current_tool"]
    assert isinstance(tool["exit_code"], int) and tool["meaning"] in oracle.EXIT_MEANING.values()
    assert tool["messages"], "the tool's actual response is recorded"
    assert row["ple_s"]["violated_bound"] == "lower"
    assert row["admitted_by_governed_scope"]["admitted"] is False
    assert row["admitted_by_governed_scope"]["implied_alternative"] is None
    assert row["class"] in oracle.CLASSES and row["class"] != "defect"


def test_both_axes_negative_shows_the_two_fields_are_independent(comparison) -> None:
    row = _rows(comparison)["both-axes-negative"]
    tool = row["configuration_valid_under_current_tool"]
    assert tool["valid"] is False and tool["violated_constraints"] == ["C001"]
    assert row["admitted_by_governed_scope"]["admitted"] is False
    assert _blocking_governed(row) == {"eclipseSCORE"}
    assert set(row["admitted_by_governed_scope"]["alternatives_realized"]) == {"aaosIntegrated", "standalone"}
    assert row["ple_s"]["configuration"] is None
    assert row["class"] == "equal" and "independent" in row["class_reason"]


def test_probes_are_generated_outside_the_repository_and_never_committed(comparison) -> None:
    tracked = subprocess.run(["git", "ls-files", "--", oracle.CONFIGURATIONS.as_posix()], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout.split()
    generated = {row["operational_input"]["name"] for row in comparison["rows"]
                 if row["operational_input"]["kind"] == "generated"}
    assert generated == {"BothIntegrationModesProbe", "NoIntegrationModeProbe", "OpenpilotNoMiddlewareProbe",
                         "RadarOnlySensingProbe"}
    for path in tracked:
        assert "Probe" not in path and "probe" not in Path(path).stem
    status = subprocess.run(["git", "status", "--porcelain", "--", oracle.CONFIGURATIONS.as_posix()], cwd=ROOT,
                            capture_output=True, text=True, check=True).stdout
    assert status == ""


# -- admission follows the governed scope, not a list ----------------------------------


def _synthetic(evidence, *, receipt=None, governed=None):
    return {"receipt": receipt or evidence["receipt"], "governed": governed or evidence["governed"],
            "identity": evidence["identity"]}


def test_a_reclassified_governed_element_changes_the_verdict_without_touching_the_oracle(evidence) -> None:
    governed = copy.deepcopy(evidence["governed"])
    governed["deferred"]["eclipseSCORE"] = governed["reference_only"].pop("eclipseSCORE")
    rows = _rows(oracle.run_oracle(_synthetic(evidence, governed=governed)))
    [record] = [r for r in rows["ug-09-eclipse-score"]["admitted_by_governed_scope"]["selections"]
                if r["node"] == "F-PLATFORM-MIDDLEWARE-ECLIPSE-SCORE"]
    assert {k["kind"] for k in record["classifications"]} == {"deferred"}
    assert rows["ug-09-eclipse-score"]["class"] == "intentional-scope"


def test_a_changed_ple_s_derivation_is_a_defect_that_exits_non_zero(evidence) -> None:
    receipt = copy.deepcopy(evidence["receipt"])
    [configuration] = [c for c in receipt["alignment"]["configurations"]
                       if c["configuration"] == "standaloneAutowareAEBSReferenceMemberConfiguration"]
    for item in configuration["derived_asset_variants"]:
        if item["variation"] == "osPlatform":
            item["variant"] = "android"
    comparison = oracle.run_oracle(_synthetic(evidence, receipt=receipt))
    rows = _rows(comparison)
    assert rows["standalone-member"]["class"] == "defect"
    assert rows["standalone-member"]["comparison"]["differing"] == ["osPlatform: tool linux, PLE-S android"]
    assert comparison["summary"]["defects"] == ["standalone-member"]
    assert comparison["summary"]["exit_code"] == 1


def test_a_selection_without_correspondence_is_unclassified_and_exits_non_zero(evidence, tmp_path) -> None:
    data = yaml.safe_load(CORRESPONDENCE.read_text(encoding="utf-8"))
    data["correspondence"] = [e for e in data["correspondence"] if e["node"] != "F-PLATFORM-MIDDLEWARE-ECLIPSE-SCORE"]
    path = tmp_path / "catalogue-correspondence.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    comparison = oracle.run_oracle(evidence, correspondence_path=path)
    rows = _rows(comparison)
    assert {case for case, row in rows.items() if row["class"] == "defect"} == {
        "ug-09-eclipse-score", "ug-09-apollo-qnx-qvm", "both-axes-negative"}
    assert set(comparison["summary"]["unclassified"]) == {"ug-09-eclipse-score", "ug-09-apollo-qnx-qvm", "both-axes-negative"}
    assert comparison["summary"]["exit_code"] == 1


@pytest.mark.parametrize("mutation, message", [
    (lambda e: e[0].update(node="F-NOT-A-NODE"), "unknown catalogue node"),
    (lambda e: e[0].update(governed="notAnElement"), "not a serialized governed-scope element"),
    (lambda e: e[0].update(governed="standalone"), "may not confer admitted-alternative"),
    (lambda e: e[0].update(governed="androidKVMTopology"), "may not confer derived"),
    (lambda e: e.append(dict(e[0])), "corresponds more than once"),
    (lambda e: e[0].update(governed=None), "needs a note"),
])
def test_the_correspondence_is_validated_against_both_sides(evidence, tmp_path, mutation, message) -> None:
    data = yaml.safe_load(CORRESPONDENCE.read_text(encoding="utf-8"))
    mutation(data["correspondence"])
    path = tmp_path / "catalogue-correspondence.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    with pytest.raises(oracle.OracleRefusal, match=message):
        oracle.run_oracle(evidence, correspondence_path=path)


def test_the_correspondence_carries_no_classification() -> None:
    data = yaml.safe_load(CORRESPONDENCE.read_text(encoding="utf-8"))
    assert data["schema"] == oracle.CORRESPONDENCE_SCHEMA
    assert {key for entry in data["correspondence"] for key in entry} <= {"node", "governed", "note"}
    for word in ("reference-only", "deferred", "excluded", "admitted"):
        assert not any(word in str(entry.get("governed")) for entry in data["correspondence"]), word


# -- refusals ------------------------------------------------------------------------------


def _write(tmp_path: Path, name: str, payload: dict) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


@pytest.mark.parametrize("mutation, message", [
    ({"qualified": True}, "qualified: false"),
    ({"executor_source_dirty": True}, "dirty"),
    ({"fresh_serialization": False}, "fresh licensed serialization"),
    ({"expectation": {"matches": False, "mismatches": ["x"]}}, "expected outcome"),
    ({"model": {"path": oracle.MODEL.as_posix(), "sha256": "0" * 64},
      "executor_inputs": {oracle.MODEL.as_posix(): "0" * 64}}, oracle.MODEL.as_posix()),
])
def test_the_oracle_refuses_a_promoted_dirty_or_stale_receipt(tmp_path, mutation, message) -> None:
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    for key, value in mutation.items():
        if isinstance(value, dict) and isinstance(receipt.get(key), dict) and key == "executor_inputs":
            receipt[key].update(value)
        else:
            receipt[key] = value
    path = _write(tmp_path, "receipt.json", receipt)
    with pytest.raises(oracle.OracleRefusal, match=re.escape(message)):
        oracle.load_evidence(path, GOVERNED, evidence="retained", run_id=RUN_ID, artifact=ARTIFACT)


def test_the_oracle_refuses_a_governed_scope_the_receipt_did_not_record(tmp_path) -> None:
    governed = json.loads(GOVERNED.read_text(encoding="utf-8"))
    governed["reference_only"]["apollo"] = "0" * 8
    path = _write(tmp_path, "governed-scope-validation.json", governed)
    with pytest.raises(oracle.OracleRefusal, match="not the one the receipt recorded"):
        oracle.load_evidence(RECEIPT, path, evidence="retained", run_id=RUN_ID, artifact=ARTIFACT)


def test_the_oracle_refuses_a_mismatched_artifact_or_run_and_retained_evidence_posing_as_fresh() -> None:
    with pytest.raises(oracle.OracleRefusal, match="artifact name"):
        oracle.load_evidence(RECEIPT, GOVERNED, evidence="retained", run_id="1", artifact=ARTIFACT)
    with pytest.raises(oracle.OracleRefusal, match="artifact name"):
        oracle.load_evidence(RECEIPT, GOVERNED, evidence="retained", run_id=RUN_ID, artifact="other")
    assert subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True,
                          check=True).stdout.strip() != EXECUTOR
    with pytest.raises(oracle.OracleRefusal, match="exact head"):
        oracle.load_evidence(RECEIPT, GOVERNED, evidence="fresh", run_id=RUN_ID, artifact=ARTIFACT)


# -- the command line and the retained record ----------------------------------------


def _cli(out: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-B", str(ROOT / "scripts/compare_ple_scope_alignment.py"),
                           "--receipt", str(RECEIPT), "--governed-scope", str(GOVERNED), "--evidence", "retained",
                           "--run-id", RUN_ID, "--artifact", ARTIFACT, "--out", str(out), *extra],
                          cwd=ROOT, capture_output=True, text=True)


def test_the_command_line_writes_the_comparison_and_refuses_an_output_inside_the_repository(tmp_path) -> None:
    result = _cli(tmp_path / "out")
    assert result.returncode == 0, result.stderr
    printed = json.loads(result.stdout)
    assert printed["defects"] == [] and printed["qualified"] is False and printed["evidence"] == "retained"
    written = json.loads((tmp_path / "out/comparison.json").read_text(encoding="utf-8"))
    assert written["schema"] == oracle.SCHEMA and {row["case"] for row in written["rows"]} == CASES
    assert (tmp_path / "out/comparison.md").read_text(encoding="utf-8") == oracle.render_markdown(written)
    again = _cli(tmp_path / "out")
    assert again.returncode == 2 and "existing output directory" in again.stderr
    inside = _cli(ROOT / "docs/ple-s-oracle-must-not-write-here")
    assert inside.returncode == 2 and "outside the repository" in inside.stderr
    assert not (ROOT / "docs/ple-s-oracle-must-not-write-here").exists()


def _comparable(comparison: dict) -> dict:
    """The comparison without the oracle's own revision: the retained file is content-addressed."""
    stripped = copy.deepcopy(comparison)
    stripped["oracle"].pop("executor_revision")
    stripped["oracle"].pop("executor_source_dirty")
    return stripped


def test_the_retained_comparison_reproduces_from_the_retained_receipt_at_this_tree(comparison) -> None:
    retained = json.loads(RETAINED.read_text(encoding="utf-8"))
    assert retained["ple_s"]["evidence"] == "retained"
    assert _comparable(retained) == _comparable(comparison), (
        "the retained comparison is stale: rerun scripts/compare_ple_scope_alignment.py on the retained receipt")


def test_the_retained_record_manifest_binds_the_files_the_run_and_the_merge_tree() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["schema"] == "de4sdv.retained-ple-scope-alignment-evidence/v1"
    assert manifest["run_id"] == int(RUN_ID) and manifest["executor_revision"] == EXECUTOR
    assert manifest["artifact_name"] == ARTIFACT and manifest["workflow"] == oracle.WORKFLOW
    assert manifest["qualified"] is False and manifest["evidence"] == "retained"
    for name, digest in manifest["files"].items():
        assert oracle.sha256_of(EVIDENCE / name) == digest, name
    assert set(manifest["files"]) == {"receipt.json", "governed-scope-validation.json", "comparison.json"}
    assert manifest["tree_identical_to"]["revision"] == MERGE
    # The tree identity is verified wherever the commits are reachable: always in the CI
    # workflow (full history), and in a shallow executor checkout only when they happen to be.
    reachable = {revision for revision in (EXECUTOR, MERGE)
                 if subprocess.run(["git", "cat-file", "-e", f"{revision}^{{commit}}"], cwd=ROOT,
                                   capture_output=True).returncode == 0}
    if os.environ.get("GITHUB_WORKFLOW") == "CI":
        assert MERGE in reachable, "the CI checkout has the full history; the merge commit must be reachable"
    for revision in reachable:
        tree = subprocess.run(["git", "rev-parse", f"{revision}^{{tree}}"], cwd=ROOT, capture_output=True,
                              text=True, check=True).stdout.strip()
        assert tree == manifest["tree_identical_to"]["tree"], revision
    assert manifest["elements_export"]["retained"] is False
    assert HEX64.fullmatch(manifest["elements_export"]["sha256"])
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert receipt["artifact_sha256"]["scope-alignment-elements.json"] == manifest["elements_export"]["sha256"]


def test_the_record_distinguishes_retained_from_fresh_evidence_and_keeps_the_non_claims(comparison) -> None:
    doc = DOC.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    rendered = oracle.render_markdown(json.loads(RETAINED.read_text(encoding="utf-8")))
    table = rendered.split("\n\n")[1]
    assert table.startswith("| Case | Operational input |") and table in doc, "the doc's table is the retained comparison"
    for required in ("retained", "fresh", RUN_ID, EXECUTOR, "compare_ple_scope_alignment.py", "UG-09", "UG-10", "UG-14",
                     "not-expressible-under-tool", "intentional-scope", "intentional-representation", "defect",
                     "comparison oracle", "not a second", "qualified: false", "No PLEML adoption", "No compliance",
                     "catalogue-correspondence.yaml"):
        assert required in doc, required
    for required in ("retained", "fresh", RUN_ID, EXECUTOR, "2026-11-14", "qualified", "comparison.json"):
        assert required in readme, required
    assert "candidate model increment" not in doc
