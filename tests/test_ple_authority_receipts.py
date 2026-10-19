"""The committed receipts of the fenced PLEML feature models (ADR 0022, step S3).

The receipts and their compressed elements are written by the entry point of
the S2 evaluator from the bundle of a licensed authority run; the owner said
yes to committing them on 2026-10-19. These checks read the committed files
only: the layout, the digests of the elements and of every source the
receipts bind, the recorded serialization, and the reviewed verdicts. The
offline replay re-runs the evaluator on the committed elements; it runs where
the evaluator is on the revision. Nothing here is serializer output, a
licensed run or a qualification.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from scripts import run_ple_authority as runner

ROOT = Path(__file__).resolve().parents[1]
RECEIPTS = ROOT / runner.RECEIPTS_DIR
ELEMENTS = f"{runner.RECEIPTS_NAME}.elements.json.xz"
#: One receipt per feature model, named by the feature model's file stem.
FEATURE_MODELS = {Path(path).stem + ".receipt.json": path for path in runner.FEATURE_MODELS}
DERIVATION = "D-ASSET-APPLICATION-MIDDLEWARE-ADAPTER"
#: The reviewed outcome, per configuration: valid, admitted alternative (None: not admitted),
#: derived adapter and violated constraints.
VERDICTS = {
    "sdv_product_line.receipt.json": {
        "aebsAutowareLinuxLidarCamera": (True, "standalone", "none", []),
        "middlewareAutowareAAOSSDVReference": (True, "aaosIntegrated", "autowareToAAOSSDV", []),
        "exampleLinuxSCOREVariant": (True, None, "autowareToSCORE", []),
        "apolloQNXQVMVariant": (True, None, "apolloToSCORE", []),
        "invalidSCOREAndroidVariant": (False, None, None, ["C001"]),
    },
    "engineering_execution_environments.receipt.json": {
        "incAEBS009AJetsonExecutionEnvironment": (True, None, None, []),
        "appleSiliconMacOSCandidate": (True, None, None, []),
    },
    "vehicle_execution_environments.receipt.json": {
        "nxpZephyrVehicleTargetCandidate": (True, None, None, []),
    },
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _receipts() -> dict[str, dict]:
    return {path.name: json.loads(path.read_text(encoding="utf-8")) for path in sorted(RECEIPTS.glob("*.receipt.json"))}


def test_the_receipts_directory_holds_one_receipt_per_feature_model_and_the_elements() -> None:
    assert sorted(path.name for path in RECEIPTS.iterdir()) == sorted([*FEATURE_MODELS, ELEMENTS])
    for name, receipt in _receipts().items():
        assert receipt["schema"] == "de4sdv.pleml-configuration-receipt/v1"
        assert receipt["qualified"] is False and receipt["native_expression_executed"] is False
        assert receipt["elements"]["path"] == ELEMENTS
        assert receipt["elements"]["sha256"] == _sha256(RECEIPTS / ELEMENTS), name
        # Each receipt covers its own feature model and the configurations of its tree.
        assert FEATURE_MODELS[name] in receipt["model_sources"], name
        assert set(receipt["model_sources"]) <= set(runner.AUTHORITY_SOURCES) | set(runner.FIXTURES)


def test_the_receipts_together_cover_every_pleml_file_once() -> None:
    covered = [source for receipt in _receipts().values() for source in receipt["model_sources"]]
    assert sorted(covered) == sorted([*runner.AUTHORITY_SOURCES, *runner.FIXTURES])


def test_the_receipts_bind_the_documents_of_this_tree_by_digest() -> None:
    """A receipt names every document of its bundle by digest; each is this tree's file.

    The library is the installed fenced package, which the public CI syncs
    before the suite; elsewhere it may be absent.
    """
    for name, receipt in _receipts().items():
        paths = [source["path"] for source in receipt["sources"]]
        assert sorted(paths) == sorted([runner.LIBRARY["label"], *runner.AUTHORITY_SOURCES, *runner.FIXTURES,
                                        *runner.REFERENCED_SOURCES]), name
        for source in receipt["sources"]:
            path = ROOT / source["path"]
            if source["path"] == runner.LIBRARY["label"]:
                assert source["sha256"] == runner.LIBRARY["sha256"], name
                if not path.is_file():
                    continue
            assert _sha256(path) == source["sha256"], f"{source['path']} changed after the receipt {name}"


def test_the_receipts_record_one_licensed_serialization() -> None:
    serializers = [receipt["serializer"] for receipt in _receipts().values()]
    assert all(serializer == serializers[0] for serializer in serializers)
    [serializer] = serializers[:1]
    assert {key: serializer[key] for key in ("name", "version", "options")} == {
        "name": "syside", "version": runner.SERIALIZER_VERSION, "options": "production export"}
    assert re.fullmatch(r"[0-9a-f]{40}", serializer["executor_revision"])
    assert serializer["bundle_git_commit"] == serializer["executor_revision"]


def test_the_receipts_hold_the_reviewed_verdicts() -> None:
    receipts = _receipts()
    assert set(receipts) == set(VERDICTS)
    for name, expected in VERDICTS.items():
        [model] = receipts[name]["evaluation"]["feature_models"]
        assert model["integrity_errors"] == [], name
        found = {}
        for configuration in model["configurations"]:
            admission = configuration["admission"]
            adapters = [item["variant"] for item in configuration["derived_variants"]
                        if item.get("derivation") == DERIVATION]
            constraints = sorted(reason["constraint"] for reason in configuration["reasons"]
                                 if reason["class"] == "constraint")
            found[configuration["configuration"]] = (
                configuration["valid"], admission["alternative"] if admission["admitted"] else None,
                adapters[0] if adapters else None, constraints)
        assert found == expected, name
    shadow = receipts["sdv_product_line.receipt.json"]["shadow"]
    assert all(model["complement_errors"] == [] and model["rule_table_errors"] == []
               for model in shadow["feature_models"])


@pytest.mark.skipif(not (ROOT / runner.EVALUATION_CLI).is_file(),
                    reason="the evaluator of ADR 0022 step S2 (#406) is not on this revision yet")
def test_the_committed_receipts_replay_offline() -> None:
    """The unlicensed check: the evaluator reproduces every receipt from the committed elements,
    and none is stale by the digest of a source, the elements or the evaluator."""
    from scripts import run_pleml_configuration_evaluation as evaluation

    receipts = sorted(str(path) for path in RECEIPTS.glob("*.receipt.json"))
    assert len(receipts) == len(FEATURE_MODELS)
    assert evaluation.main(["replay", *receipts]) == 0
