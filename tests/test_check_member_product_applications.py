"""The pull-request gate of the derived appliesToMemberProduct fact (#412 R3), on synthetic graphs.

``scripts/check_member_product_applications.py`` runs the derivation of
``de4sdv.semantic.applies_to_member_product`` over the licensed export of a
pull-request head, in the Method Check. A refusal is a technical error that
fails the job. These tests replace the export with the synthetic platform line
of ``tests/test_applies_to_member_product.py`` (generated serializer shapes,
no model file copied) and run the gate's command line on it:

- the clean line derives one member product per governed configuration;
- a second member that owns a usage typed by a projection fails the gate;
- a second part definition with a projection's name in ``product-models/``
  fails the gate.

The genuine export of the head is the Method Check's own input.
"""
from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from scripts import check_member_product_applications as gate
from test_applies_to_member_product import Line

REVISION = "a" * 40


def _model(line: Line) -> dict:
    elements, sources = line.graph.build()
    return {
        "git_commit": REVISION,
        "export_sha256": "0" * 64,
        "elements": elements,
        "element_sources": sources,
        "kernel_bindings": {**line.graph.kernel_bindings(), "MemberProduct": line.member_root},
        "external_references": (),
        "governed_scope": None,
        "library_source": line.graph.library,
    }


def _run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, line: Line, revision: str = REVISION) -> tuple[int, dict, str]:
    monkeypatch.setattr(gate, "load_export", lambda export_path, root=gate.ROOT: _model(line))
    output, summary = tmp_path / "member-products.json", tmp_path / "summary.md"
    code = gate.main(["--export", str(tmp_path / "model-export.json"), "--revision", revision,
                      "--output", str(output), "--summary", str(summary)])
    return code, json.loads(output.read_text(encoding="utf-8")), summary.read_text(encoding="utf-8")


def test_the_clean_line_passes_the_gate_with_one_member_per_governed_configuration(monkeypatch, tmp_path) -> None:
    line = Line()
    code, record, summary = _run(monkeypatch, tmp_path, line)
    assert code == 0
    assert (record["schema"], record["status"], record["revision"]) == (gate.SCHEMA, "derived", REVISION)
    rows = {row["configuration"]: row for row in record["configuration_member_products"]["configurations"]}
    assert rows["standaloneMember"]["member_product"]["element_id"] == line.standalone_product
    assert rows["integratedMember"]["member_product"]["element_id"] == line.configured_member
    assert rows["referenceOnly"]["member_product"] is None
    assert "| `integratedMember` | `IntegratedConfiguredMember` |" in summary


def test_a_second_member_owning_a_usage_typed_by_a_projection_fails_the_gate(monkeypatch, tmp_path) -> None:
    line = Line()
    # The test article specializes the AAOS-integrated member; owning the projection makes it a second member.
    line.usage(line.test_article, "platformStack", line.projections["IntegratedProjection"])
    code, record, summary = _run(monkeypatch, tmp_path, line)
    assert code == 1
    assert record["status"] == "refused"
    assert "MemberProductError" in record["error"] and "applies to 2 member products" in record["error"]
    assert "**Refused**" in summary


def test_a_second_part_definition_with_a_projection_name_in_product_models_fails_the_gate(
        monkeypatch, tmp_path) -> None:
    line = Line()
    line.projection("StandaloneProjection")  # another document of product-models/ declares the same name
    code, record, _summary = _run(monkeypatch, tmp_path, line)
    assert code == 1
    assert record["status"] == "refused" and "matches 2 part definitions" in record["error"]


def test_an_export_of_another_revision_fails_the_gate(monkeypatch, tmp_path) -> None:
    code, record, _summary = _run(monkeypatch, tmp_path, Line(), revision="b" * 40)
    assert code == 1 and "not of " + "b" * 40 in record["error"]


def test_the_gate_reads_the_export_as_the_method_check_and_the_scope_battery_do() -> None:
    """The kernel bindings come from the export's own binding validation (ADR 0011), and the
    derivation takes the production scope validator's record, as the ingestion's battery does."""
    source = inspect.getsource(gate.load_export)
    assert "load_export_snapshot(export_path, None, root=root)" in source
    assert "validate_scope_elements(snapshot.elements, sources)" in source
    assert "governed_scope=model.get(\"governed_scope\")" in inspect.getsource(gate.derive)
