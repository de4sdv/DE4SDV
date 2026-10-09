#!/usr/bin/env python3
"""Evaluate one increment offline against the method gates of a model export.

Reads a full-model JSON export (and, optionally, the validated revision
binding of the same commit), evaluates the increment once, and prints the
requested projections of that one canonical evaluation:

    python scripts/evaluate_increment.py \\
        --export de4sdv-full-model-export.json \\
        [--binding de4sdv-full-model-binding.json] \\
        --increment INC-AEBS-010 [--phase phase4_needs] \\
        [--query status|gaps|next|contract|all] [--output result.json]

Without ``--binding`` the export is evaluated as an export snapshot: kernel
identity is validated from the export by the ingestion validator. Exit codes:
0 evaluated (whatever the verdict), 2 refused (identity mismatch or invalid
input). Read-only; no API, network or repository writes.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.semantic.export_evaluation import ExportEvaluationRefused, evaluate_export  # noqa: E402
from de4sdv.semantic.increment_scope import IncrementIdentifierError  # noqa: E402

QUERIES = ("status", "gaps", "next", "contract")


def run(argv: list[str] | None = None) -> tuple[int, dict, Path | None]:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--export", type=Path, required=True)
    parser.add_argument("--binding", type=Path)
    parser.add_argument("--increment", required=True)
    parser.add_argument("--phase")
    parser.add_argument("--query", choices=(*QUERIES, "all"), default="all")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)

    started = time.perf_counter()
    try:
        snapshot, evaluation = evaluate_export(args.export, args.increment, binding_path=args.binding, root=args.root)
    except (ExportEvaluationRefused, IncrementIdentifierError) as error:
        return 2, {"status": "refused", "reason": str(error)}, args.output
    timings = {"evaluation_seconds": round(time.perf_counter() - started, 3)}
    mark = time.perf_counter()
    projections = {
        "status": lambda: evaluation.status(args.phase),
        "gaps": lambda: evaluation.gaps(args.phase),
        "next": lambda: evaluation.next_obligation(args.phase),
        "contract": lambda: evaluation.phase_contract(args.phase),
    }
    selected = QUERIES if args.query == "all" else (args.query,)
    report = {
        "schema": "de4sdv-increment-evaluation/v1",
        "increment": evaluation.increment_id,
        "evaluation_key": evaluation.evaluation_key,
        "export_sha256": snapshot.export_sha256,
        "identity_mode": snapshot.identity_mode,
        "semantic_authority": snapshot.semantic_authority_id,
        "element_count": len(snapshot.elements),
        **{name: projections[name]() for name in selected},
    }
    timings["projection_seconds"] = round(time.perf_counter() - mark, 3)
    timings["total_seconds"] = round(time.perf_counter() - started, 3)
    report["timings"] = timings
    return 0, report, args.output


def main(argv: list[str] | None = None) -> int:
    code, report, output = run(argv)
    text = json.dumps(report, indent=2, sort_keys=False)
    if output is not None:
        output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
