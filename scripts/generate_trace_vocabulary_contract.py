#!/usr/bin/env python3
"""Generate (or check) the trace-vocabulary contract.

Canonical artifact:

- ``de4sdv/semantic/contract-data/trace-vocabulary-contract.json``

The runtime serves the trace relations of the method kernel (``allocatedTo``,
``hasValidationScenario`` and its inverse ``validationScenarioFor``,
``hasRegulatorySource``) and refuses the retired relation names from this
file; it never parses the model. The file is written from the
trace-vocabulary package
(``textual-notation-of-model/packages/methods/de4sdv/de4sdv_trace_vocabulary.sysml``)
and the class pins of the generated projection layers, so run this after the
other generators (``docs/guides/generated-semantic-assets.md``).

Generation is deterministic and records no Git revision or input digest; the
check is the freshness gate, and ``scripts/check_repo.py`` runs it.

Usage:

    python scripts/generate_trace_vocabulary_contract.py              # write
    python scripts/generate_trace_vocabulary_contract.py --check      # verify
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.semantic.model_contract import TRACE_CONTRACT_PATH, canonical_json  # noqa: E402
from de4sdv.semantic.trace_vocabulary_contract import build_document, run_check_errors  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the committed file equals regeneration (no writes)",
    )
    args = parser.parse_args(argv)

    if args.check:
        errors = run_check_errors(ROOT)
        if errors:
            print("Trace-vocabulary contract check failed:")
            for error in errors:
                print(f"  - {error}")
            return 1
        print("Trace-vocabulary contract matches regeneration from the current sources.")
        return 0

    try:
        document = build_document(ROOT)
    except ValueError as exc:
        print(f"Trace-vocabulary contract generation refused: {exc}")
        return 1
    (ROOT / TRACE_CONTRACT_PATH).write_text(canonical_json(document), encoding="utf-8")
    contract = document["contract"]
    print(f"Wrote {TRACE_CONTRACT_PATH} ({len(contract['relations'])} relations, "
          f"{len(contract['retired'])} retired names) from the current sources.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
