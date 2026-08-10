"""Tests for the DE4SDV SysML v2 view editor.

The fixture mirrors the DE4SDV middleware topology: five roles, eight ports,
four directed typed flows. Tests lock the semantic-graph extraction, the
parity gate, the layout sidecar lifecycle, and the SVG render.
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
from tools.sysml_view_editor.parser import load_model
from tools.sysml_view_editor.render import render_svg

TOOLS = Path(__file__).resolve().parents[1]
FIXTURES = TOOLS / "tests" / "fixtures"
MODEL = FIXTURES / "mw_physical_software_realization.sysml"
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


def test_fixture_mirrors_de4sdv_topology() -> None:
    model = load_model(MODEL)
    deployment = re.search(
        r"part def VehicleSpeedCampaignCommunicationDeployment\s*\{",
        model,
    )
    assert deployment, "fixture missing deployment part def"
    assert model.count("flow from ") == 4
    assert " render asInterconnectionDiagram;" in model


def test_graph_extracts_five_roles_eight_ports_four_flows() -> None:
    graph = load_graph(MODEL)
    assert len(graph.roles) == 5
    assert len(graph.ports) == 8
    assert len(graph.flows) == 4

    role_ids = set(graph.role_ids)
    assert role_ids == {
        "vmA.cuttlefishGuest",
        "vmA.hostForwarder",
        "vmB.ros2Ingress",
        "vmB.independentObserver",
        "privateTcpBoundary",
    }

    # Exact authoritative flow endpoints preserved.
    endpoints = [(f.source, f.target) for f in graph.flows]
    assert endpoints == [
        (
            "vmA.cuttlefishGuest.structuredLogcatOut.envelope",
            "vmA.hostForwarder.structuredLogcatIn.envelope",
        ),
        (
            "vmA.hostForwarder.privateTcpOut.envelope",
            "privateTcpBoundary.vmAIn.envelope",
        ),
        (
            "privateTcpBoundary.vmBOut.envelope",
            "vmB.ros2Ingress.privateTcpIn.envelope",
        ),
        (
            "vmB.ros2Ingress.velocityReportOut.velocityReport",
            "vmB.independentObserver.velocityReportIn.velocityReport",
        ),
    ]


def test_graph_is_deterministic() -> None:
    first = load_graph(MODEL)
    second = load_graph(MODEL)
    assert first.to_json() == second.to_json()
    assert first.semantic_hash() == second.semantic_hash()


def test_parity_passes_on_fixture() -> None:
    graph = load_graph(MODEL)
    result = check_parity(graph, _expected())
    assert result.passed, result.errors
    assert result.errors == []


def test_parity_catches_missing_flow() -> None:
    graph = load_graph(MODEL)
    expected = _expected()
    # Add a flow to the expectation that the graph does not contain.
    expected.flows.append(
        ("vmA.cuttlefishGuest.inventedOut.envelope", "vmB.inventedIn.envelope")
    )
    result = check_parity(graph, expected)
    assert not result.passed
    assert any("missing flows" in e for e in result.errors)


def test_parity_catches_extra_role() -> None:
    graph = load_graph(MODEL)
    expected = _expected()
    # Remove a role from the expectation so the graph has an unexpected one.
    expected.roles.remove("vmA.cuttlefishGuest")
    result = check_parity(graph, expected)
    assert not result.passed
    assert any("unexpected roles" in e for e in result.errors)


def test_docs_extracted_from_fixture() -> None:
    """Source `doc` comments attach to roles, ports, flows, and deployment."""
    graph = load_graph(MODEL)

    assert "provider/observer" in graph.deployment_doc.lower() or "campaign" in graph.deployment_doc.lower()

    cuttlefish = next(r for r in graph.roles if r.id == "vmA.cuttlefishGuest")
    assert "guest-side" in cuttlefish.doc.lower()
    assert "logcat" in cuttlefish.doc.lower()

    boundary = next(r for r in graph.roles if r.id == "privateTcpBoundary")
    assert "private tcp" in boundary.doc.lower()

    # Port docs resolve through the role's part definition -> port definition.
    logcat_in = next(p for p in graph.ports if p.id == "vmA.hostForwarder.structuredLogcatIn")
    assert "logcat" in logcat_in.doc.lower()

    # Flow docs attach to the immediately preceding doc comment.
    assert any(f.doc for f in graph.flows), "expected at least one flow doc"
    first = graph.flows[0]
    assert "envelope" in first.doc.lower()


def test_docs_do_not_change_semantic_hash_or_parity() -> None:
    """Docs are explanatory, not topological: hash and parity stay stable."""
    stripped_only = build_graph(load_model(MODEL))
    with_docs = load_graph(MODEL)
    assert stripped_only.semantic_hash() == with_docs.semantic_hash()
    result = check_parity(with_docs, _expected())
    assert result.passed, result.errors


def test_render_embeds_doc_tooltips() -> None:
    graph = load_graph(MODEL)
    layout = empty_layout(graph.view_name, graph.semantic_hash())
    svg = render_svg(graph, layout, title=graph.view_name)

    # Roles and flows carry <title> tooltips populated from source docs.
    assert "<title>" in svg
    assert svg.count("<title>") >= len(graph.roles) + len(graph.flows)
    # A specific role doc text appears inside a tooltip.
    assert "logcat" in svg.lower()


def test_layout_sidecar_roundtrip() -> None:
    graph = load_graph(MODEL)
    layout = empty_layout(graph.view_name, graph.semantic_hash())
    layout["nodes"]["vmA.cuttlefishGuest"] = {
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
        assert loaded["nodes"]["vmA.cuttlefishGuest"]["x"] == 42
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
    graph = load_graph(MODEL)
    layout = empty_layout(graph.view_name, graph.semantic_hash())

    warnings = reconcile(layout, graph)
    assert any("unplaced: vmA.cuttlefishGuest" in w for w in warnings)
    assert any("unplaced: flow-0" in w for w in warnings)

    # Orphan entries are reported, never silently dropped.
    layout["nodes"]["vmA.deletedRole"] = {"x": 0, "y": 0}
    warnings = reconcile(layout, graph)
    assert any("orphan: vmA.deletedRole" in w for w in warnings)


def test_render_produces_svg_with_topology() -> None:
    graph = load_graph(MODEL)
    layout = empty_layout(graph.view_name, graph.semantic_hash())
    svg = render_svg(graph, layout, title=graph.view_name)

    assert svg.startswith("<svg")
    assert svg.endswith("</svg>")

    # All five role names appear as box labels.
    for role in graph.roles:
        assert role.name in svg

    # All four flow payload labels appear.
    assert svg.count(">envelope<") >= 3
    assert svg.count(">velocityReport<") >= 1

    # Role boxes exist: count rects >= roles.
    assert svg.count("<rect ") >= len(graph.roles)


def test_render_ignores_layout_only_state() -> None:
    """Layout entries do not add semantic elements to the rendered graph."""
    graph = load_graph(MODEL)
    layout = empty_layout(graph.view_name, graph.semantic_hash())
    layout["nodes"]["vmA.inventedRole"] = {"x": 0, "y": 0}  # orphan, not semantic
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
        layout["nodes"]["vmA.cuttlefishGuest"] = {
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
        assert fresh["nodes"]["vmA.cuttlefishGuest"]["x"] == 80

        # The sidecar on disk must also contain it.
        disk = json.loads(layout_path.read_text(encoding="utf-8"))
        assert disk["nodes"]["vmA.cuttlefishGuest"]["y"] == 160
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
