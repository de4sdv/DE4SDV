"""Historical definition records and current model boundaries.

This cleanup retires current-documentation equality with copied or frozen definitions.
Live checks retain owned nonempty documentation, structure and claim boundaries.
Inventory/decision parity fields below describe frozen historical evidence only;
they are not recomputed from, or imposed on, current model wording.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from de4sdv.semantic.model_contract import O2_CHAIN_IDENTITIES as MIGRATED_IDENTITIES
from model_contract_fixtures import owned_definition_documentation

REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCT_LINE = REPO_ROOT / "textual-notation-of-model/packages/methods/de4sdv/de4sdv_product_line.sysml"
REGISTER = REPO_ROOT / "de4sdv/semantic/contract-data/ontology-identity-register.json"

BATCH_ROWS = ("ProductLine", "MemberProduct", "DeferredProductLineScope")
MAPPING = {
    "ProductLine": "part def ProductLine",
    "MemberProduct": "part def ProductLineMemberProduct",
    "DeferredProductLineScope": "part def DeferredProductLineScope",
}

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
def register_rows() -> dict:
    return {row["identity"]: row for row in json.loads(REGISTER.read_text())["rows"]}


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


def test_definitions_have_owned_nonempty_documentation(model_text):
    # This cleanup retired accepted-definition copied prose, not the declaration homes.
    for identity in BATCH_ROWS:
        assert owned_definition_documentation(model_text, MAPPING[identity]).strip(), identity


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
        "de4sdv/semantic/contract-data/frozen-records/semantic-projection-v1.1.json": (
            ["VerificationCase"],
            ["hasSubject", "verifiedBy"],
        ),
        "de4sdv/semantic/contract-data/frozen-records/semantic-projection-v1.2.json": (
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
    for identity in BATCH_ROWS:
        assert identity not in MIGRATED_IDENTITIES
        assert register_rows[identity].get("gate_wave") is None
