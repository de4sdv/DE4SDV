"""Evidence-restoration guards for the 009B canonical run bundle (PR #188 repair).

The canonical evidence document `evidence/009b/scenario-evidence.json` hash-binds
five run artifacts that #68 deleted from tracking while keeping the references.
The repair restores four of them byte-identically from b20834d via
`git add -f` (the `implementation/*/evidence/**/runs/` ignore rule caused the
silent skip). The zero-byte `observer.log` is deliberately NOT restored as an
unexplained empty log: per docs/evidence-management.md a zero-byte file is not
evidence, so its absence is asserted here and its empty-string SHA is
acknowledged as retained history inside the canonical document, which is the
manifest-declared sentinel semantics for that reference.

These guards run in the repository pytest scope (`pytest tests`) so clean
checkouts and CI keep failing if the canonical references lose their files
again.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "implementation" / "aebs-autoware-nominal-vehicle-target-bench"
EVIDENCE = BENCH / "evidence" / "009b" / "scenario-evidence.json"
RUN_DIR = BENCH / "evidence" / "009b" / "runs" / "20260727T103958Z-4d22f5c8b44d584c"

# The zero-byte observer.log is intentionally untracked (empty files are not
# evidence); its canonical-manifest SHA is the well-known empty-string digest.
ZERO_BYTE_SENTINEL_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
ZERO_BYTE_NAME = "observer_log"


def _canonical_document() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_restored_run_artifacts_are_tracked_and_hash_bound():
    document = _canonical_document()
    restored = {
        name: record
        for name, record in document["artifacts"].items()
        if name != ZERO_BYTE_NAME
    }
    assert set(restored) == {
        "launch_log", "map_runtime", "observer_raw", "run_metadata"
    }
    for name, record in restored.items():
        path = BENCH / record["path"]
        assert path.is_file(), f"restored artifact missing: {record['path']}"
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == record["sha256"], f"{name} SHA-256 differs from canonical manifest"


def test_zero_byte_observer_log_is_not_tracked_as_evidence():
    """Policy: empty files are not evidence (docs/evidence-management.md)."""
    document = _canonical_document()
    record = document["artifacts"][ZERO_BYTE_NAME]
    assert record["sha256"] == ZERO_BYTE_SENTINEL_SHA256
    assert not (BENCH / record["path"]).exists()


def test_runs_ignore_rule_negation_covers_the_restored_bundle():
    """The restore used git add -f because .gitignore excludes runs/; this test
    documents that choice so a future canonical reference to a run artifact
    gets force-added and verified, not silently skipped."""
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "implementation/*/evidence/**/runs/" in gitignore
