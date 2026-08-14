#!/usr/bin/env python3
"""Fail when a generated SysIDE SVG does not materialize its view graph."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


def _text_labels(svg: Path) -> list[str]:
    try:
        root = ET.parse(svg).getroot()
    except (OSError, ET.ParseError) as exc:
        raise ValueError(f"cannot read SVG {svg}: {exc}") from exc

    labels: list[str] = []
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] != "text":
            continue
        label = "".join(element.itertext()).strip()
        if label:
            labels.append(label)
    return labels


def check_materialization(
    svg: Path,
    *,
    view_name: str,
    required_labels: list[str],
    forbidden_labels: list[str],
    min_flow_count: int,
) -> list[str]:
    labels = _text_labels(svg)
    graph_labels = [label for label in labels if not label.startswith("expose ")]
    errors: list[str] = []

    expected_title = f"«view» {view_name}"
    if expected_title not in graph_labels:
        errors.append(f"missing view title: {expected_title}")

    for required in required_labels:
        if not any(required in label for label in graph_labels):
            errors.append(f"required graph label not materialized: {required}")

    for forbidden in forbidden_labels:
        if any(forbidden in label for label in graph_labels):
            errors.append(f"forbidden graph label materialized: {forbidden}")

    flow_count = sum("«flow»" in label for label in graph_labels)
    if flow_count < min_flow_count:
        errors.append(
            f"materialized flow count {flow_count} is below required {min_flow_count}"
        )

    return errors


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("svg", type=Path)
    parser.add_argument("--view-name", required=True)
    parser.add_argument("--require-label", action="append", default=[])
    parser.add_argument("--forbid-label", action="append", default=[])
    parser.add_argument("--min-flow-count", type=int, default=0)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        errors = check_materialization(
            args.svg,
            view_name=args.view_name,
            required_labels=args.require_label,
            forbidden_labels=args.forbid_label,
            min_flow_count=args.min_flow_count,
        )
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(f"materialization check passed: {args.svg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
