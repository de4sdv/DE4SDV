"""Semantic graph extraction for the DE4SDV view editor.

Builds a deterministic graph from the authoritative SysML v2 textual model:
roles (endpoint-bearing parts), ports (typed port features), and directed
typed flows between port features. This graph is the *semantic* input to the
renderer; it contains no presentation state.

The graph is derived entirely from the flow endpoints declared in the
deployment's `flow from A to B;` statements plus the deployment's `part`
usages. Roles/ports that do not participate in a flow are not invented here.

Endpoint path shapes (both occur in the DE4SDV model):

- host.role.port.payload   (4 segments) — role nested inside a host part,
  e.g. vmA.cuttlefishGuest.structuredLogcatOut.envelope
- role.port.payload        (3 segments) — role is a direct deployment part
  that itself carries ports, e.g. privateTcpBoundary.vmAIn.envelope
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .parser import Flow, extract_flows, extract_part_usages, named_block


def resolve_endpoint(path: list[str]) -> tuple[list[str], list[str], str]:
    """Return (role_path, port_path, payload) for a flow endpoint path."""
    if len(path) == 4:
        return path[:2], path[:3], path[3]
    if len(path) == 3:
        return path[:1], path[:2], path[2]
    raise ValueError(
        f"Unsupported endpoint path shape {path!r}: expected "
        "host.role.port.payload or role.port.payload"
    )


@dataclass
class Role:
    """A deployment part that carries flow endpoint ports."""

    id: str  # qualified usage path, e.g. vmA.cuttlefishGuest
    name: str  # short name, e.g. cuttlefishGuest
    host: str  # owning host part usage, e.g. vmA (or the role itself)
    type_name: str  # SysML type of the role part, if resolvable
    doc: str = ""  # doc comment from the role's part definition


@dataclass
class Port:
    """A typed port feature at a flow endpoint."""

    id: str  # qualified path, e.g. vmA.cuttlefishGuest.structuredLogcatOut
    name: str  # short name, e.g. structuredLogcatOut
    role_id: str  # owning role id
    host: str  # owning host
    payload: str  # typed item flowing through this port (from flows)
    doc: str = ""  # doc comment from the port's definition, if resolvable


@dataclass
class SemanticGraph:
    """The full deterministic semantic graph for a deployment view."""

    deployment: str
    view_name: str
    roles: list[Role] = field(default_factory=list)
    ports: list[Port] = field(default_factory=list)
    flows: list[Flow] = field(default_factory=list)
    deployment_doc: str = ""  # doc comment on the deployment part def
    view_spec: dict = field(default_factory=dict)  # the view usage that sourced this diagram

    @property
    def role_ids(self) -> list[str]:
        return [r.id for r in self.roles]

    @property
    def port_ids(self) -> list[str]:
        return [p.id for p in self.ports]

    def semantic_hash(self) -> str:
        """Stable hash of the semantic content (no layout, no ordering noise).

        Docs and view metadata are explanatory content, not topology: they do
        not affect the hash, so an existing layout sidecar stays valid when
        docs or view annotations change.
        """
        payload = {
            "deployment": self.deployment,
            "view": self.view_name,
            "roles": sorted(self.role_ids),
            "ports": sorted(self.port_ids),
            "flows": sorted((f.source, f.target) for f in self.flows),
        }
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()[:16]

    def to_json(self) -> dict:
        return {
            "deployment": self.deployment,
            "view": self.view_name,
            "view_spec": self.view_spec,
            "deployment_doc": self.deployment_doc,
            "roles": [
                {"id": r.id, "name": r.name, "host": r.host, "type": r.type_name, "doc": r.doc}
                for r in self.roles
            ],
            "ports": [
                {
                    "id": p.id,
                    "name": p.name,
                    "role": p.role_id,
                    "host": p.host,
                    "payload": p.payload,
                    "doc": p.doc,
                }
                for p in self.ports
            ],
            "flows": [
                {
                    "id": f.stable_id,
                    "source": f.source,
                    "target": f.target,
                    "payload": f.payload,
                    "doc": f.doc,
                }
                for f in self.flows
            ],
            "semantic_hash": self.semantic_hash(),
        }


def _role_type(part_usages: dict[str, str], role_path: list[str], text: str) -> str:
    """Resolve a role part's SysML type name when the definition is in-scope.

    The type of a usage like `vmA.cuttlefishGuest` is the type of the
    part usage named `cuttlefishGuest` inside the part def that types `vmA`.
    A role that is itself a deployment part (e.g. privateTcpBoundary) uses
    the deployment part usage type directly.
    """
    if len(role_path) == 1:
        return part_usages.get(role_path[0], "")
    parent_type = part_usages.get(role_path[0], "")
    if not parent_type:
        return ""
    parent_def = named_block(text, "part def", parent_type)
    nested = extract_part_usages(parent_def)
    return nested.get(role_path[1], "")


def _port_type(text: str, role_type: str, port_name: str) -> str:
    """Resolve a port usage's SysML type inside the role's part definition."""
    if not role_type:
        return ""
    try:
        role_def = named_block(text, "part def", role_type)
    except AssertionError:
        return ""
    match = re.search(
        rf"\bport\s+{re.escape(port_name)}\s*:\s*([A-Za-z_][A-Za-z0-9_]*)\s*;",
        role_def,
    )
    return match.group(1) if match else ""


def attach_docs(graph: SemanticGraph, raw_text: str) -> None:
    """Attach `doc /* ... */` text from the raw SysML source to graph elements.

    Docs are explanatory model content, not presentation: they come from the
    authoritative source and are surfaced by the renderer/editor. Elements
    whose definitions are absent or undocumented keep an empty doc.
    """
    from .parser import doc_for_decl, flow_docs

    graph.deployment_doc = doc_for_decl(raw_text, "part def", graph.deployment)

    for role in graph.roles:
        role.doc = doc_for_decl(raw_text, "part def", role.type_name)

    for port in graph.ports:
        role_type = next(
            (r.type_name for r in graph.roles if r.id == port.role_id), ""
        )
        port_type = _port_type(raw_text, role_type, port.name)
        port.doc = doc_for_decl(raw_text, "port def", port_type)

    deployment_block = named_block(raw_text, "part def", graph.deployment)
    docs = flow_docs(deployment_block)
    for flow, doc in zip(graph.flows, docs):
        flow.doc = doc


def _resolve_deployment_from_view(model_text: str, view_spec) -> str | None:
    """Resolve the view's expose targets to a deployment part def name.

    Expose targets may carry path qualifiers (`vehicleSpeedCampaignDeployment::**`);
    the root name is looked up as a `part <name> : <Type>;` usage, whose type
    is the deployment definition. A direct `part def <name>` expose also works.
    Returns None when nothing resolves (e.g. the view exposes item/port types,
    which this flow-graph renderer cannot project).
    """
    for expose in view_spec.exposes:
        root = expose.split("::", 1)[0].strip()
        if not root:
            continue
        usage = re.search(
            rf"\bpart\s+{re.escape(root)}\s*:\s*([A-Za-z_][A-Za-z0-9_]*)\s*;",
            model_text,
        )
        if usage:
            return usage.group(1)
        try:
            named_block(model_text, "part def", root)
            return root
        except AssertionError:
            continue
    return None


def build_graph(
    model_text: str,
    *,
    deployment: str | None = None,
    view_name: str = "mwVehicleSpeedCampaignInternalExchangeView",
    default_deployment: str = "VehicleSpeedCampaignCommunicationDeployment",
) -> SemanticGraph:
    """Extract the deterministic semantic graph for a deployment view.

    `model_text` must be comment-stripped SysML v2 textual notation.

    Selection is view-driven: when `deployment` is not given explicitly, the
    named `view` block's `expose` targets are resolved to the deployment part
    def (the diagram is sourced from the declared view, per the SysML v2 spec:
    diagrams are rendered view usages). `default_deployment` is used only when
    the model has no resolving view block.
    """
    from .parser import parse_view_spec

    view_spec = parse_view_spec(model_text, view_name)
    deployment_source = "explicit"
    unresolved_exposes: list[str] = []
    if deployment is None:
        resolved = _resolve_deployment_from_view(model_text, view_spec) if view_spec else None
        if resolved:
            deployment = resolved
            deployment_source = "view"
        elif view_spec is not None:
            # The view exists but exposes no deployment part usage — this
            # renderer cannot project its declared content. Fall back, but
            # mark it so consumers surface the mismatch instead of silently
            # drawing the default deployment as if it were the view.
            deployment = default_deployment
            deployment_source = "default"
            unresolved_exposes = list(view_spec.exposes)
        else:
            # No view block in the model at all (legacy input): keep the
            # default deployment as the anchor.
            deployment = default_deployment
            deployment_source = "default"

    deployment_block = named_block(model_text, "part def", deployment)
    flows = extract_flows(deployment_block)
    part_usages = extract_part_usages(deployment_block)

    role_map: dict[str, Role] = {}
    port_map: dict[str, Port] = {}

    def ensure_endpoint(path: list[str]) -> tuple[str, str]:
        role_path, port_path, payload = resolve_endpoint(path)
        role_id = ".".join(role_path)
        if role_id not in role_map:
            role_map[role_id] = Role(
                id=role_id,
                name=role_path[-1],
                host=role_path[0],
                type_name=_role_type(part_usages, role_path, model_text),
            )
        port_id = ".".join(port_path)
        if port_id not in port_map:
            port_map[port_id] = Port(
                id=port_id,
                name=port_path[-1],
                role_id=role_id,
                host=role_path[0],
                payload=payload,
            )
        return role_id, port_id

    for flow in flows:
        source_role, source_port = ensure_endpoint(flow.source_path)
        target_role, target_port = ensure_endpoint(flow.target_path)
        # Store resolved endpoints on the flow for the renderer.
        flow.source_role = source_role
        flow.source_port = source_port
        flow.target_role = target_role
        flow.target_port = target_port

    view_spec_dict = {}
    if view_spec is not None:
        view_spec_dict = {
            "name": view_spec.name,
            "viewpoint": view_spec.viewpoint,
            "viewpoint_type": view_spec.viewpoint_type,
            "concern": view_spec.concern,
            "exposes": view_spec.exposes,
            "depth": view_spec.depth,
            "render": view_spec.render,
            "doc": view_spec.doc,
            "deployment_source": deployment_source,
            "unresolved_exposes": unresolved_exposes,
        }

    return SemanticGraph(
        deployment=deployment,
        view_name=view_name,
        roles=[role_map[k] for k in sorted(role_map)],
        ports=[port_map[k] for k in sorted(port_map)],
        flows=flows,
        view_spec=view_spec_dict,
    )


def load_graph(model_path: str | Path, **kwargs) -> SemanticGraph:
    """Build a semantic graph directly from a .sysml file path.

    Structural parsing uses comment-stripped text; doc comments are then
    attached from the raw source.
    """
    from .parser import load_model

    raw = Path(model_path).read_text(encoding="utf-8")
    graph = build_graph(load_model(model_path), **kwargs)
    attach_docs(graph, raw)
    return graph
