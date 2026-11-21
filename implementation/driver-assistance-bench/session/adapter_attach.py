"""Each run's actuation adapter attach, from the fetched S-CORE output (T4 of the closure check of 8fae4100).

The adapter writes one JSON line per event to run/score/actuationAdapter.jsonl (actuation-adapter/run_log.h): a
`config` event whose data holds `heroActorId` once it found the vehicle with role name hero, or an `error` event
(`what`, `message`) when it gave up (actuation_adapter_main.cpp). A run whose adapter never attached sent no command
to the car, whatever the session's exit code.
"""
from __future__ import annotations

import json
import os

RECORD = os.path.join("score_side", "run", "score", "actuationAdapter.jsonl")


def attach(score_out: str, run: str, fetched: bool):
    """{"heroActorId": int | None, "error": str | None}, or "not fetched" / "no adapter record fetched"."""
    if not fetched:
        return "not fetched"
    path = os.path.join(score_out, "score_" + run, RECORD)
    try:
        lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
    except OSError:
        return "no adapter record fetched"
    hero, error = None, None
    for line in lines:
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        data = ev.get("data") if isinstance(ev, dict) else None
        if not isinstance(data, dict):
            continue
        if ev.get("event") == "config" and data.get("heroActorId") is not None:
            hero = data["heroActorId"]
        elif ev.get("event") == "error" and error is None:
            error = ": ".join(str(data[k]) for k in ("what", "message") if data.get(k))
    return {"heroActorId": hero, "error": error}
