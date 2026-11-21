"""A site's start against the server's own waypoint (J5 of the closure check of 44a4be29).

The world side builds a site setting at ``SiteSpec.start`` (road:lane:s) and its ``start_pose``. It asks the server for
its own waypoint there (``get_waypoint_xodr``) and refuses the site, as a bench error that names the reason, when the
server has none or when that waypoint lies more than 0.5 m from the site's start pose. Why: on the real server
(F3 of lane I-W, G4, 2026-11-20, boot 1) the start ``54:6:62.56``, road 54's own length, had no waypoint, and the hero's
pose projected onto a junction's connector; the world side recorded ``serverWaypointDistanceM: null`` and spawned.

The fake answers ``get_waypoint_xodr`` on the site roads from the real server's own waypoints
(``tests/data/town06_opt_g4_waypoints_sites.json``), so these tests read the server's geometry, not the site code's.
"""

from __future__ import annotations

import dataclasses
import json
import math

import pytest

import carla  # the fake
from world_side_testkit import run_main

import da_world_side as ws_mod
import scenarios
import sites

# The 0.5 m rule of J5: the server's waypoint at a site's start lies at most this far from the site's start pose
SITE_START_WAYPOINT_MAX_M = 0.5

# F3 of lane I-W on the real server (G4, 2026-11-20, boot 2, bench head e2293929; I-W/f3/FACTS.md and each run's
# fetched simulator/setting_record.json): the committed sites' starts, their poses, and the distance from the server's
# own get_waypoint_xodr waypoint to that pose
F3_STARTS = {
    "SC-DRIVING-014@30": ("54:6:62.063", 9.7023, -35.3262, 0.0005),
    "SC-DRIVING-015@40": ("17:-4:54.312", -245.9089, 243.6923, 0.0003),
}
# F3 boot 1 (bench head 841ce5c8): the start at road 54's own length, where the real server had no waypoint
F3_BOOT1_START = ("54:6:62.56", 9.699, -34.8297)


def _expected(server, setting_id):
    st = scenarios.setting(setting_id)
    world = carla.Client("127.0.0.1", 2000, _server=server, name="test").get_world()
    lib = [b.id for b in world.get_blueprint_library().filter("static.prop.*")]
    return sites.resolve(world.get_map(), st.site, st, props_available=lib, approach_rule=st.site_approach_rule,
                         approach_min_m=st.site_approach_min_m, lane_rule=st.site_lane, rule_reason=st.site_reason)


def _run(tmp_path, factory, clock, setting):
    run_dir = tmp_path / "run"
    rc, lines = run_main(["run", "--run-dir", str(run_dir), "--setting", setting, "--run-s", "1"], factory, clock)
    return rc, lines, run_dir / "simulator"


def _heroes(server):
    return [s for s in server.actors.values() if s.alive and s.type_id.startswith("vehicle.")
            and s.attributes.get("role_name") == "hero"]


def _move_start(monkeypatch, start: str, x: float, y: float) -> list:
    """The world side's sites.resolve, with the site's start and its pose replaced (yaw and z kept)."""
    calls: list = []
    real = sites.resolve

    def resolve(world_map, site_id, setting=None, **kw):
        spec = real(world_map, site_id, setting, **kw)
        calls.append(spec.start)
        return dataclasses.replace(spec, start=start, start_pose={**spec.start_pose, "x": x, "y": y})
    monkeypatch.setattr(ws_mod.sites, "resolve", resolve)
    return calls


def _beside(server, start: str, metres: float) -> tuple[float, float]:
    """A point ``metres`` to the side of the server's waypoint at ``start`` (across its heading)."""
    road, lane, s = start.split(":")
    wp = server.map.get_waypoint_xodr(int(road), int(lane), float(s))
    assert wp is not None, f"precondition: the fake gives the server's waypoint at {start}"
    loc, yaw = wp.transform.location, math.radians(wp.transform.rotation.yaw)
    return loc.x - math.sin(yaw) * metres, loc.y + math.cos(yaw) * metres


# ------------------------------------------------------------------------------------- the fake against F3


def test_the_fake_answers_the_real_site_starts_from_the_servers_own_waypoints(server):
    m = server.map
    for sid, (start, x, y, _dist) in F3_STARTS.items():
        road, lane, s = start.split(":")
        wp = m.get_waypoint_xodr(int(road), int(lane), float(s))
        assert wp is not None, f"{sid}: the fake gives no waypoint at {start}, where the real server gave one (F3)"
        assert (wp.road_id, wp.lane_id) == (int(road), int(lane))
        assert math.hypot(wp.transform.location.x - x, wp.transform.location.y - y) <= 0.01, sid
    # and none at road 54's own length, as on the real server (F3 boot 1), nor on a lane the road does not hold
    assert m.get_waypoint_xodr(54, 6, 62.56) is None
    assert m.get_waypoint_xodr(54, 9, 10.0) is None


def test_every_committed_site_start_is_the_one_f3_measured_and_meets_the_rule(server):
    # the committed settings resolve to the starts F3 measured on the real server, and each measured distance meets
    # the 0.5 m rule; a start that did not would be reported, not the rule loosened
    for sid, (start, x, y, dist) in F3_STARTS.items():
        spec = _expected(server, sid)
        assert spec.start == start, sid
        assert (spec.start_pose["x"], spec.start_pose["y"]) == pytest.approx((x, y), abs=1e-4), sid
        assert dist <= SITE_START_WAYPOINT_MAX_M, sid


@pytest.mark.parametrize("setting", sorted(F3_STARTS))
def test_a_committed_site_run_records_the_servers_waypoint_distance(tmp_path, server, factory, clock, setting):
    rc, lines, sim = _run(tmp_path, factory, clock, setting)
    assert rc == 0, lines
    start = json.loads((sim / "setting_record.json").read_text())["start"]
    assert start["start"] == F3_STARTS[setting][0]
    assert start["serverWaypointDistanceM"] is not None and start["serverWaypointDistanceM"] <= 0.01


# ------------------------------------------------------------------------------------- the world side's rule


def test_a_site_start_with_no_server_waypoint_is_refused_by_name(tmp_path, server, factory, clock, monkeypatch):
    start, x, y = F3_BOOT1_START
    assert server.map.get_waypoint_xodr(54, 6, 62.56) is None, "precondition: no waypoint at road 54's own length"
    calls = _move_start(monkeypatch, start, x, y)
    rc, _lines, sim = _run(tmp_path, factory, clock, "SC-DRIVING-014@30")
    assert calls, "precondition: the world side resolved the site"
    assert rc == 2
    reason = json.loads((sim / "error.json").read_text())["reason"]
    assert reason.startswith("site sc014-curve: ") and "no waypoint" in reason and start in reason
    assert _heroes(server) == []


def test_a_site_start_whose_server_waypoint_lies_more_than_half_a_metre_off_is_refused(tmp_path, server, factory,
                                                                                       clock, monkeypatch):
    start = F3_STARTS["SC-DRIVING-014@30"][0]
    x, y = _beside(server, start, 0.51)
    calls = _move_start(monkeypatch, start, x, y)
    rc, _lines, sim = _run(tmp_path, factory, clock, "SC-DRIVING-014@30")
    assert calls, "precondition: the world side resolved the site"
    assert rc == 2
    reason = json.loads((sim / "error.json").read_text())["reason"]
    assert reason.startswith("site sc014-curve: ") and start in reason and "0.51" in reason and "0.5 m" in reason
    assert _heroes(server) == []


def test_a_site_start_within_half_a_metre_of_the_servers_waypoint_is_built(tmp_path, server, factory, clock,
                                                                         monkeypatch):
    start = F3_STARTS["SC-DRIVING-014@30"][0]
    x, y = _beside(server, start, 0.49)
    _move_start(monkeypatch, start, x, y)
    rc, lines, sim = _run(tmp_path, factory, clock, "SC-DRIVING-014@30")
    assert rc == 0, lines
    rec = json.loads((sim / "setting_record.json").read_text())
    assert rec["start"]["serverWaypointDistanceM"] == pytest.approx(0.49, abs=1e-3)
