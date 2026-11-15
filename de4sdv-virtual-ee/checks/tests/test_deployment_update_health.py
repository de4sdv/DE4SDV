"""update_health.py: the pure parts of the update health gate.

Identity assumptions, from vxedge 0.30.0 sources (vxedge-core `zones/plan.rs`,
`model/mod.rs`) and the committed package:

* a container node's runtime name is `vx-` + the device id with every non
  alphanumeric ASCII character replaced by `-`; the payload container is
  `<runtime name>-payload` (the names the harness has always used);
* the payload is created from the deployed part's `image_ref()`, `ref@digest`
  when the part names a digest — which Podman reports as the container's
  `ImageName`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

CHECKS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CHECKS))

import update_health as uh  # noqa: E402

VEHICLE = CHECKS.parent / "vehicle"
# Expected runtime identities come from the independently retained native scan,
# not the resolver under test or a duplicated older deployment pin.
SCANNED_IMAGES = json.loads((CHECKS.parent / "sbom/inventory.json").read_text())["baseline_images"]
ZONE_DIGEST = SCANNED_IMAGES["zone-ecu"].rsplit("@", 1)[1]
GW_DIGEST = SCANNED_IMAGES["can-gw"].rsplit("@", 1)[1]


def test_default_deadline_covers_the_zone_broker_wait():
    # zones/entrypoint.sh waits up to 60 s for the broker before it starts the plant
    # that publishes the status frame, so a shorter gate rejects a healthy zone.
    assert uh.DEFAULT_TIMEOUT_S > 60


@pytest.mark.parametrize(
    "text, ok",
    [
        ("  vcan0  281   [8]  00 00 01 00 00 00 00 00", True),
        (" (1794704071.379251)  vcan0  281   [8]  00 00 01 00 00 00 00 00", True),
        ("  vcan0  181   [8]  00 00 00 28 10 00 00 00", False),  # 281 only in the payload
        ("  vcan0  0281  [8]  00 00 01 00 00 00 00 00", True),
        ("candump: filter vcan0,281:7FF: no such device", False),
        ("", False),
    ],
)
def test_status_frame_matches_the_id_field_only(text, ok):
    assert uh.has_status_frame(text, 0x281) is ok


def test_expected_digest_comes_from_the_part_deployed_on_the_zone():
    assert uh.expected_image_digest(VEHICLE, "vx-zone-rl-payload") == ZONE_DIGEST
    assert uh.expected_image_digest(VEHICLE, "vx-hpc1-payload") == GW_DIGEST


def test_unknown_container_has_no_expected_digest():
    with pytest.raises(LookupError):
        uh.expected_image_digest(VEHICLE, "vx-zone-xx-payload")


def _inspect(cid, image, status="running"):
    return json.dumps([{"Id": cid, "ImageName": image, "State": {"Status": status, "Running": status == "running"}}])


def test_identity_is_parsed_from_podman_inspect_json():
    ident = uh.parse_identity(_inspect("abc", "r:1@" + ZONE_DIGEST))
    assert ident == {"id": "abc", "image_name": "r:1@" + ZONE_DIGEST, "running": True}
    assert uh.parse_identity("") is None
    assert uh.parse_identity("[]") is None


@pytest.mark.parametrize(
    "ident, problem",
    [
        ({"id": "new", "image_name": "r:11@" + ZONE_DIGEST, "running": True}, None),
        ({"id": "old", "image_name": "r:11@" + ZONE_DIGEST, "running": True}, "stale"),
        ({"id": "new", "image_name": "r:11@sha256:" + "ab" * 32, "running": True}, "digest"),
        ({"id": "new", "image_name": "r:11", "running": True}, "digest"),
        ({"id": "new", "image_name": "r:11@" + ZONE_DIGEST, "running": False}, "running"),
        (None, "missing"),
    ],
)
def test_binding_needs_fresh_running_container_with_the_package_digest(ident, problem):
    got = uh.binding_problem(ident, previous_id="old", digest=ZONE_DIGEST)
    if problem is None:
        assert got is None
    else:
        assert got is not None and problem in got


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def clock(self):
        return self.now

    def sleep(self, s):
        assert s > 0
        self.sleeps.append(s)
        self.now += s


def test_failing_probe_runs_to_the_deadline_with_backoff():
    fc = FakeClock()
    calls = []

    def attempt():
        calls.append(fc.now)
        return False

    ok, attempts, elapsed = uh.wait_until(attempt, 90, clock=fc.clock, sleep=fc.sleep)
    assert ok is False
    assert elapsed >= 90
    assert attempts == len(calls)
    assert fc.sleeps[1] > fc.sleeps[0]  # backoff grows
    assert max(fc.sleeps) <= 5.0
    assert attempts <= 30


def test_probe_that_succeeds_later_stops_waiting():
    fc = FakeClock()
    ok, attempts, elapsed = uh.wait_until(lambda: fc.now >= 3, 90, clock=fc.clock, sleep=fc.sleep)
    assert ok is True and elapsed < 10
