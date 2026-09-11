"""Lane D: validated snapshot path — acceptance matrix (MC-21, MC-22, MC-28, MC-32).

Covers the D-owned snapshot cases (docs/method-conformance/mc-outcome-owner-matrix.md)
plus the adversarial set required by the Lane D brief:

- corrupt / incomplete / wrong-bound / self-attested snapshots are rejected;
- there is no silent "latest" fallback and loading is revision-explicit;
- API-loaded and snapshot-loaded transports produce identical canonical
  conformance payloads (including an unmerged candidate revision);
- reordered snapshot serialization does not alter the canonical result;
- remote-service unavailability after snapshot creation does not rewrite the
  historical evaluated result (availability is reported separately).

The snapshot is not a second semantic authority: it serializes the exact
semantic inputs of the one deterministic evaluator, and every load re-enters
the same assembly and evaluator code path as the API transport.

In-memory / tmp-path synthetic fixtures only; no real model files are copied.
Shapes mirror the committed pilot contract and the validated serializer forms
exercised by tests/test_method_contract_binding.py.
"""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from de4sdv.semantic import method_evaluator as me
from de4sdv.semantic import method_pilot as mp
from de4sdv.semantic import snapshot as sn

ROOT = Path(__file__).resolve().parents[1]

REV_SHA = "1" * 40
OTHER_SHA = "9" * 40
TESTED_HEAD = "2" * 40
EXPORT_SHA = "e" * 64
BINDING_SHA = "b" * 64
PROJECT_ID = "proj-0001"
SYSML_COMMIT = "commit-0001"

PROFILES = (
    "fresh_false_control",
    "fresh_true_conscious_override",
    "stale",
    "missing",
    "malformed",
    "future_stamped",
)


# ---------------------------------------------------------------------------
# Synthetic pilot graph and file trees (serializer-shaped fixtures)
# ---------------------------------------------------------------------------


def _element(element_id: str, element_type: str, name: str, **extra: object) -> dict:
    element = {"@id": element_id, "@type": element_type, "declaredName": name}
    element.update(extra)
    return element


def _text_member(parent_id: str, member_name: str, value: str, suffix: str) -> list[dict]:
    """FeatureMembership(memberName) -> attribute usage -> FeatureValue -> literal."""
    membership_id = f"{parent_id}-{suffix}-fm"
    attribute_id = f"{parent_id}-{suffix}-av"
    feature_value_id = f"{parent_id}-{suffix}-fv"
    literal_id = f"{parent_id}-{suffix}-ls"
    return [
        {
            "@id": membership_id,
            "@type": "FeatureMembership",
            "owningRelatedElement": {"@id": parent_id},
            "memberName": member_name,
            "memberElement": {"@id": attribute_id},
        },
        {
            "@id": attribute_id,
            "@type": "AttributeUsage",
            "owningRelatedElement": {"@id": membership_id},
            "ownedRelationship": [{"@id": feature_value_id}],
        },
        {
            "@id": feature_value_id,
            "@type": "FeatureValue",
            "owningRelatedElement": {"@id": attribute_id},
            "memberElement": {"@id": literal_id},
        },
        {"@id": literal_id, "@type": "LiteralString", "value": value},
    ]


def mini_pilot_elements() -> list[dict]:
    """Compact synthetic pilot graph with real serializer member chains."""
    elements: list[dict] = []
    definition_id = "aaaaaaaa-0000-4000-8000-0000000000d0"
    elements.append(
        _element(
            definition_id,
            "VerificationCaseDefinition",
            "ConsciousOverrideVerification",
            declaredShortName="VC-AEBS-009D-DE",
        )
    )
    for index, profile in enumerate(PROFILES, start=1):
        usage_id = f"aaaaaaaa-0000-4000-8000-000000000{index:03d}"
        elements.append(
            _element(
                usage_id,
                "VerificationCaseUsage",
                f"override{profile.title().replace('_', '')}Verification",
                declaredShortName=f"VC-AEBS-009D-{index:02d}",
            )
        )
        elements.append(
            {
                "@id": f"{usage_id}-typing",
                "@type": "FeatureTyping",
                "owningRelatedElement": {"@id": usage_id},
                "specific": {"@id": usage_id},
                "typedFeature": {"@id": usage_id},
                "general": {"@id": definition_id},
                "type": {"@id": definition_id},
            }
        )
        elements.append(
            {
                "@id": f"{usage_id}-subject",
                "@type": "SubjectMembership",
                "owningRelatedElement": {"@id": usage_id},
                "memberElement": {"@id": f"{usage_id}-bench"},
            }
        )
        elements.append(
            _element(f"{usage_id}-bench", "PartUsage", f"{profile}Bench")
        )
        elements.append(
            {
                "@id": f"{usage_id}-meta-m",
                "@type": "OwningMembership",
                "owningRelatedElement": {"@id": usage_id},
                "memberElement": {"@id": f"{usage_id}-meta-u"},
            }
        )
        elements.append(
            {
                "@id": f"{usage_id}-meta-u",
                "@type": "MetadataUsage",
                "owningRelationship": {"@id": f"{usage_id}-meta-m"},
            }
        )
    # Objective on the definition + the three evidence-contract requirements.
    objective_id = "aaaaaaaa-0000-4000-8000-0000000000e0"
    elements.append(_element(objective_id, "RequirementUsage", "evidenceObjective"))
    elements.append(
        {
            "@id": "aaaaaaaa-0000-4000-8000-0000000000e1",
            "@type": "ObjectiveMembership",
            "owningRelatedElement": {"@id": definition_id},
            "memberElement": {"@id": objective_id},
        }
    )
    for index, short in enumerate(
        ("EC-009D-01", "EC-009D-02", "EC-009D-03"), start=1
    ):
        requirement_id = f"aaaaaaaa-0000-4000-8000-0000000000f{index}"
        elements.append(
            _element(
                requirement_id,
                "RequirementUsage",
                f"evidenceContract{index}",
                declaredShortName=short,
            )
        )
        elements.append(
            {
                "@id": f"{requirement_id}-verify",
                "@type": "RequirementVerificationMembership",
                "owningRelatedElement": {"@id": objective_id},
                "memberElement": {"@id": requirement_id},
            }
        )
    # The declared pilot scope record (PSC-009D) with its member values.
    scope_record_id = "aaaaaaaa-0000-4000-8000-0000000000c0"
    scope_members = _text_member(scope_record_id, "incrementId", "INC-AEBS-009D", "increment")
    elements.append(
        _element(
            scope_record_id,
            "PartUsage",
            "aebsOverridePilotScope",
            declaredShortName="PSC-009D",
            ownedRelationship=[{"@id": item["@id"]} for item in scope_members],
        )
    )
    elements.extend(scope_members)
    # The declared tested scope (testedScope item) + bench definition.
    tested_scope_id = "aaaaaaaa-0000-4000-8000-0000000000c1"
    head_members = _text_member(tested_scope_id, "executionHead", TESTED_HEAD, "head")
    profile_members = _text_member(
        tested_scope_id, "profileIdentities", ",".join(PROFILES), "profiles"
    )
    elements.append(
        _element(
            tested_scope_id,
            "ItemUsage",
            "testedScope",
            ownedRelationship=[
                {"@id": item["@id"]} for item in head_members + profile_members
            ],
        )
    )
    elements.extend(head_members)
    elements.extend(profile_members)
    elements.append(
        _element(
            "aaaaaaaa-0000-4000-8000-0000000000b0",
            "PartDefinition",
            mp.BENCH_DEFINITION_NAME,
        )
    )
    return elements


def _write_tree(root: Path, files: dict[str, bytes]) -> Path:
    for relative, blob in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)
    return root


def _read_tree(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def candidate_files() -> dict[str, bytes]:
    manifest = {
        "execution_head": TESTED_HEAD,
        "increment_id": "INC-AEBS-009D",
        "profiles": {
            profile: {
                "path": f"evidence/009d/{profile}/scenario-evidence.json",
                "run_id": f"run-{profile}",
                "sha256": "0" * 64,
            }
            for profile in PROFILES
        },
    }
    files = {
        f"{mp.MANIFEST_PATH}": json.dumps(manifest).encode(),
        f"{mp.BENCH_ROOT}/runtime-lock.yaml": yaml.safe_dump(
            {
                "container": {
                    "index_digest": "sha256:" + "a" * 64,
                    "platform": "linux/arm64",
                },
                "map": {"sha256": "b" * 64},
                "inherited_009a": {
                    "execution_manifest_sha256": "c" * 64,
                    "runtime_lock_sha256": "d" * 64,
                },
            }
        ).encode(),
        f"{mp.BENCH_ROOT}/config/scenario-009d-conscious-override-matrix.yaml": b"matrix: []\n",
    }
    for profile in PROFILES:
        files[f"{mp.BENCH_ROOT}/evidence/009d/{profile}/scenario-evidence.json"] = json.dumps(
            {
                "profile": profile,
                "provenance": {
                    "repository_head": TESTED_HEAD,
                    "override_matrix_sha256": hashlib.sha256(b"matrix: []\n").hexdigest(),
                    "override_execution_manifest_sha256": "1" * 64,
                    "execution_manifest_sha256": "2" * 64,
                    "runtime_lock_sha256": "3" * 64,
                    "inherited_009a": {
                        "execution_manifest_sha256": "c" * 64,
                        "runtime_lock_sha256": "d" * 64,
                    },
                    "image_digest": "sha256:" + "a" * 64,
                    "map_digest": "sha256:" + "b" * 64,
                    "host_arch": "aarch64",
                },
                "evaluation": {"passed": True, "disposition": "control_clear"},
            }
        ).encode()
    return files


def _tested_files() -> dict[str, bytes]:
    files = {
        f"{mp.BENCH_ROOT}/runtime-lock.yaml": b"container: {}\n",
        f"{mp.BENCH_ROOT}/compose.yaml": b"services: {}\n",
        f"{mp.BENCH_ROOT}/scripts/run_campaign.py": b"print('campaign')\n",
        f"{mp.BENCH_ROOT}/src/de4sdv_aebs_009b_bench/__init__.py": b"",
    }
    return files


# ---------------------------------------------------------------------------
# Snapshot payload construction
# ---------------------------------------------------------------------------


def semantic_binding(git_commit: str = REV_SHA, scope: str = "candidate") -> dict:
    return {
        "git_repository": "de4sdv/DE4SDV",
        "git_commit": git_commit,
        "sysml_project_id": PROJECT_ID,
        "sysml_commit_id": SYSML_COMMIT,
        "scope": scope,
        "ontology": {"path": "ontology.yaml", "sha256": "0" * 64},
        "kernel_binding_count": 1,
    }


def method_binding() -> dict:
    return {
        "method_id": "de4sdv.method-conformance.pilot.009d.v1",
        "contract_id": "INC-AEBS-009D",
        "contract_digest": "c" * 64,
        "policy_bundle_id": "de4sdv.acceptance.maintainer-decision.v1",
    }


def scope_binding() -> dict:
    return {
        "scope_id": "PSC-009D",
        "increment_id": "INC-AEBS-009D",
        "usage_ids": [f"VC-AEBS-009D-{index:02d}" for index in range(1, 7)],
        "profiles": list(PROFILES),
        "declared_tested_head": TESTED_HEAD,
    }


def provenance(
    *,
    kind: str = "validated-api-revision",
    git_commit: str = REV_SHA,
    export_sha256: str = EXPORT_SHA,
    binding_sha256: str = BINDING_SHA,
) -> dict:
    return {
        "kind": kind,
        "validation_handle": {
            "validation_run": "34576049742",
            "artifact": "full-model-api-ingestion-<sha>",
            "git_commit": git_commit,
            "sysml_project_id": PROJECT_ID,
            "sysml_commit_id": SYSML_COMMIT,
            "scope": "candidate",
            "export_sha256": export_sha256,
            "binding_sha256": binding_sha256,
            "transaction_id": "t" * 64,
        },
    }


def expectations(**overrides) -> sn.SnapshotExpectations:
    values = dict(
        method_id=method_binding()["method_id"],
        contract_id="INC-AEBS-009D",
        contract_digest="c" * 64,
        policy_bundle_id="de4sdv.acceptance.maintainer-decision.v1",
        evaluator_build=me.EVALUATOR_BUILD_ID,
        scope_id="PSC-009D",
        increment_id="INC-AEBS-009D",
        usage_ids=tuple(scope_binding()["usage_ids"]),
        profiles=PROFILES,
        declared_tested_head=TESTED_HEAD,
        candidate_roots=(mp.BENCH_ROOT, mp.REGISTRY_PATH),
        tested_roots=(mp.BENCH_ROOT,),
        expected_evaluation_key=None,
    )
    values.update(overrides)
    return sn.SnapshotExpectations(**values)


def trusted(payload: dict | None = None, **overrides) -> sn.TrustedSnapshotBinding:
    """Build the retained-record values a caller supplies out-of-band.

    When ``payload`` is given, the externally trusted content digest is taken
    from that payload (the honest build flow: the operator records the digest
    the build produced). When omitted, a valid-shaped placeholder is used —
    only refusal tests that fail before the content binding may rely on it.
    """
    values = dict(
        git_commit=REV_SHA,
        sysml_project_id=PROJECT_ID,
        sysml_commit_id=SYSML_COMMIT,
        scope="candidate",
        export_sha256=EXPORT_SHA,
        expected_payload_digest=(
            sn.payload_digest_of(payload) if payload is not None else "e0" * 32
        ),
        binding_sha256=BINDING_SHA,
        validation_run="34576049742",
    )
    values.update(overrides)
    return sn.TrustedSnapshotBinding(**values)


def _reforge(payload: dict) -> dict:
    """Simulate a competent attacker: recompute every internal digest.

    Updates each file's recorded sha256 from its (mutated) content, then runs
    ``finalize_payload`` so every internal digest — per-file, per-role file
    inventory, elements, and payload — is self-consistent with the mutation.
    Only the externally trusted content binding can stop this.
    """
    forged = json.loads(json.dumps(payload))
    for entry in forged["file_sources"].values():
        for file_entry in entry["files"].values():
            blob = base64.b64decode(file_entry["content_b64"])
            file_entry["sha256"] = hashlib.sha256(blob).hexdigest()
    return sn.finalize_payload(forged)


def build_payload(**overrides) -> dict:
    values: dict = dict(
        semantic_binding=semantic_binding(),
        method_binding=method_binding(),
        evaluator_binding={"build_id": me.EVALUATOR_BUILD_ID},
        scope_binding=scope_binding(),
        elements=mini_pilot_elements(),
        file_sources={
            "candidate": {
                "revision": REV_SHA,
                "roots": [mp.BENCH_ROOT, mp.REGISTRY_PATH],
                "files": candidate_files(),
            },
            "tested": {
                "revision": TESTED_HEAD,
                "roots": [mp.BENCH_ROOT],
                "files": _tested_files(),
            },
        },
        provenance=provenance(),
        declared_evaluation_key=None,
    )
    values.update(overrides)
    return sn.build_snapshot_payload(**values)


def write_snapshot(tmp_path: Path, payload: dict, name: str = "snapshot.json") -> Path:
    target = tmp_path / name
    target.write_text(json.dumps(payload))
    return target


def reload_payload(tmp_path: Path, payload: dict, name: str = "snapshot.json") -> Path:
    """Re-serialize through the writer so digests stay consistent."""
    target = tmp_path / name
    sn.write_snapshot(payload, target)
    return target


# ---------------------------------------------------------------------------
# MC-21: valid snapshot loads; every corruption class fails closed
# ---------------------------------------------------------------------------


def test_mc21_valid_exact_bound_snapshot_loads(tmp_path: Path) -> None:
    payload = build_payload()
    path = reload_payload(tmp_path, payload)
    loaded = sn.load_snapshot(path, trusted=trusted(payload), expectations=expectations())
    assert loaded.revision == me.RevisionIdentity(
        git_commit=REV_SHA,
        sysml_project_id=PROJECT_ID,
        sysml_commit_id=SYSML_COMMIT,
        scope="candidate",
    )
    assert len(loaded.elements) == len(mini_pilot_elements())
    assert set(loaded.sources) == {"candidate", "tested"}
    assert loaded.sources["candidate"].read_bytes(
        f"{mp.MANIFEST_PATH}"
    ) is not None
    assert len(loaded.payload_digest) == 64


def test_mc21_missing_required_section_rejected(tmp_path: Path) -> None:
    payload = build_payload()
    del payload["integrity"]
    path = write_snapshot(tmp_path, payload)
    with pytest.raises(sn.SnapshotCompletenessError, match="integrity"):
        sn.load_snapshot(path, trusted=trusted(), expectations=expectations())


def test_mc21_corrupt_payload_digest_rejected(tmp_path: Path) -> None:
    payload = build_payload()
    payload["integrity"]["payload_digest"] = "0" * 64
    path = write_snapshot(tmp_path, payload)
    with pytest.raises(sn.SnapshotIntegrityError, match="payload_digest"):
        sn.load_snapshot(path, trusted=trusted(), expectations=expectations())


def test_mc21_corrupt_element_payload_rejected(tmp_path: Path) -> None:
    payload = build_payload()
    payload["graph"]["elements"][0]["declaredName"] = "Tampered"
    path = write_snapshot(tmp_path, payload)
    with pytest.raises(sn.SnapshotIntegrityError, match="elements"):
        sn.load_snapshot(path, trusted=trusted(), expectations=expectations())


def test_mc21_corrupt_file_blob_rejected(tmp_path: Path) -> None:
    payload = build_payload()
    role = payload["file_sources"]["candidate"]
    first_key = sorted(role["files"])[0]
    role["files"][first_key]["content_b64"] = "AAAA"
    path = write_snapshot(tmp_path, payload)
    with pytest.raises(sn.SnapshotIntegrityError):
        sn.load_snapshot(path, trusted=trusted(), expectations=expectations())


def test_mc21_empty_graph_rejected(tmp_path: Path) -> None:
    with pytest.raises(sn.SnapshotCompletenessError, match="empty"):
        build_payload(elements=[])


def test_mc21_wrong_git_revision_rejected(tmp_path: Path) -> None:
    path = reload_payload(tmp_path, build_payload())
    with pytest.raises(sn.SnapshotValidationError, match="git_commit"):
        sn.load_snapshot(path, trusted=trusted(git_commit=OTHER_SHA), expectations=expectations())


def test_mc21_malformed_trusted_identity_rejected(tmp_path: Path) -> None:
    path = reload_payload(tmp_path, build_payload())
    with pytest.raises(ValueError, match="40-character"):
        sn.load_snapshot(path, trusted=trusted(git_commit="not-a-sha"), expectations=expectations())


def test_mc21_wrong_sysml_project_rejected(tmp_path: Path) -> None:
    path = reload_payload(tmp_path, build_payload())
    with pytest.raises(sn.SnapshotValidationError, match="sysml_project_id"):
        sn.load_snapshot(
            path, trusted=trusted(sysml_project_id="other-project"), expectations=expectations()
        )


def test_mc21_wrong_sysml_commit_rejected(tmp_path: Path) -> None:
    path = reload_payload(tmp_path, build_payload())
    with pytest.raises(sn.SnapshotValidationError, match="sysml_commit_id"):
        sn.load_snapshot(
            path, trusted=trusted(sysml_commit_id="other-commit"), expectations=expectations()
        )


def test_mc21_wrong_scope_rejected(tmp_path: Path) -> None:
    path = reload_payload(tmp_path, build_payload(semantic_binding=semantic_binding(scope="full-model")))
    with pytest.raises(sn.SnapshotValidationError, match="scope"):
        sn.load_snapshot(path, trusted=trusted(), expectations=expectations())


def test_mc21_wrong_evaluator_identity_rejected(tmp_path: Path) -> None:
    payload = build_payload(evaluator_binding={"build_id": "de4sdv.method-evaluator/999"})
    path = reload_payload(tmp_path, payload)
    with pytest.raises(sn.SnapshotValidationError, match="evaluator"):
        sn.load_snapshot(path, trusted=trusted(), expectations=expectations())


def test_mc21_wrong_method_identity_rejected(tmp_path: Path) -> None:
    binding = method_binding()
    binding["contract_digest"] = "d" * 64
    path = reload_payload(tmp_path, build_payload(method_binding=binding))
    with pytest.raises(sn.SnapshotValidationError, match="contract"):
        sn.load_snapshot(path, trusted=trusted(), expectations=expectations())


def test_mc21_wrong_policy_identity_rejected(tmp_path: Path) -> None:
    binding = method_binding()
    binding["policy_bundle_id"] = "de4sdv.acceptance.other.v9"
    path = reload_payload(tmp_path, build_payload(method_binding=binding))
    with pytest.raises(sn.SnapshotValidationError, match="policy"):
        sn.load_snapshot(path, trusted=trusted(), expectations=expectations())


def test_mc21_self_attested_provenance_rejected(tmp_path: Path) -> None:
    payload = build_payload()
    payload["provenance"]["kind"] = "self-attested"
    payload = sn.finalize_payload(payload)
    path = reload_payload(tmp_path, payload)
    with pytest.raises(sn.SnapshotValidationError, match="self-attested|trusted provenance"):
        sn.load_snapshot(path, trusted=trusted(), expectations=expectations())


def test_mc21_missing_trusted_record_rejected(tmp_path: Path) -> None:
    path = reload_payload(tmp_path, build_payload())
    with pytest.raises(sn.SnapshotValidationError, match="trusted"):
        sn.load_snapshot(path, trusted=None, expectations=expectations())


def test_mc21_validation_handle_digest_mismatch_rejected(tmp_path: Path) -> None:
    # The bundle carries its own claimed hashes; they must match the retained
    # validation record. A bundle cannot authorize itself.
    payload = build_payload(provenance=provenance(export_sha256="a" * 64))
    path = reload_payload(tmp_path, payload)
    with pytest.raises(sn.SnapshotValidationError, match="export_sha256"):
        sn.load_snapshot(path, trusted=trusted(), expectations=expectations())


def test_mc21_unknown_schema_rejected(tmp_path: Path) -> None:
    payload = build_payload()
    payload["schema"] = "de4sdv-method-snapshot/999"
    path = write_snapshot(tmp_path, payload)
    with pytest.raises(sn.SnapshotValidationError, match="schema"):
        sn.load_snapshot(path, trusted=trusted(), expectations=expectations())


def test_mc21_no_silent_latest_fallback(tmp_path: Path) -> None:
    """An invalid snapshot is refused by name; a valid newer snapshot in the
    same directory is never silently substituted, and loading stays
    revision-explicit."""
    good_payload = build_payload()
    good = reload_payload(tmp_path, good_payload, name="good.json")
    bad_payload = build_payload()
    bad_payload["integrity"]["elements_digest"] = "0" * 64
    bad = write_snapshot(tmp_path, bad_payload, name="bad.json")
    latest_payload = build_payload(
        semantic_binding=semantic_binding(git_commit=OTHER_SHA),
        provenance=provenance(git_commit=OTHER_SHA),
    )
    reload_payload(tmp_path, latest_payload, name="latest.json")

    with pytest.raises(sn.SnapshotIntegrityError, match="bad.json"):
        sn.load_snapshot(bad, trusted=trusted(), expectations=expectations())

    # The requested revision remains authoritative: loading `good.json` with
    # the matching trusted record returns exactly that revision, not the
    # "latest" one.
    loaded = sn.load_snapshot(
        good, trusted=trusted(good_payload), expectations=expectations()
    )
    assert loaded.revision.git_commit == REV_SHA
    assert loaded.revision.git_commit != OTHER_SHA


def test_mc21_root_coverage_required(tmp_path: Path) -> None:
    payload = build_payload()
    payload["file_sources"]["candidate"]["roots"] = ["somewhere/else"]
    payload = sn.finalize_payload(payload)
    path = reload_payload(tmp_path, payload)
    with pytest.raises(sn.SnapshotCompletenessError, match=mp.BENCH_ROOT):
        sn.load_snapshot(path, trusted=trusted(), expectations=expectations())


def test_mc21_tested_role_required_when_declared(tmp_path: Path) -> None:
    payload = build_payload()
    del payload["file_sources"]["tested"]
    payload = sn.finalize_payload(payload)
    path = reload_payload(tmp_path, payload)
    with pytest.raises(sn.SnapshotCompletenessError, match="tested"):
        sn.load_snapshot(path, trusted=trusted(), expectations=expectations())


def test_mc21_tested_revision_must_match_declared_head(tmp_path: Path) -> None:
    payload = build_payload()
    payload["file_sources"]["tested"]["revision"] = "3" * 40
    payload = sn.finalize_payload(payload)
    path = reload_payload(tmp_path, payload)
    with pytest.raises(sn.SnapshotValidationError, match="tested"):
        sn.load_snapshot(path, trusted=trusted(), expectations=expectations())


def test_mc21_wrong_scope_profiles_rejected(tmp_path: Path) -> None:
    binding = scope_binding()
    binding["profiles"] = list(reversed(PROFILES))
    path = reload_payload(tmp_path, build_payload(scope_binding=binding))
    with pytest.raises(sn.SnapshotValidationError, match="profiles"):
        sn.load_snapshot(path, trusted=trusted(), expectations=expectations())


def test_mc21_declared_key_mismatch_rejected(tmp_path: Path) -> None:
    path = reload_payload(
        tmp_path, build_payload(declared_evaluation_key="0" * 64)
    )
    with pytest.raises(sn.SnapshotIntegrityError, match="evaluation key"):
        sn.load_snapshot(
            path,
            trusted=trusted(),
            expectations=expectations(expected_evaluation_key="1" * 64),
        )


# ---------------------------------------------------------------------------
# SnapshotFileSource semantics (must mirror the live file source behavior)
# ---------------------------------------------------------------------------


def test_file_source_reads_and_completeness_semantics() -> None:
    source = sn.SnapshotFileSource(
        {"bench/a.txt": b"a", "bench/sub/b.txt": b"b", "docs/x.md": b"x"}
    )
    assert source.read_bytes("bench/a.txt") == b"a"
    assert source.read_bytes("bench/missing.txt") is None
    assert source.exists("bench/a.txt") is True
    assert source.exists("bench") is True  # directory with content
    assert source.exists("bench/none") is False
    assert source.list_files("bench") == ["bench/a.txt", "bench/sub/b.txt"]
    assert source.list_files("bench/sub") == ["bench/sub/b.txt"]
    assert source.list_files("absent") is None
    assert source.list_files("bench/a.txt") == ["bench/a.txt"]


# ---------------------------------------------------------------------------
# MC-28: remote unavailability never rewrites the historical result
# ---------------------------------------------------------------------------


def test_mc28_remote_unavailable_historical_result_unchanged(tmp_path: Path) -> None:
    candidate_dir = _write_tree(tmp_path / "candidate", candidate_files())
    _write_tree(tmp_path / "tested", _tested_files())
    snapshot_path = tmp_path / "snapshot.json"
    sn.write_snapshot(build_payload(), snapshot_path)

    _, before = _evaluate_snapshot(snapshot_path)

    # The remote source disappears entirely.
    import shutil

    shutil.rmtree(candidate_dir)

    availability = sn.source_availability(
        source_label="validated-api-revision",
        probe=lambda: candidate_dir.exists(),
        observed_at="2026-09-11T12:00:00+00:00",
    )
    assert availability["available"] is False
    assert availability["affects_historical_result"] is False

    _, after = _evaluate_snapshot(snapshot_path)
    assert after.evaluation_key == before.evaluation_key
    assert json.dumps(after.increment_status(), sort_keys=True) == json.dumps(
        before.increment_status(), sort_keys=True
    )


# ---------------------------------------------------------------------------
# MC-22 / MC-32: API/snapshot canonical parity through the real assembly
# ---------------------------------------------------------------------------


def _evaluate_snapshot(
    path: Path,
    *,
    trusted_binding: "sn.TrustedSnapshotBinding | None" = None,
    exp: "sn.SnapshotExpectations | None" = None,
):
    """Load one snapshot and run it through the SAME assembly + evaluator as
    the API transport (there is no snapshot-specific evaluator)."""
    raw = sn.read_snapshot(path)
    loaded = sn.load_snapshot(
        path,
        trusted=trusted_binding or trusted(raw),
        expectations=exp or expectations(),
    )
    approved = mp.load_approved_contract_from_yaml(
        ROOT / "docs/method-conformance/pilot-obligations.yaml"
    )
    assembly = mp.assemble_pilot_context(
        approved_contract=approved,
        elements=loaded.elements,
        revision=loaded.revision,
        candidate_source=loaded.sources["candidate"],
        tested_source=loaded.sources["tested"],
    )
    evaluation = me.MethodEvaluator(approved).evaluate(assembly.context)
    return loaded, evaluation


def _parity_pair(tmp_path: Path, *, git_commit: str = REV_SHA, scope: str = "candidate"):
    candidate_dir = _write_tree(tmp_path / "candidate", candidate_files())
    tested_dir = _write_tree(tmp_path / "tested", _tested_files())
    elements = mini_pilot_elements()
    payload = build_payload(
        semantic_binding=semantic_binding(git_commit=git_commit, scope=scope),
        provenance=provenance(git_commit=git_commit),
    )
    snapshot_path = tmp_path / "snapshot.json"
    sn.write_snapshot(payload, snapshot_path)

    approved = mp.load_approved_contract_from_yaml(
        ROOT / "docs/method-conformance/pilot-obligations.yaml"
    )
    revision = me.RevisionIdentity(
        git_commit=git_commit,
        sysml_project_id=PROJECT_ID,
        sysml_commit_id=SYSML_COMMIT,
        scope=scope,
    )
    api_assembly = mp.assemble_pilot_context(
        approved_contract=approved,
        elements=elements,
        revision=revision,
        candidate_source=mp.DirectoryFileSource(candidate_dir),
        tested_source=mp.DirectoryFileSource(tested_dir),
    )
    loaded = sn.load_snapshot(
        snapshot_path,
        trusted=trusted(payload, git_commit=git_commit),
        expectations=expectations(),
    )
    snapshot_assembly = mp.assemble_pilot_context(
        approved_contract=approved,
        elements=loaded.elements,
        revision=loaded.revision,
        candidate_source=loaded.sources["candidate"],
        tested_source=loaded.sources["tested"],
    )
    readiness = [
        me.ReadinessTarget(target_type="PHASE_EXIT", target_id=f"{mp.PILOT_SCOPE_RECORD}/phase10")
    ]
    api_evaluation = me.MethodEvaluator(approved).evaluate(
        api_assembly.context, requested_readiness=readiness
    )
    snapshot_evaluation = me.MethodEvaluator(approved).evaluate(
        snapshot_assembly.context, requested_readiness=readiness
    )
    return api_assembly, snapshot_assembly, api_evaluation, snapshot_evaluation


def test_mc22_api_snapshot_canonical_parity(tmp_path: Path) -> None:
    api_assembly, snapshot_assembly, api_eval, snap_eval = _parity_pair(tmp_path)
    assert api_assembly.diagnostics == snapshot_assembly.diagnostics
    assert api_assembly.closure_mismatches == snapshot_assembly.closure_mismatches
    assert api_eval.evaluation_key == snap_eval.evaluation_key
    assert json.dumps(api_eval.increment_status(), sort_keys=True) == json.dumps(
        snap_eval.increment_status(), sort_keys=True
    )
    assert api_eval.assessment_coverage == snap_eval.assessment_coverage
    assert api_eval.evaluation_state == snap_eval.evaluation_state
    assert api_eval.conformance_verdict == snap_eval.conformance_verdict
    assert api_eval.failed_ids == snap_eval.failed_ids
    assert api_eval.indeterminate_ids == snap_eval.indeterminate_ids
    assert api_eval.errored_ids == snap_eval.errored_ids
    assert api_eval.unassessed_ids == snap_eval.unassessed_ids
    assert [block.as_dict() for block in api_eval.readiness] == [
        block.as_dict() for block in snap_eval.readiness
    ]


def test_mc32_unmerged_candidate_api_snapshot_parity(tmp_path: Path) -> None:
    _, _, api_eval, snap_eval = _parity_pair(
        tmp_path, git_commit="5" * 40, scope="candidate"
    )
    assert api_eval.evaluation_key == snap_eval.evaluation_key
    payload = json.loads(json.dumps(snap_eval.increment_status(), sort_keys=True))
    assert payload["revision"]["git_commit"] == "5" * 40
    assert payload["revision"]["scope"] == "candidate"


def test_reordered_serialization_same_canonical_result(tmp_path: Path) -> None:
    payload = build_payload()
    path = reload_payload(tmp_path, payload, name="ordered.json")
    _, baseline = _evaluate_snapshot(path)

    permuted = build_payload()
    permuted["graph"]["elements"] = list(reversed(permuted["graph"]["elements"]))
    # Permute unordered file-map insertion order as well.
    role = permuted["file_sources"]["candidate"]
    role["files"] = dict(reversed(list(role["files"].items())))
    permuted["file_sources"]["tested"]["roots"] = list(
        reversed(permuted["file_sources"]["tested"]["roots"])
    )
    # The order-insensitive digests must be identical after permutation.
    assert permuted["integrity"]["elements_digest"] == payload["integrity"]["elements_digest"]
    path2 = reload_payload(tmp_path, permuted, name="permuted.json")
    _, twice = _evaluate_snapshot(path2)
    assert twice.evaluation_key == baseline.evaluation_key
    assert json.dumps(twice.increment_status(), sort_keys=True) == json.dumps(
        baseline.increment_status(), sort_keys=True
    )


# ---------------------------------------------------------------------------
# R1: externally trusted snapshot CONTENT binding
#
# The retained record externally binds the canonical content digest. An
# attacker who mutates content and recomputes every internal digest produces
# an internally self-consistent bundle that still cannot match the external
# binding — a bundle never authorizes its own contents.
# ---------------------------------------------------------------------------


def test_r1_missing_external_content_binding_refused(tmp_path: Path) -> None:
    payload = build_payload()
    path = reload_payload(tmp_path, payload)
    with pytest.raises(ValueError, match="expected_payload_digest"):
        sn.load_snapshot(
            path,
            trusted=trusted(payload, expected_payload_digest=""),
            expectations=expectations(),
        )


def test_r1_element_mutation_with_reforged_digests_refused(tmp_path: Path) -> None:
    payload = build_payload()
    binding = trusted(payload)
    forged = json.loads(json.dumps(payload))
    forged["graph"]["elements"][3]["declaredName"] = "TamperedElement"
    forged = sn.finalize_payload(forged)
    path = write_snapshot(tmp_path, forged)
    with pytest.raises(sn.SnapshotValidationError, match="expected_payload_digest"):
        sn.load_snapshot(path, trusted=binding, expectations=expectations())


def test_r1_candidate_file_mutation_with_reforged_digests_refused(
    tmp_path: Path,
) -> None:
    payload = build_payload()
    binding = trusted(payload)
    forged = json.loads(json.dumps(payload))
    entry = forged["file_sources"]["candidate"]
    first = sorted(entry["files"])[0]
    entry["files"][first]["content_b64"] = base64.b64encode(
        b"tampered-candidate-content"
    ).decode()
    forged = _reforge(forged)
    path = write_snapshot(tmp_path, forged)
    with pytest.raises(sn.SnapshotValidationError, match="expected_payload_digest"):
        sn.load_snapshot(path, trusted=binding, expectations=expectations())


def test_r1_tested_source_mutation_with_reforged_digests_refused(
    tmp_path: Path,
) -> None:
    payload = build_payload()
    binding = trusted(payload)
    forged = json.loads(json.dumps(payload))
    entry = forged["file_sources"]["tested"]
    first = sorted(entry["files"])[0]
    entry["files"][first]["content_b64"] = base64.b64encode(
        b"tampered-tested-content"
    ).decode()
    forged = _reforge(forged)
    path = write_snapshot(tmp_path, forged)
    with pytest.raises(sn.SnapshotValidationError, match="expected_payload_digest"):
        sn.load_snapshot(path, trusted=binding, expectations=expectations())


def test_r1_copied_handle_into_foreign_payload_refused(tmp_path: Path) -> None:
    """The provenance handle is copied verbatim into a different, internally
    self-consistent payload; only the external content binding can refuse it."""
    payload = build_payload()
    binding = trusted(payload)
    forged = json.loads(json.dumps(payload))
    forged["graph"]["elements"] = list(reversed(forged["graph"]["elements"]))
    forged["graph"]["elements"][0]["declaredName"] = "ForeignPayload"
    forged = sn.finalize_payload(forged)
    assert forged["provenance"] == payload["provenance"]  # handle copied
    path = write_snapshot(tmp_path, forged)
    with pytest.raises(sn.SnapshotValidationError, match="expected_payload_digest"):
        sn.load_snapshot(path, trusted=binding, expectations=expectations())


def test_r1_stored_value_spoof_cannot_satisfy_external_binding(
    tmp_path: Path,
) -> None:
    """Setting the snapshot's stored payload digest to the externally trusted
    value does not help: the loader recomputes from contents, so the spoofed
    stored value no longer matches the recomputation, and the external binding
    is still unsatisfied."""
    payload = build_payload()
    binding = trusted(payload)
    forged = json.loads(json.dumps(payload))
    forged["graph"]["elements"][0]["declaredName"] = "SpoofedElement"
    forged = sn.finalize_payload(forged)
    forged["integrity"]["payload_digest"] = binding.expected_payload_digest
    path = write_snapshot(tmp_path, forged)
    with pytest.raises(sn.SnapshotError, match="payload_digest"):
        sn.load_snapshot(path, trusted=binding, expectations=expectations())


def test_r1_external_section_digest_bindings_enforced(tmp_path: Path) -> None:
    """The optional externally trusted section digests are enforced too."""
    payload = build_payload()
    path = reload_payload(tmp_path, payload)
    binding = trusted(
        payload,
        expected_elements_digest="0" * 64,
    )
    with pytest.raises(sn.SnapshotValidationError, match="expected_elements_digest"):
        sn.load_snapshot(path, trusted=binding, expectations=expectations())
