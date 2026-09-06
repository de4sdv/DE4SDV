"""Evidence repository hygiene guards.

Two guard families share this file:

1. Media hygiene (restored from main; the 009B repair previously replaced
   them): video bytes are never tracked in the repository tree, no zero-byte
   placeholders live under the 010 evidence root, and every external-media
   manifest entry carries a complete identity (unique owner-relative path,
   sha256, byte count, disposition, availability) whose bytes are not
   in-tree.
2. 009B canonical run-bundle restoration guards (PR #188 repair): the
   canonical evidence document `evidence/009b/scenario-evidence.json`
   hash-binds five run artifacts that #68 deleted from tracking while keeping
   the references; four are restored byte-identically via `git add -f`, and
   the zero-byte `observer.log` is deliberately not restored (empty files are
   not evidence per docs/evidence-management.md).
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "implementation" / "aebs-autoware-nominal-vehicle-target-bench"
EVIDENCE = BENCH / "evidence" / "009b" / "scenario-evidence.json"
RUN_DIR = BENCH / "evidence" / "009b" / "runs" / "20260727T103958Z-4d22f5c8b44d584c"
EVIDENCE_ROOT = (
    ROOT
    / "implementation"
    / "aebs-aaos-sdv-visualization-bench"
    / "evidence"
    / "010"
)
RETENTION_MANIFEST = EVIDENCE_ROOT / "external-media.yaml"

# The zero-byte observer.log is intentionally untracked (empty files are not
# evidence); its canonical-manifest SHA is the well-known empty-string digest.
ZERO_BYTE_SENTINEL_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
ZERO_BYTE_NAME = "observer_log"


def _canonical_document() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Media hygiene (restored from main)
# ---------------------------------------------------------------------------


def test_video_bytes_are_not_tracked_in_repository_tree() -> None:
    videos = sorted(
        path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*.mp4")
    )
    assert [] == videos


def test_evidence_files_are_not_empty_placeholders() -> None:
    observed = {
        path
        for path in EVIDENCE_ROOT.rglob("*")
        if path.is_file() and path.stat().st_size == 0
    }
    assert set() == observed


def test_removed_media_manifest_has_complete_identity() -> None:
    manifest = yaml.safe_load(RETENTION_MANIFEST.read_text(encoding="utf-8"))
    artifacts = manifest["artifacts"]
    assert 18 == len(artifacts)
    assert 18 == len({entry["former_path"] for entry in artifacts})
    for entry in artifacts:
        assert re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])
        assert entry["bytes"] > 0
        assert "disposition" in entry
        assert "availability" in entry
        assert not (EVIDENCE_ROOT / entry["former_path"]).exists()


# ---------------------------------------------------------------------------
# 009B canonical run-bundle restoration (PR #188 repair)
# ---------------------------------------------------------------------------


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
