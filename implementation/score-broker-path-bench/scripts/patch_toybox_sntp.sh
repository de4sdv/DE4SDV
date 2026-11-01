#!/usr/bin/env bash
# Enable the toybox sntp applet in the bench AOSP tree (INC-MW-011 phase 10, ASM-MW-030).
#
# set_ivi_clock.sh sets the IVI clock with the image's own SNTP client: `toybox sntp -s <host>`.
# The image's toybox has no such applet, and not for one reason but three, all inside
# external/toybox (each is enough on its own to keep the applet out):
#
#   1. android/device/generated/config.h carries `#define CFG_SNTP 0` and an empty
#      `#define USE_SNTP(...)`, so newtoys.h's USE_SNTP(...) entry expands to nothing.
#   2. Android.bp's device_srcs lists no toys/net/sntp.c, so the applet's source is not compiled.
#   3. android/device/generated/globals.h declares no sntp_data struct and no union member, so the
#      applet's GLOBALS(r, t, p, m, M) has nowhere to live.
#
# The tree ships no .config-* files, so its own regeneration flow (post_update.sh) cannot run;
# these are the three edits it would have produced. The build's own comment says a new toy needs
# the .config edit, the regeneration and the `srcs` edit.
#
#   patch_toybox_sntp.sh apply    apply the three edits and rebuild toybox
#   patch_toybox_sntp.sh check    tell whether the applet is in the built binary
#   patch_toybox_sntp.sh revert   restore the three tracked files (the undo)
#
# The edits touch only external/toybox, which is a git checkout, so `revert` uses git. Record
# `git -C external/toybox diff --stat` with the run: the change belongs to the bench image.
set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/bench_env.sh"

TOYBOX="$AOSP_TOP/external/toybox"
TOYBOX_BIN="$AOSP_TOP/out/target/product/$IVI_PRODUCT/system/bin/toybox"
DEVICE_CONFIG="$TOYBOX/android/device/generated/config.h"
DEVICE_GLOBALS="$TOYBOX/android/device/generated/globals.h"
TOYBOX_BP="$TOYBOX/Android.bp"

_apply_edits() {
  python3 - "$DEVICE_CONFIG" "$DEVICE_GLOBALS" "$TOYBOX_BP" <<'PY'
import re, sys

config_path, globals_path, bp_path = sys.argv[1:4]
changed = []

text = open(config_path).read()
if "#define CFG_SNTP 0" in text:
    text = text.replace("#define CFG_SNTP 0", "#define CFG_SNTP 1", 1)
    text = text.replace("#define USE_SNTP(...)\n#define SKIP_SNTP(...) __VA_ARGS__",
                        "#define USE_SNTP(...) __VA_ARGS__\n#define SKIP_SNTP(...)", 1)
    open(config_path, "w").write(text)
    changed.append("config.h")

text = open(bp_path).read()
if '"toys/net/sntp.c"' not in text:
    text = text.replace('    "toys/net/rfkill.c",',
                        '    "toys/net/rfkill.c",\n    "toys/net/sntp.c",', 1)
    open(bp_path, "w").write(text)
    changed.append("Android.bp")

text = open(globals_path).read()
if "struct sntp_data {" not in text:
    text = text.replace("extern union global_union {",
                        "struct sntp_data {\n  long r, t;\n  char *p, *m, *M;\n};\n\nextern union global_union {", 1)
    text = text.replace("\tstruct netstat_data netstat;",
                        "\tstruct netstat_data netstat;\n\tstruct sntp_data sntp;", 1)
    open(globals_path, "w").write(text)
    changed.append("globals.h")

print("changed:", ", ".join(changed) if changed else "(already applied)")
PY
}

apply() {
  [ -d "$TOYBOX" ] || { log "ERROR: no toybox checkout at $TOYBOX"; return 1; }
  _apply_edits || return 1
  local rc=0
  (
    set +u
    cd "$AOSP_TOP" || exit 1
    source build/envsetup.sh >/dev/null
    lunch "${IVI_PRODUCT}-${RELEASE}-${VARIANT}" >/dev/null || exit 1
    m toybox || exit 1
  ) 2>&1 | tail -5
  [ "${PIPESTATUS[0]:-0}" = 0 ] || rc=1
  [ "$rc" = 0 ] || { log "ERROR: the toybox rebuild failed"; return 1; }
  check || return 1
  git -C "$TOYBOX" diff --stat | tail -3 | sed 's/^/tree diff: /'
  log "toybox now has the sntp applet; push it to a running guest or rebuild the image"
}

check() {
  [ -f "$TOYBOX_BIN" ] || { log "ERROR: no toybox at $TOYBOX_BIN"; return 1; }
  local n; n="$(strings "$TOYBOX_BIN" | grep -c '^sntp$' || true)"
  if [ "${n:-0}" -ge 1 ]; then
    log "sntp present in $TOYBOX_BIN ($(stat -c%s "$TOYBOX_BIN") B)"
    return 0
  fi
  log "sntp ABSENT from $TOYBOX_BIN ($(stat -c%s "$TOYBOX_BIN") B)"
  return 1
}

revert() {
  git -C "$TOYBOX" checkout -- android/device/generated/config.h \
    android/device/generated/globals.h Android.bp 2>/dev/null \
    && log "restored the three tracked toybox files (rebuild toybox to get the old binary back)" \
    || { log "ERROR: the git restore failed"; return 1; }
}

case "${1:-}" in
  apply) apply ;;
  check) check ;;
  revert) revert ;;
  *) echo "usage: $0 {apply|check|revert}" >&2; exit 2 ;;
esac
