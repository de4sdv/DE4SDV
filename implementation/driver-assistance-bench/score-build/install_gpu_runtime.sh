#!/usr/bin/env bash
# DE4SDV driver-assistance bench (INC-DRIVING-002): the native GPU runtime of the S-CORE host, and its checks.
#
# VisionPilot runs on the S-CORE host as a native process under the Launch Manager, not in a container (the
# supervision decision of 2026-11-18). Every GPU run before used upstream's container image, which brings its own CUDA
# runtime. This script installs, on the host itself, the CUDA and cuDNN runtime that the pinned ONNX Runtime GPU build
# needs, and checks that ONNX Runtime's CUDA provider loads and runs, and that GStreamer's nvh264enc encodes on the
# GPU (the visualization recorder's encoder).
#
# Host: x86_64 Ubuntu 22.04 with the NVIDIA driver already installed (580 on the L4 host). Run as a user with sudo:
#   implementation/driver-assistance-bench/score-build/install_gpu_runtime.sh [--bundle DIR] [--prefix DIR]
#     --bundle DIR  the bundle of build_score_bench.sh (bin/ort_cuda_check, lib/libonnxruntime*.so*, the networks);
#                   without it the script fetches the pinned ONNX Runtime package and compiles ort_cuda_check with g++
#     --prefix DIR  install directory (default /opt/de4sdv/gpu-runtime)
#
# What it installs (pins.sh): CUDA 12.8 Update 1 runtime libraries (cudart, cuBLAS/cuBLASLt, cuFFT, cuRAND, NVRTC,
# nvJitLink) and cuDNN 9.28.1.4 for CUDA 12, from NVIDIA's redistributable archives, each checked by sha256; one file
# /etc/ld.so.conf.d/de4sdv-cuda-<version>.conf so that the dynamic loader finds them (no environment variable needed
# in the Launch Manager's configuration); the Ubuntu run-time packages of the bundle (GStreamer, Ipopt, CppAD).
# ONNX Runtime 1.26.0's GPU package is a CUDA 12 build (CUDA 12.8, cuDNN 9), so CUDA 13 is not installed.
#
# Idempotent; logs every step to <prefix>/logs/; stops at the first failure with "GPU RUNTIME FAILED in step <step>:
# <reason>". The last line is "GPU RUNTIME OK" when every check passed.
set -Eeuo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=pins.sh
source "$HERE/pins.sh"

PREFIX=/opt/de4sdv/gpu-runtime
BUNDLE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --bundle) BUNDLE=$(cd "${2:?--bundle needs a directory}" && pwd); shift 2 ;;
    --prefix) PREFIX=${2:?--prefix needs a directory}; shift 2 ;;
    -h|--help) sed -n '2,26p' "$0"; exit 0 ;;
    *) echo "unknown argument $1" >&2; exit 2 ;;
  esac
done
if [ ! -d "$PREFIX" ] || [ ! -w "$PREFIX" ]; then
  sudo mkdir -p "$PREFIX" && sudo chown "$(id -u):$(id -g)" "$PREFIX"
fi
mkdir -p "$PREFIX/logs" "$PREFIX/dl" "$PREFIX/checks"
LOG=$PREFIX/logs/install-$(date -u +%Y%m%dT%H%M%SZ).log
exec > >(tee -a "$LOG") 2>&1

STEP=init
die() { echo "GPU RUNTIME FAILED in step $STEP: $*"; echo "log: $LOG"; exit 1; }
trap 'rc=$?; echo "GPU RUNTIME FAILED in step $STEP: command \"$BASH_COMMAND\" exited $rc (line $LINENO)"; echo "log: $LOG"; exit $rc' ERR
step() { STEP=$1; echo; echo "=== step $1 $(date -u +%FT%TZ)"; }

# fetch <file name> <url> <sha256> [size]: download into $PREFIX/dl (resumable, retried) and check the sha256.
fetch() {
  local name=$1 url=$2 sha=$3 size=${4:-} dst=$PREFIX/dl/$1 try
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
  if [ -n "$size" ] && [ "$(stat -c %s "$dst.part")" != "$size" ]; then
    die "$name has $(stat -c %s "$dst.part") bytes, pins.sh says $size"
  fi
  echo "$sha  $dst.part" | sha256sum -c --quiet - || die "sha256 of $name differs from pins.sh"
  mv "$dst.part" "$dst"
  echo "fetched $name (sha256 ok)"
}

CUDA_DIR=$PREFIX/cuda-$CUDA_VERSION-cudnn-$CUDNN_VERSION
LDCONF=/etc/ld.so.conf.d/de4sdv-cuda-$CUDA_VERSION.conf

# ---------------------------------------------------------------------------------------------------------------------
step preflight
[ "$(uname -m)" = x86_64 ] || die "this host is $(uname -m)"
. /etc/os-release
[ "${VERSION_ID:-}" = "22.04" ] || die "this host runs ${PRETTY_NAME:-unknown}; the bundle is built for Ubuntu 22.04"
command -v nvidia-smi > /dev/null || die "no nvidia-smi: the NVIDIA driver is not installed"
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader > "$PREFIX/checks/gpu.txt" \
  || die "nvidia-smi cannot query the GPU"
cat "$PREFIX/checks/gpu.txt"
driver=$(sed -n 1p "$PREFIX/checks/gpu.txt" | awk -F', ' '{print $2}')
[ "${driver%%.*}" -ge "$CUDA_MIN_DRIVER_MAJOR" ] || die "driver $driver is older than branch $CUDA_MIN_DRIVER_MAJOR, which CUDA $CUDA_VERSION needs"
free_gb=$(df -BG --output=avail "$PREFIX" | tail -1 | tr -dc 0-9)
[ "$free_gb" -ge 8 ] || die "only ${free_gb} GB free under $PREFIX; about 8 GB are needed"
if [ -n "$BUNDLE" ]; then
  [ -f "$BUNDLE/SHA256SUMS" ] || die "$BUNDLE has no SHA256SUMS: not a bundle of build_score_bench.sh"
  (cd "$BUNDLE" && sha256sum -c --quiet SHA256SUMS) || die "the bundle differs from its SHA256SUMS"
  echo "bundle $BUNDLE verified"
fi

# ---------------------------------------------------------------------------------------------------------------------
step cuda
while IFS='|' read -r name rel sha size; do
  [ -n "$name" ] || continue
  fetch "$(basename "$rel")" "$CUDA_REDIST/$rel" "$sha" "$size"
done <<< "$CUDA_ARCHIVES"
while IFS='|' read -r name rel sha size; do
  [ -n "$name" ] || continue
  fetch "$(basename "$rel")" "$CUDNN_REDIST/$rel" "$sha" "$size"
done <<< "$CUDNN_ARCHIVES"
if [ ! -f "$CUDA_DIR/.complete" ]; then
  rm -rf "$CUDA_DIR" && mkdir -p "$CUDA_DIR/lib" "$CUDA_DIR/licenses"
  while IFS='|' read -r name rel sha size; do
    [ -n "$name" ] || continue
    a=$PREFIX/dl/$(basename "$rel"); top=$(basename "$rel" .tar.xz)
    tar -xJf "$a" -C "$CUDA_DIR" "$top/lib" || die "extracting $top/lib from $a"
    tar -xJf "$a" -C "$CUDA_DIR" "$top/LICENSE" 2>/dev/null || echo "note: $a holds no $top/LICENSE"
    cp -a "$CUDA_DIR/$top/lib/." "$CUDA_DIR/lib/"
    if [ -f "$CUDA_DIR/$top/LICENSE" ]; then cp "$CUDA_DIR/$top/LICENSE" "$CUDA_DIR/licenses/$name.LICENSE"; fi
    rm -rf "${CUDA_DIR:?}/$top"
  done <<< "$CUDA_ARCHIVES
$CUDNN_ARCHIVES"
  # only the shared libraries: the static archives and stubs are build files
  find "$CUDA_DIR/lib" \( -name '*.a' -o -type d -name stubs -o -type d -name cmake \) -prune -exec rm -rf {} +
  touch "$CUDA_DIR/.complete"
fi
echo "$CUDA_DIR/lib" | sudo tee "$LDCONF" > /dev/null
sudo ldconfig
ldconfig -p > "$PREFIX/checks/ldconfig.txt"
for so in $ORT_CUDA_NEEDED; do
  grep -qE "^[[:space:]]+${so//./\\.} " "$PREFIX/checks/ldconfig.txt" || die "the dynamic loader does not find $so after ldconfig"
  echo "loader finds $so"
done

# ---------------------------------------------------------------------------------------------------------------------
step packages
if [ -n "$BUNDLE" ] && [ -s "$BUNDLE/facts/apt-runtime-packages.txt" ]; then
  PKGS=$(tr '\n' ' ' < "$BUNDLE/facts/apt-runtime-packages.txt")
else
  PKGS="$APT_RUNTIME $APT_PINNED"
fi
need_g=""
[ -n "$BUNDLE" ] || need_g="g++ unzip"
sudo DEBIAN_FRONTEND=noninteractive apt-get update -q
# shellcheck disable=SC2086
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q --no-install-recommends $PKGS $need_g
# shellcheck disable=SC2046
dpkg-query -W -f='${Package}=${Version}\n' $(for p in $PKGS; do echo "${p%%=*}"; done) > "$PREFIX/checks/apt-installed.txt"
cat "$PREFIX/checks/apt-installed.txt"

# ---------------------------------------------------------------------------------------------------------------------
step onnxruntime
if [ -n "$BUNDLE" ]; then
  ORT_LIB=$BUNDLE/lib
  CHECK=$BUNDLE/bin/ort_cuda_check
  MODEL=$BUNDLE/share/visionpilot/modules/models/weights/autosteer_fp32.onnx
else
  fetch "ort-gpu-linux-$ORT_VERSION.nupkg" "$ORT_URL" "$ORT_SHA256"
  O=$PREFIX/onnxruntime-$ORT_VERSION
  if [ ! -f "$O/lib/libonnxruntime.so.1" ]; then
    rm -rf "$O" "$PREFIX/ort-x" && mkdir -p "$O/lib" "$O/include" "$PREFIX/ort-x"
    unzip -q "$PREFIX/dl/ort-gpu-linux-$ORT_VERSION.nupkg" 'runtimes/linux-x64/native/*' 'buildTransitive/native/include/*' -d "$PREFIX/ort-x"
    N=$PREFIX/ort-x/runtimes/linux-x64/native
    cp "$N/libonnxruntime.so" "$O/lib/libonnxruntime.so.1"
    ln -sf libonnxruntime.so.1 "$O/lib/libonnxruntime.so"
    cp "$N/libonnxruntime_providers_cuda.so" "$N/libonnxruntime_providers_shared.so" "$O/lib/"
    cp "$PREFIX"/ort-x/buildTransitive/native/include/*.h "$O/include/"
  fi
  ORT_LIB=$O/lib
  CHECK=$PREFIX/checks/ort_cuda_check
  g++ -std=c++17 -O2 -I "$O/include" "$HERE/workspace/ort_cuda_check.cpp" -o "$CHECK" -L "$O/lib" -lonnxruntime \
    -Wl,-rpath,"$O/lib" || die "compiling ort_cuda_check with g++"
  MODEL=""
fi
echo "$ORT_PROVIDERS_CUDA_SHA256  $ORT_LIB/libonnxruntime_providers_cuda.so" | sha256sum -c --quiet - \
  || die "libonnxruntime_providers_cuda.so differs from pins.sh"
ldd "$ORT_LIB/libonnxruntime_providers_cuda.so" > "$PREFIX/checks/ldd_providers_cuda.txt" 2>&1 || true
cat "$PREFIX/checks/ldd_providers_cuda.txt"
! grep -q "not found" "$PREFIX/checks/ldd_providers_cuda.txt" || die "the CUDA provider has unresolved libraries (see above)"

# ---------------------------------------------------------------------------------------------------------------------
step ort-cuda-check
# shellcheck disable=SC2086
"$CHECK" $MODEL ${MODEL:+20} > "$PREFIX/checks/ort_cuda_check.txt" 2>&1 || true
cat "$PREFIX/checks/ort_cuda_check.txt"
grep -q "^ORT_CUDA_CHECK PASS" "$PREFIX/checks/ort_cuda_check.txt" || die "ONNX Runtime's CUDA provider did not load or run"

# ---------------------------------------------------------------------------------------------------------------------
step nvenc
ldconfig -p > "$PREFIX/checks/ldconfig.txt"
grep -qE "^[[:space:]]+libnvidia-encode\.so\.1 " "$PREFIX/checks/ldconfig.txt" \
  || die "no libnvidia-encode.so.1: the driver's video encoder library is missing; install the package of the installed driver branch (for example libnvidia-encode-${driver%%.*} or libnvidia-encode-${driver%%.*}-server, matching 'dpkg -l | grep nvidia-driver')"
gst-inspect-1.0 nvh264enc > "$PREFIX/checks/gst_nvh264enc.txt" 2>&1 || die "GStreamer has no nvh264enc (gst-inspect-1.0 nvh264enc failed)"
sed -n 1,12p "$PREFIX/checks/gst_nvh264enc.txt"
rm -f "$PREFIX/checks/nvenc.mkv"
gst-launch-1.0 -q videotestsrc num-buffers=100 ! video/x-raw,format=BGR,width=1920,height=1280,framerate=20/1 \
  ! videoconvert ! video/x-raw,format=NV12 ! nvh264enc ! h264parse ! matroskamux \
  ! filesink location="$PREFIX/checks/nvenc.mkv" > "$PREFIX/checks/gst_launch.txt" 2>&1 \
  || { cat "$PREFIX/checks/gst_launch.txt"; die "the nvh264enc test pipeline failed"; }
[ "$(stat -c %s "$PREFIX/checks/nvenc.mkv")" -gt 10000 ] || die "the nvh264enc test file is too small"
echo "nvh264enc encoded 100 frames of 1920x1280: $(stat -c %s "$PREFIX/checks/nvenc.mkv") bytes"

echo
echo "CUDA $CUDA_VERSION and cuDNN $CUDNN_VERSION in $CUDA_DIR/lib (loader: $LDCONF)"
echo "checks: $PREFIX/checks (gpu.txt, ort_cuda_check.txt, gst_nvh264enc.txt, nvenc.mkv)"
echo "log: $LOG"
echo "GPU RUNTIME OK"
