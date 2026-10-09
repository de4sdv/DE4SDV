"""O4 Wave C1: coverage-gate kernel accounting and the blocking retained residual.

Two changes are under test:

- the governed-kernel declaration accounting that used to live in sync point 5
  of ``scripts/check_model_sync.py`` (kernel -> ontology direction and the
  feature-slice re-declaration guard) is enforced by the model-projection
  coverage gate, against model-projected pins and the kernel-internal
  declarations manifest (owner decision D3);
- a non-empty retained residual blocks regardless of the baseline, while the
  two owner-visible exceptions stay ratcheted until Wave C2.

O4 Wave C2 closed the transition: the mode is ``blocking`` (any residual
identity or declaration blocks), the two exceptions are refused with their
register disposition and the five former aliases are retired (both ratcheted
in the baseline), the D3 manifest lost the six relationship-carrier pins
(81 entries; listed and projected are a disjoint union) and the C1
transition lock against the authored list is gone with the authored ontology.
Replaced in C2: ``test_manifest_must_equal_the_authored_list_until_wave_c2``
(-> ``test_listed_carrier_pin_is_a_second_home``),
``test_non_empty_retained_residual_blocks_even_when_the_baseline_lists_it``
(-> ``test_any_residual_blocks_even_when_the_baseline_lists_it``),
``test_owner_visible_exceptions_stay_ratcheted_and_allowed``
(-> ``test_refused_and_retired_identities_are_ratcheted``).

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
    assert report["mode"] == coverage.MODE == "blocking"
    assert report["residual"] == [] and report["residual_declarations"] == []


def test_kernel_internal_manifest_is_the_exclusion_source():
    report = coverage.build_report(ROOT)
    manifest = _manifest()
    excluded = {key: value["reason"] for key, value in report["kernel_declarations"].items()
                if value["status"] == "excluded"}
    expected = {f"{file}::{declaration}": reason
                for file, declarations in manifest["declarations"].items()
                for declaration, reason in declarations.items()}
    assert len(expected) == 101  # + AssuranceClaim, AssuranceArgument, AssuranceCounterClaim
    # Every listed declaration is excluded with exactly its reason (disjoint
    # union: none is also projected).
    assert excluded == expected
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
    assert any("EngineeringIncrement" in e and "is both projected" in e
               and "listed as kernel-internal" in e for e in errors), errors


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
    # Since C2 the manifest is also a model-contract input: a manifest the
    # contract cannot be built from makes the gate unevaluable (fails closed).
    document = _manifest()
    mutate(document)
    with _served({MANIFEST: yaml.safe_dump(document, sort_keys=False)}):
        errors = coverage.run_check_errors(ROOT)
    assert errors and any(needle in e for e in errors), errors


def test_listed_carrier_pin_is_a_second_home():
    """D3 (C2): a relationship-carrier pin projected by a model layer must
    not also be listed (the six C1 carry-overs were removed)."""
    document = _manifest()
    document["declarations"].setdefault(
        GOVERNED_DIR + "/de4sdv_method_context.sysml", {}
    )["connection def HasStakeholder"] = "carry-over"
    errors = _accounting_errors(_report_with_manifest(document))
    assert any("HasStakeholder" in e and "is both projected" in e for e in errors), errors


def test_the_six_carrier_pins_are_projected_not_listed():
    report = coverage.build_report(ROOT)
    listed = {declaration for declarations in _manifest()["declarations"].values()
              for declaration in declarations}
    for name in ("HasStakeholder", "AddressesConcern", "ProducesView", "RecordsAssumption",
                 "RecordsGap", "SelectedViewpoint"):
        keys = [k for k in report["kernel_declarations"] if k.endswith(f" def {name}")]
        assert len(keys) == 1, (name, keys)
        assert report["kernel_declarations"][keys[0]]["status"] == "projected", name
        assert not any(d.endswith(f" def {name}") for d in listed), name


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


def test_any_residual_blocks_even_when_the_baseline_lists_it():
    report = coverage.build_report(ROOT)
    planted = dict(report, residual=sorted(report["residual"] + ["PlantedRetained"]))
    baseline = coverage.baseline_from_report(planted)
    errors = coverage.compare(planted, baseline)
    assert any("residual is blocking" in e and "PlantedRetained" in e for e in errors), errors
    declaration = dict(report, residual_declarations=["x.sysml::part def Planted"])
    errors = coverage.compare(declaration, coverage.baseline_from_report(declaration))
    assert any("residual is blocking" in e and "Planted" in e for e in errors), errors


def test_refused_and_retired_identities_are_ratcheted():
    report = coverage.build_report(ROOT)
    assert report["refused"] == ["IncrementTraceabilityShell", "derivesNeedFromConcern"]
    assert report["retired"] == sorted(["realizedBy", "deployedTo", "validatedBy",
                                        "constrainedBy", "validatesFitnessForUse"])
    baseline = coverage.load_baseline(ROOT)
    assert coverage.compare(report, baseline) == []
    for key in ("refused", "retired"):
        grown = dict(report, **{key: report[key] + ["PlantedName"]})
        assert any("PlantedName" in e and "drift" in e
                   for e in coverage.compare(grown, baseline)), key
        shrunk = dict(report, **{key: report[key][1:]})
        assert any("update the baseline" in e for e in coverage.compare(shrunk, baseline)), key


def test_baseline_records_the_blocking_mode():
    baseline = coverage.load_baseline(ROOT)
    assert baseline["schema"] == coverage.BASELINE_SCHEMA
    assert baseline["mode"] == "blocking"
    assert "retained_residual" not in baseline and "exceptions" not in baseline
    stale = copy.deepcopy(baseline)
    stale["mode"] = "blocking-retained"
    assert any("mode" in e for e in coverage.compare(coverage.build_report(ROOT), stale))
