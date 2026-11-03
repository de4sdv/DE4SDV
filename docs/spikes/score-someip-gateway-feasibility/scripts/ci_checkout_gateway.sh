#!/usr/bin/env bash
# DE4SDV throwaway spike (INC-MW-011 gateway feasibility), never merged.
# Checks out eclipse-score/inc_someip_gateway at the pinned commit, proves the
# identity (commit and tree) and a clean tree, and, with --overlay, adds the
# spike package //de4sdv_spike (new files only; no upstream file changes).
# With COMMUNICATION_PATCH set (a path relative to the spike directory), it also
# copies that patch into //de4sdv_spike and appends it to the patches of the
# gateway's score_communication single_version_override in MODULE.bazel. Then
# MODULE.bazel is the only modified upstream file, and the script proves that
# its diff is exactly the one added patch line.
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
     "$spike_dir/config/mw_com_config_gatewayd.json" \
     "$spike_dir/config/mw_com_config_gatewayd_mwcom.json" \
     "$spike_dir/config/mw_com_config_someipd.json" "$dest/de4sdv_spike/"
fi

patch_rel=${COMMUNICATION_PATCH:-}
patch_label=""
if [ -n "$patch_rel" ]; then
  if [ "$overlay" != "--overlay" ]; then
    echo "COMMUNICATION_PATCH needs --overlay" >&2
    exit 1
  fi
  patch_src="$spike_dir/$patch_rel"
  test -f "$patch_src"
  cp "$patch_src" "$dest/de4sdv_spike/communication_extra.patch"
  printf '\nexports_files(["communication_extra.patch"])\n' >> "$dest/de4sdv_spike/BUILD.bazel"
  patch_label="//de4sdv_spike:communication_extra.patch"
  python3 - "$dest/MODULE.bazel" "$patch_label" <<'EOF'
import re, sys
path, label = sys.argv[1:]
text = open(path).read()
# The score_communication override block: from its module_name line to the
# closing "]," of its patches list.
pattern = re.compile(r'(single_version_override\(\s*module_name = "score_communication",.*?patches = \[)(.*?)(\n    \],)', re.S)
matches = pattern.findall(text)
if len(matches) != 1:
    sys.exit(f"expected one score_communication override with patches, found {len(matches)}")
text = pattern.sub(lambda m: m.group(1) + m.group(2) + f'\n        "{label}",' + m.group(3), text, count=1)
open(path, "w").write(text)
EOF
  git -C "$dest" diff -U0 -- MODULE.bazel > "$out/module_bazel_patch.diff"
  cat "$out/module_bazel_patch.diff"
  added=$(grep -c '^+[^+]' "$out/module_bazel_patch.diff" || true)
  removed=$(grep -c '^-[^-]' "$out/module_bazel_patch.diff" || true)
  if [ "$added" != "1" ] || [ "$removed" != "0" ] || ! grep -qF "+        \"$patch_label\"," "$out/module_bazel_patch.diff"; then
    echo "MODULE.bazel diff is not exactly the one added patch line" >&2
    exit 1
  fi
fi

status=$(git -C "$dest" status --porcelain --untracked-files=all)
modified=$(printf '%s\n' "$status" | grep -v '^?? de4sdv_spike/' | grep -v '^$' || true)
expected_modified=""
if [ -n "$patch_label" ]; then
  expected_modified=" M MODULE.bazel"
fi
patch_sha=""
if [ -n "$patch_rel" ]; then
  patch_sha=$(sha256sum "$spike_dir/$patch_rel" | cut -d' ' -f1)
fi
python3 - "$out/gateway_checkout.json" "$head" "$tree" "$overlay" "$modified" "$dest" "$patch_rel" "$patch_label" "$patch_sha" <<'EOF'
import hashlib, json, pathlib, sys
path, head, tree, overlay, modified, dest, patch_rel, patch_label, patch_sha = sys.argv[1:]
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
    "communication_patch": ({"source": patch_rel, "sha256": patch_sha, "label": patch_label,
                             "module_bazel_diff": "module_bazel_patch.diff"} if patch_rel else None),
}, open(path, "w"), indent=2)
EOF
cat "$out/gateway_checkout.json"
if [ "$modified" != "$expected_modified" ]; then
  echo "upstream files modified: '$modified', expected: '$expected_modified'" >&2
  exit 1
fi
