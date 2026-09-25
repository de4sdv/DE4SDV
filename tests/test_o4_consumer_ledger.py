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


# ---------------------------------------------------------------------------
# check_repo gate registration (sentinel + spy)
# ---------------------------------------------------------------------------


def _passing_gate_mocks():
    from unittest import mock

    from de4sdv.semantic import (
        definition_projection,
        external_reference_contract,
        vocabulary_carrier,
    )
    from scripts import check_repo

    return (
        mock.patch.object(vocabulary_carrier, "run_check_errors", return_value=[]),
        mock.patch.object(
            external_reference_contract, "run_check_errors", return_value=[]
        ),
        mock.patch.object(definition_projection, "run_check_errors", return_value=[]),
        mock.patch.object(check_repo, "find_duplicate_global_packages", return_value={}),
        mock.patch.object(
            check_repo.validate_aebs_executable_bench, "validate_bench", return_value=[]
        ),
        mock.patch.object(check_repo.check_model_sync, "run_all_checks", return_value=[]),
        mock.patch.object(
            check_repo.generate_scenario_manifest, "run_check_errors", return_value=[]
        ),
        mock.patch.object(check_repo.check_naming, "run_all_checks", return_value=[]),
        mock.patch.object(
            check_repo.generate_semantic_authority_inventory,
            "run_check_errors",
            return_value=[],
        ),
        mock.patch.object(
            check_repo.generate_semantic_projection_v1,
            "run_check_errors",
            return_value=[],
        ),
        mock.patch.object(
            check_repo.generate_semantic_projection_o22,
            "run_check_errors_o22",
            return_value=[],
        ),
        mock.patch.object(
            check_repo.generate_semantic_projection_o23,
            "run_check_errors_o23",
            return_value=[],
        ),
        mock.patch.object(
            check_repo.generate_semantic_projection_o2p,
            "run_check_errors_o2p",
            return_value=[],
        ),
        mock.patch.object(check_repo.validate_review, "run_check_errors", return_value=[]),
        mock.patch.object(
            check_repo.generate_o4_execution_register, "run_check_errors", return_value=[]
        ),
        mock.patch.object(
            check_repo.check_o4_lifecycle_consistency, "run_all_checks", return_value=[]
        ),
    )


def test_check_repo_fails_when_consumer_ledger_gate_fails():
    from unittest import mock

    from de4sdv.semantic import o4_consumers
    from scripts import check_repo

    mocks = _passing_gate_mocks()
    for m in mocks:
        m.start()
    try:
        with mock.patch.object(
            o4_consumers,
            "load_and_check",
            return_value=["sentinel consumer-ledger error"],
        ):
            assert check_repo.main() == 1
    finally:
        for m in mocks:
            m.stop()


def test_check_repo_invokes_the_consumer_ledger_gate():
    from unittest import mock

    from de4sdv.semantic import o4_consumers
    from scripts import check_repo

    calls: list = []
    original = o4_consumers.load_and_check

    def spy(root):
        calls.append(root)
        return original(root)

    mocks = _passing_gate_mocks()
    for m in mocks:
        m.start()
    try:
        with mock.patch.object(o4_consumers, "load_and_check", side_effect=spy):
            code = check_repo.main()
    finally:
        for m in mocks:
            m.stop()
    assert calls, "check_repo did not invoke the consumer-ledger gate"
    assert code == 0
