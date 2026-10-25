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
# `then` prefixes use-case include actions (`then include 'x' { ... }`).
# A declaration can have more than one prefix keyword (`variant ref part x`,
# `in ref item x`). Thus the prefix group repeats. `library package` and
# `standard library package` declare packages: their kind is `package`.
_PREFIX = (
    r"(?:(?:abstract|derived|in|out|inout|ref|variant|variation|then|"
    r"standard|library)\s+)*"
)
_KIND = (
    r"part def|port def|item def|requirement def|viewpoint def|concern def|"
    r"action def|state def|interface def|flow def|attribute def|metadata def|"
    r"enum def|verification def|calc def|allocation def|constraint def|"
    r"connection def|use case def|package|part|port|item|requirement|view|viewpoint|concern|"
    r"action|state|interface|flow|attribute|metadata|usage|exhibit|enum|"
    r"verification|calc|allocation|assert constraint|constraint|story|interaction|event|transfer|"
    r"stakeholder|subject|dependency|trace|satisfy|verify|refine|actor|"
    r"objective|alias|claim|argument|evidence|counterclaim|use case|include|connection|binding|bind"
)
_NAME = r"[A-Za-z_][A-Za-z0-9_]*|'[^']*'"
# A short name sits between the kind and the name: `requirement <'REQ-1'> r`.
# The name can follow it without a space (`<'VC-1'>Check`).
_SHORT = r"'(?:[^'\\]|\\.)*'|[A-Za-z_][A-Za-z0-9_]*"

# A keyword is never a name. `def` after a usage kind: a kind that the list
# does not have (`connection def X` before `connection def` was in it) or a
# definition with a short name (`verification def <'ID'>X`) matched the
# usage kind with the name `def`. `redefines`, `subsets` and `references`
# start the relationship of an unnamed usage (`attribute redefines x = 1;`
# is `attribute :>> x = 1;`).
DECL_RE = re.compile(
    rf"^\s*{_PREFIX}(?P<kind>{_KIND})"
    rf"(?:\s*<(?P<short>{_SHORT})>\s*|\s+)"
    rf"(?P<name>(?!(?:def|redefines|subsets|references)\b)(?:{_NAME}))(?=\s|:|;|\{{|$)"
)


def _short_name(group: str | None) -> str:
    """The short name without its quotes (`'REQ-1'` -> `REQ-1`), or ''."""
    if not group:
        return ""
    if group.startswith("'") and group.endswith("'"):
        return re.sub(r"\\(.)", r"\1", group[1:-1])
    return group

# flow statements without a name (`flow from A to B;`) must not be parsed
# as declarations named 'from'/'to'/'between'. `flow of T from A to B;` is
# an unnamed flow of T: like `objective` and `subject`, it is listed under
# its keyword, never under the name 'of'.
_FLOW_NO_NAME = frozenset({"from", "to", "between"})

# anonymous usages: `objective { doc ... }` or `subject;` — the keyword is
# the usage's only name; diagrams render it as a compartment heading, so
# the declaration must be indexable under that keyword.
_ANON_USAGE_RE = re.compile(
    rf"^\s*{_PREFIX}(?P<kind>objective|subject)\s*(?={{|;|$)"
)

# `bind a.b = c;` with a dotted source: DECL_RE cannot take the dotted
# name, so capture the full source path as the bind's name.
_BIND_DOTTED_RE = re.compile(
    r"^\s*bind\s+([A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*)\s*="
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
    depth: int          # code braces open before the declaration, plus 1
    line: int           # 1-based line of the declaration
    doc: str = ""       # attached doc /* ... */ text (raw, unescaped)
    type_name: str = "" # declared typing (`part x : T;` -> "T"), usages only
    children: list["Member"] = field(default_factory=list)
    short_name: str = ""  # `requirement <'REQ-1'> r` -> "REQ-1"
    type_names: tuple[str, ...] = ()  # all types of a typing list; type_name is the first
    library: bool = False  # a `library package` (also `standard library package`)
    # the nearest parsed declaration whose braces contain this one (None:
    # an index root); children lists the members that have it as parent
    parent: "Member | None" = field(default=None, repr=False, compare=False)


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
    # the names that the code of the file uses as a qualifier (`Q::`), also
    # in its imports (`import Q::*`): see file_index
    qualifiers: frozenset[str] = frozenset()


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

    A doc that sits inside a member's block (immediately after its opening
    brace) belongs to that member EXCLUSIVELY — rule (b) claims it first so
    rule (a) can never hand the same doc to the next declaration too (the
    off-by-one doc steal: `part def X { doc ... }` followed by `part a ...`
    must give the doc to X, not to a).
    """
    if not members:
        return
    decl_lines = sorted(m.line for m in members)
    # docs already claimed by rule (b): they sit inside a member's block and
    # must not also be offered to the member that follows them.
    claimed_by_block: set[int] = set()
    for i, m in enumerate(members):
        if m.doc:
            continue
        next_line = decl_lines[i + 1] if i + 1 < len(decl_lines) else m.line + 1
        brace = _block_open_brace(text, _line_start(text, m.line), _line_start(text, next_line))
        if brace == -1:
            continue
        for doc in DOC_RE.finditer(text):
            if doc.start() <= brace + 1:
                continue
            gap = text[brace + 1 : doc.start()]
            if not gap.strip():
                claimed_by_block.add(doc.start())
                break
    for doc in DOC_RE.finditer(text):
        doc_text = _clean_doc(doc.group(1))
        if not doc_text:
            continue
        doc_line = text.count("\n", 0, doc.start()) + 1
        doc_end = doc.end()
        # (a) doc immediately before a declaration — unless the previous
        # declaration's block already owns this doc (it sits right after
        # that member's `{`).
        if doc.start() not in claimed_by_block:
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


_LIBRARY_RE = re.compile(r"^\s*(?:standard\s+)?library\s+package\b")
_QUALIFIER_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*::")

# the text of a string or a quoted name in the code mask: not white space
# (it can start a statement), never a brace or a semicolon
_TEXT_MARK = "\0"


def _code_mask(text: str) -> tuple[str, set[int]]:
    """The text with notes, comments, strings and quoted names masked.

    A note (`//` to the end of the line, `//* ... */`) and a comment body
    (`/* ... */`) become spaces. A string (`"..."`) and a quoted name
    (`'...'`) become _TEXT_MARK. Newlines stay, so every position keeps its
    line. Also returns the positions just after each comment body: a doc,
    a comment and a textual representation end with their body.
    """
    out = list(text)
    ends: set[int] = set()
    n = len(text)
    i = 0
    while i < n:
        c = text[i]
        if c == "/" and text.startswith(("//", "/*"), i):
            if text.startswith("//*", i):
                j = text.find("*/", i + 3)
                j = n if j == -1 else j + 2
            elif text.startswith("//", i):
                j = text.find("\n", i)
                j = n if j == -1 else j
            else:
                j = text.find("*/", i + 2)
                j = n if j == -1 else j + 2
                ends.add(j)
            for p in range(i, j):
                if out[p] != "\n":
                    out[p] = " "
            i = j
            continue
        if c in "\"'":
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if text[j] == "\\" else 1
            j = min(n, j + 1)
            for p in range(i, j):
                if out[p] != "\n":
                    out[p] = _TEXT_MARK
            i = j
            continue
        i += 1
    return "".join(out), ends


# a type: a name or a qualified name (`Q::T`, also `Q :: T`)
_TYPE = r"[A-Za-z_][A-Za-z0-9_]*(?:\s*::\s*[A-Za-z_][A-Za-z0-9_]*)*"
_TYPE_LIST_RE = re.compile(rf"\s*({_TYPE}(?:\s*,\s*{_TYPE})*)")
# What can come after a typing: the end of the declaration or of its line;
# a value, a multiplicity or a default; a reference, a subsetting or a
# redefinition, as a keyword or as a symbol (`:>` also starts `:>>`); the
# ends of a connection, an allocation, a binding, a flow or a succession;
# the annotated element of a metadata usage.
_AFTER_TYPING_RE = re.compile(
    r"$|[;{\[=]|:=|::>|:>|(?:references|subsets|redefines|default|ordered|"
    r"nonunique|about|connect|allocate|bind|from|first)\b"
)


def _declared_types(raw: str) -> tuple[str, ...]:
    """Types named in a usage declaration (`part x : T;` -> ("T",)).

    Captured so hover enrichment can fall back to the type definition's doc
    when the usage itself is undocumented, even from BARE diagram labels
    (matrix row/column labels print only the usage name). Returns () for
    definitions, untyped usages, and usages that only specialize
    (`part x :> y;`), because a specialization is not a typing.

    Only the header of the declaration counts: the line before its first
    `{`. In `port def P { in item x : T; }`, T is the type of x, not of P.
    A qualified type keeps its qualifier (`Q::T`). A typing list
    (`: A, B`) gives all its types, in their order. A ` : ` after `=` or
    `default` is in a value (`x = c ? a : b`), not a typing; a ` : ` in a
    string or a quoted name is no typing either.
    """
    code = _code_mask(raw)[0]
    header_end = code.find("{")
    colon = code.find(" : ", 0, header_end if header_end != -1 else len(code))
    if colon == -1 or re.search(r"=|\bdefault\b", code[:colon]):
        return ()
    tail = raw[colon + 3:]
    m = _TYPE_LIST_RE.match(tail)
    if not m or not _AFTER_TYPING_RE.match(tail[m.end():].lstrip()):
        return ()
    return tuple(re.sub(r"\s+", "", t) for t in m.group(1).split(","))


def _declaration(raw: str, lineno: int, depth: int) -> Member | None:
    """The member that a source line declares, or None."""
    m = DECL_RE.match(raw)
    if m:
        kind = m.group("kind").strip()
        name = m.group("name")
        short = _short_name(m.group("short"))
        types = _declared_types(raw)
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
            return None
        if kind == "flow" and name == "of":
            name = "flow"  # `flow of T from A to B;` — an unnamed flow
        if kind == "package":
            return Member(kind=kind, name=name, depth=depth, line=lineno,
                          short_name=short, library=bool(_LIBRARY_RE.match(raw)))
        return Member(kind=kind, name=name, depth=depth, line=lineno,
                      type_name=types[0] if types else "", type_names=types,
                      short_name=short)
    bm = _BIND_DOTTED_RE.match(raw)
    if bm:
        # `bind a.b = c;` — dotted source; the full path is the name
        return Member(kind="bind", name=bm.group(1), depth=depth, line=lineno)
    anon = _ANON_USAGE_RE.match(raw)
    if anon:
        # `objective { doc ... }` / `subject;` — anonymous usage;
        # index it under its keyword so diagram compartment labels
        # resolve to the declaration (with its doc)
        akind = anon.group("kind").strip()
        return Member(kind=akind, name=akind, depth=depth, line=lineno)
    return None


def _scan_members(text: str, code: str, comment_ends: set[int]) -> list[Member]:
    """The declared members of a file, each with its parent and children.

    A line declares a member when its first character is code and starts a
    statement. A statement starts at the first character after `;`, `{`,
    `}` or a comment body; thus a line that continues a statement declares
    nothing. A `{` belongs to the statement that it ends. The parent of a
    member is the nearest member that owns one of the braces open at its
    line. A brace whose statement is no member (`perform ... {`,
    `attribute :>> x = ... {`) is no parent: the members inside it get the
    nearest member around it, never a member that comes before it. The
    depth of a member is the number of code braces open before its line,
    plus 1: a declaration outside all braces has depth 1. This is a
    navigation heuristic, not SysML v2 name resolution. code and
    comment_ends are the result of _code_mask(text).
    """
    members: list[Member] = []
    owners: list[Member | None] = []   # the owner of each open code brace
    stmt_start: int | None = None      # where the current statement starts
    declared: dict[int, Member] = {}   # statement start -> its member
    pos = 0
    for lineno, raw in enumerate(text.split("\n"), start=1):
        first = pos + len(raw) - len(raw.lstrip())
        for i in range(pos, pos + len(raw)):
            if i in comment_ends:
                stmt_start = None
            if i == first and stmt_start is None and code[i] == text[i]:
                member = _declaration(raw, lineno, len(owners) + 1)
                if member is not None:
                    member.parent = next(
                        (o for o in reversed(owners) if o is not None), None)
                    if member.parent is not None:
                        member.parent.children.append(member)
                    members.append(member)
                    declared[i] = member
            c = code[i]
            if c == "{":
                owners.append(declared.get(stmt_start) if stmt_start is not None else None)
                stmt_start = None
            elif c == "}":
                if owners:
                    owners.pop()
                stmt_start = None
            elif c == ";":
                stmt_start = None
            elif stmt_start is None and not c.isspace():
                stmt_start = i
        pos += len(raw)
        if pos in comment_ends:   # a comment body that ends the line
            stmt_start = None
        pos += 1
    return members


def parse_file(path: Path, repo_root: Path) -> ModelFile:
    """Parse one .sysml file into a ModelFile."""
    text = path.read_text(encoding="utf-8")
    mf = ModelFile(path=path, rel_path=path.relative_to(repo_root).as_posix())
    code, comment_ends = _code_mask(text)
    mf.members = _scan_members(text, code, comment_ends)
    mf.qualifiers = frozenset(_QUALIFIER_RE.findall(code))

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


#: Never loaded: the synthetic fixtures of the model roots (the invalid
#: configuration and the parity probes under feature-configurations/fixtures/),
#: which the export and the served model leave out too.
EXCLUDED_PART = "fixtures"


def model_paths(repo_root: Path, roots: list[str]) -> list[Path]:
    """The .sysml files under the given repo-relative roots, without their fixtures."""
    paths: list[Path] = []
    for root in roots:
        base = repo_root / root
        if not base.is_dir():
            continue
        paths.extend(path for path in sorted(base.rglob("*.sysml"))
                     if EXCLUDED_PART not in path.relative_to(base).parts)
    return paths


def load_model(repo_root: Path, roots: list[str]) -> list[ModelFile]:
    """Load the .sysml files under the given repo-relative roots, without their fixtures."""
    return [parse_file(path, repo_root) for path in model_paths(repo_root, roots)]


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
    element_file: str = ""    # element nodes only: declaring .sysml rel_path
    element_line: int = 0     # element nodes only: declaration line (1-based)
    short_name: str = ""      # element nodes only: the short name, shown before the label

    @property
    def text(self) -> str:
        """The text of the node in the tree: `<short> label` (the notation of
        the SysIDE diagrams), or the label. The label alone is the element
        identity (data-tip-name)."""
        return f"<{self.short_name}> {self.label}" if self.short_name else self.label


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
                    element_file=mf.rel_path,
                    element_line=v.line,
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
                    element_file=mf.rel_path,
                    element_line=mm.line,
                    short_name=mm.short_name,
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
    type_name: str = ""     # declared typing (`part x : T;` -> "T"), usages only
    short_name: str = ""    # `requirement <'REQ-1'> r` -> "REQ-1"
    type_names: tuple[str, ...] = ()  # all types of a typing list; type_name is the first
    library: str = ""       # the library package that contains the declaration, if any


def _walk_with_parent(
    members: list[Member], parent: Member | None
) -> Iterable[tuple[Member, Member | None]]:
    """Yield every member with its enclosing declaration (or None)."""
    for m in members:
        yield m, parent
        yield from _walk_with_parent(m.children, m)


def _library_of(m: Member) -> str:
    """The name of the library package that contains m (or is m), or ''."""
    node: Member | None = m
    while node is not None:
        if node.library:
            return node.name
        node = node.parent
    return ""


def build_member_index(files: list[ModelFile]) -> dict[str, list[ElementRef]]:
    """Index every declared member and view by name.

    Names are stored under both the raw and quote-stripped forms so SVG
    labels can match quoted names ('exchange vehicle signals').
    """
    index: dict[str, list[ElementRef]] = {}
    for mf in files:
        # mf.members is flat (children are also listed); walk only the
        # roots (members without a parent) and descend via the tree so
        # nothing is doubled. A member in the braces of a declaration that
        # the scanner does not parse (a top-level `library package` before)
        # is a root too, so it is not lost.
        for m, parent in _walk_with_parent(
            [m for m in mf.members if m.parent is None], None
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
                    short_name=m.short_name,
                    library=_library_of(m),
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
                type_name=m.type_name,
                short_name=m.short_name,
                type_names=m.type_names,
                library=_library_of(m),
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


def file_index(
    index: dict[str, list[ElementRef]], mf: ModelFile
) -> dict[str, list[ElementRef]]:
    """The index as one file sees it, for its source references and its
    diagram labels.

    A declaration in a library package L counts only in its own file and in
    a file that names L as a qualifier (`import L::*`, `L::x`). Elsewhere a
    common name (`kind`, `path`) would go to the library. The full index
    keeps every declaration, for Ask and the tree. This is a navigation
    heuristic, not SysML v2 name resolution.
    """
    def visible(ref: ElementRef) -> bool:
        return (not ref.library or ref.rel_path == mf.rel_path
                or ref.library in mf.qualifiers)

    view: dict[str, list[ElementRef]] = {}
    for key, refs in index.items():
        kept = [r for r in refs if visible(r)]
        if kept:
            view[key] = kept
    return view


def _index_add(index: dict[str, list[ElementRef]], ref: ElementRef) -> None:
    index.setdefault(ref.name, []).append(ref)
    if ref.name.startswith("'") and ref.name.endswith("'"):
        index.setdefault(ref.name[1:-1], []).append(ref)
    # a short name is a name of the element too (SysML v2 resolves it like
    # the name), so `REQ-1` finds `requirement <'REQ-1'> r`
    if ref.short_name and ref.short_name != ref.name:
        index.setdefault(ref.short_name, []).append(ref)
