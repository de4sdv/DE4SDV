"""The scenario sites of S1 (``sites.py``) on the real map read, and the fake's replay of that read (lane A2).

The G4 read of 2026-11-20 (``inc-driving-002/phase10/s1-map/``; CARLA 1.0-14ac3b1a5, Town06_Opt) gave the map's own
OpenDRIVE (``to_opendrive()``, sha256 a90b6131..., the same bytes as the pack's ``Town06_Opt.xodr``), the server's 83
``static.prop.*`` blueprints (no guard pipe among them) and 12,958 waypoints at 2 m. ``data/town06_opt_g4.xodr.xz``,
``data/town06_opt_g4_read.json`` and ``data/town06_opt_g4_waypoints_sites.json`` hold them; the fake replays them.

Model: SC-DRIVING-014 "toward a curve of at most 25 m radius" (driver_assistance_needs_requirements.sysml:192-193),
guard pipes on its outer side and a stationary vehicle "on the extension of the centre of the lane ... never in its
path"; SC-DRIVING-015 a vehicle ahead "that slows down and turns off at a corner, while the vehicle goes straight on"
(driver_assistance_operational_context.sysml:271-323).
"""

from __future__ import annotations

import hashlib
import json
import lzma
import math
from pathlib import Path

import pytest

import carla  # the fake
import sites

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
READ = json.loads((DATA / "town06_opt_g4_read.json").read_text())
XODR_SHA256 = "a90b613175fa837fdc128ddfaf5ddad25797b128fdbd8cd945974bc21a60496e"   # the G4's to_opendrive()


def real_map():
    client = carla.Client("127.0.0.1", 2000, _server=carla._Server("Carla/Maps/Town10HD_Opt"))
    return client, client.load_world("Town06_Opt")


def prop_extents():
    return {k: {"extent": v["extent"]} for k, v in READ["prop_bounding_boxes"].items()}


def props(world):
    return [b.id for b in world.get_blueprint_library().filter("static.prop.*")]


# ------------------------------------------------------------------------------------------- A8: the replay


def test_the_fake_replays_the_real_map_read():
    _client, world = real_map()
    text = world.get_map().to_opendrive()
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == XODR_SHA256 == READ["to_opendrive"]["sha256"]
    assert READ["package_xodr"]["sha256"] == XODR_SHA256          # the pack's own file is the same map
    assert sorted(props(world)) == sorted(READ["static_prop"]) and len(READ["static_prop"]) == 83
    assert READ["api"]["Vehicle.enable_constant_velocity"] is True


def test_the_fake_refuses_a_prop_the_server_does_not_list():
    _client, world = real_map()
    library = world.get_blueprint_library()
    assert library.find("static.prop.streetbarrier").id == "static.prop.streetbarrier"
    with pytest.raises(IndexError):
        library.find("static.prop.guardpipe")                     # no guard pipe on the real server
    assert not [p for p in READ["static_prop"] if "pipe" in p or "guardrail" in p]


def test_a_map_without_a_replay_has_no_opendrive_to_give():
    client = carla.Client("127.0.0.1", 2000, _server=carla._Server("Carla/Maps/Town10HD_Opt"))
    world = client.load_world("Town04_Opt")
    with pytest.raises(RuntimeError):
        world.get_map().to_opendrive()


# ------------------------------------------------------------------------------------- the OpenDRIVE reader


def test_lane_centres_equal_the_real_servers_waypoints():
    x = sites.Xodr(lzma.open(DATA / "town06_opt_g4.xodr.xz", "rt").read())
    rows = json.loads((DATA / "town06_opt_g4_waypoints_sites.json").read_text())["rows"]
    assert len(rows) > 500
    worst = 0.0
    for road, _sec, lane, s, wx, wy, _wz, yaw, *_ in rows:
        r = x.roads[str(road)]
        cx, cy, h = r.lane_center(min(max(s, 1e-6), r.length - 1e-6), lane)
        p = sites.carla_pose(cx, cy, h + (math.pi if lane > 0 else 0.0))
        worst = max(worst, math.hypot(p["x"] - wx, p["y"] - wy))
        assert abs((p["yaw"] - yaw + 180.0) % 360.0 - 180.0) < 0.5, (road, lane, s)
    assert worst < 0.01


# ------------------------------------------------------------------------------------- A4: SC-DRIVING-014


def _loop_xodr(approach=200.0, radius=20.0, turn_deg=180.0):
    """A synthetic one-way road: a straight approach, then a left arc; three 3.5 m driving lanes on the right of the
    reference line and a 1.0 m shoulder outside them; nothing else on the map."""
    k = 1.0 / radius
    arc = math.radians(turn_deg) / k
    lanes = ('<lane id="-1" type="driving"><width sOffset="0" a="3.5" b="0" c="0" d="0"/></lane>'
             '<lane id="-2" type="driving"><width sOffset="0" a="3.5" b="0" c="0" d="0"/></lane>'
             '<lane id="-3" type="driving"><width sOffset="0" a="3.5" b="0" c="0" d="0"/></lane>'
             '<lane id="-4" type="shoulder"><width sOffset="0" a="1.0" b="0" c="0" d="0"/></lane>')
    xe = approach
    return (f'<OpenDRIVE><header name="loop"/><road id="1" length="{approach + arc}" junction="-1"><planView>'
            f'<geometry s="0" x="0" y="0" hdg="0" length="{approach}"><line/></geometry>'
            f'<geometry s="{approach}" x="{xe}" y="0" hdg="0" length="{arc}"><arc curvature="{k}"/></geometry>'
            f'</planView><lanes><laneSection s="0"><center><lane id="0" type="none"/></center><right>{lanes}</right>'
            '</laneSection></lanes></road></OpenDRIVE>')


class _Map:
    def __init__(self, text, name="Carla/Maps/Synthetic"):
        self.text, self.name = text, name

    def to_opendrive(self):
        return self.text


def test_the_curve_site_on_a_synthetic_loop():
    # reference radius 14 m, left turn: the right lanes lie outside the reference line, lane centres at 15.75 (-1),
    # 19.25 (-2) and 22.75 m (-3, the outermost); the shoulder ends at 25.5 m, the road edge
    spec = sites.resolve(_Map(_loop_xodr(radius=14.0)), "sc014-curve", props_available=READ["static_prop"],
                         prop_extents=prop_extents())
    g = spec.geometry
    assert g["road"] == "1" and g["lane"] == -3 and g["turnSide"] == "left" and g["outermostLane"]
    assert g["laneCentreRadiusM"][1] == pytest.approx(22.75, abs=0.05)
    assert g["laneCentreRadiusM"][1] <= sites.CURVE_RADIUS_MAX_M
    assert g["roadEdgeRadiusM"] == pytest.approx(25.5, abs=0.05) and g["roadEdgeWithinModel"] is False
    assert g["turnDeg"] >= sites.CURVE_TURN_MIN_DEG
    assert g["approachM"] >= sites.APPROACH_014_M and g["approachStraightM"] == pytest.approx(200.0, abs=1.0)
    assert spec.start.startswith("1:-3:") and float(spec.start.split(":")[2]) == pytest.approx(50.0, abs=1.0)
    # the target on the tangent extension of the lane centre at the curve entry (x = 200, y_carla = 8.75)
    t = spec.target
    assert t["motion"] == "stationary" and t["yaw"] == pytest.approx(0.0, abs=1e-6)
    assert t["y"] == pytest.approx(8.75, abs=1e-6) and t["x"] > 200.0
    # its body, with the clearance, beyond the road edge: the inner rear corner, from the arc's centre (200, 14)
    hl, hw = sites.TARGET_HALF[0] + sites.TARGET_CLEARANCE_M, sites.TARGET_HALF[1] + sites.TARGET_CLEARANCE_M

    def inner_corner(x):
        return math.hypot(x - hl - 200.0, -t["y"] + hw - 14.0)

    assert inner_corner(t["x"]) >= 25.5 - 1e-6
    assert inner_corner(t["x"] - sites.TARGET_STEP_M) < 25.5          # the nearest such place on the tangent
    assert spec.checks["targetNeverInPath"] and spec.checks["pipesOffDrivingLanes"]
    assert spec.props and {p["blueprint"] for p in spec.props} == {"static.prop.streetbarrier"}
    # the pipes on the shoulder, between 24.5 and 25.5 m from the centre
    for p in spec.props:
        assert 24.5 <= math.hypot(p["x"] - 200.0, -p["y"] - 14.0) <= 25.5 or p["x"] < 200.0


def test_the_straight_rule_refuses_the_real_map_and_names_the_curve():
    _client, world = real_map()
    with pytest.raises(sites.SiteError) as err:
        sites.resolve(world.get_map(), "sc014-curve", props_available=props(world), prop_extents=prop_extents())
    text = str(err.value)
    assert "rule 'straight'" in text
    assert "road 64 lane -5 approach 3.94 m" in text and "road 10 lane -5 approach 17.16 m" in text


def test_the_curve_site_on_the_real_map_under_the_named_gentle_bend_rule():
    _client, world = real_map()
    spec = sites.resolve(world.get_map(), "sc014-curve", props_available=props(world), prop_extents=prop_extents(),
                         approach_rule="gentle-bend")
    g = spec.geometry
    assert spec.xodr_sha256 == XODR_SHA256 and spec.map_name == "Town06_Opt"
    assert (g["road"], g["lane"], g["turnSide"]) == ("10", -4, "left")
    assert g["laneCentreRadiusM"][1] <= sites.CURVE_RADIUS_MAX_M and g["turnDeg"] >= 90.0
    assert g["roadEdgeRadiusM"] <= sites.CURVE_RADIUS_MAX_M and g["roadEdgeWithinModel"] is True
    assert g["approachM"] >= sites.APPROACH_014_M and g["approachStraightM"] < sites.APPROACH_014_M
    assert spec.readings["approachRule"] == "gentle-bend"
    assert spec.start == "55:5:16.887"
    assert g["entryRoadLaneS"] == "10:-4:11.941"                   # the arc begins at s 12.1 (planView)
    # the target on the tangent at the entry: no lateral offset from the entry's line
    e, t = g["entry"], spec.target
    yaw = math.radians(e["yaw"])
    assert abs(-math.sin(yaw) * (t["x"] - e["x"]) + math.cos(yaw) * (t["y"] - e["y"])) < 1e-3
    assert spec.checks["targetNeverInPath"] and spec.checks["targetClearanceFromHeroPathM"] > 0.5
    assert all(p["blueprint"] in READ["static_prop"] for p in spec.props)
    assert spec.checks["pipesOffDrivingLanes"] and spec.checks["pipesOnDrivingLanes"] == []


def test_an_unknown_prop_is_refused():
    _client, world = real_map()
    without = [p for p in props(world) if "barrier" not in p]
    with pytest.raises(sites.SiteError, match="no guard-pipe-like prop"):
        sites.resolve(world.get_map(), "sc014-curve", props_available=without, approach_rule="gentle-bend")
    with pytest.raises(sites.SiteError, match="static.prop"):
        sites.resolve(world.get_map(), "sc014-curve", approach_rule="gentle-bend")


def test_the_setting_record_carries_the_guidance_values():
    _client, world = real_map()
    spec = sites.resolve(world.get_map(), "sc014-curve", props_available=props(world), prop_extents=prop_extents(),
                         approach_rule="gentle-bend")
    record = json.loads(json.dumps({"site": spec.as_record()}))["site"]
    reg = record["guidance"]["regulation"]
    assert (reg["ttcAtTurnInMaxS"], reg["ttcAtOverlapZeroMaxS"], reg["atCurveEntryMinKmh"], reg["inCurveMinKmh"],
            reg["curveRadiusMaxM"]) == (1.6, 1.1, 22.0, 21.0, 25.0)
    pred = record["guidance"]["predicted"]
    assert pred["ttcAtTurnInS"]["at30Kmh"] == pytest.approx(pred["gapAtTurnInM"] / (30 / 3.6), abs=1e-3)
    assert record["siteId"] == "sc014-curve" and record["start"] == spec.start


# ------------------------------------------------------------------------------------- A5: SC-DRIVING-015


def test_the_turnoff_site_on_the_real_map():
    _client, world = real_map()
    spec = sites.resolve(world.get_map(), "sc015-turnoff")
    g = spec.geometry
    assert (g["junction"], g["incomingRoad"], g["incomingLane"]) == ("838", "19", -4)
    assert g["straightConnector"]["road"] == "888" and abs(g["straightConnector"]["turnDeg"]) < 15.0
    assert g["rightConnector"]["road"] == "863" and 60.0 <= -g["rightConnector"]["turnDeg"] <= 120.0
    assert g["approachM"] >= sites.APPROACH_015_M
    # the hero starts on a road, not in a junction, at least 200 m before the junction
    road = spec.start.split(":")[0]
    assert road == "17" and g["startBackM"] >= sites.APPROACH_015_M
    # the hero's lane goes straight on: its path ends heading as it starts
    first, last = spec.ego_path[0], spec.ego_path[-1]
    assert abs((last["yaw"] - first["yaw"] + 180.0) % 360.0 - 180.0) < 5.0


def test_the_target_script_holds_and_turns_at_10_kmh_on_the_right_connector():
    _client, world = real_map()
    spec = sites.resolve(world.get_map(), "sc015-turnoff")
    phases = [p["phase"] for p in spec.target_script]
    assert phases == ["accelerate", "hold", "brake", "turn"]
    acc, hold, brake, turn = spec.target_script
    assert acc["accelMps2"] == 1.5 and acc["durationS"] == pytest.approx(40 / 3.6 / 1.5, abs=1e-3)
    assert hold["durationS"] >= 4.0 and hold["fromMps"] == pytest.approx(40 / 3.6)
    assert turn["fromMps"] == pytest.approx(10 / 3.6) and turn["connector"] == "863"
    motion = spec.target_motion()
    t_turn = acc["durationS"] + hold["durationS"] + brake["durationS"]
    xodr = sites.Xodr(world.get_map().to_opendrive())
    connector = [sites.carla_pose(p[0], p[1], p[2]) for p in xodr.sample_piece(("863", 0, -1), 0.25)]
    on = motion.at(t_turn + 2.0)
    assert on["phase"] == "turn" and on["speedMps"] == pytest.approx(10 / 3.6, abs=1e-9)
    assert min(math.hypot(on["x"] - c["x"], on["y"] - c["y"]) for c in connector) < 0.2
    before = motion.at(acc["durationS"] + 1.0)
    assert before["phase"] == "hold" and before["speedMps"] == pytest.approx(40 / 3.6)
    start = motion.at(0.0)
    hero = spec.start_pose
    assert math.hypot(start["x"] - hero["x"], start["y"] - hero["y"]) == pytest.approx(30.0, abs=0.5)


def test_a_target_script_without_4_s_at_40_kmh_is_refused(monkeypatch):
    _client, world = real_map()
    xodr = sites.Xodr(world.get_map().to_opendrive())
    monkeypatch.setitem(sites.TARGET_015, "aheadM", 130.0)       # the hero starts 225 m back: 24.9 m of hold
    with pytest.raises(sites.SiteError, match="hold at 40 km/h lasts 2.24 s, under 4.0 s"):
        sites.build_turnoff_site(xodr, "Town06_Opt")


def test_in_the_fake_the_target_moved_by_its_script_is_on_the_connector_at_10_kmh():
    client, world = real_map()
    spec = sites.resolve(world.get_map(), "sc015-turnoff")
    settings = world.get_settings()
    settings.synchronous_mode, settings.fixed_delta_seconds = True, 0.05
    world.apply_settings(settings)
    bp = world.get_blueprint_library().find("vehicle.tesla.model3")
    t0 = spec.target
    actor = world.spawn_actor(bp, carla.Transform(carla.Location(t0["x"], t0["y"], t0["z"] + 0.3),
                                                  carla.Rotation(yaw=t0["yaw"])))
    actor.set_simulate_physics(False)
    motion = spec.target_motion()
    seen = []
    for k in range(1, int(30.0 / 0.05)):
        m = motion.at(k * 0.05)
        actor.set_transform(carla.Transform(carla.Location(m["x"], m["y"], m["z"] + 0.3), carla.Rotation(yaw=m["yaw"])))
        world.tick()
        loc = actor.get_location()
        seen.append((m["phase"], m["speedMps"], loc.x, loc.y))
    turning = [s for s in seen if s[0] == "turn"]
    assert turning and all(abs(s[1] - 10 / 3.6) < 1e-9 for s in turning)
    steps = [math.hypot(b[2] - a[2], b[3] - a[3]) / 0.05 for a, b in zip(turning, turning[1:])]
    assert max(abs(v - 10 / 3.6) for v in steps) < 0.05


def test_resolve_refuses_an_unknown_site_and_a_setting_naming_another():
    _client, world = real_map()
    with pytest.raises(sites.SiteError, match="unknown site"):
        sites.resolve(world.get_map(), "sc099-nowhere")

    class Setting:
        setting_id, site = "SC-DRIVING-015@40", "sc015-turnoff"

    with pytest.raises(sites.SiteError, match="names site"):
        sites.resolve(world.get_map(), "sc014-curve", Setting(), props_available=props(world))
    assert sites.resolve(world.get_map(), "sc015-turnoff", Setting()).site_id == "sc015-turnoff"
