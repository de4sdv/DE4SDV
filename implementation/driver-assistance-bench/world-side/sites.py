"""Scenario sites of S1 on the real map: SC-DRIVING-014 (a tight curve) and SC-DRIVING-015 (a turn-off junction).

Pure Python, no simulator: the sites are found in the map's own OpenDRIVE text (``carla.Map.to_opendrive()``), so the
same code runs on the simulator host and on any archived ``.xodr``. ``resolve(world_map, site_id, setting)`` gives a
``SiteSpec``: the hero's start (``road:lane:s``, as ``da_world_side.py --start`` takes it), the target's spawn and its
path and speed script, the props, the geometry read off the map, the checks that refuse a bad site, and the guidance
values of the regulation to write into ``setting_record.json``.

Model sources (``textual-notation-of-model/packages/features/driving/``):

- ``driver_assistance_needs_requirements.sysml:192-194``: SC-DRIVING-014 at 30 km/h (28 to 30 km/h) "toward a curve
  of at most 25 m radius"; SC-DRIVING-015 at 40 km/h (38 to 40 km/h) "behind the vehicle ahead at the same speed";
- ``driver_assistance_operational_context.sysml:271-323``: 014 "a tight curve with guard pipes on its outer side, and
  a stationary vehicle ... just outside the guard pipes, on the extension of the centre of the lane: ahead of the
  vehicle before the curve turns it away, never in its path"; 015 "a vehicle ahead in its lane that slows down and
  turns off at a corner, while the vehicle goes straight on".

The regulation's guidance (UN R152 annex, phase 5 INPUTS-BRIEF.md:270-294) is recorded, not judged: neither setting
has a judged-run term (needs_requirements.sysml:196-211). Everything else is a BENCH READING or a PROPOSAL of this
bench and is marked so; the record names each one.

Frames: OpenDRIVE is right-handed (x east, y north, heading counter-clockwise). CARLA's frame is left-handed:
x_carla = x, y_carla = -y, yaw_carla = -heading in degrees. Every pose a ``SiteSpec`` holds is in CARLA's frame.
"""

from __future__ import annotations

import hashlib
import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

SITE_IDS = ("sc014-curve", "sc015-turnoff")
KMH = 1.0 / 3.6

# ---------------------------------------------------------------- model and regulation values
CURVE_RADIUS_MAX_M = 25.0          # needs_requirements.sysml:193 "a curve of at most 25 m radius"
# R152 guidance of SC-014 (INPUTS-BRIEF.md:281-294): recorded per run, not judged
GUIDANCE_014 = {"source": "UN R152 annex, guidance of the curved road with guard pipes (R152:1744-1756)",
                "approachKmh": [28.0, 30.0], "atCurveEntryMinKmh": 22.0, "ttcAtTurnInMaxS": 1.6,
                "inCurveMinKmh": 21.0, "ttcAtOverlapZeroMaxS": 1.1,
                "curveRadiusMaxM": 25.0, "radiusMeasuredAt": "the outer side of the road"}
# R152 guidance of SC-015 (INPUTS-BRIEF.md:270-279)
GUIDANCE_015 = {"source": "UN R152 annex, guidance of the forward vehicle turning off (R152:1705-1716)",
                "bothKmh": [38.0, 40.0], "targetTurnKmh": [8.0, 10.0], "egoAtTurnBeginMinKmh": 26.0,
                "ttcAtTurnBeginMaxS": 4.7, "egoAfterMinKmh": 20.0, "ttcAtOverlapZeroMaxS": 2.5}

# ---------------------------------------------------------------- bench readings and proposals
CURVE_TURN_MIN_DEG = 90.0          # BENCH READING (S1 plan A4): the tight stretch turns at least 90 deg
APPROACH_014_M = 120.0             # BENCH READING (S1 plan A4): straight approach before the curve
APPROACH_015_M = 200.0             # BENCH READING (S1 plan A5): straight approach before the junction
APPROACH_YAW_MAX_DEG = 2.0         # BENCH READING: "straight" approach, heading within this of the entry's
APPROACH_LATERAL_MAX_M = 0.5       # BENCH READING: and each point within this of the entry's tangent line
# The second approach rule, chosen only by name (resolve(..., approach_rule="gentle-bend")), never as a fallback: the
# real Town06_Opt (G4 read of 2026-11-20) has no tight curve with 120 m of approach under the straight rule
BEND_YAW_MAX_DEG = 20.0            # BENCH READING: heading within this of the entry's
# BENCH READING: no lane-centre radius at or under the model's 25 m on the approach (it holds no second tight curve)
BEND_RADIUS_MIN_M = CURVE_RADIUS_MAX_M
APPROACH_RULES = ("straight", "gentle-bend")
# Lane rules of the curve site, chosen only by name (resolve(..., lane_rule="outermost")), never as a fallback:
# "outermost" keeps the candidates in the outermost driving lane of their direction (the SC-014 site decision of
# 2026-11-20, a bench choice; scenarios.SITE_RULE_014 names it with its reason)
LANE_RULES = ("outermost",)
STRAIGHT_KAPPA_MAX = 1.0 / 500.0   # BENCH READING: a curve starts where the lane-centre radius drops below 500 m
SAMPLE_M = 0.5                     # sampling of lane centres
STRAIGHT_TURN_MAX_DEG = 15.0       # BENCH READING: a junction connector turning less than this goes straight
RIGHT_TURN_DEG = (60.0, 120.0)     # BENCH READING: a connector turning right by this much is a right turn
PROP_PATTERNS = ("guardrail", "guardpipe", "streetbarrier", "chainbarrier")   # PROPOSAL: in this order
PROP_LEAD_M = 10.0                 # PROPOSAL (S1 plan): pipes from 10 m before the curve to its end
PROP_GAP_M = 0.2                   # PROPOSAL: gap between neighbouring props
PROP_DEFAULT_LENGTH_M = 2.0        # used only when the read gives no bounding box for the prop
TARGET_CLEARANCE_M = 0.5           # PROPOSAL: the stationary target's body this far outside road and pipes
TARGET_STEP_M = 0.25
SURFACE_TYPES = ("driving", "shoulder", "border", "parking", "biking", "stop", "restricted", "median", "curb",
                 "entry", "exit", "onRamp", "offRamp", "connectingRamp", "bidirectional")
# SC-015's target script (S1 plan A5): 1.5 m/s2 to 40 km/h, holds at least 4 s, brakes to 10 km/h, then turns
TARGET_015 = {"aheadM": 30.0, "accelMps2": 1.5, "holdKmh": 40.0, "holdMinS": 4.0, "brakeMps2": 2.0,
              "turnKmh": 10.0, "afterTurnM": 40.0}
# The props' extents on the real server (the G4 read of 2026-11-20, data/town06_opt_g4_read.json
# prop_bounding_boxes): the pipes' spacing where the caller gives no extents of its own (the world side)
PROP_EXTENTS_G4 = {"static.prop.streetbarrier": {"extent": [0.5980620980262756, 0.21414536237716675, 0.534582257270813]},
                   "static.prop.chainbarrier": {"extent": [0.7474053502082825, 0.4056827127933502, 0.3460488021373749]}}
EGO_HALF = (2.446, 0.918)          # vehicle.lincoln.mkz bounding box, the G4 read of 2026-11-20 (mapread.json)
TARGET_HALF = (2.347, 1.044)       # vehicle.tesla.model3, the same read


class SiteError(Exception):
    """A site that cannot be built, or one that fails its own checks; the world side stops on it."""


# ====================================================================== OpenDRIVE


def _f(e, k, d=0.0):
    v = e.get(k)
    return d if v is None else float(v)


def _poly(rec, ds):
    a, b, c, d = rec
    return a + ds * (b + ds * (c + ds * d))


class _Geometry:
    def __init__(self, g):
        self.s, self.x, self.y, self.hdg, self.length = (_f(g, k) for k in ("s", "x", "y", "hdg", "length"))
        kind = g[0]
        self.kind = kind.tag
        self.k0 = self.k1 = 0.0
        if self.kind == "arc":
            self.k0 = self.k1 = _f(kind, "curvature")
        elif self.kind == "spiral":
            self.k0, self.k1 = _f(kind, "curvStart"), _f(kind, "curvEnd")
        elif self.kind == "paramPoly3":
            self.pp = [_f(kind, k) for k in ("aU", "bU", "cU", "dU", "aV", "bV", "cV", "dV")]
            self.p_range = kind.get("pRange", "normalized")
        elif self.kind == "poly3":
            self.pp = [0.0, 1.0, 0.0, 0.0] + [_f(kind, k) for k in ("a", "b", "c", "d")]
            self.p_range = "u"
        self._table = None

    def pose(self, ds):
        ds = min(max(ds, 0.0), self.length)
        h0 = self.hdg
        if self.kind == "line":
            return self.x + ds * math.cos(h0), self.y + ds * math.sin(h0), h0
        if self.kind == "arc" and self.k0 != 0.0:
            k = self.k0
            return (self.x + (math.sin(h0 + k * ds) - math.sin(h0)) / k,
                    self.y + (math.cos(h0) - math.cos(h0 + k * ds)) / k, h0 + k * ds)
        if self.kind in ("arc", "spiral"):
            # heading h0 + k0 s + (k1 - k0) s^2 / (2 L); Simpson's rule on cos and sin
            n = max(2, int(math.ceil(ds / 0.25)) * 2)
            dk = (self.k1 - self.k0) / self.length if self.length else 0.0
            hd = lambda u: h0 + self.k0 * u + 0.5 * dk * u * u  # noqa: E731
            h = ds / n
            sx = sy = 0.0
            for i in range(n + 1):
                w = 1 if i in (0, n) else (4 if i % 2 else 2)
                sx += w * math.cos(hd(i * h))
                sy += w * math.sin(hd(i * h))
            return self.x + sx * h / 3.0, self.y + sy * h / 3.0, hd(ds)
        return self._poly_pose(ds)

    def _poly_pose(self, ds):
        if self._table is None:          # arc length table over the parameter
            n = 400
            top = 1.0 if self.p_range == "normalized" else self.length
            pts = [self._uv(top * i / n) for i in range(n + 1)]
            acc = [0.0]
            for i in range(1, n + 1):
                acc.append(acc[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]))
            self._table = (top, n, acc)
        top, n, acc = self._table
        i = 1
        while i < n and acc[i] < ds:
            i += 1
        f = 0.0 if acc[i] == acc[i - 1] else (ds - acc[i - 1]) / (acc[i] - acc[i - 1])
        p = top * (i - 1 + min(max(f, 0.0), 1.0)) / n
        u, v = self._uv(p)
        du, dv = self._duv(p)
        c, s = math.cos(self.hdg), math.sin(self.hdg)
        return self.x + u * c - v * s, self.y + u * s + v * c, self.hdg + math.atan2(dv, du)

    def _uv(self, p):
        a = self.pp
        return _poly(a[0:4], p), _poly(a[4:8], p)

    def _duv(self, p):
        a = self.pp
        return a[1] + 2 * a[2] * p + 3 * a[3] * p * p, a[5] + 2 * a[6] * p + 3 * a[7] * p * p


class _Lane:
    def __init__(self, ln):
        self.id = int(ln.get("id"))
        self.type = ln.get("type") or "none"
        self.widths = sorted(((_f(w, "sOffset"), (_f(w, "a"), _f(w, "b"), _f(w, "c"), _f(w, "d")))
                              for w in ln.findall("width")), key=lambda x: x[0])
        link = ln.find("link")
        p = None if link is None else link.find("predecessor")
        q = None if link is None else link.find("successor")
        self.pred = None if p is None else int(p.get("id"))
        self.succ = None if q is None else int(q.get("id"))

    def width(self, ds):
        w = 0.0
        for off, rec in self.widths:
            if off <= ds + 1e-9:
                w = _poly(rec, ds - off)
        return max(w, 0.0)


class _Section:
    def __init__(self, sec, s_end):
        self.s = _f(sec, "s")
        self.s_end = s_end
        self.lanes = {}
        for side in ("left", "right"):
            for ln in sec.findall(f"{side}/lane"):
                lane = _Lane(ln)
                self.lanes[lane.id] = lane


class Road:
    def __init__(self, r):
        self.id = r.get("id")
        self.length = _f(r, "length")
        self.junction = r.get("junction", "-1")
        self.geoms = [_Geometry(g) for g in r.findall("planView/geometry")]
        self.elev = sorted((_f(e, "s"), (_f(e, "a"), _f(e, "b"), _f(e, "c"), _f(e, "d")))
                           for e in r.findall("elevationProfile/elevation"))
        self.offsets = sorted((_f(e, "s"), (_f(e, "a"), _f(e, "b"), _f(e, "c"), _f(e, "d")))
                              for e in r.findall("lanes/laneOffset"))
        secs = r.findall("lanes/laneSection")
        starts = [_f(s, "s") for s in secs]
        self.sections = [_Section(s, starts[i + 1] if i + 1 < len(secs) else self.length)
                         for i, s in enumerate(secs)]
        self.link = {}
        for kind in ("predecessor", "successor"):
            e = r.find(f"link/{kind}")
            if e is not None:
                self.link[kind] = (e.get("elementType"), e.get("elementId"), e.get("contactPoint"))
        self._bbox = None

    # ---- reference line, lanes
    def ref(self, s):
        s = min(max(s, 0.0), self.length)
        g = self.geoms[0]
        for cand in self.geoms:
            if cand.s <= s + 1e-9:
                g = cand
        return g.pose(s - g.s)

    def z(self, s):
        out = 0.0
        for s0, rec in self.elev:
            if s0 <= s + 1e-9:
                out = _poly(rec, s - s0)
        return out

    def lane_offset(self, s):
        out = 0.0
        for s0, rec in self.offsets:
            if s0 <= s + 1e-9:
                out = _poly(rec, s - s0)
        return out

    def section_index(self, s):
        idx = 0
        for i, sec in enumerate(self.sections):
            if sec.s <= s + 1e-9:
                idx = i
        return idx

    def borders(self, s, idx=None):
        """{lane id: (inner t, outer t)} at s; t positive to the left of the reference line."""
        idx = self.section_index(s) if idx is None else idx
        sec = self.sections[idx]
        ds = s - sec.s
        base = self.lane_offset(s)
        out = {}
        for sign in (1, -1):
            t = base
            k = 1
            while sign * k in sec.lanes:
                w = sec.lanes[sign * k].width(ds)
                out[sign * k] = (t, t + sign * w)
                t += sign * w
                k += 1
        return out

    def point(self, s, t):
        x, y, h = self.ref(s)
        return x - t * math.sin(h), y + t * math.cos(h), h

    def lane_center(self, s, lane_id, idx=None):
        inner, outer = self.borders(s, idx)[lane_id]
        return self.point(s, 0.5 * (inner + outer))

    def bbox(self):
        if self._bbox is None:
            xs, ys = [], []
            n = max(2, int(self.length / 2.0) + 1)
            for i in range(n + 1):
                s = self.length * i / n
                for t in (-40.0, 40.0):
                    x, y, _ = self.point(s, t)
                    xs.append(x)
                    ys.append(y)
            self._bbox = (min(xs), min(ys), max(xs), max(ys))
        return self._bbox


class Xodr:
    """The parts of an OpenDRIVE map the sites need: roads, lanes, links and junction connections."""

    def __init__(self, text: str):
        self.text = text
        self.sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
        root = ET.fromstring(text)
        self.header = dict(root.find("header").attrib) if root.find("header") is not None else {}
        self.roads = {r.get("id"): Road(r) for r in root.findall("road")}
        self.junctions = {}
        for j in root.findall("junction"):
            conns = []
            for c in j.findall("connection"):
                conns.append({"incoming": c.get("incomingRoad"), "connecting": c.get("connectingRoad"),
                              "contact": c.get("contactPoint"),
                              "lanes": [(int(l.get("from")), int(l.get("to"))) for l in c.findall("laneLink")]})
            self.junctions[j.get("id")] = conns

    # ---- lane pieces: (road id, section index, lane id); right lanes (id < 0) travel +s, left lanes -s
    def piece_range(self, piece):
        road = self.roads[piece[0]]
        sec = road.sections[piece[1]]
        return sec.s, sec.s_end

    def piece_lane(self, piece):
        return self.roads[piece[0]].sections[piece[1]].lanes.get(piece[2])

    def _enter(self, road_id, contact, lane_id):
        road = self.roads.get(road_id)
        if road is None or lane_id is None:
            return None
        idx = 0 if contact == "start" else len(road.sections) - 1
        if lane_id not in road.sections[idx].lanes:
            return None
        return (road_id, idx, lane_id)

    def next_pieces(self, piece, forward=True):
        """The lane pieces that follow ``piece`` in its direction of travel (``forward``) or precede it."""
        road_id, idx, lane_id = piece
        road = self.roads[road_id]
        lane = road.sections[idx].lanes[lane_id]
        plus = (lane_id < 0) == forward          # moving toward +s
        link_id = lane.succ if plus else lane.pred
        nidx = idx + (1 if plus else -1)
        if 0 <= nidx < len(road.sections):
            nid = link_id if link_id is not None else lane_id
            return [(road_id, nidx, nid)] if nid in road.sections[nidx].lanes else []
        end = road.link.get("successor" if plus else "predecessor")
        if end is None:
            return []
        etype, eid, contact = end
        if etype == "road":
            p = self._enter(eid, contact, link_id)
            return [p] if p else []
        out = []
        my_contact = "end" if plus else "start"
        for c in self.junctions.get(eid, []):
            if c["incoming"] == road_id:
                for frm, to in c["lanes"]:
                    if frm == lane_id:
                        p = self._enter(c["connecting"], c["contact"], to)
                        if p and self._travels_away(p, c["contact"], forward):
                            out.append(p)
            cr = self.roads.get(c["connecting"])
            if cr is None:
                continue
            for kind in ("successor", "predecessor"):
                lk = cr.link.get(kind)
                if lk and lk[0] == "road" and lk[1] == road_id and lk[2] == my_contact:
                    cidx = len(cr.sections) - 1 if kind == "successor" else 0
                    for cl in cr.sections[cidx].lanes.values():
                        target = cl.succ if kind == "successor" else cl.pred
                        if target == lane_id:
                            p = (cr.id, cidx, cl.id)
                            if p not in out and self._travels_toward(p, kind, forward):
                                out.append(p)
        return out

    def _travels_away(self, piece, contact, forward):
        plus = piece[2] < 0
        away = plus if contact == "start" else not plus      # moving away from the contact point
        return away == forward

    def _travels_toward(self, piece, kind, forward):
        plus = piece[2] < 0
        toward = plus if kind == "successor" else not plus   # moving toward the linked end
        return toward == (not forward)

    def sample_piece(self, piece, step=SAMPLE_M):
        """Lane-centre points of a piece in its direction of travel: (x, y, heading, z, s) in OpenDRIVE's frame."""
        road = self.roads[piece[0]]
        s0, s1 = self.piece_range(piece)
        n = max(1, int(math.ceil((s1 - s0) / step)))
        ss = [s0 + (s1 - s0) * i / n for i in range(n + 1)]
        if piece[2] > 0:
            ss.reverse()
        out = []
        for s in ss:
            x, y, h = road.lane_center(min(max(s, s0 + 1e-6), s1 - 1e-6), piece[2], piece[1])
            if piece[2] > 0:
                h += math.pi
            out.append((x, y, h, road.z(s), s, piece))
        return out

    def locate(self, x, y, types=SURFACE_TYPES):
        """The lanes (road, lane id, type) whose surface holds the point (x, y) in OpenDRIVE's frame."""
        hits = []
        for road in self.roads.values():
            bx0, by0, bx1, by1 = road.bbox()
            if not (bx0 - 1 <= x <= bx1 + 1 and by0 - 1 <= y <= by1 + 1):
                continue
            best = None
            n = max(2, int(road.length / 0.5))
            for i in range(n + 1):
                s = road.length * i / n
                rx, ry, h = road.ref(s)
                d = (x - rx) ** 2 + (y - ry) ** 2
                if best is None or d < best[0]:
                    best = (d, s)
            s = best[1]
            rx, ry, h = road.ref(s)
            along = (x - rx) * math.cos(h) + (y - ry) * math.sin(h)
            if abs(along) > 0.6 and 0.0 < s < road.length:
                continue
            if (s <= 0.0 and along < -0.05) or (s >= road.length and along > 0.05):
                continue
            t = -(x - rx) * math.sin(h) + (y - ry) * math.cos(h)
            for lid, (a, b) in road.borders(s).items():
                lane = road.sections[road.section_index(s)].lanes[lid]
                if lane.type in types and min(a, b) - 1e-6 <= t <= max(a, b) + 1e-6 and abs(a - b) > 0.05:
                    hits.append((road.id, lid, lane.type))
        return hits


# ====================================================================== helpers


def carla_pose(x, y, h, z=0.0):
    """OpenDRIVE (x, y, heading rad) -> CARLA dict (x, y = -y, yaw deg = -heading)."""
    yaw = -math.degrees(h)
    yaw = (yaw + 180.0) % 360.0 - 180.0
    return {"x": round(x, 4), "y": round(-y, 4), "z": round(z, 4), "yaw": round(yaw, 4)}


def _wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def _heading_change(points):
    total = 0.0
    for i in range(1, len(points)):
        total += _wrap(points[i][2] - points[i - 1][2])
    return total


def _circle(p, q, r):
    """Signed curvature and centre of the circle through three points (OpenDRIVE frame)."""
    ax, ay = p[0], p[1]
    bx, by = q[0], q[1]
    cx, cy = r[0], r[1]
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-12:
        return 0.0, None
    ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d
    rad = math.hypot(ax - ux, ay - uy)
    cross = (bx - ax) * (cy - by) - (by - ay) * (cx - bx)
    return (1.0 / rad) * (1 if cross > 0 else -1), (ux, uy)


def _box(cx, cy, h, half_l, half_w):
    c, s = math.cos(h), math.sin(h)
    return [(cx + a * half_l * c - b * half_w * s, cy + a * half_l * s + b * half_w * c)
            for a, b in ((1, 1), (1, -1), (-1, -1), (-1, 1))]


def _box_samples(cx, cy, h, half_l, half_w, step=0.25):
    out = []
    nl = max(1, int(2 * half_l / step))
    nw = max(1, int(2 * half_w / step))
    c, s = math.cos(h), math.sin(h)
    for i in range(nl + 1):
        for j in range(nw + 1):
            if 0 < i < nl and 0 < j < nw:
                continue
            a = -half_l + 2 * half_l * i / nl
            b = -half_w + 2 * half_w * j / nw
            out.append((cx + a * c - b * s, cy + a * s + b * c))
    return out


def _boxes_overlap(a, b):
    """Separating-axis test of two convex quadrilaterals."""
    for poly in (a, b):
        for i in range(4):
            p, q = poly[i], poly[(i + 1) % 4]
            nx, ny = q[1] - p[1], p[0] - q[0]
            pa = [nx * x + ny * y for x, y in a]
            pb = [nx * x + ny * y for x, y in b]
            if max(pa) < min(pb) or max(pb) < min(pa):
                return False
    return True


def _walk(xodr, piece, length, forward, choose):
    """Lane-centre points from the start (forward) or the end (backward) of ``piece`` over about ``length`` m,
    following the lane chain; ``choose`` picks among several next pieces. Points are in travel order; each carries
    its piece. Backward walks return points ending at the start of ``piece``."""
    pts, pieces, cur, got = [], [], piece, 0.0
    while cur is not None and got < length:
        sp = xodr.sample_piece(cur)
        seg = sp if forward else list(reversed(sp))
        start = 1 if pts else 0
        for p in seg[start:]:
            if pts:
                got += math.hypot(p[0] - pts[-1][0], p[1] - pts[-1][1])
            pts.append(p)
            if got >= length:
                break
        pieces.append(cur)
        nxt = xodr.next_pieces(cur, forward)
        nxt = [n for n in nxt if n not in pieces]
        cur = choose(nxt) if nxt else None
    if not forward:
        pts.reverse()
    return pts


def _straightest(xodr):
    def choose(cands):
        best = None
        for c in cands:
            turn = abs(_heading_change(xodr.sample_piece(c, 2.0)))
            if best is None or turn < best[0]:
                best = (turn, c)
        return best[1] if best and best[0] < math.radians(STRAIGHT_TURN_MAX_DEG) else None
    return choose


def _straight_run(points_back, entry_h, rule=None):
    """Length of the approach from the entry backward (points_back[0] is the entry) that holds ``rule``:
    "straight" (the default): every point's heading within APPROACH_YAW_MAX_DEG of the entry's and within
    APPROACH_LATERAL_MAX_M of its tangent line; "gentle-bend": every point's heading within BEND_YAW_MAX_DEG of the
    entry's and no lane-centre radius under BEND_RADIUS_MIN_M (no lateral limit)."""
    rule = rule or "straight"
    if rule not in APPROACH_RULES:
        raise SiteError(f"unknown approach rule {rule!r}; known: {list(APPROACH_RULES)}")
    ex, ey = points_back[0][0], points_back[0][1]
    fx, fy = math.cos(entry_h), math.sin(entry_h)
    run = 0.0
    for i in range(1, len(points_back)):
        p = points_back[i]
        dh = abs(_wrap(p[2] - entry_h))
        if rule == "straight":
            lateral = abs(-fy * (p[0] - ex) + fx * (p[1] - ey))
            if dh > math.radians(APPROACH_YAW_MAX_DEG) or lateral > APPROACH_LATERAL_MAX_M:
                break
        else:
            if dh > math.radians(BEND_YAW_MAX_DEG):
                break
            if 1 <= i < len(points_back) - 1:
                k, _ = _circle(points_back[i - 1], p, points_back[i + 1])
                if k and 1.0 / abs(k) <= BEND_RADIUS_MIN_M:
                    break
        run += math.hypot(p[0] - points_back[i - 1][0], p[1] - points_back[i - 1][1])
    return run


def _start_on_chain(chain, distance, xodr=None, limit=None):
    """The point ``distance`` m back along chain (entry first): (point, piece, distance back). With ``xodr``, a
    point on a junction's connecting road is passed over, further back up to ``limit`` m: the hero starts on a road."""
    got = 0.0
    for i in range(1, len(chain)):
        got += math.hypot(chain[i][0] - chain[i - 1][0], chain[i][1] - chain[i - 1][1])
        if got >= distance:
            if xodr is not None and xodr.roads[chain[i][5][0]].junction != "-1":
                if limit is not None and got > limit:
                    return None, None, got
                continue
            return chain[i], chain[i][5], got
    return None, None, got


def target_box_check(xodr, cx, cy, h, half=TARGET_HALF, clearance=TARGET_CLEARANCE_M, cap=5.0, step=0.1):
    """The stationary target's body (its bounding box, not only its centre; OpenDRIVE frame, heading h) against
    every road surface of the map: ``clearanceM`` is the largest margin by which the box can grow on every side and
    still touch no surface lane (0.0 when the box itself touches or overlaps one; ``cap`` when nothing is that
    near; resolution 0.01 m). ``ok`` needs a clearance of at least ``clearance``; ``reason`` names the surface the
    box touches or comes within ``clearance`` of."""
    def hits(m):
        found = set()
        for x, y in _box_samples(cx, cy, h, half[0] + m, half[1] + m, step):
            found.update(xodr.locate(x, y))
        return sorted(found)

    on = hits(0.0)
    if on:
        return {"ok": False, "clearanceM": 0.0, "surfaces": [list(o) for o in on],
                "reason": "the target's box touches or overlaps " + ", ".join(
                    f"road {r} lane {l} ({t})" for r, l, t in on)}
    lo, hi = 0.0, cap
    if hits(cap):
        while hi - lo > 0.01:
            mid = 0.5 * (lo + hi)
            if hits(mid):
                hi = mid
            else:
                lo = mid
    near = hits(hi) if hi < cap else []
    out = {"ok": lo >= clearance - 1e-9, "clearanceM": round(lo, 3), "surfaces": [list(o) for o in near]}
    if not out["ok"]:
        out["reason"] = (f"the target's box is {lo:.3f} m from " + ", ".join(f"road {r} lane {l} ({t})"
                                                                               for r, l, t in near)
                         + f", under the clearance of {clearance} m")
    return out


# ====================================================================== the site record


@dataclass
class SiteSpec:
    site_id: str
    map_name: str
    xodr_sha256: str
    start: str                                   # road:lane:s, as da_world_side.py --start takes it
    start_pose: dict
    ego_path: list                               # CARLA poses along the hero's lane, from the start, 1 m apart
    target: dict                                 # blueprint, role, pose, motion ("stationary" or "script")
    target_path: list = field(default_factory=list)   # CARLA poses with s, for a moving target
    target_script: list = field(default_factory=list)
    props: list = field(default_factory=list)
    geometry: dict = field(default_factory=dict)
    guidance: dict = field(default_factory=dict)
    checks: dict = field(default_factory=dict)
    alternatives: list = field(default_factory=list)
    readings: dict = field(default_factory=dict)

    def as_record(self) -> dict:
        return {"siteId": self.site_id, "map": self.map_name, "xodrSha256": self.xodr_sha256, "start": self.start,
                "startPose": self.start_pose, "target": self.target, "targetScript": self.target_script,
                "targetPathPoints": len(self.target_path), "props": self.props, "geometry": self.geometry,
                "guidance": self.guidance, "checks": self.checks, "alternatives": self.alternatives,
                "benchReadings": self.readings, "egoPathPoints": len(self.ego_path)}

    def target_motion(self) -> "TargetMotion":
        return TargetMotion(self.target_script, self.target_path)


class TargetMotion:
    """SC-015's target: speed by the script's phases, position along its path (CARLA poses with ``s``)."""

    def __init__(self, script, path):
        self.script, self.path = list(script), list(path)
        self.times = []
        t = 0.0
        for ph in self.script:
            self.times.append(t)
            t += ph["durationS"]
        self.end_s = path[-1]["s"] if path else 0.0

    def at(self, t: float) -> dict:
        s, v, name = 0.0, 0.0, "rest"
        for t0, ph in zip(self.times, self.script):
            if t < t0:
                break
            dt = min(t - t0, ph["durationS"])
            v0, a = ph["fromMps"], ph["accelMps2"]
            s = ph["fromS"] + v0 * dt + 0.5 * a * dt * dt
            v = v0 + a * dt
            name = ph["phase"]
        if s >= self.end_s:
            s, v, name = self.end_s, 0.0, "stopped"
        pose = pose_at(self.path, s)
        return {"s": s, "speedMps": v, "phase": name, **pose}


def pose_at(path, s):
    """Linear interpolation of a CARLA pose list (each with ``s``) at s."""
    if not path:
        raise SiteError("empty path")
    if s <= path[0]["s"]:
        p = path[0]
        return {k: p[k] for k in ("x", "y", "z", "yaw")}
    for a, b in zip(path, path[1:]):
        if a["s"] <= s <= b["s"]:
            f = 0.0 if b["s"] == a["s"] else (s - a["s"]) / (b["s"] - a["s"])
            dyaw = (b["yaw"] - a["yaw"] + 180.0) % 360.0 - 180.0
            return {"x": a["x"] + f * (b["x"] - a["x"]), "y": a["y"] + f * (b["y"] - a["y"]),
                    "z": a["z"] + f * (b["z"] - a["z"]), "yaw": a["yaw"] + f * dyaw}
    p = path[-1]
    return {k: p[k] for k in ("x", "y", "z", "yaw")}


def _path_record(points, s0=0.0):
    out, s = [], s0
    for i, p in enumerate(points):
        if i:
            s += math.hypot(p[0] - points[i - 1][0], p[1] - points[i - 1][1])
        out.append({"s": round(s, 3), **carla_pose(p[0], p[1], p[2], p[3])})
    return out


def _thin(path, step=1.0):
    out = []
    for p in path:
        if not out or p["s"] - out[-1]["s"] >= step - 1e-9:
            out.append(p)
    if path and out[-1] is not path[-1]:
        out.append(path[-1])
    return out


def _start_str(xodr, piece, p):
    s = p[4]
    road = xodr.roads[piece[0]]
    s = min(max(s, 0.0), road.length)
    return f"{piece[0]}:{piece[2]}:{round(s, 3)}"


# ====================================================================== SC-DRIVING-014: the curve

START_BACK_014_M = 150.0      # PROPOSAL (S1 plan section 3): the hero starts this far before the curve when the
                              # straight approach is that long, else at APPROACH_014_M


def _road_lane_chains(xodr, road):
    """Per driving lane of a road, its samples in travel order across the road's lane sections."""
    out = []
    for idx, sec in enumerate(road.sections):
        for lid, lane in sec.lanes.items():
            if lane.type != "driving":
                continue
            first = (idx == 0) if lid < 0 else (idx == len(road.sections) - 1)
            if not first:
                continue
            piece, pts, seen = (road.id, idx, lid), [], set()
            while piece is not None and piece[0] == road.id and piece not in seen:
                seen.add(piece)
                sp = xodr.sample_piece(piece)
                pts += sp[1:] if pts else sp
                nxt = [n for n in xodr.next_pieces(piece, True) if n[0] == road.id]
                piece = nxt[0] if nxt else None
            out.append(pts)
    return out


def _curvatures(pts, k=2):
    out = [0.0] * len(pts)
    centres = [None] * len(pts)
    for i in range(k, len(pts) - k):
        out[i], centres[i] = _circle(pts[i - k], pts[i], pts[i + k])
    for i in range(k):
        out[i], centres[i] = out[k], centres[k]
        out[-1 - i], centres[-1 - i] = out[-1 - k], centres[-1 - k]
    return out, centres


def _outer_edges(xodr, p, centre, sign):
    """Radii, at sample p, of the outermost border of the surface lanes (road edge) and of the driving lanes on the
    outer side of the hero's lane; sign > 0: the curve turns left (the outer side is the right)."""
    road = xodr.roads[p[5][0]]
    s = p[4]
    idx = road.section_index(s)
    lanes = road.sections[idx].lanes
    edge = drive = None
    for lid, (a, b) in road.borders(s, idx).items():
        typ = lanes[lid].type
        for t in (a, b):
            x, y, _ = road.point(s, t)
            r = math.hypot(x - centre[0], y - centre[1])
            if typ in SURFACE_TYPES:
                edge = r if edge is None else max(edge, r)
            if typ == "driving":
                drive = r if drive is None else max(drive, r)
    return edge, drive


def find_curve_candidates(xodr, rule=None):
    cands = []
    for road in xodr.roads.values():
        if road.junction != "-1":
            continue
        for pts in _road_lane_chains(xodr, road):
            if len(pts) < 10:
                continue
            kap, centres = _curvatures(pts)
            i = 0
            while i < len(pts):
                if abs(kap[i]) < 1.0 / CURVE_RADIUS_MAX_M - 1e-6:
                    i += 1
                    continue
                sign = 1 if kap[i] > 0 else -1
                j = i
                while j + 1 < len(pts) and kap[j + 1] * sign >= 1.0 / CURVE_RADIUS_MAX_M - 1e-6:
                    j += 1
                turn = _heading_change(pts[i:j + 1])
                if abs(math.degrees(turn)) >= CURVE_TURN_MIN_DEG:
                    e = i
                    while e > 0 and kap[e - 1] * sign > STRAIGHT_KAPPA_MAX:
                        e -= 1
                    if 0 < e < i:
                        # the 3-point circles reach 1 m (two samples) ahead: the first curved one lies 0.5 to 1 m
                        # before the curve; one sample on puts the entry within 0.5 m before it
                        e += 1
                    # the radius off the 3-point circles that lie wholly inside the tight run (the ones that
                    # straddle its ends mix in the straight before and after it)
                    inner = range(i + 2, j - 1) if j - i > 4 else range(i, j + 1)
                    radii = [1.0 / abs(kap[q]) for q in inner]
                    edges = [_outer_edges(xodr, pts[q], centres[q], sign) for q in list(inner)[::4]]
                    run, chain = _approach_mid(xodr, pts, e, rule)
                    piece = pts[i][5]
                    same_dir = sorted(l for l, ln in xodr.roads[road.id].sections[piece[1]].lanes.items()
                                      if ln.type == "driving" and (l < 0) == (piece[2] < 0))
                    cands.append({
                        "road": road.id, "lane": piece[2], "entryIndex": e, "tightFrom": i, "tightTo": j,
                        "pts": pts, "chain": chain, "turnDeg": round(math.degrees(turn), 2),
                        "turnSide": "left" if sign > 0 else "right",
                        "laneCentreRadiusM": [round(min(radii), 3), round(max(radii), 3)],
                        "roadEdgeRadiusM": round(max(e_[0] for e_ in edges if e_[0] is not None), 3),
                        "drivingEdgeRadiusM": round(max(e_[1] for e_ in edges if e_[1] is not None), 3),
                        "tightLengthM": round(sum(math.hypot(pts[q][0] - pts[q - 1][0], pts[q][1] - pts[q - 1][1])
                                                  for q in range(i + 1, j + 1)), 2),
                        "approachM": round(run, 2), "centre": centres[(i + j) // 2], "sign": sign,
                        "outermostLane": piece[2] == (min(same_dir) if piece[2] < 0 else max(same_dir)),
                        "sameDirectionLanes": len(same_dir),
                    })
                i = j + 1
    return cands


def _approach_mid(xodr, pts, e, rule=None):
    """Approach from point e of a road's lane chain ``pts``: the chain's own points back to its start, then the lanes
    before it (the straightest predecessor at each branch). Returns (length by ``rule``, chain from e backward)."""
    chain = list(reversed(pts[: e + 1]))
    prev = xodr.next_pieces(pts[0][5], False)
    first = _straightest(xodr)(prev) if prev else None
    if first is not None:
        back = _walk(xodr, first, 400.0, False, _straightest(xodr))
        chain += list(reversed(back))[1:]
    return _straight_run(chain, pts[e][2], rule), chain


def _curve_rank(c):
    # prefer: the outer road edge within the radius, then the outer lane (R152: "the subject vehicle drives outer lane
    # than the centre of the road"): the outermost lane of its direction, then the largest lane-centre radius; then
    # the longest approach
    return (c["roadEdgeRadiusM"] > CURVE_RADIUS_MAX_M, not c["outermostLane"], -c["laneCentreRadiusM"][1],
            -c["approachM"], int(c["road"]) if str(c["road"]).lstrip("-").isdigit() else 0, c["lane"])


def _offset_points(points, lateral):
    """Points moved ``lateral`` m to the right of travel (OpenDRIVE frame: right = -left normal)."""
    out = []
    for p in points:
        out.append((p[0] + lateral * math.sin(p[2]), p[1] - lateral * math.cos(p[2]), p[2], p[3], p[4], p[5]))
    return out


def _resample(points, step):
    out = [points[0]]
    acc = 0.0
    for a, b in zip(points, points[1:]):
        d = math.hypot(b[0] - a[0], b[1] - a[1])
        acc += d
        if acc >= step:
            out.append(b)
            acc = 0.0
    return out


def build_curve_site(xodr, map_name, props_available, prop_extents, rule="straight", approach_min_m=None,
                     lane_rule=None, reason=None, extents_source=None):
    if lane_rule is not None and lane_rule not in LANE_RULES:
        raise SiteError(f"unknown lane rule {lane_rule!r}; known: {list(LANE_RULES)}")
    min_m = APPROACH_014_M if approach_min_m is None else float(approach_min_m)
    named = f"rule {rule!r}" + (f", lane {lane_rule!r}" if lane_rule else "")
    every = find_curve_candidates(xodr, rule)
    pool = [c for c in every if c["outermostLane"]] if lane_rule == "outermost" else every
    cands = [c for c in pool if c["approachM"] >= min_m]
    if not cands:
        best = sorted(pool, key=_curve_rank)[:3]
        raise SiteError(f"no non-junction curve with a lane-centre radius of at most {CURVE_RADIUS_MAX_M} m over "
                        f"{CURVE_TURN_MIN_DEG} deg and {min_m} m of approach ({named}) on {map_name}"
                        + (f", under the minimum approach of {min_m} m" if approach_min_m is not None else "")
                        + "; best: " + "; ".join(f"road {c['road']} lane {c['lane']} approach {c['approachM']} m"
                                                 for c in best))
    cands.sort(key=_curve_rank)
    c = cands[0]
    pts, e, j = c["pts"], c["entryIndex"], c["tightTo"]
    entry = pts[e]
    # the hero's start on the approach; under a named minimum, at the approach's far end (the most time at speed)
    if c["approachM"] >= START_BACK_014_M:
        back = START_BACK_014_M
    elif approach_min_m is not None:
        back = c["approachM"] - 0.01
    else:
        back = APPROACH_014_M
    sp, spiece, back = _start_on_chain(c["chain"], back, xodr, c["approachM"])
    if sp is None:
        raise SiteError("no start on a road (outside junctions) within the approach")
    start = _start_str(xodr, spiece, sp)
    # the hero's lane from the start, through the curve, 20 m beyond the tight part
    to_entry = list(reversed(c["chain"][: c["chain"].index(sp) + 1]))
    through = pts[e + 1: min(len(pts), j + 41)]
    ego = to_entry + through
    ego_path = _thin(_path_record(ego))
    # guard pipes on the outer shoulder: between the outermost driving border and the road edge
    prop = _choose_prop(props_available)
    ext = prop_extents.get(prop) or {}
    half_l, half_w = _prop_halves(ext)
    centre = c["centre"]
    r_lane = math.hypot(pts[(c["tightFrom"] + j) // 2][0] - centre[0], pts[(c["tightFrom"] + j) // 2][1] - centre[1])
    shoulder_mid = 0.5 * (c["drivingEdgeRadiusM"] + c["roadEdgeRadiusM"])
    if c["roadEdgeRadiusM"] - c["drivingEdgeRadiusM"] >= 2 * half_w + 0.1:
        r_prop, where = shoulder_mid, "on the outer shoulder, midway between the driving lane's edge and the road edge"
    else:
        r_prop, where = c["roadEdgeRadiusM"] + half_w + 0.1, "just outside the outer road edge (no shoulder wide enough)"
    lateral = (r_prop - r_lane) * (1 if c["sign"] > 0 else -1)   # right of travel for a left curve
    # from PROP_LEAD_M before the entry to the end of the tight part
    lead = list(reversed(c["chain"][: c["chain"].index(_start_on_chain(c["chain"], PROP_LEAD_M)[0]) + 1]))
    rail = _offset_points(lead + pts[e + 1: j + 1], lateral)
    spacing = 2 * half_l + PROP_GAP_M
    props, boxes = [], []
    for p in _resample(rail, spacing):
        yaw_h = p[2] + (math.pi / 2 if ext.get("longAxis") == "y" else 0.0)
        props.append({"blueprint": prop, **carla_pose(p[0], p[1], yaw_h, p[3])})
        boxes.append(_box(p[0], p[1], p[2], half_l, half_w))
    # the stationary target on the tangent extension of the lane centre at the entry, outside the road and pipes
    hx, hy, hh = entry[0], entry[1], entry[2]
    target, first_refusal = None, None
    for k in range(int(5.0 / TARGET_STEP_M), int(80.0 / TARGET_STEP_M)):
        d = k * TARGET_STEP_M
        cx, cy = hx + d * math.cos(hh), hy + d * math.sin(hh)
        body = _box(cx, cy, hh, TARGET_HALF[0] + TARGET_CLEARANCE_M, TARGET_HALF[1] + TARGET_CLEARANCE_M)
        if any(_boxes_overlap(body, b) for b in boxes):
            continue
        if any(xodr.locate(x, y) for x, y in _box_samples(cx, cy, hh, TARGET_HALF[0] + TARGET_CLEARANCE_M,
                                                          TARGET_HALF[1] + TARGET_CLEARANCE_M)):
            if first_refusal is None:
                first_refusal = (d, target_box_check(xodr, cx, cy, hh))
            continue
        target = (d, cx, cy)
        break
    if target is None:
        d0, chk = first_refusal or (None, {"reason": "the pipes fill the tangent extension"})
        raise SiteError("no place for the stationary target on the tangent extension within 80 m of the curve "
                        f"entry, clear of every road surface by {TARGET_CLEARANCE_M} m (first try at {d0} m: "
                        f"{chk.get('reason')})")
    d, cx, cy = target
    box_check = target_box_check(xodr, cx, cy, hh)
    if not box_check["ok"]:
        raise SiteError("SC-014 target refused: " + box_check["reason"])
    z = entry[3]
    tbox = _box(cx, cy, hh, TARGET_HALF[0], TARGET_HALF[1])
    # checks: the pipes keep off every driving lane; the target is off the hero's path through the curve
    pipe_on_driving = [i for i, b in enumerate(boxes)
                       if any(h[2] == "driving" for x, y in _box_samples(*_centre_of(b), _yaw_of(b),
                                                                         half_l, half_w) for h in xodr.locate(x, y))]
    curve_pts = pts[e: j + 41]
    min_clear = min(_min_dist_box(p, tbox) for p in curve_pts) - EGO_HALF[1]
    gap = d - TARGET_HALF[0] - EGO_HALF[0]
    checks = {
        "targetOffEveryRoadSurface": box_check["clearanceM"] > 0.0,
        "targetClearanceFromRoadSurfaceM": box_check["clearanceM"],
        "targetNearestSurface": box_check["surfaces"],
        "targetClearOfPipes": True,
        "pipesOffDrivingLanes": not pipe_on_driving,
        "pipesOnDrivingLanes": pipe_on_driving,
        "targetClearanceFromHeroPathM": round(min_clear, 3),
        "targetNeverInPath": min_clear > TARGET_CLEARANCE_M,
        "laneCentreRadiusWithinModel": c["laneCentreRadiusM"][1] <= CURVE_RADIUS_MAX_M + 1e-6,
    }
    if not checks["pipesOffDrivingLanes"] or not checks["targetNeverInPath"]:
        raise SiteError(f"SC-014 site fails its checks: {checks}")
    geometry = {k: c[k] for k in ("road", "lane", "turnDeg", "turnSide", "laneCentreRadiusM", "roadEdgeRadiusM",
                                  "drivingEdgeRadiusM", "tightLengthM", "approachM", "outermostLane",
                                  "sameDirectionLanes")}
    geometry["approachStraightM"] = round(_straight_run(c["chain"], entry[2], "straight"), 2)
    geometry["approachGentleBendM"] = round(_straight_run(c["chain"], entry[2], "gentle-bend"), 2)
    geometry.update({"entry": carla_pose(*entry[:3], entry[3]), "entryRoadLaneS": _start_str(xodr, entry[5], entry),
                     "startBackM": round(back, 2), "pipeRadiusM": round(r_prop, 3), "pipePlacement": where,
                     "roadEdgeWithinModel": c["roadEdgeRadiusM"] <= CURVE_RADIUS_MAX_M + 1e-6})
    v30, v22 = 30.0 * KMH, GUIDANCE_014["atCurveEntryMinKmh"] * KMH
    guidance = {"regulation": GUIDANCE_014, "predicted": {
        "gapAtTurnInM": round(gap, 3),
        "ttcAtTurnInS": {"at30Kmh": round(gap / v30, 3), "at22Kmh": round(gap / v22, 3)},
        "ttcAtTurnInMetAt30Kmh": gap / v30 <= GUIDANCE_014["ttcAtTurnInMaxS"],
        "radiusAtOuterRoadSideM": c["roadEdgeRadiusM"],
        "note": "geometric: the hero's front bumper at the curve entry and the target's nearest face on the "
                "tangent; the run's own ticks give the measured values"}}
    alt = [{k: a[k] for k in ("road", "lane", "turnDeg", "laneCentreRadiusM", "roadEdgeRadiusM", "approachM")}
           for a in cands[1:8]]
    readings = {"curveTurnMinDeg": CURVE_TURN_MIN_DEG, "approachMinM": min_m, "approachRule": rule,
                "approachStraight": f"heading within {APPROACH_YAW_MAX_DEG} deg of the entry's and within "
                                    f"{APPROACH_LATERAL_MAX_M} m of its tangent",
                "approachGentleBend": f"heading within {BEND_YAW_MAX_DEG} deg of the entry's and no lane-centre "
                                      f"radius under {BEND_RADIUS_MIN_M} m (chosen by name only)",
                "curveStartsBelowRadiusM": 1.0 / STRAIGHT_KAPPA_MAX,
                "radiusOfTheModel": "the lane-centre radius in the hero's lane (D-S1-4); the road edge is recorded",
                "propChoice": f"the first static.prop.* containing one of {list(PROP_PATTERNS)}",
                "targetClearanceM": TARGET_CLEARANCE_M,
                "propExtentsSource": extents_source or "the caller's prop_extents"}
    if lane_rule is not None or approach_min_m is not None:
        readings["siteSelection"] = {"approachRule": rule, "lane": lane_rule, "approachMinM": min_m, "reason": reason,
                                     "chosen": {"road": c["road"], "lane": c["lane"], "approachM": c["approachM"]}}
    return SiteSpec("sc014-curve", map_name, xodr.sha256, start, carla_pose(sp[0], sp[1], sp[2], sp[3]), ego_path,
                    {"blueprint": "vehicle.tesla.model3", "motion": "stationary", "tangentDistanceM": d,
                     **carla_pose(cx, cy, hh, z)},
                    props=props, geometry=geometry, guidance=guidance, checks=checks, alternatives=alt,
                    readings=readings)


def _centre_of(box):
    return sum(p[0] for p in box) / 4.0, sum(p[1] for p in box) / 4.0


def _yaw_of(box):
    return math.atan2(box[0][1] - box[3][1], box[0][0] - box[3][0])


def _min_dist_box(p, box):
    px, py = p[0], p[1]
    if _point_in(px, py, box):
        return 0.0
    best = None
    for i in range(4):
        a, b = box[i], box[(i + 1) % 4]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = dx * dx + dy * dy
        f = 0.0 if L == 0 else max(0.0, min(1.0, ((px - a[0]) * dx + (py - a[1]) * dy) / L))
        d = math.hypot(px - a[0] - f * dx, py - a[1] - f * dy)
        best = d if best is None else min(best, d)
    return best


def _point_in(x, y, box):
    sign = None
    for i in range(4):
        a, b = box[i], box[(i + 1) % 4]
        cr = (b[0] - a[0]) * (y - a[1]) - (b[1] - a[1]) * (x - a[0])
        if sign is None:
            sign = cr >= 0
        elif (cr >= 0) != sign:
            return False
    return True


def _choose_prop(props_available):
    if props_available is None:
        raise SiteError("the server's static.prop.* list is needed to choose the guard pipes")
    for pattern in PROP_PATTERNS:
        for pid in sorted(props_available):
            if pid.startswith("static.prop.") and pattern in pid.lower():
                return pid
    raise SiteError(f"no guard-pipe-like prop ({list(PROP_PATTERNS)}) among the server's static.prop.* blueprints")


def _prop_halves(ext):
    e = ext.get("extent")
    if not e:
        return PROP_DEFAULT_LENGTH_M / 2.0, 0.25
    return max(e[0], e[1]), min(e[0], e[1])


# ====================================================================== SC-DRIVING-015: the turn-off


def _connector_turn(xodr, piece):
    pts = []
    cur, seen = piece, set()
    while cur is not None and cur[0] == piece[0] and cur not in seen:
        seen.add(cur)
        sp = xodr.sample_piece(cur, 1.0)
        pts += sp[1:] if pts else sp
        nxt = [n for n in xodr.next_pieces(cur, True) if n[0] == piece[0]]
        cur = nxt[0] if nxt else None
    turn = _heading_change(pts)
    kap = [abs(_circle(pts[i - 1], pts[i], pts[i + 1])[0]) for i in range(1, len(pts) - 1)] or [0.0]
    return math.degrees(turn), (1.0 / max(kap) if max(kap) > 0 else None), pts


def find_turnoff_candidates(xodr):
    out = []
    for jid, conns in xodr.junctions.items():
        groups = {}
        for c in conns:
            inc = xodr.roads.get(c["incoming"])
            cr = xodr.roads.get(c["connecting"])
            if inc is None or cr is None:
                continue
            for frm, to in c["lanes"]:
                p = xodr._enter(cr.id, c["contact"], to)
                if p is None or xodr.piece_lane(p).type != "driving":
                    continue
                turn, rmin, cpts = _connector_turn(xodr, p)
                groups.setdefault((inc.id, frm), []).append({"connecting": cr.id, "piece": p, "turnDeg": turn,
                                                             "minRadiusM": rmin, "pts": cpts})
        for (rid, lane), lst in groups.items():
            straight = [x for x in lst if abs(x["turnDeg"]) < STRAIGHT_TURN_MAX_DEG]
            right = [x for x in lst if RIGHT_TURN_DEG[0] <= -x["turnDeg"] <= RIGHT_TURN_DEG[1]]
            if not straight or not right:
                continue
            road = xodr.roads[rid]
            link = road.link.get("successor")
            at_end = link is not None and link[0] == "junction" and link[1] == jid
            idx = len(road.sections) - 1 if at_end else 0
            piece = (rid, idx, lane)
            if piece[2] not in road.sections[idx].lanes or xodr.piece_lane(piece).type != "driving":
                continue
            if (lane < 0) != at_end:          # the lane must travel into the junction
                continue
            pts = xodr.sample_piece(piece)
            run, chain = _approach_mid(xodr, pts, len(pts) - 1)
            same_dir = [l for l, ln in road.sections[idx].lanes.items()
                        if ln.type == "driving" and (l < 0) == (lane < 0)]
            outermost = lane == (min(same_dir) if lane < 0 else max(same_dir))
            out.append({"junction": jid, "road": rid, "lane": lane, "entry": pts[-1], "chain": chain,
                        "outermostLane": outermost,
                        "approachM": round(run, 2), "straight": straight, "right": right})
    return out


def build_turnoff_site(xodr, map_name):
    cands = [c for c in find_turnoff_candidates(xodr) if c["approachM"] >= APPROACH_015_M]
    if not cands:
        raise SiteError(f"no junction lane with a straight and a right-turn connector and {APPROACH_015_M} m of "
                        f"straight approach on {map_name}")
    cands.sort(key=lambda c: (not c["outermostLane"], -c["approachM"],
                              int(c["junction"]) if c["junction"].isdigit() else 0))
    c = cands[0]
    straight = min(c["straight"], key=lambda x: abs(x["turnDeg"]))
    right = min(c["right"], key=lambda x: abs(-x["turnDeg"] - 90.0))
    sp, spiece, back = _start_on_chain(c["chain"], APPROACH_015_M, xodr, c["approachM"])
    if sp is None:
        raise SiteError("no start on a road (outside junctions) within the approach")
    start = _start_str(xodr, spiece, sp)
    to_entry = list(reversed(c["chain"][: c["chain"].index(sp) + 1]))

    def beyond(conn, metres):
        after = _walk(xodr, conn["pts"][-1][5], metres + 5.0, True, _straightest(xodr))
        tail = [p for p in after if p[5][0] != conn["piece"][0]]
        return conn["pts"][1:] + tail[1:]

    ego = to_entry + beyond(straight, TARGET_015["afterTurnM"])
    ego_path = _thin(_path_record(ego))
    # the target: TARGET_015["aheadM"] ahead of the hero in its lane, then the right-turn connector
    tpath_all = _path_record(to_entry + beyond(right, TARGET_015["afterTurnM"]))
    s0 = TARGET_015["aheadM"]
    tpath = [dict(p, s=round(p["s"] - s0, 3)) for p in tpath_all if p["s"] >= s0 - 1e-9]
    entry_s = _path_record(to_entry)[-1]["s"] - s0
    v1, v2 = TARGET_015["holdKmh"] * KMH, TARGET_015["turnKmh"] * KMH
    a1, b = TARGET_015["accelMps2"], TARGET_015["brakeMps2"]
    d_a, d_b = v1 * v1 / (2 * a1), (v1 * v1 - v2 * v2) / (2 * b)
    d_h = entry_s - d_a - d_b
    t_h = d_h / v1
    if t_h < TARGET_015["holdMinS"]:
        raise SiteError(f"the target's hold at 40 km/h lasts {t_h:.2f} s, under {TARGET_015['holdMinS']} s")
    end_s = tpath[-1]["s"]
    script = [
        {"phase": "accelerate", "fromS": 0.0, "fromMps": 0.0, "accelMps2": a1, "durationS": round(v1 / a1, 4)},
        {"phase": "hold", "fromS": round(d_a, 4), "fromMps": v1, "accelMps2": 0.0, "durationS": round(t_h, 4)},
        {"phase": "brake", "fromS": round(d_a + d_h, 4), "fromMps": v1, "accelMps2": -b,
         "durationS": round((v1 - v2) / b, 4)},
        {"phase": "turn", "fromS": round(entry_s, 4), "fromMps": v2, "accelMps2": 0.0,
         "durationS": round((end_s - entry_s) / v2, 4), "connector": right["connecting"]},
    ]
    t_turn = sum(p["durationS"] for p in script[:3])
    geometry = {"junction": c["junction"], "incomingRoad": c["road"], "incomingLane": c["lane"],
                "outermostLane": c["outermostLane"], "startBackM": round(back, 2),
                "approachM": c["approachM"], "entry": carla_pose(*c["entry"][:3], c["entry"][3]),
                "straightConnector": {"road": straight["connecting"], "turnDeg": round(straight["turnDeg"], 2)},
                "rightConnector": {"road": right["connecting"], "turnDeg": round(right["turnDeg"], 2),
                                   "minRadiusM": None if right["minRadiusM"] is None else round(right["minRadiusM"], 2)},
                "otherConnectorsFromTheLane": sorted({x["connecting"] for x in c["straight"] + c["right"]}
                                                     - {straight["connecting"], right["connecting"]})}
    guidance = {"regulation": GUIDANCE_015, "predicted": {
        "targetTurnBeginS": round(t_turn, 3), "targetTurnBeginPose": pose_at(tpath, entry_s),
        "targetSpeedAtTurnKmh": TARGET_015["turnKmh"],
        "note": "the hero's speed and TTC at the turn begin come from the run's ticks (the candidate drives)"}}
    checks = {"holdS": round(t_h, 3), "holdAtLeastMinS": t_h >= TARGET_015["holdMinS"],
              "egoGoesStraight": abs(straight["turnDeg"]) < STRAIGHT_TURN_MAX_DEG,
              "targetTurnsRight": RIGHT_TURN_DEG[0] <= -right["turnDeg"] <= RIGHT_TURN_DEG[1],
              "sameIncomingLane": True}
    alt = [{"junction": a["junction"], "road": a["road"], "lane": a["lane"], "approachM": a["approachM"],
            "right": [x["connecting"] for x in a["right"]], "straight": [x["connecting"] for x in a["straight"]]}
           for a in cands[1:8]]
    readings = {"approachMinM": APPROACH_015_M, "straightTurnMaxDeg": STRAIGHT_TURN_MAX_DEG,
                "rightTurnDeg": list(RIGHT_TURN_DEG), "targetScript": TARGET_015,
                "approachStraight": f"heading within {APPROACH_YAW_MAX_DEG} deg of the entry's and within "
                                    f"{APPROACH_LATERAL_MAX_M} m of its tangent"}
    tpose = tpath[0]
    return SiteSpec("sc015-turnoff", map_name, xodr.sha256, start, carla_pose(sp[0], sp[1], sp[2], sp[3]), ego_path,
                    {"blueprint": "vehicle.tesla.model3", "motion": "script", "aheadM": s0,
                     **{k: tpose[k] for k in ("x", "y", "z", "yaw")}},
                    target_path=tpath, target_script=script, geometry=geometry, guidance=guidance, checks=checks,
                    alternatives=alt, readings=readings)


# ====================================================================== entry point


_CACHE: dict = {}


def resolve(world_map, site_id: str, setting=None, *, props_available=None, prop_extents=None,
            approach_rule: str = "straight", approach_min_m: float | None = None, lane_rule: str | None = None,
            rule_reason: str | None = None) -> SiteSpec:
    """The site ``site_id`` on ``world_map`` (a ``carla.Map``: its ``name`` and ``to_opendrive()``).

    ``props_available``: the server's ``static.prop.*`` blueprint ids (``blueprint_library.filter('static.prop.*')``);
    SC-014 refuses a prop the server does not list. ``prop_extents``: {prop id: {"extent": [x, y, z]}} from the map
    read, for the pipes' spacing; None: the G4 read's (PROP_EXTENTS_G4). ``setting`` (``scenarios.Setting``) is
    checked against the site when it names one. SC-014 only: ``approach_min_m`` (default APPROACH_014_M) and
    ``lane_rule`` (LANE_RULES) select the curve by name, and ``rule_reason`` is recorded with them
    (``readings["siteSelection"]``).
    """
    if approach_rule is None:
        raise SiteError("no approach rule named: the setting names one (scenarios.Setting.site_approach_rule)")
    if site_id not in SITE_IDS:
        raise SiteError(f"unknown site {site_id!r}; known: {list(SITE_IDS)}")
    want = getattr(setting, "site", site_id) if setting is not None else site_id
    if want != site_id:
        raise SiteError(f"setting {getattr(setting, 'setting_id', setting)} names site {want!r}, not {site_id!r}")
    text = world_map.to_opendrive()
    key = (hashlib.sha256(text.encode("utf-8")).hexdigest(), site_id,
           tuple(sorted(props_available)) if props_available is not None else None, approach_rule, approach_min_m,
           lane_rule, rule_reason, prop_extents is None)
    if key in _CACHE:
        return _CACHE[key]
    xodr = Xodr(text)
    name = str(world_map.name).rstrip("/").split("/")[-1]
    if site_id == "sc014-curve":
        source = "the caller's prop_extents"
        if prop_extents is None:
            prop_extents, source = PROP_EXTENTS_G4, "the G4 read of 2026-11-20 (sites.PROP_EXTENTS_G4)"
        spec = build_curve_site(xodr, name, props_available, prop_extents, approach_rule, approach_min_m, lane_rule,
                                rule_reason, source)
    else:
        spec = build_turnoff_site(xodr, name)
    _CACHE[key] = spec
    return spec
