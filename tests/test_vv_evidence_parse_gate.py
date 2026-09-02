"""Parse gate for retained runtime evidence artifacts.

Every evidence artifact referenced by a V&V pilot YAML must be loadable.
E-MW-012 previously shipped with an unquoted colon inside a detail string,
which made the whole artifact unparseable - an unevaluatable evidence file is
a broken chain-of-evidence link, so this gate fails fast on that class of
defect.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
PILOTS = [
    ROOT / "methodologies/sysmod-sysmlv2/pilots/middleware-v-and-v-evidence.yaml",
    ROOT / "methodologies/sysmod-sysmlv2/pilots/aebs-needs-requirements.yaml",
]


def _referenced_evidence(data, paths):
    """Collect artifact paths referenced from known evidence-bearing fields."""
    if isinstance(data, dict):
        for key, value in data.items():
            if key in ("artifact", "evidence") and isinstance(value, str):
                if value.startswith("implementation/") and "evidence/" in value:
                    paths.add(value)
            elif key == "current_evidence" and isinstance(value, list):
                for item in value:
                    if isinstance(item, str) and item.startswith("implementation/"):
                        paths.add(item)
            else:
                _referenced_evidence(value, paths)
    elif isinstance(data, list):
        for item in data:
            _referenced_evidence(item, paths)
    return paths


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
        assert path.is_file(), f"missing evidence artifact: {rel}"
        try:
            yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:  # pragma: no cover - message context
            raise AssertionError(f"unparseable evidence artifact {rel}: {exc}")


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
