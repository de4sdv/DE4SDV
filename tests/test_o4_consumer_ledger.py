"""O4 consumer-ledger preparation machinery: fail-closed detection, no cutover."""
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "de4sdv").mkdir(parents=True)
    (root / "de4sdv" / "reader.py").write_text(
        "from de4sdv.semantic.kernel_contract import KernelContract\n"
        "ONTOLOGY = 'approach/framework/ontology/de4sdv-basic-ontology.yaml'\n",
        encoding="utf-8",
    )
    (root / "docs").mkdir()
    (root / "docs" / "note.md").write_text(
        "Mentions Legacy-Yaml and de4sdv-basic-ontology.\n", encoding="utf-8"
    )
    (root / "unrelated.py").write_text("print('nothing')\n", encoding="utf-8")
    return root


def _files(root: Path) -> list[str]:
    return [
        str(p.relative_to(root))
        for p in sorted(root.rglob("*"))
        if p.is_file()
    ]


def test_scan_is_case_insensitive_and_file_type_agnostic(tmp_path):
    from de4sdv.semantic.o4_consumers import scan_files

    root = _repo(tmp_path)
    hits = scan_files(root, _files(root))
    assert "de4sdv/reader.py" in hits
    assert "docs/note.md" in hits
    assert "unrelated.py" not in hits
    assert set(hits["docs/note.md"]["markers"]) >= {"legacy_yaml_authority"}


def test_check_requires_exact_file_set_equality(tmp_path):
    from de4sdv.semantic.o4_consumers import check_ledger, scan_files

    root = _repo(tmp_path)
    scan = scan_files(root, _files(root))
    ledger = {"version": "de4sdv.o4-consumer-ledger/v1", "entries": {
        "docs/stale.md": {"role": "documentation", "markers": ["legacy_yaml_authority"],
                          "retirement_status": "active"}}}
    errors = check_ledger(root, ledger, scan)
    assert any("missing from the ledger" in e for e in errors)
    assert any("no live scan" in e for e in errors)


def test_retired_entry_with_live_consumption_fails(tmp_path):
    from de4sdv.semantic.o4_consumers import check_ledger, scan_files

    root = _repo(tmp_path)
    files = _files(root)
    scan = scan_files(root, files)
    entries = {
        path: {
            "role": "gate" if path.endswith(".py") and "de4sdv" in path else "documentation",
            "markers": sorted(info["markers"]),
            "retirement_status": "retired" if path == "de4sdv/reader.py" else "active",
        }
        for path, info in scan.items()
    }
    errors = check_ledger(root, {"entries": entries}, scan)
    assert any("retired" in e and "still consumes" in e for e in errors)


def test_marker_drift_fails_closed(tmp_path):
    from de4sdv.semantic.o4_consumers import check_ledger, scan_files

    root = _repo(tmp_path)
    scan = scan_files(root, _files(root))
    entries = {
        path: {"role": "documentation", "markers": sorted(info["markers"]),
               "retirement_status": "active"}
        for path, info in scan.items()
    }
    entries["de4sdv/reader.py"]["markers"] = ["legacy_yaml_authority", "gate"]
    errors = check_ledger(root, {"entries": entries}, scan)
    assert any("marker" in e for e in errors)


def test_unknown_role_and_status_fail(tmp_path):
    from de4sdv.semantic.o4_consumers import check_ledger, scan_files

    root = _repo(tmp_path)
    scan = scan_files(root, _files(root))
    entries = {
        path: {"role": "mystery", "markers": sorted(info["markers"]),
               "retirement_status": "later"}
        for path, info in scan.items()
    }
    errors = check_ledger(root, {"entries": entries}, scan)
    assert any("role" in e for e in errors)
    assert any("retirement_status" in e for e in errors)


def test_committed_ledger_matches_the_real_tree():
    from de4sdv.semantic.o4_consumers import (
        LEDGER_PATH, check_ledger, load_ledger, scan_tracked_files,
    )

    ledger = load_ledger(REPO_ROOT / LEDGER_PATH)
    scan = scan_tracked_files(REPO_ROOT)
    errors = check_ledger(REPO_ROOT, ledger, scan)
    assert errors == [], errors


def test_unreadable_tracked_file_fails_closed(tmp_path):
    from de4sdv.semantic.o4_consumers import ConsumerScanError, scan_files

    root = _repo(tmp_path)
    files = _files(root) + ["missing_file.md"]
    with pytest.raises(ConsumerScanError):
        scan_files(root, files)