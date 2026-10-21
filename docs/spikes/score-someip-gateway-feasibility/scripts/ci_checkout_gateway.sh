#!/usr/bin/env bash
# DE4SDV throwaway spike (INC-MW-011 gateway feasibility), never merged.
# Checks out eclipse-score/inc_someip_gateway at the pinned commit, proves the
# identity (commit and tree) and a clean tree, and, with --overlay, adds the
# spike package //de4sdv_spike (new files only; no upstream file changes).
# Usage: ci_checkout_gateway.sh <dest> <facts-dir> [--overlay]
set -euo pipefail

dest=${1:?}
out=${2:?}
overlay=${3:-}
spike_dir=$(cd "$(dirname "$0")/.." && pwd)
: "${GATEWAY_REPO:?}" "${GATEWAY_SHA:?}"
mkdir -p "$out"

git init -q "$dest"
git -C "$dest" remote add origin "$GATEWAY_REPO"
git -C "$dest" fetch -q --depth 1 origin "$GATEWAY_SHA"
git -C "$dest" checkout -q --detach FETCH_HEAD

head=$(git -C "$dest" rev-parse HEAD)
tree=$(git -C "$dest" rev-parse 'HEAD^{tree}')
if [ "$head" != "$GATEWAY_SHA" ]; then
  echo "checked out $head, expected $GATEWAY_SHA" >&2
  exit 1
fi
if [ -n "$(git -C "$dest" status --porcelain --untracked-files=all)" ]; then
  echo "fresh checkout is not clean" >&2
  exit 1
fi

if [ "$overlay" = "--overlay" ]; then
  cp -r "$spike_dir/overlay/de4sdv_spike" "$dest/de4sdv_spike"
  cp "$spike_dir/config/someip_gateway_config.json" \
     "$spike_dir/config/mw_com_config_publisher.json" \
     "$spike_dir/config/mw_com_config_gatewayd.json" "$dest/de4sdv_spike/"
fi

status=$(git -C "$dest" status --porcelain --untracked-files=all)
modified=$(printf '%s\n' "$status" | grep -v '^?? de4sdv_spike/' | grep -v '^$' || true)
python3 - "$out/gateway_checkout.json" "$head" "$tree" "$overlay" "$modified" "$dest" <<'EOF'
import hashlib, json, pathlib, sys
path, head, tree, overlay, modified, dest = sys.argv[1:]
files = {}
if overlay == "--overlay":
    for f in sorted(pathlib.Path(dest, "de4sdv_spike").rglob("*")):
        if f.is_file():
            files[str(f.relative_to(dest))] = hashlib.sha256(f.read_bytes()).hexdigest()
json.dump({
    "repository": "https://github.com/eclipse-score/inc_someip_gateway.git",
    "commit": head,
    "tree": tree,
    "overlay_package_added": overlay == "--overlay",
    "overlay_files_sha256": files,
    "upstream_files_modified": [line for line in modified.splitlines() if line.strip()],
}, open(path, "w"), indent=2)
EOF
cat "$out/gateway_checkout.json"
if [ -n "$modified" ]; then
  echo "upstream files modified: $modified" >&2
  exit 1
fi
