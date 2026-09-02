#!/usr/bin/env python3
"""Generate a documented view inventory for a SysML v2 package folder.

Scans every .sysml file under the given folder, extracts each declared
`view` block (viewpoint, framed concern, expose targets, depth, render
hint), and writes a human-readable index that explains the view and maps it
to the rendered artifact used by the privileged Syside validation workflow
(`syside viz view`).

Self-contained: no dependency on the view editor package, so it runs on
any branch.

Usage:
    python scripts/generate_view_index.py \
        textual-notation-of-model/packages/features/middleware
"""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ViewSpec:
    name: str
    view_type: str = ""
    viewpoint: str = ""
    viewpoint_type: str = ""
    concern: str = ""
    exposes: list[str] = field(default_factory=list)
    depth: str = ""
    render: str = ""
    explanation: str = ""


CONCERN_EXPLANATIONS = {
    "conceptualFunctionMappingConcern": (
        "Maps functional responsibilities to the conceptual system elements "
        "that perform them."
    ),
    "conceptualInternalExchangeConcern": (
        "Shows the typed exchanges between conceptual system elements and "
        "their boundary interfaces."
    ),
    "conceptualStructureConcern": (
        "Shows the conceptual system boundary, its responsibilities, and its "
        "internal decomposition."
    ),
    "functionalBehaviorConcern": (
        "Shows the functional actions and the behavior chain used to realize "
        "the feature intent."
    ),
    "functionalInterfaceConcern": (
        "Shows the functional boundary interfaces and the information items "
        "they exchange."
    ),
    "physicalContextConcern": (
        "Shows the physical system of interest together with the external "
        "context used for this engineering slice."
    ),
    "physicalExchangeTypeConcern": (
        "Catalogues the physical exchange types used at the modeled boundary."
    ),
    "physicalInterfaceConcern": (
        "Shows the physical interfaces and typed items used by the selected "
        "realization."
    ),
    "physicalLogicalItemMappingConcern": (
        "Maps logical information items to the physical exchange items that "
        "carry them."
    ),
    "physicalLogicalMappingConcern": (
        "Maps logical responsibilities to the physical elements selected to "
        "realize them."
    ),
    "physicalStructureConcern": (
        "Shows the selected physical or software parts and their structural "
        "decomposition."
    ),
    "requirementTraceConcern": (
        "Shows the requirement set and its trace links to needs, behavior, or "
        "architecture."
    ),
    "stakeholderNeedsConcern": (
        "Lists the stakeholder needs that frame the feature and its engineering "
        "obligations."
    ),
    "visualizationFunctionExchangeConcern": (
        "Shows how visualization functions exchange observation and evidence "
        "information."
    ),
    "visualizationFunctionMappingConcern": (
        "Maps visualization requirements to the functions that address them."
    ),
    "visualizationFunctionStructureConcern": (
        "Shows the functional decomposition of the engineering visualization "
        "chain."
    ),
    "visualizationLogicalExchangeConcern": (
        "Shows the typed exchanges between the logical visualization roles."
    ),
    "visualizationLogicalStructureConcern": (
        "Shows the logical roles that collect, transport, present, and retain "
        "visualization evidence."
    ),
    "visualizationNeedsConcern": (
        "Lists the stakeholder needs that justify the engineering visualization "
        "slice."
    ),
    "visualizationPhysicalExchangeConcern": (
        "Shows the exchanges across the selected physical visualization "
        "realization."
    ),
    "visualizationPhysicalStructureConcern": (
        "Shows the deployed parts that implement the visualization evidence "
        "chain."
    ),
    "visualizationProvenanceMappingConcern": (
        "Maps logical visualization responsibilities to their selected physical "
        "realization."
    ),
    "visualizationRequirementTraceConcern": (
        "Shows how visualization requirements trace to needs and downstream "
        "architecture."
    ),
}


DIAGRAM_PUBLICATION_GAPS = {
    "aebsVisualizationFramingView": (
        "Withheld because the validated SVG contains only the view frame and "
        "expose row; no model elements materialized."
    ),
    "aebsVisualizationFunctionInternalExchangeView": (
        "Withheld because the validated SVG contains only the view frame and "
        "expose rows; no exchange topology or endpoints materialized."
    ),
    "aebsVisualizationFunctionRequirementMappingView": (
        "Withheld because the validated native grid export reported no rows or "
        "columns. The model view remains authoritative, but the native diagram "
        "frame is not a usable mapping matrix."
    ),
}


KNOWN_PRESENTATION_NOTES = {
    "aebsVisualizationProductLineConfigurationView": (
        "Long qualified labels overlap in the current SysIDE layout; use the "
        "source and exposure list above for exact names."
    ),
    "aebsVisualizationProductModelAssemblyView": (
        "Long qualified labels overlap in the current SysIDE layout; use the "
        "source and exposure list above for exact names."
    ),
    "aebsPhysicalLogicalMappingView": (
        "The single-column grid is narrower than its title; the mapping cells "
        "remain readable at full size."
    ),
    "middlewareProductLineConfigurationView": (
        "Long qualified labels overlap in the current SysIDE layout; use the "
        "source and exposure list above for exact names."
    ),
    "middlewareProductModelAssemblyView": (
        "Long qualified labels overlap in the current SysIDE layout; use the "
        "source and exposure list above for exact names."
    ),
}


QUALIFIED_NAME = r"[A-Za-z_][A-Za-z0-9_]*(?:::[A-Za-z_][A-Za-z0-9_]*)*"
VIEW_RE = re.compile(
    rf"\bview\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?::\s*({QUALIFIED_NAME}))?\s*\{{"
)
VIEWPOINT_RE = re.compile(
    r"viewpoint\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*([A-Za-z_][A-Za-z0-9_]*)\s*\{"
)
FRAME_RE = re.compile(r"frame\s+([A-Za-z_][A-Za-z0-9_.]*)")
EXPOSE_RE = re.compile(r"\bexpose\s+([^;\n]+?)\s*;")
DEPTH_RE = re.compile(r"attribute\s+depth\s*=\s*(-?\d+)")
RENDER_RE = re.compile(r"render\s+([A-Za-z_][A-Za-z0-9_]*)")


def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    return text


def _clean_doc(text: str) -> str:
    lines = [re.sub(r"^\s*\*\s?", "", line).strip() for line in text.splitlines()]
    return re.sub(r"\s+", " ", " ".join(lines)).strip()


def _first_sentence(text: str) -> str:
    match = re.match(r"(.+?[.!?])(?:\s|$)", text)
    return match.group(1) if match else text


def _concern_explanation(model_text: str, concern: str) -> str:
    if concern:
        match = re.search(
            rf"\bconcern\s+{re.escape(concern)}\b[^{{]*\{{\s*"
            r"doc\s*/\*(.*?)\*/",
            model_text,
            flags=re.S,
        )
        if match:
            return _first_sentence(_clean_doc(match.group(1)))
        if concern in CONCERN_EXPLANATIONS:
            return CONCERN_EXPLANATIONS[concern]
        words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", concern)
        words = re.sub(r"Concern$", "", words).lower().strip()
        return f"Shows the model elements selected to address the {words} concern."
    return "Shows the model elements selected by this view."


def _find_block(text: str, decl: str, name: str) -> str | None:
    match = re.search(rf"\b{decl}\s+{name}\b[^{{]*\{{", text)
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


def parse_view_spec(model_text: str, name: str) -> ViewSpec | None:
    block = _find_block(_strip_comments(model_text), "view", name)
    if not block:
        return None
    header = re.search(
        rf"\bview\s+{re.escape(name)}\s*(?::\s*({QUALIFIED_NAME}))?\s*\{{",
        block,
    )
    spec = ViewSpec(name=name, view_type=header.group(1) if header and header.group(1) else "")
    vp = VIEWPOINT_RE.search(block)
    if vp:
        spec.viewpoint, spec.viewpoint_type = vp.group(1), vp.group(2)
    frame = FRAME_RE.search(block)
    if frame:
        spec.concern = frame.group(1)
    spec.exposes = [e for e in EXPOSE_RE.findall(block) if e != name]
    depth = DEPTH_RE.search(block)
    if depth:
        spec.depth = depth.group(1)
    render = RENDER_RE.search(block)
    if render:
        spec.render = render.group(1)
    spec.explanation = _concern_explanation(model_text, spec.concern)
    return spec


def artifact_filename(view_name: str, view_type: str) -> str:
    short_type = view_type.rsplit("::", 1)[-1]
    if short_type == "MatrixView":
        return f"diagram-matrix-{view_name}.svg"
    if short_type == "TableView":
        return f"diagram-table-{view_name}.svg"
    return f"diagram-{view_name}.svg"


def collect_views(folder: Path) -> list[tuple[Path, list[ViewSpec]]]:
    out = []
    for path in sorted(folder.glob("*.sysml")):
        text = path.read_text(encoding="utf-8")
        views = []
        for match in VIEW_RE.finditer(text):
            name = match.group(1)
            spec = parse_view_spec(text, name)
            if spec is not None:
                views.append(spec)
        if views:
            out.append((path, views))
    return out


def _folder_title(folder: Path) -> str:
    if folder.name == "aebs":
        return "AEBS Views"
    if folder.name == "de4sdv":
        return "DE4SDV Method Views"
    if folder.name == "product-models":
        return "Product Model Views"
    label = folder.name.replace("_", " ").replace("-", " ").title()
    return f"{label} Views"


def _count_label(count: int, singular: str) -> str:
    suffix = "" if count == 1 else "s"
    return f"{count} {singular}{suffix}"


def _svg_labels(svg: Path) -> list[str]:
    try:
        root = ET.parse(svg).getroot()
    except (OSError, ET.ParseError):
        return []
    labels = []
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] != "text":
            continue
        label = re.sub(r"\s+", " ", "".join(element.itertext())).strip()
        if label:
            labels.append(label)
    return labels


def _presentation_notes(svg: Path, view_name: str) -> list[str]:
    labels = _svg_labels(svg)
    notes = []
    if any(label in {"…", "..."} for label in labels):
        notes.append(
            "The current SVG truncates at least one compartment with an "
            "ellipsis; use the linked source for the complete declaration."
        )
    if len(labels) >= 120:
        notes.append(
            "This is a dense review artifact; open the SVG at full size rather "
            "than reading it from the page thumbnail."
        )
    statement_notes = _table_statement_notes(labels)
    if statement_notes:
        for note in statement_notes:
            notes.append(note)
    anonymous_comments = labels.count("«comment»")
    if anonymous_comments >= 3:
        notes.append(
            f"This render contains {anonymous_comments} anonymous «comment» "
            "boxes; the renderer does not attach them to the elements they "
            "annotate, so treat each comment as a section note for the "
            "declarations that follow it in the source file."
        )
    known_note = KNOWN_PRESENTATION_NOTES.get(view_name)
    if known_note:
        notes.append(known_note)
    return notes


def _table_statement_notes(labels: list[str]) -> list[str]:
    header = next(
        (
            index
            for index in range(len(labels) - 2)
            if labels[index : index + 3] == ["ID", "Name", "Statement"]
        ),
        None,
    )
    if header is None:
        return []
    rows = labels[header + 3 :]
    statements = rows[2::3]
    notes = []
    if statements and all(
        re.match(r"^(N-[A-Z]+-\d+|REQ-[A-Z0-9-]+|MW-\d+)\b", s or " ")
        for s in statements
    ):
        notes.append(
            "Every Statement cell shows a short status line rather than the "
            "full need or requirement prose; the complete statements live in "
            "the source file and the viewer tooltips."
        )
    return notes


def render_markdown(folder: Path) -> str:
    collected = collect_views(folder)
    diagrams_dir = folder / "diagrams"
    view_count = sum(len(views) for _, views in collected)
    published_count = sum(
        (diagrams_dir / artifact_filename(spec.name, spec.view_type)).is_file()
        for _, views in collected
        for spec in views
    )
    lines = [
        f"# {_folder_title(folder)}",
        "",
        "This index lists every SysML v2 `view` declared in the `.sysml` files of",
        "this first-level model area. Each entry explains the reviewer question in",
        "plain language and embeds the committed diagram SysIDE renders from the",
        "view (`syside viz view`, run by the Privileged Syside Validation workflow).",
        "The SVGs live in [`diagrams/`](diagrams/) beside the model files.",
        "",
        "Generated by `scripts/generate_view_index.py` — do not edit by hand.",
        "",
        f"**{_count_label(len(collected), 'file')}, "
        f"{_count_label(view_count, 'view')}, "
        f"{_count_label(published_count, 'published diagram')}.**",
        "",
    ]
    for path, views in collected:
        lines.append(f"## `{path.name}`")
        lines.append("")
        for spec in views:
            lines.append(f"### `{spec.name}`")
            lines.append("")
            lines.append(spec.explanation)
            lines.append("")
            lines.append(f"- **Source:** `{path.name}`")
            if spec.viewpoint:
                lines.append(
                    f"- **Viewpoint:** `{spec.viewpoint}` (`{spec.viewpoint_type}`)"
                )
            if spec.view_type:
                lines.append(f"- **View type:** `{spec.view_type}`")
            if spec.concern:
                lines.append(f"- **Concern:** `{spec.concern}`")
            if spec.exposes:
                lines.append(
                    "- **Exposes:** " + ", ".join(f"`{e}`" for e in spec.exposes)
                )
            if spec.depth:
                lines.append(f"- **Depth:** `{spec.depth}`")
            if spec.render:
                lines.append(f"- **Render:** `{spec.render}`")
            lines.append("")
            filename = artifact_filename(spec.name, spec.view_type)
            svg = diagrams_dir / filename
            if svg.exists():
                lines.append("- **Diagram status:** Published from the committed SysIDE SVG.")
                for note in _presentation_notes(svg, spec.name):
                    lines.append(f"- **Presentation note:** {note}")
                lines.append("")
                lines.append(f"![{spec.name}](diagrams/{filename})")
            else:
                gap = DIAGRAM_PUBLICATION_GAPS.get(spec.name)
                if gap:
                    lines.append(f"- **Diagram status:** {gap}")
                else:
                    lines.append("- **Diagram status:** Not yet published in this folder.")
                lines.append("")
                lines.append(f"_Diagram not present: `diagrams/{filename}` "
                             f"(regenerate via the Privileged Syside Validation workflow)._")
            lines.append("")
    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    folder = Path(sys.argv[1]).resolve()
    if not folder.is_dir():
        print(f"Not a folder: {folder}", file=sys.stderr)
        return 2
    output = folder / "VIEWS.md"
    output.write_text(render_markdown(folder), encoding="utf-8")
    print(f"wrote {output} ({len(output.read_text(encoding='utf-8').splitlines())} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
