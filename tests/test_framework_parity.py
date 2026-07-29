"""Smoke tests for the shared AEBS evidence framework.

The per-increment builders were removed after parity was proven, so this file
now checks that the framework can still build valid evidence documents for the
supported contracts.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BENCH_ROOT = REPO_ROOT / "implementation" / "aebs-autoware-nominal-vehicle-target-bench"
SCRIPTS_ROOT = BENCH_ROOT / "scripts"
PACKAGE_ROOT = BENCH_ROOT / "src" / "de4sdv_aebs_009b_bench"
FRAMEWORK_ROOT = REPO_ROOT / "implementation" / "aebs-bench-framework"

for path in (REPO_ROOT, SCRIPTS_ROOT, PACKAGE_ROOT, FRAMEWORK_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from evidence_document import load_strict_json
from evidence_pipeline import build_evidence, load_contract
from de4sdv_aebs_009b_bench.crossing_target_matrix import TargetType
from de4sdv_aebs_009b_bench.degraded_input_matrix import DegradedInputScenario
from de4sdv_aebs_009b_bench.non_activation_matrix import NonActivationScenario
from de4sdv_aebs_009b_bench.override_matrix import OverrideScenario


def _assert_smoke_document(document: dict, *, schema: str, increment_id: str) -> None:
    assert document["schema"] == schema
    assert document["increment_id"] == increment_id
    assert document["claim_boundary"]
    assert document["evaluation"]
    assert document["collection"]["observations"]
    assert document["artifacts"]


def _load_009d_fixture(profile: OverrideScenario) -> tuple[dict, dict, dict]:
    manifest = load_strict_json(BENCH_ROOT / "evidence" / "009d" / "campaign-manifest.json")
    entry = manifest["profiles"][profile.value]
    run_dir = (
        BENCH_ROOT
        / "evidence"
        / "009d"
        / "profiles"
        / profile.value
        / "runs"
        / entry["run_id"]
    )
    return (
        load_strict_json(run_dir / "observer-raw.json"),
        load_strict_json(run_dir / "provenance.json"),
        load_strict_json(run_dir / "artifacts.json"),
    )


class TestFrameworkSmoke009D:
    def test_override_evidence_builds_with_shared_framework(self) -> None:
        raw, provenance, artifacts = _load_009d_fixture(OverrideScenario.FRESH_FALSE_CONTROL)
        contract = load_contract(BENCH_ROOT / "config/contract-009d.yaml")
        document = build_evidence(
            raw,
            OverrideScenario.FRESH_FALSE_CONTROL,
            provenance,
            artifacts,
            contract=contract,
            bench_root=BENCH_ROOT,
        )
        _assert_smoke_document(
            document,
            schema="de4sdv.aebs-009d.override-evidence.v1",
            increment_id="INC-AEBS-009D",
        )


class TestFrameworkSmoke009E:
    def test_non_activation_evidence_builds_with_shared_framework(self) -> None:
        from tests.test_aebs_009e_non_activation_matrix import (
            _make_artifacts,
            _make_provenance,
            _make_raw,
            _passing_observations,
        )

        profile = NonActivationScenario.CLEAR_PATH
        raw = _make_raw(_passing_observations(), profile)
        artifacts, _ = _make_artifacts(BENCH_ROOT, profile.value, "framework-smoke-009e", raw)
        try:
            document = build_evidence(
                raw,
                profile,
                _make_provenance(BENCH_ROOT, profile.value),
                artifacts,
                contract=load_contract(BENCH_ROOT / "config/contract-009e.yaml"),
                bench_root=BENCH_ROOT,
            )
            _assert_smoke_document(
                document,
                schema="de4sdv.aebs-009e.non-activation-evidence.v1",
                increment_id="INC-AEBS-009E",
            )
            assert document["profile"] == profile.value
        finally:
            import shutil

            shutil.rmtree(BENCH_ROOT / "evidence" / "009e" / "test_fixtures", ignore_errors=True)


class TestFrameworkSmoke009F:
    def test_degraded_input_evidence_builds_with_shared_framework(self) -> None:
        from tests.test_aebs_009f_degraded_input_matrix import (
            _cleanup_fixtures,
            _make_artifacts,
            _make_provenance,
            _make_raw,
            _observations,
        )

        profile = DegradedInputScenario.STALE_INPUT
        raw = _make_raw(_observations(profile), profile)
        artifacts, _ = _make_artifacts(BENCH_ROOT, profile.value, "framework-smoke-009f", raw)
        try:
            document = build_evidence(
                raw,
                profile,
                _make_provenance(BENCH_ROOT),
                artifacts,
                contract=load_contract(BENCH_ROOT / "config/contract-009f.yaml"),
                bench_root=BENCH_ROOT,
            )
            _assert_smoke_document(
                document,
                schema="de4sdv.aebs-009f.scenario-evidence.v1",
                increment_id="INC-AEBS-009F",
            )
            assert document["degraded_input_profile"] == profile.value
        finally:
            _cleanup_fixtures(BENCH_ROOT, profile.value)


class TestFrameworkSmoke009G009H:
    def test_crossing_target_evidence_builds_with_shared_framework(self) -> None:
        from tests.test_aebs_009g_009h_crossing_target import (
            _authorization,
            _make_artifacts,
            _make_provenance,
            _make_raw,
            _observations,
            _sample,
        )
        from de4sdv_aebs_009b_bench.crossing_target_matrix import load_crossing_target_config

        cases = [
            (
                "009g",
                "INC-AEBS-009G",
                "de4sdv.aebs-009g.scenario-evidence.v1",
                TargetType.PEDESTRIAN,
                BENCH_ROOT / "config/scenario-009g-pedestrian-crossing.yaml",
                BENCH_ROOT / "config/contract-009g.yaml",
                3.935,
            ),
            (
                "009h",
                "INC-AEBS-009H",
                "de4sdv.aebs-009h.scenario-evidence.v1",
                TargetType.BICYCLE,
                BENCH_ROOT / "config/scenario-009h-bicycle-crossing.yaml",
                BENCH_ROOT / "config/contract-009h.yaml",
                3.185,
            ),
        ]

        for subdir, increment_id, schema, target_type, config_path, contract_path, separation_m in cases:
            config = load_crossing_target_config(config_path)
            sample = _sample()
            auth = _authorization()
            raw = _make_raw(_observations(separation_m=separation_m), sample, auth, config)
            artifacts, _ = _make_artifacts(BENCH_ROOT, subdir, f"framework-smoke-{subdir}", raw)
            try:
                document = build_evidence(
                    raw,
                    target_type,
                    _make_provenance(BENCH_ROOT),
                    artifacts,
                    contract=load_contract(contract_path),
                    bench_root=BENCH_ROOT,
                )
                _assert_smoke_document(document, schema=schema, increment_id=increment_id)
                assert document["target_type"] == target_type.value
            finally:
                import shutil

                shutil.rmtree(BENCH_ROOT / "evidence" / subdir / "test_fixtures", ignore_errors=True)
