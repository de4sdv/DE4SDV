"""O4 W2 batch 6 — product-line class definitions parity (three rows).

Batch scope (exactly three retained, ungated ``MODEL_AUTHORITY_PARITY`` rows
grounded in ``de4sdv_product_line.sysml``):

* ``ProductLine``              -> ``part def ProductLine``
* ``MemberProduct``            -> ``part def ProductLineMemberProduct``
* ``DeferredProductLineScope`` -> ``part def DeferredProductLineScope``

All three close definition-level parity normalized-exact: the model docs
carry the reviewed definition texts verbatim under cosmetic normalization
only.  Declarations and their names are unchanged; the native variation
mechanism and the other classification rows are untouched.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from de4sdv.semantic.o3_bundle import MIGRATED_IDENTITIES

REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCT_LINE = REPO_ROOT / "textual-notation-of-model/packages/methods/de4sdv/de4sdv_product_line.sysml"
INVENTORY = REPO_ROOT / "docs/method-conformance/o1/semantic-authority-inventory.json"
DECISIONS = REPO_ROOT / "docs/method-conformance/o1/authority-review-decisions.yaml"
REGISTER = REPO_ROOT / "docs/method-conformance/o4/o4-execution-register.json"
SCOPE = REPO_ROOT / "docs/method-conformance/o3/o3-equivalence-scope.json"

BATCH_ROWS = ("ProductLine", "MemberProduct", "DeferredProductLineScope")
MAPPING = {
    "ProductLine": "part def ProductLine",
    "MemberProduct": "part def ProductLineMemberProduct",
    "DeferredProductLineScope": "part def DeferredProductLineScope",
}
ACCEPTED_DEFINITION = {
    "ProductLine": "A family of related member products managed through shared assets and variability.",
    "MemberProduct": "A configured product or product variant that belongs to a product line.",
    "DeferredProductLineScope": (
        "Product-line scope deliberately deferred from the current increment, including recorded gaps."
    ),
}
STAGE = "o4-w2 batch 6 (definitions parity)"
OBLIGATION = "O2 admission / generated Semantic Projection from the reviewed model representation"

USAGES = {
    "model-based-product-line-engineering/scoping/de4sdv_aebs_product_line_scope.sysml": [
        "part def GovernedDE4SDVAEBSReferenceProductLineScope :> SDVProductLine {",
    ],
    "textual-notation-of-model/packages/features/aebs/aebs_needs_requirements.sysml": [
        "part memberProduct : ProductLineMemberProduct;",
    ],
    "textual-notation-of-model/packages/features/middleware/middleware_feature_classification.sysml": [
        "part safetyPathDecision : DeferredProductLineScope {",
        "part securityTrustBoundary : DeferredProductLineScope {",
    ],
}


def _flat(text: str) -> str:
    return " ".join(text.replace("*", " ").split())


def _declaration_block(text: str, decl_start: str) -> list[str]:
    lines = text.splitlines()
    start = next(index for index, line in enumerate(lines) if line.strip().startswith(decl_start))
    base_indent = len(lines[start]) - len(lines[start].lstrip())
    block = [lines[start]]
    for line in lines[start + 1 :]:
        block.append(line)
        if line.strip() == "}" and (len(line) - len(line.lstrip())) == base_indent:
            break
    return block


@pytest.fixture(scope="module")
def model_text() -> str:
    return PRODUCT_LINE.read_text()


@pytest.fixture(scope="module")
def inventory() -> dict:
    return json.loads(INVENTORY.read_text())


@pytest.fixture(scope="module")
def decisions() -> dict:
    return yaml.safe_load(DECISIONS.read_text())["entries"]


@pytest.fixture(scope="module")
def register_rows() -> dict:
    return {row["identity"]: row for row in json.loads(REGISTER.read_text())["rows"]}


def _entry(inventory: dict, identity: str) -> dict:
    return next(e for e in inventory["entries"] if e["identity"] == identity)


# ---------------------------------------------------------------------------
# 1. Batch scope, mappings, definitions, parity state
# ---------------------------------------------------------------------------


def test_exact_three_row_scope(register_rows):
    for identity in BATCH_ROWS:
        row = register_rows[identity]
        assert row["membership"] == "o4-target"
        assert row["base_wave"] == "W2"
        assert row.get("gate_wave") is None
        assert row.get("migration_class") == "MODEL_AUTHORITY_PARITY"
        assert row.get("blocker") is None
    assert len(BATCH_ROWS) == 3


def test_exactly_the_batch_rows_carry_the_batch_stage(decisions):
    staged = [name for name, row in decisions.items() if row.get("stage") == STAGE]
    assert sorted(staged) == sorted(BATCH_ROWS)


def test_declaration_mapping(inventory):
    for identity in BATCH_ROWS:
        entry = _entry(inventory, identity)
        observed = entry["observed"]
        assert observed["declaration"] == MAPPING[identity]
        assert observed["file"] == "textual-notation-of-model/packages/methods/de4sdv/de4sdv_product_line.sysml"
        assert observed["yaml_path"] == f"classes:{identity}"


def test_accepted_definitions_are_carried(model_text):
    for identity in BATCH_ROWS:
        block = _flat(" ".join(_declaration_block(model_text, MAPPING[identity])))
        assert ACCEPTED_DEFINITION[identity] in block, identity


def test_honest_parity_state(inventory, decisions):
    for identity in BATCH_ROWS:
        entry = _entry(inventory, identity)
        assert entry["observed"]["doc_text_observation"] == "normalized-exact", identity
        assert entry["reviewed"]["semantic_text_equivalence"] is None, identity
        row = decisions[identity]
        assert row["semantic_text_equivalence"] is None
        assert row["stage"] == STAGE
        assert "batch-6 parity-reviewed" in row["note"]
        assert row["exact_fit_decision"].startswith(
            "exact fit: definition-level parity complete (o4-w2 batch 6)"
        )


def test_legacy_yaml_authority_remains(decisions, inventory):
    for identity in BATCH_ROWS:
        row = decisions[identity]
        assert row["authority_current"] == "legacy-yaml"
        assert row["authority_target"] == "model-authoritative"
        assert row["conditional_target"] is False
        assert row["transition_gate"] is None
        assert row["closure_evidence_ref"] is None
        assert row["adoption_status"] == "not-applicable"
        assert row["evidence_state"] == "repository-evidenced"
        assert _entry(inventory, identity)["reviewed"]["authority_current"] == "legacy-yaml"


def test_remaining_obligation_is_o4_o2_only(decisions):
    for identity in BATCH_ROWS:
        evidence = decisions[identity]["required_evidence"]
        assert evidence == [OBLIGATION], identity
        assert all("O3" not in item for item in evidence)


# ---------------------------------------------------------------------------
# 2. Declaration-name, classification-root, and native-boundary boundaries
# ---------------------------------------------------------------------------


def test_declaration_names_unchanged(model_text):
    # No silent rename: the member-product declaration keeps its governed name.
    assert "part def ProductLineMemberProduct {" in model_text
    assert "part def MemberProduct {" not in model_text
    assert "part def ProductLine {" in model_text
    assert "part def DeferredProductLineScope :> ProductLineCharacteristic {" in model_text


def test_classification_root_kept(model_text):
    block = " ".join(_declaration_block(model_text, "part def ProductLine"))
    assert ":>" not in block.split("doc /*")[0]


def test_deferred_scope_distinct_from_native_variation(model_text):
    deferred = " ".join(_declaration_block(model_text, "part def DeferredProductLineScope"))
    assert "DeferredProductLineVariation" not in deferred
    assert "DeferredVariantChoice" not in deferred
    # The native variation mechanism remains present and untouched.
    assert "variation part def DeferredProductLineVariation {" in model_text
    assert "variant part deferredChoice;" in model_text
    assert "part def DeferredVariantChoice :> ProductLineVariantChoice {" in model_text


def test_unrelated_product_line_rows_untouched(model_text):
    # The still-untreated classification rows keep their pre-batch docs.
    # (ProductLineCharacteristic is treated by W2 batch 7 / safe-set 2; its
    # doc parity is pinned in tests/test_o4_accelerated_safe_set_2.py.)
    assert (
        "doc /* Capability required across member products; not a feature unless it distinguishes member products. */"
        in model_text
    )
    assert (
        "doc /* Candidate distinguishing characteristic; must not be accepted as a feature until member-product variability is shown. */"
        in model_text
    )


def test_existing_usages_remain_intact():
    for path, lines in USAGES.items():
        text = (REPO_ROOT / path).read_text()
        for line in lines:
            assert line in text, (path, line)


# ---------------------------------------------------------------------------
# 3. Projections, runtime, frozen O3, prior batches
# ---------------------------------------------------------------------------


def test_no_new_projection_rows():
    expected_rows = {
        "docs/method-conformance/o2/semantic-projection-v1.1.json": (
            ["VerificationCase"],
            ["hasSubject", "verifiedBy"],
        ),
        "docs/method-conformance/o2/semantic-projection-v1.2.json": (
            [],
            ["derivesRequirementFromNeed", "derivedRequirementsOfNeed", "hasRelevantArchitecture"],
        ),
    }
    for artifact, (concepts, predicates) in expected_rows.items():
        data = json.loads((REPO_ROOT / artifact).read_text())
        assert [row["identity"] for row in data.get("concepts", [])] == concepts, artifact
        assert [row["identity"] for row in data.get("predicates", [])] == predicates, artifact
        row_ids = {row["identity"] for row in data.get("concepts", []) + data.get("predicates", [])}
        assert not (row_ids & set(BATCH_ROWS)), artifact


def test_no_runtime_or_o3_promotion(register_rows):
    scope = json.loads(SCOPE.read_text())
    identities = {row["identity"] for row in scope["identities"]}
    assert identities == set(MIGRATED_IDENTITIES)
    assert len(identities) == 13
    for identity in BATCH_ROWS:
        assert identity not in identities
        assert register_rows[identity].get("gate_wave") is None


def test_prior_batch_rows_unchanged(decisions):
    expected_stage = {
        "EngineeringIncrement": "o4-w2 pilot 1 (definitions parity)",
        "FeatureIncrement": "o4-w2 pilot 1 (definitions parity)",
        "NeedsRequirementsIncrement": "o4-w2 pilot 1 (definitions parity)",
        "IncrementEngineeringQuestion": "o4-w2 pilot 2 (definitions parity)",
        "IncrementLifecycleDecision": "o4-w2 pilot 2 (definitions parity)",
        "SystemLayer": "o4-w2 pilot 2 (definitions parity)",
        "ProblemStatement": "o4-w2 pilot 2 (definitions parity)",
        "Assumption": "o4-w2 pilot 2 (definitions parity)",
        "Gap": "o4-w2 pilot 2 (definitions parity)",
        "SignalMappingDisposition": "o4-w2 batch 3 (definitions parity)",
        "LogicalToSoftwareSignalMappingRecord": "o4-w2 batch 3 (definitions parity)",
        "SystemToSoftwareSignalMappingCandidate": "o4-w2 batch 3 (definitions parity)",
        "Need": "o4-w2 batch 4 (definitions parity)",
        "Requirement": "o4-w2 batch 4 (definitions parity)",
        "RegulatoryConstraint": "o4-w2 batch 4 (definitions parity)",
        "MissingRealizationRecord": "o4-w2 batch 5 (definitions parity)",
        "BlockedRealizationBranchRecord": "o4-w2 batch 5 (definitions parity)",
    }
    for identity, stage in expected_stage.items():
        assert decisions[identity]["stage"] == stage, identity
        assert decisions[identity]["authority_current"] == "legacy-yaml", identity
    # Untreated W2 rows keep their pre-parity stage. ProductLineCharacteristic
    # left this set in W2 batch 7 (safe-set 2); its executed stage is pinned in
    # tests/test_o4_accelerated_safe_set_2.py.
    for identity in ("Feature", "CommonCapability"):
        assert decisions[identity]["stage"] == "batched-parity (post-0a/0b)", identity
