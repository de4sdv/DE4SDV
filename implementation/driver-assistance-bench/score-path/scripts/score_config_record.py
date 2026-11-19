#!/usr/bin/env python3
"""Records what the candidate and the adapter of one S-CORE start read (start_score_side.sh, after the start is up).

  score_config_record.py <stage> <out.json> [<requested speed_limit>]

From the stage: the values of vision_pilot.conf that the model sets for the S-CORE path (PSR
VisionPilotSCOREApplication: source.mode, engine.provider, model.precision, visualization_on, rrd_on, and speed_limit
per scenario by System 2), hero_wait_s of the staged adapter.json, the staged conf's sha256, and the sha256 that the
identity record (run/score/candidate_record.json) gives the same file. It writes them to <out.json> and prints one
line, `SCORE_CONFIG key=value ...` (no commas, no spaces in a value), which the session reads from the step's tail
into session.json (score_runs.<run>.staged).

Exit status: 0 recorded; 2 usage; 3 the stage lacks the conf or adapter.json.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

KEYS = ("source.mode", "engine.provider", "model.precision", "visualization_on", "rrd_on", "speed_limit")


def conf_values(text: str) -> dict[str, str]:
    """The values of an upstream-style .conf: `key = value` with an optional `;` and `#` comment."""
    values: dict[str, str] = {}
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if "=" not in line:
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        values[key] = value.rstrip(";").strip()
    return values


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3):
        print(__doc__, file=sys.stderr)
        return 2
    stage, out = Path(argv[0]), Path(argv[1])
    requested = argv[2] if len(argv) == 3 and argv[2] else None
    conf = stage / "vision_pilot" / "config" / "vision_pilot.conf"
    adapter = stage / "config" / "adapter.json"
    if not conf.is_file() or not adapter.is_file():
        print(f"score_config_record: {conf} or {adapter} is missing", file=sys.stderr)
        return 3
    values = conf_values(conf.read_text(encoding="utf-8"))
    digest = hashlib.sha256(conf.read_bytes()).hexdigest()
    recorded = None
    try:
        record = json.loads((stage / "run" / "score" / "candidate_record.json").read_text(encoding="utf-8"))
        hits = [f.get("sha256") for f in record.get("configuration_files", []) if f.get("path") == str(conf)]
        recorded = hits[0] if hits else None
    except (OSError, ValueError, AttributeError):
        pass
    hero_wait_s = json.loads(adapter.read_text(encoding="utf-8")).get("hero_wait_s")
    doc = {"vision_pilot_conf": {k: values.get(k) for k in KEYS}, "speed_limit_requested": requested,
           "hero_wait_s": hero_wait_s, "vision_pilot_conf_path": str(conf), "vision_pilot_conf_sha256": digest,
           "identity_record_conf_sha256": recorded, "identity_record_carries_the_staged_conf": recorded == digest}
    out.write_text(json.dumps(doc, indent=1) + "\n")
    words = [f"speed_limit={values.get('speed_limit')}", f"speed_limit_requested={requested or 'none'}",
             f"hero_wait_s={hero_wait_s}"] + [f"{k}={values.get(k)}" for k in KEYS[:-1]] + \
        [f"conf_sha256={digest}", f"conf_recorded={1 if recorded == digest else 0}"]
    print("SCORE_CONFIG " + " ".join(w.replace(" ", "_").replace(",", "_") for w in words))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
