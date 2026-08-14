import csv
import importlib.util
from pathlib import Path


SCRIPT = Path("scripts/render_grid_csv.py")


def _load_module():
    spec = importlib.util.spec_from_file_location("render_grid_csv", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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

    module = _load_module()
    output = tmp_path / "diagram-aebsSystemFunctionMappingView.svg"
    module.render_csv(source, output)

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

    module = _load_module()
    outputs = module.render_directory(source_dir, output_dir)

    assert outputs == [output_dir / "diagram-requirements.svg"]
    assert outputs[0].is_file()
