"""Lane I-S of the S1 integration (INC-DRIVING-002, 2026-11-20): what the merge of the score-side, C-fix and C-s1 lanes
must hold together.

- The chase recorder's listening handshake (R7 of C-fix) before every recorded world step of s1, the warm-up included.
- The stop run's path stop calls score-side's path_stop.sh as that script takes its arguments (one <out>).

The expected orders and values are written out here, not taken from the script.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from test_session_dryrun import G4, L4, RANGED, assert_invariants, run, vp_clone, _vp_env  # noqa: F401
from test_session_s1 import LABELS, record, s1_run, s1_seq

SESSION_DIR = Path(__file__).resolve().parents[1]
BENCH = SESSION_DIR.parent
PATH_STOP = BENCH / "score-path" / "scripts" / "path_stop.sh"


def _code(path: Path) -> list[str]:
    return [ln for ln in path.read_text().splitlines() if not ln.lstrip().startswith("#")]


# ───────────── a: the recorder listens before every recorded world step of s1, the warm-up included ─────────────


@pytest.mark.parametrize("kind", ["s1", "p10-2"])
def test_the_warmup_waits_for_its_recorders_listening_file_before_it_starts(tmp_path: Path, kind: str) -> None:
    # the lap rule: the warm-up's recorder must attach to the lap's hero and write, or no run is recorded; a recorder
    # that takes its list after the warm-up spawned the hero takes that hero for one already there (R7, T2)
    r = s1_run(tmp_path, "--without-guest-host") if kind == "s1" else run(tmp_path, "p10-2", "--without-guest-host")
    assert r.rc == 0, r.stdout + r.log
    rec_start = r.ssh(G4, "host_step.sh start rec_warmup ")[0]
    listen = r.ssh(G4, "test -e $HOME/da-kit/T/out/rec_warmup/listening")
    warmup = r.ssh(G4, "host_step.sh start warmup ")[0]
    assert listen and rec_start < listen[0] and listen[-1] < warmup, (rec_start, listen, warmup)
    assert "the chase recorder of warmup listens" in r.log
    assert not [s for s in r.sequence() if "listening" in s], r.sequence()


def test_s1_every_recorded_run_the_stop_run_included_waits_for_its_recorder_and_calib_steer_has_none(
        tmp_path: Path) -> None:
    r = s1_run(tmp_path, "--without-guest-host")
    assert r.rc == 0, r.stdout + r.log
    for w in LABELS:
        rec_start = r.ssh(G4, f"host_step.sh start rec_{w} ")[0]
        listen = r.ssh(G4, f"test -e $HOME/da-kit/T/out/rec_{w}/listening")
        world = r.ssh(G4, f"host_step.sh start world_{w} ")[0]
        assert listen and rec_start < listen[0] and listen[-1] < world, (w, rec_start, listen, world)
    # calib_steer is not recorded: no recorder, so nothing to wait for
    assert not r.ssh(G4, "rec_calib_steer")
    assert r.sequence() == s1_seq(guest=False)


# ───────────── d: the path stop by the callee's own contract ─────────────


def test_path_stop_sh_takes_one_out_folder_and_prints_one_json_line() -> None:
    # the callee's lines the session depends on (score-side lane, shared contract 3): its one argument and its line
    code = _code(PATH_STOP)
    assert 'OUT=${1:?usage: path_stop.sh <out>}' in code
    assert any('line="{\\"runTarget\\":\\"$RUN_TARGET\\",\\"stopInstantRealNs\\":$real,\\"stopInstantMonoNs\\":$mono,'
               '\\"rc\\":$rc}"' in ln for ln in code), "the contract line moved"
    assert "  printf '%s\\n' \"$line\"" in code


def test_the_stop_runs_path_stop_step_passes_its_out_folder(tmp_path: Path) -> None:
    r = s1_run(tmp_path, "--without-guest-host")
    assert r.rc == 0, r.stdout + r.log
    (ps,) = r.ssh(L4, "start path_stop_")
    assert r.command(ps).endswith("bash extra/path_stop.sh $HOME/da-kit/T/out/path_stop_stop"), r.command(ps)
    rec = record(r)
    assert rec["s1"]["stop_instant"]["runTarget"] == "path_stopped"


# ───────────── b: C-fix's fetch owed and C-s1's chase fetch in one s1 ─────────────


def test_s1_an_owed_simulator_pack_names_fetch_owed_before_fetch_chase(tmp_path: Path) -> None:
    # the budget scaled to 2 + 3 = 5 s: the 3.5 MiB pack needs 64 s at 1 MB/s, so C-fix's R2 leaves it on the host. The
    # chase videos' list (pack_excluded.tsv, C-s1's C3) is inside that pack: the hand fetch of the pack comes first
    r = s1_run(tmp_path, "--without-guest-host", DA_T_TRAP_PACK_S="2", DA_T_TRAP_SCP_S="3", **RANGED)
    rec = record(r)
    assert r.rc == 5 and rec["ended_by"] == "fetch", r.log
    assert [x for x in rec["not_fetched"] if x.startswith("sim: ~/da-kit/T/out.tgz sha256 ") and "(fetch owed)" in x]
    lines = [ln for ln in r.log.splitlines() if "fetch_owed.sh" in ln and "fetch_chase.sh" in ln]
    assert len(lines) == 1, r.log
    assert lines[0].index("fetch_owed.sh") < lines[0].index("fetch_chase.sh"), lines[0]
    assert f"incoming_T" in lines[0]
    assert_invariants(r)


def test_s1_a_fetched_simulator_pack_names_only_fetch_chase(tmp_path: Path) -> None:
    r = s1_run(tmp_path, "--without-guest-host")
    assert r.rc == 0, r.log
    assert not [ln for ln in r.log.splitlines() if "fetch_owed.sh" in ln], r.log

