"""The DE4SDV visualization recorder in every run of mode full (the owner's decision of 2026-11-17: keep the recorder
in every run and state its delay), and the start-order text of the README.

- Patch 0001 (VIS8, score-interface/patches/0001-de4sdv-visualization-recorder.diff) switches the recorder on only
  when DE4SDV_VISUALIZATION_RECORD names the output video; unset or empty means off. Before this change the Launch
  Manager configuration never set it, so no run had a visualization recording.
- Lifecycle v0.10.0 starts a process with exactly its configured environment (no HOME, nothing inherited:
  test_launch_manager_environment.py). So the variable, and whatever GStreamer needs, are in vision_pilot's own
  environmental_variables, with fixed paths in the stage (the configuration is static).
- GStreamer's registry: without HOME, GLib falls back to the passwd entry's home (/root for uid 0), so the plugin scan
  would write into /root/.cache and read whatever an earlier check left there. GST_REGISTRY puts it in the stage,
  outside every folder the stop collects (run/, state/, config/, vision_pilot/).
- The path-only configuration is derived from this file and keeps every component (the identity recorder reads the
  candidate's launch settings from it); no run target of p10-1 or p10-3 starts vision_pilot, so the recorder never
  runs there.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parents[1]
CONFIG = BENCH / "launch-manager" / "config" / "launch_manager_config.json"
PATH_ONLY = BENCH / "score-path" / "config" / "launch_manager_config_path_only.json"
README = BENCH / "launch-manager" / "README.md"
STOP = BENCH / "score-path" / "scripts" / "stop_score_side.sh"
PATCH = BENCH / "score-interface" / "patches" / "0001-de4sdv-visualization-recorder.diff"
VIDEO = "/tmp/de4sdv-da-bench/run/visualization.mkv"
REGISTRY = "/tmp/de4sdv-da-bench/gst/registry.x86_64.bin"


def _env(path: Path, name: str) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    return config["components"][name].get("deployment_config", {}).get("environmental_variables", {})


def test_the_candidate_records_its_visualization_into_the_run_directory() -> None:
    env = _env(CONFIG, "vision_pilot")
    assert env.get("DE4SDV_VISUALIZATION_RECORD") == VIDEO
    # the patch's own name for the variable, and its own defaults kept (nvh264enc at 4000 kbit/s)
    assert "DE4SDV_VISUALIZATION_RECORD" in PATCH.read_text(encoding="utf-8")
    for key in ("DE4SDV_VISUALIZATION_ENCODER", "DE4SDV_VISUALIZATION_BITRATE_KBPS",
                "DE4SDV_VISUALIZATION_GST_ENCODER"):
        assert key not in env, key


def test_gstreamers_registry_lies_in_the_stage_outside_what_the_stop_collects() -> None:
    env = _env(CONFIG, "vision_pilot")
    assert env.get("GST_REGISTRY") == REGISTRY
    stop = STOP.read_text(encoding="utf-8")
    collected = set(re.findall(r'collect "\$DA_STAGE/([a-z_]+)', stop)) | {"vision_pilot"}
    assert REGISTRY.split("/")[3] not in collected, collected
    assert "HOME" not in env


def test_only_the_candidate_gets_the_recorder() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    for name in config["components"]:
        env = _env(CONFIG, name)
        if name != "vision_pilot":
            assert not [k for k in env if k.startswith(("DE4SDV_VISUALIZATION", "GST_"))], name
    assert not [k for k in config["defaults"]["deployment_config"]["environmental_variables"]
                if k.startswith(("DE4SDV_VISUALIZATION", "GST_"))]


def test_the_path_only_configuration_keeps_the_candidates_settings_and_starts_no_candidate() -> None:
    # derived verbatim (derive_path_only_config.py): the identity record of p10-1 and p10-3 shows the same launch
    # settings, and supervised_path, their only target, does not start vision_pilot
    assert _env(PATH_ONLY, "vision_pilot") == _env(CONFIG, "vision_pilot")
    path_only = json.loads(PATH_ONLY.read_text(encoding="utf-8"))
    assert "vision_pilot" not in path_only["run_targets"]["supervised_path"]["depends_on"]
    assert path_only["initial_run_target"] == "supervised_path"


def test_the_readme_states_the_start_order_of_a9384a0c() -> None:
    text = re.sub(r"\s+", " ", README.read_text(encoding="utf-8"))
    # since a9384a0c the candidate's process depends on the identity recorder only: it no longer starts after
    # someipd and gatewayd
    assert "someipd and gatewayd start before the candidate's process" not in text
    assert ("The candidate's process depends on the identity recorder only, so it can start before someipd and "
            "gatewayd") in text
    assert ("the start (`score-path/scripts/start_score_side.sh`) returns only once someipd and gatewayd run, the "
            "session writes the go only after it") in text


def test_the_readme_names_the_visualization_recording() -> None:
    text = re.sub(r"\s+", " ", README.read_text(encoding="utf-8"))
    assert "`DE4SDV_VISUALIZATION_RECORD` = `/tmp/de4sdv-da-bench/run/visualization.mkv`" in text
    assert "`GST_REGISTRY`" in text
