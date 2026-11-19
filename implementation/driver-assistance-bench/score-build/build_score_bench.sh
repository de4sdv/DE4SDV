#!/usr/bin/env bash
# DE4SDV driver-assistance bench (INC-DRIVING-002), build item B2: builds VisionPilot natively as an Eclipse S-CORE
# application, with the actuation adapter, the ONNX Runtime CUDA check, gatewayd and someipd, on a fresh x86_64
# Ubuntu 22.04 host, and packs a bundle for the S-CORE host.
#
# Usage (from a checkout of this repository, as a user with sudo):
#   implementation/driver-assistance-bench/score-build/build_score_bench.sh [--root DIR] [--jobs N]
#     --root DIR  work and output directory (default /opt/da-b2); the bundle is DIR/bundle, logs are DIR/logs/
#     --jobs N    parallel compile jobs for CMake and Bazel (default: nproc)
#     --min-free-gb N  free disk (GiB) the preflight asks for under DIR (default 70, the estimate for a cold build);
#                 a rerun with finished stages, or a run watched by a disk guard, may ask for less
#
# Idempotent: each stage leaves DIR/.done-<stage> and is skipped on a rerun; delete the mark to redo a stage. The
# downloads are kept in DIR/dl and checked against pins.sh on every run. Every step is logged; the script stops at the
# first failure with "BUILD FAILED in stage <stage>: <reason>" and the log path. At the end it prints the sha256 of
# every bundled binary and library.
#
# Stages: preflight, apt, tools, sources, visionpilot, workspace, carla, opencv, rerun, thirdparty, gateway, bazel,
# bundle. The recipes are those of the readiness probe DA-P8 (runs e and h) and of probe P5 (the gateway at the
# v0.10.0 module set), extended to VisionPilot itself. The README says what each stage does and why.
set -Eeuo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
BENCH=$(cd "$HERE/.." && pwd)
REPO=$(cd "$BENCH/../.." && pwd)
# shellcheck source=pins.sh
source "$HERE/pins.sh"

ROOT=/opt/da-b2
JOBS=$(nproc)
MIN_FREE_GB=70
while [ $# -gt 0 ]; do
  case "$1" in
    --root) ROOT=${2:?--root needs a directory}; shift 2 ;;
    --jobs) JOBS=${2:?--jobs needs a number}; shift 2 ;;
    --min-free-gb) MIN_FREE_GB=${2:?--min-free-gb needs a number}; shift 2 ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "unknown argument $1" >&2; exit 2 ;;
  esac
done

if [ ! -d "$ROOT" ] || [ ! -w "$ROOT" ]; then
  sudo mkdir -p "$ROOT" && sudo chown "$(id -u):$(id -g)" "$ROOT"
fi
mkdir -p "$ROOT/logs" "$ROOT/dl" "$ROOT/src" "$ROOT/tools" "$ROOT/thirdparty" "$ROOT/facts"
LOG=$ROOT/logs/build-$(date -u +%Y%m%dT%H%M%SZ).log
exec > >(tee -a "$LOG") 2>&1

STAGE=init
die() { echo "BUILD FAILED in stage $STAGE: $*"; echo "log: $LOG"; exit 1; }
trap 'rc=$?; echo "BUILD FAILED in stage $STAGE: command \"$BASH_COMMAND\" exited $rc (line $LINENO)"; echo "log: $LOG"; exit $rc' ERR
step() { STAGE=$1; echo; echo "=== stage $1 $(date -u +%FT%TZ) free $(df -B1 --output=avail "$ROOT" | tail -1 | tr -dc 0-9) B"; }
is_done() { [ -f "$ROOT/.done-$1" ]; }
mark_done() { touch "$ROOT/.done-$1"; echo "=== stage $1 done $(date -u +%FT%TZ)"; }

# fetch <file name> <url> <sha256>: download into $ROOT/dl (resumable, retried) and check the sha256.
fetch() {
  local name=$1 url=$2 sha=$3 dst=$ROOT/dl/$1 try
  if [ -f "$dst" ] && echo "$sha  $dst" | sha256sum -c --quiet - 2>/dev/null; then
    echo "have $name (sha256 ok)"; return 0
  fi
  rm -f "$dst"
  for try in 1 2 3 4 5; do
    curl -fsSL --http1.1 --retry 5 --retry-delay 5 -C - -o "$dst.part" "$url" && break
    echo "download try $try of $name failed; retrying"
    sleep 5
  done
  [ -f "$dst.part" ] || die "download of $url failed"
  echo "$sha  $dst.part" | sha256sum -c --quiet - || die "sha256 of $name differs from pins.sh: $(sha256sum "$dst.part" | cut -c1-64)"
  mv "$dst.part" "$dst"
  echo "fetched $name (sha256 ok)"
}

# git_at <dir> <url> <commit>: a depth-1 checkout of exactly <commit>, with no tracked change.
git_at() {
  local dir=$1 url=$2 commit=$3
  if [ ! -d "$dir/.git" ]; then
    git init -q "$dir"
    git -C "$dir" remote add origin "$url"
    git -C "$dir" fetch -q --depth 1 origin "$commit" || die "git fetch $commit from $url"
    git -C "$dir" checkout -q FETCH_HEAD
  fi
  [ "$(git -C "$dir" rev-parse HEAD)" = "$commit" ] || die "$dir is not at $commit"
  echo "$dir at $commit"
}

bazel_feo() { "$ROOT/tools/bazel-$BAZEL_FEO_VERSION" "$@"; }
bazel_gw() { "$ROOT/tools/bazel-$BAZEL_GATEWAY_VERSION" "$@"; }
export PATH=$ROOT/tools/cmake/bin:$PATH
# Ubuntu 22.04's GStreamer .pc files pull in libunwind's -I/usr/include/x86_64-linux-gnu (Requires.private), the
# multiarch directory of the host glibc's bits/ headers; in a compile with the S-CORE sysroot they clash with the
# sysroot's glibc ("'__fpclassify' has not been declared"). GStreamer and GLib need no header from there, so
# pkg-config treats it as a system directory and leaves it out, for OpenCV's configure and the thirdparty stage.
# CMake's FindPkgConfig sets PKG_CONFIG_ALLOW_SYSTEM_CFLAGS=1, which would bring both directories back (and
# /usr/include itself): OpenCV's configure gets the wrapper $ROOT/tools/pkg-config-score, which unsets it.
export PKG_CONFIG_SYSTEM_INCLUDE_PATH=/usr/include:/usr/include/x86_64-linux-gnu

WS=$ROOT/ws                 # the S-CORE workspace (FEO 313b3d84 + the bench's packages)
GW=$ROOT/src/gateway        # the SOME/IP gateway workspace (inc_someip_gateway d9eac670)
VP=$ROOT/src/vp             # VisionPilot at the pin, patched
CB=$ROOT/carla              # the CARLA 1.0 client build
TP=$ROOT/thirdparty         # @da_b2_thirdparty
OVERLAY=$WS/de4sdv_da_bench

echo "build_score_bench.sh root=$ROOT jobs=$JOBS repo=$REPO commit=$(git -C "$REPO" rev-parse HEAD 2>/dev/null || echo unknown)"

# ---------------------------------------------------------------------------------------------------------------------
step preflight
[ "$(uname -m)" = x86_64 ] || die "this host is $(uname -m); the S-CORE toolchain is x86_64"
. /etc/os-release
[ "${VERSION_ID:-}" = "22.04" ] || die "this host runs ${PRETTY_NAME:-unknown}; build on Ubuntu 22.04, the S-CORE host's release, because the binary links Ubuntu 22.04 libraries (GStreamer, Ipopt, CppAD)"
free_gb=$(df -BG --output=avail "$ROOT" | tail -1 | tr -dc 0-9)
[ "$free_gb" -ge "$MIN_FREE_GB" ] || die "only ${free_gb} GB free under $ROOT; the build asks for $MIN_FREE_GB GB (--min-free-gb; a cold build needs about 70 GB)"
echo "host $(hostname) $(nproc) vCPU $(free -g | awk '/Mem:/{print $2}') GB RAM, ${free_gb} GB free, ${PRETTY_NAME}"
(cd "$BENCH/score-interface/patches" && sha256sum -c SHA256SUMS) || die "the patch series differs from its SHA256SUMS"
for f in "$BENCH/actuation-adapter/BUILD.bazel" "$BENCH/interfaces/include/de4sdv/driver_assistance/payloads.h" \
         "$BENCH/score-path/config/gateway_overlay.BUILD.bazel" "$BENCH/launch-manager/config/launch_manager_config.json" \
         "$BENCH/score-path/config/launch_manager_config_path_only.json" \
         "$REPO/implementation/closed-loop-driving-bench/agent/workspace/feo-313b3d84-bench.diff"; do
  [ -f "$f" ] || die "missing $f; run from a full checkout of the repository"
done

# ---------------------------------------------------------------------------------------------------------------------
step apt
if ! is_done apt; then
  sudo DEBIAN_FRONTEND=noninteractive apt-get update -q
  # shellcheck disable=SC2086
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q --no-install-recommends $APT_BUILD $APT_PINNED
  mark_done apt
fi
# shellcheck disable=SC2086
dpkg-query -W -f='${Package}=${Version}\n' $(for p in $APT_BUILD $APT_RUNTIME; do echo "${p%%=*}"; done) \
  coinor-libipopt-dev libcppad-dev 2>/dev/null | sort -u > "$ROOT/facts/apt-build-packages.txt" || true
cat "$ROOT/facts/apt-build-packages.txt"

# ---------------------------------------------------------------------------------------------------------------------
step tools
fetch "bazel-$BAZEL_FEO_VERSION" "https://github.com/bazelbuild/bazel/releases/download/$BAZEL_FEO_VERSION/bazel-$BAZEL_FEO_VERSION-linux-x86_64" "$BAZEL_FEO_SHA256"
fetch "bazel-$BAZEL_GATEWAY_VERSION" "https://github.com/bazelbuild/bazel/releases/download/$BAZEL_GATEWAY_VERSION/bazel-$BAZEL_GATEWAY_VERSION-linux-x86_64" "$BAZEL_GATEWAY_SHA256"
fetch cmake.tar.gz "$CMAKE_URL" "$CMAKE_SHA256"
install -m 0755 "$ROOT/dl/bazel-$BAZEL_FEO_VERSION" "$ROOT/tools/bazel-$BAZEL_FEO_VERSION"
install -m 0755 "$ROOT/dl/bazel-$BAZEL_GATEWAY_VERSION" "$ROOT/tools/bazel-$BAZEL_GATEWAY_VERSION"
if [ ! -x "$ROOT/tools/cmake/bin/cmake" ]; then
  mkdir -p "$ROOT/tools/cmake" && tar -xzf "$ROOT/dl/cmake.tar.gz" -C "$ROOT/tools/cmake" --strip-components=1
fi
cmake --version | sed -n 1p; ninja --version; bazel_feo --version; bazel_gw --version

# ---------------------------------------------------------------------------------------------------------------------
step sources
git_at "$ROOT/src/feo" "$FEO_URL" "$FEO_COMMIT"
git_at "$GW" "$GATEWAY_URL" "$GATEWAY_COMMIT"
git_at "$ROOT/src/vp-pin" "$VP_URL" "$VP_COMMIT"
mkdir -p "$CB"
git_at "$CB/carla" "$CARLA_URL" "$CARLA_COMMIT"
[ -z "$(git -C "$ROOT/src/vp-pin" status --porcelain --untracked-files=no)" ] || die "the VisionPilot clone at the pin has tracked changes"
[ -z "$(git -C "$CB/carla" status --porcelain --untracked-files=no)" ] || die "CARLA has tracked changes; its version string would no longer equal the server's"
w=$ROOT/src/vp-pin/VisionPilot/modules/models/weights/autosteer_fp32.onnx
[ "$(stat -c %s "$w")" -gt 1000000 ] || die "$w is not the network file (size $(stat -c %s "$w"))"

# ---------------------------------------------------------------------------------------------------------------------
step visionpilot
if ! is_done visionpilot; then
  # the series' own check: a fresh clone at the pin, 0001 then 0002, and 0002 re-created byte for byte
  "$BENCH/score-interface/check_patch.sh" "$ROOT/src/vp-pin" "$ROOT/src/check_patch" || die "check_patch.sh failed"
  rm -rf "$VP"
  git clone -q --shared "$ROOT/src/vp-pin" "$VP"
  git -C "$VP" checkout -q "$VP_COMMIT"
  git -C "$VP" apply --index "$BENCH/score-interface/patches/0001-de4sdv-visualization-recorder.diff"
  git -C "$VP" apply --index "$BENCH/score-interface/patches/0002-de4sdv-score-interface.diff"
  git -C "$VP" diff --cached --stat "$VP_COMMIT" | tail -1
  mark_done visionpilot
fi

# ---------------------------------------------------------------------------------------------------------------------
step workspace
if ! is_done workspace; then
  rm -rf "$WS"
  git clone -q --shared "$ROOT/src/feo" "$WS"
  git -C "$WS" checkout -q "$FEO_COMMIT"
  git -C "$WS" apply --include=MODULE.bazel --include=.bazelrc \
    "$REPO/implementation/closed-loop-driving-bench/agent/workspace/feo-313b3d84-bench.diff"
  python3 - "$WS/MODULE.bazel" "$HERE/workspace/MODULE.fragment.bazel" "$ROOT" <<'PY'
import re, sys
path, fragment, root = sys.argv[1:]
text = open(path).read()
old = 'build_file = "//probe/carla:libcarla.BUILD",\n    path = "/opt/carla-d/libcarla-install",'
new = ('build_file = "//de4sdv_da_bench/score-build/workspace:libcarla10.BUILD",\n'
       '    path = "%s/carla/libcarla10-bundle",' % root)
assert text.count(old) == 1, "the bench diff's @libcarla entry was not found once"
text = text.replace(old, new)
text, n = re.subn(r'\n# WP2a \(slice 10b\).*?\n\)\n', '\n', text, flags=re.S)
assert n == 1, "the bench diff's @python312 entry was not found once"
assert 'new_local_repository = use_repo_rule(' in text
# S-CORE Lifecycle v0.10.0, the version of the Launch Manager configuration and the lifecycle clients (B6)
life = 'bazel_dep(name = "score_lifecycle")\nsingle_version_override(\n    module_name = "score_lifecycle",\n    version = "0.10.0",\n)'
assert text.count(life) == 1 and text.count('module_name = "score_lifecycle"') == 1, "score_lifecycle is not 0.10.0 once"
text += '\n' + open(fragment).read().replace('@ROOT@', root)
open(path, 'w').write(text)
print("MODULE.bazel: @libcarla -> the CARLA 1.0 bundle, @python312 dropped, @da_b2_thirdparty added")
PY
  git -C "$WS" diff > "$ROOT/facts/workspace.diff"
  mark_done workspace
fi
cd "$WS"
echo "S-CORE workspace: FEO $(git -C "$WS" rev-parse --short HEAD), Bazel $BAZEL_FEO_VERSION, --config=x86_64-linux"
if [ ! -f "$ROOT/facts/toolchain_path" ]; then
  if ! bazel_feo build --config=x86_64-linux --jobs="$JOBS" @score_communication//score/mw/com > "$ROOT/logs/mwcom-bazel.log" 2>&1; then
    grep -E "^ERROR|error:" "$ROOT/logs/mwcom-bazel.log" | sed -n 1,20p; die "bazel build of mw::com failed"
  fi
  tail -n 3 "$ROOT/logs/mwcom-bazel.log"
  OB=$(bazel_feo info output_base)
  TC=$(find "$OB/external" -maxdepth 1 -name '*score_gcc_x86_64_toolchain_pkg' -print -quit)
  [ -n "$TC" ] || die "the S-CORE gcc toolchain package was not found under $OB/external"
  echo "$TC" > "$ROOT/facts/toolchain_path"
fi
TC=$(cat "$ROOT/facts/toolchain_path")
SR=$TC/x86_64-unknown-linux-gnu/sysroot
CC=$TC/bin/x86_64-unknown-linux-gnu-gcc
CXX=$TC/bin/x86_64-unknown-linux-gnu-g++
AR=$TC/bin/x86_64-unknown-linux-gnu-gcc-ar
RANLIB=$TC/bin/x86_64-unknown-linux-gnu-gcc-ranlib
"$CXX" --version | sed -n 1p
# The S-CORE gcc 12.2.0 for the CMake builds outside Bazel: compilers, archiver and sysroot only (DA-P8 e and h).
cat > "$ROOT/score-gcc.cmake" <<EOF
set(CMAKE_C_COMPILER $CC)
set(CMAKE_CXX_COMPILER $CXX)
set(CMAKE_AR $AR)
set(CMAKE_RANLIB $RANLIB)
set(CMAKE_SYSROOT $SR)
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
EOF

# ---------------------------------------------------------------------------------------------------------------------
step carla
if ! is_done carla; then
  # CARLA 14ac3b1a50 always requests Boost.Python; a client-only configure then stops in BoostRoot.cmake. Drop it in
  # Boost's directory scope only; no tracked file changes, so the client's version string stays the commit's.
  cat > "$CB/boost_no_python.cmake" <<'EOF'
list(REMOVE_ITEM BOOST_INCLUDE_LIBRARIES python)
message(STATUS "DE4SDV B2: BOOST_INCLUDE_LIBRARIES in Boost's scope = ${BOOST_INCLUDE_LIBRARIES}")
EOF
  cmake -G Ninja -S "$CB/carla" -B "$CB/build" -DCMAKE_TOOLCHAIN_FILE="$ROOT/score-gcc.cmake" -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_CARLA_CLIENT=ON -DBUILD_CARLA_SERVER=OFF -DBUILD_CARLA_UNREAL=OFF -DBUILD_PYTHON_API=OFF \
    -DBUILD_EXAMPLES=ON -DBUILD_LIBCARLA_TESTS=OFF -DENABLE_ROS2=OFF -DENABLE_RSS=OFF -DBUILD_OSM_WORLD_RENDERER=OFF \
    -DCMAKE_PROJECT_Boost_INCLUDE_BEFORE="$CB/boost_no_python.cmake" > "$CB/cmake-configure.log" 2>&1 \
    || { tail -30 "$CB/cmake-configure.log"; die "CARLA configure failed"; }
  grep -E "CARLA version string" "$CB/cmake-configure.log" || true
  ninja -C "$CB/build" -j "$JOBS" carla-client > "$CB/build-client.log" 2>&1 \
    || { grep -m10 -E "error:|FAILED" "$CB/build-client.log"; die "carla-client build failed"; }
  ninja -C "$CB/build" -j "$JOBS" carla-example-client > "$CB/build-example.log" 2>&1 \
    || { grep -m10 -E "error:|undefined reference|FAILED" "$CB/build-example.log"; die "carla-example-client link failed"; }
  ninja -C "$CB/build" -t commands carla-client > "$CB/commands-client.txt"
  grep "carla/client/World.cpp" "$CB/commands-client.txt" | sed -n 1p > "$CB/compile-command-World.txt"
  [ -s "$CB/compile-command-World.txt" ] || die "no compile command of carla/client/World.cpp"
  ninja -C "$CB/build" -t commands carla-example-client > "$CB/commands-example.txt"
  tail -n 1 "$CB/commands-example.txt" > "$CB/example-link-command.txt"
  # The bundle for Bazel (DA-P8 h): headers from a client unit's include roots, archives in the example's link order.
  python3 - "$CB" <<'PY'
import json, os, shlex, shutil, sys
cb = sys.argv[1]; bundle = cb + '/libcarla10-bundle'; bd = cb + '/build'
shutil.rmtree(bundle, ignore_errors=True); os.makedirs(bundle + '/inc'); os.makedirs(bundle + '/lib')
toks = shlex.split(open(cb + '/compile-command-World.txt').read().strip())
incs, defs, i = [], [], 0
while i < len(toks):
    t = toks[i]
    if t in ('-isystem', '-I', '-iquote'):
        incs.append(toks[i + 1]); i += 2; continue
    if t.startswith('-isystem') and len(t) > 8: incs.append(t[8:])
    elif t.startswith('-I'): incs.append(t[2:])
    elif t.startswith('-D'): defs.append(t[2:])
    i += 1
incs = [p if os.path.isabs(p) else os.path.normpath(os.path.join(bd, p)) for p in incs]
ext = ('.h', '.hpp', '.hh', '.hxx', '.ipp', '.inl', '.tcc', '.inc', '.def')
n = 0
for d in incs:
    for root, dirs, files in os.walk(d):
        dirs[:] = [x for x in dirs if x != 'CMakeFiles']
        for f in files:
            if not f.endswith(ext):
                continue
            src = os.path.join(root, f); dst = os.path.join(bundle, 'inc', os.path.relpath(src, d))
            if os.path.exists(dst):
                continue
            os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy2(src, dst); n += 1
link = shlex.split(open(cb + '/example-link-command.txt').read().strip())
archives = []
for t in link:
    if t.endswith('.a'):
        p = t if os.path.isabs(t) else os.path.normpath(os.path.join(bd, t))
        if p not in archives:
            archives.append(p)
assert archives, 'no archive on the example link line'
libs = []
for k, p in enumerate(archives):
    name = os.path.basename(p)
    if name in [os.path.basename(x) for x in libs]:
        name = '%02d_%s' % (k, name)
    shutil.copy2(p, os.path.join(bundle, 'lib', name)); libs.append(os.path.join(bundle, 'lib', name))
defs = [d for d in defs if d != 'NDEBUG']
linkopts = sorted(set(t for t in link if t.startswith('-l'))) or ['-lpthread']
for need in ('-lpthread', '-ldl', '-lm'):
    if need not in linkopts:
        linkopts.append(need)
json.dump(dict(include_roots=incs, headers_copied=n, defines=defs, archives=archives, linkopts=linkopts),
          open(cb + '/bundle.json', 'w'), indent=1)
srcs = ',\n        '.join('"lib/%s"' % os.path.basename(x) for x in libs)
open(cb + '/libcarla10.BUILD', 'w').write('''# CARLA 1.0 C++ client (carla-simulator/carla 14ac3b1a50), built by CARLA's CMake with the S-CORE gcc 12.2.0;
# archives in the link order of upstream's in-tree example, headers from a client unit's include roots
# (generated by build_score_bench.sh, the recipe of DA-P8 h).
cc_library(
    name = "client",
    srcs = [
        %s,
    ],
    hdrs = glob(["inc/**/*.h", "inc/**/*.hpp"]),
    textual_hdrs = glob(["inc/**"], exclude = ["inc/**/*.h", "inc/**/*.hpp"]),
    defines = %s,
    includes = ["inc"],
    linkopts = %s,
    linkstatic = True,
    visibility = ["//visibility:public"],
)
''' % (srcs, json.dumps(defs), json.dumps(linkopts)))
print('CARLA bundle: %d archives, %d headers' % (len(libs), n))
PY
  mark_done carla
fi
ls "$CB/libcarla10-bundle/lib" | wc -l

# ---------------------------------------------------------------------------------------------------------------------
step opencv
if ! is_done opencv; then
  fetch opencv-4.6.0.tar.gz "$OPENCV_URL" "$OPENCV_SHA256"
  rm -rf "$ROOT/src/opencv-4.6.0" "$ROOT/src/opencv-build"
  tar -xzf "$ROOT/dl/opencv-4.6.0.tar.gz" -C "$ROOT/src"
  cat > "$ROOT/tools/pkg-config-score" <<'EOF'
#!/bin/sh
# pkg-config for CMake configures with the S-CORE sysroot (build_score_bench.sh): no host system include directory
unset PKG_CONFIG_ALLOW_SYSTEM_CFLAGS
export PKG_CONFIG_SYSTEM_INCLUDE_PATH=/usr/include:/usr/include/x86_64-linux-gnu
exec /usr/bin/pkg-config "$@"
EOF
  chmod 0755 "$ROOT/tools/pkg-config-score"
  PKG_CONFIG_ALLOW_SYSTEM_CFLAGS=1 "$ROOT/tools/pkg-config-score" --cflags-only-I gstreamer-app-1.0 gstreamer-video-1.0 \
    | tr ' ' '\n' > "$ROOT/facts/pkg-config-score-gstreamer.txt"
  if grep -qxE -- '-I/usr/include(/x86_64-linux-gnu)?' "$ROOT/facts/pkg-config-score-gstreamer.txt"; then
    die "pkg-config-score still returns a host system include directory"
  fi
  # Static, with the S-CORE gcc; the image codecs from OpenCV's own sources; videoio with the GStreamer back end
  # (the visualization recorder's nvh264enc pipeline), found through pkg-config on the host (C libraries); highgui
  # without a GUI back end (visualization_on = false on the bench).
  cmake -S "$ROOT/src/opencv-4.6.0" -B "$ROOT/src/opencv-build" -G Ninja -DCMAKE_TOOLCHAIN_FILE="$ROOT/score-gcc.cmake" \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$TP/opencv" -DCMAKE_INSTALL_LIBDIR=lib \
    -DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=BOTH -DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=BOTH \
    -DPKG_CONFIG_EXECUTABLE="$ROOT/tools/pkg-config-score" \
    -DBUILD_LIST=core,imgproc,imgcodecs,videoio,highgui -DBUILD_SHARED_LIBS=OFF \
    -DWITH_GSTREAMER=ON -DWITH_FFMPEG=OFF -DWITH_V4L=OFF -DWITH_1394=OFF -DWITH_GTK=OFF -DWITH_QT=OFF -DWITH_VTK=OFF \
    -DWITH_OPENGL=OFF -DWITH_IPP=OFF -DWITH_ITT=OFF -DWITH_OPENCL=OFF -DWITH_CUDA=OFF -DWITH_EIGEN=OFF -DWITH_LAPACK=OFF \
    -DWITH_OPENMP=OFF -DWITH_PROTOBUF=OFF -DWITH_TIFF=OFF -DWITH_WEBP=OFF -DWITH_OPENEXR=OFF -DWITH_JASPER=OFF \
    -DWITH_OPENJPEG=OFF -DWITH_GDAL=OFF -DWITH_GPHOTO2=OFF -DWITH_IMGCODEC_HDR=ON -DBUILD_ZLIB=ON -DBUILD_PNG=ON \
    -DBUILD_JPEG=ON -DBUILD_TESTS=OFF -DBUILD_PERF_TESTS=OFF -DBUILD_opencv_apps=OFF -DBUILD_JAVA=OFF \
    -DBUILD_opencv_python3=OFF -DCV_TRACE=OFF > "$ROOT/logs/opencv-cmake.log" 2>&1 \
    || { tail -30 "$ROOT/logs/opencv-cmake.log"; die "OpenCV configure failed"; }
  # CMake prefixes its status lines with "--": the summary line reads "--     GStreamer:   YES (1.20.3)"
  grep -E "^--\s+GStreamer:" "$ROOT/logs/opencv-cmake.log" || true
  grep -qE "^--\s+GStreamer:\s+YES" "$ROOT/logs/opencv-cmake.log" \
    || die "OpenCV found no GStreamer (see $ROOT/logs/opencv-cmake.log); the recorder's nvh264enc path needs it"
  grep -E "^GSTREAMER_[a-z]+_INCLUDE_DIRS:" "$ROOT/src/opencv-build/CMakeCache.txt" | tr ';=' '\n\n' \
    > "$ROOT/facts/opencv-gstreamer-include-dirs.txt"
  if grep -qxE '/usr/include(/x86_64-linux-gnu)?' "$ROOT/facts/opencv-gstreamer-include-dirs.txt"; then
    die "OpenCV's GStreamer include directories hold a host system directory (CMakeCache.txt)"
  fi
  ninja -C "$ROOT/src/opencv-build" -j "$JOBS" install > "$ROOT/logs/opencv-build.log" 2>&1 \
    || { grep -m10 -E " error|FAILED" "$ROOT/logs/opencv-build.log"; die "OpenCV build failed"; }
  mark_done opencv
fi
find "$TP/opencv" -name "*.a" | sort

# ---------------------------------------------------------------------------------------------------------------------
step rerun
if ! is_done rerun; then
  fetch rerun_cpp_sdk-0.34.1.zip "$RERUN_URL" "$RERUN_SHA256"
  rm -rf "$ROOT/src/rerun_cpp_sdk" "$ROOT/src/rerun-build"
  unzip -q "$ROOT/dl/rerun_cpp_sdk-0.34.1.zip" -d "$ROOT/src"
  # Rerun's CMake downloads and builds Arrow C++ 18.0.0 (URL and MD5 fixed in the pinned SDK archive).
  cmake -S "$ROOT/src/rerun_cpp_sdk" -B "$ROOT/src/rerun-build" -G Ninja -DCMAKE_TOOLCHAIN_FILE="$ROOT/score-gcc.cmake" \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$TP/rerun" -DCMAKE_INSTALL_LIBDIR=lib \
    > "$ROOT/logs/rerun-cmake.log" 2>&1 || { tail -30 "$ROOT/logs/rerun-cmake.log"; die "Rerun configure failed"; }
  ninja -C "$ROOT/src/rerun-build" -j "$JOBS" install > "$ROOT/logs/rerun-build.log" 2>&1 \
    || { grep -m10 -iE "error|failed" "$ROOT/logs/rerun-build.log"; die "Rerun build failed"; }
  mark_done rerun
fi
find "$TP/rerun" -name "*.a" | sort

# ---------------------------------------------------------------------------------------------------------------------
step thirdparty
fetch eigen-5.0.0.tar.gz "$EIGEN_URL" "$EIGEN_SHA256"
fetch ort-gpu-linux-$ORT_VERSION.nupkg "$ORT_URL" "$ORT_SHA256"
if ! is_done thirdparty; then
  rm -rf "$TP/eigen" "$TP/onnxruntime" "$TP/solver" "$TP/boost" "$TP/hostinc"
  # Eigen 5.0.0 headers
  mkdir -p "$TP/eigen" && tar -xzf "$ROOT/dl/eigen-5.0.0.tar.gz" -C "$TP/eigen" --strip-components=1 eigen-5.0.0/Eigen
  # ONNX Runtime 1.26.0 GPU: the shared libraries and the headers of the NuGet package
  mkdir -p "$TP/onnxruntime/lib" "$TP/onnxruntime/include" "$ROOT/src/ort"
  unzip -q -o "$ROOT/dl/ort-gpu-linux-$ORT_VERSION.nupkg" 'runtimes/linux-x64/native/*' 'buildTransitive/native/include/*' -d "$ROOT/src/ort"
  N=$ROOT/src/ort/runtimes/linux-x64/native
  echo "$ORT_LIBONNXRUNTIME_SHA256  $N/libonnxruntime.so" | sha256sum -c --quiet - || die "libonnxruntime.so differs"
  echo "$ORT_PROVIDERS_CUDA_SHA256  $N/libonnxruntime_providers_cuda.so" | sha256sum -c --quiet - || die "providers_cuda differs"
  echo "$ORT_PROVIDERS_SHARED_SHA256  $N/libonnxruntime_providers_shared.so" | sha256sum -c --quiet - || die "providers_shared differs"
  cp "$N/libonnxruntime.so" "$TP/onnxruntime/lib/libonnxruntime.so.1"
  ln -sf libonnxruntime.so.1 "$TP/onnxruntime/lib/libonnxruntime.so"
  cp "$N/libonnxruntime_providers_cuda.so" "$N/libonnxruntime_providers_shared.so" "$TP/onnxruntime/lib/"
  cp "$ROOT"/src/ort/buildTransitive/native/include/*.h "$TP/onnxruntime/include/"
  # CppAD and Ipopt headers of Ubuntu 22.04, Ipopt's as coin-or/ (CppAD includes <coin-or/IpIpoptApplication.hpp>; the
  # package installs /usr/include/coin, as upstream's Dockerfile notes)
  mkdir -p "$TP/solver/include"
  cp -a /usr/include/cppad "$TP/solver/include/cppad"
  ipopt_header=$(find /usr/include -name IpIpoptApplication.hpp -print -quit)
  [ -n "$ipopt_header" ] || die "no IpIpoptApplication.hpp under /usr/include (coinor-libipopt-dev)"
  cp -a "$(dirname "$ipopt_header")" "$TP/solver/include/coin-or"
  # One Boost in the process: the headers of the Boost that CARLA's build fetched (all libraries of that release)
  BS=$CB/build/_deps/boost-src
  [ -d "$BS/libs/beast/include/boost" ] || die "CARLA's Boost source has no Beast ($BS)"
  mkdir -p "$TP/boost/include/boost"
  for d in "$BS"/libs/*/include/boost "$BS"/libs/numeric/*/include/boost; do
    if [ -d "$d" ]; then cp -rn "$d/." "$TP/boost/include/boost/"; fi
  done
  # nlohmann json and the GStreamer/GLib include directories of the host, copied: no host include root in a compile
  mkdir -p "$TP/hostinc/gstreamer"
  cp -a /usr/include/nlohmann "$TP/hostinc/nlohmann"
  GST_MODULES="gstreamer-app-1.0 gstreamer-sdp-1.0 gstreamer-webrtc-1.0 gstreamer-video-1.0 gstreamer-pbutils-1.0
    gstreamer-riff-1.0 gstreamer-audio-1.0 gstreamer-base-1.0 gstreamer-1.0"
  # shellcheck disable=SC2086
  pkg-config --exists $GST_MODULES || die "pkg-config does not find every GStreamer module: $GST_MODULES"
  gst_includes=""
  # shellcheck disable=SC2086
  for d in $(pkg-config --cflags-only-I $GST_MODULES | tr ' ' '\n' | sed -n 's/^-I//p' | sort -u); do
    case "$d" in
      /usr/include|/usr/include/x86_64-linux-gnu) die "pkg-config returned $d as a GStreamer include directory" ;;
    esac
    name=$(echo "${d#/}" | tr '/' '_')
    cp -a "$d" "$TP/hostinc/gstreamer/$name"
    gst_includes="$gst_includes\"hostinc/gstreamer/$name\", "
  done
  # The host shared libraries, by full path (the sysroot stays the linker's library search path)
  resolve() {
    local lib=$1 p
    for p in /usr/lib/x86_64-linux-gnu/lib$lib.so /usr/lib/lib$lib.so; do
      [ -e "$p" ] && { echo "$p"; return 0; }
    done
    die "no shared library lib$lib.so on this host"
  }
  gst_libs=""
  # shellcheck disable=SC2086
  for l in $(pkg-config --libs-only-l $GST_MODULES | tr ' ' '\n' | sed -n 's/^-l//p' | awk '!seen[$0]++'); do
    gst_libs="$gst_libs\"$(resolve "$l")\", "
  done
  solver_libs="\"$(resolve ipopt)\", \"$(resolve cppad_lib)\", "
  sed -e "s|@HOST_GSTREAMER_LIBS@|$gst_libs|" -e "s|@HOST_SOLVER_LIBS@|$solver_libs|" \
      -e "s|@HOST_GSTREAMER_INCLUDES@|$gst_includes|" "$HERE/workspace/thirdparty.BUILD.in" > "$ROOT/thirdparty.BUILD"
  ! grep -q "@HOST_" "$ROOT/thirdparty.BUILD" || die "thirdparty.BUILD has an unfilled placeholder"
  mark_done thirdparty
fi
grep -E "^HOST_|\"hostinc" "$ROOT/thirdparty.BUILD"

# ---------------------------------------------------------------------------------------------------------------------
step gateway
if ! is_done gateway; then
  cd "$GW"
  git checkout -q -- MODULE.bazel
  # Probe P5's three version lines: Communication 0.6.0, Baselibs 0.2.17 (the 0.5.0-era patches still apply) and
  # Lifecycle 0.10.0, the module set of the S-CORE workspace, so that gatewayd speaks the candidate's mw::com.
  python3 - MODULE.bazel <<'PY'
import sys
path = sys.argv[1]; text = open(path).read()
edits = [
    ('bazel_dep(name = "score_communication", version = "0.5.0")',
     'bazel_dep(name = "score_communication", version = "0.6.0")'),
    ('bazel_dep(name = "score_baselibs", version = "0.2.16")',
     'bazel_dep(name = "score_baselibs", version = "0.2.17")\n'
     'bazel_dep(name = "score_lifecycle", version = "0.10.0")\n'
     'single_version_override(\n    module_name = "score_lifecycle",\n    version = "0.10.0",\n)\n'),
]
for old, new in edits:
    assert text.count(old) == 1, "not found once: " + old
    text = text.replace(old, new)
open(path, 'w').write(text)
print("gateway MODULE.bazel: communication 0.6.0, baselibs 0.2.17, lifecycle 0.10.0")
PY
  git diff MODULE.bazel > "$ROOT/facts/gateway-MODULE.bazel.diff"
  rm -rf de4sdv_driver_assistance && mkdir de4sdv_driver_assistance
  cp "$BENCH"/score-path/config/*.json de4sdv_driver_assistance/
  cp "$BENCH/score-path/config/gateway_overlay.BUILD.bazel" de4sdv_driver_assistance/BUILD.bazel
  if ! bazel_gw build -c opt --jobs="$JOBS" //score/gatewayd //score/someipd //score/serializer:null_serializer \
      //de4sdv_driver_assistance:someip_gateway_config_warning > "$ROOT/logs/gateway-bazel.log" 2>&1; then
    grep -E "^ERROR|error:" "$ROOT/logs/gateway-bazel.log" | sed -n 1,20p; die "gateway build failed"
  fi
  tail -n 3 "$ROOT/logs/gateway-bazel.log"
  bazel_gw mod explain score_communication score_baselibs > "$ROOT/facts/gateway-mod-explain.txt" 2>&1 || true
  mark_done gateway
fi
cd "$GW"
GB=$(bazel_gw info -c opt bazel-bin)
H=$GW/score/serializer/pre_serialized_data.h
echo "$GATEWAY_PRE_SERIALIZED_DATA_SHA256  $H" | sha256sum -c --quiet - || die "the gateway's pre_serialized_data.h differs from pins.sh"

# ---------------------------------------------------------------------------------------------------------------------
step bazel
cd "$WS"
# stage the bench's packages: //visionpilot, //de4sdv_da_bench/{interfaces,actuation-adapter,launch-manager,
# score-build/workspace}
rm -rf "$WS/visionpilot" "$OVERLAY"
mkdir -p "$WS/visionpilot" "$OVERLAY/interfaces" "$OVERLAY/actuation-adapter" "$OVERLAY/launch-manager" \
  "$OVERLAY/score-build/workspace/gateway_include/score/serializer"
(cd "$VP/VisionPilot" && tar --exclude='*.onnx' --exclude='*.pt' --exclude='*.pth' --exclude='*.mp4' -cf - .) | tar -xf - -C "$WS/visionpilot"
cp "$HERE/workspace/visionpilot.BUILD.bazel" "$WS/visionpilot/BUILD.bazel"
cp -a "$BENCH/interfaces/include" "$OVERLAY/interfaces/"
cp "$HERE/workspace/interfaces.BUILD.bazel" "$OVERLAY/interfaces/BUILD.bazel"
(cd "$BENCH/actuation-adapter" && tar --exclude='.build' --exclude='__pycache__' -cf - .) | tar -xf - -C "$OVERLAY/actuation-adapter"
cp "$BENCH/launch-manager/config/launch_manager_config.json" "$BENCH/score-path/config/launch_manager_config_path_only.json" \
  "$OVERLAY/launch-manager/"
cp "$HERE/workspace/launch_manager.BUILD.bazel" "$OVERLAY/launch-manager/BUILD.bazel"
cp "$HERE/workspace/BUILD.bazel" "$HERE/workspace/ort_cuda_check.cpp" "$OVERLAY/score-build/workspace/"
cp "$CB/libcarla10.BUILD" "$ROOT/thirdparty.BUILD" "$OVERLAY/score-build/workspace/"
cp "$H" "$OVERLAY/score-build/workspace/gateway_include/score/serializer/"
# the identity recorder (lane B4) joins TARGETS and the bundle once its package exists
TARGETS=(//visionpilot:VisionPilot //de4sdv_da_bench/actuation-adapter:actuation_adapter
         //de4sdv_da_bench/score-build/workspace:ort_cuda_check
         @score_lifecycle//score/launch_manager:launch_manager //de4sdv_da_bench/launch-manager:de4sdv_lm_config
         //de4sdv_da_bench/launch-manager:de4sdv_lm_config_path_only)
start=$(date +%s)
if ! bazel_feo build --config=x86_64-linux -c opt --jobs="$JOBS" --features=-treat_warnings_as_errors "${TARGETS[@]}" \
    > "$ROOT/logs/score-bazel.log" 2>&1; then
  grep -E "^ERROR|error:|undefined reference" "$ROOT/logs/score-bazel.log" | sed -n 1,30p
  die "Bazel build of VisionPilot, the actuation adapter, ort_cuda_check, the Launch Manager or its configuration failed"
fi
tail -n 8 "$ROOT/logs/score-bazel.log"
echo "bazel build: $(( $(date +%s) - start )) s"
bazel_feo mod explain score_lifecycle score_communication score_baselibs > "$ROOT/facts/score-mod-explain.txt" 2>&1 || true
life_versions=$(grep -o -E 'score_lifecycle@[^ ,)]*' "$ROOT/facts/score-mod-explain.txt" | sort -u | tr '\n' ' ' || true)
echo "score_lifecycle as resolved: ${life_versions:-not shown by bazel mod explain}"
for v in $life_versions; do
  [ "$v" = "score_lifecycle@0.10.0" ] || die "Bazel resolved $v, not score_lifecycle@0.10.0 (facts/score-mod-explain.txt)"
done
bazel_feo aquery --config=x86_64-linux -c opt 'mnemonic("CppCompile", //visionpilot:de4sdv_score_carla_client)' 2>/dev/null \
  | grep -o -E "x86_64-unknown-linux-gnu-g\+\+|-std=[a-z+0-9]*" | sort | uniq -c > "$ROOT/facts/carla_unit_std.txt" || true
cat "$ROOT/facts/carla_unit_std.txt"

# ---------------------------------------------------------------------------------------------------------------------
step bundle
B=$ROOT/bundle
rm -rf "$B" && mkdir -p "$B/bin" "$B/lib" "$B/config/visionpilot" "$B/config/gateway" "$B/config/launch_manager" \
  "$B/config/actuation_adapter" "$B/share/visionpilot" "$B/facts"
# The output directory of the build above from cquery: `bazel info --config=x86_64-linux` stops with "Repository
# '@@score_bazel_platforms' is not defined" (the config's --platforms label), while cquery resolves it as the build did.
VPO=$(bazel_feo cquery --config=x86_64-linux -c opt --output=files //visionpilot:VisionPilot 2>/dev/null | tail -n 1)
[ "${VPO%/visionpilot/VisionPilot}" != "$VPO" ] || die "cquery gave no output file of //visionpilot:VisionPilot ($VPO)"
SB=$(bazel_feo info execution_root)/${VPO%/visionpilot/VisionPilot}
[ -f "$SB/visionpilot/VisionPilot" ] || die "no VisionPilot binary under $SB"
echo "S-CORE bazel-bin: $SB"
# bin/ holds the binary names of the Launch Manager configuration (binary_name): vision_pilot, actuation_adapter,
# gatewayd, someipd; identity_recorder joins with lane B4. launch_manager is the daemon, ort_cuda_check the GPU check.
cp -L "$SB/visionpilot/VisionPilot" "$B/bin/vision_pilot"
cp -L "$SB/de4sdv_da_bench/actuation-adapter/actuation_adapter" \
      "$SB/de4sdv_da_bench/score-build/workspace/ort_cuda_check" "$B/bin/"
LMD=$(find -L "$SB/external" -path '*score_lifecycle*/score/launch_manager/src/daemon/launch_manager' -type f -print -quit)
[ -n "$LMD" ] || die "no launch_manager daemon under $SB/external"
cp -L "$LMD" "$B/bin/launch_manager"
# each .bin beside the JSON it was converted from: score-path/scripts/stage_score_side.py stages a .bin only when
# that JSON is the bench's file of the mode (full; path: the warning path only, P10-3 and p10-1's late subscriber)
for c in launch_manager_config launch_manager_config_path_only; do
  LMC=$(find -L "$SB/de4sdv_da_bench/launch-manager" -name "$c.bin" -type f -print -quit)
  [ -n "$LMC" ] || die "no $c.bin under $SB/de4sdv_da_bench/launch-manager"
  cp -L "$LMC" "$B/config/launch_manager/"
done
cp "$BENCH/launch-manager/config/launch_manager_config.json" "$BENCH/score-path/config/launch_manager_config_path_only.json" \
  "$B/config/launch_manager/"
cp "$BENCH/actuation-adapter/mw_com_config_actuation_adapter.json" "$BENCH/actuation-adapter/config/adapter.json" \
   "$B/config/actuation_adapter/"
cp -L "$GB/score/gatewayd/gatewayd" "$GB/score/someipd/someipd" "$B/bin/"
cp -L "$TP/onnxruntime/lib/libonnxruntime.so.1" "$TP/onnxruntime/lib/libonnxruntime_providers_cuda.so" \
      "$TP/onnxruntime/lib/libonnxruntime_providers_shared.so" "$B/lib/"
SER=$(find -L "$GB/score/serializer" -maxdepth 1 -name 'score_com_serializer.so' -print -quit)
[ -n "$SER" ] || die "no score_com_serializer.so under $GB/score/serializer"
cp -L "$SER" "$B/lib/"
VS=$(find -L "$GB" -name libvsomeip3.so.3 -not -path '*.runfiles*' -print -quit)
[ -n "$VS" ] || die "no libvsomeip3.so.3 under $GB"
VL=$(dirname "$VS")
cp -L "$VL"/libvsomeip3*.so.3 "$B/lib/"
cp -L "$GB/de4sdv_driver_assistance/someip_gateway_config_warning.bin" "$BENCH"/score-path/config/*.json "$B/config/gateway/"
cp -a "$VP/VisionPilot/config/." "$B/config/visionpilot/"
# homography_C_matrix.yaml, which the candidate also reads (image_preprocessor.cpp:7), is no file at the pin: upstream's
# CMake build derives it from config/H.yaml with scripts/find_homography_C_matrix.py (CMakeLists.txt:49-53), which
# reads ../config/H.yaml from its working directory. Mode path and p10-1 stage it (score-path/scripts/README.md).
(cd "$VP/VisionPilot/scripts" && /usr/bin/python3 find_homography_C_matrix.py \
   --output "$B/config/visionpilot/homography_C_matrix.yaml") > "$ROOT/logs/homography_C_matrix.log" 2>&1 \
  || die "find_homography_C_matrix.py failed (logs/homography_C_matrix.log; it needs python3-opencv and python3-numpy)"
cp -a "$VP/VisionPilot/assets" "$B/share/visionpilot/assets"
mkdir -p "$B/share/visionpilot/modules/models/weights"
cp "$ROOT"/src/vp-pin/VisionPilot/modules/models/weights/*.onnx "$B/share/visionpilot/modules/models/weights/"
cp "$BENCH"/score-interface/patches/*.diff "$BENCH/score-interface/patches/SHA256SUMS" "$B/facts/"
cp "$ROOT"/facts/*.txt "$ROOT"/facts/*.diff "$B/facts/" 2>/dev/null || true
# the run-time packages of the S-CORE host (install_gpu_runtime.sh installs them): name=version where this host has
# the package installed, the bare name where it has not (dpkg-query prints "name=" for a package it knows but has
# not installed, and apt-get refuses an empty version)
for p in $APT_RUNTIME coinor-libipopt1v5 coinor-libipopt-dev libcppad-dev; do
  v=$(dpkg-query -W -f='${db:Status-Abbrev}|${Version}' "$p" 2>/dev/null || true)
  case "$v" in ii*) echo "$p=${v#*|}" ;; *) echo "$p" ;; esac
done > "$B/facts/apt-runtime-packages.txt"
{
  echo "VisionPilot $VP_COMMIT with $(cat "$BENCH/score-interface/patches/SHA256SUMS" | tr '\n' ' ')"
  echo "FEO $FEO_COMMIT; gateway $GATEWAY_COMMIT; CARLA $CARLA_COMMIT; ONNX Runtime $ORT_VERSION (nuget sha256 $ORT_SHA256)"
  echo "repository $(git -C "$REPO" rev-parse HEAD 2>/dev/null || echo unknown)"
} > "$B/facts/sources.txt"
# binary checks
{
  for f in "$B"/bin/*; do
    echo "== $(basename "$f")"; file "$f"
    readelf -d "$f" | grep -E "NEEDED|RUNPATH|RPATH" || true
    echo "max GLIBC $(objdump -T "$f" | grep -o 'GLIBC_[0-9.]*' | sort -V -u | tail -1)"
  done
  echo "== vision_pilot symbols"
  V=$B/bin/vision_pilot
  echo "carla::client $(nm -C "$V" | grep -c 'carla::client::')"
  echo "score::mw::com $(nm -C "$V" | grep -c 'score::mw::com')"
  echo "score::mw::lifecycle $(nm -C "$V" | grep -c 'score::mw::lifecycle')"
  echo "cv:: $(nm -C "$V" | grep -c ' cv::')"; echo "rerun:: $(nm -C "$V" | grep -c 'rerun::')"
  echo "CARLA version strings: $(strings "$V" | grep -E '^1\.0(-[0-9a-f]{9})?(-dirty)?$' | sort -u | tr '\n' ' ')"
  echo "== actuation_adapter symbols"
  echo "score::mw::lifecycle $(nm -C "$B/bin/actuation_adapter" | grep -c 'score::mw::lifecycle')"
  echo "== ldd with the bundle's lib/"
  for f in "$B"/bin/*; do echo "-- $(basename "$f")"; LD_LIBRARY_PATH=$B/lib ldd "$f" || true; done
} > "$B/facts/binary_checks.txt" 2>&1
if LD_LIBRARY_PATH=$B/lib ldd "$B/bin/vision_pilot" | grep "not found"; then die "vision_pilot has unresolved libraries"; fi
# both supervised processes hold the Lifecycle v0.10.0 client (report_running and the Alive API)
for f in vision_pilot actuation_adapter; do
  nm -C "$B/bin/$f" > "$ROOT/facts/$f.nm"
  for sym in score_mw_lifecycle_report_running 'score::mw::lifecycle::Alive::ReportAlive'; do
    grep -q -F "$sym" "$ROOT/facts/$f.nm" || die "$f does not hold the Lifecycle client symbol $sym"
  done
done
strings "$B/bin/vision_pilot" > "$B/facts/vision_pilot.strings"
grep -q -E '^1\.0-14ac3b1a5$' "$B/facts/vision_pilot.strings" || die "vision_pilot does not hold the CARLA client version string 1.0-14ac3b1a5"
# the ORT check on this host: the CUDA provider is in the build; loading it needs the GPU host (install_gpu_runtime.sh)
"$B/bin/ort_cuda_check" --cpu-only "$B/share/visionpilot/modules/models/weights/autosteer_fp32.onnx" 3 \
  > "$B/facts/ort_cuda_check_cpu.txt" 2>&1 || true
cat "$B/facts/ort_cuda_check_cpu.txt"
grep -q "ORT_CUDA_CHECK PASS" "$B/facts/ort_cuda_check_cpu.txt" || die "ort_cuda_check --cpu-only failed"
(cd "$B" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
tar -czf "$ROOT/da-b2-bundle.tgz" -C "$ROOT" bundle
echo
echo "=== BUILD OK $(date -u +%FT%TZ)"
echo "free under $ROOT: $(df -B1 --output=avail "$ROOT" | tail -1 | tr -dc 0-9) B"
echo "bundle: $B ($(du -sh "$B" | cut -f1)); archive $ROOT/da-b2-bundle.tgz sha256 $(sha256sum "$ROOT/da-b2-bundle.tgz" | cut -c1-64)"
echo "binaries and libraries (sha256):"
(cd "$B" && sha256sum bin/* lib/*)
echo "log: $LOG"
