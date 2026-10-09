"""The increments a model declares, found through charters and short names.

Synthetic increments over the model's method layer (the genuine export cut,
so the export passes kernel validation). An increment is the part usage in
the EngineeringIncrement lineage whose declared short name is an increment
identifier; a charter (IncrementTraceObligations lineage) names it through
its ``increment`` value. Nothing is looked up by element name.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from de4sdv.semantic.export_evaluation import export_view, load_export_snapshot
from de4sdv.semantic.increment_discovery import declared_increments
from de4sdv.sysml_api.errors import IdentityNotFoundError
from increment_model_fixtures import ModelBuilder, increment_scenario, method_builder

GIT = "d" * 40


def _snapshot(tmp_path: Path, builder: ModelBuilder):
    path = tmp_path / "export.json"
    path.write_text(json.dumps(builder.export(git_commit=GIT)))
    return load_export_snapshot(path)


def _view(tmp_path: Path, builder: ModelBuilder):
    return export_view(_snapshot(tmp_path, builder))


def _two_increments() -> ModelBuilder:
    builder = method_builder("discovery")
    increment_scenario(builder, increment_id="INC-FIXTURE-002", name="Second")
    increment_scenario(builder, increment_id="INC-FIXTURE-001", name="First")
    return builder


def test_every_increment_with_a_charter_is_found_in_identifier_order(tmp_path: Path) -> None:
    discovery = declared_increments(_view(tmp_path, _two_increments()))
    assert discovery.increment_ids == ("INC-FIXTURE-001", "INC-FIXTURE-002")
    first = discovery.increments[0]
    assert first.usage["qualified_name"] == "DE4SDV_FirstFraming::incFirst"
    assert [c["qualified_name"] for c in first.charters] == ["DE4SDV_FirstFraming::firstCharter"]
    assert discovery.notes == ()


def test_an_identified_increment_without_a_charter_is_still_found(tmp_path: Path) -> None:
    builder = _two_increments()
    framing = next(e for e in builder.elements if e.get("declaredName") == "DE4SDV_FirstFraming")
    definition = next(e for e in builder.elements if e.get("declaredName") == "FirstIncrement")
    builder.usage("PartUsage", "incThird", framing, [definition], short="INC-FIXTURE-003")
    discovery = declared_increments(_view(tmp_path, builder))
    assert discovery.increment_ids == ("INC-FIXTURE-001", "INC-FIXTURE-002", "INC-FIXTURE-003")
    third = discovery.increments[2]
    assert third.charters == ()


def test_a_charter_whose_increment_carries_no_identifier_is_a_note(tmp_path: Path) -> None:
    builder = _two_increments()
    framing = next(e for e in builder.elements if e.get("declaredName") == "DE4SDV_FirstFraming")
    definition = next(e for e in builder.elements if e.get("declaredName") == "FirstIncrement")
    anonymous = builder.usage("PartUsage", "incAnonymous", framing, [definition])
    charter = builder.usage("PartUsage", "anonymousCharter", framing,
                            [builder.kernel_definition("IncrementTraceObligations")])
    builder.attribute(charter, "increment", anonymous, kind="PartUsage")
    discovery = declared_increments(_view(tmp_path, builder))
    assert discovery.increment_ids == ("INC-FIXTURE-001", "INC-FIXTURE-002")
    assert len(discovery.notes) == 1
    note = discovery.notes[0]
    assert "DE4SDV_FirstFraming::anonymousCharter" in note
    assert "DE4SDV_FirstFraming::incAnonymous" in note
    assert "no increment identifier" in note


def test_an_identifier_on_an_element_outside_the_increment_lineage_is_a_note(tmp_path: Path) -> None:
    builder = _two_increments()
    framing = next(e for e in builder.elements if e.get("declaredName") == "DE4SDV_FirstFraming")
    builder.usage("PartUsage", "notAnIncrement", framing, short="INC-FIXTURE-009")
    discovery = declared_increments(_view(tmp_path, builder))
    assert "INC-FIXTURE-009" not in discovery.increment_ids
    assert any("DE4SDV_FirstFraming::notAnIncrement" in note and "INC-FIXTURE-009" in note
               for note in discovery.notes)


def test_an_identifier_on_two_increment_usages_is_listed_once_with_a_note(tmp_path: Path) -> None:
    builder = _two_increments()
    framing = next(e for e in builder.elements if e.get("declaredName") == "DE4SDV_SecondFraming")
    definition = next(e for e in builder.elements if e.get("declaredName") == "SecondIncrement")
    builder.usage("PartUsage", "incSecondCopy", framing, [definition], short="INC-FIXTURE-001")
    discovery = declared_increments(_view(tmp_path, builder))
    assert discovery.increment_ids == ("INC-FIXTURE-001", "INC-FIXTURE-002")
    assert any(note.startswith("2 increment usages carry the identifier INC-FIXTURE-001") for note in discovery.notes)


def test_a_model_without_increments_declares_none(tmp_path: Path) -> None:
    discovery = declared_increments(_view(tmp_path, method_builder("empty")))
    assert discovery.increment_ids == ()
    assert discovery.notes == ()


def test_an_unbound_increment_lineage_is_an_identity_error(tmp_path: Path) -> None:
    # The export is refused before discovery when its kernel identity fails
    # validation; discovery itself fails closed on a view without the binding.
    snapshot = _snapshot(tmp_path, _two_increments())
    unbound = dataclasses.replace(snapshot, kernel_bindings=tuple(
        b for b in snapshot.kernel_bindings if b.ontology_class != "EngineeringIncrement"))
    with pytest.raises(IdentityNotFoundError, match="EngineeringIncrement"):
        declared_increments(export_view(unbound))
