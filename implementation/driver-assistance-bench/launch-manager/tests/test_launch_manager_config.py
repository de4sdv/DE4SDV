"""The Launch Manager configuration of the S-CORE host (launch-manager/config/launch_manager_config.json).

What is pinned:
- the format of S-CORE Lifecycle v0.10.0 (schema_version 2) and the rule of its v0.10.0 converter that every run
  target's switch_run_target names fallback_run_target (scripts/config_mapping/lifecycle_config.py, read at
  2afae116);
- the supervision decision of 2026-11-18: alive supervision of exactly the candidate's process and the actuation
  adapter, recovery to a target without both, nothing else supervised;
- the alive supervision values: equal to the README's table and derived from the 0.1 s cycle by the README's rules;
- the start order of the phase 8 model's Launch Manager: the identity recorder first, then the candidate's process
  and the actuation adapter; someipd before gatewayd before the candidate's process;
- the alive supervision's behavior for these values, by a re-implementation in Python of the evaluation of
  Alive.cpp at v0.10.0 (score/launch_manager/src/daemon/src/alive_monitor/details/supervision/Alive.cpp:202-255,
  362-436, 544-552): a single slow cycle up to 0.4 s never trips it, a gap of 0.6 s always does. This is this test's
  reading of upstream's code, not upstream's code; the S-CORE build probe of phase 10 shows the real one.

With LIFECYCLE_SRC set to a checkout of eclipse-score/lifecycle at v0.10.0, the upstream converter also validates
the file against its schema and converts it; otherwise that test is skipped with the reason.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
LM = HERE.parent
BENCH = LM.parent
CONFIG = LM / "config" / "launch_manager_config.json"
README = LM / "README.md"

SUPERVISED = {"vision_pilot", "actuation_adapter"}
CYCLE_MS = 100  # one image, one plan, one command per 0.1 s of simulation time, paced at wall-clock pace


def load() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def component_property(config: dict, name: str, key: str):
    own = config["components"][name].get("component_properties", {})
    if key in own:
        return own[key]
    return config["defaults"]["component_properties"].get(key)


def app_type(config: dict, name: str) -> str:
    own = config["components"][name].get("component_properties", {}).get("application_profile", {})
    return own.get("application_type", config["defaults"]["component_properties"]["application_profile"]["application_type"])


def deployment(config: dict, name: str, key: str):
    own = config["components"][name].get("deployment_config", {})
    return own.get(key, config["defaults"]["deployment_config"].get(key))


def closure(config: dict, names: list[str]) -> set[str]:
    """The components a list of dependencies activates: run targets expand, components pull their depends_on."""
    out: set[str] = set()
    stack = list(names)
    while stack:
        name = stack.pop()
        if name in config["run_targets"]:
            stack.extend(config["run_targets"][name].get("depends_on", []))
        elif name in config["components"]:
            if name not in out:
                out.add(name)
                stack.extend(component_property(config, name, "depends_on") or [])
        else:
            raise AssertionError(f"unknown dependency {name}")
    return out


def readme_values() -> dict[str, int]:
    """The alive supervision table of the README: | `key` | value | ... |."""
    values: dict[str, int] = {}
    for line in README.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*`(reporting_cycle_ms|failed_cycles_tolerance|min_indications|max_indications|"
                     r"evaluation_cycle_ms)`\s*\|\s*(\d+)\s*\|", line)
        if m:
            assert m.group(1) not in values, f"{m.group(1)} twice in the README"
            values[m.group(1)] = int(m.group(2))
    return values


# ── format and recovery ─────────────────────────────────────────────────────────────────────────────────────────

def test_format_of_lifecycle_v0_10_0() -> None:
    config = load()
    assert config["schema_version"] == 2
    assert set(config) == {"schema_version", "defaults", "components", "run_targets", "initial_run_target",
                           "fallback_run_target", "alive_supervision"}
    assert config["initial_run_target"] in config["run_targets"]
    assert "fallback_run_target" not in config["run_targets"]  # a reserved name at v0.10.0
    assert not set(config["components"]) & set(config["run_targets"])


def test_every_recovery_switches_to_the_fallback_run_target() -> None:
    config = load()
    for name, target in config["run_targets"].items():
        assert target["recovery_action"] == {"switch_run_target": {"run_target": "fallback_run_target"}}, name
    for name in config["components"]:
        assert deployment(config, name, "recovery_action") == {
            "switch_run_target": {"run_target": "fallback_run_target"}}, name
    assert "recovery_action" not in config["fallback_run_target"]


def test_the_recovery_target_excludes_the_candidate_and_the_adapter() -> None:
    config = load()
    fallback = closure(config, config["fallback_run_target"]["depends_on"])
    assert fallback == {"identity_recorder", "someipd", "gatewayd"}
    assert not fallback & SUPERVISED
    initial = closure(config, [config["initial_run_target"]])
    assert initial == set(config["components"])
    assert fallback < initial


# ── supervision ─────────────────────────────────────────────────────────────────────────────────────────────────

def test_exactly_the_candidate_and_the_adapter_are_supervised() -> None:
    config = load()
    supervised = {n for n in config["components"] if app_type(config, n) in {"Reporting_And_Supervised",
                                                                            "State_Manager"}}
    assert supervised == SUPERVISED
    for name in config["components"]:
        profile = config["components"][name].get("component_properties", {}).get("application_profile", {})
        assert ("alive_supervision" in profile) == (name in SUPERVISED), name
        assert app_type(config, name) != "State_Manager", name  # nothing may switch the run target
    assert "alive_supervision" not in config["defaults"]["component_properties"]["application_profile"]


def test_the_values_equal_the_readme_and_follow_from_the_cycle() -> None:
    config = load()
    stated = readme_values()
    assert set(stated) == {"reporting_cycle_ms", "failed_cycles_tolerance", "min_indications", "max_indications",
                           "evaluation_cycle_ms"}
    # the README's rules: a window of two cycles, at least one notification in it, at most three times the
    # nominal two, one failed window tolerated, evaluated every half window
    assert stated["reporting_cycle_ms"] == 2 * CYCLE_MS
    assert stated["min_indications"] == 1
    assert stated["max_indications"] == 3 * (stated["reporting_cycle_ms"] // CYCLE_MS)
    assert stated["failed_cycles_tolerance"] == 1
    assert stated["evaluation_cycle_ms"] == stated["reporting_cycle_ms"] // 2
    for name in SUPERVISED:
        alive = config["components"][name]["component_properties"]["application_profile"]["alive_supervision"]
        assert alive == {k: stated[k] for k in ("reporting_cycle_ms", "failed_cycles_tolerance", "min_indications",
                                                "max_indications")}, name
    assert config["alive_supervision"] == {"evaluation_cycle_ms": stated["evaluation_cycle_ms"]}


def test_the_ready_timeouts_cover_the_start() -> None:
    """The candidate reports running after its first pass with a result: its ready timeout covers the attach to the
    hero (carla.attach_timeout_s, 300 s by default in seams.hpp), the network sessions and the first inference; the
    run target's transition covers the longest ready timeout."""
    config = load()
    seams = (BENCH / "score-interface" / "module" / "include" / "de4sdv" / "score_interface" / "seams.hpp")
    found = re.search(r"double attach_timeout_s = ([0-9.]+);", seams.read_text(encoding="utf-8"))
    assert found, "no attach_timeout_s default in seams.hpp"
    attach_s = float(found.group(1))
    assert deployment(config, "vision_pilot", "ready_timeout_ms") >= attach_s * 1000 + 60000
    longest = max(deployment(config, n, "ready_timeout_ms") for n in config["components"])
    assert config["run_targets"][config["initial_run_target"]]["transition_timeout_ms"] > longest


# ── start order ─────────────────────────────────────────────────────────────────────────────────────────────────

def test_start_order_of_the_phase_8_launch_manager() -> None:
    config = load()

    def deps(name: str) -> set[str]:
        return closure(config, component_property(config, name, "depends_on") or [])

    assert deps("identity_recorder") == set()  # first
    assert "identity_recorder" in deps("vision_pilot")
    assert "identity_recorder" in deps("actuation_adapter")
    assert {"someipd", "gatewayd"} <= deps("vision_pilot")  # the warning path is up before the first warning
    assert deps("gatewayd") == {"someipd"}
    # the adapter does not wait for the candidate: it finds the command service itself, and so it subscribes
    # before the candidate's first command, which needs the network sessions and the first inference
    assert "vision_pilot" not in deps("actuation_adapter")
    assert "actuation_adapter" not in deps("vision_pilot")
    # the recorder is ready only once it reports running (the record written and offered)
    assert app_type(config, "identity_recorder") == "Reporting"
    for name in config["components"]:
        assert name not in deps(name), f"cycle at {name}"


# ── files the configuration names ───────────────────────────────────────────────────────────────────────────────

REPO_FILES = {
    "mw_com_config_someipd_warning.json": BENCH / "score-path" / "config",
    "vsomeip_someipd_warning.json": BENCH / "score-path" / "config",
    "mw_com_config_gatewayd_warning.json": BENCH / "score-path" / "config",
    "mw_com_config_actuation_adapter.json": BENCH / "actuation-adapter",
    "adapter.json": BENCH / "actuation-adapter" / "config",
}
# Named by the configuration, made elsewhere: the gateway config binary (score-path/config's Bazel overlay), the
# recorder's manifest (the identity recorder's item) and the interface settings (the session's staging).
STAGED_ELSEWHERE = {"someip_gateway_config_warning.bin", "mw_com_config_identity_recorder.json",
                    "de4sdv_score_interface.conf"}


def test_every_config_file_named_is_in_the_repo_or_listed() -> None:
    config = load()
    text = json.dumps(config)
    named = set(re.findall(r"/tmp/de4sdv-da-bench/config/([A-Za-z0-9_.-]+)", text))
    assert named == set(REPO_FILES) | STAGED_ELSEWHERE
    for name, folder in REPO_FILES.items():
        assert (folder / name).is_file(), name
    # the candidate's manifest is named by the interface settings, not by the Launch Manager
    assert (BENCH / "score-path" / "config" / "mw_com_config_vision_pilot.json").is_file()


# ── the alive supervision, as Alive.cpp at v0.10.0 evaluates it ─────────────────────────────────────────────────

def expires(notifications_ms: list[float], end_ms: float, alive: dict) -> bool:
    """True when the supervision expires (the Launch Manager kills the process). Activation at 0 ms, the first
    window [0, cycle], each later window (start, start + cycle]; a notification at a window's end counts in it."""
    cycle = alive["reporting_cycle_ms"]
    lo, hi, tolerance = alive["min_indications"], alive["max_indications"], alive["failed_cycles_tolerance"]
    status, failed, start = "ok", 0, 0.0
    while start + cycle <= end_ms:
        end = start + cycle
        count = sum(1 for t in notifications_ms if (start < t <= end) or (start == 0.0 and t == 0.0))
        error = (lo != 0 and count < lo) or (hi != 0 and count > hi)
        if status == "ok":
            if error:
                if failed < tolerance:
                    status, failed = "failed", failed + 1
                else:
                    return True
        else:  # failed
            if error:
                failed += 1
                if failed > tolerance:
                    return True
            elif failed <= 1:
                status, failed = "ok", 0
            else:
                failed -= 1
        start = end
    return False


def cycles(durations_ms: list[float], first_ms: float = 0.0) -> list[float]:
    """The times of the alive notifications of passes of the given durations."""
    out, t = [], first_ms
    for d in durations_ms:
        t += d
        out.append(t)
    return out


def alive_values() -> dict:
    return load()["components"]["vision_pilot"]["component_properties"]["application_profile"]["alive_supervision"]


def test_the_nominal_cycle_never_trips() -> None:
    alive = alive_values()
    # 60 s of 0.1 s cycles; the notification at the end of each pass, 35 to 65 ms after its image (VIS8's p99 of
    # 65 ms with the recorder), the images 100 ms apart
    pattern = [35, 65, 41, 50, 65, 38, 44]
    times = [k * CYCLE_MS + pattern[k % len(pattern)] for k in range(600)]
    assert not expires([0.0, *times], times[-1], alive)


@pytest.mark.parametrize("phase_ms", range(0, 200, 10))
def test_a_single_slow_cycle_up_to_0_4_s_never_trips(phase_ms: int) -> None:
    alive = alive_values()
    before = cycles([CYCLE_MS] * 10, phase_ms)
    after = cycles([CYCLE_MS] * 20, before[-1] + 400)
    times = [0.0, *before, before[-1] + 400, *after]
    assert not expires(times, times[-1], alive)


@pytest.mark.parametrize("phase_ms", range(0, 200, 10))
def test_a_gap_of_0_6_s_always_trips(phase_ms: int) -> None:
    alive = alive_values()
    before = cycles([CYCLE_MS] * 10, phase_ms)
    times = [0.0, *before]
    assert expires(times, before[-1] + 600 + alive["reporting_cycle_ms"], alive)


def test_a_catch_up_after_a_stall_does_not_trip_the_maximum() -> None:
    alive = alive_values()
    # a 300 ms pass, then the waiting images handled back to back at 30 ms each, then the cycle again
    times = [0.0, *cycles([CYCLE_MS] * 10)]
    times += cycles([300, 30, 30, 30, 30, 30], times[-1])
    times += cycles([CYCLE_MS] * 20, times[-1])
    assert not expires(times, times[-1], alive)


def test_a_stop_of_the_notifications_trips() -> None:
    alive = alive_values()
    times = [0.0, *cycles([CYCLE_MS] * 30)]
    assert expires(times, times[-1] + 1000, alive)


# ── the upstream converter, when a checkout is given ────────────────────────────────────────────────────────────

def test_the_lifecycle_v0_10_0_converter_accepts_the_file(tmp_path: Path) -> None:
    source = os.environ.get("LIFECYCLE_SRC")
    if not source:
        pytest.skip("LIFECYCLE_SRC is not set to a checkout of eclipse-score/lifecycle at v0.10.0")
    try:
        import jsonschema  # noqa: F401  (the converter skips its schema validation without it)
    except ImportError:
        pytest.skip("jsonschema is not installed: the converter would skip its schema validation")
    converter = Path(source) / "scripts" / "config_mapping" / "lifecycle_config.py"
    schema = (Path(source) / "score" / "launch_manager" / "src" / "daemon" / "src" / "configuration"
              / "config_schema" / "launch_manager.schema.json")
    result = subprocess.run([sys.executable, str(converter), str(CONFIG), "-o", str(tmp_path), "--schema",
                             str(schema)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Schema Validation successful" in result.stdout
    generated = json.loads((tmp_path / "launch_manager_config_gen.json").read_text(encoding="utf-8"))
    assert {c["name"] for c in generated["components"]} == set(load()["components"])
