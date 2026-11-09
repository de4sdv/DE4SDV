"""VC-003 / 006 / 007 decided from the C2 metadata of amendments 1 and 2.

A11 adds the per-step mapContext, routeMask and front_hi_res fields; A16 adds
waypointsInWindow / waypointsOnCorridor and rasterPose; A17 fixes what a
camera width/height means. These tests pass on the nominal synthetic run and
break one field at a time on a copy, so each check is shown to measure
something.
"""

from __future__ import annotations

import json

import cases
from conftest import edit_jsonl, verdict

NOMINAL = "nominal"
C2 = "score/checkpointInputs.jsonl"


def _run(run_for):
    from runio import Run
    return Run(run_for(NOMINAL).root)


def copied(run_for, tmp_path, tag):
    import strip
    return strip.copy_run(run_for(NOMINAL).root, tmp_path / f"nominal-{tag}")


def _edit_c2(d, fn):
    return edit_jsonl(d / C2, "out.checkpoint_inputs", fn)


def _first_with_waypoints(fn):
    """Apply fn to the first plan step whose routeMask has in-window waypoints.

    The fixture writes C2 from the agent's first step, as the agent does; the
    steps before the end of priming have no plan and are not judged."""
    state = {"done": False}

    def edit(data):
        rm = data.get("routeMask") or {}
        if not state["done"] and data.get("primed") \
                and isinstance(rm.get("waypointsInWindow"), int) \
                and rm["waypointsInWindow"] > 0:
            fn(data)
            state["done"] = True
        return data
    return edit


# ------------------------------------------------------------------ nominal
def test_nominal_passes_vc003(run_for):
    res = verdict(_run(run_for), "VC-DRIVING-003")
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.missing, res.notes)


def test_nominal_passes_vc006(run_for):
    res = verdict(_run(run_for), "VC-DRIVING-006")
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.missing, res.notes)
    assert res.measured["worst_render_age_s"] <= 0.5


def test_nominal_passes_vc007(run_for):
    res = verdict(_run(run_for), "VC-DRIVING-007")
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.missing, res.notes)
    assert res.measured["recount_done"] is True
    assert res.measured["recount_mismatches"] == []


# ------------------------------------------------------------- map context
def test_one_step_with_another_geometry_tag_fails_vc006(run_for, tmp_path):
    d = copied(run_for, tmp_path, "map-geometry")
    state = {"done": False}

    def fn(data):
        if not state["done"] and data.get("primed"):     # a plan step
            data["mapContext"]["geometry"] = "other-bev-450x300-0p4m-v1"
            state["done"] = True
        return data
    assert _edit_c2(d, fn) == 1
    from runio import Run
    res = verdict(Run(d), "VC-DRIVING-006")
    assert res.outcome == cases.FAIL
    assert res.measured["problems"][0]["problems"]


def test_one_step_with_thirteen_channels_fails_vc006(run_for, tmp_path):
    d = copied(run_for, tmp_path, "map-channels")
    state = {"done": False}

    def fn(data):
        if not state["done"] and data.get("primed"):     # a plan step
            data["mapContext"]["channels"] = 13
            state["done"] = True
        return data
    assert _edit_c2(d, fn) == 1
    from runio import Run
    res = verdict(Run(d), "VC-DRIVING-006")
    assert res.outcome == cases.FAIL


def test_render_age_of_600_ms_fails_vc006(run_for, tmp_path):
    d = copied(run_for, tmp_path, "map-age")
    state = {"done": False}

    def fn(data):
        if not state["done"] and data.get("primed"):     # a plan step
            data["map_context_render_sim_ms"] = data["sim_ms"] - 600
            state["done"] = True
        return data
    assert _edit_c2(d, fn) == 1
    from runio import Run
    res = verdict(Run(d), "VC-DRIVING-006")
    assert res.outcome == cases.FAIL
    assert res.measured["worst_render_age_s"] > 0.5


def test_no_map_context_is_inconclusive_vc006(run_for, tmp_path):
    d = copied(run_for, tmp_path, "map-absent")

    def fn(data):
        data.pop("mapContext", None)
        return data
    assert _edit_c2(d, fn) > 0
    from runio import Run
    res = verdict(Run(d), "VC-DRIVING-006")
    assert res.outcome == cases.INCONCL
    assert any("mapContext" in m for m in res.missing)


# -------------------------------------------------------------- route mask
def test_another_route_sha_fails_vc007(run_for, tmp_path):
    d = copied(run_for, tmp_path, "route-sha")
    state = {"done": False}

    def fn(data):
        if not state["done"] and data.get("primed"):     # a plan step
            data["routeMask"]["routeSha256"] = "0" * 64
            state["done"] = True
        return data
    assert _edit_c2(d, fn) == 1
    from runio import Run
    res = verdict(Run(d), "VC-DRIVING-007")
    assert res.outcome == cases.FAIL
    assert res.measured["sha_mismatches"]


def test_one_corridor_count_short_fails_vc007(run_for, tmp_path):
    d = copied(run_for, tmp_path, "route-short")

    def fn(data):
        rm = data["routeMask"]
        rm["waypointsOnCorridor"] = rm["waypointsInWindow"] - 1
    assert _edit_c2(d, _first_with_waypoints(fn)) == 1
    from runio import Run
    res = verdict(Run(d), "VC-DRIVING-007")
    assert res.outcome == cases.FAIL
    assert res.measured["corridor_mismatches"]


def test_shifted_raster_pose_fails_the_recount(run_for, tmp_path):
    d = copied(run_for, tmp_path, "route-pose")

    def fn(data):
        data["rasterPose"]["x_map_m"] += 30.0
    assert _edit_c2(d, _first_with_waypoints(fn)) == 1
    from runio import Run
    res = verdict(Run(d), "VC-DRIVING-007")
    assert res.outcome == cases.FAIL
    assert res.measured["recount_done"] is True
    assert res.measured["recount_mismatches"]


def test_no_route_mask_is_inconclusive_vc007(run_for, tmp_path):
    d = copied(run_for, tmp_path, "route-absent")

    def fn(data):
        data.pop("routeMask", None)
        return data
    assert _edit_c2(d, fn) > 0
    from runio import Run
    res = verdict(Run(d), "VC-DRIVING-007")
    assert res.outcome == cases.INCONCL
    assert any("routeMask" in m for m in res.missing)


def test_no_raster_pose_is_inconclusive_vc007(run_for, tmp_path):
    d = copied(run_for, tmp_path, "pose-absent")

    def fn(data):
        data.pop("rasterPose", None)
        return data
    assert _edit_c2(d, fn) > 0
    from runio import Run
    res = verdict(Run(d), "VC-DRIVING-007")
    assert res.outcome == cases.INCONCL
    assert any("rasterPose" in m for m in res.missing)


def test_without_the_route_file_the_case_is_still_decided(run_for, tmp_path):
    d = copied(run_for, tmp_path, "route-file-gone")
    (d / "navigation/route.json").unlink()
    from runio import Run
    res = verdict(Run(d), "VC-DRIVING-007")
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)
    assert res.measured["recount_done"] is False
    assert any("recount" in n for n in res.notes)


def test_without_a_route_entry_the_sha_comes_from_the_announcements(run_for, tmp_path):
    d = copied(run_for, tmp_path, "route-record-gone")
    import strip
    rec = json.loads((d / "run_record.json").read_text())
    rec.pop("route", None)
    strip._replace(d / "run_record.json",
                   json.dumps(rec, indent=1, sort_keys=True) + "\n")
    from runio import Run
    res = verdict(Run(d), "VC-DRIVING-007")
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)
    assert res.measured["recount_done"] is False
    assert res.measured["route_sha_source"] == "route_announcement.routeSha256"


# ------------------------------------------------------------- image sizes
def test_front_hi_res_at_512_fails_vc003(run_for, tmp_path):
    d = copied(run_for, tmp_path, "hi-res-512")
    state = {"done": False}

    def fn(data):
        if not state["done"] and data.get("primed"):     # a plan step
            for c in data["cameras"]:
                if c.get("name") in ("front", "cam_front"):
                    c["front_hi_res"] = {"width": 512, "height": 512}
                    state["done"] = True
                    break
        return data
    assert _edit_c2(d, fn) == 1
    from runio import Run
    res = verdict(Run(d), "VC-DRIVING-003")
    assert res.outcome == cases.FAIL
