#!/usr/bin/env python3
"""Local ask-model spike: element + question -> grounded answer via Nous.

Local-first prototype for the viewer "Ask the model" capability. No server
changes, no secrets in the repo: the key comes from the environment
(NOUS_API_KEY) and the model/provider are configurable.

Grounding contract (same as the production design):
  - resolve the element via the viewer's own index (same parser, same
    resolution preference: exact-name first, then typing, then parent)
  - read the element's declaration text and its doc comment straight from
    the .sysml file in the working tree (the validated model)
  - give the LLM ONLY that evidence + a strict system prompt; the answer
    must cite element names and may say "not in the model"

Usage:
    export NOUS_API_KEY=...
    python tools/sysml_html_viewer/ask_model_spike.py \\
        --element observer --question "What does this part do?"
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.sysml_html_viewer.model_parse import (  # noqa: E402
    build_member_index,
    load_model,
)

API_URL = "https://inference-api.nousresearch.com/v1/chat/completions"
MODEL = os.environ.get("NOUS_MODEL", "z-ai/glm-5.3-flash")
API_KEY_ENV = "NOUS_API_KEY"

SYSTEM_PROMPT = """You are the DE4SDV model assistant. You answer questions
about a SysML v2 model. You are given exactly one model element: its
declaration source text and its documentation comment from the authoritative
repository. Rules:
- Answer ONLY from the provided evidence. Never invent elements,
  requirements, flows, ports, or compliance claims.
- Cite the element by name when you use it.
- If the evidence does not answer the question, say exactly what the model
  does not contain. Do not speculate.
- You are not a compliance authority: never claim certification,
  homologation, or approval.
- Keep answers under 150 words unless the user asks for detail.
"""


def resolve_element(index, name: str):
    """Same preference order as the viewer: exact name, then typing, then parent."""
    refs = index.get(name)
    if refs:
        return refs[0], refs
    typed = [r for rs in index.values() for r in rs if r.type_name == name]
    if typed:
        return typed[0], typed
    parented = [
        r for rs in index.values() for r in rs
        if r.parent_name and name in (r.name, r.type_name)
    ]
    if parented:
        return parented[0], parented
    return None, []


def element_source(ref, files) -> str:
    """The element's declaration text: its line plus continuation lines
    until a line at the same indent closes the block, capped at 40 lines."""
    mf = next((f for f in files if f.rel_path == ref.rel_path), None)
    if mf is None:
        return ""
    lines = mf.path.read_text(errors="replace").splitlines()
    if ref.line <= 0 or ref.line > len(lines):
        return ""
    start = ref.line - 1
    first = lines[start]
    block = [first]
    brace_open = first.count("{") - first.count("}")
    stripped = first.strip()
    if brace_open <= 0 and (brace_open < 0 or stripped.endswith(";")):
        # single-line declaration: the element is exactly this line
        return "\n".join(block)
    i = start + 1
    # Well-formed SysML declarations end either with a balanced brace block
    # or a terminating ';'. Wrapped headers (no braces yet, no ';') keep
    # consuming lines. Cap guards against pathological files.
    while i < len(lines) and len(block) < 80:
        line = lines[i]
        block.append(line)
        brace_open += line.count("{") - line.count("}")
        stripped = line.strip()
        if brace_open <= 0 and (brace_open < 0 or stripped.endswith(";")
                                or stripped.endswith("}")):
            break
        i += 1
    return "\n".join(block)


def siblings_of(ref, files) -> list[str]:
    """Names of the element's owner's children (same file), for context."""
    mf = next((f for f in files if f.rel_path == ref.rel_path), None)
    if mf is None:
        return []

    def find(members, parent_name):
        for m in members:
            if m.name == ref.name and m.line == ref.line:
                return parent_name, [c.name for c in m.children]
            hit = find(m.children, m.name or parent_name)
            if hit:
                return hit
        return None

    hit = find(mf.members, "")
    if not hit:
        return []
    owner, kids = hit
    return kids


def ask_llm(evidence: dict, question: str, api_key: str) -> str:
    # Cloudflare on the inference endpoint blocks default urllib/requests
    # user agents (HTTP 403, "error code: 1010"): present the same UA shape
    # Hermes itself uses, plus the portal attribution tags.
    body = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": (
                f"Evidence (from the authoritative model repository):\n"
                f"```json\n{json.dumps(evidence, indent=2)}\n```\n\n"
                f"Question: {question}"
            )},
        ],
        "max_tokens": int(os.environ.get("NOUS_MAX_TOKENS", "2000")),
        "temperature": 0.2,
        "tags": ["product=hermes-agent", "client=hermes-client-v0.20.0"],
    }).encode()
    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "HermesAgent/0.20.0",
            "HTTP-Referer": "https://hermes-agent.nousresearch.com",
            "X-Title": "Hermes Agent",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode())
    msg = data["choices"][0]["message"]
    content = msg.get("content")
    if not content:
        # reasoning models can return null content when the token budget is
        # consumed by thinking; surface that honestly instead of failing
        finish = data["choices"][0].get("finish_reason")
        raise RuntimeError(
            f"model returned no content (finish_reason={finish!r}); "
            f"raise NOUS_MAX_TOKENS or pick a non-reasoning model"
        )
    return content


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--element", required=True, help="element name in the model")
    ap.add_argument("--question", required=True)
    ap.add_argument("--json", action="store_true", help="print evidence JSON only")
    args = ap.parse_args()

    files = load_model(REPO, ["textual-notation-of-model",
                              "model-based-product-line-engineering/product-models"])
    index = build_member_index(files)
    ref, candidates = resolve_element(index, args.element)
    if ref is None:
        print(f"error: element {args.element!r} not in the model index",
              file=sys.stderr)
        return 1
    if len(candidates) > 1:
        print(f"note: {len(candidates)} elements named {args.element!r}; "
              f"using {ref.rel_path}:{ref.line}", file=sys.stderr)

    kids = siblings_of(ref, files)
    evidence = {
        "element": {
            "name": ref.name, "kind": ref.kind,
            "file": ref.rel_path, "line": ref.line,
            "typed_as": ref.type_name or None,
            "owner": ref.parent_name or None,
        },
        "doc": ref.doc or None,
        "child_elements": kids or None,
        "declaration_source": element_source(ref, files) or None,
    }
    if args.json:
        print(json.dumps(evidence, indent=2))
        return 0

    api_key = os.environ.get(API_KEY_ENV)
    if not api_key:
        print(f"error: set {API_KEY_ENV} for the LLM call", file=sys.stderr)
        return 2

    answer = ask_llm(evidence, args.question, api_key)
    print(answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
