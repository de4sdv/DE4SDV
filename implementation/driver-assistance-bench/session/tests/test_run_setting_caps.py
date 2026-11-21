"""The s1 disk test's run cap agrees with the session's source for it (the x86 gates at 70974ffb).

test_s1_checks_the_disk_before_each_score_start_with_one_runs_need pinned 90 s for SC-DRIVING-012@20 after lane
I-W's merge cut that setting's cap to 60 s (scenarios.py:135). The session asked for the 60 s need and the test
expected the 90 s one, so it failed in both x86 gates.

The cap has one source the session and the test both read: `run_setting.py <scenario> <setting>` prints
`<id> <speed_limit> <cap_s> <lo_kmh> <hi_kmh>`, and the session fills RUN_CAP from it.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SESSION = Path(__file__).resolve().parents[1]


def test_the_disk_tests_012_cap_is_the_sessions_own() -> None:
    out = subprocess.run([sys.executable, str(SESSION / "run_setting.py"), "SC-DRIVING-012", "20kmh"],
                         capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    fields = out.stdout.split()
    assert fields[0] == "SC-DRIVING-012@20", fields
    assert float(fields[2]) == 60, f"SC-DRIVING-012@20's run cap is {fields[2]} s; scenarios.py:135 says 60"
