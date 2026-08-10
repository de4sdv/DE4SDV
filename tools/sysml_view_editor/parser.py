"""SysML v2 textual-notation parsing helpers for the DE4SDV view editor.

These patterns are proven in the repo's existing traceability tooling
(scripts/query_model_impact.py, scripts/check_model_sync.py) and the
sysml-v2-textual-notation-parsing skill. Regex parsing extracts structural
relationships for rendering and traceability; it is not a SysML v2
semantic validator (use licensed SysIDE for that).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


def strip_comments(text: str) -> str:
    """Remove /* ... */ and // ... comments, preserving newlines for position tracking."""
    text = re.sub(
        r"/\*.*?\*/",
        lambda m: re.sub(r"[^\n]", " ", m.group(0)),
        text,
        flags=re.DOTALL,
    )
    text = re.sub(r"//[^\n]*", "", text)
    return text


def braced_block(text: str, header: str) -> tuple[int, int] | None:
    """Return (start, end) char offsets of the body following `header`.

    `header` is like "part def VehicleSpeedCampaignCommunicationDeployment".
    Returns None if not found or no matching braces. The returned range is
    the body *between* the opening and closing braces (exclusive).
    """
    idx = text.find(header)
    if idx == -1:
        return None
    opening = text.find("{", idx + len(header))
    if opening == -1:
        return None
    depth = 0
    for pos in range(opening, len(text)):
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
            if depth == 0:
                return (opening + 1, pos)
    return None


def named_block(text: str, declaration: str, name: str) -> str:
    """Return the full declaration block (header through matching brace).

    Raises AssertionError if the declaration is missing or unterminated.
    """
    match = re.search(
        rf"\b{re.escape(declaration)}\s+{re.escape(name)}"
        rf"(?:\s*:\s*[^{{]+)?\s*\{{",
        text,
    )
    assert match, f"Missing {declaration} {name}"
    brace = text.find("{", match.start())
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[match.start() : index + 1]
    raise AssertionError(f"Unterminated {declaration} {name}")


def normalized(text: str) -> str:
    """Collapse all whitespace runs to single spaces."""
    return " ".join(text.split())


@dataclass
class Flow:
    """A directed typed flow between two port feature endpoints.

    `source_role`, `source_port`, `target_role`, `target_port` are filled by
    the graph builder after endpoint-path resolution; they are empty until then.
    """

    source: str  # e.g. vmA.cuttlefishGuest.structuredLogcatOut.envelope
    target: str  # e.g. vmA.hostForwarder.structuredLogcatIn.envelope
    index: int  # declaration order within the deployment
    source_role: str = ""  # e.g. vmA.cuttlefishGuest
    source_port: str = ""  # e.g. vmA.cuttlefishGuest.structuredLogcatOut
    target_role: str = ""  # e.g. privateTcpBoundary
    target_port: str = ""  # e.g. privateTcpBoundary.vmAIn
    doc: str = ""  # doc comment preceding the flow declaration

    @property
    def source_path(self) -> list[str]:
        return self.source.split(".")

    @property
    def target_path(self) -> list[str]:
        return self.target.split(".")

    @property
    def source_host(self) -> str:
        return self.source_path[0]

    @property
    def target_host(self) -> str:
        return self.target_path[0]

    @property
    def payload(self) -> str:
        """The typed item at the end of the endpoint path."""
        return self.source_path[-1]

    @property
    def stable_id(self) -> str:
        return f"flow-{self.index}"


FLOW_RE = re.compile(
    r"\bflow\s+from\s+([A-Za-z_][A-Za-z0-9_.]*)\s+"
    r"to\s+([A-Za-z_][A-Za-z0-9_.]*)\s*;"
)


def extract_flows(deployment_body: str) -> list[Flow]:
    """Extract all `flow from A to B;` declarations in declaration order."""
    flows: list[Flow] = []
    for index, match in enumerate(FLOW_RE.finditer(deployment_body)):
        flows.append(Flow(source=match.group(1), target=match.group(2), index=index))
    return flows


PART_USAGE_RE = re.compile(
    r"\bpart\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*([A-Za-z_][A-Za-z0-9_]*)\s*;"
)


def extract_part_usages(deployment_body: str) -> dict[str, str]:
    """Extract `part name : Type;` usages -> {usage_name: type_name}."""
    return dict(PART_USAGE_RE.findall(deployment_body))


def load_model(path: str | Path) -> str:
    """Read a .sysml file and strip comments for structural parsing."""
    return strip_comments(Path(path).read_text(encoding="utf-8"))


DOC_BLOCK_RE = re.compile(r"\bdoc\s*/\*(.*?)\*/", flags=re.DOTALL)


def _normalize_doc(raw: str) -> str:
    """Collapse a `doc /* ... */` body to one trimmed line of prose."""
    lines = [re.sub(r"^\s*\*\s?", "", line) for line in raw.splitlines()]
    return " ".join(line.strip() for line in lines if line.strip())


def doc_for_decl(raw_text: str, decl_kind: str, name: str) -> str:
    """Return the first `doc /* ... */` inside a `decl_kind name { ... }` block.

    `decl_kind` is the full leading keyword, e.g. "part def" or "port def".
    Returns "" when the declaration is absent (e.g. imported from another
    file) or carries no doc comment.
    """
    try:
        block = named_block(raw_text, decl_kind, name)
    except AssertionError:
        return ""
    match = DOC_BLOCK_RE.search(block)
    if not match:
        return ""
    return _normalize_doc(match.group(1))


def flow_docs(deployment_block_raw: str) -> list[str]:
    """Return the doc text preceding each `flow from ... to ...;` declaration.

    A doc attaches to a flow only when it is immediately followed by that flow
    (whitespace, no other statement between). Entries align with
    `extract_flows()` order; flows without a preceding doc yield "".
    """
    flows = list(FLOW_RE.finditer(deployment_block_raw))
    docs: list[str] = []
    for flow_match in flows:
        best = None
        for doc_match in DOC_BLOCK_RE.finditer(deployment_block_raw[: flow_match.start()]):
            between = deployment_block_raw[doc_match.end() : flow_match.start()]
            if between.strip() == "":
                best = doc_match
        docs.append(_normalize_doc(best.group(1)) if best else "")
    return docs


@dataclass
class ViewSpec:
    """What a SysML v2 `view` usage declares (the diagram's source spec).

    Views are the normative source for diagrams: a view satisfies one or more
    viewpoints, exposes the model subset it shows, and names a rendering.
    Selection is therefore driven by this spec, not by a hardcoded deployment
    name. Fields are empty when the view block omits them.
    """

    name: str  # view usage name, e.g. mwVehicleSpeedCampaignInternalExchangeView
    viewpoint: str = ""  # viewpoint usage name nested in the view
    viewpoint_type: str = ""  # e.g. PhysicalInternalExchangeViewpoint
    concern: str = ""  # frame target, e.g. vehicleSpeedCampaignInternalExchangeConcern
    exposes: list[str] = field(default_factory=list)  # expose targets (raw paths, may have ::)
    depth: int | None = None  # attribute depth, e.g. -1 (all levels)
    render: str = ""  # render hint, e.g. asInterconnectionDiagram
    doc: str = ""  # doc comment on the view usage


VIEW_POINT_USAGE_RE = re.compile(
    r"\bviewpoint\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*([A-Za-z_][A-Za-z0-9_]*)\s*\{"
)
FRAME_RE = re.compile(r"\bframe\s+([A-Za-z_][A-Za-z0-9_.]*)\s*;")
EXPOSE_RE = re.compile(r"\bexpose\s+([A-Za-z_][A-Za-z0-9_.:]*)\s*;")
VIEW_DEPTH_RE = re.compile(r"\battribute\s+depth\s*=\s*(-?\d+)\s*;")
VIEW_RENDER_RE = re.compile(r"\brender\s+([A-Za-z_][A-Za-z0-9_]*)\s*;")


def parse_view_spec(model_text: str, view_name: str) -> ViewSpec | None:
    """Extract the `view <view_name> { ... }` block's declaration spec.

    Operates on comment-stripped text (structure only). Returns None when the
    view block is absent, so callers can fall back to legacy defaults.
    """
    try:
        block = named_block(model_text, "view", view_name)
    except AssertionError:
        return None

    spec = ViewSpec(name=view_name)
    viewpoint = VIEW_POINT_USAGE_RE.search(block)
    if viewpoint:
        spec.viewpoint = viewpoint.group(1)
        spec.viewpoint_type = viewpoint.group(2)
        # The frame lives inside the viewpoint usage body.
        viewpoint_block = named_block(block, "viewpoint", spec.viewpoint)
        frame = FRAME_RE.search(viewpoint_block)
        if frame:
            spec.concern = frame.group(1)

    spec.exposes = [m.group(1) for m in EXPOSE_RE.finditer(block)]
    depth = VIEW_DEPTH_RE.search(block)
    if depth:
        spec.depth = int(depth.group(1))
    render = VIEW_RENDER_RE.search(block)
    if render:
        spec.render = render.group(1)
    doc_match = DOC_BLOCK_RE.search(block)
    if doc_match:
        spec.doc = _normalize_doc(doc_match.group(1))
    return spec
