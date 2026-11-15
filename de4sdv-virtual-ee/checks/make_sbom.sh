#!/bin/sh
# Regenerate CycloneDX inventories from the immutable current baseline images.
# Requires syft plus the declared checks/requirements-dev.txt dependencies.
set -eu

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
OUT=${1:-$HERE/../sbom}
command -v syft >/dev/null 2>&1 || {
    echo "syft is required: https://github.com/anchore/syft (Apache-2.0)" >&2
    exit 1
}
exec "${PYTHON:-python3}" "$HERE/sbom_inventory.py" generate --out "$OUT"
