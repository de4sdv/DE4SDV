from __future__ import annotations

import json


def test_outcome_serialization_is_json_safe_and_sorted() -> None:
    """Regression: exact-head CI export crashed on frozenset values."""

    from scripts.run_pleml_gate_a import serialize_outcomes
    from tools.pleml_gate_a import DerivationOutcome

    outcomes = {
        "valid": DerivationOutcome(
            configuration_id="cfg-b",
            selected_feature_ids=frozenset({"b-feature", "a-feature"}),
            status="derivation-complete",
            derivation_attempted=True,
            rule_ids=("rule-1",),
        ),
        "invalid": DerivationOutcome(
            configuration_id="cfg-a",
            selected_feature_ids=frozenset({"z-feature"}),
            status="configuration-invalid",
            derivation_attempted=False,
            constraint_ids=("constraint-1",),
        ),
    }

    payload = serialize_outcomes(outcomes)

    assert payload["valid"]["selected_feature_ids"] == ["a-feature", "b-feature"]
    assert payload["invalid"]["derivation_attempted"] is False
    json.dumps(payload)  # must not raise
