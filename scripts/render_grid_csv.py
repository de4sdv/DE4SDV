#!/usr/bin/env python3
"""Render SysIDE grid-view CSV exports as reviewable SVG tables/matrices."""

from __future__ import annotations

import argparse
import csv
import textwrap
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

FONT_SIZE = 14
LINE_HEIGHT = 20
CELL_PAD_X = 12
CELL_PAD_Y = 10
MIN_COLUMN_WIDTH = 110
MAX_COLUMN_WIDTH = 360
TITLE_HEIGHT = 54
AXIS_TITLE_HEIGHT = 84


@dataclass(frozen=True)
class GridMetadata:
    title: str
    description: str
    row_label: str | None = None
    column_label: str | None = None


GRID_METADATA = {
    "matrix-aebsSystemFunctionMappingView": GridMetadata(
        "AEBS system-function mapping",
        "Maps system functions to conceptual system elements.",
        "system functions (action usages)",
        "conceptual system elements (part usages)",
    ),
    "matrix-aebsPhysicalLogicalMappingView": GridMetadata(
        "AEBS conceptual-to-physical mapping",
        "Maps conceptual system elements to physical/software elements.",
        "conceptual system elements (part usages)",
        "physical/software elements (part usages)",
    ),
    "matrix-aebsSimulationPhysicalLogicalMappingView": GridMetadata(
        "AEBS conceptual-to-simulation mapping",
        "Maps conceptual system elements to simulation/deployment elements.",
        "conceptual system elements (part usages)",
        "simulation/deployment elements (part usages)",
    ),
    "matrix-aebsSimulationPhysicalLogicalItemMappingView": GridMetadata(
        "AEBS conceptual-to-simulation item mapping",
        "Maps conceptual exchange items to simulation/deployment exchange items.",
        "conceptual exchange items",
        "simulation/deployment exchange items",
    ),
    "matrix-middlewareSystemFunctionMappingView": GridMetadata(
        "Middleware system-function mapping",
        "Maps system functions to conceptual system elements.",
        "system functions (action usages)",
        "conceptual system elements (part usages)",
    ),
    "matrix-middlewarePhysicalLogicalMappingView": GridMetadata(
        "Middleware conceptual-to-physical mapping",
        "Maps conceptual system elements to physical/software elements.",
        "conceptual system elements (part usages)",
        "physical/software elements (part usages)",
    ),
    "table-middlewareProductLineClassificationView": GridMetadata(
        "Middleware product-line classification",
        "Classifies middleware characteristics and attaches each rationale to its element.",
    ),
    "table-middlewareStakeholderNeedsView": GridMetadata(
        "Middleware stakeholder needs",
        "Lists stakeholder needs with their authoritative natural-language statements.",
    ),
    "table-middlewareSystemRequirementsView": GridMetadata(
        "Middleware system requirements",
        "Lists system requirements with their authoritative natural-language statements.",
    ),
    "table-aebsStakeholderNeedsView": GridMetadata(
        "AEBS stakeholder needs",
        "Lists stakeholder needs with their authoritative statements.",
    ),
}


def _read_rows(path: Path) -> list[list[str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = [[cell.strip() for cell in row] for row in csv.reader(stream)]
    if not rows:
        raise ValueError(f"grid CSV is empty: {path}")
    width = max(len(row) for row in rows)
    return [row + [""] * (width - len(row)) for row in rows]


def _column_widths(rows: list[list[str]]) -> list[int]:
    widths: list[int] = []
    for column in range(len(rows[0])):
        longest = max(len(row[column]) for row in rows)
        estimated = longest * 8 + 2 * CELL_PAD_X
        widths.append(max(MIN_COLUMN_WIDTH, min(MAX_COLUMN_WIDTH, estimated)))
    return widths


def _wrap(value: str, width_px: int) -> list[str]:
    characters = max(8, (width_px - 2 * CELL_PAD_X) // 8)
    return textwrap.wrap(value, width=characters, break_long_words=False) or [""]


def render_csv(source: Path, output: Path) -> None:
    rows = _read_rows(source)
    widths = _column_widths(rows)
    wrapped = [[_wrap(cell, widths[index]) for index, cell in enumerate(row)] for row in rows]
    row_heights = [
        max(len(cell_lines) for cell_lines in row) * LINE_HEIGHT + 2 * CELL_PAD_Y
        for row in wrapped
    ]
    table_width = sum(widths)
    table_height = sum(row_heights)
    metadata = GRID_METADATA.get(source.stem)
    title = metadata.title if metadata else source.stem
    description = (
        metadata.description
        if metadata
        else f"{title}. Generated from SysIDE grid CSV."
    )
    has_axes = bool(metadata and metadata.row_label and metadata.column_label)
    title_height = AXIS_TITLE_HEIGHT if has_axes else TITLE_HEIGHT
    total_height = title_height + table_height

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{table_width}" '
            f'height="{total_height}" viewBox="0 0 {table_width} {total_height}" '
            f'role="img" aria-labelledby="title description">'
        ),
        f"  <title id=\"title\">{escape(title)}</title>",
        f"  <desc id=\"description\">{escape(description)}</desc>",
        "  <!-- Generated from SysIDE grid CSV; SysML remains authoritative. -->",
        "  <rect width=\"100%\" height=\"100%\" fill=\"#ffffff\"/>",
        f'  <rect x="0" y="0" width="{table_width}" height="{title_height}" fill="#172033"/>',
        (
            f'  <text x="{CELL_PAD_X}" y="34" font-family="Inter, Arial, sans-serif" '
            f'font-size="20" font-weight="700" fill="#ffffff">{escape(title)}</text>'
        ),
    ]

    if has_axes and metadata:
        axis_summary = (
            f"Rows ↓: {metadata.row_label}   |   "
            f"Columns →: {metadata.column_label}"
        )
        parts.append(
            f'  <text x="{CELL_PAD_X}" y="62" font-family="Inter, Arial, sans-serif" '
            f'font-size="13" fill="#d9e2f2">{escape(axis_summary)}</text>'
        )

    y = title_height
    for row_index, row in enumerate(wrapped):
        height = row_heights[row_index]
        background = "#e8eef8" if row_index == 0 else ("#ffffff" if row_index % 2 else "#f6f8fb")
        x = 0
        for column_index, lines in enumerate(row):
            width = widths[column_index]
            parts.append(
                f'  <rect x="{x}" y="{y}" width="{width}" height="{height}" '
                f'fill="{background}" stroke="#9aa7b8" stroke-width="1"/>'
            )
            mapped = any(line in {"✔", "↗", "↙", "X", "x"} for line in lines)
            if mapped and row_index > 0:
                parts.append(
                    f'  <rect x="{x + 3}" y="{y + 3}" width="{width - 6}" '
                    f'height="{height - 6}" rx="5" fill="#dff4e5"/>'
                )
            font_weight = "700" if row_index == 0 or column_index == 0 else "400"
            anchor = "middle" if mapped and row_index > 0 else "start"
            text_x = x + width / 2 if anchor == "middle" else x + CELL_PAD_X
            text_y = y + CELL_PAD_Y + FONT_SIZE
            parts.append(
                f'  <text x="{text_x}" y="{text_y}" font-family="Inter, Arial, sans-serif" '
                f'font-size="{FONT_SIZE}" font-weight="{font_weight}" fill="#172033" '
                f'text-anchor="{anchor}">'
            )
            for line_index, line in enumerate(lines):
                dy = 0 if line_index == 0 else LINE_HEIGHT
                parts.append(
                    f'    <tspan x="{text_x}" dy="{dy}">{escape(line)}</tspan>'
                )
            parts.append("  </text>")
            x += width
        y += height

    parts.append("</svg>")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(parts) + "\n", encoding="utf-8")


def render_directory(source_dir: Path, output_dir: Path) -> list[Path]:
    outputs: list[Path] = []
    for source in sorted(source_dir.glob("*.csv")):
        output = output_dir / f"diagram-{source.stem}.svg"
        render_csv(source, output)
        outputs.append(output)
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render SysIDE grid CSV exports as deterministic SVGs."
    )
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    outputs = render_directory(args.source_dir, args.output_dir)
    if not outputs:
        parser.error(f"no CSV files found in {args.source_dir}")
    for output in outputs:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
