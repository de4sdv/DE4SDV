"""Model parsing for the DE4SDV static HTML model viewer.

Parses the authoritative ``.sysml`` textual notation under
``textual-notation-of-model/packages`` into a navigation model: packages,
declared members (with their ``doc`` comments), and declared ``view`` usages
with their SysIDE render artifacts.

This module is self-contained (stdlib only). The view-block parsing mirrors
``scripts/generate_view_index.py`` so both tools agree on the view inventory;
a parity test locks that agreement (see ``tests/test_sysml_html_viewer.py``).

Only ``.sysml`` files are the semantic authority. No roles, ports, flows, or
endpoints are invented here — the viewer links rendered diagrams, it does not
re-derive them.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

# ---------------------------------------------------------------------------
# Declaration scanning
# ---------------------------------------------------------------------------

# SysML v2 member declaration kinds found in the DE4SDV model (verified by
# scanning textual-notation-of-model/packages). "abstract"/"derived" and the
# direction/prefix keywords are handled as separate prefixes so
# `abstract part def`, `in item x`, `ref part x`, `variant part x` all parse;
# `then` prefixes use-case include actions (`then include 'x' { ... }`)
_PREFIX = r"(?:(?:abstract|derived|in|out|inout|ref|variant|variation|then)\s+)?"
_KIND = (
    r"part def|port def|item def|requirement def|viewpoint def|concern def|"
    r"action def|state def|interface def|flow def|attribute def|metadata def|"
    r"enum def|verification def|calc def|allocation def|constraint def|"
    r"use case def|package|part|port|item|requirement|view|viewpoint|concern|"
    r"action|state|interface|flow|attribute|metadata|usage|exhibit|enum|"
    r"verification|calc|allocation|constraint|story|interaction|event|transfer|"
    r"stakeholder|subject|dependency|trace|satisfy|verify|refine|actor|"
    r"objective|alias|claim|argument|evidence|counterclaim|use case|include|connection"
)
_NAME = r"[A-Za-z_][A-Za-z0-9_]*|'[^']*'"

DECL_RE = re.compile(
    rf"^\s*{_PREFIX}(?P<kind>{_KIND})\s+"
    rf"(?P<name>{_NAME})(?=\s|:|;|\{{|$)"
)

# flow statements without a name (`flow from A to B;`) must not be parsed
# as declarations named 'from'/'to'/'between'.
_FLOW_NO_NAME = frozenset({"from", "to", "between"})

# anonymous usages: `objective { doc ... }` or `subject;` — the keyword is
# the usage's only name; diagrams render it as a compartment heading, so
# the declaration must be indexable under that keyword.
_ANON_USAGE_RE = re.compile(
    rf"^\s*{_PREFIX}(?P<kind>objective|subject)\s*(?={{|;|$)"
)

# `exhibit state lifecycleStates { ... }` declares an inline usage inside
# an exhibit block; the exhibited element carries the real name.
_EXHIBIT_USAGE_RE = re.compile(
    r"^exhibit\s+([A-Za-z_][A-Za-z0-9_]*)\s+"
    r"([A-Za-z_][A-Za-z0-9_]*|'[^']*')"
)
_USAGE_KINDS = frozenset({
    "state", "action", "part", "port", "item", "flow", "interface",
    "attribute", "metadata", "event", "interaction", "transfer", "story",
})

DOC_RE = re.compile(r"doc\s*/\*(.*?)\*/\s*", flags=re.S)


@dataclass
class Member:
    """One declared member of a package (or the package itself)."""

    kind: str
    name: str
    depth: int          # brace depth at which the member lives
    line: int           # 1-based line of the declaration
    doc: str = ""       # attached doc /* ... */ text (raw, unescaped)
    children: list["Member"] = field(default_factory=list)


@dataclass
class ViewInfo:
    """A declared `view` usage plus its SysIDE artifact mapping."""

    name: str
    view_type: str = ""
    viewpoint: str = ""
    viewpoint_type: str = ""
    concern: str = ""
    exposes: list[str] = field(default_factory=list)
    depth: str = ""
    render: str = ""
    line: int = 0
    doc: str = ""


@dataclass
class ModelFile:
    """Everything the viewer needs from one .sysml file."""

    path: Path                  # absolute path
    rel_path: str               # repo-relative posix path
    members: list[Member] = field(default_factory=list)
    views: list[ViewInfo] = field(default_factory=list)
    file_doc: str = ""


def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    return text


def _find_block(text: str, decl: str, name: str) -> str | None:
    match = re.search(rf"\b{decl}\s+{name}\b[^{{]*{{", text)
    if not match:
        return None
    start = match.end() - 1
    depth = 1
    for i in range(start + 1, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[match.start() : i + 1]
    return None


_QUALIFIED_NAME = r"[A-Za-z_][A-Za-z0-9_]*(?:::[A-Za-z_][A-Za-z0-9_]*)*"
_VIEW_RE = re.compile(
    rf"\bview\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?::\s*({_QUALIFIED_NAME}))?\s*\{{"
)
_VIEWPOINT_RE = re.compile(
    r"viewpoint\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*([A-Za-z_][A-Za-z0-9_]*)\s*\{"
)
_FRAME_RE = re.compile(r"frame\s+([A-Za-z_][A-Za-z0-9_.]*)")
_EXPOSE_RE = re.compile(r"\bexpose\s+([^;\n]+?)\s*;")
_DEPTH_RE = re.compile(r"attribute\s+depth\s*=\s*(-?\d+)")
_RENDER_RE = re.compile(r"render\s+([A-Za-z_][A-Za-z0-9_]*)")


def artifact_filename(view_name: str, view_type: str) -> str:
    """SysIDE artifact name for a view (same mapping as generate_view_index)."""
    short = view_type.rsplit("::", 1)[-1]
    if short == "MatrixView":
        return f"diagram-matrix-{view_name}.svg"
    if short == "TableView":
        return f"diagram-table-{view_name}.svg"
    return f"diagram-{view_name}.svg"


def _parse_view(text: str, name: str) -> ViewInfo | None:
    """Parse one view block (mirrors generate_view_index.parse_view_spec)."""
    block = _find_block(_strip_comments(text), "view", name)
    if not block:
        return None
    header = re.search(
        rf"\bview\s+{re.escape(name)}\s*(?::\s*({_QUALIFIED_NAME}))?\s*\{{",
        block,
    )
    info = ViewInfo(
        name=name,
        view_type=header.group(1) if header and header.group(1) else "",
    )
    vp = _VIEWPOINT_RE.search(block)
    if vp:
        info.viewpoint, info.viewpoint_type = vp.group(1), vp.group(2)
    frame = _FRAME_RE.search(block)
    if frame:
        info.concern = frame.group(1)
    info.exposes = [e for e in _EXPOSE_RE.findall(block) if e != name]
    d = _DEPTH_RE.search(block)
    if d:
        info.depth = d.group(1)
    r = _RENDER_RE.search(block)
    if r:
        info.render = r.group(1)
    return info


def _line_start(text: str, line: int) -> int:
    pos = 0
    for _ in range(line - 1):
        pos = text.find("\n", pos)
        if pos == -1:
            return len(text)
        pos += 1
    return pos


def _block_open_brace(text: str, decl_start: int, next_decl_start: int) -> int:
    """Position of the opening brace of the declaration at decl_start."""
    window = text[decl_start:next_decl_start]
    brace = window.find("{")
    semi = window.find(";")
    if brace == -1:
        return -1
    if semi != -1 and semi < brace:
        return -1  # declaration ends with ';' — no block
    return decl_start + brace


def _clean_doc(doc_text: str) -> str:
    """Normalize block-comment doc text: strip the leading ` * ` comment
    markers and collapse stray blank lines."""
    lines = []
    for raw in doc_text.splitlines():
        line = re.sub(r"^\s*\*\s?", "", raw).rstrip()
        lines.append(line)
    cleaned = "\n".join(lines).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned


def _attach_docs(text: str, members: list[Member]) -> None:
    """Attach `doc /* ... */` blocks to the declaration they document.

    A doc block attaches when it sits immediately before the declaration
    (only whitespace between) or immediately after the declaration's opening
    brace. A doc nested deeper (e.g. inside a ``require constraint``) is not
    the declaration's doc and attaches to nothing.
    """
    if not members:
        return
    decl_lines = sorted(m.line for m in members)
    for doc in DOC_RE.finditer(text):
        doc_text = _clean_doc(doc.group(1))
        if not doc_text:
            continue
        doc_line = text.count("\n", 0, doc.start()) + 1
        doc_end = doc.end()
        # (a) doc immediately before a declaration
        for m in members:
            if m.line > doc_line and not m.doc:
                gap = text[doc_end : _line_start(text, m.line)]
                if not gap.strip():
                    m.doc = doc_text
                    break
        if all(m.doc for m in members):
            break
        # (b) doc immediately after a declaration's opening brace
        for i, m in enumerate(members):
            if m.doc:
                continue
            next_line = decl_lines[i + 1] if i + 1 < len(decl_lines) else m.line + 1
            brace = _block_open_brace(text, _line_start(text, m.line), _line_start(text, next_line))
            if brace == -1:
                continue
            # the doc must sit INSIDE this member's block: right after its
            # opening brace. A doc before the brace (or in a sibling block)
            # is never this member's doc — an empty slice must not count.
            if doc.start() <= brace + 1:
                continue
            gap = text[brace + 1 : doc.start()]
            if not gap.strip():
                m.doc = doc_text
                break


def parse_file(path: Path, repo_root: Path) -> ModelFile:
    """Parse one .sysml file into a ModelFile."""
    text = path.read_text(encoding="utf-8")
    mf = ModelFile(path=path, rel_path=path.relative_to(repo_root).as_posix())

    depth = 0
    for lineno, raw in enumerate(text.splitlines(), start=1):
        m = DECL_RE.match(raw)
        opens = raw.count("{")
        closes = raw.count("}")
        if m:
            kind = m.group("kind").strip()
            name = m.group("name")
            if kind == "exhibit":
                # `exhibit state lifecycleStates {` — index the exhibited
                # usage (state, action, ...) under its real name so diagram
                # labels like "lifecycleStates" resolve; a plain
                # `exhibit partName;` stays an exhibit of that part.
                sub = _EXHIBIT_USAGE_RE.match(raw.strip())
                if sub and sub.group(1) in _USAGE_KINDS:
                    kind = sub.group(1)
                    name = sub.group(2)
            if kind == "flow" and name in _FLOW_NO_NAME:
                # `flow from A to B;` — no declaration
                pass
            elif kind == "package":
                decl_depth = depth + 1
                depth += 1
                mf.members.append(Member(kind=kind, name=name, depth=decl_depth, line=lineno))
            else:
                mf.members.append(Member(kind=kind, name=name, depth=depth, line=lineno))
        else:
            anon = _ANON_USAGE_RE.match(raw)
            if anon:
                # `objective { doc ... }` / `subject;` — anonymous usage;
                # index it under its keyword so diagram compartment labels
                # resolve to the declaration (with its doc)
                akind = anon.group("kind").strip()
                mf.members.append(Member(kind=akind, name=akind, depth=depth, line=lineno))
        depth += opens - closes
        if depth < 0:
            depth = 0

    # member tree: parent = nearest preceding member with depth-1
    stack: list[tuple[int, Member]] = []
    for m in mf.members:
        while stack and stack[-1][0] >= m.depth:
            stack.pop()
        if stack:
            stack[-1][1].children.append(m)
        stack.append((m.depth, m))

    # --- views ---
    for match in _VIEW_RE.finditer(text):
        name = match.group(1)
        info = _parse_view(text, name)
        if info is None:
            continue
        info.line = text.count("\n", 0, match.start()) + 1
        mf.views.append(info)

    # --- docs ---
    _attach_docs(text, mf.members)
    if mf.members and mf.members[0].kind == "package":
        mf.file_doc = mf.members[0].doc
    view_names = {v.name for v in mf.views}
    for mm in mf.members:
        if mm.kind == "view" and mm.name in view_names and mm.doc:
            for v in mf.views:
                if v.name == mm.name:
                    v.doc = mm.doc
                    break
    return mf


def load_model(repo_root: Path, roots: list[str]) -> list[ModelFile]:
    """Load all .sysml files under the given repo-relative roots."""
    files: list[ModelFile] = []
    for root in roots:
        base = repo_root / root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.sysml")):
            files.append(parse_file(path, repo_root))
    return files


# ---------------------------------------------------------------------------
# Tree construction
# ---------------------------------------------------------------------------


@dataclass
class TreeNode:
    label: str
    kind: str = "node"
    href: str = ""
    children: list["TreeNode"] = field(default_factory=list)
    meta: str = ""
    site_href: str = ""  # site-root-relative href (set during generation)
    depth: int = 0       # tree depth (set during generation)
    viewpoint_type: str = ""  # views only: referenced viewpoint type
    saf_domain: str = ""      # views only: SAF domain from viewpoint def doc
    saf_aspect: str = ""      # views only: SAF aspect from viewpoint def doc


_SAF_DOMAIN_RE = re.compile(r"SAF\s+([A-Za-z &]+?)\s+Domain")
_SAF_ASPECT_RE = re.compile(r"Aspect:\s*([A-Za-z &]+)")


def saf_viewpoint_catalog(files: list[ModelFile]) -> dict[str, tuple[str, str]]:
    """Viewpoint type -> (SAF domain, SAF aspect), parsed from the doc
    comments of `viewpoint def` declarations in the model itself (the
    source-backed taxonomy: "SAF <Domain> Domain" / "Aspect: <Aspect>").
    Types without a SAF doc comment are absent from the catalog."""
    catalog: dict[str, tuple[str, str]] = {}
    vp_re = re.compile(r"viewpoint\s+def\s+([A-Za-z_][A-Za-z0-9_]*)")
    for mf in files:
        try:
            text = mf.path.read_text(encoding="utf-8")
        except OSError:
            continue
        for m in vp_re.finditer(text):
            name = m.group(1)
            if name in catalog:
                continue
            window = text[m.end() : m.end() + 600]
            dom = _SAF_DOMAIN_RE.search(window)
            asp = _SAF_ASPECT_RE.search(window)
            catalog[name] = (
                dom.group(1).strip() if dom else "",
                asp.group(1).strip() if asp else "",
            )
    return catalog


def build_tree(files: list[ModelFile]) -> TreeNode:
    """Build the navigation tree: root -> area dirs -> package dirs -> files."""
    root = TreeNode(label="Model", kind="root")
    catalog = saf_viewpoint_catalog(files)
    for mf in files:
        parts = Path(mf.rel_path).parts
        node = root
        for i, part in enumerate(parts[:-1]):
            child = next((c for c in node.children if c.label == part), None)
            if child is None:
                child = TreeNode(
                    label=part,
                    kind="dir",
                    href=f"pages/{'/'.join(parts[: i + 1])}/index.html",
                )
                node.children.append(child)
            node = child
        file_node = TreeNode(
            label=parts[-1],
            kind="file",
            href=f"pages/{mf.rel_path}.html",
        )
        for v in mf.views:
            meta = "view"
            if v.render:
                meta += f" · {v.render}"
            elif v.view_type:
                meta += f" · {v.view_type}"
            domain, aspect = catalog.get(v.viewpoint_type, ("", ""))
            file_node.children.append(
                TreeNode(
                    label=v.name,
                    kind="view",
                    href=f"pages/{mf.rel_path}.html#view-{slugify(v.name)}",
                    meta=meta,
                    viewpoint_type=v.viewpoint_type,
                    saf_domain=domain,
                    saf_aspect=aspect,
                )
            )
        # every declared member links to its declaration line in the source;
        # the kind is shown in written form next to the name. View
        # declarations and everything nested inside them (viewpoints,
        # concerns) are framing — the views loop above already lists them.
        skip: set[int] = set()
        stack = [m for m in mf.members if m.kind == "view"]
        while stack:
            m = stack.pop()
            skip.add(id(m))
            stack.extend(m.children)
        for mm in mf.members:
            if id(mm) in skip:
                continue
            if mm.kind == "package":
                # packages are structural containers, not leaf members
                continue
            file_node.children.append(
                TreeNode(
                    label=mm.name,
                    kind=mm.kind,
                    href=f"pages/{mf.rel_path}.html#src-{mm.line}",
                    meta=mm.kind,
                )
            )
        node.children.append(file_node)
    return root


def count_stats(files: list[ModelFile]) -> dict[str, int]:
    stats = {"files": len(files), "views": 0, "members": 0, "packages": 0}
    for mf in files:
        stats["views"] += len(mf.views)
        stats["members"] += sum(1 for m in mf.members if m.kind != "package")
        stats["packages"] += sum(1 for m in mf.members if m.kind == "package")
    return stats


# ---------------------------------------------------------------------------
# Model-wide lookup index (for diagram hover enrichment)
# ---------------------------------------------------------------------------


def slugify(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-")
    return slug or "item"


@dataclass
class ElementRef:
    """One model element as seen by the hover lookup."""

    name: str
    kind: str
    doc: str = ""
    rel_path: str = ""
    line: int = 0
    anchor: str = ""        # page anchor, e.g. "member-MiddlewareSystem"
    parent_name: str = ""   # enclosing declaration (for anonymous usages)
    parent_line: int = 0
    has_children: bool = False


def _walk_with_parent(
    members: list[Member], parent: Member | None
) -> Iterable[tuple[Member, Member | None]]:
    """Yield every member with its enclosing declaration (or None)."""
    for m in members:
        yield m, parent
        yield from _walk_with_parent(m.children, m)


def build_member_index(files: list[ModelFile]) -> dict[str, list[ElementRef]]:
    """Index every declared member and view by name.

    Names are stored under both the raw and quote-stripped forms so SVG
    labels can match quoted names ('exchange vehicle signals').
    """
    index: dict[str, list[ElementRef]] = {}
    for mf in files:
        # mf.members is flat (children are also listed); walk only the
        # top-level entries and descend via the tree so nothing is doubled
        for m, parent in _walk_with_parent(
            [m for m in mf.members if m.depth == 1], None
        ):
            if m.kind == "package":
                # packages resolve `expose PackageName::*` diagram labels
                ref = ElementRef(
                    name=m.name,
                    kind="package",
                    doc=m.doc,
                    rel_path=mf.rel_path,
                    line=m.line,
                    anchor=f"src-{m.line}",
                    parent_name=parent.name if parent else "",
                    parent_line=parent.line if parent else 0,
                    has_children=bool(m.children),
                )
                _index_add(index, ref)
                continue
            ref = ElementRef(
                name=m.name,
                kind=m.kind,
                doc=m.doc,
                rel_path=mf.rel_path,
                line=m.line,
                anchor=f"src-{m.line}",  # jump to the declaration in source
                parent_name=parent.name if parent else "",
                parent_line=parent.line if parent else 0,
                has_children=bool(m.children),
            )
            _index_add(index, ref)
        for v in mf.views:
            ref = ElementRef(
                name=v.name,
                kind="view",
                doc=v.doc,
                rel_path=mf.rel_path,
                line=v.line,
                anchor=f"view-{slugify(v.name)}",
            )
            _index_add(index, ref)
    return index


def _index_add(index: dict[str, list[ElementRef]], ref: ElementRef) -> None:
    index.setdefault(ref.name, []).append(ref)
    if ref.name.startswith("'") and ref.name.endswith("'"):
        index.setdefault(ref.name[1:-1], []).append(ref)
