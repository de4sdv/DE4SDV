"""Element-grounded model Q&A for the DE4SDV viewer ("Ask the model").

Shared grounding + inference layer for the ask-model capability:

- resolve an element through the viewer's own member index (same parser,
  same preference order as the hover tooltips)
- read evidence straight from the authoritative .sysml files: the
  element's declaration source, its doc comment, children, owner
- one strict grounding prompt: answer only from the evidence, cite
  element names, state what the model does not contain, never claim
  certification/homologation/approval

Secrets never live in this repository: the API key comes from the
NOUS_API_KEY environment variable or a 0600 key file under the Hermes
home directory (never committed, never printed).
"""
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

API_URL = "https://inference-api.nousresearch.com/v1/chat/completions"
MODEL = os.environ.get("NOUS_MODEL", "~deepseek/deepseek-v4-flash-latest")
API_KEY_ENV = "NOUS_API_KEY"
DEFAULT_KEY_FILE = Path.home() / ".hermes" / "secrets" / "de4sdv-nous-api-key"

# Cloudflare on the inference endpoint blocks default urllib/requests
# user agents (HTTP 403, "error code: 1010"): present the same UA shape
# Hermes itself uses, plus the portal attribution tags.
_USER_AGENT = "HermesAgent/0.20.0"
_PORTAL_TAGS = ["product=hermes-agent", "client=hermes-client-v0.20.0"]

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


def load_api_key() -> str:
    """NOUS_API_KEY env wins; else the 0600 key file; never printed."""
    key = os.environ.get(API_KEY_ENV, "").strip()
    if key:
        return key
    try:
        return DEFAULT_KEY_FILE.read_text().strip()
    except OSError:
        return ""


def resolve_element(index: dict, name: str):
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
    until the declaration is balanced or terminated, capped at 80 lines."""
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
    """Names of the element's own children (same file). Never the owner."""
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
    _owner, kids = hit
    return kids


def build_evidence(ref, files) -> dict:
    """The evidence bundle one ask is grounded on."""
    return {
        "element": {
            "name": ref.name, "kind": ref.kind,
            "file": ref.rel_path, "line": ref.line,
            "typed_as": ref.type_name or None,
            "owner": ref.parent_name or None,
        },
        "doc": ref.doc or None,
        "child_elements": siblings_of(ref, files) or None,
        "declaration_source": element_source(ref, files) or None,
    }


def ask_llm(evidence: dict, question: str, api_key: str,
            model: str = "") -> str:
    body = json.dumps({
        "model": model or MODEL,
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
        "tags": list(_PORTAL_TAGS),
    }).encode()
    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": _USER_AGENT,
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
