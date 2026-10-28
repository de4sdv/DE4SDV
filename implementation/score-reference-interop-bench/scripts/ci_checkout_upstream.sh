#!/usr/bin/env bash
# Checks out an upstream Eclipse S-CORE repository at one pinned commit into a
# throwaway directory, proves the commit, the tree and a clean checkout, and
# copies DE4SDV overlay directories into it as new packages. Only new files
# may appear; an overlay that would change an upstream file fails the step.
# No S-CORE file enters the DE4SDV repository: the overlay goes the other way.
# Usage: ci_checkout_upstream.sh <repo-url> <commit> <dest> <facts-dir> <name> [<src-dir>=<dest-subdir> ...]
set -euo pipefail

repo=${1:?}
commit=${2:?}
dest=${3:?}
out=${4:?}
name=${5:?}
shift 5
mkdir -p "$out"

git init -q "$dest"
git -C "$dest" remote add origin "$repo"
git -C "$dest" fetch -q --depth 1 origin "$commit"
git -C "$dest" checkout -q --detach FETCH_HEAD
head=$(git -C "$dest" rev-parse HEAD)
tree=$(git -C "$dest" rev-parse 'HEAD^{tree}')
if [ "$head" != "$commit" ]; then
  echo "checked out $head, expected $commit" >&2
  exit 1
fi
if [ -n "$(git -C "$dest" status --porcelain --untracked-files=all)" ]; then
  echo "the fresh checkout is not clean" >&2
  exit 1
fi

overlay_dirs=()
for mapping in "$@"; do
  src=${mapping%%=*}
  sub=${mapping#*=}
  if [ -e "$dest/$sub" ]; then
    echo "overlay target $sub exists upstream; the overlay may only add files" >&2
    exit 1
  fi
  mkdir -p "$(dirname "$dest/$sub")"
  cp -r "$src" "$dest/$sub"
  overlay_dirs+=("$sub")
done

status=$(git -C "$dest" status --porcelain --untracked-files=all)
modified=$(printf '%s\n' "$status" | grep -v '^?? ' | grep -v '^$' || true)
python3 - "$out/${name}_checkout.json" "$repo" "$head" "$tree" "$dest" "$modified" "${overlay_dirs[@]}" <<'PY'
import hashlib, json, pathlib, sys
path, repo, head, tree, dest, modified, *overlays = sys.argv[1:]
files = {}
for overlay in overlays:
    for file in sorted(pathlib.Path(dest, overlay).rglob("*")):
        if file.is_file():
            files[str(file.relative_to(dest))] = hashlib.sha256(file.read_bytes()).hexdigest()
json.dump({
    "repository": repo,
    "commit": head,
    "tree": tree,
    "overlay_packages": overlays,
    "overlay_files_sha256": files,
    "upstream_files_modified": [line for line in modified.splitlines() if line.strip()],
}, open(path, "w"), indent=2)
PY
cat "$out/${name}_checkout.json"
if [ -n "$modified" ]; then
  echo "upstream files modified: $modified" >&2
  exit 1
fi
