#!/usr/bin/env bash
# The patch series of a VisionPilot candidate of the DE4SDV S-CORE build (INC-DRIVING-002), chosen by DA_CANDIDATE:
#   pin    (the default) 0001-0003 of patches/, the series of the pin 014e0e7a: patches/SHA256SUMS lists it
#   pr427  0001-0003 and candidates/pr427/0004-de4sdv-port-of-upstream-pr427.diff, DE4SDV's port of the two fixes of
#          upstream draft PR #427 (decision D4's second candidate); candidates/pr427/SHA256SUMS lists 0004
#
# Usage: series.sh list           the series' diff files in apply order, one absolute path per line
#        series.sh extra          the diffs beyond 0001-0003 (none for pin)
#        series.sh check          sha256sum -c of every diff of the series against its SHA256SUMS
#        series.sh facts <dir>    copy the series' diffs into <dir> and write <dir>/SHA256SUMS listing each of them:
#                                 the bundle's facts/, the source difference that the staging copies and the identity
#                                 recorder hashes. For pin this is patches/*.diff and patches/SHA256SUMS byte for byte.
set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PATCHES=$HERE/patches
CANDIDATE=${DA_CANDIDATE:-pin}
case "$CANDIDATE" in
  pin) EXTRA_DIR="" ;;
  pr427) EXTRA_DIR=$HERE/candidates/pr427 ;;
  *) echo "series.sh: unknown candidate DA_CANDIDATE=$CANDIDATE (pin or pr427)" >&2; exit 2 ;;
esac

base() { find "$PATCHES" -maxdepth 1 -name '*.diff' | sort; }
extra() { if [ -n "$EXTRA_DIR" ]; then find "$EXTRA_DIR" -maxdepth 1 -name '*.diff' | sort; fi; }

case "${1:-}" in
  list) base; extra ;;
  extra) extra ;;
  check)
    (cd "$PATCHES" && sha256sum -c --quiet SHA256SUMS)
    if [ -n "$EXTRA_DIR" ]; then (cd "$EXTRA_DIR" && sha256sum -c --quiet SHA256SUMS); fi
    echo "series $CANDIDATE: sha256 ok" ;;
  facts)
    dest=${2:?usage: series.sh facts <dir>}
    mkdir -p "$dest"
    cp "$PATCHES"/*.diff "$PATCHES/SHA256SUMS" "$dest/"
    if [ -n "$EXTRA_DIR" ]; then
      cp "$EXTRA_DIR"/*.diff "$dest/"
      cat "$EXTRA_DIR/SHA256SUMS" >> "$dest/SHA256SUMS"
    fi ;;
  *) echo "usage: series.sh list|extra|check|facts <dir>" >&2; exit 2 ;;
esac
