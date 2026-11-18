#!/usr/bin/env bash
# DE4SDV driver-assistance bench (INC-DRIVING-002): the fallback route of risk R3, written ready but NOT RUN yet.
#
# Use it only if the Bazel build of //visionpilot:VisionPilot (stage "bazel" of build_score_bench.sh) fails and cannot
# be fixed in time. It is the two-step route of INC-MW-011 (score-reference-interop-bench/README.md, "Build route"):
#   1. Bazel builds, with the S-CORE gcc 12.2.0, one static archive of the S-CORE interface module's two binding units
#      (lola_bindings.cpp with mw::com 0.6.0, carla_client.cpp as C++20) behind seams.hpp, which uses plain C++ types;
#   2. upstream's own CMake build compiles VisionPilot with Ubuntu 22.04's g++ 12 and links that archive as
#      DE4SDV_SCORE_BINDINGS (0002's module CMakeLists.txt), with the CARLA 1.0 archives and the ONNX Runtime GPU
#      package of the main build, and OpenCV, Ipopt, CppAD and GStreamer from Ubuntu, as upstream's Dockerfile does.
# The process then holds one shared libstdc++ (the host's) plus the static S-CORE objects, as the INC-MW-011 adapter.
#
# Prerequisite: build_score_bench.sh ran through its stage "thirdparty" with the same --root (its sources, S-CORE
# workspace, toolchain, CARLA bundle, Rerun SDK and ONNX Runtime are reused).
# Usage: implementation/driver-assistance-bench/score-build/fallback_cmake_build.sh [--root DIR] [--jobs N]
# Output: <root>/fallback/build/VisionPilot, copied over <root>/bundle/bin/VisionPilot when the bundle exists (the
# Bazel-built binary is kept as VisionPilot.bazel if there was one).
set -Eeuo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
BENCH=$(cd "$HERE/.." && pwd)
# shellcheck source=pins.sh
source "$HERE/pins.sh"
ROOT=/opt/da-b2
JOBS=$(nproc)
while [ $# -gt 0 ]; do
  case "$1" in
    --root) ROOT=${2:?}; shift 2 ;;
    --jobs) JOBS=${2:?}; shift 2 ;;
    *) echo "unknown argument $1" >&2; exit 2 ;;
  esac
done
F=$ROOT/fallback
mkdir -p "$F" "$ROOT/logs"
LOG=$ROOT/logs/fallback-$(date -u +%Y%m%dT%H%M%SZ).log
exec > >(tee -a "$LOG") 2>&1
STAGE=init
die() { echo "FALLBACK FAILED in stage $STAGE: $*"; echo "log: $LOG"; exit 1; }
trap 'rc=$?; echo "FALLBACK FAILED in stage $STAGE: command \"$BASH_COMMAND\" exited $rc (line $LINENO)"; echo "log: $LOG"; exit $rc' ERR
step() { STAGE=$1; echo; echo "=== stage $1 $(date -u +%FT%TZ)"; }
export PATH=$ROOT/tools/cmake/bin:$PATH
WS=$ROOT/ws
VP=$ROOT/src/vp
TP=$ROOT/thirdparty
bazel_feo() { "$ROOT/tools/bazel-$BAZEL_FEO_VERSION" "$@"; }

step preflight
for m in workspace carla rerun thirdparty; do
  [ -f "$ROOT/.done-$m" ] || die "build_score_bench.sh has not finished its stage $m under $ROOT"
done
[ -d "$WS/visionpilot" ] || die "$WS/visionpilot is not staged; run build_score_bench.sh to its stage bazel (a failing Bazel build there is fine)"

step apt
# What upstream's docker/Dockerfile installs for the CMake build (without CUDA, ROS 2 and TensorRT), on Ubuntu 22.04
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q --no-install-recommends g++-12 libopencv-dev python3-opencv \
  python3-numpy libboost-system-dev nlohmann-json3-dev libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev \
  libgstreamer-plugins-bad1.0-dev $APT_PINNED

step bindings-archive
mkdir -p "$WS/de4sdv_da_bench/score-build/fallback"
cp "$HERE/workspace/fallback.BUILD.bazel" "$WS/de4sdv_da_bench/score-build/fallback/BUILD.bazel"
cd "$WS"
T=//de4sdv_da_bench/score-build/fallback:de4sdv_score_bindings
if ! bazel_feo build --config=x86_64-linux -c opt --jobs="$JOBS" --experimental_cc_static_library \
    --output_groups=+linkopts,+linkdeps "$T" > "$ROOT/logs/fallback-bazel.log" 2>&1; then
  grep -E "^ERROR|error:" "$ROOT/logs/fallback-bazel.log" | sed -n 1,20p; die "Bazel build of the bindings archive failed"
fi
SB=$(bazel_feo info --config=x86_64-linux -c opt bazel-bin)/de4sdv_da_bench/score-build/fallback
A=$SB/libde4sdv_score_bindings.a
[ -f "$A" ] || die "no $A"
cat "$SB/de4sdv_score_bindings_linkdeps.txt" "$SB/de4sdv_score_bindings_linkopts.txt" || true
# The link inputs after the archive: CARLA's archives in the example's link order, other linkdeps, the linkopts.
python3 - "$A" "$SB" "$ROOT/carla/libcarla10.BUILD" "$ROOT/carla/libcarla10-bundle" "$(bazel_feo info output_base)" > "$F/bindings_link.txt" <<'PY'
import glob, os, re, shlex, sys
archive, sb, carla_build, carla_bundle, output_base = sys.argv[1:]
items = [archive]
for label in open(os.path.join(sb, 'de4sdv_score_bindings_linkdeps.txt')).read().split():
    if 'libcarla' in label:
        # the 17 archives in the order of libcarla10.BUILD, which is the example client's link order
        items += [os.path.join(carla_bundle, rel) for rel in re.findall(r'"(lib/[^"]+\.a)"', open(carla_build).read())]
    elif 'acl' in label:
        found = glob.glob(os.path.join(output_base, 'external', '*acl*', '**', 'libacl.a'), recursive=True)
        assert found, 'libacl.a of %s not found' % label
        items.append(found[0])
    else:
        raise SystemExit('unhandled linkdeps entry ' + label)
seen = []
for line in open(os.path.join(sb, 'de4sdv_score_bindings_linkopts.txt')):
    for t in shlex.split(line):
        if t not in seen:
            seen.append(t)
print(';'.join(items + seen + ['-lpthread', '-ldl', '-lrt']))
PY
echo "DE4SDV_SCORE_BINDINGS = $(cat "$F/bindings_link.txt")"

step cmake
# Upstream's CMake as is, at the pin with 0001 and 0002; Eigen and Rerun from the pinned archives of the main build
# (FetchContent would fetch them by tag), Ipopt's headers as coin-or/ through a private include directory (upstream's
# Dockerfile makes the same link under /usr/include instead).
mkdir -p "$F/inc" && ln -sfn /usr/include/coin "$F/inc/coin-or"
rm -rf "$F/eigen" && mkdir -p "$F/eigen" && tar -xzf "$ROOT/dl/eigen-5.0.0.tar.gz" -C "$F/eigen" --strip-components=1
cmake -S "$VP/VisionPilot" -B "$F/build" -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=gcc-12 -DCMAKE_CXX_COMPILER=g++-12 \
  -DONNXRUNTIME_ROOT="$TP/onnxruntime" -DGPU=ON -DENABLE_ROS2_INTERFACE=OFF -DENABLE_OCCUPANCY=OFF \
  -DENABLE_RERUN=ON -DRERUN_SDK_ROOT="$ROOT/src/rerun_cpp_sdk" -DFETCHCONTENT_SOURCE_DIR_EIGEN="$F/eigen" \
  -DENABLE_SCORE_INTERFACE=ON -DDE4SDV_DA_INTERFACES_INCLUDE_DIR="$BENCH/interfaces/include" \
  -DDE4SDV_SCORE_BINDINGS="$(cat "$F/bindings_link.txt")" -DCMAKE_CXX_FLAGS="-isystem $F/inc" \
  -DCMAKE_CXX_STANDARD_LIBRARIES="-lcppad_lib" > "$ROOT/logs/fallback-cmake.log" 2>&1 \
  || { tail -30 "$ROOT/logs/fallback-cmake.log"; die "upstream's CMake configure failed"; }
make -C "$F/build" -j "$JOBS" VisionPilot > "$ROOT/logs/fallback-make.log" 2>&1 \
  || { grep -E "error|undefined reference" "$ROOT/logs/fallback-make.log" | sed -n 1,30p; die "upstream's CMake build failed"; }

step result
V=$F/build/VisionPilot
readelf -d "$V" | grep -E "NEEDED|RUNPATH" || true
strings "$V" > "$F/VisionPilot.strings"
grep -q -E '^1\.0-14ac3b1a5$' "$F/VisionPilot.strings" || die "the binary does not hold the CARLA client version string"
if [ -d "$ROOT/bundle/bin" ]; then
  if [ -f "$ROOT/bundle/bin/VisionPilot" ]; then mv "$ROOT/bundle/bin/VisionPilot" "$ROOT/bundle/bin/VisionPilot.bazel"; fi
  cp "$V" "$ROOT/bundle/bin/VisionPilot"
  (cd "$ROOT/bundle" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
fi
echo "=== FALLBACK OK: $V sha256 $(sha256sum "$V" | cut -c1-64)"
