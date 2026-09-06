#!/usr/bin/env python3
"""Local ask-model spike: element + question -> grounded answer via Nous.

CLI front-end over tools.sysml_html_viewer.ask_model (the shared grounding
layer). See that module for the grounding contract and secret handling.

Usage:
    python tools/sysml_html_viewer/ask_model_spike.py \
        --element observer --question "What does this part do?" [--json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.sysml_html_viewer.ask_model import (  # noqa: E402
    DEFAULT_KEY_FILE,
    build_evidence,
    load_api_key,
    resolve_element,
)
from tools.sysml_html_viewer.model_parse import (  # noqa: E402
    build_member_index,
    load_model,
)

MODEL_ROOTS = ["textual-notation-of-model",
               "model-based-product-line-engineering/product-models"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--element", required=True, help="element name in the model")
    ap.add_argument("--question", required=True)
    ap.add_argument("--json", action="store_true", help="print evidence JSON only")
    args = ap.parse_args()

    files = load_model(REPO, MODEL_ROOTS)
    index = build_member_index(files)
    ref, candidates = resolve_element(index, args.element)
    if ref is None:
        print(f"error: element {args.element!r} not in the model index",
              file=sys.stderr)
        return 1
    if len(candidates) > 1:
        print(f"note: {len(candidates)} elements named {args.element!r}; "
              f"using {ref.rel_path}:{ref.line}", file=sys.stderr)

    evidence = build_evidence(ref, files)
    if args.json:
        print(json.dumps(evidence, indent=2))
        return 0

    api_key = load_api_key()
    if not api_key:
        print(f"error: set NOUS_API_KEY or create {DEFAULT_KEY_FILE}",
              file=sys.stderr)
        return 2

    answer = ask_llm(evidence, args.question, api_key)
    print(answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
