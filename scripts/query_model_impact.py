#!/usr/bin/env python3
"""Impact analysis tool for AEBS SysML v2 model slices.

Answers the question: *if I change requirement X, what is affected?*

The default text backend preserves the existing repository-file query. The API
backend performs ontology-mapped semantic traversal against one exact Systems
Modeling API project/commit bound to one Git revision. A validated full-model
binding is the production source; the bounded fixture remains test infrastructure.

A reverse map ``target -> [(file, dependency_name, source)]`` lets a
maintainer see every evidence contract and verification case that traces
to a given requirement or stakeholder need.

Usage
-----
::

    python3 scripts/query_model_impact.py reqCommandEmergencyBraking
    python3 scripts/query_model_impact.py --list-requirements
    python3 scripts/query_model_impact.py --list-evidence-contracts
    python3 scripts/query_model_impact.py --json reqCommandEmergencyBraking

No V&V verdict, satisfaction claim, or regulatory compliance claim is
made by this tool. The dependencies it indexes are *relevance* links in
the model, not ``verify`` or ``satisfy`` relationships.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
AEBS_DIR = ROOT / "textual-notation-of-model" / "packages" / "features" / "aebs"
REQUIREMENTS_FILE = AEBS_DIR / "aebs_needs_requirements.sysml"

# --- Regexes ---------------------------------------------------------------

# ``requirement reqXxx`` and ``requirement needXxx`` usages.
REQUIREMENT_RE = re.compile(
    r"\brequirement\s+(req[A-Za-z_]\w*|need[A-Za-z_]\w*)\b"
)

# ``requirement <name>`` usages that declare evidence contracts
# (the convention in the model is ``evidenceContract...``).
EVIDENCE_CONTRACT_RE = re.compile(
    r"\brequirement\s+(evidenceContract\w+)\b"
)

# A SysML v2 textual-notation dependency spans two lines, e.g.::
#
#     dependency warningEvidenceRelevantToWarningCandidate
#         from evidenceContract009BWarningLead to reqProvideCollisionWarning;
#
DEPENDENCY_RE = re.compile(
    r"\bdependency\s+([A-Za-z_]\w*)\s*\n\s*"
    r"from\s+([A-Za-z_]\w*)\s+to\s+([A-Za-z_]\w*)\s*;",
    re.MULTILINE,
)

# A one-liner dependency (also present in the requirements file).
DEPENDENCY_INLINE_RE = re.compile(
    r"\bdependency\s+([A-Za-z_]\w*)\s+"
    r"from\s+([A-Za-z_]\w*)\s+to\s+([A-Za-z_]\w*)\s*;",
)

# ``verification def Name`` declarations.
VERIFICATION_DEF_RE = re.compile(r"\bverification\s+def\s+([A-Za-z_]\w*)\b")

# ``verification <usageName> : <defName>`` usages.
VERIFICATION_USAGE_RE = re.compile(
    r"\bverification\s+([A-Za-z_]\w*)\s*:\s*([A-Za-z_]\w*)"
)


# --- Data classes ----------------------------------------------------------


@dataclass
class DependencyEdge:
    """A single ``dependency ... from <source> to <target>`` relationship."""

    name: str
    source: str
    target: str
    file: str
    verification_def: Optional[str] = None
    verification_usage: Optional[str] = None


@dataclass
class ImpactReport:
    """Result of querying a single target node."""

    target: str
    edges: List[DependencyEdge] = field(default_factory=list)

    def to_dict(self) -> dict:
        by_file: Dict[str, list] = defaultdict(list)
        for edge in self.edges:
            by_file[edge.file].append(
                {
                    "dependency": edge.name,
                    "source": edge.source,
                    "verification_def": edge.verification_def,
                    "verification_usage": edge.verification_usage,
                }
            )
        return {
            "target": self.target,
            "count": len(self.edges),
            "files": {
                fname: {"count": len(items), "edges": items}
                for fname, items in sorted(by_file.items())
            },
        }


# --- Parsing helpers -------------------------------------------------------


def _strip_comments(text: str) -> str:
    """Remove ``/* ... */`` and ``// ...`` comments, preserving newlines."""
    text = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=re.DOTALL)
    text = re.sub(r"//[^\n]*", "", text)
    return text


def _find_all_dependencies(text: str, file_name: str) -> List[DependencyEdge]:
    """Return every dependency edge declared in ``text``.

    Handles both the two-line (indented ``from``/``to``) and the one-line
    forms of the SysML v2 textual notation.
    """
    code = _strip_comments(text)
    edges: List[DependencyEdge] = []

    seen: set = set()
    for regex in (DEPENDENCY_RE, DEPENDENCY_INLINE_RE):
        for match in regex.finditer(code):
            name, source, target = (match.group(1), match.group(2), match.group(3))
            key = (name, source, target)
            if key in seen:
                continue
            seen.add(key)
            edges.append(
                DependencyEdge(
                    name=name,
                    source=source,
                    target=target,
                    file=file_name,
                )
            )
    return edges


def _braced_block(code: str, header: str) -> Optional[Tuple[int, int]]:
    """Return ``(start, end)`` char offsets of the body following ``header``.

    ``header`` is a string like ``"verification def Name"``. Returns ``None``
    if the header is not found or no matching ``{ ... }`` block exists.
    """
    idx = code.find(header)
    if idx == -1:
        return None
    opening = code.find("{", idx + len(header))
    if opening == -1:
        return None
    depth = 0
    for pos in range(opening, len(code)):
        ch = code[pos]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return (opening + 1, pos)
    return None


def _annotate_edges_with_verification(
    edges: List[DependencyEdge], code: str
) -> None:
    """Fill in the verification def / usage that owns each edge's source.

    In the AEBS model slices the ``dependency ... from <source> to <target>``
    declarations live at package level, *not* inside a ``verification def``
    block. The meaningful ownership link is: the evidence contract ``source``
    is verified by a ``verification def`` whose body contains
    ``verify <source>;``. This helper finds that def and the
    ``verification <usage> : <def>`` that instantiates it.

    Uses the same braced-block extraction as
    :mod:`tests.sysml_shapes`.
    """
    code_no_comments = _strip_comments(code)

    # Map: source-evidence-contract-name -> verification def name.
    source_to_vdef: Dict[str, str] = {}
    for m in VERIFICATION_DEF_RE.finditer(code_no_comments):
        vdef_name = m.group(1)
        span = _braced_block(code_no_comments, m.group(0))
        if span is None:
            continue
        body = code_no_comments[span[0] : span[1]]
        for v in re.findall(r"\bverify\s+([A-Za-z_]\w*)\s*;", body):
            source_to_vdef[v] = vdef_name

    # Map: verification def name -> list of usage names that instantiate it.
    vdef_to_usages: Dict[str, List[str]] = defaultdict(list)
    for m in VERIFICATION_USAGE_RE.finditer(code_no_comments):
        usage_name, def_name = m.group(1), m.group(2)
        vdef_to_usages[def_name].append(usage_name)

    for edge in edges:
        vdef_name = source_to_vdef.get(edge.source)
        if vdef_name:
            edge.verification_def = vdef_name
            usages = vdef_to_usages.get(vdef_name)
            if usages:
                edge.verification_usage = usages[0]


# --- Model scanner ---------------------------------------------------------


def list_requirements() -> List[str]:
    """Return every ``reqXxx``/``needXxx`` name declared in the requirements file."""
    code = _strip_comments(REQUIREMENTS_FILE.read_text(encoding="utf-8"))
    names: List[str] = []
    seen: set = set()
    for m in REQUIREMENT_RE.finditer(code):
        name = m.group(1)
        if name not in seen:
            seen.add(name)
            names.append(name)
    return names


def _verification_and_evidence_files() -> List[Path]:
    """Return sorted verification + nominal-evidence ``.sysml`` files."""
    files = sorted(AEBS_DIR.glob("*_verification.sysml"))
    nominal = AEBS_DIR / "aebs_evidence.sysml"
    if nominal.exists() and nominal not in files:
        files.append(nominal)
    return files


def list_evidence_contracts() -> List[str]:
    """Return every ``evidenceContract...`` name across verification files."""
    names: List[str] = []
    seen: set = set()
    for path in _verification_and_evidence_files():
        code = _strip_comments(path.read_text(encoding="utf-8"))
        for m in EVIDENCE_CONTRACT_RE.finditer(code):
            name = m.group(1)
            if name not in seen:
                seen.add(name)
                names.append(name)
    return names


def build_reverse_impact_graph() -> Dict[str, List[DependencyEdge]]:
    """Build the reverse map: ``target -> [DependencyEdge, ...]``."""
    graph: Dict[str, List[DependencyEdge]] = defaultdict(list)

    for path in _verification_and_evidence_files():
        text = path.read_text(encoding="utf-8")
        edges = _find_all_dependencies(text, path.name)
        _annotate_edges_with_verification(edges, text)
        for edge in edges:
            graph[edge.target].append(edge)

    return dict(graph)


def query_impact(target: str, graph: Optional[Dict[str, List[DependencyEdge]]] = None) -> ImpactReport:
    """Return all evidence contracts and verification cases that trace to ``target``."""
    if graph is None:
        graph = build_reverse_impact_graph()
    return ImpactReport(target=target, edges=list(graph.get(target, [])))


def query_api_impact(
    target: str,
    *,
    api_url: str,
    binding_path: Path,
    git_revision: str,
    ontology_path: Path = ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml",
) -> dict:
    """Query one exact API revision through the ontology traversal layer."""
    from de4sdv.semantic.api_binding import OntologyApiBinder
    from de4sdv.semantic.impact import ImpactService
    from de4sdv.semantic.kernel_contract import KernelContract
    from de4sdv.semantic.traversal import SemanticTraversal
    from de4sdv.sysml_api.client import ApiClient
    from de4sdv.sysml_api.repository import SysMLRepository
    from de4sdv.sysml_api.revisions import RevisionBinding

    binding = RevisionBinding.load(binding_path)
    contract = KernelContract.load(ontology_path)
    repository = SysMLRepository(ApiClient(api_url))
    return ImpactService(
        repository=repository,
        binding=binding,
        contract=contract,
        binder=OntologyApiBinder(
            contract,
            repository,
            project_id=binding.sysml_project_id,
            commit_id=binding.sysml_commit_id,
        ),
        traversal=SemanticTraversal(contract),
    ).impact(target, git_revision=git_revision)


def current_git_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


# --- CLI rendering ---------------------------------------------------------


def _render_text(report: ImpactReport) -> str:
    lines: List[str] = []
    lines.append(f"Impact analysis for: {report.target}")
    if not report.edges:
        lines.append("  No evidence contracts or verification cases trace to this node.")
        return "\n".join(lines)

    by_file: Dict[str, List[DependencyEdge]] = defaultdict(list)
    for edge in report.edges:
        by_file[edge.file].append(edge)

    lines.append(f"  Files affected: {len(by_file)}")
    lines.append(f"  Total sources:  {len(report.edges)}")
    lines.append("")
    for fname, file_edges in sorted(by_file.items()):
        lines.append(f"  [{fname}]  ({len(file_edges)} source(s))")
        for edge in sorted(file_edges, key=lambda e: e.source):
            parts = [f"source={edge.source}", f"dependency={edge.name}"]
            if edge.verification_def:
                parts.append(f"verification_def={edge.verification_def}")
            if edge.verification_usage:
                parts.append(f"verification_usage={edge.verification_usage}")
            lines.append(f"    - {', '.join(parts)}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _render_api_text(report: dict) -> str:
    revision = report["revision"]
    root = report["root"]
    lines = [
        f"API semantic impact for: {root['qualified_name'] or root['declared_name']}",
        f"  UUID: {root['element_id']}",
        (
            "  Revision: "
            f"Git {revision['git_commit']} -> SysML "
            f"{revision['sysml_project_id']}/{revision['sysml_commit_id']} "
            f"({revision['binding_status']})"
        ),
    ]
    for category in ("architecture", "verification", "evidence", "product-line"):
        nodes = [node for node in report["nodes"] if node["category"] == category]
        lines.append(f"  {category}: {len(nodes)}")
        for node in nodes:
            lines.append(
                f"    - {node['qualified_name'] or node['declared_name']} "
                f"[{node['element_id']}]"
            )
    if report["gaps"]:
        lines.append("  Explicit gaps:")
        for gap in report["gaps"]:
            lines.append(f"    - {gap['category']}: {gap['reason']}")
    lines.append(
        "  Claim boundary: dependency links mean relevance, not verification, "
        "satisfaction, or compliance."
    )
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Trace requirement -> verification cases -> evidence contracts."
    )
    parser.add_argument(
        "target",
        nargs="?",
        help="Requirement or need name to query (e.g. reqCommandEmergencyBraking).",
    )
    parser.add_argument(
        "--list-requirements",
        action="store_true",
        help="Print every requirement/need name found in aebs_needs_requirements.sysml.",
    )
    parser.add_argument(
        "--list-evidence-contracts",
        action="store_true",
        help="Print every evidence contract name across verification files.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of human-readable text (for tooling integration).",
    )
    parser.add_argument(
        "--backend",
        choices=("text", "api"),
        default="text",
        help="Query repository text (default) or one bound SysML API revision.",
    )
    parser.add_argument("--api-url", default="http://127.0.0.1:9000")
    parser.add_argument(
        "--binding",
        type=Path,
        help="Revision-binding JSON required by the API backend.",
    )
    parser.add_argument(
        "--git-revision",
        help="Full Git SHA to compare with the API binding (default: current HEAD).",
    )
    parser.add_argument(
        "--ontology",
        type=Path,
        default=ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml",
    )
    args = parser.parse_args(argv)

    if args.list_requirements:
        names = list_requirements()
        if args.json:
            json.dump({"count": len(names), "requirements": names}, sys.stdout, indent=2)
            sys.stdout.write("\n")
        else:
            print(f"Requirements found: {len(names)}")
            for name in names:
                print(f"  - {name}")
        return 0

    if args.list_evidence_contracts:
        names = list_evidence_contracts()
        if args.json:
            json.dump({"count": len(names), "evidence_contracts": names}, sys.stdout, indent=2)
            sys.stdout.write("\n")
        else:
            print(f"Evidence contracts found: {len(names)}")
            for name in names:
                print(f"  - {name}")
        return 0

    if not args.target:
        parser.error("a target name is required unless --list-* is given")

    if args.backend == "api":
        if args.binding is None:
            parser.error("--binding is required for --backend api")
        api_report = query_api_impact(
            args.target,
            api_url=args.api_url,
            binding_path=args.binding,
            git_revision=args.git_revision or current_git_revision(),
            ontology_path=args.ontology,
        )
        if args.json:
            json.dump(api_report, sys.stdout, indent=2)
            sys.stdout.write("\n")
        else:
            print(_render_api_text(api_report))
        return 0

    report = query_impact(args.target)
    if args.json:
        json.dump(report.to_dict(), sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        print(_render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
