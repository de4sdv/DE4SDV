"""Whole-chain verifier tests: binding, extends, and the frozen lane — fail-closed.

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
    frozen = verifier._frozen_lane_entries
    monkeypatch.setattr(verifier, "_expected_inputs", lambda root:
        expected(root) if root == REPO_ROOT else {ARTIFACT_A: {INPUT_REL}})
    # Synthetic chains without a frozen-records manifest have no frozen lane;
    # the real repository (and any fixture that writes a manifest) always does.
    monkeypatch.setattr(verifier, "_frozen_lane_entries", lambda root:
        frozen(root) if root == REPO_ROOT
        or (root / verifier.FROZEN_MANIFEST_PATH).exists() else [])


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

# ---------------------------------------------------------------------------
# Frozen lane (owner decisions Q7 + D10, 2026-10-07)
# ---------------------------------------------------------------------------

FROZEN_O1 = "docs/method-conformance/o1/inventory.json"
FROZEN_O1_NOTE = "docs/method-conformance/o1/review.md"
FROZEN_O2 = "docs/method-conformance/o2/semantic-projection-v1.json"
FROZEN_O3 = "docs/method-conformance/o3/o3-equivalence-scope.json"


def _frozen_fixture(tmp_path: Path, *, o2_binding=None) -> tuple[Path, str, str]:
    """A chain with frozen o1/o2/o3 records, then a manifest pinned at a revision.

    Returns ``(root, input_revision, frozen_revision)``.
    """
    from scripts import verify_generated_chain as verifier

    root, revision = _fixture(tmp_path)
    _write_artifact(root / FROZEN_O1, {"schema": "test/o1",
                                        "binding": _binding(root, revision)})
    (root / FROZEN_O1_NOTE).write_text("frozen prose\n", encoding="utf-8")
    binding = o2_binding(root, revision) if o2_binding else _binding(root, revision)
    _write_artifact(root / FROZEN_O2, {"schema": "test/o2", "binding": binding})
    o1_digest = _sha256((root / FROZEN_O1).read_bytes())
    o2_digest = _sha256((root / FROZEN_O2).read_bytes())
    _write_artifact(root / FROZEN_O3, {"basis": {
        "comparison_base_revision": revision,
        "o1_inventory": {"path": FROZEN_O1, "sha256": o1_digest},
        "o2_chain": [{"path": FROZEN_O2, "sha256": o2_digest}],
    }})
    frozen_revision = _commit(root, "records to be frozen")
    (root / verifier.FROZEN_MANIFEST_PATH).write_text(
        verifier.render_frozen_manifest_text(root, frozen_revision), encoding="utf-8")
    _commit(root, "freeze manifest")
    return root, revision, frozen_revision


def _frozen_errors(root: Path, artifact: str) -> list[str]:
    entries = verify_generated_chain(root, include_passing=True)
    return [e for entry in entries if entry["artifact"] == artifact for e in entry["errors"]]


def _manifest_path():
    from scripts import verify_generated_chain as verifier
    return verifier.FROZEN_MANIFEST_PATH


def test_frozen_fixture_chain_passes(tmp_path):
    root, _, _ = _frozen_fixture(tmp_path)
    report = verify_generated_chain(root, include_passing=True)
    assert [e for e in report if not e["ok"]] == []
    assert {FROZEN_O1, FROZEN_O1_NOTE, FROZEN_O2, FROZEN_O3, _manifest_path()} <= {
        e["artifact"] for e in report}


def test_frozen_byte_flip_fails(tmp_path):
    root, _, _ = _frozen_fixture(tmp_path)
    (root / FROZEN_O1_NOTE).write_text("frozen prose!\n", encoding="utf-8")
    assert any("frozen record bytes changed" in e for e in _frozen_errors(root, FROZEN_O1_NOTE))


def test_frozen_directory_addition_fails(tmp_path):
    root, _, _ = _frozen_fixture(tmp_path)
    (root / "docs/method-conformance/o2/new-record.json").write_text("{}\n", encoding="utf-8")
    assert any("not a frozen record" in e for e in _frozen_errors(root, _manifest_path()))
    _commit(root, "commit the addition too")
    assert any("not a frozen record" in e for e in _frozen_errors(root, _manifest_path()))


def test_frozen_record_removal_fails_even_with_the_manifest_row_removed(tmp_path):
    root, _, _ = _frozen_fixture(tmp_path)
    (root / FROZEN_O1_NOTE).unlink()
    assert any("missing from the checkout" in e for e in _frozen_errors(root, _manifest_path()))
    manifest = json.loads((root / _manifest_path()).read_text(encoding="utf-8"))
    manifest["records"] = [r for r in manifest["records"] if r["path"] != FROZEN_O1_NOTE]
    (root / _manifest_path()).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    assert any("differs from its rendering" in e for e in _frozen_errors(root, _manifest_path()))


def test_frozen_binding_survives_input_edit_and_deletion_at_head(tmp_path):
    """The point of freezing: inputs may change at HEAD; history still verifies."""
    root, _, _ = _frozen_fixture(tmp_path)
    (root / INPUT_REL).write_text("payload-v2\n", encoding="utf-8")
    _commit(root, "input edited at head")
    # The live (non-frozen) artifact bound to the same input now fails ...
    assert any(INPUT_REL in e for e in _frozen_errors(root, ARTIFACT_A))
    # ... while the frozen records stay valid.
    for frozen in (FROZEN_O1, FROZEN_O2, FROZEN_O3, _manifest_path()):
        assert _frozen_errors(root, frozen) == [], frozen
    (root / INPUT_REL).unlink()
    _commit(root, "input deleted at head")
    for frozen in (FROZEN_O1, FROZEN_O2, FROZEN_O3, _manifest_path()):
        assert _frozen_errors(root, frozen) == [], frozen


def test_frozen_forged_bound_input_digest_fails_the_historical_check(tmp_path):
    root, _, _ = _frozen_fixture(tmp_path, o2_binding=lambda root, revision: {
        "source_revision": revision, "bound_inputs": {INPUT_REL: "sha256:" + "0" * 64}})
    errors = _frozen_errors(root, FROZEN_O2)
    assert any("does not match its bytes at source revision" in e for e in errors), errors


def test_frozen_missing_bound_input_at_its_revision_fails(tmp_path):
    root, _, _ = _frozen_fixture(tmp_path, o2_binding=lambda root, revision: {
        "source_revision": revision, "bound_inputs": {"src/absent.txt": "sha256:" + "0" * 64}})
    errors = _frozen_errors(root, FROZEN_O2)
    assert any("does not exist at source revision" in e for e in errors), errors


def test_frozen_non_ancestor_source_revision_fails(tmp_path):
    root, _ = _fixture(tmp_path)
    branch = _git(root, "symbolic-ref", "--short", "HEAD")
    _git(root, "checkout", "-q", "-b", "side")
    (root / "src" / "side.txt").write_text("side\n", encoding="utf-8")
    side_revision = _commit(root, "side commit")
    _git(root, "checkout", "-q", branch)
    from scripts import verify_generated_chain as verifier
    _write_artifact(root / FROZEN_O1, {"schema": "test/o1", "binding": {
        "source_revision": side_revision,
        "bound_inputs": {"src/side.txt": _sha256(b"side\n")}}})
    _write_artifact(root / FROZEN_O3, {"basis": {
        "comparison_base_revision": _git(root, "rev-parse", "HEAD"),
        "o1_inventory": {"path": FROZEN_O1, "sha256": _sha256((root / FROZEN_O1).read_bytes())},
        "o2_chain": []}})
    frozen_revision = _commit(root, "records")
    (root / verifier.FROZEN_MANIFEST_PATH).write_text(
        verifier.render_frozen_manifest_text(root, frozen_revision), encoding="utf-8")
    _commit(root, "freeze")
    assert any("not an ancestor" in e for e in _frozen_errors(root, FROZEN_O1))


def test_frozen_manifest_tamper_and_binding_key_fail(tmp_path):
    root, _, _ = _frozen_fixture(tmp_path)
    path = root / _manifest_path()
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["records"][0]["sha256"] = "sha256:" + "3" * 64
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    assert any("differs from its rendering" in e for e in _frozen_errors(root, _manifest_path()))
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["binding"] = {"source_revision": "0" * 40}
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    assert any("must not carry a 'binding' key" in e for e in _frozen_errors(root, _manifest_path()))


def test_frozen_manifest_revision_must_be_an_ancestor(tmp_path):
    root, _, _ = _frozen_fixture(tmp_path)
    path = root / _manifest_path()
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["frozen_at_revision"] = "e" * 40
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    assert any("frozen_at_revision" in e for e in _frozen_errors(root, _manifest_path()))


def test_frozen_manifest_missing_fails(tmp_path, monkeypatch):
    from scripts import verify_generated_chain as verifier
    monkeypatch.undo()  # the real lane, not the synthetic-registry wrapper
    root, _, _ = _frozen_fixture(tmp_path)
    (root / verifier.FROZEN_MANIFEST_PATH).unlink()
    entries = verifier._frozen_lane_entries(root)
    assert entries == [{"artifact": verifier.FROZEN_MANIFEST_PATH, "ok": False,
                        "errors": ["frozen-records manifest is missing"]}]


def test_frozen_o3_basis_digest_and_base_checks(tmp_path):
    """Replaces the former live O3 scope lane test: the basis is frozen data."""
    from scripts import verify_generated_chain as verifier
    root, revision = _fixture(tmp_path)
    _write_artifact(root / FROZEN_O1, {"schema": "test/o1"})
    o1_digest = _sha256((root / FROZEN_O1).read_bytes())

    def _freeze(basis: dict) -> None:
        _write_artifact(root / FROZEN_O3, {"basis": basis})
        frozen_revision = _commit(root, "o3 scope")
        (root / verifier.FROZEN_MANIFEST_PATH).write_text(
            verifier.render_frozen_manifest_text(root, frozen_revision), encoding="utf-8")
        _commit(root, "freeze")

    _freeze({"comparison_base_revision": revision,
             "o1_inventory": {"path": FROZEN_O1, "sha256": o1_digest}, "o2_chain": []})
    assert _frozen_errors(root, FROZEN_O3) == []
    _freeze({"comparison_base_revision": revision,
             "o1_inventory": {"path": FROZEN_O1, "sha256": "sha256:" + "2" * 64}, "o2_chain": []})
    assert any("o3 basis.o1_inventory" in e for e in _frozen_errors(root, FROZEN_O3))
    _freeze({"comparison_base_revision": "e" * 40,
             "o1_inventory": {"path": FROZEN_O1, "sha256": o1_digest}, "o2_chain": []})
    assert any("comparison_base_revision" in e for e in _frozen_errors(root, FROZEN_O3))
    _freeze({"comparison_base_revision": revision,
             "o1_inventory": {"path": ARTIFACT_A, "sha256": _sha256((root / ARTIFACT_A).read_bytes())},
             "o2_chain": []})
    assert any("must be a frozen record" in e for e in _frozen_errors(root, FROZEN_O3))


# -- real repository ---------------------------------------------------------


def _real_manifest() -> dict:
    from scripts import verify_generated_chain as verifier
    return json.loads((REPO_ROOT / verifier.FROZEN_MANIFEST_PATH).read_text(encoding="utf-8"))


def test_real_frozen_manifest_covers_whole_directories():
    from scripts import verify_generated_chain as verifier
    manifest = _real_manifest()
    assert manifest["directories"] == list(verifier.FROZEN_DIRECTORIES)
    tracked = _git(REPO_ROOT, "ls-files", "--", *verifier.FROZEN_DIRECTORIES).splitlines()
    assert sorted(r["path"] for r in manifest["records"]) == sorted(tracked)
    assert len(tracked) == 29
    assert not {"binding", "source_revision", "extends"} & set(manifest)
    assert sum(r["kind"] == "generated" for r in manifest["records"]) == 7


def test_real_frozen_manifest_equals_its_rendering():
    from scripts import verify_generated_chain as verifier
    manifest = _real_manifest()
    rendered = verifier.render_frozen_manifest_text(REPO_ROOT, manifest["frozen_at_revision"])
    assert rendered == (REPO_ROOT / verifier.FROZEN_MANIFEST_PATH).read_text(encoding="utf-8")


def test_real_frozen_records_pass_although_frozen_o1_inputs_changed_at_head():
    """check_model_sync.py is a bound input of the frozen O1 inventory: editing
    it (O4 Wave C1) no longer breaks the record, whose binding is historical."""
    from scripts import verify_generated_chain as verifier
    inventory = json.loads((REPO_ROOT / "docs/method-conformance/o1/"
                            "semantic-authority-inventory.json").read_text(encoding="utf-8"))
    bound = inventory["binding"]["bound_inputs"]
    changed = [path for path in ("scripts/check_model_sync.py",
               "textual-notation-of-model/packages/methods/de4sdv/"
               "de4sdv_ontology_validation_rules.sysml")
               if _sha256((REPO_ROOT / path).read_bytes()) != bound[path]]
    assert changed, "expected at least one frozen O1 bound input to differ at HEAD"
    assert verifier.frozen_record_errors(REPO_ROOT) == []


def test_frozen_lane_does_not_read_the_authored_ontology_at_head(monkeypatch):
    """The frozen lane never opens a bound input from the working tree."""
    from scripts import verify_generated_chain as verifier
    opened = []
    original = Path.read_bytes

    def spy(self):
        opened.append(self)
        return original(self)

    monkeypatch.setattr(Path, "read_bytes", spy)
    assert verifier.frozen_record_errors(REPO_ROOT) == []
    frozen = tuple(REPO_ROOT / d for d in verifier.FROZEN_DIRECTORIES)
    assert opened and all(any(p.is_relative_to(d) for d in frozen) for p in opened), [
        str(p) for p in opened if not any(p.is_relative_to(d) for d in frozen)]
