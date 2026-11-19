#!/usr/bin/env python3
"""One run's setting for the session (da_session.sh): the setting id the world side builds and the candidate's
speed_limit for it.

  run_setting.py <scenario> <setting>     e.g. SC-DRIVING-012 20kmh, or ASM-DRIVING-006 20kmh (calib_steer)

The mapping of <scenario> <setting> to a setting id is the world side's (world-side/scripts/common.sh ws_setting:
a calibration scenario runs on SC-DRIVING-012's road and vehicle). The values come from world-side/scenarios.py, the
model's settings: speed_limit_mps is that file's proposal, the middle of the setting's tolerance (SC-DRIVING-012@20:
20 to 22 km/h, so 21 km/h, 5.833 m/s), so that the candidate's own driving can hold the band; the model asks that
speed_limit be set per scenario by System 2 (PSR VisionPilotSCOREApplication) and sets no value of its own.

Prints one line: <setting id> <speed_limit_mps> <run_cap_s> <low_kmh> <high_kmh>. Exit 2 on an unknown setting.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "world-side"))
import scenarios  # noqa: E402


def setting_id(scenario: str, setting: str) -> str:
    if "@" in setting:
        return setting
    for unit in ("kmh", "km/h"):
        if setting.endswith(unit):
            setting = setting[: -len(unit)]
    if not scenario.startswith("SC-DRIVING-"):
        scenario = "SC-DRIVING-012"
    return f"{scenario}@{setting}"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        st = scenarios.setting(setting_id(*argv))
    except KeyError as error:
        print(f"run_setting: {error}", file=sys.stderr)
        return 2
    print(f"{st.setting_id} {st.speed_limit_mps} {st.run_cap_s:g} {st.low_kmh:g} {st.high_kmh:g}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
