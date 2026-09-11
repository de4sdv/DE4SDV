"""Runner-level MC-11 regressions for the production method-conformance runner.

The runner must establish ONE exact candidate identity before assembling any
evaluation context: the evaluated candidate revision, the validated candidate
binding's Git commit, and the candidate export's Git commit must be the same
exact Git SHA. Anything else refuses fail-closed, and a binding/integrity
refusal is an error condition — never PASS, FAIL, or INDETERMINATE.

Git-identical subtrees at two different SHAs are diagnostic provenance only;
they never authorize evaluating one Git revision with another revision's API
binding.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import scripts.run_method_conformance as rmc
from de4sdv.semantic import method_pilot as mp

ROOT = Path(__file__).resolve().parents[1]

SHA_A = "1" * 40
SHA_B = "2" * 40

#: Keys that only exist when an evaluation actually ran. A refusal must carry
#: none of them: no evaluation key, no verdict, no readiness, no projections.
EVALUATION_KEYS = (
    "evaluation_key",
    "disposition",
    "conformance_verdict",
    "evaluation_state",
    "assessment_coverage",
    "readiness",
    "increment_status",
    "method_gaps",
    "next_obligation",
    "phase_contract",
    "evaluated_revision",
)


def _binding(**overrides) -> dict:
    body = {
        "git_commit": SHA_A,
        "git_repository": "de4sdv/DE4SDV",
        "sysml_project_id": "proj-1",
        "sysml_commit_id": "commit-1",
        "scope": "candidate",
        "ontology": {"path": "o.yaml", "sha256": "f" * 64},
        "semantic_validation": "passed",
        "kernel_bindings": [],
    }
    body.update(overrides)
    return body


def _export(**overrides) -> dict:
    body = {
        "schema": "de4sdv-sysml-api-baseline-export/v1",
        "git_commit": SHA_A,
        "element_sources": {},
        "library_anchors": [],
        "elements": [],
    }
    body.update(overrides)
    return body


def _write(tmp_path: Path, name: str, payload: dict) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload))
    return path


def _git(repo: Path, *args: str) -> str:
    probe = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    )
    return probe.stdout.strip()


def _init_repo_with_two_identical_subtrees(tmp_path: Path) -> tuple[Path, str, str]:
    """Two commits whose governed subtrees are content-identical.

    Commit B changes only an unrelated file, so the SysML/bench subtrees are
    Git-identical across A and B — exactly the tempting-but-illegal case.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "--quiet")
    _git(repo, "config", "user.email", "t@example.invalid")
    _git(repo, "config", "user.name", "t")
    governed = repo / "textual-notation-of-model"
    governed.mkdir()
    (governed / "model.sysml").write_text("package P { }\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "A")
    sha_a = _git(repo, "rev-parse", "HEAD")
    (repo / "unrelated.txt").write_text("churn\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "B")
    sha_b = _git(repo, "rev-parse", "HEAD")
    return repo, sha_a, sha_b


# ---------------------------------------------------------------------------
# 1. binding Git SHA != export Git SHA -> refused, no disposition emitted
# ---------------------------------------------------------------------------


def test_binding_and_export_revision_mismatch_refuses() -> None:
    identity, diagnostics = mp.establish_candidate_identity(
        binding=_binding(git_commit=SHA_A), export=_export(git_commit=SHA_B)
    )
    assert identity is None
    joined = " ".join(diagnostics)
    assert "different Git/API identity: refusing the mismatched evaluation" in joined
    assert "git_commit" in joined


def test_runner_refuses_binding_export_mismatch_without_disposition(tmp_path: Path) -> None:
    binding = _write(tmp_path, "binding.json", _binding(git_commit=SHA_A))
    export = _write(tmp_path, "export.json", _export(git_commit=SHA_B))
    output = tmp_path / "report.json"

    exit_code = rmc.run(
        repo=tmp_path,
        candidate_export=export,
        candidate_binding=binding,
        candidate_revision=None,
        spec=None,
        output=output,
    )

    assert exit_code == 2
    report = json.loads(output.read_text())
    assert report["status"] == "refused-identity-mismatch"
    assert report["reason_codes"] == ["BINDING_MISMATCH"]
    assert report["candidate_binding_revision"] == SHA_A
    assert report["candidate_export_revision"] == SHA_B
    assert "integrity refusal" in report["claim_boundary"]
    for key in EVALUATION_KEYS:
        assert key not in report, key


# ---------------------------------------------------------------------------
# 2. --candidate-revision != binding Git SHA -> refused
# ---------------------------------------------------------------------------


def test_selected_candidate_revision_must_repeat_binding_sha() -> None:
    identity, diagnostics = mp.establish_candidate_identity(
        binding=_binding(git_commit=SHA_A),
        export=_export(git_commit=SHA_A),
        requested_revision=SHA_B,
    )
    assert identity is None
    assert any("selected --candidate-revision" in d for d in diagnostics)


def test_runner_refuses_selected_revision_rebinding(tmp_path: Path) -> None:
    binding = _write(tmp_path, "binding.json", _binding(git_commit=SHA_A))
    export = _write(tmp_path, "export.json", _export(git_commit=SHA_A))
    output = tmp_path / "report.json"

    exit_code = rmc.run(
        repo=tmp_path,
        candidate_export=export,
        candidate_binding=binding,
        candidate_revision=SHA_B,
        spec=None,
        output=output,
    )

    assert exit_code == 2
    report = json.loads(output.read_text())
    assert report["status"] == "refused-identity-mismatch"
    assert any("selected --candidate-revision" in d for d in report["diagnostics"])
    for key in EVALUATION_KEYS:
        assert key not in report, key


# ---------------------------------------------------------------------------
# 3. missing export revision identity -> refused (fail closed)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "export_overrides, binding_overrides, expected",
    [
        ({"git_commit": ""}, {}, "candidate export git_commit"),
        ({}, {"sysml_project_id": ""}, "candidate binding sysml_project_id"),
        ({}, {"sysml_commit_id": ""}, "candidate binding sysml_commit_id"),
    ],
)
def test_missing_revision_identity_fails_closed(
    export_overrides: dict, binding_overrides: dict, expected: str
) -> None:
    identity, diagnostics = mp.establish_candidate_identity(
        binding=_binding(**binding_overrides), export=_export(**export_overrides)
    )
    assert identity is None
    assert any(
        "missing required revision identity" in d and expected in d for d in diagnostics
    )


def test_malformed_revision_identity_fails_closed() -> None:
    identity, diagnostics = mp.establish_candidate_identity(
        binding=_binding(git_commit="deadbeef"), export=_export(git_commit="deadbeef")
    )
    assert identity is None
    assert any("not a full 40-character Git SHA" in d for d in diagnostics)


def test_runner_refuses_missing_export_identity(tmp_path: Path) -> None:
    binding = _write(tmp_path, "binding.json", _binding(git_commit=SHA_A))
    export = _write(tmp_path, "export.json", _export(git_commit=""))
    output = tmp_path / "report.json"

    exit_code = rmc.run(
        repo=tmp_path,
        candidate_export=export,
        candidate_binding=binding,
        candidate_revision=None,
        spec=None,
        output=output,
    )

    assert exit_code == 2
    report = json.loads(output.read_text())
    assert report["status"] == "refused-identity-mismatch"
    assert any(
        "missing required revision identity" in d for d in report["diagnostics"]
    )


# ---------------------------------------------------------------------------
# 4. matching binding/export/evaluated SHA -> normal evaluation
# ---------------------------------------------------------------------------


def test_matching_identity_returns_one_exact_revision() -> None:
    identity, diagnostics = mp.establish_candidate_identity(
        binding=_binding(git_commit=SHA_A),
        export=_export(git_commit=SHA_A),
        requested_revision=SHA_A,
    )
    assert diagnostics == ()
    assert identity is not None
    assert identity.git_commit == SHA_A
    assert identity.sysml_project_id == "proj-1"
    assert identity.sysml_commit_id == "commit-1"
    assert identity.scope == "candidate"


def test_runner_proceeds_past_identity_gate_when_sha_is_exact(tmp_path: Path) -> None:
    """The identity gate is permissive only for one exact SHA.

    Full evaluation of the governed pilot is exercised by the real-pilot run and
    the focused evaluator suite; here the runner must clear the identity gate
    and continue (any later refusal is a policy-closure refusal, never an
    identity refusal).
    """
    repo, sha_a, _sha_b = _init_repo_with_two_identical_subtrees(tmp_path)
    binding = _write(tmp_path, "binding.json", _binding(git_commit=sha_a))
    export = _write(tmp_path, "export.json", _export(git_commit=sha_a, elements=[]))
    output = tmp_path / "report.json"

    exit_code = rmc.run(
        repo=repo,
        candidate_export=export,
        candidate_binding=binding,
        candidate_revision=None,
        spec=ROOT / "docs" / "method-conformance" / "pilot-obligations.yaml",
        output=output,
    )

    report = json.loads(output.read_text())
    assert exit_code in (0, 2)
    assert report.get("status") != "refused-identity-mismatch"
    assert report["evaluated_revision"]["git_commit"] == sha_a
    assert report["evaluated_revision"]["sysml_project_id"] == "proj-1"
    assert sha_a in report["claim_boundary"]


# ---------------------------------------------------------------------------
# 5. Git-identical subtrees at two SHAs do NOT authorize mixed-revision work
# ---------------------------------------------------------------------------


def test_subtree_identical_does_not_authorize_mixed_revision_evaluation() -> None:
    identity, diagnostics = mp.establish_candidate_identity(
        binding=_binding(git_commit=SHA_A),
        export=_export(git_commit=SHA_B),
        relation_probe=lambda left, right: "subtree-identical",
    )
    assert identity is None
    joined = " ".join(diagnostics)
    assert "subtree-identical" in joined
    assert "never authorization" in joined


def test_runner_refuses_real_git_identical_subtrees(tmp_path: Path) -> None:
    repo, sha_a, sha_b = _init_repo_with_two_identical_subtrees(tmp_path)
    probe = subprocess.run(
        [
            "git", "-C", str(repo), "diff", "--stat", sha_a, sha_b,
            "--", "textual-notation-of-model",
        ],
        capture_output=True,
        text=True,
    )
    assert probe.returncode == 0
    assert probe.stdout.strip() == ""  # subtrees really are identical

    binding = _write(tmp_path, "binding.json", _binding(git_commit=sha_a))
    export = _write(tmp_path, "export.json", _export(git_commit=sha_b))
    output = tmp_path / "report.json"

    exit_code = rmc.run(
        repo=repo,
        candidate_export=export,
        candidate_binding=binding,
        candidate_revision=None,
        spec=None,
        output=output,
    )

    assert exit_code == 2
    report = json.loads(output.read_text())
    assert report["status"] == "refused-identity-mismatch"
    assert any("subtree-identical" in d for d in report["diagnostics"])
    assert any("never authorization" in d for d in report["diagnostics"])


# ---------------------------------------------------------------------------
# 6. refusal cannot produce a successful evaluation outcome
# ---------------------------------------------------------------------------


def test_refusal_carries_no_evaluation_outcome(tmp_path: Path) -> None:
    binding = _write(tmp_path, "binding.json", _binding(git_commit=SHA_A))
    export = _write(tmp_path, "export.json", _export(git_commit=SHA_B))
    output = tmp_path / "report.json"

    rmc.run(
        repo=tmp_path,
        candidate_export=export,
        candidate_binding=binding,
        candidate_revision=None,
        spec=None,
        output=output,
    )

    serialized = output.read_text()
    report = json.loads(serialized)
    assert report["status"] == "refused-identity-mismatch"
    assert report["reason_codes"] == ["BINDING_MISMATCH"]
    for key in EVALUATION_KEYS:
        assert key not in report, key
    # No verdict vocabulary may leak into a refusal report.
    for forbidden in (
        '"PASS"',
        '"FAIL"',
        '"INDETERMINATE"',
        '"UNASSESSED"',
        "evaluation_key",
    ):
        assert forbidden not in serialized, forbidden
