"""Session kind s1 (INC-DRIVING-002 S1, the judged runs): the run list, the per-run disk check, the stop run's path
stop, the chase videos left on the simulator host and fetched after the session, the per-run records and the
candidate option.

Plan: ~/.hermes/outputs/inc-driving-002/phase10/S1-BUILD-PLAN.md, sections 4 (session design) and 5 (lane C). The
expected orders and values are written out here from the plan and the shared contracts, not taken from the script.
The dry runs use an SC-DRIVING-012-only run list (the world side knows the other settings only from lane A1 on).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

from test_session_dryrun import (FAKE, G4, GH, GUEST_UP_SEQ, HERE, L4, STUBS, assert_invariants, env_for, run,  # noqa: F401
                                 vp_clone, _vp_env, _cap_sums, _session_defaults)

SESSION_DIR = HERE.parent
BENCH = SESSION_DIR.parent
RUNS_TSV = SESSION_DIR / "s1_runs.tsv"
FETCH_CHASE = SESSION_DIR / "fetch_chase.sh"
MODEL = BENCH.parents[1] / "textual-notation-of-model" / "packages" / "features" / "driving" / \
    "driver_assistance_needs_requirements.sysml"

# the shared contract 4 of the S1 build (fixed by the lead): the run ids, each setting twice, then the stop run
EXPECTED_RUNS = [(sid, rep) for sid in ("SC-DRIVING-012@20", "SC-DRIVING-012@42", "SC-DRIVING-012@60",
                                        "SC-DRIVING-013@30", "SC-DRIVING-013@60", "SC-DRIVING-014@30",
                                        "SC-DRIVING-015@40") for rep in ("r1", "r2")] + [("stop", "further")]

# the dry runs' run list: SC-DRIVING-012 only, and the stop run on SC-DRIVING-012@20's road
TEST_RUNS = "# run_id\trun\nSC-DRIVING-012@20\tr1\nSC-DRIVING-012@20\tr2\nstop\tfurther\n"
LABELS = ["012_20_r1", "012_20_r2", "stop"]
STOP_LINE = '{"runTarget":"path_stopped","stopInstantRealNs":1795000012000000000,"stopInstantMonoNs":4321000000,"rc":0}'
RATE, HOLD, MARGIN = 88000000, 60, 5000000000


def s1_env(tmp: Path, runs: str = TEST_RUNS, **extra: str) -> dict[str, str]:
    (tmp / "runs.tsv").write_text(runs)
    stub = tmp / "stubs"
    if not stub.exists():   # the stop run's entry is the score-side lane's: a stand-in in the kit's extra/
        stub.mkdir()
        for p in STUBS.iterdir():
            (stub / p.name).write_bytes(p.read_bytes())
            (stub / p.name).chmod(p.stat().st_mode)
        (stub / "path_stop.sh").write_text("#!/bin/bash\necho '%s'\n" % STOP_LINE)
        (stub / "path_stop.sh").chmod(0o755)
    return dict(DA_S1_RUNS=str(tmp / "runs.tsv"), S1_STOP_SETTING="SC-DRIVING-012@20",
                ENTRY_SCORE_PATH_STOP="extra/path_stop.sh", **extra)


def s1_run(tmp: Path, *more: str, runs: str = TEST_RUNS, timeout: float = 240, **extra: str):
    env = s1_env(tmp, runs, **extra)
    args = [a if a != str(STUBS) else str(tmp / "stubs") for a in more]
    return run(tmp, "s1", "--kit-extra", str(tmp / "stubs"), *args, timeout=timeout, **env)


def record(r) -> dict:
    return json.loads((r.incoming / "session.json").read_text())


def _s1_run_seq(w: str, first: bool, stop: bool = False, guest: bool = True) -> list[str]:
    window = (["guest:mcast_route"] if first else []) + [f"guest:unit_{w}", f"guest:app_restart_{w}",
                                                         f"guest:ivi_clock_{w}", f"guest:capture_{w}&"]
    close = [f"guest:capture_stop_{w}", f"guest:wait-capture_{w}", f"guest:receipts_{w}"]
    if not guest:
        window, close = [], []
    mark = [f"guest:logmark_{w}"] if guest else []
    return [f"score:disk_check_{w}", f"sim:rec_{w}&", f"sim:world_{w}&", "sim:file-ready.json", *mark,
            f"score:score_start_{w}", *window, "sim:touch-go", *([f"score:path_stop_{w}"] if stop else []),
            "sim:file-run_end.json", f"score:score_stop_{w}", "sim:touch-release", f"sim:wait-world_{w}",
            f"sim:wait-rec_{w}", *close]


def s1_seq(guest: bool = True) -> list[str]:
    # plan section 4: the p10-2 order without its upfront disk check, the calibrations, calib_steer, then each run of
    # the list with its own disk check before its S-CORE start, the stop run's path stop at go + 12 s
    return (["sim:sim_setup", "score:carla_reach"] + (GUEST_UP_SEQ if guest else []) + [
        "sim:rec_warmup&", "sim:warmup", "sim:wait-rec_warmup", "sim:calibrate", "lead:make_h",
        "score:disk_check_calib_steer", "sim:world_calib_steer&", "sim:file-ready.json",
        "score:score_start_calib_steer", "sim:touch-go", "sim:file-run_end.json", "score:score_stop_calib_steer",
        "sim:touch-release", "sim:wait-world_calib_steer"]
        + _s1_run_seq("012_20_r1", True, guest=guest) + _s1_run_seq("012_20_r2", False, guest=guest)
        + _s1_run_seq("stop", False, stop=True, guest=guest))


# ───────────── C1: the run list ─────────────


def _tsv_rows(text: str) -> list[tuple[str, str]]:
    return [tuple(line.split("\t")) for line in text.splitlines() if line.strip() and not line.startswith("#")]


def _model_setting_ids() -> set[str]:
    """The seven settings of the model's terms (needs_requirements.sysml, `Setting:`), read from the model text."""
    text = re.sub(r"\s*\n\s*\*\s*", " ", MODEL.read_text())
    m = re.search(r"- Setting: a scenario with an approach speed and its tolerance\. The settings are (.*?)\. Each "
                  r"setting is run twice", text)
    assert m, "the model's setting term moved"
    ids, scenario = set(), None
    # an approach speed: "at <v> km/h (<lo> to"; never the target's own speed ("behind a target at 20 km/h")
    for tok in re.finditer(r"(SC-DRIVING-0\d\d)|(?<!target )\bat (\d+) km/h \((\d+) to", m.group(1)):
        if tok.group(1):
            scenario = tok.group(1)
        elif scenario:
            ids.add(f"{scenario}@{tok.group(2)}")
    return ids


def test_s1_runs_tsv_holds_the_shared_run_ids_in_their_order() -> None:
    # shared contract 4: 012 ascending, then 013, 014, 015, each r1 and r2, then the stop run
    assert _tsv_rows(RUNS_TSV.read_text()) == EXPECTED_RUNS


def test_every_setting_id_of_the_run_list_is_one_of_the_seven_model_settings() -> None:
    model = _model_setting_ids()
    assert len(model) == 7, model
    ids = {sid for sid, _ in _tsv_rows(RUNS_TSV.read_text()) if sid != "stop"}
    assert ids == model, (ids ^ model)


def test_s1_sequence(tmp_path: Path) -> None:
    r = s1_run(tmp_path, "--owner-ok-guest-host", "--permissive-ivi", "--camcal", "settings")
    assert r.rc == 0, r.stdout + r.log
    assert r.sequence() == s1_seq()
    assert_invariants(r)
    rec = record(r)
    assert rec["kind"] == "s1" and rec["exit_code"] == 0
    assert [x["label"] for x in rec["s1"]["runs"]] == LABELS
    assert rec["s1"]["runs_done"] == LABELS and rec["s1"]["runs_owed"] == []


def test_s1_sequence_without_the_guest_host(tmp_path: Path) -> None:
    r = s1_run(tmp_path, "--without-guest-host", "--camcal", "settings")
    assert r.rc == 0, r.stdout + r.log
    assert r.sequence() == s1_seq(guest=False)


def test_s1_reads_the_committed_run_list_unless_a_dry_run_names_another(tmp_path: Path) -> None:
    # the run list is the committed s1_runs.tsv; DA_S1_RUNS is a dry-run knob a real session refuses
    # HOME in the test folder: the real gcloud of a real session ($HOME/google-cloud-sdk) is never reachable here
    env = {k: v for k, v in env_for(tmp_path, HOME=str(tmp_path), **s1_env(tmp_path)).items()
           if not k.startswith("DA_T_") and k != "DA_MAKE_H"}   # the other dry-run knobs, refused before it
    p = subprocess.run(["bash", str(SESSION_DIR / "da_session.sh"), "--kind", "s1", "--evidence-root",
                        str(tmp_path / "ev"), "--session-id", "T"], env=env, capture_output=True, text=True,
                       timeout=60)
    assert p.returncode == 2 and "DA_S1_RUNS is a dry-run knob" in p.stdout + p.stderr, p.stdout + p.stderr
    assert not (tmp_path / "fake" / "calls.log").exists() or "start" not in (tmp_path / "fake" / "calls.log").read_text()


@pytest.mark.parametrize("runs, needle", [
    ("SC-DRIVING-099@20\tr1\n", "run list"),
    ("SC-DRIVING-012@20\tr3\n", "run list"),
    ("SC-DRIVING-012@20\tr1\nSC-DRIVING-012@20\tr1\n", "twice"),
    ("stop\tfurther\nSC-DRIVING-012@20\tr1\n", "last"),
    ("SC-DRIVING-012@21\tr1\n", "no setting"),
])
def test_s1_refuses_a_bad_run_list_before_any_start(tmp_path: Path, runs: str, needle: str) -> None:
    r = s1_run(tmp_path, "--owner-ok-guest-host", runs=runs)
    assert r.rc == 2 and needle in r.log, r.log
    assert not r.starts(G4) and not r.starts(L4) and not r.starts(GH)


# ───────────── C2: the per-run disk check ─────────────


def _need(cap_s: float) -> int:
    return RATE * (int(cap_s) + HOLD) * 11 // 10 + MARGIN


def test_s1_checks_the_disk_before_each_score_start_with_one_runs_need(tmp_path: Path) -> None:
    r = s1_run(tmp_path, "--without-guest-host", "--camcal", "settings")
    assert r.rc == 0, r.log
    assert not r.ssh(L4, "start disk_check ")   # no upfront check over every run
    need = _need(90)   # SC-DRIVING-012@20: run cap 90 s (scenarios.py)
    for w in ["calib_steer"] + LABELS:
        (d,) = r.ssh(L4, f"start disk_check_{w} ")
        (s,) = r.ssh(L4, f"start score_start_{w} ")
        assert d < s, w
        assert r.command(d).endswith(f"disk_check.sh $HOME/da-kit/T/out/disk_check_{w} {need} {need}"), r.command(d)
    rec = record(r)
    assert rec["score_runs"]["012_20_r2"]["disk_check"]["need_bytes"] == need


def test_s1_a_short_disk_ends_the_session_cleanly_before_run_k_with_the_rest_owed(tmp_path: Path) -> None:
    # C2: the fake host's disk turns short before the second run: no S-CORE start of that run, the session ends exit 5
    # named, with runs k.. listed as owed; every VM stopped, every host fetched
    r = s1_run(tmp_path, "--owner-ok-guest-host", "--camcal", "settings", FAKE_STEP_RC="disk_check_012_20_r2:9",
               FAKE_TAIL_ADD="disk_check_012_20_r2:DISK_CHECK short need_bytes=1 avail_bytes=0")
    assert r.rc == 5, r.log
    assert_invariants(r)
    assert r.ssh(L4, "start score_stop_012_20_r1 ") and not r.ssh(L4, "start score_start_012_20_r2 ")
    assert not r.ssh(G4, "start world_012_20_r2 ")
    rec = record(r)
    assert rec["failed_step"] == "disk_check_012_20_r2"
    assert "disk" in rec["ended_by"].lower() and "012_20_r2" in rec["ended_by"], rec["ended_by"]
    assert rec["s1"]["runs_done"] == ["012_20_r1"]
    assert [x["label"] for x in rec["s1"]["runs_owed"]] == ["012_20_r2", "stop"]
    assert rec["s1"]["runs_owed"][0]["run_id"] == "SC-DRIVING-012@20" and rec["s1"]["runs_owed"][1]["run_id"] == "stop"
    assert sorted(rec["fetched"]) == ["guest", "score", "sim"]
    assert "DISK SPACE SHORT" in r.log and "owed" in r.log


# ───────────── C5: per-run setting, runIdentity, scenario digest ─────────────


def _digest(setting_id: str) -> str:
    """The test's own digest of the scenario definition (plan C5, simulatedConfiguration): sha256 of the canonical
    JSON of the setting's record and the sha256 of each world-side file that fixes the simulated configuration."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("scen_t", BENCH / "world-side" / "scenarios.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    files = {}
    for rel in ("world-side/scenarios.py", "world-side/da_world_side.py", "world-side/sites.py",
                "world-side/scripts/common.sh"):
        p = BENCH / rel
        if p.is_file():
            files[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    doc = {"setting": mod.setting(setting_id).as_record(), "files": files}
    return hashlib.sha256(json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def test_s1_records_each_runs_setting_identity_and_scenario_digest(tmp_path: Path) -> None:
    r = s1_run(tmp_path, "--without-guest-host", "--camcal", "settings")
    assert r.rc == 0, r.log
    runs = record(r)["score_runs"]
    want = {"012_20_r1": ("SC-DRIVING-012@20", "SC-DRIVING-012@20/r1", "SC-DRIVING-012"),
            "012_20_r2": ("SC-DRIVING-012@20", "SC-DRIVING-012@20/r2", "SC-DRIVING-012"),
            "stop": ("stop", "stop/further", "SC-DRIVING-012")}
    for w, (run_id, ident, scen) in want.items():
        d = runs[w]
        assert d["run_id"] == run_id and d["runIdentity"] == ident and d["scenario"] == scen, d
        assert d["setting"] == "SC-DRIVING-012@20", d
        assert d["simulatedConfiguration"]["sha256"] == _digest("SC-DRIVING-012@20"), d
        assert "world-side/scenarios.py" in d["simulatedConfiguration"]["files"]


# ───────────── the stop run: path_stop at go + 12 s ─────────────


def test_s1_the_stop_run_stops_the_path_at_go_plus_its_delay_and_records_the_instant(tmp_path: Path) -> None:
    r = s1_run(tmp_path, "--without-guest-host", "--camcal", "settings", DA_T_PATH_STOP_AFTER_S="1.5")
    assert r.rc == 0, r.log
    (ps,) = r.ssh(L4, "start path_stop_")
    assert "start path_stop_stop -- " in r.command(ps) and r.command(ps).endswith("bash extra/path_stop.sh")
    gos = r.ssh(G4, "/out/world_stop/go")
    ends = r.ssh(G4, "world_stop/simulator/run_end.json")
    assert gos and ends and gos[-1] < ps < ends[0]
    times = [float(json.loads(x)[0]) for x in (tmp_path / "fake" / "calls.log").read_text().splitlines()]
    assert times[ps] - times[gos[-1]] >= 1.5, times[ps] - times[gos[-1]]
    rec = record(r)
    assert rec["s1"]["stop_instant"] == json.loads(STOP_LINE)
    assert rec["s1"]["path_stop"]["after_go_s"] == 1.5 and rec["s1"]["path_stop"]["label"] == "stop"


@pytest.mark.parametrize("line", ['{"runTarget":"path_stopped","stopInstantRealNs":1,"stopInstantMonoNs":2,"rc":3}',
                                  '{"runTarget":"full","stopInstantRealNs":1,"stopInstantMonoNs":2,"rc":0}',
                                  "none"])
def test_s1_a_path_stop_without_a_good_json_line_fails_the_stop_run(tmp_path: Path, line: str) -> None:
    r = s1_run(tmp_path, "--without-guest-host", "--camcal", "settings", DA_T_PATH_STOP_AFTER_S="0.2",
               FAKE_PATH_STOP_LINE=line)
    assert r.rc == 5, r.log
    rec = record(r)
    assert rec["failed_step"] == "path_stop_stop", rec["failed_step"]
    assert_invariants(r)


def test_only_the_stop_run_gets_a_path_stop(tmp_path: Path) -> None:
    r = s1_run(tmp_path, "--without-guest-host", "--camcal", "settings",
               runs="SC-DRIVING-012@20\tr1\nSC-DRIVING-012@20\tr2\n")
    assert r.rc == 0, r.log
    assert not r.ssh(L4, "path_stop")
    assert record(r)["s1"]["stop_instant"] is None


def _t_step() -> int:
    return int(re.search(r"\bT_STEP=(\d+)\b", (SESSION_DIR / "da_session.sh").read_text()).group(1))


def test_s1_the_windows_capture_cap_covers_the_stop_runs_path_stop(tmp_path: Path) -> None:
    # Q3/Q4 for s1: --max-s is the longest window that ends well; the stop run's window also holds the wait to the
    # path stop (12 s) and its step (start call 60 + T_STEP + POLL_S + poll 60 + tail 60)
    r = s1_run(tmp_path, "--owner-ok-guest-host", "--camcal", "settings", runs="stop\tfurther\n")
    assert r.rc == 0, r.log
    d = dict(_session_defaults(), POLL_S=1)
    want = _cap_sums(d)["p10-2"] + 12 + 60 + _t_step() + 1 + 60 + 60
    start = r.command(r.ssh(GH, "start capture_stop ")[0])
    assert start.endswith("capture_stop --max-s %d" % want), start
    full = _cap_sums(_session_defaults())["p10-2"] + 12 + 60 + _t_step() + 20 + 60 + 60
    readme = (SESSION_DIR / "README.md").read_text()
    assert re.search(r"= --max-s of an s1 window +(\d+) s", readme).group(1) == str(full)


# ───────────── the candidate option ─────────────


def _score_step_starts(r) -> list[int]:
    return [i for i in r.ssh(L4, "host_step.sh start ")]


def test_candidate_pr427_sets_its_bundle_on_every_score_step_and_records_it(tmp_path: Path) -> None:
    r = s1_run(tmp_path, "--without-guest-host", "--camcal", "settings", "--candidate", "pr427")
    assert r.rc == 0, r.log
    starts = _score_step_starts(r)
    assert starts and all("-- env DA_B2_BUNDLE=/opt/da-b2-pr427/bundle " in r.command(i) for i in starts)
    assert not [i for i in r.ssh(G4, "host_step.sh start ") if "DA_B2_BUNDLE" in r.command(i)]
    rec = record(r)
    assert rec["candidate"] == {"name": "pr427", "bundle": "/opt/da-b2-pr427/bundle"}
    assert rec["remote_env"]["score"]["DA_B2_BUNDLE"] == "/opt/da-b2-pr427/bundle"


@pytest.mark.parametrize("kind, more", [("s1", ("--without-guest-host", "--camcal", "settings")),
                                        ("p10-1", ())])
def test_candidate_pin_is_the_default_and_changes_no_command(tmp_path: Path, kind: str, more: tuple) -> None:
    if kind == "s1":
        r = s1_run(tmp_path, *more)
    else:
        r = run(tmp_path, kind, *more)
    assert r.rc == 0, r.log
    assert not [c for c in r.calls if any("DA_B2_BUNDLE" in a for a in c)]
    bundle = re.search(r'DA_B2_BUNDLE:=([^}]+)\}', (BENCH / "score-path" / "scripts" / "lib_score_side.sh").read_text())
    assert record(r)["candidate"] == {"name": "pin", "bundle": bundle.group(1)}


@pytest.mark.parametrize("more, needle", [(("--candidate", "pr999"), "--candidate takes pin or pr427"),
                                          (("--remote-env", "DA_B2_BUNDLE=/opt/x"), "set by --candidate")])
def test_candidate_refusals_before_any_start(tmp_path: Path, more: tuple, needle: str) -> None:
    r = run(tmp_path, "p10-1", *more)
    assert r.rc == 2 and needle in r.stdout + r.log, r.stdout + r.log
    assert not r.starts(G4) and not r.starts(L4)


FACTS_PIN = "0001-de4sdv-score-interface.diff+0002-x.diff+0003-y.diff"
FACTS_PR427 = FACTS_PIN + "+0004-de4sdv-port-of-upstream-pr427.diff"


def _staged(facts: str) -> str:
    return ("SCORE_CONFIG speed_limit=5.833 speed_limit_requested=5.833 hero_wait_s=400.0 rrd_on=true "
            "conf_recorded=1 facts_diffs=%s" % facts)


@pytest.mark.parametrize("candidate, facts, rc", [("pr427", FACTS_PR427, 0), ("pr427", FACTS_PIN, 5),
                                                  ("pin", FACTS_PIN, 0), ("pin", FACTS_PR427, 5)])
def test_the_staged_facts_must_list_patch_0004_exactly_for_pr427(tmp_path: Path, candidate: str, facts: str,
                                                                    rc: int) -> None:
    r = s1_run(tmp_path, "--without-guest-host", "--camcal", "settings", "--candidate", candidate,
               runs="SC-DRIVING-012@20\tr1\n",
               FAKE_TAIL_ADD="score_start_012_20_r1:" + _staged(facts))
    assert r.rc == rc, r.log
    if rc:
        assert record(r)["failed_step"] == "score_start_012_20_r1"
        assert "0004" in r.log
        assert_invariants(r)
    else:
        assert record(r)["score_runs"]["012_20_r1"]["staged"]["facts_diffs"] == facts


def test_score_config_record_lists_the_staged_facts_diffs(tmp_path: Path) -> None:
    stage = tmp_path / "stage"
    (stage / "vision_pilot" / "config").mkdir(parents=True)
    (stage / "config").mkdir()
    (stage / "facts").mkdir()
    (stage / "vision_pilot" / "config" / "vision_pilot.conf").write_text("speed_limit = 5.833;\n")
    (stage / "config" / "adapter.json").write_text('{"hero_wait_s": 400.0}')
    for n in ("0002-b.diff", "0001-a.diff", "0004-de4sdv-port-of-upstream-pr427.diff"):
        (stage / "facts" / n).write_text("x\n")
    (stage / "facts" / "SHA256SUMS").write_text("x\n")
    p = subprocess.run(["python3", str(BENCH / "score-path" / "scripts" / "score_config_record.py"), str(stage),
                        str(tmp_path / "o.json"), "5.833"], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    words = dict(w.split("=", 1) for w in p.stdout.split("SCORE_CONFIG ", 1)[1].split())
    assert words["facts_diffs"] == "0001-a.diff+0002-b.diff+0004-de4sdv-port-of-upstream-pr427.diff"
    assert json.loads((tmp_path / "o.json").read_text())["facts_diffs"] == \
        ["0001-a.diff", "0002-b.diff", "0004-de4sdv-port-of-upstream-pr427.diff"]


# ───────────── C3: the pack leaves the chase videos on the simulator host ─────────────


def test_the_pack_leaves_every_chase_video_on_the_host_and_lists_its_sha256(tmp_path: Path) -> None:
    kit = tmp_path / "home" / "da-kit" / "S1"
    rem = kit / "bench" / "session" / "remote"
    rem.mkdir(parents=True)
    (rem / "host_step.sh").write_bytes((SESSION_DIR / "remote" / "host_step.sh").read_bytes())
    (kit / "session_id").write_text("S1\n")
    vids = {}
    for w in ("warmup", "012_20_r1"):
        d = kit / "out" / f"rec_{w}"
        d.mkdir(parents=True)
        data = os.urandom(3000 + len(w))
        (d / "chase_view.mp4").write_bytes(data)
        (d / "summary.json").write_text("{}")
        vids[f"out/rec_{w}/chase_view.mp4"] = data
    (kit / "out" / "world_x").mkdir()
    (kit / "out" / "world_x" / "chase_view.mp4").write_bytes(b"not a recorder's")   # only rec_*/ is left out
    p = subprocess.run(["bash", str(rem / "host_step.sh"), "pack"], capture_output=True, text=True,
                       env={**os.environ, "HOME": str(tmp_path / "home")})
    assert p.returncode == 0, p.stderr
    with tarfile.open(kit / "out.tgz") as t:
        names = set(t.getnames())
        listed = t.extractfile("out/pack_excluded.tsv").read().decode()
    assert not [n for n in names if n.startswith("out/rec_") and n.endswith(".mp4")], names
    assert "out/rec_012_20_r1/summary.json" in names and "out/world_x/chase_view.mp4" in names
    assert sorted(listed.splitlines()) == sorted("%s\t%d\t%s" % (k, len(v), hashlib.sha256(v).hexdigest())
                                                 for k, v in vids.items()), listed
    assert all((kit / k).read_bytes() == v for k, v in vids.items())   # still on the host's disk


def test_session_json_names_each_chase_video_left_on_the_host_with_its_sha256(tmp_path: Path) -> None:
    tsv = tmp_path / "excluded.tsv"
    sha = "a" * 64
    tsv.write_text("out/rec_012_20_r1/chase_view.mp4\t1234\t%s\n" % sha)
    r = s1_run(tmp_path, "--without-guest-host", "--camcal", "settings", runs="SC-DRIVING-012@20\tr1\n",
               FAKE_PACK_ADD="out/pack_excluded.tsv=%s" % tsv)
    assert r.rc == 0, r.log
    ex = record(r)["not_fetched_from_hosts"]["sim"]
    assert {"path": "out/rec_012_20_r1/chase_view.mp4", "bytes": 1234, "sha256": sha} in ex, ex
    assert "fetch_chase.sh" in r.log


# ───────────── C6: fetch_chase.sh, the simulator host alone after the session ─────────────


def _incoming(tmp: Path, files: dict[str, bytes], sid: str = "S1T", wrong: str | None = None) -> Path:
    inc = tmp / "ev" / f"incoming_{sid}"
    (inc / "sim" / "out").mkdir(parents=True)
    (inc / "sim" / "out" / "session_id").write_text(sid + "\n")
    rows = []
    remote = tmp / "remote"
    for rel, data in files.items():
        (remote / rel).parent.mkdir(parents=True, exist_ok=True)
        (remote / rel).write_bytes(data)
        sha = hashlib.sha256(data).hexdigest() if rel != wrong else "0" * 64
        rows.append("%s\t%d\t%s" % (rel, len(data), sha))
    rows.append("out/score_x/visionpilot.rrd\t99")   # an rrd row: not the fetch's
    (inc / "sim" / "out" / "pack_excluded.tsv").write_text("\n".join(rows) + "\n")
    return inc


def _fetch(tmp: Path, inc: Path, units: str = "", **extra: str) -> subprocess.CompletedProcess:
    (tmp / "fake").mkdir(exist_ok=True)
    fb = tmp / "fakebin"
    fb.mkdir(exist_ok=True)
    (fb / "systemctl").write_text("#!/bin/bash\nprintf '%s'\n" % units.replace("%", "%%"))
    (fb / "systemctl").chmod(0o755)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("FAKE_", "DA_"))}
    env.update(FAKE_DIR=str(tmp / "fake"), DA_GCLOUD=str(FAKE), FAKE_REMOTE_FILES=str(tmp / "remote"),
               PATH=f"{fb}:{env['PATH']}", DA_T_RETRY_S="0.2", DA_T_SSH_PAUSE_S="0.1", DA_T_STOP_POLL_S="0.1",
               DA_T_RUNNING_WAIT_S="1", FETCH_RANGE_MIB="1", FETCH_PARALLEL="3")
    env.update(extra)
    return subprocess.run(["bash", str(FETCH_CHASE), "--dry-run", str(inc)], env=env, capture_output=True,
                          text=True, timeout=180)


def _calls(tmp: Path) -> list[list[str]]:
    p = tmp / "fake" / "calls.log"
    return [json.loads(x)[1:] for x in p.read_text().splitlines()] if p.exists() else []


def _vm_status(tmp: Path) -> str:
    return json.loads((tmp / "fake" / "state.json").read_text())["vm"][G4]


VIDEOS = {"out/rec_012_20_r1/chase_view.mp4": os.urandom(2 * 1048576 + 1234),
          "out/rec_stop/chase_view.mp4": os.urandom(700000)}


def test_fetch_chase_fetches_each_video_by_ranges_checks_its_sha256_and_stops_the_host(tmp_path: Path) -> None:
    inc = _incoming(tmp_path, VIDEOS)
    p = _fetch(tmp_path, inc)
    assert p.returncode == 0, p.stdout + p.stderr
    for rel, data in VIDEOS.items():
        assert (inc / "sim" / rel).read_bytes() == data
    calls = _calls(tmp_path)
    start = [i for i, c in enumerate(calls) if c[2:5] == ["compute", "instances", "start"]]
    stop = [i for i, c in enumerate(calls) if c[2:5] == ["compute", "instances", "stop"]]
    dd = [i for i, c in enumerate(calls) if c[2:4] == ["compute", "ssh"] and any(a.startswith("dd if=") for a in c)]
    assert len(start) == 1 and stop and dd and start[0] < dd[0] and dd[-1] < stop[-1]
    assert all("--tunnel-through-iap" in calls[i] and "--ssh-flag=-T" in calls[i] for i in dd)
    assert len(dd) == 3 + 1   # 1 MiB ranges: 3 of the first video, 1 of the second
    assert _vm_status(tmp_path) == "TERMINATED"
    rec = json.loads((inc / "sim" / "fetch_chase" / "fetch_chase.json").read_text())
    assert rec["result"] == "ok" and rec["vm_status_after"] == "TERMINATED"
    assert {f["path"]: f["result"] for f in rec["files"]} == {k: "ok" for k in VIDEOS}
    assert "TERMINATED" in p.stdout


def test_fetch_chase_refuses_a_simulator_host_that_is_not_terminated(tmp_path: Path) -> None:
    inc = _incoming(tmp_path, VIDEOS)
    p = _fetch(tmp_path, inc, FAKE_INIT=f"{G4}:RUNNING")
    assert p.returncode == 2 and "TERMINATED" in p.stdout + p.stderr, p.stdout + p.stderr
    assert not [c for c in _calls(tmp_path) if c[2:4] == ["compute", "instances"] and c[4] in ("start", "stop")]
    assert _vm_status(tmp_path) == "RUNNING"


def test_fetch_chase_refuses_while_a_session_unit_is_active(tmp_path: Path) -> None:
    inc = _incoming(tmp_path, VIDEOS)
    p = _fetch(tmp_path, inc, units="da-session-20261123T120000Z.service loaded active running x\n")
    assert p.returncode == 2 and "da-session" in p.stdout + p.stderr, p.stdout + p.stderr
    assert not [c for c in _calls(tmp_path) if c[2:5] == ["compute", "instances", "start"]]


def test_fetch_chase_a_sha256_mismatch_fails_keeps_no_file_and_stops_the_host(tmp_path: Path) -> None:
    bad = "out/rec_stop/chase_view.mp4"
    inc = _incoming(tmp_path, VIDEOS, wrong=bad)
    p = _fetch(tmp_path, inc)
    assert p.returncode == 5, p.stdout + p.stderr
    assert not (inc / "sim" / bad).exists() and not list((inc / "sim").rglob("*.part"))
    good = "out/rec_012_20_r1/chase_view.mp4"
    assert (inc / "sim" / good).read_bytes() == VIDEOS[good]
    assert _vm_status(tmp_path) == "TERMINATED"
    assert [c for c in _calls(tmp_path) if c[2:5] == ["compute", "instances", "stop"]]
    rec = json.loads((inc / "sim" / "fetch_chase" / "fetch_chase.json").read_text())
    assert {f["path"]: f["result"] for f in rec["files"]}[bad].startswith("sha256 mismatch")


def test_fetch_chase_retries_a_capacity_refusal_every_round(tmp_path: Path) -> None:
    # a refused start costs nothing: the next round after RETRY_S (180 s; the dry run's 0.2 s), up to RETRY_N
    inc = _incoming(tmp_path, VIDEOS)
    p = _fetch(tmp_path, inc, FAKE_START=f"{G4}:POOL|POOL|OK")
    assert p.returncode == 0, p.stdout + p.stderr
    starts = [c for c in _calls(tmp_path) if c[2:5] == ["compute", "instances", "start"]]
    assert len(starts) == 3
    assert p.stdout.count("no capacity") == 2
    assert _vm_status(tmp_path) == "TERMINATED"


def test_fetch_chase_gives_up_after_its_rounds_with_the_capacity_code(tmp_path: Path) -> None:
    inc = _incoming(tmp_path, VIDEOS)
    p = _fetch(tmp_path, inc, FAKE_START=f"{G4}:POOL", DA_T_RETRY_N="3")
    assert p.returncode == 4, p.stdout + p.stderr
    assert len([c for c in _calls(tmp_path) if c[2:5] == ["compute", "instances", "start"]]) == 3


def test_fetch_chase_skips_a_video_already_fetched_whole(tmp_path: Path) -> None:
    inc = _incoming(tmp_path, VIDEOS)
    rel = "out/rec_012_20_r1/chase_view.mp4"
    (inc / "sim" / rel).parent.mkdir(parents=True)
    (inc / "sim" / rel).write_bytes(VIDEOS[rel])
    p = _fetch(tmp_path, inc)
    assert p.returncode == 0, p.stdout + p.stderr
    dd = [c for c in _calls(tmp_path) if c[2:4] == ["compute", "ssh"] and any(a.startswith("dd if=") for a in c)]
    assert dd and all("rec_stop" in " ".join(c) for c in dd)


def test_fetch_chase_refuses_a_real_gcloud_in_a_dry_run_and_the_knobs_in_a_real_one(tmp_path: Path) -> None:
    inc = _incoming(tmp_path, VIDEOS)
    # a stand-in at a real gcloud's path that must never run: a refusal that failed could not reach the cloud
    real = tmp_path / "google-cloud-sdk" / "bin" / "gcloud"
    real.parent.mkdir(parents=True)
    real.write_text("#!/bin/bash\necho called >> %s\nexit 1\n" % (tmp_path / "real_called"))
    real.chmod(0o755)
    p = _fetch(tmp_path, inc, DA_GCLOUD=str(real))
    assert p.returncode == 9 and not (tmp_path / "real_called").exists(), p.stdout + p.stderr
    env = {k: v for k, v in os.environ.items() if not k.startswith(("FAKE_", "DA_"))}
    env.update(DA_T_RETRY_S="1", HOME=str(tmp_path))
    q = subprocess.run(["bash", str(FETCH_CHASE), str(inc)], env=env, capture_output=True, text=True, timeout=60)
    assert q.returncode == 2 and "dry-run knob" in q.stdout + q.stderr, q.stdout + q.stderr


# ───────────── C7: the README and the cap ─────────────


def test_the_s1_cap_is_8_eur_in_hosts_env_and_the_readme() -> None:
    hosts = (SESSION_DIR / "hosts.env").read_text()
    assert re.search(r': "\$\{CAP_EUR_S1:=8\.00\}"', hosts)
    readme = (SESSION_DIR / "README.md").read_text()
    row = [ln for ln in readme.splitlines() if ln.startswith("| `s1` |") and "EUR 8.00" in ln]
    assert len(row) == 1, "no s1 row with the cap in the README's tables"


def test_the_readme_s1_block_runs_permissive_with_camcal_settings_and_names_the_chase_fetch() -> None:
    text = (SESSION_DIR / "README.md").read_text()
    m = re.search(r"^### `s1`.*?\n```bash\n(.*?)```", text, re.S | re.M)
    assert m
    lines = [re.sub(r"\s+", " ", ln.strip()) for ln in m.group(1).replace("\\\n", " ").splitlines()
             if ln.strip() and not ln.strip().startswith("#")]
    sess = [c for c in lines if "da_session.sh" in c]
    assert len(sess) == 2 and sum("--dry-run" in c for c in sess) == 1, sess
    assert all("--kind s1 --owner-ok-guest-host --permissive-ivi --camcal settings" in c for c in sess), sess
    assert any(c.startswith("systemd-run --user ") and "-p KillMode=mixed" in c and "-p TimeoutStopSec=infinity" in c
               and "-p SendSIGHUP=no" in c and "/usr/bin/env -i " in c for c in sess), sess
    assert any(c.startswith("env -i ") and "--dry-run" in c for c in sess), sess
    assert "fetch_chase.sh" in text


def test_the_readme_durations_count_the_ranged_fetch_and_the_chase_fetch() -> None:
    text = (SESSION_DIR / "README.md").read_text()
    part = text.split("## Durations and costs", 1)[1].split("\n## ", 1)[0]
    assert "2-5 min" not in part
    assert "fetch_chase.sh" in part and "EUR 8.00" in part
