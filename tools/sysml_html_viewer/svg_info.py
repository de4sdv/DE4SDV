"""Diagram hover enrichment: extract SVG text labels and resolve them to
model elements.

SysIDE renders each diagram as a flat SVG: element names, stereotype
labels (``«part def»``), and usage labels (``signalTranslator :
SignalTranslator``) are plain ``<text>`` elements. This module turns those
labels back into model knowledge (kind, doc, source location, viewer
anchor) so the generated viewer can show a tooltip on hover.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .model_parse import ElementRef

_TEXT_RE = re.compile(r"<text\b[^>]*>(.*?)</text>", flags=re.S)
_TAG_RE = re.compile(r"<[^>]+>")

# Label shapes SysIDE emits: stereotype prefix «view» name, `expose name`,
# `name : Type`, plain name. Anything else is layout text (headers, notes).
_STEREOTYPE_RE = re.compile(r"^«[^»]*»\s*")
_EXPOSE_RE = re.compile(r"^expose\s+")
_EXHIBIT_RE = re.compile(r"^exhibit\s+")
# `states lifecycleStates` renders the exhibited usage; resolve by its name
_PLURAL_USAGE_RE = re.compile(
    r"^(?:states|parts|ports|actions|items|flows|interfaces|attributes)\s+"
)


def _unescape(s: str) -> str:
    """SysIDE SVG text may carry HTML entities (&gt; for the :> specializer)."""
    s = s.replace("&lt;", "<")
    s = s.replace("&gt;", ">")
    s = s.replace("&quot;", '"')
    s = s.replace("&#39;", "'")
    s = s.replace("&apos;", "'")
    s = s.replace("&amp;", "&")  # last, so &amp;gt; resolves to >
    return s


def extract_text_labels(svg_text: str) -> list[str]:
    """All text-element contents, normalized (whitespace collapsed, entities
    unescaped)."""
    labels = []
    for m in _TEXT_RE.finditer(svg_text):
        plain = _TAG_RE.sub("", m.group(1))
        plain = _unescape(plain)
        plain = re.sub(r"\s+", " ", plain).strip()
        if plain:
            labels.append(plain)
    return labels


def _normalize(label: str) -> list[str]:
    """Candidate lookup keys for a raw SVG label, most specific first."""
    candidates = []
    s = _STEREOTYPE_RE.sub("", label).strip()
    s = _EXPOSE_RE.sub("", s).strip()
    s = _EXHIBIT_RE.sub("", s).strip()
    s = s.lstrip("^")  # `^name` = redefines marker
    if not s:
        return []
    candidates.append(s)
    # plural usage labels (`states lifecycleStates`) resolve by their name
    s2 = _PLURAL_USAGE_RE.sub("", s)
    if s2 and s2 != s:
        candidates.append(s2)
    # strip a specializer/typing suffix: ` :> Super`, ` :>> Super`, ` : Type`
    for sep in (" :>> ", " :> ", " : "):
        if sep in s:
            candidates.append(s.split(sep, 1)[0].strip())
            break
    # qualified paths (`Root::member`) resolve by their root name
    for c in list(candidates):
        if "::" in c:
            candidates.append(c.split("::", 1)[0].strip())
    # dotted deployment paths (`host.role.port.item`) resolve by their
    # first and last segments (host part / item name)
    for c in list(candidates):
        if "." in c and "::" not in c:
            segs = [s for s in c.split(".") if s]
            if len(segs) > 1:
                candidates.append(segs[0])
                candidates.append(segs[-1])
    # quoted-name form ('exchange vehicle signals' vs exchange vehicle signals)
    for c in list(candidates):
        if c.startswith("'") and c.endswith("'"):
            candidates.append(c[1:-1])
    return [c for c in candidates if c]


def _prefer(refs: list[ElementRef], view_file: str, view_folder: str) -> ElementRef | None:
    """Pick the best match: same file, then same folder, then first."""
    if not refs:
        return None
    for ref in refs:
        if ref.rel_path == view_file:
            return ref
    for ref in refs:
        if ref.rel_path.startswith(view_folder):
            return ref
    return refs[0]


@dataclass
class LabelInfo:
    """Resolved hover info for one diagram label."""

    label: str
    name: str
    kind: str
    doc: str = ""
    rel_path: str = ""
    line: int = 0
    anchor: str = ""

    def to_dict(self) -> dict[str, object]:
        d: dict[str, object] = {"name": self.name, "kind": self.kind}
        if self.doc:
            d["doc"] = self.doc
        if self.rel_path:
            d["file"] = self.rel_path
            d["line"] = self.line
            d["anchor"] = self.anchor
        return d


def resolve_labels(
    labels: list[str],
    index: dict[str, list[ElementRef]],
    view_file: str,
    view_folder: str,
) -> list[LabelInfo]:
    """Resolve diagram labels against the model index, most specific first."""
    out: list[LabelInfo] = []
    for label in labels:
        for key in _normalize(label):
            refs = index.get(key)
            if not refs:
                continue
            ref = _prefer(refs, view_file, view_folder)
            if ref is None:
                continue
            out.append(
                LabelInfo(
                    label=label,
                    name=ref.name,
                    kind=ref.kind,
                    doc=ref.doc,
                    rel_path=ref.rel_path,
                    line=ref.line,
                    anchor=ref.anchor,
                )
            )
            break  # first resolvable key wins (exact > stripped > name part)
    return out


def labels_to_json(
    resolved: list[LabelInfo],
    page_dir: str,  # repo-relative dir of the generated page (for hrefs)
) -> str:
    """Stable JSON for embedding: label -> {info, href}."""
    payload: dict[str, dict] = {}
    for li in resolved:
        href = ""
        if li.anchor:
            href = f"pages/{li.rel_path}.html#{li.anchor}"
        entry = li.to_dict()
        if href:
            entry["href"] = href
        payload[li.label] = entry
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)
