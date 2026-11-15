#!/usr/bin/env python3
"""Health gate for update_with_rollback.sh, bound to the container the update made.

A status frame proves a zone works only if it comes from the zone the package just
created. A container with the same name can belong to an older vehicle or survive a
failed `up`, so the gate first binds to an identity:

* the container is not the one that existed before the apply (fresh `Id`),
* it is running, and
* its `ImageName` names the digest the package's `parts.yaml` deploys on that
  device. vxedge 0.30.0 creates a payload from the part's `ref@digest`
  (vxedge-core `Part::image_ref`), and names the node `vx-<device id>`
  (`zones::plan::runtime_name_of`) with the payload member `-payload`.

Then it asks that container (by id, not by name) for its own status frame, with a
real monotonic deadline and a growing sleep between attempts, and re-checks the
binding after the frame so a container replaced or exited meanwhile does not pass.

Usage:
  update_health.py container-id <container>
  update_health.py gate --package <dir> --container <name> --previous-id <id|''>
                        --signal <hex id> [--timeout <s>]

`gate` prints one JSON receipt line and exits 0 healthy, 1 not.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

# zones/entrypoint.sh waits up to 60 s for the broker before it starts the plant that
# publishes the status frame; the rest is the plant's own start and a status period.
DEFAULT_TIMEOUT_S = 90.0
FIRST_BACKOFF_S = 0.5
MAX_BACKOFF_S = 5.0
PROBE_TIMEOUT_S = 10.0

# candump line: optional "(timestamp)", interface, id, "[dlc]", payload
FRAME_RE = re.compile(r"^\s*(?:\(\d+\.\d+\)\s+)?\S+\s+([0-9A-Fa-f]{1,8})\s+\[\d+\]")


def has_status_frame(text: str, can_id: int) -> bool:
    """True if a candump line carries `can_id` in its id field (never the payload)."""
    for line in text.splitlines():
        m = FRAME_RE.match(line)
        if m and int(m.group(1), 16) == can_id:
            return True
    return False


def runtime_name_of(node_id: str) -> str:
    """vxedge 0.30.0 `zones::plan::runtime_name_of`."""
    return "vx-" + "".join(c if c.isascii() and c.isalnum() else "-" for c in node_id)[:48]


def expected_image_digest(package_dir: Path | str, container: str) -> str:
    """Digest of the part the package deploys on the device that runs `container`."""
    import yaml  # PyYAML; deliberately only needed by the gate

    pkg = Path(package_dir)
    vehicle = yaml.safe_load((pkg / "vehicle.yaml").read_text())
    parts = yaml.safe_load((pkg / "parts.yaml").read_text())
    devices = [d for d in (vehicle.get("devices") or {}) if runtime_name_of(d) + "-payload" == container]
    if len(devices) != 1:
        raise LookupError(f"{container}: no single device of the package runs it")
    functions = {f for f, spec in (vehicle.get("functions") or {}).items() if spec.get("deployed_on") == devices[0]}
    digests = {
        p["digest"]
        for p in (parts.get("parts") or [])
        if p.get("digest") and functions.intersection(p.get("target_ids") or [])
    }
    if len(digests) != 1:
        raise LookupError(f"{container}: the package pins {len(digests)} payload digests for {devices[0]}")
    return digests.pop()


def parse_identity(inspect_json: str) -> dict | None:
    """Identity from `podman container inspect` (a JSON array of one object)."""
    try:
        data = json.loads(inspect_json)
    except ValueError:
        return None
    if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], dict):
        return None
    c = data[0]
    state = c.get("State") or {}
    return {
        "id": c.get("Id") or "",
        "image_name": c.get("ImageName") or "",
        "running": state.get("Status") == "running",
    }


def binding_problem(identity: dict | None, previous_id: str, digest: str) -> str | None:
    """None when `identity` is the container the apply created; else why not."""
    if identity is None or not identity.get("id"):
        return "missing: no such container"
    if previous_id and identity["id"] == previous_id:
        return "stale: the container predates this apply"
    if not identity.get("running"):
        return "running: the container is not running"
    if not identity.get("image_name", "").endswith("@" + digest):
        return f"digest: image {identity.get('image_name')!r} is not {digest}"
    return None


def wait_until(attempt, timeout_s, clock=time.monotonic, sleep=time.sleep,
               first_backoff=FIRST_BACKOFF_S, max_backoff=MAX_BACKOFF_S):
    """Call `attempt()` until it returns True or `timeout_s` of real time passed.

    Returns (ok, attempts, elapsed). An attempt that fails at once is followed by a
    sleep, so a missing container cannot exhaust the deadline in milliseconds.
    """
    start = clock()
    deadline = start + float(timeout_s)
    backoff = first_backoff
    attempts = 0
    while True:
        attempts += 1
        if attempt():
            return True, attempts, clock() - start
        remaining = deadline - clock()
        if remaining <= 0:
            return False, attempts, clock() - start
        sleep(min(backoff, remaining))
        backoff = min(backoff * 2, max_backoff)


def _run(argv: list[str], timeout: float) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None


def inspect(container: str) -> dict | None:
    res = _run(["podman", "container", "inspect", container], PROBE_TIMEOUT_S)
    if res is None or res.returncode != 0:
        return None
    return parse_identity(res.stdout)


def gate(package: str, container: str, previous_id: str, signal: int, timeout_s: float) -> dict:
    receipt = {"container": container, "package": package, "previous_id": previous_id,
               "signal": f"0x{signal:X}", "timeout_s": timeout_s}
    try:
        digest = expected_image_digest(package, container)
    except (LookupError, OSError, ImportError, AttributeError, TypeError) as exc:
        receipt.update(ok=False, reason=f"identity: {exc}")
        return receipt
    receipt["expected_digest"] = digest
    last = {"reason": "no attempt"}

    def attempt() -> bool:
        ident = inspect(container)
        problem = binding_problem(ident, previous_id, digest)
        if problem:
            last.update(reason=problem, identity=ident)
            return False
        probe = _run(["podman", "exec", ident["id"], "sh", "-c",
                      f"timeout 2 candump -n 1 vcan0,{signal:X}:7FF"], PROBE_TIMEOUT_S)
        if probe is None or not has_status_frame(probe.stdout, signal):
            last.update(reason=f"no 0x{signal:X} frame from {ident['id'][:12]}", identity=ident)
            return False
        after = inspect(container)
        if after is None or after.get("id") != ident["id"] or not after.get("running"):
            last.update(reason="replaced or stopped while probing", identity=after)
            return False
        last.update(reason="healthy", identity=ident)
        return True

    ok, attempts, elapsed = wait_until(attempt, timeout_s)
    receipt.update(ok=ok, attempts=attempts, elapsed_s=round(elapsed, 3), **last)
    return receipt


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    cid = sub.add_parser("container-id")
    cid.add_argument("container")
    g = sub.add_parser("gate")
    g.add_argument("--package", required=True)
    g.add_argument("--container", required=True)
    g.add_argument("--previous-id", default="")
    g.add_argument("--signal", required=True)
    g.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S)
    args = ap.parse_args(argv)
    if args.cmd == "container-id":
        ident = inspect(args.container)
        print(ident["id"] if ident else "")
        return 0
    receipt = gate(args.package, args.container, args.previous_id, int(args.signal, 16), args.timeout)
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
