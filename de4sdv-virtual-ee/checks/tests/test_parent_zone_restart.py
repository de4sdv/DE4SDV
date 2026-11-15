"""A restarted container retains /tmp; its old shutdown marker cannot stop boot."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def test_zone_startup_clears_a_previous_shutdown_marker(tmp_path):
    source = (ROOT / "zones/entrypoint.sh").read_text()
    parts = source.split("# The provider is supervised:", 1)
    assert len(parts) == 2, "startup phase boundary moved; update this executable probe"
    state = tmp_path / "state"
    state.mkdir()
    marker = state / "zone-stopping"
    marker.write_text("previous stop\n")
    config = tmp_path / "dbc_feeder.ini"
    config.write_text("dbc=@@ZONE_DBC@@\n")
    binaries = tmp_path / "bin"
    binaries.mkdir()
    for name in ("ip", "python"):
        path = binaries / name
        path.write_text("#!/bin/sh\nexit 0\n")
        path.chmod(0o755)
    startup = parts[0].replace("/tmp/", str(state) + "/").replace("/opt/zone/dbc_feeder.ini", str(config))
    env = {**os.environ, "PATH": str(binaries) + os.pathsep + os.environ["PATH"], "ZONE_DBC": "/unused.dbc", "ZONE_ECU": "headlamp", "CAN_TUNNEL_REMOTE": ""}
    result = subprocess.run(["/bin/sh", "-c", startup], env=env, text=True, capture_output=True, timeout=5)
    assert result.returncode == 0, result.stderr
    assert not marker.exists(), "a previous container stop must not make the provider supervisor exit immediately on restart"
