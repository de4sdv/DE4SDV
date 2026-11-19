#!/usr/bin/env bash
# Checks the patch series of the DE4SDV S-CORE interface for VisionPilot at the pin:
#   1. the three patch files against patches/SHA256SUMS;
#   2. a fresh `git clone --shared` of a local VisionPilot clone, checked out at the pin and clean;
#   3. 0001 (the VIS8 visualization recorder) with `git apply --check`, then for real; then 0002 the same way;
#   4. `git diff` of the result against 0001 re-creates 0002 byte for byte; then 0003 (LocalDisplay without a window,
#      C-2) is checked and applied on top of 0002 the same way, and `git diff` against 0002 re-creates it;
#   5. optional, when OpenCV 4, ONNX Runtime and Eigen headers are given: g++ -fsyntax-only of the patched
#      vision_pilot.cpp and vision_pilot_config.cpp with and without ENABLE_SCORE_INTERFACE, and the preprocessed
#      vision_pilot.cpp without it compared between "0001" and "0001 + 0002".
#
# Usage: check_patch.sh <visionpilot-clone> [scratch-dir]
#   <visionpilot-clone>  a local clone that holds the pin (a blob-less partial clone is fine; the network weights are
#                        left out of the checkout)
#   ORT_INCLUDE, EIGEN_INCLUDE, OPENCV_INCLUDE  optional include directories for step 5
# From a blob-less source clone, git may print "invalid object ... .onnx" during the checkout: those are the weights
# the sparse checkout leaves out; the clean-tree check below still holds.
# Exit status 0 when steps 1-4 pass (and step 5, if it ran).
set -uo pipefail

PIN=014e0e7a56ee8e597c2cab8175233f74edd9b856
HERE=$(cd "$(dirname "$0")" && pwd)
PATCHES=$HERE/patches
INTERFACES=$(cd "$HERE/../interfaces/include" && pwd)
SOURCE=${1:?usage: check_patch.sh <visionpilot-clone> [scratch-dir]}
SCRATCH=${2:-${TMPDIR:?set TMPDIR or pass a scratch dir}/score-interface-check}
fail() { echo "FAIL $*"; exit 1; }

echo "=== check_patch $(date -u +%FT%TZ)"
(cd "$PATCHES" && sha256sum -c SHA256SUMS) || fail "patch sha256 differs from SHA256SUMS"

rm -rf "$SCRATCH" && mkdir -p "$SCRATCH" || fail "scratch $SCRATCH"
git clone -q --shared --no-checkout "$SOURCE" "$SCRATCH/vp" || fail "git clone --shared $SOURCE"
cd "$SCRATCH/vp" || exit 1
git config core.sparseCheckout true
printf '/*\n!*.onnx\n!*.pt\n!*.pth\n!*.mp4\n' > .git/info/sparse-checkout
git checkout -q "$PIN" || fail "checkout $PIN"
[ "$(git rev-parse HEAD)" = "$PIN" ] || fail "HEAD is not the pin"
[ -z "$(git status --porcelain)" ] || fail "fresh clone not clean"
echo "fresh clone at $(git rev-parse HEAD), clean"

git apply --check "$PATCHES/0001-de4sdv-visualization-recorder.diff" || fail "0001 --check"
echo "0001 git apply --check: ok"
git apply --index "$PATCHES/0001-de4sdv-visualization-recorder.diff" || fail "0001 apply"
echo "0001 applied"
mkdir -p "$SCRATCH/tree0001" && cp -r VisionPilot "$SCRATCH/tree0001/"
git apply --check "$PATCHES/0002-de4sdv-score-interface.diff" || fail "0002 --check on top of 0001"
echo "0002 git apply --check on top of 0001: ok"
git apply "$PATCHES/0002-de4sdv-score-interface.diff" || fail "0002 apply"
echo "0002 applied; against 0001:"
git add -N VisionPilot/modules/de4sdv/score_interface
git diff --stat | tail -1
# the abbreviation pinned to the patch's 8 hex digits: git's automatic length follows the clone's object count, and a
# depth-1 clone (build_score_bench.sh) writes 7-digit index lines
git -c core.abbrev=8 diff | cmp -s - "$PATCHES/0002-de4sdv-score-interface.diff" || fail "git diff does not re-create 0002"
echo "git diff against 0001 re-creates 0002 byte for byte"
# 0002's result becomes the index, the base of 0003 (no commit: a blob-less clone cannot write the tree)
git add -u VisionPilot && git add VisionPilot/modules/de4sdv/score_interface || fail "staging 0002's result"
git apply --check "$PATCHES/0003-de4sdv-headless-display.diff" || fail "0003 --check on top of 0002"
echo "0003 git apply --check on top of 0002: ok"
git apply "$PATCHES/0003-de4sdv-headless-display.diff" || fail "0003 apply"
git -c core.abbrev=8 diff | cmp -s - "$PATCHES/0003-de4sdv-headless-display.diff" || fail "git diff does not re-create 0003"
echo "git diff against 0002 re-creates 0003 byte for byte"

OPENCV_INCLUDE=${OPENCV_INCLUDE:-/usr/include/opencv4}
if [ -n "${ORT_INCLUDE:-}" ] && [ -n "${EIGEN_INCLUDE:-}" ] && [ -f "$OPENCV_INCLUDE/opencv2/core/mat.hpp" ]; then
  includes() {
    local tree=$1; local -a inc=()
    for d in $(find "$tree/VisionPilot/modules" -type d -name include | sort); do inc+=("-I$d"); done
    inc+=("-I$OPENCV_INCLUDE" "-I$ORT_INCLUDE" "-I$EIGEN_INCLUDE" "-I$INTERFACES")
    printf '%s\n' "${inc[@]}"
  }
  mapfile -t INC < <(includes "$SCRATCH/vp")
  for def in "" "-DENABLE_SCORE_INTERFACE=1"; do
    for f in app/vision_pilot.cpp modules/config/src/vision_pilot_config.cpp; do
      g++ -std=c++17 -fsyntax-only $def "${INC[@]}" "VisionPilot/$f" 2> "$SCRATCH/syntax.err" \
        || { cat "$SCRATCH/syntax.err"; fail "syntax $f $def"; }
      echo "syntax ok: $f ${def:-(ENABLE_SCORE_INTERFACE unset)}"
    done
  done
  mapfile -t INC1 < <(includes "$SCRATCH/tree0001")
  g++ -std=c++17 -E -P "${INC1[@]}" "$SCRATCH/tree0001/VisionPilot/app/vision_pilot.cpp" > "$SCRATCH/pp0001.ii" \
    || fail "preprocess 0001"
  g++ -std=c++17 -E -P "${INC[@]}" VisionPilot/app/vision_pilot.cpp > "$SCRATCH/pp0002.ii" || fail "preprocess 0002"
  diff "$SCRATCH/pp0001.ii" "$SCRATCH/pp0002.ii" > "$SCRATCH/pp.diff"
  echo "preprocessed vision_pilot.cpp without ENABLE_SCORE_INTERFACE, 0001 against 0001 + 0002:"
  cat "$SCRATCH/pp.diff"
  [ "$(grep -c '^[<>]' "$SCRATCH/pp.diff")" = 2 ] && grep -q '^> enum class SourceMode .*Score = 3' "$SCRATCH/pp.diff" \
    || fail "the preprocessed translation unit differs beyond the enum"
  echo "the preprocessed translation unit differs only in the enum line"
else
  echo "step 5 skipped: set ORT_INCLUDE and EIGEN_INCLUDE (and OPENCV_INCLUDE if not /usr/include/opencv4)"
fi
echo "=== check_patch: PASS"
