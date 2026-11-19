"""R5 of the closure check of the p10-2 line (7befc3c1): the exit trap's pre-stop slots, every call hanging.

The closure check's harness (scratch/closure-p10-2/p1_slots/harness.sh) took the session's helpers and the trap's
pre-stop section verbatim, scaled them, made every SSH, scp and gcloud call hang to its bound, and measured each
slot: a failed poll's status read and a sleep after the last poll ran past their slots, and slot() charged the
overrun to the last fetch, the guest host's (31 s of 42 at 1/10 scale). This test is that harness, cut out of the
script by markers (not line numbers, which move), at 1/20 scale: every literal 60 becomes 3, every 120 becomes 6,
POLL_S 1, TRAP_GC_TO_S 2, T_CAPTURE_END 12, TRAP_PACK_S 6, TRAP_SCP_S 15, TRAP_SCORE_S 6. The state is a TERM inside
p10-2's window run1: a guest step running, the capture open, the S-CORE side up, the world side up, nothing fetched.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
SESSION = HERE.parent / "da_session.sh"

PRE = {"POLL_S": 1, "CAP_P": 1, "STEP_TERM_POLLS": 6, "T_CAPTURE_END": 12, "TRAP_PACK_S": 6, "TRAP_SCP_S": 15,
       "TRAP_SCORE_S": 6}
PLAN = {"step": 3 + 6 * 1 + 3 + 3, "capture": 12 + 3, "score": 6, "world": 3 + 3 * (3 + 1), "fetch": 6 + 15}
ORDER = ["step", "capture", "score", "world", "fetch sim", "fetch score", "fetch guest"]


def _cut(text: str, first: str, last: str) -> str:
    lines = text.splitlines()
    i = next(n for n, ln in enumerate(lines) if ln.startswith(first))
    j = next(n for n in range(i, len(lines)) if lines[n].startswith(last))
    return "\n".join(lines[i:j + 1]) + "\n"


def _scaled(code: str) -> str:
    return re.sub(r"\b120\b", "6", re.sub(r"\b60\b", "3", code))


def harness(src: Path, work: Path) -> dict:
    text = src.read_text()
    helpers = _scaled(_cut(text, "log() {", "ipof() {").rsplit("\nipof() {", 1)[0] + "\n")
    prestop = _scaled(_cut(text, "  PHASE_END=$(( $(date +%s) + PRESTOP_S ))", '  PRE_END=""; PHASE_END=""'))
    work.mkdir(parents=True, exist_ok=True)
    (work / "gcloud").write_text("#!/bin/bash\nexec sleep 1000\n")
    (work / "gcloud").chmod(0o755)
    (work / "helpers.sh").write_text(helpers)
    (work / "prestop.sh").write_text(prestop)
    total = PLAN["step"] + PLAN["capture"] + PLAN["score"] + PLAN["world"] + 3 * PLAN["fetch"]
    sets = " ".join(f"{k}={v}" for k, v in PRE.items())
    script = f"""set -uo pipefail
W={work}; IN=$W/in; mkdir -p "$IN"; LOG=$IN/session.log; CMDS=$IN/commands.log; : > "$LOG"
GCLOUD=$W/gcloud; GCLOUD_CONFIGURATION=x; DRY=0; SID=T; SIM_SSH_IAP=1
SIM_VM=g4; SIM_PROJECT=p; SIM_ZONE=z; SCORE_VM=l4; SCORE_PROJECT=p; SCORE_ZONE=z; GUEST_VM=gh; GUEST_PROJECT=p
GUEST_ZONE=z; GUEST_STOP_CMD=x; ENTRY_SCORE_STOP=stop.sh; ENTRY_GUEST_CAPTURE=cap.sh; T_SCORE_START=90
{sets}
GC_TO=2
exec 3>/dev/null
. "$W/helpers.sh"
renv() {{ :; }}
ROLES=(sim score guest)
PRE_STEP_S={PLAN['step']}; PRE_CAP_S={PLAN['capture']}; PRE_SCORE_S={PLAN['score']}; PRE_WORLD_S={PLAN['world']}
PRE_FETCH_S={PLAN['fetch']}; PRESTOP_S={total}; PRE_SUM={total}
CUR_STEP="guest app_restart_run1"; CAP_OPEN=run1; CAP_TRY=0; CAPTURES=""; SCORE_UP=/x; SCORE_RUN=run1; STOPS=""
WORLD_UP=" world_run1"; UPLOADED=" sim score guest"; FETCHED=""; FETCH_OK=""; FETCH_BAD=""; LOST=""
GUEST_STEP_RUNNING=""
eval "orig_$(declare -f slot)"
PHASE_END_SEEN=""
slot() {{ echo "slot $(date +%s.%N)" >> "$W/marks"; orig_slot "$@"; PHASE_END_SEEN=$PHASE_END; }}
. "$W/prestop.sh"
echo "end $(date +%s.%N) $PHASE_END_SEEN" >> "$W/marks"
"""
    # PHASE_END is cleared at the section's end: the slot() wrapper keeps it (PHASE_END_SEEN)
    (work / "run.sh").write_text(script)
    p = subprocess.run(["bash", str(work / "run.sh")], capture_output=True, text=True, timeout=total + 120,
                       env={"PATH": "/usr/bin:/bin", "HOME": str(work)}, start_new_session=True)
    marks = (work / "marks").read_text().split("\n") if (work / "marks").exists() else []
    times = [float(m.split()[1]) for m in marks if m.startswith(("slot ", "end "))]
    end = [m for m in marks if m.startswith("end ")]
    used: dict = {name: times[k + 1] - times[k] for k, name in enumerate(ORDER) if k + 1 < len(times)}
    used["_rc"] = p.returncode
    used["_phase_end"] = float(end[0].split()[2]) if end and len(end[0].split()) > 2 else float("nan")
    used["_end"] = times[-1] if times else float("nan")
    used["_log"] = (work / "in" / "session.log").read_text() if (work / "in" / "session.log").exists() else ""
    return used


def test_r5_every_fetch_keeps_its_slot_when_every_call_hangs_to_its_bound(tmp_path: Path) -> None:
    used = harness(SESSION, tmp_path / "h")
    assert used["_rc"] == 0, used
    assert all(name in used for name in ORDER), used
    # every fetch keeps its own slot: the overruns of the earlier steps come out of the earlier steps, never out of
    # a fetch (the guest host's was cut 42 -> 31 s at 1/10 scale)
    for host in ("sim", "score", "guest"):
        assert used[f"fetch {host}"] >= PLAN["fetch"] - 1.5, (host, used)
    # and the phase still ends at its bound
    assert used["_end"] <= used["_phase_end"] + 1.5, used
    assert "fetching gh before its stop" in used["_log"], used["_log"]


if __name__ == "__main__":   # the scaled harness by hand: python3 test_prestop_slots.py [da_session.sh]
    import sys
    import tempfile
    res = harness(Path(sys.argv[1]) if len(sys.argv) > 1 else SESSION, Path(tempfile.mkdtemp()))
    for k in ORDER:
        print(f"{k:12s} used {res.get(k, float('nan')):6.1f} s planned {PLAN[k.split()[0]]} s")
    print("rc", res["_rc"], "end - phase end", round(res["_end"] - res["_phase_end"], 2))
