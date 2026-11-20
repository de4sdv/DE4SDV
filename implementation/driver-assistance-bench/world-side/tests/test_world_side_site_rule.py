"""The SC-DRIVING-014 site rule of the SC-014 site decision of 2026-11-20, on the real map read (lane I-W).

A bench choice (rule 44 of the bench's practice), named in the setting and never taken as a fallback: road 10's
outermost driving lane under the named gentle-bend approach reading, with a minimum approach of 90 m.

- The model fixes neither the lane nor the approach: "toward a curve of at most 25 m radius"
  (driver_assistance_needs_requirements.sysml:192-193), guard pipes on the outer side and the stationary vehicle on
  the extension of the lane centre, just outside them (driver_assistance_operational_context.sysml:280-284).
- The regulation's guidance has the vehicle drive "outer lane than the centre of the road" (R152:1744-1756, quoted
  in phase 5's INPUTS-BRIEF.md:281-294) and gives 1.6 s as the TTC when the vehicle begins to turn in.
- 90 m: in attempt 3 the candidate reached 20.9 km/h within 15 m of its first move; 29 km/h needs about 35 m.

Expected values come from the decision and the G4 read (s1-map/FACTS.md), not from the code under test.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

import carla  # the fake
import scenarios
import sites

HERE = Path(__file__).resolve().parent
READ = json.loads((HERE / "data" / "town06_opt_g4_read.json").read_text())
MIN_APPROACH_M = 90.0              # the decision's minimum, pinned as a number
GUIDANCE_TTC_AT_TURN_IN_S = 1.6    # R152:1744-1756
MODEL_RADIUS_M = 25.0              # needs_requirements.sysml:193
KMH30 = 30.0 / 3.6


def real_world():
    client = carla.Client("127.0.0.1", 2000, _server=carla._Server("Carla/Maps/Town10HD_Opt"))
    return client.load_world("Town06_Opt")


def props(world):
    return [b.id for b in world.get_blueprint_library().filter("static.prop.*")]


def resolve_as_the_world_side(world_map, st, props_available, **over):
    """The call the world side makes for a site setting: the setting's own rule, the server's prop list, no
    extents (the world side has none of its own)."""
    kw = dict(props_available=props_available, approach_rule=st.site_approach_rule,
              approach_min_m=st.site_approach_min_m, lane_rule=st.site_lane, rule_reason=st.site_reason)
    kw.update(over)
    return sites.resolve(world_map, st.site, st, **kw)


# ---------------------------------------------------------------------------------- the setting names the rule


def test_the_sc014_setting_names_its_site_rule():
    st = scenarios.setting("SC-DRIVING-014@30")
    assert (st.site, st.site_approach_rule, st.site_approach_min_m, st.site_lane) == \
        ("sc014-curve", "gentle-bend", MIN_APPROACH_M, "outermost")
    assert "outer lane than the centre of the road" in st.site_reason
    assert "2026-11-20" in st.site_reason and "90 m" in st.site_reason
    rec = st.as_record()
    for key in ("site_approach_rule", "site_approach_min_m", "site_lane", "site_reason"):
        assert key in rec and key in rec["proposal"]
    # SC-015's approach is named too (the straight rule), never left to a default
    assert scenarios.setting("SC-DRIVING-015@40").site_approach_rule == "straight"
    for sid in ("SC-DRIVING-012@20", "SC-DRIVING-013@30", "stop"):
        s = scenarios.setting(sid)
        assert (s.site, s.site_approach_rule, s.site_approach_min_m, s.site_lane) == (None, None, None, None)


# ------------------------------------------------------------------------------- the site on the real map read


@pytest.fixture(scope="module")
def spec014():
    world = real_world()
    st = scenarios.setting("SC-DRIVING-014@30")
    return resolve_as_the_world_side(world.get_map(), st, props(world)), sites.Xodr(world.get_map().to_opendrive())


def test_the_rule_gives_road_10_lane_minus_5_with_at_least_90_m_of_approach(spec014):
    spec, _x = spec014
    g = spec.geometry
    assert (g["road"], g["lane"], g["outermostLane"], g["turnSide"]) == ("10", -5, True, "left")
    assert g["approachM"] >= MIN_APPROACH_M
    assert g["approachGentleBendM"] == pytest.approx(97.04, abs=0.05)        # FACTS.md: 97.0 m
    # the hero starts on the approach, on a road, at least the minimum before the curve
    assert MIN_APPROACH_M <= g["startBackM"] <= g["approachM"] + 1e-6
    assert spec.start.split(":")[:2] == ["54", "6"]           # the approach's far end, on road 54 (not a junction)


def test_the_curve_is_within_25_m_at_the_lane_centre_and_at_the_road_edge_and_turns_90_deg(spec014):
    spec, _x = spec014
    g = spec.geometry
    assert g["laneCentreRadiusM"][1] <= MODEL_RADIUS_M
    assert g["roadEdgeRadiusM"] <= MODEL_RADIUS_M and g["roadEdgeWithinModel"] is True
    assert abs(g["turnDeg"]) >= 90.0


def test_the_target_box_is_clear_of_every_road_surface_with_its_clearance_measured(spec014):
    spec, x = spec014
    t = spec.target
    assert t["motion"] == "stationary"
    # independently of the site's own check: the box (the read's model3 extent) against every surface lane
    cx, cy, h = t["x"], -t["y"], -math.radians(t["yaw"])
    hit = {o for px, py in sites._box_samples(cx, cy, h, *sites.TARGET_HALF) for o in x.locate(px, py)}
    assert hit == set()
    c = spec.checks
    assert c["targetOffEveryRoadSurface"] is True and c["targetClearanceFromRoadSurfaceM"] >= 0.5
    assert c["targetNearestSurface"]                                          # the nearest surface is named
    assert c["targetNeverInPath"] is True


def test_no_prop_stands_on_a_driving_lane(spec014):
    spec, x = spec014
    assert spec.props and {p["blueprint"] for p in spec.props} <= set(READ["static_prop"])
    ext = READ["prop_bounding_boxes"]["static.prop.streetbarrier"]["extent"]
    on_driving = []
    for i, p in enumerate(spec.props):
        cx, cy, h = p["x"], -p["y"], -math.radians(p["yaw"])
        for px, py in sites._box_samples(cx, cy, h, max(ext[0], ext[1]), min(ext[0], ext[1])):
            if any(o[2] == "driving" for o in x.locate(px, py)):
                on_driving.append(i)
                break
    assert on_driving == []
    assert spec.checks["pipesOffDrivingLanes"] is True and spec.checks["pipesOnDrivingLanes"] == []
    # the props are spaced by the server's own streetbarrier (the read's extent), not a default length
    assert spec.readings["propExtentsSource"].startswith("the G4 read of 2026-11-20")


def test_the_ttc_at_turn_in_at_30_kmh_is_reported_against_the_1_6_s_guidance(spec014):
    spec, _x = spec014
    reg = spec.guidance["regulation"]
    pred = spec.guidance["predicted"]
    assert reg["ttcAtTurnInMaxS"] == GUIDANCE_TTC_AT_TURN_IN_S
    ttc = pred["ttcAtTurnInS"]["at30Kmh"]
    assert ttc == pytest.approx(pred["gapAtTurnInM"] / KMH30, abs=1e-3)
    assert pred["ttcAtTurnInMetAt30Kmh"] is (ttc <= GUIDANCE_TTC_AT_TURN_IN_S)


def test_the_record_carries_the_reading_the_lane_the_approach_and_the_reason(spec014):
    spec, _x = spec014
    st = scenarios.setting("SC-DRIVING-014@30")
    rec = json.loads(json.dumps(spec.as_record()))
    sel = rec["benchReadings"]["siteSelection"]
    assert sel == {"approachRule": "gentle-bend", "lane": "outermost", "approachMinM": MIN_APPROACH_M,
                   "reason": st.site_reason, "chosen": {"road": "10", "lane": -5,
                                                        "approachM": spec.geometry["approachM"]}}
    assert rec["benchReadings"]["approachMinM"] == MIN_APPROACH_M


# ------------------------------------------------------------------------------------------------ the boundary


def _loop_xodr(approach):
    """One road: a straight approach of ``approach`` m, then a 180 deg left arc of radius 14 m; three 3.5 m driving
    lanes right of the reference line and a 1.0 m shoulder (lane -3 is the outermost driving lane)."""
    k, arc = 1.0 / 14.0, math.pi * 14.0
    lanes = "".join(f'<lane id="-{i}" type="driving"><width sOffset="0" a="3.5" b="0" c="0" d="0"/></lane>'
                    for i in (1, 2, 3)) + \
        '<lane id="-4" type="shoulder"><width sOffset="0" a="1.0" b="0" c="0" d="0"/></lane>'
    return (f'<OpenDRIVE><header name="loop"/><road id="1" length="{approach + arc}" junction="-1"><planView>'
            f'<geometry s="0" x="0" y="0" hdg="0" length="{approach}"><line/></geometry>'
            f'<geometry s="{approach}" x="{approach}" y="0" hdg="0" length="{arc}"><arc curvature="{k}"/></geometry>'
            f'</planView><lanes><laneSection s="0"><center><lane id="0" type="none"/></center><right>{lanes}</right>'
            '</laneSection></lanes></road></OpenDRIVE>')


class _Map:
    def __init__(self, text):
        self.text, self.name = text, "Carla/Maps/Synthetic"

    def to_opendrive(self):
        return self.text


def test_an_89_m_approach_is_refused_with_a_named_reason():
    st = scenarios.setting("SC-DRIVING-014@30")
    with pytest.raises(sites.SiteError) as err:
        resolve_as_the_world_side(_Map(_loop_xodr(89.0)), st, READ["static_prop"])
    text = str(err.value)
    assert "rule 'gentle-bend', lane 'outermost'" in text
    assert "under the minimum approach of 90.0 m" in text
    assert "road 1 lane -3 approach 8" in text                     # the outermost lane, its approach named
    # and 91 m passes the same rule, in the outermost lane
    spec = resolve_as_the_world_side(_Map(_loop_xodr(91.0)), st, READ["static_prop"])
    assert spec.geometry["lane"] == -3 and spec.geometry["approachM"] >= MIN_APPROACH_M


def test_an_unknown_lane_rule_is_refused():
    world = real_world()
    st = scenarios.setting("SC-DRIVING-014@30")
    with pytest.raises(sites.SiteError, match="unknown lane rule 'innermost'"):
        resolve_as_the_world_side(world.get_map(), st, props(world), lane_rule="innermost")
