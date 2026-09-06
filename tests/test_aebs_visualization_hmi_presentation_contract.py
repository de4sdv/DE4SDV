"""Presentation-contract guards for the final INC-AEBS-010 public HMI.

These tests deliberately inspect maintained source artifacts. They protect the
human-facing claim boundary without duplicating reducer or SysML semantics.

Follow-up to merged PR #164: adds the presentation-scale contract (one
isotropic metre-per-pixel scene scale, fixture-true ego footprint, decorative
point glow), the diagnostic `Displayed obstacle range` row (never compared
with `rss_distance`), and the removal of the native-metrics boundary row.
"""
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "implementation/aebs-aaos-sdv-visualization-bench/aosp/vendor/de4sdv/aebs_visualization/app"
LAYOUT = APP / "res/layout/activity_main.xml"
STRINGS = APP / "res/values/strings.xml"
VIEW = APP / "src/org/de4sdv/aebsvisualization/ForwardSituationView.java"
ACTIVITY = APP / "src/org/de4sdv/aebsvisualization/MainActivity.java"
CONTRACT = ROOT / "implementation/aebs-aaos-sdv-visualization-bench/VISUALIZATION-CONTRACT.md"
ANDROID = "{http://schemas.android.com/apk/res/android}"


def _layout_nodes_by_id() -> dict[str, ET.Element]:
    tree = ET.parse(LAYOUT)
    result = {}
    for node in tree.iter():
        raw_id = node.attrib.get(ANDROID + "id", "")
        if raw_id.startswith("@+id/"):
            result[raw_id.removeprefix("@+id/")] = node
    return result


def _sp(node: ET.Element) -> int:
    value = node.attrib[ANDROID + "textSize"]
    assert value.endswith("sp")
    return int(value[:-2])


def test_real_window_insets_are_applied_to_named_root():
    nodes = _layout_nodes_by_id()
    root = nodes["root"]
    assert root.attrib[ANDROID + "fitsSystemWindows"] == "true"
    activity = ACTIVITY.read_text(encoding="utf-8")
    assert "setOnApplyWindowInsetsListener" in activity
    assert "getSystemWindowInsetTop" in activity
    assert "getSystemWindowInsetBottom" in activity


def test_state_is_dominant_and_health_is_secondary():
    nodes = _layout_nodes_by_id()
    current = nodes["state_current"]
    health = nodes["health_chip"]
    target = nodes["metric_obstacle_points"]
    assert _sp(current) >= 30
    assert _sp(current) > _sp(target) > _sp(health)
    assert current.attrib[ANDROID + "textStyle"] == "bold"
    activity = ACTIVITY.read_text(encoding="utf-8")
    assert "stateRowBackground(color, active)" in activity
    assert "GradientDrawable" in activity


def test_public_hmi_does_not_compare_cloud_range_with_native_rss():
    strings = STRINGS.read_text(encoding="utf-8")
    activity = ACTIVITY.read_text(encoding="utf-8")
    view = VIEW.read_text(encoding="utf-8")
    contract = CONTRACT.read_text(encoding="utf-8")
    assert "Filtered obstacle points" in strings
    # Native-metrics boundary row removed with PR #164's follow-up; the HMI
    # shows the diagnostic displayed range instead and names no native pair.
    assert "AEB decision distances not visualized" not in strings
    assert "Displayed obstacle range" in strings
    assert "filtered point cloud" in strings
    assert "Target range" not in strings
    assert "AEB braking threshold" not in strings
    assert "Native AEB decision metrics" not in strings + activity
    assert "getTargetRangeText" not in view
    assert "getRssDistanceText" not in view
    assert "isRssBoundaryVisible" not in view
    assert '"Target range  "' not in activity
    assert '"AEB braking threshold  "' not in activity
    # The displayed range is never bound next to the native RSS value.
    assert '"Displayed obstacle range  "' in activity
    assert "rss_distance" not in view
    assert "must not be presented as a comparable pair" in contract
    assert "purely temporal" in contract
    assert "collision_keeping_sec" in contract
    assert "sample-hold" in contract


def test_displayed_obstacle_range_is_diagnostic_only():
    activity = ACTIVITY.read_text(encoding="utf-8")
    strings = STRINGS.read_text(encoding="utf-8")
    contract = CONTRACT.read_text(encoding="utf-8")
    contract_flat = " ".join(contract.split())
    # Exact approved wording, one decimal metre precision.
    assert '"Displayed obstacle range  "' in activity
    assert "%.1f m" in activity
    assert "filtered point cloud" in strings
    # No RSS comparison, no threshold pair, no state/reducer influence: no
    # CODE-level rss_distance reference exists in the activity (comments only).
    code_only = "\n".join(
        line.split("//", 1)[0] for line in activity.splitlines())
    assert code_only.count("rss_distance") == 0
    assert "setRssDistance(null)" in activity
    # Contract documents the diagnostic boundary explicitly.
    assert "Displayed obstacle range" in contract
    assert "NOT a native Autoware AEB decision distance" in contract_flat


def test_ego_and_filtered_point_roles_remain_distinct_without_distance_pill():
    source = VIEW.read_text(encoding="utf-8")
    assert 'canvas.drawText("EGO"' in source
    assert "Filtered obstacle cluster" in source
    assert '"OBSTACLE  "' not in source
    assert "drawClosestPointMarker" not in source


def test_ego_uses_true_fixture_footprint_without_presentation_enlargement():
    view = VIEW.read_text(encoding="utf-8")
    geometry = (APP / "src/org/de4sdv/aebsvisualization/SituationSceneGeometry.java").read_text(
        encoding="utf-8")
    model = (APP / "src/org/de4sdv/aebsvisualization/SituationRenderModel.java").read_text(
        encoding="utf-8")
    contract = CONTRACT.read_text(encoding="utf-8")
    contract_flat = " ".join(contract.split())
    # Fixture dimensions are owned by the pure render model; the scene
    # geometry projects them and the view consumes that projection with no
    # presentation multiplier.
    assert "EGO_FRONT_M = 3.74f" in model
    assert "EGO_REAR_M = 1.03f" in model
    assert "EGO_WIDTH_M = 1.83f" in model
    assert "SituationRenderModel.EGO_FRONT_M" in geometry
    # Both longitudinal bounds are fixture-true: full rear, unshortened by
    # any presentation factor (defect: bottom = originY + rear * 0.4).
    assert "originY + carRear," in geometry
    assert "0.4f" not in geometry
    assert "0.4f" not in view
    assert "egoFootprintRectPx" in view
    assert not re.search(r"EGO_\w+\s*/\s*mPerPx\s*\)\s*\*\s*\d", view), \
        "ego footprint must not be scaled by a presentation multiplier"
    # One isotropic metre-per-pixel factor: the lateral projection divides by
    # the same geometry factor used for the footprint conversion.
    assert "return g[0] + metres / g[4];" in view
    assert "metresPerPx = MAX_RANGE_M / usableHeight" in geometry
    # Contract states the single-scale and no-enlargement rules.
    assert "one consistent metre-per-pixel scale" in contract_flat
    assert "isotropic" in contract_flat


def test_no_circular_ego_halo_remains():
    view = VIEW.read_text(encoding="utf-8")
    # The former circular emphasis halo is removed: a circle cannot stay
    # inside the projected fixture-true footprint (width ~14 px at 1080x600),
    # so any glow beyond the footprint boundary read as false visual contact
    # (contract §13.1). Containment is pinned behaviorally on the JVM by
    # SituationSceneGeometryTest (projected bounds, not source strings).
    assert "egoHaloPaint" not in view
    assert "drawCircle(g[0]" not in view
    # Dead-wiring recurrence guard (round-1 review): the view must actually
    # instantiate the geometry class, not call its methods on a float[].
    assert "new SituationSceneGeometry(" in view


def test_point_glow_is_decorative_and_small():
    view = VIEW.read_text(encoding="utf-8")
    contract = CONTRACT.read_text(encoding="utf-8")
    assert "POINT_GLOW_PX = 6f" in view
    assert "POINT_CORE_PX = 3.5f" in view
    # No oversized legacy glow radii remain in the cluster path.
    assert "drawCircle(px, py, 11f" not in view
    assert "drawCircle(px, py, 5f" not in view
    assert "visual decoration" in contract
    assert "does not represent physical extent" in contract


def test_ego_label_has_clearance_from_silhouette_boundary():
    view = VIEW.read_text(encoding="utf-8")
    geometry = (APP / "src/org/de4sdv/aebsvisualization/SituationSceneGeometry.java").read_text(
        encoding="utf-8")
    assert "EGO_LABEL_CLEARANCE_PX = 5f" in geometry
    # Label placement goes through the geometry helper with the actual glyph
    # ascent from the label paint's font bounds (getTextBounds).
    assert "egoLabelBaselinePx" in view
    assert "getTextBounds" in view
    # No dark-on-light inside-the-body label rendering remains.
    assert "egoLabel.setColor(COLOR_BASE)" not in view


def test_stale_invalid_unavailable_clear_displayed_range():
    activity = ACTIVITY.read_text(encoding="utf-8")
    # All three degraded dispositions clear the displayed range in the same
    # fail-closed block that clears the scene geometry.
    block = activity.split("private void renderDisposition", 1)[1]
    block = block.split("private void renderStatePanel", 1)[0]
    for state in ("STALE", "INVALID", "UNAVAILABLE"):
        assert state in block
    assert "initial_displayed_obstacle_range" in block
    assert "clearTrail()" in block


def test_provenance_and_read_only_boundary_remain_publicly_visible():
    strings = STRINGS.read_text(encoding="utf-8")
    assert "SIMULATED POINT CLOUD" in strings
    assert "Read-only engineering visualization · issues no vehicle commands" in strings
    nodes = _layout_nodes_by_id()
    assert _sp(nodes["health_chip"]) >= 16
    assert _sp(nodes["provenance"]) >= 16
    assert _sp(nodes["disposition"]) >= 15


def test_no_unsupported_scene_semantics_are_added():
    public_text = (VIEW.read_text(encoding="utf-8") + STRINGS.read_text(encoding="utf-8")).lower()
    for forbidden in ("lane marking", "field of view", "radar sweep", "time to collision", "ttc", "predicted trajectory", "confidence"):
        assert forbidden not in public_text
