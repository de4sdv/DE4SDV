"""Presentation-contract guards for the final INC-AEBS-010 public HMI.

These tests deliberately inspect maintained source artifacts. They protect the
human-facing claim boundary without duplicating reducer or SysML semantics.
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
    assert "AEB decision distances not visualized" in strings
    assert "Target range" not in strings
    assert "AEB braking threshold" not in strings
    assert "getTargetRangeText" not in view
    assert "getRssDistanceText" not in view
    assert "isRssBoundaryVisible" not in view
    assert '"Target range  "' not in activity
    assert '"AEB braking threshold  "' not in activity
    assert "must not be presented as a comparable pair" in contract
    assert "purely temporal" in contract
    assert "collision_keeping_sec" in contract
    assert "sample-hold" in contract


def test_ego_and_filtered_point_roles_remain_distinct_without_distance_pill():
    source = VIEW.read_text(encoding="utf-8")
    assert 'canvas.drawText("EGO"' in source
    assert "Filtered obstacle cluster" in source
    assert '"OBSTACLE  "' not in source
    assert "drawClosestPointMarker" not in source


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
