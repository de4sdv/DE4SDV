#!/bin/sh
# Regenerate the committed SBOMs (CycloneDX) for the images the baseline names.
#
# The committed files are gzipped because they are large and regenerated whenever an
# image changes; the recipe is what makes them reproducible, not the bytes in git.
set -eu

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
OUT=${1:-$HERE/../sbom}
ZONE=${ZONE_IMAGE:-localhost/de4sdv/zone-ecu:10}
GW=${GW_IMAGE:-localhost/de4sdv/can-gw:4}

command -v syft >/dev/null 2>&1 || {
    echo "syft is required: https://github.com/anchore/syft (Apache-2.0)" >&2
    exit 1
}

mkdir -p "$OUT"
syft "$ZONE" -o "cyclonedx-json=$OUT/zone-ecu.cdx.json"
syft "$GW" -o "cyclonedx-json=$OUT/can-gw.cdx.json"
gzip -9 -f "$OUT/zone-ecu.cdx.json" "$OUT/can-gw.cdx.json"
echo "wrote $OUT/zone-ecu.cdx.json.gz and $OUT/can-gw.cdx.json.gz"
