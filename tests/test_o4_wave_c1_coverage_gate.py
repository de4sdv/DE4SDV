"""O4 Wave C1: coverage-gate kernel accounting and the blocking retained residual.

Two changes are under test:

- the governed-kernel declaration accounting that used to live in sync point 5
  of ``scripts/check_model_sync.py`` (kernel -> ontology direction and the
  feature-slice re-declaration guard) is enforced by the model-projection
  coverage gate, against model-projected pins and the kernel-internal
  declarations manifest (owner decision D3);
- a non-empty retained residual blocks regardless of the baseline, while the
  two owner-visible exceptions stay ratcheted until Wave C2.

Every failure mode is induced on a live copy (tampered file text served to the
gate) and attributed to a named error, per the declarative-artifact-testing
approach of the replaced ``tests/test_ontology_kernel_contract.py`` cases.
"""

from __future__ import annotations

import copy
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

import pytest
import yaml

from de4sdv.semantic import model_projection_coverage as coverage

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / coverage.KERNEL_INTERNAL_PATH
GOVERNED_DIR = "textual-notation-of-model/packages/methods/de4sdv"


@contextmanager
def _served(texts: dict[Path, str]):
    """Serve tampered texts for the given paths to every reader."""
    original = Path.read_text

    def fake_read(self, *args, **kwargs):
        if self in texts:
            return texts[self]
        return original(self, *args, **kwargs)

    with mock.patch.object(Path, "read_text", fake_read):
        yield


def _manifest() -> dict:
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))


def _report_with_manifest(document: dict) -> dict:
    with _served({MANIFEST: yaml.safe_dump(document, sort_keys=False)}):
        return coverage.build_report(ROOT)


def _accounting_errors(report: dict) -> list[str]:
    return list(report["kernel_accounting_errors"])


# -- clean repository --------------------------------------------------------


def test_clean_repository_has_no_kernel_accounting_errors():
    report = coverage.build_report(ROOT)
    assert _accounting_errors(report) == []
    assert coverage.compare(report, coverage.load_baseline(ROOT)) == []
    assert report["mode"] == coverage.MODE == "blocking-retained"


def test_kernel_internal_manifest_is_the_exclusion_source():
    report = coverage.build_report(ROOT)
    manifest = _manifest()
    excluded = {key: value["reason"] for key, value in report["kernel_declarations"].items()
                if value["status"] == "excluded"}
    expected = {f"{file}::{declaration}": reason
                for file, declarations in manifest["declarations"].items()
                for declaration, reason in declarations.items()}
    assert len(expected) == 87
    # Every excluded declaration comes from the manifest with its reason; a
    # listed declaration that is a relationship-carrier pin reports as
    # projected (a carrier is not class vocabulary), never as residual.
    assert excluded.items() <= expected.items()
    for key in expected.keys() - excluded.keys():
        assert report["kernel_declarations"][key]["status"] == "projected", key
    assert manifest["governed_directory"] == GOVERNED_DIR


def test_kernel_internal_manifest_carries_no_binding_block():
    assert "binding" not in _manifest()
    assert _manifest()["schema"] == coverage.KERNEL_INTERNAL_SCHEMA


# -- kernel -> model direction (relocated from sync point 5) ----------------


def test_catches_unclassified_new_kernel_declaration():
    process = ROOT / GOVERNED_DIR / "de4sdv_method_process.sysml"
    original = process.read_text(encoding="utf-8")
    tampered = original.replace(
        "enum def IncrementSize {",
        "part def BrandNewConcept {\n  }\n\n  enum def IncrementSize {",
    )
    assert tampered != original
    with _served({process: tampered}):
        report = coverage.build_report(ROOT)
    errors = _accounting_errors(report)
    assert any("BrandNewConcept" in e and "unclassified" in e for e in errors), errors
    # Blocking regardless of the baseline (not a ratchet entry).
    assert any("BrandNewConcept" in e for e in coverage.compare(
        report, coverage.baseline_from_report(report)))


def test_catches_stale_exclusion_after_rename():
    document = _manifest()
    rel_file = next(iter(document["declarations"]))
    first = next(iter(document["declarations"][rel_file]))
    del document["declarations"][rel_file][first]
    document["declarations"][rel_file]["part def Ghost"] = "stale"
    errors = _accounting_errors(_report_with_manifest(document))
    assert any("Ghost" in e and "stale" in e for e in errors), errors


def test_catches_exclusion_with_empty_reason():
    document = _manifest()
    rel_file = next(iter(document["declarations"]))
    first = next(iter(document["declarations"][rel_file]))
    document["declarations"][rel_file][first] = ""
    errors = _accounting_errors(_report_with_manifest(document))
    assert any("non-empty reason" in e for e in errors), errors


def test_catches_projection_and_exclusion_overlap():
    document = _manifest()
    document["declarations"].setdefault(
        GOVERNED_DIR + "/de4sdv_method_context.sysml", {}
    )["part def EngineeringIncrement"] = "double bookkeeping"
    errors = _accounting_errors(_report_with_manifest(document))
    assert any("EngineeringIncrement" in e and "both projected and listed" in e
               for e in errors), errors


def test_catches_exclusion_outside_governed_directory():
    document = _manifest()
    document["declarations"]["somewhere/else.sysml"] = {"part def Thing": "not governed"}
    errors = _accounting_errors(_report_with_manifest(document))
    assert any("outside the governed directory" in e for e in errors), errors


@pytest.mark.parametrize("mutate, needle", [
    (lambda d: d.pop("declarations"), "declarations"),
    (lambda d: d.update(schema="other/v1"), "schema"),
    (lambda d: d.update(governed_directory="../escape"), "governed directory"),
    (lambda d: d.update(binding={}), "binding"),
])
def test_malformed_manifest_fails_closed(mutate, needle):
    document = _manifest()
    mutate(document)
    errors = _accounting_errors(_report_with_manifest(document))
    assert errors and any(needle in e for e in errors), errors


def test_manifest_must_equal_the_authored_list_until_wave_c2():
    """No second, drifting home while the authored list still exists."""
    document = _manifest()
    rel_file = next(iter(document["declarations"]))
    first = next(iter(document["declarations"][rel_file]))
    document["declarations"][rel_file][first] = "a different reason"
    errors = _accounting_errors(_report_with_manifest(document))
    assert any("differs from the authored ontology list" in e for e in errors), errors


# -- feature-slice guard (relocated from sync point 5) ----------------------


def test_catches_slice_redeclaration_of_projected_kernel_name():
    slice_path = ROOT / (
        "textual-notation-of-model/packages/features/aebs/aebs_needs_requirements.sysml"
    )
    original = slice_path.read_text(encoding="utf-8")
    with _served({slice_path: original + "\npart def RequirementCandidate {}\n"}):
        report = coverage.build_report(ROOT)
    errors = _accounting_errors(report)
    assert any("re-declares projected kernel name 'RequirementCandidate'" in e
               for e in errors), errors


def test_slice_guard_derives_names_from_projection_not_a_list():
    import inspect

    source = inspect.getsource(coverage.kernel_accounting)
    assert "_PROTECTED_CONCEPTS" not in source


# -- retained residual (blocking) -------------------------------------------


def test_non_empty_retained_residual_blocks_even_when_the_baseline_lists_it():
    report = coverage.build_report(ROOT)
    planted = dict(report, residual=sorted(report["residual"] + ["PlantedRetained"]),
                   retained_residual=["PlantedRetained"])
    baseline = coverage.baseline_from_report(planted)
    errors = coverage.compare(planted, baseline)
    assert any("retained residual" in e and "PlantedRetained" in e for e in errors), errors


def test_owner_visible_exceptions_stay_ratcheted_and_allowed():
    report = coverage.build_report(ROOT)
    assert report["exceptions"] == ["IncrementTraceabilityShell", "derivesNeedFromConcern"]
    assert coverage.compare(report, coverage.load_baseline(ROOT)) == []
    # Still a ratchet: an extra exception not in the baseline fails.
    grown = dict(report, exceptions=report["exceptions"] + ["PlantedException"])
    assert any("PlantedException" in e for e in coverage.compare(
        grown, coverage.load_baseline(ROOT)))


def test_baseline_records_the_blocking_mode():
    baseline = coverage.load_baseline(ROOT)
    assert baseline["schema"] == coverage.BASELINE_SCHEMA
    assert baseline["mode"] == "blocking-retained"
    assert baseline["retained_residual"] == []
    stale = copy.deepcopy(baseline)
    stale["mode"] = "shadow"
    assert any("mode" in e for e in coverage.compare(coverage.build_report(ROOT), stale))
