"""Tests for the v1.1-round bounded fixes:

- isolated exact-SHA candidate export production (real path, distinct artifacts);
- MC-14 independent-transaction correspondence fail-closed behavior;
- per-usage VerificationCase library grounding from the actual relationship
  representation (not library-definition presence).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from de4sdv.semantic.relationships import build_relationship_graph


# ---------------------------------------------------------------------------
# Isolated candidate export (B-R3 real path)
# ---------------------------------------------------------------------------

def _synthetic_repo(path: Path) -> tuple[Path, str]:
    repo = path / "synthetic-repo"
    repo.mkdir()
    (repo / "textual-notation-of-model").mkdir()
    (repo / "textual-notation-of-model" / "a.sysml").write_text(
        "package P { }\n"
    )
    (repo / "sysand-lock.toml").write_text("# pinned lock\n")
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "c1"],
        check=True,
    )
    sha = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()
    return repo, sha


def test_candidate_export_runs_serializer_from_isolated_checkout(tmp_path, monkeypatch):
    """The export is produced from the isolated checkout's serializer, with a
    transaction identity and a distinct artifact path."""
    import scripts.prepare_candidate_export as pce

    repo, sha = _synthetic_repo(tmp_path)

    calls: list[dict] = []

    def fake_serializer(checkout: Path, git_commit: str, output: Path) -> None:
        calls.append({"checkout": checkout, "commit": git_commit, "output": output})
        # Prove the serializer ran against the ISOLATED checkout: it sees the
        # isolated tree, not the origin working tree.
        assert (checkout / "textual-notation-of-model" / "a.sysml").is_file()
        output.write_text(
            json.dumps(
                {
                    "schema": "de4sdv-sysml-api-baseline-export/v1",
                    "git_commit": git_commit,
                    "elements": [{"@id": "00000000-0000-4000-8000-000000000001", "@type": "Package", "declaredName": "P"}],
                    "source_manifest": [],
                }
            )
            + "\n"
        )

    monkeypatch.setattr(pce, "_run_serializer", fake_serializer)
    monkeypatch.setattr(pce, "_sync_dependencies", lambda checkout: None)

    identity = pce.prepare_candidate_export(
        repo,
        sha,
        tmp_path / "iso",
        tmp_path / "cand.json",
        tmp_path / "cand-identity.json",
    )
    assert len(calls) == 1
    assert calls[0]["checkout"] == tmp_path / "iso"
    assert calls[0]["commit"] == sha
    assert identity["git_commit"] == sha
    assert identity["transaction_label"] == "candidate-1"
    assert identity["element_count"] == 1
    assert identity["export_sha256"]


def test_candidate_export_two_transactions_same_source(tmp_path, monkeypatch):
    """MC-14 transactions: same checkout, two independent serializer runs, two
    distinct artifacts + transaction identities."""
    import scripts.prepare_candidate_export as pce

    repo, sha = _synthetic_repo(tmp_path)
    serial = [0]

    def fake_serializer(checkout: Path, git_commit: str, output: Path) -> None:
        serial[0] += 1
        output.write_text(
            json.dumps(
                {
                    "schema": "de4sdv-sysml-api-baseline-export/v1",
                    "git_commit": git_commit,
                    "elements": [
                        {"@id": f"00000000-0000-4000-8000-{serial[0]:012d}", "@type": "Package", "declaredName": "P"}
                    ],
                    "source_manifest": [],
                }
            )
            + "\n"
        )

    monkeypatch.setattr(pce, "_run_serializer", fake_serializer)
    monkeypatch.setattr(pce, "_sync_dependencies", lambda checkout: None)

    worktree = tmp_path / "iso"
    first = pce.prepare_candidate_export(
        repo, sha, worktree, tmp_path / "c1.json", tmp_path / "i1.json",
        transaction_label="candidate-1",
    )
    second = pce.prepare_candidate_export(
        repo, sha, worktree, tmp_path / "c2.json", tmp_path / "i2.json",
        transaction_label="candidate-2", reuse_checkout=True,
        comparison_export=tmp_path / "c1.json",
    )
    assert (tmp_path / "c1.json").read_bytes() != (tmp_path / "c2.json").read_bytes()
    assert first["transaction_id"] != second["transaction_id"]
    assert second["candidate_export_equals_comparison_bytes"] is False


def test_candidate_export_rejects_wrong_commit_export(tmp_path, monkeypatch):
    import scripts.prepare_candidate_export as pce

    repo, sha = _synthetic_repo(tmp_path)

    def fake_serializer(checkout: Path, git_commit: str, output: Path) -> None:
        output.write_text(
            json.dumps(
                {
                    "schema": "de4sdv-sysml-api-baseline-export/v1",
                    "git_commit": "f" * 40,
                    "elements": [{"@id": "00000000-0000-4000-8000-000000000001"}],
                }
            )
        )

    monkeypatch.setattr(pce, "_run_serializer", fake_serializer)
    monkeypatch.setattr(pce, "_sync_dependencies", lambda checkout: None)
    with pytest.raises(RuntimeError, match="declares commit"):
        pce.prepare_candidate_export(
            repo, sha, tmp_path / "iso", tmp_path / "c.json", tmp_path / "i.json"
        )




def test_prepare_candidate_export_cli_accepts_workflow_flags(tmp_path):
    """The exact CLI invocations used by the privileged workflow must work end
    to end (a run died at argparse-equivalent wiring before; function-level
    tests alone do not cover the flags the workflow passes).

    Both transactions are exercised through subprocess with a stub serializer
    committed in the synthetic repository, mirroring CI: transaction 1 creates
    the isolated worktree, transaction 2 reuses it with --sync-deps=false.
    """
    repo, sha = _synthetic_repo(tmp_path)
    # Stub the licensed serializer inside the synthetic repository. The
    # realistic path: the isolated checkout's own export script is invoked.
    serial_dir = repo / "scripts"
    serial_dir.mkdir()
    (serial_dir / "export_sysml_api_baseline.py").write_text(
        "import json, sys\n"
        "args = sys.argv\n"
        "git_commit = args[args.index('--git-commit') + 1]\n"
        "output = args[args.index('--output') + 1]\n"
        "payload = {\n"
        "    'schema': 'de4sdv-sysml-api-baseline-export/v1',\n"
        "    'git_commit': git_commit,\n"
        "    'elements': [{'@id': '00000000-0000-4000-8000-000000000001',"
        " '@type': 'Package', 'declaredName': 'P'}],\n"
        "    'source_manifest': [],\n"
        "}\n"
        "open(output, 'w').write(json.dumps(payload) + '\\n')\n"
    )
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t",
         "commit", "-qm", "stub serializer"],
        check=True,
    )
    sha = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()

    import scripts.prepare_candidate_export as pce

    worktree = tmp_path / "iso"
    cmd1 = [
        "python3", str(pce.__file__),
        "--repository", str(repo),
        "--git-commit", sha,
        "--worktree", str(worktree),
        "--output", str(tmp_path / "c1.json"),
        "--identity", str(tmp_path / "i1.json"),
        "--transaction-label", "candidate-1",
        "--sync-deps=false",
        "--baseline-export", str(repo / "missing-baseline.json"),
    ]
    result1 = subprocess.run(cmd1, capture_output=True, text=True)
    assert result1.returncode == 0, result1.stderr
    cmd2 = [
        "python3", str(pce.__file__),
        "--repository", str(repo),
        "--git-commit", sha,
        "--worktree", str(worktree),
        "--output", str(tmp_path / "c2.json"),
        "--identity", str(tmp_path / "i2.json"),
        "--transaction-label", "candidate-2",
        "--reuse-checkout",
        "--sync-deps=false",
    ]
    result2 = subprocess.run(cmd2, capture_output=True, text=True)
    assert result2.returncode == 0, result2.stderr
    identity2 = json.loads((tmp_path / "i2.json").read_text())
    assert identity2["transaction_label"] == "candidate-2"
    assert identity2["git_commit"] == sha
    assert identity2["source_checkout_head"] == sha
    # Transaction 1 identity also recorded, with baseline comparison handled.
    identity1 = json.loads((tmp_path / "i1.json").read_text())
    assert identity1["transaction_label"] == "candidate-1"


# ---------------------------------------------------------------------------
# MC-14 correspondence script (fail-closed)
# ---------------------------------------------------------------------------

def _binding(tmp_path: Path, project_id: str, commit_id: str, sha: str) -> Path:
    payload = {
        "git_repository": "de4sdv/DE4SDV",
        "git_commit": sha,
        "sysml_project_id": project_id,
        "sysml_commit_id": commit_id,
        "import_timestamp": "2026-09-10T00:00:00+00:00",
        "import_tool_version": "de4sdv-full-model-import/1+official-syside-json",
        "semantic_validation": "passed",
        "ontology": {"path": "approach/framework/ontology/de4sdv-basic-ontology.yaml", "sha256": "a" * 64},
        "scope": "candidate",
    }
    path = tmp_path / f"binding-{project_id[:8]}.json"
    path.write_text(json.dumps(payload))
    return path


class _FakeRepository:
    def __init__(self, elements_by_project: dict[str, list[dict]]):
        self._elements = elements_by_project

    def list_elements(self, project_id: str, commit_id: str) -> list[dict]:
        return list(self._elements.get(project_id, []))


def test_correspondence_two_independent_transactions_uuids_differ(tmp_path, monkeypatch):
    import scripts.verify_reimport_correspondence as vrc

    sha = "a" * 40
    # Same explicit identities, DIFFERENT serializer UUIDs, same relationships.
    elements_a = [
        {"@id": "11111111-0000-4000-8000-000000000001", "@type": "VerificationCaseUsage", "declaredShortName": "VC-AEBS-009D-01", "declaredName": "overrideVerification01"},
        {"@id": "11111111-0000-4000-8000-000000000002", "@type": "VerificationCaseDefinition", "declaredShortName": "VC-AEBS-009D-DE", "declaredName": "ConsciousOverrideVerification"},
        {"@id": "11111111-0000-4000-8000-000000000003", "@type": "Subclassification", "subclassifier": {"@id": "11111111-0000-4000-8000-000000000001"}, "superclassifier": {"@id": "11111111-0000-4000-8000-000000000002"}},
    ]
    elements_b = [
        {"@id": "22222222-0000-4000-8000-000000000001", "@type": "VerificationCaseUsage", "declaredShortName": "VC-AEBS-009D-01", "declaredName": "overrideVerification01"},
        {"@id": "22222222-0000-4000-8000-000000000002", "@type": "VerificationCaseDefinition", "declaredShortName": "VC-AEBS-009D-DE", "declaredName": "ConsciousOverrideVerification"},
        {"@id": "22222222-0000-4000-8000-000000000003", "@type": "Subclassification", "subclassifier": {"@id": "22222222-0000-4000-8000-000000000001"}, "superclassifier": {"@id": "22222222-0000-4000-8000-000000000002"}},
    ]
    monkeypatch.setattr(
        vrc, "SysMLRepository",
        lambda client: _FakeRepository({"proj-a": elements_a, "proj-b": elements_b}),
    )
    monkeypatch.setattr(vrc, "ApiClient", lambda url, timeout=600.0: None)

    binding_a = _binding(tmp_path, "proj-a", "commit-a", sha)
    binding_b = _binding(tmp_path, "proj-b", "commit-b", sha)
    report = vrc.verify(
        "http://x", binding_a, binding_b,
        required_identities=("VC-AEBS-009D-DE", "VC-AEBS-009D-01"),
    )
    assert report["passed"] is True
    assert report["uuid_attribution"]["identical_uuids"] == 0
    assert report["uuid_attribution"]["differing_uuids"] == 2
    assert report["correspondence"]["uuid_reuse_assumed"] is False
    # Zero name-based identity correspondence.
    assert report["correspondence"]["name_based_correspondence_used"] is False
    assert report["correspondence"]["declared_name_used_as_identity_key"] is False
    assert report["correspondence"]["persistent_identity_field"] == "declaredShortName"
    assert report["semantic_witness_equivalence"]["mismatched"] == 0
    assert report["identities_compared"] == 2
    by_id = {row["identity"]: row for row in report["per_identity"]}
    assert by_id["VC-AEBS-009D-01"]["relationships_match"] is True
    uuids = by_id["VC-AEBS-009D-01"]["uuid_by_transaction"]
    assert list(uuids.values())[0] != list(uuids.values())[1]
    assert set(uuids) == {"transaction-a", "transaction-b"}


def test_correspondence_fails_on_relationship_mismatch(tmp_path, monkeypatch):
    import scripts.verify_reimport_correspondence as vrc

    sha = "b" * 40
    elements_a = [
        {"@id": "11111111-0000-4000-8000-000000000001", "@type": "VerificationCaseUsage", "declaredShortName": "VC-AEBS-009D-01", "declaredName": "v1"},
        {"@id": "11111111-0000-4000-8000-000000000002", "@type": "VerificationCaseDefinition", "declaredShortName": "VC-AEBS-009D-DE", "declaredName": "d"},
        {"@id": "11111111-0000-4000-8000-000000000003", "@type": "Subclassification", "subclassifier": {"@id": "11111111-0000-4000-8000-000000000001"}, "superclassifier": {"@id": "11111111-0000-4000-8000-000000000002"}},
    ]
    # Transaction B: same identities but the usage lost its definition edge.
    elements_b = [
        {"@id": "22222222-0000-4000-8000-000000000001", "@type": "VerificationCaseUsage", "declaredShortName": "VC-AEBS-009D-01", "declaredName": "v1"},
        {"@id": "22222222-0000-4000-8000-000000000002", "@type": "VerificationCaseDefinition", "declaredShortName": "VC-AEBS-009D-DE", "declaredName": "d"},
    ]
    monkeypatch.setattr(
        vrc, "SysMLRepository",
        lambda client: _FakeRepository({"proj-a": elements_a, "proj-b": elements_b}),
    )
    monkeypatch.setattr(vrc, "ApiClient", lambda url, timeout=600.0: None)
    report = vrc.verify(
        "http://x", _binding(tmp_path, "proj-a", "commit-a", sha), _binding(tmp_path, "proj-b", "commit-b", sha),
        required_identities=("VC-AEBS-009D-DE", "VC-AEBS-009D-01"),
    )
    assert report["passed"] is False
    assert "VC-AEBS-009D-01" in report["relationship_mismatches"]


def test_correspondence_fails_on_duplicate_identity(tmp_path, monkeypatch):
    import scripts.verify_reimport_correspondence as vrc

    sha = "c" * 40
    elements = [
        {"@id": "11111111-0000-4000-8000-000000000001", "@type": "VerificationCaseUsage", "declaredShortName": "VC-AEBS-009D-01", "declaredName": "v1"},
        {"@id": "11111111-0000-4000-8000-000000000002", "@type": "VerificationCaseUsage", "declaredShortName": "VC-AEBS-009D-01", "declaredName": "v1-duplicate"},
    ]
    monkeypatch.setattr(
        vrc, "SysMLRepository",
        lambda client: _FakeRepository({"proj-a": elements, "proj-b": elements}),
    )
    monkeypatch.setattr(vrc, "ApiClient", lambda url, timeout=600.0: None)
    report = vrc.verify(
        "http://x", _binding(tmp_path, "proj-a", "commit-a", sha), _binding(tmp_path, "proj-b", "commit-b", sha),
        required_identities=(),
    )
    assert report["passed"] is False
    assert any("duplicate persistent identity" in failure for failure in report["failures"])


def test_correspondence_rejects_same_project_commit(tmp_path, monkeypatch):
    import scripts.verify_reimport_correspondence as vrc

    sha = "d" * 40
    elements = [
        {"@id": "11111111-0000-4000-8000-000000000001", "@type": "Package", "declaredName": "P"},
    ]
    monkeypatch.setattr(
        vrc, "SysMLRepository",
        lambda client: _FakeRepository({"proj-a": elements}),
    )
    monkeypatch.setattr(vrc, "ApiClient", lambda url, timeout=600.0: None)
    same = _binding(tmp_path, "proj-a", "commit-a", sha)
    report = vrc.verify("http://x", same, same, required_identities=())
    assert report["passed"] is False
    assert any("not independent transactions" in failure for failure in report["failures"])




def test_correspondence_never_merges_by_declared_name(tmp_path, monkeypatch):
    """Two different elements that share ONLY a declared name (no persistent
    identity on either side) are NOT corresponded."""
    import scripts.verify_reimport_correspondence as vrc

    sha = "e" * 40
    elements_a = [
        {"@id": "11111111-0000-4000-8000-000000000001", "@type": "PartUsage", "declaredName": "sharedName"},
    ]
    elements_b = [
        {"@id": "22222222-0000-4000-8000-000000000001", "@type": "PartUsage", "declaredName": "sharedName"},
    ]
    monkeypatch.setattr(
        vrc, "SysMLRepository",
        lambda client: _FakeRepository({"proj-a": elements_a, "proj-b": elements_b}),
    )
    monkeypatch.setattr(vrc, "ApiClient", lambda url, timeout=600.0: None)
    report = vrc.verify(
        "http://x",
        _binding(tmp_path, "proj-a", "commit-a", sha),
        _binding(tmp_path, "proj-b", "commit-b", sha),
        required_identities=(),
    )
    assert report["identities_compared"] == 0
    assert report["per_identity"] == []
    assert report["correspondence"]["name_based_correspondence_used"] is False
    assert report["transactions"]["transaction-a"]["elements_without_persistent_identity"] == 1
    assert report["transactions"]["transaction-b"]["elements_without_persistent_identity"] == 1


def test_name_only_element_never_becomes_correspondence(tmp_path, monkeypatch):
    """An element WITHOUT a persistent identity cannot become cross-transaction
    correspondence merely because declaredName matches the other side's name."""
    import scripts.verify_reimport_correspondence as vrc

    sha = "f" * 40
    elements_a = [
        {
            "@id": "11111111-0000-4000-8000-000000000001",
            "@type": "VerificationCaseUsage",
            "declaredShortName": "VC-AEBS-009D-01",
            "declaredName": "overrideVerification01",
        },
    ]
    elements_b = [
        # Same DECLARED NAME, but this is a different element with no
        # persistent identity: it must not be corresponded to the identified
        # element in transaction A.
        {"@id": "22222222-0000-4000-8000-000000000009", "@type": "VerificationCaseUsage", "declaredName": "overrideVerification01"},
    ]
    monkeypatch.setattr(
        vrc, "SysMLRepository",
        lambda client: _FakeRepository({"proj-a": elements_a, "proj-b": elements_b}),
    )
    monkeypatch.setattr(vrc, "ApiClient", lambda url, timeout=600.0: None)
    report = vrc.verify(
        "http://x",
        _binding(tmp_path, "proj-a", "commit-a", sha),
        _binding(tmp_path, "proj-b", "commit-b", sha),
        required_identities=(),
    )
    # Fail closed: the persistent identity is missing on the B side and is
    # never silently recovered by name.
    assert report["passed"] is False
    assert any(
        "present only in transaction-a" in failure for failure in report["failures"]
    )
    assert all(row["identity"] != "overrideVerification01" for row in report["per_identity"])
    assert report["correspondence"]["name_based_correspondence_used"] is False
    assert report["transactions"]["transaction-b"]["elements_without_persistent_identity"] == 1


# ---------------------------------------------------------------------------
# Per-usage library grounding# Per-usage library grounding (representation-tolerant, fail-closed) —
# exercised end-to-end through verify_pilot_readback.main() against a synthetic
# import that satisfies every read-back section.
# ---------------------------------------------------------------------------

from test_method_contract_binding import _pilot_graph  # noqa: E402

PILOT_BINDING = {
    "git_repository": "de4sdv/DE4SDV",
    "git_commit": "e" * 40,
    "sysml_project_id": "proj-pilot",
    "sysml_commit_id": "commit-pilot",
    "import_timestamp": "2026-09-10T00:00:00+00:00",
    "import_tool_version": "de4sdv-full-model-import/1+official-syside-json",
    "semantic_validation": "passed",
    "ontology": {
        "path": "approach/framework/ontology/de4sdv-basic-ontology.yaml",
        "sha256": "a" * 64,
    },
    "scope": "candidate",
}


class _FakeRepository:
    def __init__(self, elements_by_project):
        self._elements = elements_by_project

    def list_elements(self, project_id, commit_id):
        return list(self._elements.get(project_id, []))


def _full_pilot_import():
    """Synthetic validated import satisfying every read-back section, with
    library grounding carried by Subclassification/FeatureTyping edges."""
    elements = _pilot_graph()
    lib_def = "99999999-0000-4000-8000-00000000000a"
    lib_usage_set = "99999999-0000-4000-8000-00000000000b"
    definition_id = "00000000-0000-4000-8000-0000000000d0"
    elements.extend(
        [
            {
                "@id": lib_def,
                "@type": "Class",
                "declaredName": "VerificationCase",
            },
            {
                "@id": lib_usage_set,
                "@type": "ItemUsage",
                "declaredName": "verificationCases",
            },
            {
                "@id": "99999999-0000-4000-8000-00000000000c",
                "@type": "FeatureTyping",
                "typedFeature": {"@id": lib_usage_set},
                "type": {"@id": lib_def},
            },
            # Definition grounds into the library definition.
            {
                "@id": "99999999-0000-4000-8000-00000000000d",
                "@type": "Subclassification",
                "subclassifier": {"@id": definition_id},
                "superclassifier": {"@id": lib_def},
            },
            # Scope record with actual field values (B-R4): a PartUsage
            # carrying owned attribute usages (the model-resident shape).
            {
                "@id": "00000000-0000-4000-8000-000000000600",
                "@type": "PartUsage",
                "declaredName": "aebsOverridePilotScope",
                "declaredShortName": "PSC-009D",
                "ownedElement": [
                    {
                        "@id": "00000000-0000-4000-8000-000000000601",
                        "@type": "AttributeUsage",
                        "declaredName": "incrementId",
                        "ownedElement": [
                            {"@type": "LiteralString", "value": "INC-AEBS-009D"}
                        ],
                    },
                    {
                        "@id": "00000000-0000-4000-8000-000000000602",
                        "@type": "AttributeUsage",
                        "declaredName": "subjectType",
                        "ownedElement": [
                            {"@type": "LiteralString", "value": "VerificationCaseUsage"}
                        ],
                    },
                ],
            },
        ]
    )
    # Six model-resident evaluation-scope memberships (B-R5 shape).
    for index in range(1, 7):
        elements.append(
            {
                "@id": f"00000000-0000-4000-8000-0000000007{index:02d}",
                "@type": "ItemUsage",
                "declaredName": f"scopeMember{index:02d}",
                "ownedElement": [
                    {
                        "@type": "AttributeUsage",
                        "declaredName": "scopeId",
                        "ownedElement": [{"@type": "LiteralString", "value": "PSC-009D"}],
                    },
                    {
                        "@type": "AttributeUsage",
                        "declaredName": "subjectId",
                        "ownedElement": [
                            {"@type": "LiteralString", "value": f"VC-AEBS-009D-{index:02d}"}
                        ],
                    },
                    {
                        "@type": "AttributeUsage",
                        "declaredName": "contributes",
                        "ownedElement": [{"@type": "LiteralBoolean", "value": False}],
                    },
                ],
            }
        )
    # Eleven model-resident obligations (B-R6 shape; required + phase pinned).
    obligation_ids = [
        "PC-009D-SCOPE-POPULATION", "PC-009D-VC-BINDING",
        "PC-009D-SUBJECT-MEMBERSHIP", "PC-009D-OBJECTIVE-CONTRACTS",
        "PC-009D-USAGE-METHOD-METADATA", "PC-009D-DEFINITION-METHOD-METADATA",
        "PC-009D-PROFILE-POPULATION", "PC-009D-EXECUTION-RECORD",
        "PC-009D-EXECUTION-OUTCOME", "PC-009D-SCOPE-EQUALITY",
        "PC-009D-ACCEPTANCE-AUTHORITY",
    ]
    for index, obligation_id in enumerate(obligation_ids):
        elements.append(
            {
                "@id": f"00000000-0000-4000-8000-0000000008{index:02d}",
                "@type": "ItemUsage",
                "declaredName": f"obligation{index:02d}",
                "ownedElement": [
                    {
                        "@type": "AttributeUsage",
                        "declaredName": "obligationId",
                        "ownedElement": [{"@type": "LiteralString", "value": obligation_id}],
                    },
                    {
                        "@type": "AttributeUsage",
                        "declaredName": "required",
                        "ownedElement": [{"@type": "LiteralBoolean", "value": True}],
                    },
                    {
                        "@type": "AttributeUsage",
                        "declaredName": "phase",
                        "ownedElement": [
                            {"@type": "LiteralString", "value": "phase10_vvEvidence"}
                        ],
                    },
                ],
            }
        )
    return elements



def _run_readback(monkeypatch, tmp_path, elements):
    import sys

    import scripts.verify_pilot_readback as vpr

    monkeypatch.setattr(
        vpr, "SysMLRepository",
        lambda client: _FakeRepository({"proj-pilot": elements}),
    )
    monkeypatch.setattr(vpr, "ApiClient", lambda url, timeout=600.0: None)
    binding_path = tmp_path / "binding.json"
    binding_path.write_text(json.dumps(PILOT_BINDING))
    out = tmp_path / "readback.json"
    monkeypatch.setattr(
        sys, "argv",
        ["verify_pilot_readback.py", "--api-url", "http://x",
         "--binding", str(binding_path), "--output", str(out)],
    )
    exit_code = None
    try:
        exit_code = vpr.main()
    except SystemExit as exc:
        exit_code = exc.code
    return out, exit_code


def test_usage_grounding_proven_per_usage(tmp_path, monkeypatch):
    out, _ = _run_readback(monkeypatch, tmp_path, _full_pilot_import())
    report = json.loads(out.read_text())
    grounding = report["usage_grounding"]["VC-AEBS-009D-01"]
    assert grounding["completeness"] == "complete"
    assert grounding["definition_witness"]["target"] == (
        "00000000-0000-4000-8000-0000000000d0"
    )
    assert grounding["library_grounding_witness"]["target"] == (
        "99999999-0000-4000-8000-00000000000a"
    )
    assert grounding["library_usage_anchor_witness"]["anchor_metaclass"] == "ItemUsage"
    assert report["definition_grounding"]["library_grounding_witness"]["target"] == (
        "99999999-0000-4000-8000-00000000000a"
    )
    assert report["passed"] is True


def test_usage_grounding_fails_when_library_def_present_but_unreachable(tmp_path, monkeypatch):
    """Library definition PRESENT but no specialization closure: read-back
    must fail — mere presence is not grounding proof."""
    elements = _full_pilot_import()
    elements = [
        element
        for element in elements
        if element.get("@id") != "99999999-0000-4000-8000-00000000000d"
    ]
    out, exit_code = _run_readback(monkeypatch, tmp_path, elements)
    report = json.loads(out.read_text())
    assert report["passed"] is False
    assert exit_code == 1
    assert any(
        "VerificationCases::VerificationCase" in failure
        for failure in report["failures"]
    )


def test_usage_grounding_fails_when_usage_edge_missing(tmp_path, monkeypatch):
    """A usage without its definition relationship fails per-usage grounding
    even though the definition itself grounds."""
    elements = _full_pilot_import()
    elements = [
        element
        for element in elements
        if element.get("@id") != "00000000-0000-4000-8000-0000000000g1"
    ]
    out, exit_code = _run_readback(monkeypatch, tmp_path, elements)
    report = json.loads(out.read_text())
    assert report["passed"] is False
    grounding = report["usage_grounding"]["VC-AEBS-009D-01"]
    assert grounding["completeness"] == "incomplete"
    assert any("no relationship edge" in d for d in grounding["diagnostics"])


def test_relationship_graph_discovers_inline_typing_representation():
    """The graph must not hard-code Generalization: an inlined FeatureTyping
    property representation produces the same edge with implied provenance."""
    elements = [
        {"@id": "a", "@type": "VerificationCaseUsage", "declaredType": {"@id": "d"}},
        {"@id": "d", "@type": "VerificationCaseDefinition"},
    ]
    graph = build_relationship_graph(elements)
    hops = graph.outgoing("a")
    assert any(hop.target == "d" and hop.kind == "declaredType" for hop in hops)
