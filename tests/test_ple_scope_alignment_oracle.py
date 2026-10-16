"""The PLE-S comparison oracle (UG-09, UG-10, UG-14) over the retained receipt.

The oracle runs the unchanged configurator on the committed configurations and
on generated probes, and derives ``admitted-by-governed-scope`` from the
serialized PLE-S receipt and governed-scope validation of the retained
licensed run. The retained record is verified against the files of its own
revision (the commit that last changed the record directory along first
parents, read from Git history and extracted to a temporary tree), never
against the working tree: a later change to the governed scope, the superset,
the scope validator, the catalogue or the configurator makes the record
historical, not failing (owner decision, 2026-10-16). The oracle's own refusal
of a receipt whose digests differ from the tree it is compared with stays, and
is exercised here on an altered copy of that tree.

These tests assert sets of cases and classifications, never counts; they
fail, never skip, when a retained input or the history is missing; and they
prove that admission moves with the governed scope (a synthetic
reclassification changes the verdict) and that a changed derivation or a
missing correspondence is a defect that exits non-zero.
"""

from __future__ import annotations

import copy
import io
import json
import re
import subprocess
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from scripts import compare_ple_scope_alignment as oracle

ROOT = Path(__file__).resolve().parents[1]
RECORD_DIR = Path("docs/product-line-engineering/ple-s-scope-alignment-evidence")
DOC = ROOT / "docs/product-line-engineering/ple-s-scope-alignment.md"
CORRESPONDENCE = ROOT / oracle.CORRESPONDENCE
EXECUTOR = "7e895252ce2b3b3d5d404d2176cc7872b7f671e3"
MERGE = "606141c80ad83b320a88fd2644f23558cf4fdb8b"
RUN_ID = "38788579272"
ARTIFACT = f"ple-scope-alignment-{EXECUTOR}-{RUN_ID}"
#: What the oracle reads of a tree, extracted from the record's revision.
RECORD_TREE = (
    oracle.CONFIGURATOR, oracle.CATALOGUE, oracle.CONFIGURATIONS, oracle.CORRESPONDENCE.parent, oracle.SCOPE,
    oracle.SHARED_ASSETS, oracle.EVALUATOR, oracle.SCOPE_VALIDATOR, Path("de4sdv/sysml_api/baseline.py"),
    Path("de4sdv/sysml_api/repository.py"), Path("scripts/run_ple_scope_alignment.py"),
    Path("scripts/run_ple_qualification.py"), Path("sysand-lock.toml"), RECORD_DIR,
)
CASES = {
    "standalone-member", "aaos-integrated-member", "both-alternatives", "no-alternative",
    "ug-09-eclipse-score", "ug-09-apollo-qnx-qvm", "ug-09-autosar-acrn",
    "ug-10-openpilot-no-middleware", "ug-10-radar-only", "ug-10-lidar-only", "ug-10-camera-only",
    "ug-10-vehicle-target-aebs-false", "catalogue-only-adaptive-cruise-control", "derived-set-mixed",
    "both-axes-negative",
}
HEX64 = re.compile(r"[0-9a-f]{64}")


def _git(*args: str, cwd: Path = ROOT) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


@pytest.mark.parametrize("path", [RECORD_DIR / "receipt.json", RECORD_DIR / "governed-scope-validation.json",
                                  RECORD_DIR / "comparison.json", RECORD_DIR / "manifest.json",
                                  RECORD_DIR / "README.md", DOC.relative_to(ROOT), oracle.CORRESPONDENCE,
                                  oracle.CATALOGUE, oracle.CONFIGURATOR, oracle.SHARED_ASSETS])
def test_every_retained_and_operational_input_is_present(path: Path) -> None:
    assert (ROOT / path).is_file(), f"missing input: {path}"


def _record_revision() -> str:
    """The commit that last changed the retained record: the record is verified at that revision."""
    assert _git("rev-parse", "--is-shallow-repository") == "false", (
        "the retained record is verified from history; this checkout is shallow (fetch-depth 0 is needed)")
    # Along first parents: on CI's merge ref of a pull request that changes the record, this is the merge commit
    # itself, so the record is verified in the tree main gets from the squash merge. Without it, a branch brought
    # up to date with a merge commit resolves to its own older record commit and hides a bound input that main
    # changed in the meantime.
    revision = _git("log", "-1", "--first-parent", "--format=%H", "--", RECORD_DIR.as_posix())
    assert re.fullmatch(r"[0-9a-f]{40}", revision), "the retained record has no commit in this history"
    return revision


@pytest.fixture(scope="module")
def record(tmp_path_factory):
    """The record's revision, its tree extracted from Git, and a work directory for probes."""
    revision = _record_revision()
    root = tmp_path_factory.mktemp("record-tree")
    archive = subprocess.run(["git", "archive", revision, "--", *(path.as_posix() for path in RECORD_TREE)],
                             cwd=ROOT, capture_output=True, check=True).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(root, filter="data")
    for name in ("receipt.json", "governed-scope-validation.json", "comparison.json", "manifest.json"):
        assert (root / RECORD_DIR / name).is_file(), f"{name} is not part of the record at {revision}"
    for extracted in sorted((root / RECORD_DIR).iterdir()):
        current = ROOT / RECORD_DIR / extracted.name
        assert current.is_file() and current.read_bytes() == extracted.read_bytes(), (
            f"{extracted.name} in this checkout differs from the record at {revision}: commit it or restore it")
    return SimpleNamespace(revision=revision, root=root, evidence=root / RECORD_DIR,
                           work=tmp_path_factory.mktemp("oracle-work"))


@pytest.fixture(scope="module")
def evidence(record):
    return oracle.load_evidence(record.evidence / "receipt.json", record.evidence / "governed-scope-validation.json",
                                evidence="retained", run_id=RUN_ID, artifact=ARTIFACT, root=record.root)


def _run(record, evidence, **kwargs):
    return oracle.run_oracle(evidence, root=record.root, revision=record.revision, work_dir=record.work, **kwargs)


@pytest.fixture(scope="module")
def comparison(record, evidence):
    return _run(record, evidence)


def _rows(comparison) -> dict[str, dict]:
    return {row["case"]: row for row in comparison["rows"]}


def _blocking_governed(row) -> set[str]:
    """Governed elements that block admission: inadmissible classifications of selected items."""
    names = set()
    for item in row["admitted_by_governed_scope"]["selections"]:
        if not item["selected"] or item["unclassified"]:
            continue
        kinds = {kind["kind"] for kind in item["classifications"]}
        if kinds & oracle.ADMISSIBLE:
            continue
        names |= {kind["governed"] for kind in item["classifications"] if kind["kind"] in oracle.INADMISSIBLE}
    return names


def _asset(row, name) -> dict:
    [asset] = [item for item in row["admitted_by_governed_scope"]["common_assets"] if item["asset"] == name]
    return asset


# -- the table -------------------------------------------------------------------------


def test_the_record_is_verified_at_its_own_revision(record) -> None:
    assert _git("merge-base", "--is-ancestor", record.revision, "HEAD") == ""
    assert record.root != ROOT and not record.root.is_relative_to(ROOT)
    assert (record.root / oracle.CONFIGURATOR).is_file() and (record.root / oracle.CATALOGUE).is_file()


def test_every_case_of_the_design_is_classified_and_nothing_is_a_defect(comparison) -> None:
    rows = _rows(comparison)
    assert set(rows) == CASES
    assert {row["class"] for row in rows.values()} <= set(oracle.CLASSES)
    assert comparison["summary"]["defects"] == [] and comparison["summary"]["unclassified"] == []
    assert comparison["summary"]["exit_code"] == 0
    assert {name for name, cases in comparison["summary"]["classes"].items() if cases} == {
        "equal", "intentional-scope", "intentional-representation", "not-expressible-under-tool", "both-reject"}
    for row in rows.values():
        assert row["class_reason"]
        assert row["configuration_valid_under_current_tool"]["exit_code"] in (0, 1)
        assert row["ple_s"]["summary"]
    assert comparison["qualified"] is False and comparison["adoption_authorized"] is False
    assert comparison["authority_activation_authorized"] is False
    assert comparison["oracle"]["tree_source"] == "extracted tree, revision as declared"


def test_the_two_fields_are_reported_separately(comparison) -> None:
    rows = _rows(comparison)
    valid = {case for case, row in rows.items() if row["configuration_valid_under_current_tool"]["valid"]}
    admitted = {case for case, row in rows.items() if row["admitted_by_governed_scope"]["admitted"]}
    assert valid == CASES - {"both-alternatives", "no-alternative", "both-axes-negative"}
    assert admitted == {"standalone-member", "aaos-integrated-member"}
    assert {case for case, row in rows.items() if row["class"] == "intentional-scope"} == valid - admitted
    assert {case for case, row in rows.items() if row["class"] == "both-reject"} == {"no-alternative", "both-axes-negative"}
    assert {case for case, row in rows.items() if row["class"] == "not-expressible-under-tool"} == {"both-alternatives"}


# -- UG-09: tool validity stays distinct from governed admission ------------------------


def test_ug09_the_configurator_accepts_reference_only_alternatives_the_scope_does_not_admit(comparison, evidence) -> None:
    rows = _rows(comparison)
    reference_only = evidence["governed"]["reference_only"]
    expected = {"ug-09-eclipse-score": {"eclipseSCORE"},
                "ug-09-apollo-qnx-qvm": {"apollo", "eclipseSCORE", "qnxQVM", "sensingVariability"},
                "ug-09-autosar-acrn": {"autosarAdaptive", "acrn"}}
    for case, names in expected.items():
        row = rows[case]
        assert row["configuration_valid_under_current_tool"]["valid"] is True
        assert row["admitted_by_governed_scope"]["admitted"] is False
        assert row["class"] == "intentional-scope"
        assert _blocking_governed(row) == names
        assert row["ple_s"]["configuration"] is None
        assert row["comparison"]["ple_s_expected"] is None and row["comparison"]["tool_selected"]
    # Every reference-only element with a catalogue node is exercised by some row (Openpilot by the UG-10
    # row), and the classification is read from the serialized governed scope, element id included.
    exercised = set().union(*(_blocking_governed(row) for row in rows.values()))
    assert exercised >= set(reference_only) - {"automotiveGradeLinux"}
    score = rows["ug-09-eclipse-score"]
    [item] = [r for r in score["admitted_by_governed_scope"]["selections"] if r["node"] == "F-PLATFORM-MIDDLEWARE-ECLIPSE-SCORE"]
    [kind] = item["classifications"]
    assert kind["kind"] == "reference-only" and kind["governed_id"] == reference_only["eclipseSCORE"]
    assert kind["source"].startswith("governed-scope-validation:reference_only[eclipseSCORE]")
    assert item["catalogue_role"] == "feature"
    assert rows["ug-09-autosar-acrn"]["comparison"]["tool_selected"]["applicationMiddlewareAdapter"] == "autowareToAUTOSAR"


# -- UG-10: common content mapped as a distinguishing feature ---------------------------


def test_ug10_common_content_mapped_as_features_is_rejected_within_the_governed_portfolio(comparison, evidence) -> None:
    rows = _rows(comparison)
    deferred = evidence["governed"]["deferred"]
    openpilot = rows["ug-10-openpilot-no-middleware"]
    assert openpilot["configuration_valid_under_current_tool"]["valid"] is True
    assert openpilot["class"] == "intentional-scope"
    assert _blocking_governed(openpilot) == {"openpilot"}
    assert openpilot["admitted_by_governed_scope"]["incomplete_common_assets"] == ["autowareApplication"]
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
    assert radar["admitted_by_governed_scope"]["incomplete_common_assets"] == ["currentSensingBaseline"]
    [sensor] = [r for r in radar["admitted_by_governed_scope"]["selections"] if r["node"] == "F-SENSING-PERCEPTION-RADAR"]
    assert sensor["catalogue_role"] == "feature"
    assert {(k["kind"], k["governed_id"]) for k in sensor["classifications"]} == {("deferred", deferred["sensingVariability"])}


def test_ug10_a_dropped_baseline_sensor_is_never_admitted(comparison) -> None:
    """V&V finding R1: a common asset with several selectable nodes needs all of them."""
    rows = _rows(comparison)
    # The motion sensors are implied by the catalogue (a mandatory leaf), so every selection that drops
    # a perception sensor of the baseline is partial, never "not represented".
    partial = {case for case, row in rows.items()
               if _asset(row, "currentSensingBaseline")["status"].startswith("partially represented")}
    assert partial == {"ug-10-lidar-only", "ug-10-camera-only", "ug-10-radar-only", "ug-09-apollo-qnx-qvm",
                       "both-axes-negative"}
    assert {case for case, row in rows.items() if _asset(row, "currentSensingBaseline")["complete"] is True} == (
        CASES - partial)
    for case, missing in (("ug-10-lidar-only", ["F-SENSING-PERCEPTION-CAMERA"]),
                          ("ug-10-camera-only", ["F-SENSING-PERCEPTION-LIDAR"])):
        row = rows[case]
        assert row["configuration_valid_under_current_tool"]["valid"] is True
        assert row["admitted_by_governed_scope"]["admitted"] is False
        assert row["class"] == "intentional-scope"
        assert _blocking_governed(row) == set(), "no inadmissible content: the baseline itself is incomplete"
        baseline = _asset(row, "currentSensingBaseline")
        assert baseline["missing"] == missing and baseline["implied_by"] == ["C-SENSING-MOTION"]
        assert baseline["complete"] is False
        assert any("currentSensingBaseline" in reason for reason in row["admitted_by_governed_scope"]["verdict_reasons"])
    for case in ("standalone-member", "aaos-integrated-member"):
        baseline = _asset(rows[case], "currentSensingBaseline")
        assert baseline["complete"] is True and baseline["implied_by"] == ["C-SENSING-MOTION"]
        assert set(baseline["represented_by"]) == {"F-SENSING-PERCEPTION-CAMERA", "F-SENSING-PERCEPTION-LIDAR"}


def test_ug10_the_common_capability_switched_off_is_rejected_although_the_tool_accepts_it(comparison) -> None:
    """V&V R5: the configurator does not enforce mandatory leaves; the oracle does not follow it."""
    row = _rows(comparison)["ug-10-vehicle-target-aebs-false"]
    assert row["configuration_valid_under_current_tool"]["valid"] is True
    assert row["admitted_by_governed_scope"]["admitted"] is False
    assert row["class"] == "intentional-scope"
    capability = _asset(row, "vehicleTargetAEBS")
    assert capability["dropped"] == ["C-CAPABILITY-AEBS-VEHICLE-TARGET"] and capability["complete"] is False
    assert row["admitted_by_governed_scope"]["incomplete_common_assets"] == ["vehicleTargetAEBS"]


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
        statuses = {item["asset"]: item["complete"] for item in rows[case]["admitted_by_governed_scope"]["common_assets"]}
        assert statuses["protectedEmergencyCommandPathIndependence"] is None
        assert statuses["vehicleTargetAEBS"] is True


# -- the two undocumented intentional-scope reasons (V&V finding R4) ------------------


def test_a_catalogue_only_feature_candidate_is_not_in_the_governed_scope(comparison) -> None:
    row = _rows(comparison)["catalogue-only-adaptive-cruise-control"]
    assert row["configuration_valid_under_current_tool"]["valid"] is True
    assert row["admitted_by_governed_scope"]["admitted"] is False
    assert row["class"] == "intentional-scope"
    [item] = [r for r in row["admitted_by_governed_scope"]["selections"] if r["node"] == "F-CAPABILITY-ADAPTIVE-CRUISE-CONTROL"]
    assert item["selected"] is True
    assert {(k["kind"], k["governed"]) for k in item["classifications"]} == {("not-in-governed-scope", None)}
    # V&V finding R6 of PR #379: the reason names the item the governed scope has no element for.
    assert row["ple_s"]["reason"] == ("no PLE-S configuration: the admitted tree has no feature for "
                                      "Capabilities.AdaptiveCruiseControl (not-in-governed-scope)")
    assert {case for case, r in _rows(comparison).items()
            if any(k["kind"] == "not-in-governed-scope" for s in r["admitted_by_governed_scope"]["selections"]
                   if s["selected"] for k in s["classifications"])} == {"catalogue-only-adaptive-cruise-control"}


def test_a_mixed_derived_set_realizes_two_alternatives_and_is_tool_valid(comparison) -> None:
    rows = _rows(comparison)
    mixed = rows["derived-set-mixed"]
    assert mixed["configuration_valid_under_current_tool"]["valid"] is True
    assert mixed["comparison"]["tool_selected"]["applicationMiddlewareAdapter"] == "autowareToAAOSSDV"
    assert mixed["admitted_by_governed_scope"]["admitted"] is False and mixed["class"] == "intentional-scope"
    assert set(mixed["admitted_by_governed_scope"]["alternatives_realized"]) == {"aaosIntegrated", "standalone"}
    assert _blocking_governed(mixed) == set()
    assert {case for case, row in rows.items()
            if len(row["admitted_by_governed_scope"]["alternatives_realized"]) > 1} == {
        "both-alternatives", "derived-set-mixed", "both-axes-negative"}


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
    assert {case for case, row in rows.items() if row["class"] == "equal"} == {"standalone-member"}


def test_ug14_the_known_representation_difference_manifests_only_where_the_runtime_is_unrepresented(comparison) -> None:
    rows = _rows(comparison)
    standalone = {d["common_asset"]: d for d in rows["standalone-member"]["comparison"]["representation_differences"]}
    integrated = {d["common_asset"]: d for d in rows["aaos-integrated-member"]["comparison"]["representation_differences"]}
    assert set(standalone) == set(integrated) == {"linuxROS2AutowareRuntime"}
    assert standalone["linuxROS2AutowareRuntime"]["manifests"] is False
    assert standalone["linuxROS2AutowareRuntime"]["represented_by"] == ["F-PLATFORM-OS-LINUX"]
    difference = integrated["linuxROS2AutowareRuntime"]
    assert difference["manifests"] is True and difference["represented_by"] == []
    assert difference["implied_alternative_binds_variation"] is True and difference["variation"] == "osPlatform"
    [recorded] = comparison["representation_differences"]
    assert recorded["classification"] == "intentional-representation" and recorded["confirmed_in_graph"] is True
    assert "INC-MW-011" in recorded["disposition"] and "INC-MW-011" in rows["aaos-integrated-member"]["class_reason"]
    assert rows["aaos-integrated-member"]["admitted_by_governed_scope"]["exempted_common_assets"] == ["linuxROS2AutowareRuntime"]
    # The difference is owned elsewhere; the oracle neither widens PLE-S nor calls it a model increment candidate.
    assert "candidate" not in rows["aaos-integrated-member"]["class_reason"]


def test_the_representation_exemption_is_scoped_to_the_alternative_that_binds_the_variation(record, evidence) -> None:
    """V&V finding R3: the D6 exemption follows the binding, not the asset name."""
    receipt = copy.deepcopy(evidence["receipt"])
    receipt["alignment"]["bindings"] = [b for b in receipt["alignment"]["bindings"]
                                        if b["binding"] != "linuxOSPlatformBoundToStandalone"]
    synthetic = {"receipt": receipt, "governed": evidence["governed"], "identity": evidence["identity"]}
    cases = (
        oracle.Case("standalone-without-os", "synthetic", "standalone derived set with the OS key removed",
                    probe="overrides", name="StandaloneWithoutOSProbe",
                    overrides=(("PlatformStack.OS", oracle.REMOVE),)),
        oracle.Case("aaos-integrated-member", "member", "the AAOS-integrated member",
                    configuration="middleware-autoware-aaos-sdv-reference.yaml",
                    ple_s="aaosIntegratedAutowareAEBSReferenceMemberConfiguration"),
    )
    rows = _rows(_run(record, synthetic, cases=cases))
    without_os = rows["standalone-without-os"]
    assert "PlatformStack.OS" not in without_os["operational_input"]["selections"]
    assert without_os["admitted_by_governed_scope"]["implied_alternative"] == "standalone"
    assert without_os["admitted_by_governed_scope"]["admitted"] is False
    assert without_os["admitted_by_governed_scope"]["exempted_common_assets"] == []
    assert any("linuxROS2AutowareRuntime" in reason for reason in without_os["admitted_by_governed_scope"]["verdict_reasons"])
    [difference] = without_os["comparison"]["representation_differences"]
    assert difference["implied_alternative_binds_variation"] is False and difference["manifests"] is False
    integrated = rows["aaos-integrated-member"]
    assert integrated["admitted_by_governed_scope"]["admitted"] is True
    assert integrated["admitted_by_governed_scope"]["exempted_common_assets"] == ["linuxROS2AutowareRuntime"]
    assert integrated["class"] == "intentional-representation"


def test_ug14_every_row_carries_the_projection_digests_and_the_receipt_identity(comparison, record) -> None:
    catalogue = oracle.sha256_of(record.root / oracle.CATALOGUE)
    shared = oracle.sha256_of(record.root / oracle.SHARED_ASSETS)
    identity = comparison["ple_s"]
    assert identity["artifact"] == ARTIFACT and identity["evidence"] == "retained"
    assert identity["pleml_pin"] == "5f8ab8560219dc24d8ec7ec90d6f0a145896ef8e"
    assert HEX64.fullmatch(identity["model_sha256"]) and HEX64.fullmatch(identity["library_sha256"])
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
        assert receipt["receipt_sha256"] == identity["receipt_sha256"]
        assert (receipt["configuration_element_id"] is None) == (row["ple_s"]["configuration"] is None)
    baselines = {row["provenance"]["shared_assets_source_baseline"] for row in comparison["rows"]}
    assert len(baselines) == 1, "the computed baseline equals the configurator's header"


def test_the_receipt_identity_is_bound_to_the_record_tree_content(comparison, record) -> None:
    identity = comparison["ple_s"]
    assert identity["model_sha256"] == oracle.sha256_of(record.root / oracle.MODEL)
    assert identity["evaluator_sha256"] == oracle.sha256_of(record.root / oracle.EVALUATOR)
    assert identity["governed_scope_sha256"] == oracle.sha256_of(record.root / oracle.SCOPE)
    assert identity["shared_assets_sha256"] == oracle.sha256_of(record.root / oracle.SHARED_ASSETS)
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
    assert row["class"] == "both-reject" and "independent reasons" in row["class_reason"]


def test_both_axes_negative_shows_the_two_fields_are_independent(comparison) -> None:
    row = _rows(comparison)["both-axes-negative"]
    tool = row["configuration_valid_under_current_tool"]
    assert tool["valid"] is False and tool["violated_constraints"] == ["C001"]
    assert row["admitted_by_governed_scope"]["admitted"] is False
    assert _blocking_governed(row) == {"eclipseSCORE"}
    assert set(row["admitted_by_governed_scope"]["alternatives_realized"]) == {"aaosIntegrated", "standalone"}
    assert row["ple_s"]["configuration"] is None
    assert row["class"] == "both-reject" and "independent reasons" in row["class_reason"]


def test_probes_are_generated_outside_the_repository_and_never_committed(comparison, record) -> None:
    tracked = subprocess.run(["git", "ls-files", "--", oracle.CONFIGURATIONS.as_posix()], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout.split()
    generated = {row["operational_input"]["name"] for row in comparison["rows"]
                 if row["operational_input"]["kind"] == "generated"}
    assert generated == {"BothIntegrationModesProbe", "NoIntegrationModeProbe", "AUTOSARAdaptiveACRNProbe",
                         "OpenpilotNoMiddlewareProbe", "RadarOnlySensingProbe", "LidarOnlySensingProbe",
                         "CameraOnlySensingProbe", "VehicleTargetAEBSOffProbe", "AdaptiveCruiseControlProbe",
                         "MixedDerivedSetProbe"}
    for path in tracked:
        assert "Probe" not in path and "probe" not in Path(path).stem
    status = subprocess.run(["git", "status", "--porcelain", "--", oracle.CONFIGURATIONS.as_posix()], cwd=ROOT,
                            capture_output=True, text=True, check=True).stdout
    assert status == ""
    assert not any(record.root.glob("**/*Probe*")), "probes never land in the compared tree either"
    assert list(record.work.iterdir()) == [], "the oracle's temporary directory is removed after the run"


# -- admission follows the governed scope, not a list ----------------------------------


def _synthetic(evidence, *, receipt=None, governed=None):
    return {"receipt": receipt or evidence["receipt"], "governed": governed or evidence["governed"],
            "identity": evidence["identity"]}


def test_a_reclassified_governed_element_changes_the_verdict_without_touching_the_oracle(record, evidence) -> None:
    governed = copy.deepcopy(evidence["governed"])
    governed["deferred"]["eclipseSCORE"] = governed["reference_only"].pop("eclipseSCORE")
    rows = _rows(_run(record, _synthetic(evidence, governed=governed)))
    [item] = [r for r in rows["ug-09-eclipse-score"]["admitted_by_governed_scope"]["selections"]
              if r["node"] == "F-PLATFORM-MIDDLEWARE-ECLIPSE-SCORE"]
    assert {k["kind"] for k in item["classifications"]} == {"deferred"}
    assert rows["ug-09-eclipse-score"]["class"] == "intentional-scope"


def test_a_changed_ple_s_derivation_is_a_defect_that_exits_non_zero(record, evidence) -> None:
    receipt = copy.deepcopy(evidence["receipt"])
    [configuration] = [c for c in receipt["alignment"]["configurations"]
                       if c["configuration"] == "standaloneAutowareAEBSReferenceMemberConfiguration"]
    for item in configuration["derived_asset_variants"]:
        if item["variation"] == "osPlatform":
            item["variant"] = "android"
    comparison = _run(record, _synthetic(evidence, receipt=receipt))
    rows = _rows(comparison)
    assert rows["standalone-member"]["class"] == "defect"
    assert rows["standalone-member"]["comparison"]["differing"] == ["osPlatform: tool linux, PLE-S android"]
    assert comparison["summary"]["defects"] == ["standalone-member"]
    assert comparison["summary"]["exit_code"] == 1


def test_a_selection_without_correspondence_is_unclassified_and_exits_non_zero(record, evidence, tmp_path) -> None:
    data = yaml.safe_load((record.root / oracle.CORRESPONDENCE).read_text(encoding="utf-8"))
    data["correspondence"] = [e for e in data["correspondence"] if e["node"] != "F-PLATFORM-MIDDLEWARE-ECLIPSE-SCORE"]
    path = tmp_path / "catalogue-correspondence.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    comparison = _run(record, evidence, correspondence_path=path)
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
def test_the_correspondence_is_validated_against_both_sides(record, evidence, tmp_path, mutation, message) -> None:
    data = yaml.safe_load((record.root / oracle.CORRESPONDENCE).read_text(encoding="utf-8"))
    mutation(data["correspondence"])
    path = tmp_path / "catalogue-correspondence.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    with pytest.raises(oracle.OracleRefusal, match=message):
        _run(record, evidence, correspondence_path=path)


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
def test_the_oracle_refuses_a_promoted_dirty_or_stale_receipt(record, tmp_path, mutation, message) -> None:
    receipt = json.loads((record.evidence / "receipt.json").read_text(encoding="utf-8"))
    for key, value in mutation.items():
        if key == "executor_inputs":
            receipt[key].update(value)
        else:
            receipt[key] = value
    path = _write(tmp_path, "receipt.json", receipt)
    with pytest.raises(oracle.OracleRefusal, match=re.escape(message)):
        oracle.load_evidence(path, record.evidence / "governed-scope-validation.json", evidence="retained",
                             run_id=RUN_ID, artifact=ARTIFACT, root=record.root)


def test_the_oracle_refuses_a_governed_scope_the_receipt_did_not_record(record, tmp_path) -> None:
    governed = json.loads((record.evidence / "governed-scope-validation.json").read_text(encoding="utf-8"))
    governed["reference_only"]["apollo"] = "0" * 8
    path = _write(tmp_path, "governed-scope-validation.json", governed)
    with pytest.raises(oracle.OracleRefusal, match="not the one the receipt recorded"):
        oracle.load_evidence(record.evidence / "receipt.json", path, evidence="retained", run_id=RUN_ID,
                             artifact=ARTIFACT, root=record.root)


def test_the_oracle_refuses_a_tree_whose_bound_inputs_moved_while_the_record_stays_verified(record, tmp_path) -> None:
    """The fresh path refuses a receipt that does not describe the tree; the record is verified at its revision."""
    altered = tmp_path / "altered-tree"
    altered.mkdir()
    for path in (oracle.SCOPE, oracle.SHARED_ASSETS, oracle.MODEL, oracle.EVALUATOR, oracle.SCOPE_VALIDATOR):
        target = altered / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((record.root / path).read_bytes())
    with (altered / oracle.SCOPE).open("ab") as handle:
        handle.write(b"\n")
    with pytest.raises(oracle.OracleRefusal, match=re.escape(oracle.SCOPE.as_posix())):
        oracle.load_evidence(record.evidence / "receipt.json", record.evidence / "governed-scope-validation.json",
                             evidence="retained", run_id=RUN_ID, artifact=ARTIFACT, root=altered)
    accepted = oracle.load_evidence(record.evidence / "receipt.json", record.evidence / "governed-scope-validation.json",
                                    evidence="retained", run_id=RUN_ID, artifact=ARTIFACT, root=record.root)
    assert accepted["identity"]["executor_revision"] == EXECUTOR


def test_the_oracle_refuses_a_mismatched_artifact_or_run_and_tells_fresh_from_retained(record) -> None:
    receipt, governed = record.evidence / "receipt.json", record.evidence / "governed-scope-validation.json"
    with pytest.raises(oracle.OracleRefusal, match="artifact name"):
        oracle.load_evidence(receipt, governed, evidence="retained", run_id="1", artifact=ARTIFACT, root=record.root)
    with pytest.raises(oracle.OracleRefusal, match="artifact name"):
        oracle.load_evidence(receipt, governed, evidence="retained", run_id=RUN_ID, artifact="other", root=record.root)
    if _git("rev-parse", "HEAD") == EXECUTOR:
        # On a checkout of the retained executor commit the retained receipt is the fresh receipt of this head.
        fresh = oracle.load_evidence(receipt, governed, evidence="fresh", run_id=RUN_ID, artifact=ARTIFACT, root=ROOT)
        assert fresh["identity"]["evidence"] == "fresh" and fresh["identity"]["executor_revision"] == EXECUTOR
    else:
        with pytest.raises(oracle.OracleRefusal, match="exact head"):
            oracle.load_evidence(receipt, governed, evidence="fresh", run_id=RUN_ID, artifact=ARTIFACT, root=ROOT)


# -- the command line and the retained record ----------------------------------------


def _cli(record, out: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-B", str(ROOT / "scripts/compare_ple_scope_alignment.py"),
                           "--receipt", str(record.evidence / "receipt.json"),
                           "--governed-scope", str(record.evidence / "governed-scope-validation.json"),
                           "--evidence", "retained", "--run-id", RUN_ID, "--artifact", ARTIFACT,
                           "--root", str(record.root), "--revision", record.revision, "--out", str(out), *extra],
                          cwd=ROOT, capture_output=True, text=True)


def test_the_command_line_writes_the_comparison_and_refuses_an_output_inside_the_repository(record, tmp_path) -> None:
    result = _cli(record, tmp_path / "out")
    assert result.returncode == 0, result.stderr
    printed = json.loads(result.stdout)
    assert printed["defects"] == [] and printed["qualified"] is False and printed["evidence"] == "retained"
    assert printed["revision"] == record.revision and printed["tree"] == "extracted tree, revision as declared"
    written = json.loads((tmp_path / "out/comparison.json").read_text(encoding="utf-8"))
    assert written["schema"] == oracle.SCHEMA and {row["case"] for row in written["rows"]} == CASES
    assert (tmp_path / "out/comparison.md").read_text(encoding="utf-8") == oracle.render_markdown(written)
    assert [p.name for p in tmp_path.iterdir()] == ["out"], "probes are gone; only the output remains beside it"
    again = _cli(record, tmp_path / "out")
    assert again.returncode == 2 and "existing output directory" in again.stderr
    inside = _cli(record, ROOT / "docs/ple-s-oracle-must-not-write-here")
    assert inside.returncode == 2 and "outside the repository" in inside.stderr
    assert not (ROOT / "docs/ple-s-oracle-must-not-write-here").exists()
    in_tree = _cli(record, record.root / "out")
    assert in_tree.returncode == 2 and "outside the repository" in in_tree.stderr


def _comparable(comparison: dict) -> dict:
    """The comparison without the oracle's own identity: the retained record is content-addressed."""
    stripped = copy.deepcopy(comparison)
    for key in ("executor_revision", "executor_source_dirty", "tree_source", "script", "script_sha256"):
        stripped["oracle"].pop(key)
    return stripped


def test_the_retained_comparison_reproduces_from_the_retained_receipt_at_its_revision(comparison, record) -> None:
    retained = json.loads((record.evidence / "comparison.json").read_text(encoding="utf-8"))
    assert retained["ple_s"]["evidence"] == "retained"
    assert _comparable(retained) == _comparable(comparison), (
        "the retained comparison is stale at its own revision: rerun scripts/compare_ple_scope_alignment.py "
        "on the retained receipt and retain the result")


def test_the_retained_record_manifest_binds_the_files_the_run_and_the_merge_tree(record) -> None:
    manifest = json.loads((record.evidence / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == "de4sdv.retained-ple-scope-alignment-evidence/v1"
    assert manifest["run_id"] == int(RUN_ID) and manifest["executor_revision"] == EXECUTOR
    assert manifest["artifact_name"] == ARTIFACT and manifest["workflow"] == oracle.WORKFLOW
    assert manifest["qualified"] is False and manifest["evidence"] == "retained"
    for name, digest in manifest["files"].items():
        assert oracle.sha256_of(record.evidence / name) == digest, name
    assert set(manifest["files"]) == {"receipt.json", "governed-scope-validation.json", "comparison.json"}
    binding = manifest["binding"]
    assert binding["rule"].startswith("verified against the files of the commit that last changed this directory")
    assert "never against the working tree" in binding["rule"] and "licensed run" in binding["fresh_evidence"]
    assert "catalogue" in binding["historical_once"] and "configurator" in binding["historical_once"]
    assert manifest["tree_identical_to"]["revision"] == MERGE
    # The merge commit is on main and reachable in every full-history checkout; the pull-request head
    # that produced the receipt is only reachable where its ref was fetched.
    assert subprocess.run(["git", "cat-file", "-e", f"{MERGE}^{{commit}}"], cwd=ROOT, capture_output=True).returncode == 0
    reachable = [revision for revision in (MERGE, EXECUTOR) if subprocess.run(
        ["git", "cat-file", "-e", f"{revision}^{{commit}}"], cwd=ROOT, capture_output=True).returncode == 0]
    for revision in reachable:
        assert _git("rev-parse", f"{revision}^{{tree}}") == manifest["tree_identical_to"]["tree"], revision
    assert manifest["elements_export"]["retained"] is False
    assert HEX64.fullmatch(manifest["elements_export"]["sha256"])
    receipt = json.loads((record.evidence / "receipt.json").read_text(encoding="utf-8"))
    assert receipt["artifact_sha256"]["scope-alignment-elements.json"] == manifest["elements_export"]["sha256"]


def test_the_record_distinguishes_retained_from_fresh_evidence_and_keeps_the_non_claims(record) -> None:
    doc = DOC.read_text(encoding="utf-8")
    readme = (ROOT / RECORD_DIR / "README.md").read_text(encoding="utf-8")
    rendered = oracle.render_markdown(json.loads((record.evidence / "comparison.json").read_text(encoding="utf-8")))
    table = rendered.split("\n\n")[1]
    assert table.startswith("| Case | Operational input |") and table in doc, "the doc's table is the retained comparison"
    for required in ("retained", "fresh", RUN_ID, EXECUTOR, "compare_ple_scope_alignment.py", "UG-09", "UG-10", "UG-14",
                     "not-expressible-under-tool", "intentional-scope", "intentional-representation", "both-reject",
                     "defect", "comparison oracle", "not a second", "qualified: false", "No PLEML adoption",
                     "No compliance", "catalogue-correspondence.yaml", "bound to", "historical", "licensed run",
                     "not-in-governed-scope", "more than one admitted alternative", "not a superset realization"):
        assert required in doc, required
    manifest = json.loads((record.evidence / "manifest.json").read_text(encoding="utf-8"))
    expires = manifest["artifact_expires_at"][:10]
    for required in ("retained", "fresh", RUN_ID, EXECUTOR, expires, "qualified", "comparison.json", "bound to",
                     "historical", "licensed run", "PyYAML", "executor_revision", "EXECUTOR", "MERGE", "RUN_ID",
                     "--root", "--revision"):
        assert required in readme, required
    assert "candidate model increment" not in doc
