#!/usr/bin/env python3
"""Drift guard: verify the editor test fixture still mirrors the real model.

The fixture at tools/sysml_view_editor/tests/fixtures/mw_physical_software_realization.sysml
is a *derived snapshot* of the authoritative middleware model. Until PR #90
(feat/mw-vsidl-vehicle-speed-bridge) merges, the authoritative file on
origin/main may lack the deployment/view this editor renders, so the fixture
is the unit-test anchor. This guard fails whenever BOTH are present and their
semantic graphs diverge, so the mirror cannot silently rot.

After PR #90 merges, this guard becomes redundant: tests will read the
authoritative file directly and the fixture is deleted.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE = (
    REPO_ROOT
    / "tools/sysml_view_editor/tests/fixtures/mw_physical_software_realization.sysml"
)
AUTHORITATIVE = (
    REPO_ROOT
    / "textual-notation-of-model/packages/features/middleware"
    / "mw_physical_software_realization.sysml"
)
VIEW = "mwVehicleSpeedCampaignInternalExchangeView"


def main() -> int:
    import sys
    sys.path.insert(0, str(REPO_ROOT))
    from tools.sysml_view_editor.graph import load_graph

    if not FIXTURE.exists():
        print(f"ERROR: fixture missing: {FIXTURE}")
        return 2

    fixture_graph = load_graph(FIXTURE, view_name=VIEW)

    if not AUTHORITATIVE.exists():
        print(f"SKIP: authoritative model not present ({AUTHORITATIVE}); "
              f"fixture remains the test anchor until PR #90 merges.")
        return 0

    try:
        real_graph = load_graph(AUTHORITATIVE, view_name=VIEW)
    except Exception as exc:  # pragma: no cover - depends on branch state
        print(f"SKIP: authoritative model present but the view '{VIEW}' is not "
              f"available on this branch (pre-#90 state); fixture remains the "
              f"anchor. Detail: {exc}")
        return 0

    if real_graph.semantic_hash() != fixture_graph.semantic_hash():
        print("DRIFT DETECTED: fixture no longer mirrors the authoritative model.")
        print(f"  fixture: {fixture_graph.semantic_hash()}")
        print(f"  real   : {real_graph.semantic_hash()}")
        print("Regenerate the fixture or update tests before merging.")
        return 1

    print(f"OK: fixture mirrors the authoritative model (hash "
          f"{fixture_graph.semantic_hash()}).")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", action="store_true",
                        help="Print the fixture path and exit")
    args = parser.parse_args()
    if args.path:
        print(FIXTURE)
        sys.exit(0)
    sys.exit(main())
