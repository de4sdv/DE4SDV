"""Tests for the hardened derivation-slice proof CLI (R5).

Fault injection through a controlled fake service: the script must reject
wrong endpoints, incomplete witnesses, gap-ridden observations, wrong
revisions, and missing expected-revision inputs — never report a false pass.
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import scripts.prove_derivation_slice as proof  # noqa: E402

GOOD_REVISION = "a" * 40


class FakeService:
    """Configurable fake semantic runtime for fault injection."""

    def __init__(self, *, edges: dict, gaps: dict, revision: str = GOOD_REVISION):
        self._edges = edges
        self._gaps = gaps
        self._rev = revision

    def _revision(self) -> dict:
        return {
            "git_commit": self._rev,
            "sysml_project_id": "proj",
            "sysml_commit_id": "commit",
            "binding_status": "synchronized",
        }

    def resolve_element(self, name: str) -> dict:
        ids = {
            "reqDetectForwardCollisionRisk": "uuid-detect",
            "reqProvideCollisionWarning": "uuid-warn",
            "reqCommandEmergencyBraking": "uuid-brake",
            "reqPedestrianTargetResponse": "uuid-ped",
            "reqBicycleTargetResponse": "uuid-bike",
            "needCommonAEBSCapability": "uuid-need-common",
            "needPedestrianCollisionRiskReduction": "uuid-need-ped",
            "needBicycleCollisionRiskReduction": "uuid-need-bike",
        }
        if name not in ids:
            raise KeyError(name)
        return {"element": {"element_id": ids[name]}}

    _IDS = {
        "reqDetectForwardCollisionRisk": "uuid-detect",
        "reqProvideCollisionWarning": "uuid-warn",
        "reqCommandEmergencyBraking": "uuid-brake",
        "reqPedestrianTargetResponse": "uuid-ped",
        "reqBicycleTargetResponse": "uuid-bike",
        "needCommonAEBSCapability": "uuid-need-common",
        "needPedestrianCollisionRiskReduction": "uuid-need-ped",
        "needBicycleCollisionRiskReduction": "uuid-need-bike",
    }

    def semantic_neighbors(self, name: str, *, predicates: list) -> dict:
        # The real service resolves names to UUIDs; the fake must too.
        resolved = self._IDS.get(name, name)
        key = (resolved, predicates[0])
        if key in self._edges:
            return {
                "edges": self._edges[key],
                "gaps": self._gaps.get(key, []),
            }
        return {"edges": [], "gaps": self._gaps.get(key, [{"reason": "none"}])}


def _good_edges() -> dict:
    cases = {}
    pairs = {
        "reqDetectForwardCollisionRisk": "uuid-detect",
        "reqProvideCollisionWarning": "uuid-warn",
        "reqCommandEmergencyBraking": "uuid-brake",
        "reqPedestrianTargetResponse": "uuid-ped",
        "reqBicycleTargetResponse": "uuid-bike",
    }
    needs = {
        "reqDetectForwardCollisionRisk": "uuid-need-common",
        "reqProvideCollisionWarning": "uuid-need-common",
        "reqCommandEmergencyBraking": "uuid-need-common",
        "reqPedestrianTargetResponse": "uuid-need-ped",
        "reqBicycleTargetResponse": "uuid-need-bike",
    }
    for name, source in pairs.items():
        witness = {
            "connection_id": f"conn-{name}",
            "connection_definition": "DerivesFromNeed",
            "need_end_id": [needs[name]],
            "derived_requirement_end_id": [source],
        }
        cases[(source, proof.FORWARD_PREDICATE)] = [
            {
                "source": source,
                "target": needs[name],
                "api_object_id": f"conn-{name}",
                "api_object_type": "ConnectionUsage",
                "semantic_strength": "derivation",
                "witness": witness,
            }
        ]
        cases.setdefault((needs[name], proof.INVERSE_PREDICATE), []).append(
            {
                "source": needs[name],
                "target": source,
                "api_object_id": f"conn-{name}",
                "api_object_type": "ConnectionUsage",
                "semantic_strength": "derivation",
                "witness": witness,
            }
        )
    return cases


def _run(service: FakeService, tmp_path: Path, **kwargs) -> tuple[int, dict]:
    binding = tmp_path / "binding.json"
    binding.write_text(
        json.dumps(
            {
                "git_commit": kwargs.pop("binding_revision", GOOD_REVISION),
                "git_repository": "de4sdv/DE4SDV",
                "sysml_project_id": "proj",
                "sysml_commit_id": "commit",
            }
        ),
        encoding="utf-8",
    )
    argv = [
        "proof",
        "--api-url",
        "http://unused",
        "--binding",
        str(binding),
        "--expected-revision",
        kwargs.pop("expected_revision", GOOD_REVISION),
    ]
    out = kwargs.pop("output", None)
    if out is not None:
        argv += ["--output", str(out)]
    argv += [f"--{k}" for k in ()]  # no-op; keep signature simple
    with (
        patch.object(sys, "argv", argv),
        patch.object(proof, "build_semantic_runtime", return_value=service),
        contextlib.redirect_stdout(io.StringIO()) as stdout,
    ):
        rc = proof.main()
    payload = json.loads(stdout.getvalue())
    return rc, payload


def test_correct_observations_pass(tmp_path: Path) -> None:
    rc, payload = _run(FakeService(edges=_good_edges(), gaps={}), tmp_path)
    assert rc == 0
    assert payload["verdict"] == "pass"
    assert payload["failures"] == []


def test_wrong_source_fails(tmp_path: Path) -> None:
    edges = _good_edges()
    edges[("uuid-brake", proof.FORWARD_PREDICATE)][0]["source"] = "wrong-source"
    rc, payload = _run(FakeService(edges=edges, gaps={}), tmp_path)
    assert rc == 1
    assert payload["verdict"] == "fail"
    assert any("source" in f for f in payload["failures"])


def test_wrong_target_fails(tmp_path: Path) -> None:
    edges = _good_edges()
    edges[("uuid-brake", proof.FORWARD_PREDICATE)][0]["target"] = "wrong-target"
    rc, payload = _run(FakeService(edges=edges, gaps={}), tmp_path)
    assert rc == 1
    assert any("target" in f for f in payload["failures"])


def test_incomplete_witness_fails(tmp_path: Path) -> None:
    edges = _good_edges()
    edges[("uuid-brake", proof.FORWARD_PREDICATE)][0]["witness"] = {
        "connection_id": "conn-reqCommandEmergencyBraking",
        "connection_definition": "DerivesFromNeed",
    }
    rc, payload = _run(FakeService(edges=edges, gaps={}), tmp_path)
    assert rc == 1
    assert any("witness" in f for f in payload["failures"])


def test_explicit_gaps_fail_even_with_edges(tmp_path: Path) -> None:
    """R5: an incomplete-closure gap with an edge present is a FAIL."""
    edges = _good_edges()
    key = ("uuid-brake", proof.FORWARD_PREDICATE)
    gaps = {key: [{"category": proof.FORWARD_PREDICATE, "reason": "incomplete"}]}
    rc, payload = _run(FakeService(edges=edges, gaps=gaps), tmp_path)
    assert rc == 1
    assert any("gaps" in f for f in payload["failures"])


def test_wrong_revision_fails(tmp_path: Path) -> None:
    rc, payload = _run(
        FakeService(edges=_good_edges(), gaps={}),
        tmp_path,
        binding_revision="b" * 40,
    )
    assert rc == 1
    assert any("does not match" in f for f in payload["failures"])


def test_missing_expected_revision_fails(tmp_path: Path) -> None:
    binding = tmp_path / "binding.json"
    binding.write_text(json.dumps({"git_commit": GOOD_REVISION}), encoding="utf-8")
    argv = [
        "proof",
        "--api-url",
        "http://unused",
        "--binding",
        str(binding),
    ]
    with (
        patch.object(sys, "argv", argv),
        contextlib.redirect_stdout(io.StringIO()) as stdout,
    ):
        rc = proof.main()
    payload = json.loads(stdout.getvalue())
    assert rc == 1
    assert any("expected revision" in f for f in payload["failures"])


def test_adversarial_edge_fails(tmp_path: Path) -> None:
    edges = _good_edges()
    edges[("reqAllowDriverOverride", proof.FORWARD_PREDICATE)] = [
        {
            "source": "uuid-override",
            "target": "uuid-need-common",
            "api_object_id": "dep-bad",
            "semantic_strength": "derivation",
            "witness": {"relationship_id": "dep-bad"},
        }
    ]
    rc, payload = _run(FakeService(edges=edges, gaps={}), tmp_path)
    assert rc == 1
    assert any("adversarial" in f for f in payload["failures"])
