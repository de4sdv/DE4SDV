"""O3 completion record: machine checks for the production-cutover evidence.

The record binds the completed cutover to the runtime code's frozen
identity set and to well-formed evidence identities; it must not drift from
`MIGRATED_IDENTITIES` and must state its completion explicitly.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EVIDENCE = REPO / "docs/method-conformance/o3/o3-production-cutover-evidence.json"
SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
BUNDLE_ID = re.compile(r"^o3b-[0-9a-f]{32}$")


def _evidence() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_completion_record_binds_the_frozen_thirteen_to_runtime_code() -> None:
    from de4sdv.semantic.o3_bundle import MIGRATED_IDENTITIES

    evidence = _evidence()
    assert evidence["schema"] == "de4sdv.o3-production-cutover-evidence/v1"
    assert evidence["status"] == "complete"
    assert evidence["bundle"]["migrated_identities"] == list(MIGRATED_IDENTITIES)
    assert len(evidence["bundle"]["migrated_identities"]) == 13


def test_completion_evidence_identities_are_well_formed() -> None:
    evidence = _evidence()
    assert BUNDLE_ID.match(evidence["bundle"]["id"])
    assert evidence["bundle"]["state"] == "closed"
    assert evidence["bundle"]["runtime_build"].startswith("rb-")
    for sha in (
        evidence["bundle"]["sha256"],
        evidence["deployment_binding"]["binding_sha256"],
        evidence["deployment_bound_closure"]["attestation_sha256"],
        evidence["deployment_bound_closure"]["grounding_artifact_sha256"],
        evidence["privileged_evidence"]["export_sha256"],
    ):
        assert SHA256.match(sha), sha
    assert (
        evidence["deployed_git_revision"]
        == evidence["deployment_binding"]["git_revision"]
    )
    assert evidence["deployment_binding"]["element_count"] == 82102


def test_completion_gates_and_final_state_are_recorded() -> None:
    evidence = _evidence()
    closure = evidence["deployment_bound_closure"]
    assert closure["grounding"] == "EQUIVALENT"
    assert closure["activation_eligible"] is True
    assert closure["closure_verification_errors"] == "none"
    batteries = evidence["production_cutover"]["probe_batteries"]
    assert batteries["o3_activation_corrected"] == "15/15 PASS"
    assert batteries["legacy_rollback"] == "15/15 PASS"
    assert batteries["o3_reactivation"] == "15/15 PASS"
    assert batteries["cross_phase_answers"].startswith("identical")
    final = evidence["final_production_authority"]
    assert final["selector"] == "DE4SDV_SEMANTIC_AUTHORITY=o3"
    assert final["authority_id"] == (
        f"o3:{evidence['bundle']['id']}"
    )
    assert "exactly the frozen 13-identity scope" in evidence["statement"]
