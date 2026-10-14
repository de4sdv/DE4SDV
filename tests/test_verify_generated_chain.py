"""Historical records stay immutable and verify at their recorded revisions."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import verify_generated_chain as verifier  # noqa: E402
from scripts.verify_generated_chain import verify_generated_chain  # noqa: E402

INPUT_REL = "src/input.txt"
ARTIFACT_A = "live/artifact-a.json"

# Synthetic frozen records: the records are frozen in ``old/`` and later live in
# ``frozen/``, so the historical-path mapping is exercised as well.
HISTORICAL = "old"
FROZEN = "frozen"
RECORD_A = "a.json"
RECORD_B = "b.json"
NOTE = "note.md"
FROZEN_A = f"{FROZEN}/{RECORD_A}"
FROZEN_B = f"{FROZEN}/{RECORD_B}"
FROZEN_NOTE = f"{FROZEN}/{NOTE}"
MANIFEST = "frozen-records.json"


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


@pytest.fixture
def synthetic_frozen_records(monkeypatch):
    """Point the frozen-record check at the synthetic record set."""
    monkeypatch.setattr(verifier, "FROZEN_MANIFEST_PATH", MANIFEST)
    monkeypatch.setattr(verifier, "FROZEN_DIRECTORY", FROZEN)
    monkeypatch.setattr(verifier, "FROZEN_DIRECTORIES", (FROZEN,))
    monkeypatch.setattr(verifier, "HISTORICAL_DIRECTORY", HISTORICAL)
    monkeypatch.setattr(verifier, "FROZEN_RECORD_NAMES", (RECORD_A, RECORD_B, NOTE))
    return verifier


def _freeze(root: Path, records: dict[str, object]) -> str:
    """Commit ``records`` under the historical directory, freeze them, move them."""
    for name, content in records.items():
        path = root / HISTORICAL / name
        if isinstance(content, dict):
            _write_artifact(path, content)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(str(content), encoding="utf-8")
    frozen_revision = _commit(root, "records to be frozen")
    _git(root, "mv", HISTORICAL, FROZEN)
    _commit(root, "records move to their current directory")
    (root / MANIFEST).write_text(
        verifier.render_frozen_manifest_text(root, frozen_revision), encoding="utf-8")
    _commit(root, "freeze manifest")
    return frozen_revision


def _frozen_fixture(tmp_path: Path, *, b_binding=None) -> tuple[Path, str, str]:
    """Records a/b (bound to the input revision, b extends a) and a prose note.

    Returns ``(root, input_revision, frozen_revision)``.
    """
    root, revision = _fixture(tmp_path)
    (root / HISTORICAL).mkdir()
    a = {"schema": "test/a", "binding": _binding(root, revision)}
    _write_artifact(root / HISTORICAL / RECORD_A, a)
    a_digest = _sha256((root / HISTORICAL / RECORD_A).read_bytes())
    binding = b_binding(root, revision) if b_binding else _binding(root, revision)
    b = {"schema": "test/b", "binding": binding,
         "extends": {"artifact": f"{HISTORICAL}/{RECORD_A}", "artifact_digest": a_digest,
                     "source_revision": revision}}
    frozen_revision = _freeze(root, {RECORD_B: b, NOTE: "frozen prose\n"})
    return root, revision, frozen_revision


def _frozen_errors(root: Path, artifact: str) -> list[str]:
    entries = verify_generated_chain(root, include_passing=True)
    return [e for entry in entries if entry["artifact"] == artifact for e in entry["errors"]]


def test_real_repo_chain_is_consistent():
    assert verify_generated_chain(REPO_ROOT) == []


def test_report_is_deterministic(synthetic_frozen_records, tmp_path):
    root, _, _ = _frozen_fixture(tmp_path)
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
    assert report, "the historical inventory must not disappear"

# ---------------------------------------------------------------------------
# Frozen records
# ---------------------------------------------------------------------------


def test_frozen_fixture_chain_passes(synthetic_frozen_records, tmp_path):
    root, _, _ = _frozen_fixture(tmp_path)
    report = verify_generated_chain(root, include_passing=True)
    assert [e for e in report if not e["ok"]] == []
    assert {e["artifact"] for e in report} == {FROZEN_A, FROZEN_B, FROZEN_NOTE, MANIFEST}


def test_frozen_byte_flip_fails(synthetic_frozen_records, tmp_path):
    root, _, _ = _frozen_fixture(tmp_path)
    (root / FROZEN_NOTE).write_text("frozen prose!\n", encoding="utf-8")
    assert any("frozen record bytes changed" in e for e in _frozen_errors(root, FROZEN_NOTE))


def test_frozen_directory_addition_fails(synthetic_frozen_records, tmp_path):
    root, _, _ = _frozen_fixture(tmp_path)
    (root / FROZEN / "new-record.json").write_text("{}\n", encoding="utf-8")
    assert any("not a frozen record" in e for e in _frozen_errors(root, MANIFEST))
    _commit(root, "commit the addition too")
    assert any("not a frozen record" in e for e in _frozen_errors(root, MANIFEST))


def test_frozen_record_removal_fails_even_with_the_manifest_row_removed(synthetic_frozen_records, tmp_path):
    root, _, _ = _frozen_fixture(tmp_path)
    (root / FROZEN_NOTE).unlink()
    assert any("missing from the checkout" in e for e in _frozen_errors(root, MANIFEST))
    manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    manifest["records"] = [r for r in manifest["records"] if r["path"] != FROZEN_NOTE]
    (root / MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    assert any("differs from its rendering" in e for e in _frozen_errors(root, MANIFEST))


def test_frozen_binding_survives_input_edit_and_deletion_at_head(synthetic_frozen_records, tmp_path):
    """The point of freezing: inputs may change at HEAD; history still verifies."""
    root, _, _ = _frozen_fixture(tmp_path)
    (root / INPUT_REL).write_text("payload-v2\n", encoding="utf-8")
    _commit(root, "input edited at head")
    # Current-source outputs are checked by their generators, not this verifier.
    assert ARTIFACT_A not in {
        row["artifact"] for row in verify_generated_chain(root, include_passing=True)}
    for frozen in (FROZEN_A, FROZEN_B, MANIFEST):
        assert _frozen_errors(root, frozen) == [], frozen
    (root / INPUT_REL).unlink()
    _commit(root, "input deleted at head")
    for frozen in (FROZEN_A, FROZEN_B, MANIFEST):
        assert _frozen_errors(root, frozen) == [], frozen


def test_frozen_forged_bound_input_digest_fails_the_historical_check(synthetic_frozen_records, tmp_path):
    root, _, _ = _frozen_fixture(tmp_path, b_binding=lambda root, revision: {
        "source_revision": revision, "bound_inputs": {INPUT_REL: "sha256:" + "0" * 64}})
    errors = _frozen_errors(root, FROZEN_B)
    assert any("does not match its bytes at source revision" in e for e in errors), errors


def test_frozen_missing_bound_input_at_its_revision_fails(synthetic_frozen_records, tmp_path):
    root, _, _ = _frozen_fixture(tmp_path, b_binding=lambda root, revision: {
        "source_revision": revision, "bound_inputs": {"src/absent.txt": "sha256:" + "0" * 64}})
    errors = _frozen_errors(root, FROZEN_B)
    assert any("does not exist at source revision" in e for e in errors), errors


def test_frozen_non_ancestor_source_revision_fails(synthetic_frozen_records, tmp_path):
    root, _ = _fixture(tmp_path)
    branch = _git(root, "symbolic-ref", "--short", "HEAD")
    _git(root, "checkout", "-q", "-b", "side")
    (root / "src" / "side.txt").write_text("side\n", encoding="utf-8")
    side_revision = _commit(root, "side commit")
    _git(root, "checkout", "-q", branch)
    _freeze(root, {
        RECORD_A: {"schema": "test/a", "binding": {
            "source_revision": side_revision,
            "bound_inputs": {"src/side.txt": _sha256(b"side\n")}}},
        RECORD_B: {"schema": "test/b"},
        NOTE: "frozen prose\n",
    })
    assert any("not an ancestor" in e for e in _frozen_errors(root, FROZEN_A))


def test_frozen_manifest_tamper_and_binding_key_fail(synthetic_frozen_records, tmp_path):
    root, _, _ = _frozen_fixture(tmp_path)
    path = root / MANIFEST
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["records"][0]["sha256"] = "sha256:" + "3" * 64
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    assert any("differs from its rendering" in e for e in _frozen_errors(root, MANIFEST))
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["binding"] = {"source_revision": "0" * 40}
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    assert any("must not carry a 'binding' key" in e for e in _frozen_errors(root, MANIFEST))


def test_frozen_manifest_revision_must_be_an_ancestor(synthetic_frozen_records, tmp_path):
    root, _, _ = _frozen_fixture(tmp_path)
    path = root / MANIFEST
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["frozen_at_revision"] = "e" * 40
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    assert any("frozen_at_revision" in e for e in _frozen_errors(root, MANIFEST))


def test_frozen_manifest_missing_fails(synthetic_frozen_records, tmp_path):
    root, _, _ = _frozen_fixture(tmp_path)
    (root / MANIFEST).unlink()
    entries = verifier._frozen_lane_entries(root)
    assert entries == [{"artifact": MANIFEST, "ok": False,
                        "errors": ["frozen-records manifest is missing"]}]


def test_extends_resolves_historical_paths_to_the_current_directory(synthetic_frozen_records, tmp_path):
    """A record keeps its historical ``extends`` path after the move; the check
    resolves it to the current record and still checks digest and revision."""
    root, revision, _ = _frozen_fixture(tmp_path)
    b = json.loads((root / FROZEN_B).read_text(encoding="utf-8"))
    assert b["extends"]["artifact"] == f"{HISTORICAL}/{RECORD_A}"
    assert not (root / HISTORICAL).exists()
    assert _frozen_errors(root, FROZEN_B) == []

    (tmp_path / "forged").mkdir()
    other, revision = _fixture(tmp_path / "forged")
    _write_artifact(other / HISTORICAL / RECORD_A, {"schema": "test/a"})
    _freeze(other, {
        RECORD_B: {"schema": "test/b", "extends": {
            "artifact": f"{HISTORICAL}/{RECORD_A}", "artifact_digest": "sha256:" + "4" * 64,
            "source_revision": revision}},
        NOTE: "frozen prose\n",
    })
    assert any("does not match the frozen digest" in e for e in _frozen_errors(other, FROZEN_B))


# -- real repository ---------------------------------------------------------


def _real_manifest() -> dict:
    return json.loads((REPO_ROOT / verifier.FROZEN_MANIFEST_PATH).read_text(encoding="utf-8"))


def test_real_frozen_manifest_covers_exactly_the_records_the_runtime_serves():
    from de4sdv.semantic.model_contract import FROZEN_PROFILE_RECORDS, FROZEN_PROJECTION_RECORDS

    manifest = _real_manifest()
    assert manifest["directories"] == list(verifier.FROZEN_DIRECTORIES)
    tracked = _git(REPO_ROOT, "ls-files", "--", *verifier.FROZEN_DIRECTORIES).splitlines()
    paths = sorted(r["path"] for r in manifest["records"])
    assert paths == sorted(tracked)
    served = sorted(path for path, _schema in FROZEN_PROJECTION_RECORDS + FROZEN_PROFILE_RECORDS)
    assert paths == served
    assert not {"binding", "source_revision", "extends"} & set(manifest)
    assert {r["kind"] for r in manifest["records"]} == {"generated"}


def test_real_frozen_manifest_equals_its_rendering():
    manifest = _real_manifest()
    rendered = verifier.render_frozen_manifest_text(REPO_ROOT, manifest["frozen_at_revision"])
    assert rendered == (REPO_ROOT / verifier.FROZEN_MANIFEST_PATH).read_text(encoding="utf-8")


def test_real_frozen_records_pass_although_their_bound_inputs_changed_at_head():
    """The frozen records bind inputs that have since changed or been deleted;
    their bindings are historical, so the records still verify."""
    record = json.loads((REPO_ROOT / verifier.FROZEN_DIRECTORY /
                         "semantic-projection-v1.json").read_text(encoding="utf-8"))
    bound = record["binding"]["bound_inputs"]
    changed = [path for path, digest in bound.items()
               if (REPO_ROOT / path).is_file() and _sha256((REPO_ROOT / path).read_bytes()) != digest]
    absent = [path for path in bound if not (REPO_ROOT / path).exists()]
    assert changed, "expected at least one bound input to differ at HEAD"
    assert absent, "expected at least one bound input to be deleted at HEAD"
    assert verifier.frozen_record_errors(REPO_ROOT) == []


def test_frozen_record_check_does_not_read_the_authored_ontology_at_head(monkeypatch):
    """The frozen-record check never opens a bound input from the working tree."""
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
