# Runner only: each scripts/ci_*.sh sources this file as its first command.
# The ci_* scripts are written for a disposable CI runner and may change the
# host (packages, ~/.bazelrc, /usr/local, large build trees). Each one
# refuses to run elsewhere unless its first argument is --runner; this file
# removes that argument. The bench VM has its own path (README, section
# "Bench VM").
if [ "${1:-}" = "--runner" ]; then
  shift
elif [ "${GITHUB_ACTIONS:-}" != "true" ]; then
  echo "$(basename "$0"): runs only on a CI runner (GITHUB_ACTIONS=true) or with --runner as the first argument" >&2
  exit 2
fi
