#!/usr/bin/env python3
"""The digest of each run's scenario definition, from the session's kit (da_session.sh, kind s1; plan C5).

  scenario_digest.py <kit.tgz> <out.json> <setting id>...

The model's evidence record names a run's simulated configuration (driver_assistance_verification_evidence.sysml,
RetainedAssistanceRunEvidence.simulatedConfiguration): the blueprints, the map and the road, the weather, the fixed
step and synchronous mode, and the camera rig, for which "a digest of the scenario definition that fixes them is
enough". The bench's scenario definition is the setting's record (world-side/scenarios.py, its model values and the
bench's proposals) and the world-side files that build it: scenarios.py, da_world_side.py (vehicles, step,
synchronous mode, the camera rig), sites.py where the kit has it (the curve and turn-off sites) and scripts/common.sh
(the map). The road itself is the warm-up survey's (world_start.json), recorded per run by the world side.

digest = sha256 of the canonical JSON (sorted keys, no spaces) of {"setting": <the setting's record>, "files":
{<path in the bench>: <sha256 of its bytes in the kit>}}. Everything is read from the kit, the bytes the hosts run.

Prints one line per setting, `<setting id> <digest>`, and writes the details to <out.json>. Exit 2 on an unknown
setting or a kit without scenarios.py.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tarfile
import tempfile
from pathlib import Path

FILES = ("world-side/scenarios.py", "world-side/da_world_side.py", "world-side/sites.py",
         "world-side/scripts/common.sh")


def digest(record: dict, files: dict[str, str]) -> str:
    doc = {"setting": record, "files": files}
    return hashlib.sha256(json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2
    kit, out, ids = argv[0], Path(argv[1]), argv[2:]
    files: dict[str, str] = {}
    with tarfile.open(kit) as t, tempfile.TemporaryDirectory() as tmp:
        for rel in FILES:
            try:
                m = t.getmember("bench/" + rel)
            except KeyError:
                continue
            data = t.extractfile(m).read() if m.isfile() else None
            if data is None:
                continue
            files[rel] = hashlib.sha256(data).hexdigest()
            dest = Path(tmp) / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        if "world-side/scenarios.py" not in files:
            print("scenario_digest: the kit holds no world-side/scenarios.py", file=sys.stderr)
            return 2
        sys.path.insert(0, str(Path(tmp) / "world-side"))
        spec = importlib.util.spec_from_file_location("kit_scenarios", Path(tmp) / "world-side" / "scenarios.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod   # dataclasses resolve their module's annotations through sys.modules
        spec.loader.exec_module(mod)
        result = {}
        for sid in ids:
            try:
                record = mod.setting(sid).as_record()
            except KeyError as error:
                print(f"scenario_digest: {error}", file=sys.stderr)
                return 2
            result[sid] = {"sha256": digest(record, files), "files": files, "setting_record": record,
                           "rule": "sha256 of the canonical JSON of {setting: the setting's record, files: {path: "
                                   "sha256}} (session/scenario_digest.py)"}
    out.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n")
    for sid in ids:
        print(sid, result[sid]["sha256"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
