"""Whole-chain verifier tests: binding, extends, and O3 scope basis — fail-closed.

The verifier is the recovery/reproducibility diagnostic: it must pass on a
consistent committed chain and report each break cause by name (content
mismatch, stale revision, missing/foreign source revision, extends drift,
scope-basis drift) rather than silently accepting a recorded string.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.verify_generated_chain import verify_generated_chain  # noqa: E402

INPUT_REL = "src/input.txt"
ARTIFACT_A = "docs/method-conformance/artifact-a.json"


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _write_artifact(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")


def _binding(root: Path, revision: str, path: str = INPUT_REL) -> dict:
    return {
        "source_revision": revision,
        "bound_inputs": {path: _sha256((root / path).read_bytes())},
    }


def _commit(root: Path, message: str) -> str:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", message)
    return _git(root, "rev-parse", "HEAD")


def _fixture(tmp_path: Path) -> tuple[Path, str]:
    """A committed mini-chain: input @A1, artifact bound to A1, committed @A2."""
    root = tmp_path / "repo"
    root.mkdir()
    (root / "src").mkdir()
    (root / "src" / "input.txt").write_text("payload-v1\n", encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "verify@example.com")
    _git(root, "config", "user.name", "Verify Fixture")
    revision = _commit(root, "A1 input")
    _write_artifact(
        root / ARTIFACT_A,
        {"schema": "test/artifact", "binding": _binding(root, revision)},
    )
    _commit(root, "A2 artifact bound to A1")
    return root, revision


def _entry(root: Path, artifact: str = ARTIFACT_A) -> dict:
    failures = verify_generated_chain(root)
    return next(entry for entry in failures if entry["artifact"] == artifact)


@pytest.fixture(autouse=True)
def synthetic_lane_registry(monkeypatch):
    from scripts import verify_generated_chain as verifier
    expected = verifier._expected_inputs
    scope = verifier._o3_scope_entry
    monkeypatch.setattr(verifier, "_expected_inputs", lambda root:
        expected(root) if root == REPO_ROOT else {ARTIFACT_A: {INPUT_REL}})
    monkeypatch.setattr(verifier, "_o3_scope_entry", lambda root:
        scope(root) if root == REPO_ROOT or (root / verifier.O3_SCOPE_PATH).exists()
        else None)


def test_required_artifact_and_binding_cannot_disappear(tmp_path):
    root, _ = _fixture(tmp_path)
    _write_artifact(root / ARTIFACT_A, {"schema": "test/artifact"})
    assert _entry(root)["errors"]
    (root / ARTIFACT_A).unlink()
    assert _entry(root)["errors"]


def test_omitted_required_input_is_refused(tmp_path, monkeypatch):
    from scripts import verify_generated_chain as verifier
    root, _ = _fixture(tmp_path)
    monkeypatch.setattr(verifier, "_expected_inputs", lambda root:
                        {ARTIFACT_A: {INPUT_REL, "src/required.txt"}})
    assert any("generator-required" in error for error in _entry(root)["errors"])


def test_named_binding_metadata_is_validated(tmp_path):
    root, _ = _fixture(tmp_path)
    document = json.loads((root / ARTIFACT_A).read_text())
    document["binding"]["reviewed_decisions"] = {"path": "unbound.yaml", "sha256": "0" * 64}
    _write_artifact(root / ARTIFACT_A, document)
    assert any("not a bound input" in error for error in _entry(root)["errors"])


def test_frozen_record_top_level_revision_is_validated(tmp_path):
    root, revision = _fixture(tmp_path)
    record = root / "docs/method-conformance/o4/example-record.json"
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps({"schema": "test/record", "source_revision": revision}))
    _commit(root, "frozen record with valid revision")
    assert verify_generated_chain(root) == []
    # A malformed or non-ancestor claim refuses by name.
    record.write_text(json.dumps({"schema": "test/record", "source_revision": "f" * 40}))
    _commit(root, "frozen record with bad revision")
    entry = _entry(root, "docs/method-conformance/o4/example-record.json")
    assert not entry["ok"]
    assert any("ancestor" in error for error in entry["errors"])


def test_real_repo_chain_is_consistent():
    assert verify_generated_chain(REPO_ROOT) == []


def test_consistent_fixture_chain_passes(tmp_path):
    root, _ = _fixture(tmp_path)
    assert verify_generated_chain(root) == []


def test_uncommitted_input_edit_is_reported_by_name(tmp_path):
    root, _ = _fixture(tmp_path)
    (root / INPUT_REL).write_text("payload-v2\n", encoding="utf-8")
    entry = _entry(root)
    assert not entry["ok"]
    assert any(INPUT_REL in error for error in entry["errors"]), entry["errors"]


def test_stale_revision_fails_until_rebound(tmp_path):
    root, revision = _fixture(tmp_path)
    # Commit the input edit: the recorded revision no longer contains the
    # current bytes, so the binding is stale (content, not string reuse).
    (root / INPUT_REL).write_text("payload-v2\n", encoding="utf-8")
    _commit(root, "input v2")
    entry = _entry(root)
    assert not entry["ok"]
    assert any(INPUT_REL in error for error in entry["errors"]), entry["errors"]
    # Rebind to the new revision and commit: consistent again.
    new_revision = _git(root, "rev-parse", "HEAD")
    assert new_revision != revision
    _write_artifact(
        root / ARTIFACT_A,
        {"schema": "test/artifact", "binding": _binding(root, new_revision)},
    )
    _commit(root, "rebind artifact")
    assert verify_generated_chain(root) == []


def test_tampered_recorded_digest_is_reported(tmp_path):
    root, revision = _fixture(tmp_path)
    document = json.loads((root / ARTIFACT_A).read_text(encoding="utf-8"))
    document["binding"]["bound_inputs"][INPUT_REL] = "sha256:" + "0" * 64
    _write_artifact(root / ARTIFACT_A, document)
    _commit(root, "tamper digest")
    entry = _entry(root)
    assert not entry["ok"]
    assert any("does not match" in error for error in entry["errors"]), entry["errors"]


def test_unknown_source_revision_is_reported(tmp_path):
    root, _ = _fixture(tmp_path)
    document = json.loads((root / ARTIFACT_A).read_text(encoding="utf-8"))
    document["binding"]["source_revision"] = "f" * 40
    _write_artifact(root / ARTIFACT_A, document)
    _commit(root, "unknown revision")
    entry = _entry(root)
    assert not entry["ok"]
    assert entry["errors"], entry


def test_non_ancestor_source_revision_is_reported(tmp_path):
    root, _ = _fixture(tmp_path)
    branch = _git(root, "symbolic-ref", "--short", "HEAD")
    # A side-branch commit that is reachable only from the side branch.
    _git(root, "checkout", "-q", "-b", "side")
    (root / "src" / "side.txt").write_text("side\n", encoding="utf-8")
    side_revision = _commit(root, "side commit")
    _git(root, "checkout", "-q", branch)
    document = json.loads((root / ARTIFACT_A).read_text(encoding="utf-8"))
    document["binding"] = _binding(root, side_revision)
    _write_artifact(root / ARTIFACT_A, document)
    _commit(root, "bind to side revision")
    entry = _entry(root)
    assert not entry["ok"]
    assert any(
        ("not an ancestor" in error) or ("not" in error and "ancestor" in error)
        for error in entry["errors"]
    ), entry["errors"]


def test_extends_digest_and_revision_drift_are_reported(tmp_path):
    root, revision = _fixture(tmp_path)
    artifact_b = "docs/method-conformance/artifact-b.json"
    target_revision = _git(root, "rev-parse", "HEAD")
    _write_artifact(
        root / artifact_b,
        {
            "schema": "test/artifact",
            "binding": _binding(root, target_revision, path=ARTIFACT_A),
            "extends": {
                "artifact": ARTIFACT_A,
                "artifact_digest": _sha256((root / ARTIFACT_A).read_bytes()),
                "source_revision": revision,
            },
        },
    )
    _commit(root, "artifact b extends a")
    assert verify_generated_chain(root) == []
    # Digest drift.
    document = json.loads((root / artifact_b).read_text(encoding="utf-8"))
    document["extends"]["artifact_digest"] = "sha256:" + "1" * 64
    _write_artifact(root / artifact_b, document)
    _commit(root, "extend digest drift")
    entry = _entry(root, artifact_b)
    assert not entry["ok"]
    assert any("extends.artifact_digest" in error for error in entry["errors"])
    # Revision drift (digest restored).
    document["extends"]["artifact_digest"] = _sha256(
        (root / ARTIFACT_A).read_bytes()
    )
    document["extends"]["source_revision"] = "f" * 40
    _write_artifact(root / artifact_b, document)
    _commit(root, "extend revision drift")
    entry = _entry(root, artifact_b)
    assert not entry["ok"]
    assert any("extends.source_revision" in error for error in entry["errors"])


def test_o3_scope_basis_digest_and_base_checks(tmp_path):
    root, revision = _fixture(tmp_path)
    scope = root / "docs/method-conformance/o3/o3-equivalence-scope.json"
    scope.parent.mkdir(parents=True, exist_ok=True)
    basis = {
        "comparison_base_revision": revision,
        "o1_inventory": {"path": ARTIFACT_A, "sha256": _sha256((root / ARTIFACT_A).read_bytes())},
        "o2_chain": [],
    }
    scope.write_text(json.dumps({"basis": basis}, indent=1) + "\n", encoding="utf-8")
    _commit(root, "o3 scope")
    assert verify_generated_chain(root) == []
    # Digest drift.
    basis["o1_inventory"]["sha256"] = "sha256:" + "2" * 64
    scope.write_text(json.dumps({"basis": basis}, indent=1) + "\n", encoding="utf-8")
    _commit(root, "scope digest drift")
    entry = _entry(root, "docs/method-conformance/o3/o3-equivalence-scope.json")
    assert not entry["ok"]
    assert any("o3 basis.o1_inventory" in error for error in entry["errors"])
    # Base revision drift (an unknown commit).
    basis["o1_inventory"]["sha256"] = _sha256((root / ARTIFACT_A).read_bytes())
    basis["comparison_base_revision"] = "e" * 40
    scope.write_text(json.dumps({"basis": basis}, indent=1) + "\n", encoding="utf-8")
    _commit(root, "scope base drift")
    entry = _entry(root, "docs/method-conformance/o3/o3-equivalence-scope.json")
    assert not entry["ok"]
    assert any("comparison_base_revision" in error for error in entry["errors"])


def test_report_is_deterministic(tmp_path):
    root, _ = _fixture(tmp_path)
    first = verify_generated_chain(root, include_passing=True)
    second = verify_generated_chain(root, include_passing=True)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first and all(entry["ok"] for entry in first)


def test_cli_json_mode_on_the_real_repo():
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "verify_generated_chain.py"), "--json"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    report = json.loads(result.stdout)
    assert isinstance(report, list)
    assert report, "the real chain must contain binding-carrying artifacts"