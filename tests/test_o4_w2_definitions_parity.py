"""O4 W2 pilot 1 — bounded definitions-parity batch (three method-increment classes).

Pilot scope (exactly three retained, ungated ``MODEL_AUTHORITY_PARITY``
rows): ``EngineeringIncrement``, ``FeatureIncrement``,
``NeedsRequirementsIncrement`` — the method-increment classes of
``de4sdv_method_context.sysml``. The batch closes definition-level doc
parity per the O4 execution register's W2 evidence requirement
(``model-side definition parity (normalized-exact text or explicit reviewed
equivalence record)``):

1.  the live model doc text of each declaration equals the authored-YAML
    definition under the inventory's cosmetic normalization only
    (``normalized-exact``; no reviewed-equivalence record is needed);
2.  the committed inventory records it: ``doc_text_observation``
    normalized-exact, ``semantic_text_equivalence`` null, stage
    ``o4-w2 pilot 1 (definitions parity)``, the remaining O2-admission
    obligation under O4 (no O3 transition requirement), and a populated
    exact-fit decision (evidence of parity only — no authority cutover);
3.  the authored YAML remains the untouched comparison source (definitions
    pinned verbatim);
4.  no runtime-support promotion, no traversal claim, no conditional
    target, no closure evidence — and the O4 register rows stay ungated
    W2 parity rows whose retirement condition still requires O2 admission;
5.  O3 stays frozen: none of the pilot rows carries an O3 transition
    requirement, none is a member of the frozen thirteen
    ``MIGRATED_IDENTITIES``, and the O3 equivalence scope stays at exactly
    its thirteen frozen identities;
6.  unrelated reviewed rows keep their states (W1-corrected demotion, c1
    batch outcomes, the K row).
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from de4sdv.semantic.authority_inventory import doc_text_observation
from de4sdv.semantic.o3_bundle import MIGRATED_IDENTITIES

REPO = Path(__file__).resolve().parents[1]
INVENTORY_PATH = REPO / "docs/method-conformance/o1/semantic-authority-inventory.json"
DECISIONS_PATH = REPO / "docs/method-conformance/o1/authority-review-decisions.yaml"
ONTOLOGY_PATH = REPO / "approach/framework/ontology/de4sdv-basic-ontology.yaml"
REGISTER_PATH = REPO / "docs/method-conformance/o4/o4-execution-register.json"
SCOPE_PATH = REPO / "docs/method-conformance/o3/o3-equivalence-scope.json"
MODEL_PATH = (
    REPO / "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml"
)

PILOT_ROWS: dict[str, str] = {
    "EngineeringIncrement": "part def EngineeringIncrement",
    "FeatureIncrement": "part def FeatureIncrement",
    "NeedsRequirementsIncrement": "part def NeedsRequirementsIncrement",
}

REVIEWED_DEFINITIONS: dict[str, str] = {
    "EngineeringIncrement": (
        "A bounded DE4SDV work package that changes, tests, or publishes "
        "engineering knowledge."
    ),
    "FeatureIncrement": (
        "An engineering increment focused on a product-line feature, common "
        "capability, or native SysML v2 variation/variant choice."
    ),
    "NeedsRequirementsIncrement": (
        "An engineering increment focused on needs, draft requirements, "
        "traceability, and V&V planning."
    ),
}

#: The remaining forward obligation under O4 for a parity-closed W2 row: O2
#: admission / generated projection from the reviewed model representation.
#: O3 is frozen throughout O4 and these rows must never carry an O3
#: transition requirement.
REMAINING_OBLIGATION = [
    "O2 admission / generated Semantic Projection from the reviewed model representation",
]
PILOT_STAGE = "o4-w2 pilot 1 (definitions parity)"


def _inventory() -> dict:
    return json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))


def _decisions() -> dict:
    return yaml.safe_load(DECISIONS_PATH.read_text(encoding="utf-8"))["entries"]


def _entries(inventory: dict, identities=None) -> dict:
    entries = {entry["identity"]: entry for entry in inventory["entries"]}
    if identities is None:
        return entries
    return {identity: entries[identity] for identity in identities}


def test_live_model_doc_parity_is_normalized_exact() -> None:
    file_text = MODEL_PATH.read_text(encoding="utf-8")
    ontology = yaml.safe_load(ONTOLOGY_PATH.read_text(encoding="utf-8"))["classes"]
    for identity, declaration in PILOT_ROWS.items():
        definition = ontology[identity]["definition"]
        assert definition == REVIEWED_DEFINITIONS[identity]
        observation = doc_text_observation(file_text, declaration, definition)
        assert observation == "normalized-exact", identity


def test_inventory_records_the_closed_parity() -> None:
    inventory = _inventory()
    for identity, entry in _entries(inventory, PILOT_ROWS).items():
        observed = entry["observed"]
        reviewed = entry["reviewed"]
        assert observed["doc_text_observation"] == "normalized-exact", identity
        assert reviewed["semantic_text_equivalence"] is None, identity
        assert reviewed["required_evidence"] == REMAINING_OBLIGATION, identity
        assert reviewed["stage"] == PILOT_STAGE, identity
        assert "parity-reviewed" in reviewed["note"], identity
        assert "parity complete (o4-w2 pilot 1)" in reviewed["exact_fit_decision"], identity
        assert "no authority cutover implied" in reviewed["exact_fit_decision"], identity
        # The note states parity is closed but does not claim retirement:
        # authority_current stays legacy-yaml until O2 admission completes.
        assert "authority_current remains legacy-yaml until" in reviewed["note"], identity
        assert "under O4" in reviewed["note"], identity
        assert "retires as semantic authority" not in reviewed["note"], identity


def test_decisions_source_records_the_closed_parity() -> None:
    entries = _decisions()
    for identity in PILOT_ROWS:
        reviewed = entries[identity]
        assert reviewed["stage"] == PILOT_STAGE, identity
        assert reviewed["semantic_text_equivalence"] is None, identity
        assert reviewed["required_evidence"] == REMAINING_OBLIGATION, identity


def test_no_o3_transition_requirement_or_membership() -> None:
    inventory = _inventory()
    for identity, entry in _entries(inventory, PILOT_ROWS).items():
        evidence = entry["reviewed"]["required_evidence"]
        assert not any("O3" in item for item in evidence), identity

    # O3 stays frozen at exactly the thirteen migrated identities, and no
    # pilot row may be added to it.
    assert len(MIGRATED_IDENTITIES) == 13
    assert set(PILOT_ROWS).isdisjoint(set(MIGRATED_IDENTITIES))

    # No O3 scope/semantic membership expansion: the equivalence scope keeps
    # exactly its frozen thirteen identities, none of them a pilot row.
    scope = json.loads(SCOPE_PATH.read_text(encoding="utf-8"))
    scope_identities = {entry["identity"] for entry in scope["identities"]}
    assert len(scope_identities) == 13
    assert set(PILOT_ROWS).isdisjoint(scope_identities)


def test_no_support_promotion_and_no_traversal_change() -> None:
    inventory = _inventory()
    for identity, entry in _entries(inventory, PILOT_ROWS).items():
        reviewed = entry["reviewed"]
        assert reviewed["authority_current"] == "legacy-yaml", identity
        assert reviewed["authority_target"] == "model-authoritative", identity
        assert reviewed["evidence_state"] == "repository-evidenced", identity
        assert reviewed["conditional_target"] is False, identity
        assert reviewed["closure_evidence_ref"] is None, identity
        assert reviewed["adoption_status"] == "not-applicable", identity
        assert reviewed["disposition"] == "move-meaning-into-model", identity


def test_register_rows_stay_ungated_w2_parity_rows() -> None:
    register = json.loads(REGISTER_PATH.read_text(encoding="utf-8"))
    rows = {row["identity"]: row for row in register["rows"]}
    for identity in PILOT_ROWS:
        row = rows[identity]
        assert row["base_wave"] == "W2", identity
        assert row["gate_wave"] is None, identity
        assert row["migration_class"] == "MODEL_AUTHORITY_PARITY", identity
        assert row["final_disposition"] == "KEEP_DE4SDV_APPLICATION_SEMANTIC", identity
        assert (
            row["required_runtime_or_consumer_change"]["traversal_required"] is False
        ), identity


def test_register_retirement_still_requires_o2_admission() -> None:
    register = json.loads(REGISTER_PATH.read_text(encoding="utf-8"))
    rows = {row["identity"]: row for row in register["rows"]}
    for identity in PILOT_ROWS:
        condition = rows[identity]["retirement_condition"]
        assert "O2 admission" in condition, identity
        assert "O3" not in condition, identity


def test_feature_increment_note_preserves_ple_qualification() -> None:
    inventory = _inventory()
    reviewed = _entries(inventory, PILOT_ROWS)["FeatureIncrement"]["reviewed"]
    note = reviewed["note"]
    assert "variation/variant semantics remain the reference" in note
    assert "does not decide configurator authority or decision-9" in note


def test_yaml_comparison_source_is_untouched() -> None:
    ontology = yaml.safe_load(ONTOLOGY_PATH.read_text(encoding="utf-8"))["classes"]
    for identity, definition in REVIEWED_DEFINITIONS.items():
        assert ontology[identity]["definition"] == definition, identity


def test_unrelated_reviewed_rows_are_unchanged() -> None:
    inventory = _inventory()
    entries = _entries(inventory)
    # The W1-corrected demoted row keeps its bounded-vocabulary record; its
    # W3 parity requirement was closed by O4 accelerated safe-set 1, so the
    # residual is the no-promotion boundary (updated when that batch landed).
    increment_size = entries["IncrementSize"]["reviewed"]
    assert increment_size["disposition"] == "keep-as-is"
    assert increment_size["required_evidence"] == [
        "none beyond bounded vocabulary: model-resident guidance labels; never promoted to semantic authority"
    ]
    # c1's incomplete row still carries its structural gap, and c1's closed
    # rows keep their recorded outcomes.
    assert entries["MethodEvaluationScope"]["reviewed"]["evidence_state"] == (
        "repository-evidenced"
    )
    assert entries["MethodPhase"]["observed"]["doc_text_observation"] == (
        "normalized-exact"
    )
    assert entries["MethodContractObligation"]["reviewed"][
        "semantic_text_equivalence"
    ] == "reviewed-equivalent"
    # The K row keeps its review-required state.
    assert entries["DerivesFromNeed"]["reviewed"]["semantic_text_equivalence"] == (
        "review-required"
    )
