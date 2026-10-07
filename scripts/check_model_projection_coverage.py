#!/usr/bin/env python3
"""Model-projection coverage gate (shadow ratchet) — CLI.

    python scripts/check_model_projection_coverage.py            # check vs baseline
    python scripts/check_model_projection_coverage.py --json OUT # write the report
    python scripts/check_model_projection_coverage.py --bundle B # also verify a bundle
    python scripts/check_model_projection_coverage.py --write-baseline

Exit 0 = no drift (residual may be non-empty in shadow mode); 1 = drift,
duplicate providers or bundle digest mismatch.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.semantic import model_projection_coverage as coverage  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", type=Path, help="write the full coverage report")
    parser.add_argument("--bundle", type=Path, help="model-authority bundle to cross-check")
    parser.add_argument("--write-baseline", action="store_true",
                        help="rewrite the reviewed baseline from the current checkout")
    args = parser.parse_args(argv)
    report = coverage.build_report(ROOT)
    if args.json:
        args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.write_baseline:
        if report["duplicates"]:
            print("refusing to write a baseline with duplicate providers", file=sys.stderr)
            return 1
        (ROOT / coverage.BASELINE_PATH).write_text(
            coverage.render_baseline(coverage.baseline_from_report(report)), encoding="utf-8")
        print(f"wrote {coverage.BASELINE_PATH}")
        return 0
    errors = coverage.compare(report, coverage.load_baseline(ROOT))
    if args.bundle:
        errors += coverage.bundle_errors(report, json.loads(args.bundle.read_text(encoding="utf-8")), ROOT)
    summary = report["summary"]
    print(f"model-projection coverage ({report['mode']}): "
          f"{summary['projected_identities']} projected, {summary['residual_identities']} residual "
          f"identities, {summary['residual_declarations']} residual kernel declarations")
    for error in errors:
        print(f"- {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
