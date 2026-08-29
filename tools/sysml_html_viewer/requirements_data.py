"""Needs & requirements data extraction for the viewer's Requirements browser.

Extracts every ``requirement <usage> : <def> { ... }`` record from the parsed
model files (needs, design-input requirements, acceptance criteria, evidence
contracts) with the attributes a reviewer browses: ID, kind, status, subject,
stakeholders, the statement text, the doc text, and the ID cross-references
that form the trace network.

Stdlib only; mirrors the brace-aware parsing conventions of model_parse.py.
The SysML model is the sole authority: nothing is inferred beyond what the
textual notation declares.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .model_parse import ModelFile

# A requirement usage declaration: `requirement <name> : <DefName> {`
_REQ_USAGE_RE = re.compile(r"^(\s*)requirement (\w+)(?:\s*:\s*(\w+))? \{")

# ID carried in the record's doc: `doc /* N-MW-001 ... */`
_ID_RE = re.compile(r"\b([A-Z]{1,6}-[A-Z0-9]+(?:-[A-Z0-9]+)+)\b")

# Statement forms found in the model:
#   require constraint statement { language "English" /* ... */ }
#   require constraint { doc /* ... */ }
_STATEMENT_RE = re.compile(
    r"require constraint(?:\s+statement)?\s*\{[^}]*?/\*(.*?)\*/", re.S
)
_SUBJECT_RE = re.compile(r"\bsubject\s+(\w+)\s*:\s*(\w+)\s*;")
_STAKEHOLDER_RE = re.compile(r"\bstakeholder\s+(\w+)\s*:\s*(\w+)\s*;")

# kinds by ID prefix (the model's own convention) or by definition name
_PREFIX_KIND = (
    ("N-", "need"),
    ("REQ-", "requirement"),
    ("AC-", "acceptance criterion"),
    ("EC-", "evidence contract"),
)


def _record_kind(rid: str, def_name: str) -> str:
    if rid:
        for prefix, kind in _PREFIX_KIND:
            if rid.startswith(prefix):
                return kind
    if "Argument" in def_name:
        return "argument"
    if "CounterClaim" in def_name:
        return "counterclaim"
    if "Claim" in def_name:
        return "claim"
    if "Need" in def_name:
        return "need"
    if def_name.endswith("ProblemStatement"):
        return "problem statement"
    if "EvidenceContract" in def_name:
        return "evidence contract"
    if "AcceptanceCriterion" in def_name:
        return "acceptance criterion"
    return "requirement"


def _clean_doc(doc_text: str) -> str:
    lines = []
    for raw in doc_text.splitlines():
        lines.append(re.sub(r"^\s*\*\s?", "", raw).rstrip())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


@dataclass
class RequirementRecord:
    """One browsable need/requirement record."""

    name: str              # usage name (anchor-unique per file)
    def_name: str          # specializing definition
    kind: str              # need / requirement / acceptance criterion / ...
    rid: str               # controlled ID from the doc ("" when none)
    status: str            # status words from the doc after the ID
    doc: str               # full doc text
    statement: str         # normative statement text (constraint body)
    subject: str           # `subject name : Type` -> "name : Type"
    subject_type: str
    stakeholders: list[str] = field(default_factory=list)
    mentions: list[str] = field(default_factory=list)  # other IDs referenced
    rationale: str = ""    # structured `attribute :>> rationale` (ADR 0009)
    source: str = ""       # structured `attribute :>> source` (ADR 0009)
    rel_path: str = ""
    line: int = 0
    anchor: str = ""       # src-N anchor on the file page

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "def": self.def_name,
            "kind": self.kind,
            "id": self.rid,
            "status": self.status,
            "doc": self.doc,
            "statement": self.statement,
            "subject": self.subject,
            "stakeholders": self.stakeholders,
            "mentions": self.mentions,
            "rationale": self.rationale,
            "source": self.source,
            "file": self.rel_path,
            "line": self.line,
            "anchor": self.anchor,
        }
        return d


def extract_requirements(mf: ModelFile) -> list[RequirementRecord]:
    """All requirement-usage records in one model file, in source order."""
    try:
        text = mf.path.read_text(encoding="utf-8")
    except OSError:
        return []
    lines = text.splitlines()
    out: list[RequirementRecord] = []
    # block extents: from the declaration line to the line where the brace
    # depth (started at the decl's `{`) returns to zero
    open_depth = 0
    cur: tuple[int, int, str] | None = None  # (start_line, depth_at_decl, name)
    blocks: list[tuple[int, int]] = []  # (start_line, end_line)
    decls: list[re.Match] = []
    for lineno, raw in enumerate(lines, start=1):
        m = _REQ_USAGE_RE.match(raw) if cur is None else None
        if m is not None:
            cur = (lineno, depth := open_depth, m.group(2))
            decls.append(m)
        open_depth += raw.count("{") - raw.count("}")
        if cur is not None and open_depth <= cur[1]:
            blocks.append((cur[0], lineno))
            cur = None
    for (start, end), m in zip(blocks, decls):
        block = "\n".join(lines[start - 1 : end])
        docm = re.search(r"doc\s*/\*(.*?)\*/", block, re.S)
        doc = _clean_doc(docm.group(1)) if docm else ""
        idm = _ID_RE.search(doc)
        rid = idm.group(1) if idm else ""
        # structured ODE4HERA/NRM attributes when present (ADR 0009)
        attr_status = re.search(
            r"attribute :>>\s*status\s*=\s*ReqStatus::(\w+)", block
        )
        attr_source = re.search(r'attribute :>>\s*source\s*=\s*"([^"]*)"', block)
        attr_rationale = re.search(
            r'attribute :>>\s*rationale\s*=\s*"([^"]*)"', block
        )
        rationale = attr_rationale.group(1) if attr_rationale else ""
        source = attr_source.group(1) if attr_source else ""
        status = ""
        if idm:
            tail = doc[idm.end():].strip()
            # "draft design-input requirement." / "candidate." -> first sentence
            status = tail.split(".")[0].strip(" ;,") if tail else ""
            if status.lower().startswith("draft") or status.lower().startswith(
                ("candidate", "accepted")
            ):
                status = status.split(";")[0].strip()
            else:
                status = ""
        if attr_status:
            # structured status wins over doc-text heuristics
            status = attr_status.group(1)
        stm = _STATEMENT_RE.search(block)
        statement = _clean_doc(stm.group(1)) if stm else ""
        subj = _SUBJECT_RE.search(block)
        subject = f"{subj.group(1)} : {subj.group(2)}" if subj else ""
        subject_type = subj.group(2) if subj else ""
        stakeholders = [m2.group(1) for m2 in _STAKEHOLDER_RE.finditer(block)]
        # ID cross-references: IDs in doc + statement + body, excluding own
        mentions: list[str] = []
        for idm2 in _ID_RE.finditer(block):
            rid2 = idm2.group(1)
            if rid2 != rid and rid2 not in mentions:
                mentions.append(rid2)
        out.append(
            RequirementRecord(
                name=m.group(2),
                def_name=m.group(3) or "",
                kind=_record_kind(rid, m.group(3) or ""),
                rid=rid,
                status=status,
                doc=doc,
                statement=statement,
                subject=subject,
                subject_type=subject_type,
                stakeholders=stakeholders,
                mentions=mentions,
                rationale=rationale,
                source=source,
                rel_path=mf.rel_path,
                line=start,
                anchor=f"src-{start}",
            )
        )
    return out


def collect_requirement_records(
    files: list[ModelFile],
) -> list[RequirementRecord]:
    """Every requirement record across the model, in stable file order."""
    records: list[RequirementRecord] = []
    for mf in files:
        records.extend(extract_requirements(mf))
    return records


def build_trace_links(
    records: list[RequirementRecord],
) -> dict[str, list[str]]:
    """ID -> IDs of records whose text references it (bidirectional mention
    network). Only IDs that resolve to a record are kept."""
    by_id = {r.rid: r for r in records if r.rid}
    links: dict[str, list[str]] = {}
    for r in records:
        for mentioned in r.mentions:
            if mentioned in by_id:
                links.setdefault(r.rid, []).append(mentioned)
                links.setdefault(mentioned, []).append(r.rid)
    # dedupe, stable order
    out: dict[str, list[str]] = {}
    for rid, targets in links.items():
        seen: list[str] = []
        for t in targets:
            if t not in seen:
                seen.append(t)
        out[rid] = seen
    return out


def stats(records: list[RequirementRecord]) -> dict[str, int]:
    kinds: dict[str, int] = {}
    for r in records:
        kinds[r.kind] = kinds.get(r.kind, 0) + 1
    return kinds
