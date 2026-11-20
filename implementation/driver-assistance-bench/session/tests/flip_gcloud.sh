#!/bin/bash
# A wrapper around fake_gcloud.py for the dry runs of test_session_closure_r.py, ported from the closure review of
# 1bfbd6b4 (REVIEW-CLOSURE-p10-2-1bfbd6b4/flip_gcloud.sh). Knobs (environment):
#   FLIP_VM    a VM name the wrapper marks TERMINATED once, with a compute.instances.preempted operation at that time
#   FLIP_ON    a text: the flip happens before the first call (any call) whose joined arguments contain it; or once
#              the file $FAKE_DIR/flip exists
#   SLOW_OPS   seconds: every `compute operations list` call sleeps that long before the fake answers it
here=$(cd "$(dirname "$0")" && pwd)
if [ -n "${FLIP_VM:-}" ] && { { [ -n "${FLIP_ON:-}" ] && [[ "$*" == *"$FLIP_ON"* ]]; } || [ -e "$FAKE_DIR/flip" ]; } \
   && mkdir "$FAKE_DIR/flipped" 2>/dev/null; then
  python3 - <<'PY'
import fcntl, json, os, time
D = os.environ["FAKE_DIR"]; SF = os.path.join(D, "state.json"); vm = os.environ["FLIP_VM"]
lk = open(SF + ".lock", "a"); fcntl.flock(lk, fcntl.LOCK_EX)
st = json.load(open(SF))
st["vm"][vm] = "TERMINATED"; st.setdefault("lost", []).append(vm)
st.setdefault("preempted_at", {})[vm] = time.time()
tmp = SF + ".flip.tmp"; json.dump(st, open(tmp, "w")); os.replace(tmp, SF)
open(os.path.join(D, "flipped", "at"), "w").write("%.3f %s\n" % (time.time(), vm))
PY
fi
[ -n "${SLOW_OPS:-}" ] && [[ "$*" == *"operations list"* ]] && sleep "$SLOW_OPS"
exec "$here/fake_gcloud.py" "$@"
