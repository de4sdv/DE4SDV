"""CLI for the DE4SDV SysML v2 view editor.

Commands:
  graph    Extract the semantic graph from a .sysml file (JSON to stdout).
  render   Render the graph + layout to an SVG file.
  check    Run the parity gate against a hand-authored expectation.

Examples:
  python -m tools.sysml_view_editor graph --model path/to/model.sysml
  python -m tools.sysml_view_editor render --model path/to/model.sysml \
      --layout path/to/layout.json --output out.svg
  python -m tools.sysml_view_editor check --model path/to/model.sysml \
      --expectation tests/fixtures/expectation.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .graph import load_graph
from .layout import empty_layout, load_layout, reconcile
from .parity import ParityExpectation, check_parity
from .render import render_to_file

DEFAULT_MODEL = (
    "textual-notation-of-model/packages/features/middleware/"
    "mw_physical_software_realization.sysml"
)


def _cmd_graph(args: argparse.Namespace) -> int:
    graph = load_graph(args.model, view_name=args.view, deployment=args.deployment)
    print(json.dumps(graph.to_json(), indent=2, sort_keys=True))
    return 0


def _cmd_render(args: argparse.Namespace) -> int:
    graph = load_graph(args.model, view_name=args.view, deployment=args.deployment)
    if args.layout and Path(args.layout).exists():
        layout = load_layout(args.layout)
    else:
        layout = empty_layout(graph.view_name, graph.semantic_hash())
        if args.layout:
            Path(args.layout).parent.mkdir(parents=True, exist_ok=True)
            from .layout import save_layout

            save_layout(layout, args.layout)
    warnings = reconcile(layout, graph)
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    render_to_file(graph, layout, args.output, title=graph.view_name)
    print(f"wrote {args.output}")
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    graph = load_graph(args.model, view_name=args.view, deployment=args.deployment)
    expected_data = json.loads(Path(args.expectation).read_text(encoding="utf-8"))
    expected = ParityExpectation(
        roles=expected_data["roles"],
        ports=expected_data["ports"],
        flows=[tuple(f) for f in expected_data["flows"]],
        payloads=expected_data["payloads"],
    )
    result = check_parity(graph, expected)
    if result.passed:
        print("parity: PASS")
        return 0
    print("parity: FAIL", file=sys.stderr)
    for error in result.errors:
        print(f"  - {error}", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Path to the authoritative .sysml model file",
    )
    common.add_argument(
        "--view",
        default="mwVehicleSpeedCampaignInternalExchangeView",
        help="View usage that sources the diagram (its expose selects the deployment)",
    )
    common.add_argument(
        "--deployment",
        default=None,
        help="Override: use this deployment part def directly instead of resolving the view's expose",
    )

    p_graph = sub.add_parser("graph", parents=[common], help="Extract the semantic graph (JSON)")

    p_render = sub.add_parser("render", parents=[common], help="Render the view to SVG")
    p_render.add_argument("--layout", help="Layout sidecar path (created if missing)")
    p_render.add_argument("--output", required=True, help="Output SVG path")

    p_check = sub.add_parser("check", parents=[common], help="Run the parity gate")
    p_check.add_argument("--expectation", required=True, help="Parity expectation JSON")

    p_serve = sub.add_parser("serve", parents=[common], help="Run the interactive editor")
    p_serve.add_argument("--layout", help="Layout sidecar path")
    p_serve.add_argument("--port", type=int, default=8000, help="Port to bind")

    args = parser.parse_args(argv)
    if args.command == "graph":
        return _cmd_graph(args)
    if args.command == "render":
        return _cmd_render(args)
    if args.command == "check":
        return _cmd_check(args)
    if args.command == "serve":
        from .serve import serve

        serve(args.model, args.layout, args.port, view_name=args.view, deployment=args.deployment)
        return 0
    parser.error(f"unknown command {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
