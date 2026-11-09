#!/usr/bin/env bash
# Read-only probe of the aaos-build AOSP tree, before any build (RUNBOOK step 3).
#
#   scripts/probe_aosp_tree.sh            # against $AOSP_TOP
#   AOSP_TOP=/path scripts/probe_aosp_tree.sh
#
# Option B (SOME/IP struct -> broker REFLECTION -> typed VSIDL message) rests on
# five facts about the shipped release that the documentation states but does not
# pin to a commit. This script finds the code that decides each one and prints what
# it found, so the answer is a file and a line, not an assumption. It changes
# nothing, starts nothing and needs no build.
#
# Verdicts:
#   OK       the fact is in the tree, with the file named
#   READ     the code exists but the rule is in a branch that has to be read; the
#            script prints the file and the matching lines
#   BLOCKER  the fact is absent; option B cannot work as written and the fallback
#            decision belongs to the owner (fallback-a/, RISKS R1/R2)
#
# Exit: 0 no blocker, 3 at least one blocker, 1 no tree.
set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/bench_env.sh"

SDV="$AOSP_TOP/system/software_defined_vehicle"
BLOCKERS=0
CHECKS=0

say() { printf '%s\n' "$*"; }
head2() { printf '\n=== %s ===\n' "$*"; }
verdict_ok()   { CHECKS=$((CHECKS + 1)); say "VERDICT: OK      $*"; }
verdict_read() { CHECKS=$((CHECKS + 1)); say "VERDICT: READ    $*"; }
verdict_block() { CHECKS=$((CHECKS + 1)); BLOCKERS=$((BLOCKERS + 1)); say "VERDICT: BLOCKER $*"; }

find_files() { # <name pattern> <dir>
  find "$2" -name "$1" -type f 2>/dev/null | head -20
}

if [ ! -d "$SDV" ]; then
  say "no SDV tree at $SDV (set AOSP_TOP); nothing probed"
  exit 1
fi
say "probing $SDV"
if command -v repo >/dev/null 2>&1 && [ -d "$AOSP_TOP/.repo" ]; then
  say "manifest: $(cd "$AOSP_TOP" && repo manifest -r 2>/dev/null | sha256sum | awk '{print $1}')"
else
  say "manifest: repo tool or .repo unavailable; record repo manifest -r by hand"
fi

# ---------------------------------------------------------------- 1. primitives
head2 "1. SomeIpPrimitive: which primitives does this release have?"
TYPE_PROTO="$(grep -rl 'enum SomeIpPrimitive' "$SDV" 2>/dev/null | head -3)"
if [ -n "$TYPE_PROTO" ]; then
  for file in $TYPE_PROTO; do say "  $file"; done
  VALUES="$(grep -h -A 40 'enum SomeIpPrimitive' $TYPE_PROTO 2>/dev/null | grep -oE '\b(UINT8|UINT16|UINT32|UINT64|INT8|INT16|INT32|INT64|FLOAT32|FLOAT64|BOOL|STRING)\b' | sort -u | tr '\n' ' ')"
  say "  values: $VALUES"
  case "$VALUES" in
    *UINT32*) : ;;
    *) verdict_block "no UINT32 in SomeIpPrimitive: the ICD's u32 cannot be mapped" ;;
  esac
  case "$VALUES" in
    *FLOAT32*) verdict_ok "UINT32 and FLOAT32 exist; the ICD needs nothing else" ;;
    *) verdict_block "no FLOAT32 in SomeIpPrimitive: the plan's floats cannot be mapped" ;;
  esac
  case "$VALUES" in
    *UINT64*) say "  NOTE: 64-bit exists here, but the ICD deliberately uses _s/_ns u32 pairs; no mapping change" ;;
    *) say "  NOTE: no 64-bit primitive, which is why the ICD carries times as u32 pairs. No change needed." ;;
  esac
else
  verdict_block "no 'enum SomeIpPrimitive' under $SDV: the type-definition vocabulary is not where the docs say"
fi

# ------------------------------------------------------------ 2. translation mode
head2 "2. MessageTranslationMode: is REFLECTION the default translator?"
MODE_FILES="$(grep -rl 'MessageTranslationMode' "$SDV" 2>/dev/null | head -5)"
if [ -n "$MODE_FILES" ]; then
  for file in $MODE_FILES; do
    say "  $file"
    grep -n -E 'REFLECTION|INTERPRET_AS_BYTES|message_translation_mode' "$file" | head -10 | sed 's/^/    /'
  done
  if grep -rq 'REFLECTION' $MODE_FILES 2>/dev/null; then
    verdict_ok "REFLECTION is a mode of this release"
  else
    verdict_block "no REFLECTION in the mode enum: option B has no translator"
  fi
else
  verdict_block "no MessageTranslationMode under $SDV"
fi

# ------------------------------------------------- 3. reflection of the fields
head2 "3. Does the translator fill repeated float and string fields?"
BROKER_SRC="$(grep -rl -E 'type_definition|SomeIpStruct' "$SDV" --include=*.cc --include=*.cpp --include=*.h 2>/dev/null | head -10)"
if [ -n "$BROKER_SRC" ]; then
  for file in $BROKER_SRC; do say "  $file"; done
  HITS="$(grep -rn -E 'RepeatedField|AddAlreadyAllocated|FieldDescriptor::TYPE_FLOAT|is_repeated|repeated' $BROKER_SRC 2>/dev/null | head -12)"
  if [ -n "$HITS" ]; then
    printf '%s\n' "$HITS" | sed 's/^/    /'
    verdict_read "the translator touches repeated fields; read the branch before the build (RUNBOOK gate G5)"
  else
    verdict_block "no repeated-field handling in the translator: a repeated float cannot be filled"
  fi
else
  verdict_block "no type_definition consumer found under $SDV: nothing reads the SomeIpStruct"
fi

# --------------------------------------------------------- 4. string convention
head2 "4. String framing: BOM and NUL, or raw bytes?"
STR_HITS="$(grep -rn -E '0xEF|0xBB|0xBF|\bBOM\b|bom|kUtf8|WriteString|string_encoding' "$SDV" --include=*.cc --include=*.h --include=*.cpp 2>/dev/null | head -15)"
if [ -n "$STR_HITS" ]; then
  printf '%s\n' "$STR_HITS" | sed 's/^/    /'
  say "  read these against ICD section 3: length covers BOM + bytes + NUL; an empty string is 00000004 EFBBBF 00"
  verdict_read "string framing is in the tree; the exact prefix rule decides G5's string fields"
else
  verdict_block "no string framing code found; the ICD's AUTOSAR convention cannot be checked"
fi

# ------------------------------------------------------ 5. array length in bytes
head2 "5. Array length: bytes or elements?"
ARR_HITS="$(grep -rn -E 'length_field_size|kFourByteLength|array_length|ArrayLength' "$SDV" --include=*.cc --include=*.h 2>/dev/null | head -12)"
if [ -n "$ARR_HITS" ]; then
  printf '%s\n' "$ARR_HITS" | sed 's/^/    /'
  verdict_read "the array length field is implemented; confirm it counts BYTES (64 floats = 256, not 64)"
else
  verdict_block "no array length handling found"
fi

# --------------------------------------------- 6. catalog and type registration
head2 "6. Catalog registration of a publication type"
CATALOG="$SAMPLES/some_ip/catalog"
if [ -d "$CATALOG" ]; then
  say "  top level:"
  ls -1 "$CATALOG" | head -20 | sed 's/^/    /'
  say "  Android.bp modules under the catalog:"
  grep -rn -E '^[a-z_]+ \{|name: ' "$CATALOG" --include=Android.bp 2>/dev/null | head -20 | sed 's/^/    /'
  say "  proto srcs of the broker bundle:"
  grep -rn -A 6 'proto_library\|proto: {' "$CATALOG" --include=Android.bp 2>/dev/null | head -20 | sed 's/^/    /'
  if grep -rh -E '^(proto_library|java_library|cc_library)' "$CATALOG" --include=Android.bp 2>/dev/null | grep -q proto_library; then
    verdict_ok "the catalog registers protobuf types with proto_library; CATALOG_MODULE_KIND=proto_library is right"
  else
    verdict_read "the catalog's module kinds are printed above; set CATALOG_MODULE_KIND to what it uses"
  fi
  say "  publisher entries in the broker catalog (do any name a type from another package?):"
  grep -rn -A 2 'publisher {' "$CATALOG/agent" 2>/dev/null | head -20 | sed 's/^/    /'
else
  verdict_block "no catalog at $CATALOG"
fi

# ------------------------------------- 7. does gatewayd forward the mw::com frame?
head2 "7. The mw::com operational-state frame: is the 4-byte prefix stripped before SOME/IP?"
say "  ICD section 2: the publisher's event is PreSerializedData<2048>, bytes 0-1 a little-endian"
say "  length, the struct from byte 4. The SOME/IP payload must be the struct alone (section 3)."
PREFIX_HITS="$(grep -rn -E 'PreSerializedData|kSerialized|SerializedData|operational_state|operationalState' "$SDV" --include=*.cc --include=*.h --include=*.json 2>/dev/null | head -12)"
if [ -n "$PREFIX_HITS" ]; then
  printf '%s\n' "$PREFIX_HITS" | sed 's/^/    /'
  verdict_read "find where the event buffer becomes the SOME/IP payload; if byte 0 is not dropped the struct starts 4 bytes late"
else
  verdict_read "no gatewayd/someipd source under this tree (the S-CORE gateway is a separate repo); settle it at G3 with a hexdump"
fi

head2 "summary"
say "$CHECKS checks, $BLOCKERS blocker(s)"
say "Record this output in the run directory: it is the tree-specific evidence behind RUNBOOK gates G1/G1b."
[ "$BLOCKERS" -eq 0 ] || exit 3
