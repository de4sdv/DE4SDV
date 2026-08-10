"""Local server for the DE4SDV SysML v2 view editor.

Serves the interactive editor (static HTML) plus JSON endpoints for the
semantic graph and the layout sidecar. Layout writes are validated with the
same layout.py rules the CLI uses (schema version, structure) before the
sidecar is replaced.

Usage:
  python -m tools.sysml_view_editor serve \
      --model path/to/model.sysml \
      --layout path/to/layout.json \
      --port 8000

Endpoints:
  GET  /                editor HTML
  GET  /graph.json      deterministic semantic graph
  GET  /layout.json     current layout sidecar (empty one created if absent)
  PUT  /layout.json     validate + persist layout sidecar
  GET  /render.svg      server-side render (sanity check / export)
"""

from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .graph import load_graph
from .layout import empty_layout, load_layout, reconcile, save_layout
from .render import render_svg

STATIC_DIR = Path(__file__).resolve().parent / "static"

# Module-level server state, populated by serve() before the handler runs.
from .graph import SemanticGraph

_server_graph: SemanticGraph | None = None
_server_layout_path: Path | None = None
_server_layout: dict = {}


def _graph() -> SemanticGraph:
    assert _server_graph is not None, "serve() must run before the handler"
    return _server_graph


class EditorHandler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, payload: dict) -> None:
        self._send(status, json.dumps(payload).encode("utf-8"), "application/json")

    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        path = self.path.split("?")[0]
        if path == "/" or path == "/index.html":
            html = (STATIC_DIR / "index.html").read_bytes()
            self._send(200, html, "text/html; charset=utf-8")
        elif path == "/graph.json":
            self._json(200, _graph().to_json())
        elif path == "/layout.json":
            self._json(200, _server_layout)
        elif path == "/render.svg":
            g = _graph()
            svg = render_svg(g, _server_layout, title=g.view_name)
            self._send(200, svg.encode("utf-8"), "image/svg+xml")
        else:
            self._json(404, {"error": f"not found: {path}"})

    def do_PUT(self) -> None:  # noqa: N802 (http.server API)
        global _server_layout
        if self.path.split("?")[0] != "/layout.json":
            self._json(404, {"error": "only PUT /layout.json is supported"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            candidate = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            self._json(400, {"error": f"invalid JSON body: {exc}"})
            return

        # Validate structure exactly like load_layout does.
        if candidate.get("schema_version") != 1:
            self._json(400, {"error": "unsupported schema_version"})
            return
        if not isinstance(candidate.get("nodes"), dict):
            self._json(400, {"error": "nodes must be an object"})
            return
        if not isinstance(candidate.get("edges"), dict):
            self._json(400, {"error": "edges must be an object"})
            return

        # Reconcile against the semantic graph: report unplaced/orphan entries.
        warnings = reconcile(candidate, _graph())

        if _server_layout_path is not None:
            save_layout(candidate, _server_layout_path)
        _server_layout = candidate

        self._json(200, {"saved": True, "warnings": warnings})


def serve(
    model_path: str | Path,
    layout_path: str | Path | None,
    port: int,
) -> None:
    global _server_graph, _server_layout_path, _server_layout
    graph = load_graph(model_path)

    if layout_path is not None and Path(layout_path).exists():
        layout = load_layout(layout_path)
    else:
        layout = empty_layout(graph.view_name, graph.semantic_hash())
        if layout_path is not None:
            Path(layout_path).parent.mkdir(parents=True, exist_ok=True)
            save_layout(layout, layout_path)

    _server_graph = graph
    _server_layout_path = Path(layout_path) if layout_path else None
    _server_layout = layout

    server = ThreadingHTTPServer(("127.0.0.1", port), EditorHandler)
    print(f"DE4SDV view editor: http://127.0.0.1:{port}")
    print(f"  model:  {model_path}")
    print(f"  layout: {layout_path or '(in-memory only)'}")
    print("  Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="Path to the .sysml model file")
    parser.add_argument("--layout", default=None, help="Layout sidecar path")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    args = parser.parse_args(argv)
    serve(args.model, args.layout, args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
