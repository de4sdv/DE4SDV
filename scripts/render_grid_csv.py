#!/usr/bin/env python3
"""Render SysIDE grid-view CSV exports as reviewable SVG tables/matrices."""

from __future__ import annotations

import argparse
import csv
import textwrap
from pathlib import Path
from xml.sax.saxutils import escape

FONT_SIZE = 14
LINE_HEIGHT = 20
CELL_PAD_X = 12
CELL_PAD_Y = 10
MIN_COLUMN_WIDTH = 110
MAX_COLUMN_WIDTH = 360
TITLE_HEIGHT = 54


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
    total_height = TITLE_HEIGHT + table_height
    title = source.stem
    description = f"{title}. Generated from SysIDE grid CSV."

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
        f'  <rect x="0" y="0" width="{table_width}" height="{TITLE_HEIGHT}" fill="#172033"/>',
        (
            f'  <text x="{CELL_PAD_X}" y="34" font-family="Inter, Arial, sans-serif" '
            f'font-size="20" font-weight="700" fill="#ffffff">{escape(title)}</text>'
        ),
    ]

    y = TITLE_HEIGHT
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
