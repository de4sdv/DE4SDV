import csv
from pathlib import Path

from scripts.render_grid_csv import GRID_METADATA, render_csv, render_directory


EXPECTED_MAPPING_AXES = {
    "matrix-aebsSystemFunctionMappingView": (
        "system functions (action usages)",
        "conceptual system elements (part usages)",
    ),
    "matrix-aebsPhysicalLogicalMappingView": (
        "conceptual system elements (part usages)",
        "physical/software elements (part usages)",
    ),
    "matrix-aebsSimulationPhysicalLogicalMappingView": (
        "conceptual system elements (part usages)",
        "simulation/deployment elements (part usages)",
    ),
    "matrix-aebsSimulationPhysicalLogicalItemMappingView": (
        "conceptual exchange items",
        "simulation/deployment exchange items",
    ),
    "matrix-mwSystemFunctionMappingView": (
        "system functions (action usages)",
        "conceptual system elements (part usages)",
    ),
    "matrix-mwPhysicalLogicalMappingView": (
        "conceptual system elements (part usages)",
        "physical/software elements (part usages)",
    ),
}


def test_all_saf_mapping_grids_define_human_readable_axes() -> None:
    assert set(EXPECTED_MAPPING_AXES) <= set(GRID_METADATA)
    for stem, (rows, columns) in EXPECTED_MAPPING_AXES.items():
        metadata = GRID_METADATA[stem]
        assert metadata.row_label == rows
        assert metadata.column_label == columns


def test_matrix_svg_labels_row_and_column_element_kinds(tmp_path: Path) -> None:
    source = tmp_path / "matrix-mwSystemFunctionMappingView.csv"
    output = tmp_path / "matrix.svg"
    source.write_text(
        ",signalTranslator\ntranslateSignal,↗\n",
        encoding="utf-8",
    )

    render_csv(source, output)

    svg = output.read_text(encoding="utf-8")
    assert "Rows ↓: system functions (action usages)" in svg
    assert "Columns →: conceptual system elements (part usages)" in svg
    assert "Maps system functions to conceptual system elements." in svg


def test_render_csv_preserves_grid_headers_cells_and_unicode(tmp_path: Path) -> None:
    source = tmp_path / "aebsSystemFunctionMappingView.csv"
    with source.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerows(
            [
                ["Function / Element", "risk & evaluation", "brake coordination"],
                ["assessRisk", "↗", ""],
                ["requestBraking", "", "↗"],
            ]
        )

    output = tmp_path / "diagram-aebsSystemFunctionMappingView.svg"
    render_csv(source, output)

    svg = output.read_text(encoding="utf-8")
    assert "aebsSystemFunctionMappingView" in svg
    assert "risk &amp; evaluation" in svg
    assert "assessRisk" in svg
    assert "requestBraking" in svg
    assert svg.count("↗") == 2
    assert 'role="img"' in svg
    assert "Generated from SysIDE grid CSV" in svg


def test_render_directory_uses_diagram_prefix(tmp_path: Path) -> None:
    source_dir = tmp_path / "csv"
    output_dir = tmp_path / "svg"
    source_dir.mkdir()
    (source_dir / "requirements.csv").write_text(
        "ID,Requirement\nREQ-1,The system shall respond.\n", encoding="utf-8"
    )

    outputs = render_directory(source_dir, output_dir)

    assert outputs == [output_dir / "diagram-requirements.svg"]
    assert outputs[0].is_file()
