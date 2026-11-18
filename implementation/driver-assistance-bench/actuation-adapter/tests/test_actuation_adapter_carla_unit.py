"""Static checks of the parts the host cannot build: the CARLA 1.0 client unit and the S-CORE main.

simulator_client_carla.cpp needs LibCarla, which only the B2 S-CORE workspace has, so its rules are
checked on its text: no autopilot, Ackermann control only, no tick, CARLA headers only in that unit,
the C++20 guard, named lists in range-for loops. actuation_adapter_main.cpp is compiled for syntax
against the closed-loop bench's local mw::com mock (a mock, NOT S-CORE; the real API is checked only
by the B2 build).
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ADAPTER = Path(__file__).resolve().parents[1]
BENCH = ADAPTER.parent
UNIT = ADAPTER / "simulator_client_carla.cpp"
MAIN = ADAPTER / "actuation_adapter_main.cpp"
MWCOM_MOCK = (BENCH.parent / "closed-loop-driving-bench" / "state-publisher" / "tests" / "mock")


def strip_comments_and_strings(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), src, flags=re.S)
    src = re.sub(r"//[^\n]*", "", src)
    return re.sub(r'"(?:\\.|[^"\\\n])*"', '""', src)


def range_over_dereferenced_call(src: str) -> list[tuple[int, str]]:
    """Range-based for loops whose range dereferences a call result.

    The checker of the closed-loop bench's actuation adapter
    (implementation/closed-loop-driving-bench/actuation-adapter/tests/test_libcarla_shell.py).
    """
    code = strip_comments_and_strings(src)
    found = []
    for m in re.finditer(r"\bfor\s*\(", code):
        depth, j = 1, m.end()
        while j < len(code) and depth:
            depth += {"(": 1, ")": -1}.get(code[j], 0)
            j += 1
        header = code[m.end():j - 1]
        depth, colon = 0, None
        for k, c in enumerate(header):
            if c in "([{":
                depth += 1
            elif c in ")]}":
                depth -= 1
            elif c == ":" and depth == 0 and header[k - 1:k] != ":" and header[k + 1:k + 2] != ":":
                colon = k
                break
        if colon is None:
            continue
        rng = header[colon + 1:].strip()
        if rng.startswith("*") and "(" in rng:
            found.append((code.count("\n", 0, m.start()) + 1, rng))
    return found


def sources() -> dict[str, str]:
    files = sorted(ADAPTER.glob("*.cpp")) + sorted(ADAPTER.glob("*.h"))
    assert UNIT in files and MAIN in files
    return {p.name: strip_comments_and_strings(p.read_text(encoding="utf-8")) for p in files}


def test_the_checker_flags_only_dereferenced_temporaries() -> None:
    # The cases of the closed-loop bench's checker.
    assert range_over_dereferenced_call('for (const auto& a : *actors->Filter("vehicle.*")) {}')
    assert range_over_dereferenced_call("for (auto& a : *world.GetActors()) {}")
    assert not range_over_dereferenced_call("for (const auto& a : *vehicles) {}")
    assert not range_over_dereferenced_call("for (auto it = l->begin(); it != l->end(); ++it) {}")
    assert not range_over_dereferenced_call("for (const std::pair<int, int>& p : m) {}")
    assert not range_over_dereferenced_call("for (std::map<int, int>::iterator it = m.begin(); ;) {}")
    assert not range_over_dereferenced_call('// for (auto& a : *x->Filter("v")) {}')


def test_no_loop_iterates_a_dereferenced_temporary() -> None:
    bad = {name: hits for name, src in sources().items()
           if (hits := range_over_dereferenced_call(src))}
    assert not bad, bad


def test_the_autopilot_is_never_set() -> None:
    hits = [name for name, code in sources().items() if re.search(r"Autopilot", code)]
    assert not hits, hits


def test_only_the_ackermann_control_is_applied() -> None:
    for name, code in sources().items():
        assert not re.search(r"\bApplyControl\s*\(", code), name
        assert not re.search(r"\bVehicleControl\b", code), name
        assert not re.search(r"\b(SetSimulatePhysics|SetTargetVelocity|SetTransform|"
                             r"EnableConstantVelocity|AddImpulse|ApplyPhysicsControl)\b", code), name
    unit = sources()[UNIT.name]
    assert len(re.findall(r"->ApplyAckermannControl\(", unit)) == 1


def test_the_unit_never_ticks_the_world() -> None:
    assert not re.search(r"\bTick\s*\(", sources()[UNIT.name])


def test_the_unit_sets_the_five_fields_from_the_control() -> None:
    unit = sources()[UNIT.name]
    for carla_field, ours in [("steer", "steer"), ("steer_speed", "steerSpeed"), ("speed", "speed"),
                              ("acceleration", "acceleration"), ("jerk", "jerk")]:
        assert re.search(rf"ackermann\.{carla_field} = control\.{ours};", unit), carla_field


def test_the_unit_reads_time_and_speed_from_the_snapshot() -> None:
    unit = sources()[UNIT.name]
    assert "snapshot.GetTimestamp().elapsed_seconds" in unit
    assert "snapshot.Find(heroId)" in unit
    assert "Length(ego->velocity)" in unit


def test_carla_headers_only_in_the_unit() -> None:
    for path in sorted(ADAPTER.glob("*.cpp")) + sorted(ADAPTER.glob("*.h")):
        has_carla = re.search(r"#include\s*<carla/", path.read_text(encoding="utf-8"))
        assert bool(has_carla) == (path == UNIT), path.name


def test_the_unit_refuses_to_build_below_cpp20() -> None:
    text = UNIT.read_text(encoding="utf-8")
    assert re.search(r"#if __cplusplus < 202002L\n#error ", text)


def test_bazel_builds_the_unit_as_cpp20_and_the_rest_at_the_default() -> None:
    build = (ADAPTER / "BUILD.bazel").read_text(encoding="utf-8")
    unit = re.search(r'cc_library\(\s*name = "simulator_client_carla",(.*?)\n\)', build, re.S)
    assert unit, "no simulator_client_carla target"
    assert '"simulator_client_carla.cpp"' in unit.group(1)
    assert 'copts = ["-std=c++20"]' in unit.group(1)
    assert build.count("-std=c++20") == 1


def test_main_compiles_for_syntax_against_the_mwcom_mock(tmp_path: Path) -> None:
    compiler = shutil.which("g++")
    if compiler is None:
        pytest.skip("g++ is not installed")
    assert (MWCOM_MOCK / "score" / "mw" / "com" / "types.h").is_file()
    subprocess.run(
        [str(compiler), "-std=c++17", "-Wall", "-Wextra", "-Werror", "-fsyntax-only",
         "-isystem", str(MWCOM_MOCK), f"-I{ADAPTER}", f"-I{BENCH / 'interfaces' / 'include'}",
         str(MAIN)],
        check=True, cwd=tmp_path,
    )


def test_lifecycle_client_compiles_for_syntax_against_the_api_declarations(tmp_path: Path) -> None:
    """lifecycle_client_score.cpp against the Lifecycle v0.10.0 API as ../launch-manager/tests/lifecycle_mock
    declares it; the real compile is the S-CORE Bazel build's."""
    compiler = shutil.which("g++")
    if compiler is None:
        pytest.skip("g++ is not installed")
    mock = BENCH / "launch-manager" / "tests" / "lifecycle_mock"
    assert (mock / "score" / "mw" / "lifecycle" / "alive.h").is_file()
    subprocess.run(
        [str(compiler), "-std=c++17", "-Wall", "-Wextra", "-Werror", "-pedantic", "-fsyntax-only",
         "-isystem", str(mock), f"-I{ADAPTER}", f"-I{BENCH / 'interfaces' / 'include'}",
         str(ADAPTER / "lifecycle_client_score.cpp")],
        check=True, cwd=tmp_path,
    )
