#!/usr/bin/env python3
"""Run the AAOS SDV reference runtime campaign (runbook gates 1-8).

Local dry-run (rehearsal, default):

    python3 scripts/run_runtime_campaign.py --backend local --speed-kmh 36 \
      --evidence-out /tmp/campaign-evidence.yaml

Live host run (probes ADB + ROS 2 on the host):

    python3 scripts/run_runtime_campaign.py --backend host \
      --adb-serial <serial> --speed-kmh 36 --evidence-out evidence/e-mw-011.yaml
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent / "vss-vehicle-speed-adapter" / "src"))

from de4sdv_aaos_sdv_reference_bench.runtime_campaign import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
