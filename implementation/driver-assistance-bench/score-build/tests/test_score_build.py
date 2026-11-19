"""Local checks of the S-CORE build of VisionPilot (INC-DRIVING-002, build item B2).

The Bazel build itself needs the x86_64 S-CORE toolchain and runs on the build VM. These tests check what can be
checked without it:

- the shell scripts parse (bash -n);
- every direct download goes through the sha256-checked fetch helper with a pinned sha256, every git source through
  the commit-checked helper with a pinned commit;
- the overlay BUILD file of VisionPilot names exactly the source files that upstream's CMake build compiles in the
  bench's configuration, plus those of the patch series, and each of them exists at the pin or in a patch;
- the workspace edits the build script makes find their anchors in the repository's FEO bench diff;
- the bundle contract: every path that score-path/scripts/stage_score_side.py requires, or reads when present, is
  produced by the bundle step (read statically from both scripts), each binary copied from Bazel's output is a target
  of the bazel stage in a staged package;
- the pinned GPU runtime covers every CUDA library that the pinned ONNX Runtime CUDA provider needs;
- C++ files that name fixed-width integer types include <cstdint>.

Upstream is read from a local clone of VisionPilot (VISIONPILOT_CLONE, default ~/de4sdv-upstream/vision_pilot) with
git show at the pin; without the clone those tests are skipped. The ONNX Runtime package check runs when the package
file is present (DA_B2_ORT_NUPKG).
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
BUILD_DIR = HERE.parent
BENCH = BUILD_DIR.parent
REPO = BENCH.parent.parent
SCRIPTS = ["build_score_bench.sh", "install_gpu_runtime.sh", "fallback_cmake_build.sh", "pins.sh"]
VP_BUILD = BUILD_DIR / "workspace" / "visionpilot.BUILD.bazel"
PATCHES = BENCH / "score-interface" / "patches"
PIN = "014e0e7a56ee8e597c2cab8175233f74edd9b856"
CLONE = Path(os.environ.get("VISIONPILOT_CLONE", Path.home() / "de4sdv-upstream" / "vision_pilot"))
ORT_NUPKG = Path(os.environ.get("DA_B2_ORT_NUPKG",
                                Path.home() / "de4sdv-upstream" / "nuget" / "ort-gpu-linux-1.26.0.nupkg"))


def pins() -> dict[str, str]:
    """The variables of pins.sh as bash sees them."""
    out = subprocess.run(
        ["bash", "-c", 'set -a; source "$1"; set +a; env -0', "_", str(BUILD_DIR / "pins.sh")],
        check=True, capture_output=True, env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
    ).stdout.decode()
    return dict(item.split("=", 1) for item in out.split("\0") if "=" in item)


def archive_rows(text: str) -> list[list[str]]:
    return [line.split("|") for line in text.strip().splitlines() if line.strip()]


def have_clone() -> bool:
    if shutil.which("git") is None or not (CLONE / ".git").exists():
        return False
    return subprocess.run(["git", "-C", str(CLONE), "cat-file", "-e", PIN], capture_output=True).returncode == 0


def upstream(path: str) -> str:
    return subprocess.run(["git", "-C", str(CLONE), "show", f"{PIN}:VisionPilot/{path}"],
                          check=True, capture_output=True, text=True).stdout


def upstream_exists(path: str) -> bool:
    return subprocess.run(["git", "-C", str(CLONE), "cat-file", "-e", f"{PIN}:VisionPilot/{path}"],
                          capture_output=True).returncode == 0


def patch_added_files() -> dict[str, str]:
    """Files the patch series creates, with their content."""
    files: dict[str, str] = {}
    for patch in sorted(PATCHES.glob("*.diff")):
        current = None
        lines: list[str] = []
        new_file = False
        for line in patch.read_text().splitlines():
            if line.startswith("diff --git"):
                if current and new_file:
                    files[current] = "\n".join(lines)
                current, lines, new_file = None, [], False
            elif line.startswith("--- /dev/null"):
                new_file = True
            elif line.startswith("+++ b/VisionPilot/"):
                current = line[len("+++ b/VisionPilot/"):]
            elif current and line.startswith("+"):
                lines.append(line[1:])
        if current and new_file:
            files[current] = "\n".join(lines)
    return files


# Conditions of upstream's CMake files that are off in the bench's configuration (CMake options of the build).
OFF_CONDITIONS = ("BUILD_TESTING", "ENABLE_OCCUPANCY", "ENABLE_ROS2_INTERFACE")


def cmake_sources(text: str, module_dir: str) -> set[str]:
    """The .cpp files a CMakeLists.txt compiles with the bench's options, as paths under VisionPilot/."""
    text = "\n".join(line.split("#", 1)[0] for line in text.splitlines())
    sources: set[str] = set()
    skip_depth = 0
    depth = 0
    for match in re.finditer(r"(\w+)\s*\(([^()]*(?:\([^()]*\)[^()]*)*)\)", text, flags=re.S):
        command, args = match.group(1).lower(), match.group(2)
        if command == "if":
            depth += 1
            if skip_depth == 0 and any(c in args for c in OFF_CONDITIONS):
                skip_depth = depth
            continue
        if command == "endif":
            if skip_depth == depth:
                skip_depth = 0
            depth -= 1
            continue
        if skip_depth:
            continue
        if command in ("add_library", "add_executable", "target_sources", "list"):
            for token in args.split():
                if token.endswith(".cpp"):
                    sources.add(os.path.normpath(os.path.join(module_dir, token)))
    return sources


def top_level_subdirectories(text: str) -> list[str]:
    dirs = []
    skip = False
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if line.lower().startswith("if"):
            skip = any(c in line for c in OFF_CONDITIONS)
        elif line.lower().startswith("endif"):
            skip = False
        elif not skip:
            m = re.match(r"add_subdirectory\(\s*([^\s)]+)", line)
            if m:
                dirs.append(m.group(1))
    return dirs


def build_sources() -> set[str]:
    return set(re.findall(r'"((?:app|modules)/[^"]+\.cpp)"', VP_BUILD.read_text()))


def binding_units(added: dict[str, str]) -> set[str]:
    """The .cpp files patch 0002 adds to the score_interface module that its own CMakeLists.txt does not compile."""
    d = "modules/de4sdv/score_interface"
    patched = {p for p in added if p.startswith(f"{d}/src/") and p.endswith(".cpp")}
    return patched - cmake_sources(added[f"{d}/CMakeLists.txt"], d)


# ---------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("script", SCRIPTS)
def test_shell_scripts_parse(script: str) -> None:
    result = subprocess.run(["bash", "-n", str(BUILD_DIR / script)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_pins_are_well_formed() -> None:
    p = pins()
    shas = {k: v for k, v in p.items() if k.endswith("_SHA256")}
    assert len(shas) >= 12
    for key, value in shas.items():
        assert re.fullmatch(r"[0-9a-f]{64}", value), key
    commits = {k: v for k, v in p.items() if k.endswith("_COMMIT")}
    assert set(commits) == {"VP_COMMIT", "FEO_COMMIT", "GATEWAY_COMMIT", "CARLA_COMMIT"}
    for key, value in commits.items():
        assert re.fullmatch(r"[0-9a-f]{40}", value), key
    assert p["VP_COMMIT"] == PIN
    assert p["CARLA_COMMIT"].startswith("14ac3b1a50")
    assert p["GATEWAY_COMMIT"].startswith("d9eac670")
    assert p["FEO_COMMIT"].startswith("313b3d84")
    for row in archive_rows(p["CUDA_ARCHIVES"]) + archive_rows(p["CUDNN_ARCHIVES"]):
        assert len(row) == 4, row
        name, rel, sha, size = row
        assert re.fullmatch(r"[0-9a-f]{64}", sha), name
        assert size.isdigit() and int(size) > 0, name
        assert rel.startswith(name + "/linux-x86_64/") and rel.endswith("-archive.tar.xz"), rel


def test_pinned_cuda_runtime_covers_the_providers_needs() -> None:
    p = pins()
    provider = {"libcudart": "cuda_cudart", "libcublas": "libcublas", "libcublasLt": "libcublas",
                "libcufft": "libcufft", "libcurand": "libcurand", "libcudnn": "cudnn"}
    names = {row[0]: row[1] for row in archive_rows(p["CUDA_ARCHIVES"]) + archive_rows(p["CUDNN_ARCHIVES"])}
    needed = p["ORT_CUDA_NEEDED"].split()
    assert len(needed) == 6
    for soname in needed:
        stem, major = soname.split(".so.")
        assert provider[stem] in names, soname
        # every CUDA library of the CUDA 12 major release (cuFFT 11 and cuRAND 10 ship with CUDA 12), cuDNN 9
        rel = names[provider[stem]]
        if stem == "libcudnn":
            assert major == "9" and "_cuda12-archive" in rel
        elif stem in ("libcudart", "libcublas", "libcublasLt"):
            assert major == "12" and re.search(r"-12\.8\.", rel), rel
    assert p["CUDA_VERSION"].startswith("12.8")


def _function_body(text: str, name: str) -> str:
    start = text.index(f"{name}() {{")
    end = text.index("\n}\n", start)
    return text[start:end]


@pytest.mark.parametrize("script", ["build_score_bench.sh", "install_gpu_runtime.sh", "fallback_cmake_build.sh"])
def test_every_download_is_pinned_by_sha256(script: str) -> None:
    text = (BUILD_DIR / script).read_text()
    assert "wget" not in text
    curl_lines = [line for line in text.splitlines() if re.search(r"\bcurl\b", line) and not line.lstrip().startswith("#")]
    if script == "fallback_cmake_build.sh":
        assert not curl_lines  # it downloads nothing of its own
        return
    body = _function_body(text, "fetch")
    for line in curl_lines:
        assert line in body, f"curl outside the sha256-checked fetch helper: {line}"
    assert 'sha256sum -c --quiet' in body
    calls = [line.strip() for line in text.splitlines() if re.match(r"\s*fetch\s", line)]
    assert calls
    for call in calls:
        args = re.findall(r'"\$\([^)]*\)"|"[^"]*"|\S+', call)[1:]
        assert len(args) >= 3, call
        assert re.fullmatch(r'"?\$(\{)?[A-Z_]*SHA256(\})?"?|"\$sha"', args[2]), call


def test_every_git_source_is_pinned_by_commit() -> None:
    text = (BUILD_DIR / "build_score_bench.sh").read_text()
    calls = re.findall(r"^git_at (.+)$", text, flags=re.M)
    assert len(calls) == 4
    for call in calls:
        assert re.search(r'"\$[A-Z]+_URL" "\$[A-Z]+_COMMIT"$', call), call
    body = _function_body(text, "git_at")
    assert 'rev-parse HEAD)" = "$commit"' in body
    # the only clones are local and shared
    for line in text.splitlines():
        if "git clone" in line:
            assert "--shared" in line, line


@pytest.mark.skipif(not have_clone(), reason="no VisionPilot clone holding the pin (VISIONPILOT_CLONE)")
def test_overlay_names_exactly_the_cmake_sources() -> None:
    expected: set[str] = set()
    top = upstream("CMakeLists.txt")
    subdirs = top_level_subdirectories(top)
    assert "modules/visualization" in subdirs and "app" in subdirs
    assert not any("ros2" in d for d in subdirs)
    for d in subdirs:
        expected |= cmake_sources(upstream(f"{d}/CMakeLists.txt"), d)
    # the patch series: two modules added by add_subdirectory in the top-level CMakeLists.txt
    p1 = (PATCHES / "0001-de4sdv-visualization-recorder.diff").read_text()
    p2 = (PATCHES / "0002-de4sdv-score-interface.diff").read_text()
    assert "+add_subdirectory(modules/de4sdv/visualization_recorder)" in p1
    assert "+    add_subdirectory(modules/de4sdv/score_interface)" in p2
    added = patch_added_files()
    for d in ("modules/de4sdv/visualization_recorder", "modules/de4sdv/score_interface"):
        expected |= cmake_sources(added[f"{d}/CMakeLists.txt"], d)
    # DE4SDV_SCORE_BINDINGS of 0002: the binding units the patch adds beside its CMake sources, which only the S-CORE
    # build compiles (mw::com, the CARLA 1.0 client, S-CORE Lifecycle)
    bindings = binding_units(added)
    assert bindings == {"modules/de4sdv/score_interface/src/lola_bindings.cpp",
                        "modules/de4sdv/score_interface/src/carla_client.cpp",
                        "modules/de4sdv/score_interface/src/lifecycle_bindings.cpp"}
    expected |= bindings
    # what the bench configuration compiles, and what it leaves out
    assert "modules/visualization/src/webrtc_stream.cpp" in expected
    assert "modules/visualization/src/debug_display.cpp" not in expected
    assert "modules/models/src/trt_engine.cpp" not in expected
    assert build_sources() == expected


@pytest.mark.skipif(not have_clone(), reason="no VisionPilot clone holding the pin (VISIONPILOT_CLONE)")
def test_overlay_paths_exist_at_the_pin_or_in_a_patch() -> None:
    added = patch_added_files()
    text = VP_BUILD.read_text()
    for path in build_sources():
        assert upstream_exists(path) or path in added, path
    for inc in re.findall(r'"(modules/[^"*]+/include)"', text):
        has_header = any(a.startswith(inc + "/") for a in added)
        if not has_header:
            listing = subprocess.run(["git", "-C", str(CLONE), "ls-tree", "-r", "--name-only", PIN,
                                      f"VisionPilot/{inc}"], capture_output=True, text=True, check=True).stdout
            has_header = bool(listing.strip())
        assert has_header, inc


def test_overlay_names_every_module_source_of_the_score_interface() -> None:
    # the module's sources in the repository are the ones patch 0002 adds, and the overlay compiles every one
    module_sources = {f"modules/de4sdv/score_interface/src/{p.name}" for p in
                      (BENCH / "score-interface" / "module" / "src").glob("*.cpp")}
    added = patch_added_files()
    patched = {p for p in added if p.startswith("modules/de4sdv/score_interface/src/") and p.endswith(".cpp")}
    assert module_sources == patched
    assert module_sources <= build_sources()
    text = VP_BUILD.read_text()
    carla = text[text.index('name = "de4sdv_score_carla_client"'):]
    carla = carla[:carla.index(")\n")]
    assert 'copts = ["-std=c++20"]' in carla
    assert text.count("-std=c++20") == 1  # only the CARLA unit is C++20
    assert 'defines = ["ENABLE_SCORE_INTERFACE=1"]' in text
    # the lifecycle unit links S-CORE Lifecycle's two client libraries (launch-manager/README.md) into VisionPilot
    life = text[text.index('name = "de4sdv_score_lifecycle_bindings"'):]
    life = life[:life.index("\n)\n")]
    assert '"modules/de4sdv/score_interface/src/lifecycle_bindings.cpp"' in life
    assert '"@score_lifecycle//score/launch_manager:alive_cc"' in life
    assert '"@score_lifecycle//score/launch_manager:lifecycle_cc"' in life
    binary = text[text.index('name = "VisionPilot"'):]
    assert '":de4sdv_score_lifecycle_bindings"' in binary
    fallback = (BUILD_DIR / "workspace" / "fallback.BUILD.bazel").read_text()
    for unit in ("de4sdv_score_carla_client", "de4sdv_score_lifecycle_bindings", "de4sdv_score_lola_bindings"):
        assert f'"//visionpilot:{unit}"' in fallback, unit


def test_workspace_edits_find_their_anchors() -> None:
    diff = (REPO / "implementation/closed-loop-driving-bench/agent/workspace/feo-313b3d84-bench.diff").read_text()
    added = "\n".join(line[1:] for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++"))
    script = (BUILD_DIR / "build_score_bench.sh").read_text()
    old = 'build_file = "//probe/carla:libcarla.BUILD",\n    path = "/opt/carla-d/libcarla-install",'
    assert added.count(old) == 1
    assert "old = 'build_file = \"//probe/carla:libcarla.BUILD\",\\n    path = \"/opt/carla-d/libcarla-install\",'" in script
    assert len(re.findall(r'\n# WP2a \(slice 10b\).*?\n\)\n', added + "\n", flags=re.S)) == 1
    assert "new_local_repository = use_repo_rule(" in added
    fragment = (BUILD_DIR / "workspace" / "MODULE.fragment.bazel").read_text()
    assert 'name = "da_b2_thirdparty"' in fragment and "@ROOT@/thirdparty" in fragment
    assert '"//de4sdv_da_bench/score-build/workspace:thirdparty.BUILD"' in fragment


def test_thirdparty_placeholders_are_all_filled_by_the_script() -> None:
    template = (BUILD_DIR / "workspace" / "thirdparty.BUILD.in").read_text()
    placeholders = set(re.findall(r"@HOST_[A-Z_]+@", template))
    assert placeholders == {"@HOST_GSTREAMER_LIBS@", "@HOST_SOLVER_LIBS@", "@HOST_GSTREAMER_INCLUDES@"}
    script = (BUILD_DIR / "build_score_bench.sh").read_text()
    for ph in placeholders:
        assert f's|{ph}|' in script, ph
    assert '! grep -q "@HOST_"' in script


def test_labels_the_bench_packages_need_are_provided() -> None:
    adapter = (BENCH / "actuation-adapter" / "BUILD.bazel").read_text()
    script = (BUILD_DIR / "build_score_bench.sh").read_text()
    interfaces = (BUILD_DIR / "workspace" / "interfaces.BUILD.bazel").read_text()
    assert "//de4sdv_da_bench/interfaces:driver_assistance" in adapter
    assert 'name = "driver_assistance"' in interfaces
    assert (BENCH / "interfaces" / "include" / "de4sdv" / "driver_assistance" / "payloads.h").is_file()
    assert 'OVERLAY=$WS/de4sdv_da_bench' in script
    assert 'cp "$HERE/workspace/interfaces.BUILD.bazel" "$OVERLAY/interfaces/BUILD.bazel"' in script
    assert '"@libcarla//:client"' in adapter and "libcarla10.BUILD" in script
    ws_build = (BUILD_DIR / "workspace" / "BUILD.bazel").read_text()
    for label in re.findall(r'"(//de4sdv_da_bench/score-build/workspace:[a-z_]+)"', VP_BUILD.read_text()):
        assert f'name = "{label.split(":")[1]}"' in ws_build, label
    for target in ("//visionpilot:VisionPilot", "//de4sdv_da_bench/actuation-adapter:actuation_adapter",
                   "//de4sdv_da_bench/score-build/workspace:ort_cuda_check",
                   "@score_lifecycle//score/launch_manager:launch_manager",
                   "//de4sdv_da_bench/launch-manager:de4sdv_lm_config"):
        assert target in script
    # the adapter's Lifecycle labels resolve in the workspace: score_lifecycle is a bazel_dep of the bench diff at
    # 0.10.0, which the workspace stage asserts
    for label in re.findall(r'"(@score_lifecycle//[^"]+)"', adapter):
        assert label in ("@score_lifecycle//score/launch_manager:alive_cc",
                         "@score_lifecycle//score/launch_manager:lifecycle_cc"), label
    assert 'module_name = "score_lifecycle",\n    version = "0.10.0",' in added_lines_of_bench_diff()
    assert 'module_name = "score_lifecycle",\\n    version = "0.10.0",' in script
    lm_build = (BUILD_DIR / "workspace" / "launch_manager.BUILD.bazel").read_text()
    assert 'load("@score_lifecycle//:defs.bzl", "launch_manager_config")' in lm_build
    assert 'name = "de4sdv_lm_config"' in lm_build and 'config = "launch_manager_config.json"' in lm_build
    assert ('cp "$BENCH/launch-manager/config/launch_manager_config.json" '
            '"$BENCH/score-path/config/launch_manager_config_path_only.json" \\\n  "$OVERLAY/launch-manager/"') in script


def test_the_bundle_carries_both_serialized_configurations_beside_their_json() -> None:
    """The path-only configuration (mode path: P10-3 and p10-1's late subscriber) is converted by the same Lifecycle
    v0.10.0 rule as the full one, in its own flatbuffer_out_dir (the rule declares that directory in the package),
    and each .bin lands in config/launch_manager/ beside the JSON it was converted from, which
    score-path/scripts/stage_score_side.py checks against the bench's file of the mode."""
    script = (BUILD_DIR / "build_score_bench.sh").read_text()
    lm_build = (BUILD_DIR / "workspace" / "launch_manager.BUILD.bazel").read_text()
    targets = re.findall(r'launch_manager_config\(\s*name = "([^"]+)",\s*config = "([^"]+)",'
                         r'(?:\s*flatbuffer_out_dir = "([^"]+)",)?\s*\)', lm_build)
    assert [(n, c) for n, c, _ in targets] == [("de4sdv_lm_config", "launch_manager_config.json"),
                                               ("de4sdv_lm_config_path_only", "launch_manager_config_path_only.json")]
    assert len({d or "flatbuffer_out" for _, _, d in targets}) == 2
    for name, _, _ in targets:
        assert f"//de4sdv_da_bench/launch-manager:{name}" in script
    bundle = script[script.index("step bundle"):]
    assert "for c in launch_manager_config launch_manager_config_path_only; do" in bundle
    assert ('cp "$BENCH/launch-manager/config/launch_manager_config.json" '
            '"$BENCH/score-path/config/launch_manager_config_path_only.json" \\\n  "$B/config/launch_manager/"') in bundle
    assert (BENCH / "score-path" / "config" / "launch_manager_config_path_only.json").is_file()


def test_the_bundle_carries_upstreams_derived_c_matrix() -> None:
    """upstream's CMake build derives config/homography_C_matrix.yaml from H.yaml (find_homography_C_matrix.py, which
    reads ../config/H.yaml); the bundle makes it the same way, since mode path stages the bundle's calibration."""
    script = (BUILD_DIR / "build_score_bench.sh").read_text()
    bundle = script[script.index("step bundle"):]
    assert ('(cd "$VP/VisionPilot/scripts" && /usr/bin/python3 find_homography_C_matrix.py \\\n'
            '   --output "$B/config/visionpilot/homography_C_matrix.yaml")') in bundle
    pins = (BUILD_DIR / "pins.sh").read_text()
    assert "python3-opencv" in pins and "python3-numpy" in pins


def added_lines_of_bench_diff() -> str:
    diff = (REPO / "implementation/closed-loop-driving-bench/agent/workspace/feo-313b3d84-bench.diff").read_text()
    return "\n".join(line[1:] for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++"))


def test_bundle_bin_holds_the_launch_manager_binary_names() -> None:
    """bin/ of the bundle is the Launch Manager's bin_dir: every binary_name of its configuration."""
    import json
    config = json.loads((BENCH / "launch-manager" / "config" / "launch_manager_config.json").read_text())
    names = {c["component_properties"]["binary_name"] for c in config["components"].values()}
    assert names == {"identity_recorder", "someipd", "gatewayd", "vision_pilot", "actuation_adapter"}
    script = (BUILD_DIR / "build_score_bench.sh").read_text()
    bundle = script[script.index("step bundle"):]
    assert 'cp -L "$SB/visionpilot/VisionPilot" "$B/bin/vision_pilot"' in bundle
    assert '"$SB/de4sdv_da_bench/actuation-adapter/actuation_adapter"' in bundle
    assert 'cp -L "$GB/score/gatewayd/gatewayd" "$GB/score/someipd/someipd" "$B/bin/"' in bundle
    assert 'cp -L "$LMD" "$B/bin/launch_manager"' in bundle
    assert "bin/VisionPilot" not in bundle
    produced = {p for p in bundle_step_outputs(script)[0] if p.startswith("bin/")}
    assert {f"bin/{n}" for n in names} <= produced


# --- the bundle contract: stage_score_side.py reads, build_score_bench.sh's bundle step produces --------------------

STAGE_PY = BENCH / "score-path" / "scripts" / "stage_score_side.py"


def _shell_commands(text: str) -> list[str]:
    """The commands of a shell fragment: comments dropped, continuation lines joined, for-loops over literal words
    unrolled (the loop variable substituted in the body)."""
    lines = [ln for ln in text.replace("\\\n", " ").splitlines() if not ln.lstrip().startswith("#")]
    out: list[str] = []
    i = 0
    while i < len(lines):
        m = re.match(r"\s*for (\w+) in ([^;$]+); do\s*$", lines[i])
        if m:
            var, words = m.group(1), m.group(2).split()
            j = i + 1
            while lines[j].strip() != "done":
                j += 1
            for w in words:
                for body in lines[i + 1:j]:
                    out.append(body.replace("${%s}" % var, w).replace("$" + var, w))
            i = j + 1
            continue
        out.append(lines[i])
        i += 1
    return out


def bundle_step_outputs(script: str) -> tuple[set[str], list[tuple[str, str]], set[str]]:
    """What the bundle step of build_score_bench.sh writes under $B, read statically: the bundle-relative paths (a
    source glob stays a glob, "<dir>/." contents become "<dest>/<from:dir>"), each (bundle path, source) pair, and the
    bundle-relative directories copied as a whole."""
    import shlex
    bundle = script[script.index("\nstep bundle\n"):]
    produced: set[str] = set()
    pairs: list[tuple[str, str]] = []
    whole_dirs: set[str] = set()
    found: dict[str, str] = {}  # X=$(find ... -name "<name>" ...): $X is a file of that name
    for cmd in _shell_commands(bundle):
        m = re.match(r"""\s*(\w+)=\$\(find .*-name ['"]([^'"]+)['"]""", cmd)
        if m:
            found[m.group(1)] = m.group(2)
        body = cmd.strip().lstrip("(").split("&&")[-1].strip()
        if body.startswith("cp "):
            body = re.split(r"\s(?:2>|\|\|)", body)[0]
            words = [w for w in shlex.split(body)[1:] if not w.startswith("-")]
            dest, sources = words[-1], words[:-1]
            if not dest.startswith("$B/"):
                continue
            rel = dest[len("$B/"):]
            for src in sources:
                if src.startswith("$") and src[1:] in found:
                    src = found[src[1:]]
                if src.endswith("/."):
                    path = rel.rstrip("/") + "/<from:" + src[:-2] + ">"
                elif rel.endswith("/"):
                    path = rel + src.rstrip("/").rsplit("/", 1)[-1]
                else:
                    path = rel
                    if "-a" in shlex.split(body):
                        whole_dirs.add(rel)
                produced.add(path)
                pairs.append((path, src))
        for m in re.finditer(r'--output "\$B/([^"]+)"', cmd):
            produced.add(m.group(1))
            pairs.append((m.group(1), "--output"))
    if re.search(r'\(cd "\$B" && find \. -type f ! -name SHA256SUMS -print0 \| sort -z \| xargs -0 sha256sum '
                 r'> SHA256SUMS\)', bundle):
        produced.add("SHA256SUMS")
    return produced, pairs, whole_dirs


def _literal(node):
    import ast
    return ast.literal_eval(node)


def staging_reads() -> tuple[dict[str, bool], list[str]]:
    """The bundle paths stage_score_side.py reads, read statically from its constants and its bundle expressions:
    {bundle-relative path or glob: required}, and every bundle expression of the script as a path prefix."""
    import ast
    text = STAGE_PY.read_text()
    tree = ast.parse(text)
    consts: dict[str, object] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                consts[node.targets[0].id] = _literal(node.value)
            except ValueError:
                pass
    assert re.search(r'^BUNDLE_LAUNCH_DIR = Path\("config"\) / "launch_manager"$', text, flags=re.M)
    launch_dir = "config/launch_manager"
    reads: dict[str, bool] = {}
    for name in consts["REQUIRED_BINARIES"]:
        reads[f"bin/{name}"] = True
    for name in consts["OPTIONAL_BINARIES"]:
        reads[f"bin/{name}"] = False
    for serialized in consts["SERIALIZED"].values():
        reads[f"{launch_dir}/{serialized}"] = False
        reads[f"{launch_dir}/{serialized[:-len('.bin')]}.json"] = False
    for name in consts["CALIBRATION_FILES"]:
        reads[f"config/visionpilot/{name}"] = False  # the fallback of mode path; p10-1 copies them too
    reads.update({
        "lib/*": True,
        "config/gateway/someip_gateway_config_warning.bin": True,
        "config/visionpilot/vision_pilot.conf": True,
        "share/visionpilot/modules/models/weights/*.onnx": True,
        "share/visionpilot/assets": False,
        "facts/*.diff": True,
        "facts/SHA256SUMS": False,
    })
    # every expression on the bundle in the script, as its literal prefix: none may read outside the paths above
    prefixes = []
    for m in re.finditer(r'(?:args\.)?bundle((?:\s*/\s*(?:"[^"]+"|BUNDLE_LAUNCH_DIR))+)', text):
        parts = re.findall(r'"([^"]+)"|(BUNDLE_LAUNCH_DIR)', m.group(1))
        prefixes.append("/".join(a or launch_dir for a, _ in [(p[0], p[1]) for p in parts]))
    return reads, prefixes


def _covers(produced: set[str], path: str) -> bool:
    import fnmatch
    return any(p == path or fnmatch.fnmatchcase(p, path) or fnmatch.fnmatchcase(path, p) for p in produced)


def test_the_bundle_step_produces_every_path_the_staging_reads() -> None:
    """The bundle contract: every path that score-path/scripts/stage_score_side.py requires, or reads when present,
    is produced by the bundle step of build_score_bench.sh, before the bundle's SHA256SUMS is taken."""
    script = (BUILD_DIR / "build_score_bench.sh").read_text()
    produced, pairs, _ = bundle_step_outputs(script)
    reads, prefixes = staging_reads()
    assert {"bin/identity_recorder", "bin/candidate_record_probe", "bin/warning_injector"} <= set(reads)
    # the staging reads nothing the list above does not name
    for prefix in prefixes:
        assert any(r == prefix or r.startswith(prefix + "/") for r in reads), prefix
    # upstream's config/ comes in whole: its files at the pin stand for "<from:$VP/VisionPilot/config>"
    upstream_config = "config/visionpilot/<from:$VP/VisionPilot/config>"
    assert upstream_config in produced
    expanded = set(produced)
    if have_clone():
        listing = subprocess.run(["git", "-C", str(CLONE), "ls-tree", "--name-only", f"{PIN}:VisionPilot/config"],
                                 check=True, capture_output=True, text=True).stdout.split()
        added = {p.split("/", 1)[1] for p in patch_added_files() if p.startswith("config/")}
        expanded |= {f"config/visionpilot/{n}" for n in set(listing) | added}
    else:
        expanded |= {"config/visionpilot/vision_pilot.conf", "config/visionpilot/H.yaml"}
    missing = [path for path in reads if not _covers(expanded, path)]
    assert not missing, missing
    # the sums are taken last, over every file: nothing is written into $B after them
    bundle = script[script.index("\nstep bundle\n"):]
    sums = bundle.index('(cd "$B" && find . -type f ! -name SHA256SUMS')
    assert not re.search(r'"\$B/', bundle[sums:].split("tar -czf", 1)[0].split("\n", 1)[1])
    assert "SHA256SUMS" in produced


def test_the_bundle_binaries_are_built_targets_of_staged_packages() -> None:
    """Each bin/ entry copied from Bazel's output is a target of the bazel stage, in a package that the overlay
    stages from the repository and that declares it."""
    script = (BUILD_DIR / "build_score_bench.sh").read_text()
    bazel = script[script.index("\nstep bazel\n"):script.index("\nstep bundle\n")]
    targets = set(re.search(r"TARGETS=\(([^)]*)\)", bazel).group(1).split())
    _, pairs, _ = bundle_step_outputs(script)
    from_bazel = [(path, src) for path, src in pairs if src.startswith("$SB/de4sdv_da_bench/")]
    names = {path for path, _ in from_bazel}
    assert {"bin/identity_recorder", "bin/candidate_record_probe", "bin/warning_injector", "bin/actuation_adapter",
            "bin/ort_cuda_check"} <= names
    for path, src in from_bazel:
        pkg, name = src[len("$SB/de4sdv_da_bench/"):].rsplit("/", 1)
        assert f"//de4sdv_da_bench/{pkg}:{name}" in targets, src
        assert path == f"bin/{name}"
        build = BENCH / pkg / "BUILD.bazel"
        if pkg == "score-build/workspace":
            build = BUILD_DIR / "workspace" / "BUILD.bazel"
        assert re.search(r'cc_binary\(\s*name = "%s"' % re.escape(name), build.read_text()), (pkg, name)
    commands = _shell_commands(bazel)
    for pkg in ("identity-recorder", "ivi-warning/injector"):
        assert any(f'"$OVERLAY/{pkg}"' in c and c.lstrip().startswith("mkdir -p") for c in commands), pkg
        assert any(f'(cd "$BENCH/{pkg}" && tar' in c and f'-C "$OVERLAY/{pkg}"' in c for c in commands), pkg
    # the labels those packages need resolve in the workspace
    ws_build = (BUILD_DIR / "workspace" / "BUILD.bazel").read_text()
    adapter = (BENCH / "actuation-adapter" / "BUILD.bazel").read_text()
    for pkg in ("identity-recorder", "ivi-warning/injector"):
        for label in re.findall(r'"(//de4sdv_da_bench/[^"]+|@score_[a-z]+//[^"]+)"', (BENCH / pkg / "BUILD.bazel").read_text()):
            if label.startswith("//de4sdv_da_bench/score-build/workspace:"):
                assert f'name = "{label.split(":")[1]}"' in ws_build, label
            elif label.startswith("//de4sdv_da_bench/actuation-adapter:"):
                assert f'name = "{label.split(":")[1]}"' in adapter, label
            elif label.startswith("//de4sdv_da_bench/interfaces:"):
                assert label == "//de4sdv_da_bench/interfaces:driver_assistance", label
            else:
                assert label in ("@score_communication//score/mw/com",
                                 "@score_lifecycle//score/launch_manager:lifecycle_cc"), label


def test_every_repository_source_of_the_bundle_exists() -> None:
    """The bundle step's sources from this checkout (and from the pin, with the clone) exist."""
    import glob
    script = (BUILD_DIR / "build_score_bench.sh").read_text()
    _, pairs, _ = bundle_step_outputs(script)
    for _, src in pairs:
        if src.startswith("$BENCH/"):
            assert glob.glob(str(BENCH / src[len("$BENCH/"):])), src
    if have_clone():
        for rel in ("assets", "config", "scripts/find_homography_C_matrix.py"):
            assert upstream_exists(rel), rel
        weights = subprocess.run(["git", "-C", str(CLONE), "ls-tree", "--name-only",
                                  f"{PIN}:VisionPilot/modules/models/weights"],
                                 check=True, capture_output=True, text=True).stdout.split()
        assert any(w.endswith(".onnx") for w in weights)
        assert "--output" in upstream("scripts/find_homography_C_matrix.py")


@pytest.mark.skipif(not ORT_NUPKG.is_file() or shutil.which("readelf") is None,
                    reason="the ONNX Runtime package is not on this host (DA_B2_ORT_NUPKG)")
def test_ort_package_matches_its_pins(tmp_path: Path) -> None:
    p = pins()
    assert hashlib.sha256(ORT_NUPKG.read_bytes()).hexdigest() == p["ORT_SHA256"]
    with zipfile.ZipFile(ORT_NUPKG) as z:
        for member, key in (("libonnxruntime.so", "ORT_LIBONNXRUNTIME_SHA256"),
                            ("libonnxruntime_providers_cuda.so", "ORT_PROVIDERS_CUDA_SHA256"),
                            ("libonnxruntime_providers_shared.so", "ORT_PROVIDERS_SHARED_SHA256")):
            z.extract(f"runtimes/linux-x64/native/{member}", tmp_path)
            data = (tmp_path / "runtimes/linux-x64/native" / member).read_bytes()
            assert hashlib.sha256(data).hexdigest() == p[key], member
    out = subprocess.run(["readelf", "-d", str(tmp_path / "runtimes/linux-x64/native/libonnxruntime_providers_cuda.so")],
                         check=True, capture_output=True, text=True).stdout
    needed = re.findall(r"\(NEEDED\)\s+Shared library: \[([^\]]+)\]", out)
    cuda = [n for n in needed if re.match(r"lib(cu|nv)", n)]
    assert cuda == p["ORT_CUDA_NEEDED"].split()


def test_cpp_files_include_cstdint_where_they_name_fixed_width_types() -> None:
    files = [f for f in BUILD_DIR.rglob("*") if f.suffix in (".cpp", ".hpp", ".h")]
    assert files
    for f in files:
        text = f.read_text()
        if re.search(r"\b(std::)?u?int(8|16|32|64)_t\b", text):
            assert "#include <cstdint>" in text, f.name
