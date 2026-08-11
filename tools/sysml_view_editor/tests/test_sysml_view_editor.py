"""Tests for the DE4SDV SysML v2 view editor.

The test model is a small synthetic fixture (synthetic_exchange_view.sysml)
that exercises the same pipeline features as the real middleware model —
view-driven sourcing, typed ports and flows, source docs, payload labels —
without duplicating any authoritative model. The middleware model itself is
exercised by the integration gate that becomes mandatory after PR #90 merges.
"""

import json
import re
from pathlib import Path

from tools.sysml_view_editor.graph import build_graph, load_graph
from tools.sysml_view_editor.layout import (
    LayoutError,
    empty_layout,
    load_layout,
    reconcile,
    save_layout,
)
from tools.sysml_view_editor.parity import ParityExpectation, check_parity
from tools.sysml_view_editor.parser import load_model, parse_view_spec
from tools.sysml_view_editor.render import render_svg

TOOLS = Path(__file__).resolve().parents[1]
FIXTURES = TOOLS / "tests" / "fixtures"
MODEL = FIXTURES / "synthetic_exchange_view.sysml"
VIEW = "syntheticExchangeView"
DEPLOYMENT = "SyntheticExchangeDeployment"
EXPECTATION = json.loads((FIXTURES / "expectation.json").read_text(encoding="utf-8"))


def _expected() -> ParityExpectation:
    # Deep-copy the module-level expectation: parity-mutation tests must not
    # leak their edits into later tests that read the same fixture data.
    expectation = json.loads(json.dumps(EXPECTATION))
    return ParityExpectation(
        roles=expectation["roles"],
        ports=expectation["ports"],
        flows=[tuple(f) for f in expectation["flows"]],
        payloads=expectation["payloads"],
    )


def test_fixture_is_synthetic_and_self_contained() -> None:
    """The fixture must be original test data, not a copy of a real model."""
    text = Path(MODEL).read_text(encoding="utf-8")
    assert "SYNTHETIC TEST MODEL" in text
    assert "NOT a copy of any DE4SDV model" in text
    # It must not silently mirror the middleware model's identifiers.
    assert "VehicleSpeedCampaign" not in text
    assert "structuredLogcat" not in text


def test_graph_extracts_three_roles_four_ports_two_flows() -> None:
    graph = load_graph(MODEL, view_name=VIEW)
    assert len(graph.roles) == 3
    assert len(graph.ports) == 4
    assert len(graph.flows) == 2

    role_ids = set(graph.role_ids)
    assert role_ids == {"producer", "relay", "consumer"}

    # Exact flow endpoints preserved.
    endpoints = [(f.source, f.target) for f in graph.flows]
    assert endpoints == [
        ("producer.requestOut.request", "relay.requestIn.request"),
        ("relay.responseOut.response", "consumer.responseIn.response"),
    ]


def test_graph_is_deterministic() -> None:
    first = load_graph(MODEL, view_name=VIEW)
    second = load_graph(MODEL, view_name=VIEW)
    assert first.to_json() == second.to_json()
    assert first.semantic_hash() == second.semantic_hash()


def test_parity_passes_on_fixture() -> None:
    graph = load_graph(MODEL, view_name=VIEW)
    result = check_parity(graph, _expected())
    assert result.passed, result.errors
    assert result.errors == []


def test_parity_catches_missing_flow() -> None:
    graph = load_graph(MODEL, view_name=VIEW)
    expected = _expected()
    # Add a flow to the expectation that the graph does not contain.
    expected.flows.append(
        ("producer.inventedOut.request", "consumer.inventedIn.request")
    )
    result = check_parity(graph, expected)
    assert not result.passed
    assert any("missing flows" in e for e in result.errors)


def test_parity_catches_extra_role() -> None:
    graph = load_graph(MODEL, view_name=VIEW)
    expected = _expected()
    # Remove a role from the expectation so the graph has an unexpected one.
    expected.roles.remove("producer")
    result = check_parity(graph, expected)
    assert not result.passed
    assert any("unexpected roles" in e for e in result.errors)


def test_docs_extracted_from_fixture() -> None:
    """Source `doc` comments attach to roles, ports, flows, and deployment."""
    graph = load_graph(MODEL, view_name=VIEW)

    assert "synthetic deployment" in graph.deployment_doc.lower()

    producer = next(r for r in graph.roles if r.id == "producer")
    assert "producer" in producer.doc.lower()
    assert "request" in producer.doc.lower()

    relay = next(r for r in graph.roles if r.id == "relay")
    assert "relay" in relay.doc.lower()

    # Port docs resolve through the role's part definition -> port definition.
    relay_in = next(p for p in graph.ports if p.id == "relay.requestIn")
    assert "request" in relay_in.doc.lower()

    # Flow docs attach to the immediately preceding doc comment.
    assert any(f.doc for f in graph.flows), "expected at least one flow doc"
    first = graph.flows[0]
    assert "request" in first.doc.lower()


def test_docs_do_not_change_semantic_hash_or_parity() -> None:
    """Docs are explanatory, not topological: hash and parity stay stable."""
    stripped_only = build_graph(load_model(MODEL), view_name=VIEW)
    with_docs = load_graph(MODEL, view_name=VIEW)
    assert stripped_only.semantic_hash() == with_docs.semantic_hash()
    result = check_parity(with_docs, _expected())
    assert result.passed, result.errors


def test_render_embeds_doc_tooltips() -> None:
    graph = load_graph(MODEL, view_name=VIEW)
    layout = empty_layout(graph.view_name, graph.semantic_hash())
    svg = render_svg(graph, layout, title=graph.view_name)

    # Roles and flows carry <title> tooltips populated from source docs.
    assert "<title>" in svg
    assert svg.count("<title>") >= len(graph.roles) + len(graph.flows)
    # A specific role doc text appears inside a tooltip.
    assert "producer" in svg.lower()


def test_render_shows_doc_compartment_inside_roles() -> None:
    """Docs are visible in the role compartment, not only on hover/click."""
    graph = load_graph(MODEL, view_name=VIEW)
    layout = empty_layout(graph.view_name, graph.semantic_hash())
    svg = render_svg(graph, layout, title=graph.view_name)

    # A separatory line per documented role.
    documented_roles = [r for r in graph.roles if r.doc]
    assert documented_roles, "fixture must document roles"
    assert svg.count("<line ") >= len(documented_roles)

    # The doc text appears as visible SVG text (not only in <title>).
    producer = next(r for r in graph.roles if r.id == "producer")
    first_words = " ".join(producer.doc.split()[:4])
    assert first_words in svg

    # Boxes grow: documented roles are taller than the base height.
    import re as _re
    rects = _re.findall(r'<rect x="[^"]+" y="[^"]+" width="200" height="(\d+)"', svg)
    assert any(int(h) > 120 for h in rects), f"expected taller doc boxes, got {rects}"


def test_doc_wrap_is_deterministic_and_capped() -> None:
    from tools.sysml_view_editor.render import _wrap_doc

    long_doc = "word " * 200
    lines = _wrap_doc(long_doc, 200)
    assert len(lines) == 4  # DOC_MAX_LINES cap with ellipsis
    assert lines[-1].endswith("…")
    # Same input -> same output (Python renderer and JS editor must agree).
    assert _wrap_doc(long_doc, 200) == lines


# ---------------------------------------------------------------------------
# View/viewpoint-driven sourcing: diagrams come from the declared view usage.
# ---------------------------------------------------------------------------

def test_view_spec_parses_from_fixture() -> None:
    """The view block's viewpoint/frame/expose/depth/render are extracted."""
    model = load_model(MODEL)
    spec = parse_view_spec(model, VIEW)
    assert spec is not None
    assert spec.viewpoint == "selectedSyntheticExchangeViewpoint"
    assert spec.viewpoint_type == "PhysicalInternalExchangeViewpoint"
    assert spec.concern == "syntheticExchangeConcern"
    assert "syntheticDeployment" in spec.exposes
    assert spec.depth == -1
    assert spec.render == "asInterconnectionDiagram"


def test_graph_is_sourced_from_view_expose() -> None:
    """Without an explicit deployment, the view's expose selects it."""
    graph = load_graph(MODEL, view_name=VIEW)  # no deployment kwarg -> view-driven
    assert graph.deployment == DEPLOYMENT
    assert graph.view_spec["deployment_source"] == "view"
    assert graph.view_spec["viewpoint_type"] == "PhysicalInternalExchangeViewpoint"
    assert len(graph.roles) == 3
    assert len(graph.ports) == 4
    assert len(graph.flows) == 2


def test_explicit_deployment_overrides_view() -> None:
    """An explicit deployment kwarg wins over view-driven resolution."""
    graph = load_graph(MODEL, view_name=VIEW, deployment=DEPLOYMENT)
    assert graph.deployment == DEPLOYMENT
    assert graph.view_spec["deployment_source"] == "explicit"
    assert len(graph.roles) == 3


def test_view_metadata_does_not_change_shash() -> None:
    """View annotations (viewpoint/concern/render) stay out of the topology hash."""
    explicit = load_graph(MODEL, view_name=VIEW, deployment=DEPLOYMENT)
    view_driven = load_graph(MODEL, view_name=VIEW)
    assert explicit.semantic_hash() == view_driven.semantic_hash()


def test_unresolvable_view_falls_back_to_default_deployment() -> None:
    """A view whose exposes resolve to nothing falls back, marked as default."""
    stripped = load_model(MODEL)
    # Remove the deployment part usage so the expose target disappears.
    import re as _re
    broken = _re.sub(
        r"part syntheticDeployment : SyntheticExchangeDeployment;",
        "",
        stripped,
    )
    graph = build_graph(broken, view_name=VIEW, default_deployment=DEPLOYMENT)
    assert graph.deployment == DEPLOYMENT
    assert graph.view_spec["deployment_source"] == "default"
    assert "syntheticDeployment" in graph.view_spec["unresolved_exposes"]


def test_layout_sidecar_roundtrip() -> None:
    graph = load_graph(MODEL, view_name=VIEW)
    layout = empty_layout(graph.view_name, graph.semantic_hash())
    layout["nodes"]["producer"] = {
        "x": 42,
        "y": 77,
        "width": 200,
        "height": 120,
    }
    layout["edges"]["flow-0"] = {"bend_points": [[10, 10], [20, 20]]}

    path = FIXTURES / "tmp-layout.json"
    try:
        save_layout(layout, path)
        loaded = load_layout(path)
        assert loaded["schema_version"] == 1
        assert loaded["nodes"]["producer"]["x"] == 42
        assert loaded["edges"]["flow-0"]["bend_points"] == [[10, 10], [20, 20]]
    finally:
        path.unlink(missing_ok=True)


def test_layout_rejects_unknown_schema_version() -> None:
    path = FIXTURES / "tmp-bad-layout.json"
    try:
        path.write_text(
            json.dumps({"schema_version": 999, "nodes": {}, "edges": {}}),
            encoding="utf-8",
        )
        try:
            load_layout(path)
            raise AssertionError("expected LayoutError")
        except LayoutError:
            pass
    finally:
        path.unlink(missing_ok=True)


def test_reconcile_reports_unplaced_and_orphans() -> None:
    graph = load_graph(MODEL, view_name=VIEW)
    layout = empty_layout(graph.view_name, graph.semantic_hash())

    warnings = reconcile(layout, graph)
    assert any("unplaced: producer" in w for w in warnings)
    assert any("unplaced: flow-0" in w for w in warnings)

    # Orphan entries are reported, never silently dropped.
    layout["nodes"]["deletedRole"] = {"x": 0, "y": 0}
    warnings = reconcile(layout, graph)
    assert any("orphan: deletedRole" in w for w in warnings)


def test_render_produces_svg_with_topology() -> None:
    graph = load_graph(MODEL, view_name=VIEW)
    layout = empty_layout(graph.view_name, graph.semantic_hash())
    svg = render_svg(graph, layout, title=graph.view_name)

    assert svg.startswith("<svg")
    assert svg.endswith("</svg>")

    # All role names appear as box labels.
    for role in graph.roles:
        assert role.name in svg

    # Both flow payload labels appear.
    assert svg.count(">request<") >= 1
    assert svg.count(">response<") >= 1

    # Role boxes exist: count rects >= roles.
    assert svg.count("<rect ") >= len(graph.roles)


def test_render_ignores_layout_only_state() -> None:
    """Layout entries do not add semantic elements to the rendered graph."""
    graph = load_graph(MODEL, view_name=VIEW)
    layout = empty_layout(graph.view_name, graph.semantic_hash())
    layout["nodes"]["inventedRole"] = {"x": 0, "y": 0}  # orphan, not semantic
    svg = render_svg(graph, layout)
    assert "inventedRole" not in svg


# ---------------------------------------------------------------------------
# serve module tests: endpoints and layout write-back.
# ---------------------------------------------------------------------------

def test_put_requires_global_layout_update() -> None:
    """PUT /layout.json must update the in-memory layout (global state)."""
    import json
    import threading
    import urllib.request

    from tools.sysml_view_editor import serve as serve_module

    layout_path = FIXTURES / "tmp-serve-global-layout.json"
    layout_path.unlink(missing_ok=True)

    # Start the server on an ephemeral port by reserving one.
    import socket

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    thread = threading.Thread(
        target=serve_module.serve,
        args=(MODEL, layout_path, port),
        kwargs={"view_name": VIEW},
        daemon=True,
    )
    thread.start()

    base = f"http://127.0.0.1:{port}"
    try:
        import time

        deadline = time.time() + 5
        while True:
            try:
                urllib.request.urlopen(base + "/graph.json", timeout=0.5)
                break
            except Exception:
                if time.time() > deadline:
                    raise
                time.sleep(0.1)

        # PUT a moved role.
        layout = json.load(urllib.request.urlopen(base + "/layout.json"))
        layout["nodes"]["producer"] = {
            "x": 80,
            "y": 160,
            "width": 200,
            "height": 120,
        }
        req = urllib.request.Request(
            base + "/layout.json",
            data=json.dumps(layout).encode(),
            headers={"Content-Type": "application/json"},
            method="PUT",
        )
        resp = json.load(urllib.request.urlopen(req))
        assert resp["saved"] is True

        # The server's in-memory layout must now contain the moved role.
        fresh = json.load(urllib.request.urlopen(base + "/layout.json"))
        assert fresh["nodes"]["producer"]["x"] == 80

        # The sidecar on disk must also contain it.
        disk = json.loads(layout_path.read_text(encoding="utf-8"))
        assert disk["nodes"]["producer"]["y"] == 160
    finally:
        layout_path.unlink(missing_ok=True)


def test_put_rejects_unknown_schema() -> None:
    """PUT with an unsupported schema version must be rejected (400)."""
    import json
    import socket
    import threading
    import time
    import urllib.error
    import urllib.request

    from tools.sysml_view_editor import serve as serve_module

    layout_path = FIXTURES / "tmp-serve-bad-layout.json"
    layout_path.unlink(missing_ok=True)

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    thread = threading.Thread(
        target=serve_module.serve,
        args=(MODEL, layout_path, port),
        kwargs={"view_name": VIEW},
        daemon=True,
    )
    thread.start()

    base = f"http://127.0.0.1:{port}"
    try:
        deadline = time.time() + 5
        while True:
            try:
                urllib.request.urlopen(base + "/graph.json", timeout=0.5)
                break
            except Exception:
                if time.time() > deadline:
                    raise
                time.sleep(0.1)

        req = urllib.request.Request(
            base + "/layout.json",
            data=json.dumps({"schema_version": 99}).encode(),
            headers={"Content-Type": "application/json"},
            method="PUT",
        )
        try:
            urllib.request.urlopen(req)
            raise AssertionError("expected HTTP 400 for unknown schema")
        except urllib.error.HTTPError as exc:
            assert exc.code == 400
    finally:
        layout_path.unlink(missing_ok=True)
