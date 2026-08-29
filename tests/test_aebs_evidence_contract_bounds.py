"""Evidence-contract bound synchronization between SysML and bench configs.

The 009B evidence contracts state their quantitative bounds in the SysML
constraint text (warning lead, freshness, stop hold). The 009D-009H contracts
now do the same. This gate keeps those model-stated bounds and the executing
bench configs from drifting apart: every numeric bound named in a SysML
evidence contract must equal the corresponding config value, and each listed
config key must exist in the model text.

The bench configs remain the execution source of truth; the model bounds are
the verification-planning statement of the same values. If either side
changes, this test fails until both are updated together.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
MODEL_DIR = ROOT / "textual-notation-of-model/packages/features/aebs"
CONFIG_DIR = (
    ROOT
    / "implementation/aebs-autoware-nominal-vehicle-target-bench/config"
)


def _model_text(filename: str) -> str:
    return (MODEL_DIR / filename).read_text(encoding="utf-8")


def _config(filename: str) -> dict:
    return yaml.safe_load((CONFIG_DIR / filename).read_text(encoding="utf-8"))


# (sysml file, config file, [(config key, expected value)])
BOUND_CASES = [
    (
        "aebs_override_verification.sysml",
        "scenario-009d-conscious-override-matrix.yaml",
        [
            ("override_max_age_s", 0.2),
            ("closed_suppression_window_s", 0.25),
            ("graph_sampling_max_gap_s", 0.2),
        ],
    ),
    (
        "aebs_non_activation_verification.sysml",
        "scenario-009e-non-activation-matrix.yaml",
        [
            ("observation_duration_s", 4.0),
            ("sample_max_gap_s", 0.75),
            ("required_input_max_age_s", 0.5),
        ],
    ),
    (
        "aebs_degraded_input_verification.sysml",
        "scenario-009f-degraded-input-matrix.yaml",
        [
            ("degraded_state_max_age_s", 0.2),
            ("closed_detection_window_s", 0.25),
            ("graph_sampling_max_gap_s", 0.2),
        ],
    ),
    (
        "aebs_pedestrian_verification.sysml",
        "scenario-009g-pedestrian-crossing.yaml",
        [
            ("crossing_speed_mps", 1.5),
            ("closed_window_s", 2.0),
            ("max_source_age_s", 0.5),
        ],
    ),
    (
        "aebs_bicycle_verification.sysml",
        "scenario-009h-bicycle-crossing.yaml",
        [
            ("crossing_speed_mps", 4.0),
            ("closed_window_s", 2.0),
            ("max_source_age_s", 0.5),
        ],
    ),
]


def _value_in_config(config: dict, key: str):
    """Find a numeric value by key anywhere in the config tree."""
    if isinstance(config, dict):
        if key in config:
            return config[key]
        for value in config.values():
            found = _value_in_config(value, key)
            if found is not None:
                return found
    elif isinstance(config, list):
        for item in config:
            found = _value_in_config(item, key)
            if found is not None:
                return found
    return None


def test_every_model_stated_bound_matches_the_bench_config():
    for model_file, config_file, bounds in BOUND_CASES:
        text = _model_text(model_file)
        config = _config(config_file)
        for key, expected in bounds:
            found = _value_in_config(config, key)
            assert found is not None, (
                f"{key} missing from {config_file} ({model_file})"
            )
            assert float(found) == float(expected), (
                f"{key} in {config_file} is {found}, expected {expected} "
                f"(model: {model_file})"
            )
            # The model must state the same number.
            pattern = rf"(?<![\d.]){re.escape(str(expected))}(?![\d])"
            assert re.search(pattern, text), (
                f"{model_file} no longer states bound {expected} ({key}); "
                "update the evidence-contract text and the config together"
            )


def test_model_stated_bounds_live_inside_require_constraints():
    """Bounds are SysML-owned semantics: they must sit inside require
    constraint text, not in file comments or free prose."""
    for model_file, _, _ in BOUND_CASES:
        text = _model_text(model_file)
        constraint_blocks = re.findall(
            r"require constraint \{ doc /\* (.*?) \*/ \}", text, re.S
        )
        assert any(
            re.search(r"\d+\.\d+ s", block) for block in constraint_blocks
        ), f"{model_file}: no numeric bound inside any require constraint"
