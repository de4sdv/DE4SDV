"""Parse gate for retained runtime evidence artifacts.

Every evidence artifact referenced by a V&V pilot YAML must be loadable.
E-MW-012 previously shipped with an unquoted colon inside a detail string,
which made the whole artifact unparseable - an unevaluatable evidence file is
a broken chain-of-evidence link, so this gate fails fast on that class of
defect.

Evidence reference categories (mutually exclusive):

- ``file``: an in-tree file that must exist; structured suffixes must parse.
- ``artifact_directory``: an in-tree directory that must exist; a directory
  can never satisfy a raw evidence-file reference.
- ``external_media``: bytes held outside Git under the evidence policy. The
  pilot may reference the media only through the external-media manifest
  identity (owner-relative former_path + sha256 + bytes + availability); the manifest
  records identity, not byte availability or runtime behavior.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[1]
EVIDENCE_010 = ROOT / "implementation/aebs-aaos-sdv-visualization-bench/evidence/010"
EXTERNAL_MEDIA_MANIFEST = EVIDENCE_010 / "external-media.yaml"
PILOTS = [
    ROOT / "methodologies/sysmod-sysmlv2/pilots/middleware-v-and-v-evidence.yaml",
    ROOT / "methodologies/sysmod-sysmlv2/pilots/aebs-needs-requirements.yaml",
    ROOT
    / "methodologies/sysmod-sysmlv2/pilots/aebs-010-visualization-evidence.yaml",
]

EVIDENCE_PREFIX = "implementation/"
EVIDENCE_MARKER = "evidence/"


def _referenced_evidence(data, paths):
    """Collect artifact paths referenced from known evidence-bearing fields."""
    if isinstance(data, dict):
        for key, value in data.items():
            if key in ("artifact", "evidence") and isinstance(value, str):
                if value.startswith(EVIDENCE_PREFIX) and EVIDENCE_MARKER in value:
                    paths.add(value)
            elif key == "current_evidence" and isinstance(value, list):
                for item in value:
                    if (
                        isinstance(item, str)
                        and item.startswith(EVIDENCE_PREFIX)
                    ):
                        paths.add(item)
            else:
                _referenced_evidence(value, paths)
    elif isinstance(data, list):
        for item in data:
            _referenced_evidence(item, paths)
    return paths


PILOT_EVIDENCE_SUFFIXES = {".yaml", ".yml", ".json"}


def _is_machine_evaluable(rel: str) -> bool:
    """Only structured artifacts are parse-gated; logs/media are raw records."""
    suffix = rel.rsplit(".", 1)[-1].lower() if "." in rel else ""
    return f".{suffix}" in PILOT_EVIDENCE_SUFFIXES


def _external_media_artifacts() -> list[dict]:
    manifest = yaml.safe_load(
        EXTERNAL_MEDIA_MANIFEST.read_text(encoding="utf-8")
    )
    return manifest["artifacts"]


def _external_media_identity(rel: str) -> dict | None:
    """Resolve exactly within the manifest's owning evidence directory."""
    if Path(rel).is_absolute():
        return None
    owner = EXTERNAL_MEDIA_MANIFEST.parent.resolve()
    target = (ROOT / rel).resolve()
    if not target.is_relative_to(owner):
        return None
    matches = []
    for entry in _external_media_artifacts():
        former = Path(entry["former_path"])
        assert not former.is_absolute(), "absolute external-media former_path"
        candidate = (owner / former).resolve()
        assert candidate.is_relative_to(owner), "external-media path escapes owner"
        if candidate == target:
            matches.append(entry)
    assert len(matches) <= 1, f"ambiguous external-media identity for {rel}"
    return matches[0] if matches else None


def test_every_referenced_evidence_artifact_parses_and_exists():
    seen = set()
    for pilot in PILOTS:
        data = yaml.safe_load(pilot.read_text(encoding="utf-8"))
        seen |= _referenced_evidence(data, set())
    # The MW baseline evidence set is the known minimum.
    assert any("e-mw-011" in p for p in seen), (
        "MW pilot no longer references the retained runtime campaign evidence"
    )
    for rel in sorted(seen):
        path = ROOT / rel
        if path.is_dir():
            raise AssertionError(
                f"evidence artifact reference resolves to a directory, not a "
                f"file: {rel} (directories cannot satisfy file evidence)"
            )
        if not path.is_file():
            entry = _external_media_identity(rel)
            assert entry is not None, (
                f"missing evidence artifact without an external-media "
                f"manifest identity: {rel}"
            )

            assert len(entry["sha256"]) == 64
            assert entry["bytes"] > 0
            assert entry.get("availability"), (
                f"external-media entry lacks availability status: {rel}"
            )
            continue
        if not _is_machine_evaluable(rel):
            continue
        text = path.read_text(encoding="utf-8")
        if rel.endswith(".json"):
            try:
                json.loads(text)
            except json.JSONDecodeError as exc:  # pragma: no cover
                raise AssertionError(f"unparseable evidence artifact {rel}: {exc}")
        else:
            try:
                yaml.safe_load(text)
            except yaml.YAMLError as exc:  # pragma: no cover - message context
                raise AssertionError(f"unparseable evidence artifact {rel}: {exc}")


def test_pilot_evidence_ladder_directories_exist():
    """artifact_directory references must exist as directories in-tree."""
    for pilot in PILOTS:
        data = yaml.safe_load(pilot.read_text(encoding="utf-8"))

        def collect(node):
            if isinstance(node, dict):
                for key, value in node.items():
                    if key == "artifact_directory" and isinstance(value, str):
                        path = ROOT / value
                        assert path.is_dir(), (
                            f"artifact_directory does not exist: {value}"
                        )
                    else:
                        collect(value)
            elif isinstance(node, list):
                for item in node:
                    collect(item)

        collect(data)


def test_external_media_manifest_records_v21_raw_take():
    """The v21 raw take is manifested externally, not pretended in-tree."""
    entry = _external_media_identity(
        "implementation/aebs-aaos-sdv-visualization-bench/evidence/010/"
        "forward-ui/final-hmi-v21-corrected/raw-continuous.mp4"
    )
    assert entry is not None, "v21 raw take must keep its manifest identity"
    assert entry["disposition"] == "observed_bounded"
    assert entry["availability"] == "maintainer_archive"
    assert not (EVIDENCE_010 / entry["former_path"]).exists()


def test_counterclaims_trace_to_modeled_gaps():
    """Every pilot counterclaim-bearing gap must be modeled (added by #177)."""
    pilot = yaml.safe_load(
        PILOTS[2].read_text(encoding="utf-8")
    )
    model = (
        ROOT
        / "textual-notation-of-model/packages/features/aebs/"
        "aebs_visualization_verification_evidence.sysml"
    ).read_text(encoding="utf-8")
    for gap in pilot.get("runtime_evidence_gaps", []):
        element = gap.get("model_element")
        assert element, f"gap {gap.get('id')} lacks a model_element binding"
        assert f"part {element}" in model, (
            f"gap model element missing from the slice: {element}"
        )


def test_execution_records_match_their_artifact_timestamps():
    mw = yaml.safe_load(
        (
            ROOT
            / "methodologies/sysmod-sysmlv2/pilots/middleware-v-and-v-evidence.yaml"
        ).read_text(encoding="utf-8")
    )
    for record in mw["execution_records"]["records"]:
        artifact = yaml.safe_load(
            (ROOT / record["artifact"]).read_text(encoding="utf-8")
        )
        assert record["runs"] == "single", record["evidence_id"]
        if "recorded_at" in record:
            assert str(artifact.get("recorded_at", "")).replace("T", " ")[:19].startswith(
                record["recorded_at"][:19].replace("T", " ")
            ), record["evidence_id"]
        if "started_at" in record:
            assert str(artifact.get("started_at", "")).replace("T", " ")[:19].startswith(
                record["started_at"][:19].replace("T", " ")
            ), record["evidence_id"]
        if "finished_at" in record:
            assert str(artifact.get("finished_at", "")).replace("T", " ")[:19].startswith(
                record["finished_at"][:19].replace("T", " ")
            ), record["evidence_id"]

def test_model_raw_observation_artifact_references_resolve():
    """Model-side rawObservationArtifact strings must resolve like pilot
    references: in-tree file, or an external-media identity (reviewer minor
    #3: model strings were previously unguarded)."""
    model_text = (
        ROOT
        / "textual-notation-of-model/packages/features/aebs/"
        "aebs_visualization_verification_evidence.sysml"
    ).read_text(encoding="utf-8")
    artifacts = re.findall(
        r'rawObservationArtifact\s*=\s*"([^"]+)"', model_text
    )
    assert artifacts, "evidence parts must name raw observation artifacts"
    for rel in artifacts:
        path = ROOT / rel
        if path.is_file():
            continue
        assert _external_media_identity(rel) is not None, (
            f"model rawObservationArtifact neither in-tree nor in "
            f"external-media.yaml: {rel}"
        )


def test_pilot_model_artifact_paths_exist():
    """Pilot model_artifacts.configured_test_article / evidence_index
    references must exist in-tree (reviewer minor #3)."""
    pilot = yaml.safe_load(PILOTS[2].read_text(encoding="utf-8"))
    model_artifacts = pilot.get("model_artifacts", {})
    for key in ("configured_test_article", "evidence_index"):
        rel = model_artifacts.get(key)
        assert rel, f"pilot model_artifacts.{key} missing"
        assert (ROOT / rel).is_file(), f"missing: {rel}"


def test_external_identity_is_owner_scoped(tmp_path, monkeypatch):
    monkeypatch.setitem(globals(), "ROOT", tmp_path)
    monkeypatch.setitem(globals(), "EXTERNAL_MEDIA_MANIFEST", tmp_path / "campaign-a/external-media.yaml")
    entries = [{"former_path": "take/raw.mp4"}]
    monkeypatch.setitem(globals(), "_external_media_artifacts", lambda: entries)
    assert _external_media_identity("campaign-a/take/raw.mp4") == entries[0]
    assert _external_media_identity("campaign-a/take/./raw.mp4") == entries[0]
    assert _external_media_identity("campaign-b/take/raw.mp4") is None
    assert _external_media_identity("campaign-a/../campaign-b/take/raw.mp4") is None
    assert _external_media_identity(str(tmp_path / "campaign-a/take/raw.mp4")) is None
    entries.append({"former_path": "take/./raw.mp4"})
    with pytest.raises(AssertionError, match="ambiguous"):
        _external_media_identity("campaign-a/take/raw.mp4")


@pytest.mark.parametrize("former", ["../campaign-b/raw.mp4", "/tmp/raw.mp4"])
def test_external_identity_rejects_manifest_escape(tmp_path, monkeypatch, former):
    monkeypatch.setitem(globals(), "ROOT", tmp_path)
    monkeypatch.setitem(globals(), "EXTERNAL_MEDIA_MANIFEST", tmp_path / "campaign-a/external-media.yaml")
    monkeypatch.setitem(globals(), "_external_media_artifacts", lambda: [{"former_path": former}])
    with pytest.raises(AssertionError):
        _external_media_identity("campaign-a/raw.mp4")
