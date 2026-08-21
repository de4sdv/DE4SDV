#!/usr/bin/env bash
set -Eeuo pipefail

# Stage the DE4SDV Vehicle.Speed reference service bundles into an AOSP tree.
# Generated Rust, Android.bp, APEX, key, permission, and orchestration files are
# written only to the AOSP staging tree and must not be committed to DE4SDV.

AOSP_ROOT=${AOSP_ROOT:?set AOSP_ROOT to the AOSP source checkout}
DE4SDV_ROOT=${DE4SDV_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)}
OUTPUT_ROOT=${OUTPUT_ROOT:-"$AOSP_ROOT/system/software_defined_vehicle/samples/de4sdv_vehicle_speed"}
VSIDLC=${VSIDLC:-"$AOSP_ROOT/out/host/linux-x86/bin/vsidlc"}

CATALOG_ROOT="$DE4SDV_ROOT/implementation/aaos-sdv-reference-interop-bench/contract"
OVERRIDE_ROOT="$DE4SDV_ROOT/implementation/aaos-sdv-reference-interop-bench/aosp/vehicle_speed_bridge/overrides"

[[ -d "$AOSP_ROOT/.repo" ]] || { printf 'AOSP_ROOT is not an AOSP checkout: %s\n' "$AOSP_ROOT" >&2; exit 2; }
[[ -x "$VSIDLC" ]] || { printf 'VSIDLC is not executable: %s\n' "$VSIDLC" >&2; exit 2; }
[[ -f "$CATALOG_ROOT/Android.bp" ]] || { printf 'catalog Android.bp is missing: %s\n' "$CATALOG_ROOT" >&2; exit 2; }
[[ -d "$OVERRIDE_ROOT/services" ]] || { printf 'service overrides are missing: %s\n' "$OVERRIDE_ROOT" >&2; exit 2; }

case "$OUTPUT_ROOT" in
  "$AOSP_ROOT"/*) ;;
  *) printf 'OUTPUT_ROOT must be inside AOSP_ROOT: %s\n' "$OUTPUT_ROOT" >&2; exit 2 ;;
esac

rm -rf "$OUTPUT_ROOT/contract" "$OUTPUT_ROOT/generated"
mkdir -p "$OUTPUT_ROOT"
cp -a "$CATALOG_ROOT" "$OUTPUT_ROOT/contract"

"$VSIDLC" \
  --catalog-path "$OUTPUT_ROOT/contract" \
  --output-path "$OUTPUT_ROOT/generated" \
  --genrule --services --apex --target-api latest \
  --rust-formatter none \
  --android-bp-formatter none \
  --textproto-formatter none \
  --no-pest

for module in \
  libsdv_mw_rs_de4sdv_reference_vehicle_speed_vehicle_speed_provider \
  libsdv_mw_rs_de4sdv_reference_vehicle_speed_vehicle_speed_observer \
  libsdv_lm_vehicle_speed_provider \
  libsdv_lm_vehicle_speed_observer; do
  if ! grep -R -q "name: \"$module\"" "$OUTPUT_ROOT/generated"; then
    printf 'VSIDL generation did not emit expected module: %s\n' "$module" >&2
    exit 1
  fi
done

for bundle in VehicleSpeedProvider VehicleSpeedObserver; do
  cp "$OVERRIDE_ROOT/services/$bundle/src/main.rs" \
    "$OUTPUT_ROOT/generated/services/$bundle/src/main.rs"
done

# --- Stage the SELinux additions (dedicated observer domain with TCP egress).
# The observer override reads the egress endpoint from
# persist.sdv.de4sdv.vehicle_speed_egress; reading it requires rustutils and
# the dedicated domain policy staged below.

SEPOLICY_SRC="$OVERRIDE_ROOT/../sepolicy"
SEPOLICY_SRC="$(cd "$SEPOLICY_SRC" && pwd)"
SDV_SEPOLICY_ROOT="$AOSP_ROOT/device/google/sdv/sdv_core_base/sepolicy/samples"

cp "$SEPOLICY_SRC/de4sdv_vehicle_speed_observer.te" \
  "$SDV_SEPOLICY_ROOT/product/private/de4sdv_vehicle_speed_observer.te"

cat "$SEPOLICY_SRC/service_bundle_contexts.append" \
  >> "$SDV_SEPOLICY_ROOT/service_bundle_contexts"

cat "$SEPOLICY_SRC/property_contexts.append" \
  >> "$SDV_SEPOLICY_ROOT/product/private/property_contexts"

# The generated observer Android.bp has no rustutils dependency; add it so the
# override's system-property read compiles.
OBSERVER_BP="$OUTPUT_ROOT/generated/services/VehicleSpeedObserver/Android.bp"
python3 - "$OBSERVER_BP" <<'PY'
import sys
path = sys.argv[1]
with open(path) as fh:
    text = fh.read()
if "librustutils" not in text:
    text = text.replace(
        '        "libfutures",\n',
        '        "libfutures",\n        "librustutils",\n',
        1,
    )
    with open(path, "w") as fh:
        fh.write(text)
print("patched rustutils into", path)
PY

printf '%s\n' "Staged DE4SDV Vehicle.Speed bridge at $OUTPUT_ROOT"
printf '%s\n' 'Generated files, including APEX signing material, are staging artifacts only.'
printf '%s\n' 'Build the generated modules explicitly before attempting target deployment:'
printf '%s\n' '  m libsdv_lm_vehicle_speed_provider libsdv_lm_vehicle_speed_observer'
