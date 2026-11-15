#!/usr/bin/env python3
"""Check the DE4SDV virtual E/E signal contract.

Proves four things without a VM, a bus or a databroker:

1. every DBC file parses (cantools is the same parser family the provider uses);
2. every signal referenced by the VSS mapping exists in a DBC, and every signal
   that the mapping claims to carry in each direction is really there;
3. ``dbc_default_values.json`` covers every signal of every frame the provider
   may transmit (``vss2dbc``), which is what ``--dbc-default`` refuses to start
   without;
4. every enumerated VSS leaf with ``allowed`` values agrees with the DBC ``VAL_``
   table it is mapped from, so a VSS client can never receive a label the
   databroker's metadata rejects.

Exit code 0 means the contract is internally consistent. It says nothing about
whether the broker, the provider or the bus behave; that needs the testbed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cantools

ROOT = Path(__file__).resolve().parent.parent
DBC_DIR = ROOT / "dbc"
MAPPING = ROOT / "vss" / "mapping" / "vss_dbc.json"
DEFAULTS = DBC_DIR / "dbc_default_values.json"

errors: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)


def load_contract() -> tuple[cantools.database.Database, dict]:
    db = cantools.database.Database()
    for path in sorted(DBC_DIR.glob("*.dbc")):
        try:
            db.add_dbc_file(str(path))
            print(f"OK    parsed {path.name}")
        except Exception as exc:  # noqa: BLE001 - report, never mask
            fail(f"{path.name}: {exc}")
    mapping = json.loads(MAPPING.read_text())
    return db, mapping


def walk(node: dict, path: str = "Vehicle"):
    yield path, node
    for name, child in (node.get("children") or {}).items():
        yield from walk(child, f"{path}.{name}")


def main() -> int:
    errors.clear()
    db, mapping = load_contract()

    signals = {s.name: (m.name, s) for m in db.messages for s in m.signals}
    messages = {m.name: m for m in db.messages}
    print(f"OK    {len(messages)} frame(s), {len(signals)} signal(s)")

    leaves = [(p, n) for p, n in walk(mapping["Vehicle"]) if n.get("type") != "branch"]

    vss2dbc: list[tuple[str, str]] = []
    dbc2vss: list[tuple[str, str]] = []

    for path, leaf in leaves:
        if "vss2dbc" in leaf:
            sig = leaf["vss2dbc"]["signal"]
            vss2dbc.append((path, sig))
        if "dbc2vss" in leaf:
            sig = leaf["dbc2vss"]["signal"]
            dbc2vss.append((path, sig))

        for direction in ("vss2dbc", "dbc2vss"):
            block = leaf.get(direction)
            if not block:
                continue
            sig = block["signal"]
            if sig not in signals:
                fail(f"{path}.{direction}: signal {sig!r} is not in any DBC")

        allowed = leaf.get("allowed")
        if allowed:
            allowed_labels = {str(value) for value in allowed}
            for direction in ("dbc2vss", "vss2dbc"):
                block = leaf.get(direction)
                if not block or block["signal"] not in signals:
                    continue
                sig_name = block["signal"]
                sig = signals[sig_name][1]
                if sig.choices is None:
                    fail(f"{path}: VSS enumerates {allowed} but DBC signal {sig_name} has no VAL_ table")
                    continue
                labels = {str(value) for value in sig.choices.values()}
                # A status must never publish a label the broker rejects; every
                # allowed actuator target must be encodable in the command DBC.
                missing = labels - allowed_labels if direction == "dbc2vss" else allowed_labels - labels
                if missing:
                    fail(f"{path}.{direction}: incompatible labels {sorted(missing)}; VSS {sorted(allowed_labels)}, DBC {sorted(labels)}")

    print(f"OK    mapping: {len(vss2dbc)} vss2dbc, {len(dbc2vss)} dbc2vss, {len(leaves)} leaf(s)")

    defaults = json.loads(DEFAULTS.read_text())
    sent_frames = {
        signals[sig][0] for sig in (s for _, s in vss2dbc) if sig in signals
    }
    for frame in sorted(sent_frames):
        for sig in [s.name for s in messages[frame].signals]:
            if sig not in defaults:
                fail(f"dbc_default_values.json is missing {sig} (frame {frame})")
    print(f"OK    defaults cover {len(sent_frames)} transmitted frame(s): {sorted(sent_frames)}")

    orphan = sorted(
        sig for sig in signals
        if sig not in {s for _, s in vss2dbc} | {s for _, s in dbc2vss}
    )
    if orphan:
        print(f"NOTE  signals in a DBC but not mapped: {orphan}")

    if errors:
        print("\nFAILED")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("\nPASS  signal contract is consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
