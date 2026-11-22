#!/usr/bin/env python3
"""Fake gcloud for the dry runs of da_session.sh (local control-flow tests only; never touches the cloud).

Derived from the SIM20-G4 dry-run fake. State in $FAKE_DIR/state.json (file-locked); every call is appended to
$FAKE_DIR/calls.log as one JSON list of its arguments. Scenario knobs (environment):
  FAKE_INIT          "vm:STATUS,..."  status before the session (default TERMINATED for the three bench VMs)
  FAKE_START         "vm:R1|R2|...,..."  results of successive start calls (OK STOCKOUT POOL QUOTA ERROR; last repeats)
  FAKE_PREEMPT       "vm:n"  the n-th status read after the VM came up returns TERMINATED (once)
  FAKE_GPU_RUNNING   "project:name"  another GPU VM running in that project
  FAKE_FAIL_STEP     a step name whose `host_step.sh run|status` fails
  FAKE_FAIL_AFTER_LOSS  1: the detached FAKE_FAIL_STEP reads "running" until a FAKE_LOST_AFTER loss is on record and
                     the clock has passed into a later whole second than the loss; only then does its status report
                     the failure. The session then takes the failure's time (abort's t_fail) in a later second than
                     the preemption's insertTime, whatever its `date` prints for their milliseconds. uutils date
                     0.10.0 prints a %3N without the fraction's leading zeros (".094" as ".940"), and so does CI's
                     ubuntu-26.04 image (its failing runs logged losses at ".510", ".940" and ".980"). The error stays
                     inside the second, so a failure one second on reads as after the loss there and on GNU date
  FAKE_LOSS_AFTER_FAIL  1: the mirror of FAKE_FAIL_AFTER_LOSS, for a loss that comes after a failure. The ssh call
                     that triggers FAKE_LOST_AFTER first waits until the clock has passed into a later whole second
                     than the call's arrival; only then are the loss and its preemption's insertTime recorded. A
                     trigger in abort's stop path (score_stop_on_failure, say) arrives after abort took the failure's
                     time (t_fail), so the loss then reads as after the failure whatever `date` prints for their
                     milliseconds. Without it a fast host lost the VM in the failure's second, and CI's date printed
                     a t_fail of ".0xx" without its leading zero (".060" as ".600"): a loss logged at ".113" in that
                     second then read as before the failure (rc 3 for 5, on main at 2a1817d4)
  FAKE_STEP_RC       "step:rc,..."  the exit status a detached step reports (status, tail) in place of 0
  FAKE_HANG_STEP     "step:seconds"  `host_step.sh run <step>` sleeps that long before answering; a detached
                     step (`start`) reads "running" for that long after its start
  FAKE_SSH_DOWN      a VM name that never answers SSH
  FAKE_STEP_IGNORES_TERM  a step name that keeps reading "running" after its signal (its FAKE_HANG_STEP time)
  FAKE_SSH_DOWN_AFTER  "vm:text"  the VM stops answering SSH right after the first ssh call (to any VM) whose
                     command has text (an SSH loss mid-session; the VM keeps running)
  FAKE_GUEST_STOP_FAIL  1: a crosvm process stays after every guests' stop; once: after the first stop only
  FAKE_IP            "vm:ip,..."  internal IPs other than the defaults (the session must read them from gcloud)
  FAKE_NO_FILE       a substring: `test -e <path>` of a matching path never finds it (the step keeps "running")
  FAKE_FOREIGN_FETCH    1: a fetched tarball carries another session's id
  FAKE_NO_STOP       a VM name that stays RUNNING after a stop
  FAKE_SLOW_GUEST_STOP  seconds: the guests' stop (guest_stop.sh, not the safety net's arming) takes that long
  FAKE_LOST_AFTER    "vm:text"  the VM is reclaimed (TERMINATED) right after the first ssh whose command has text
  FAKE_LOST_STATUS   the status FAKE_LOST_AFTER leaves (default TERMINATED; STOPPING, say)
  FAKE_LOST_NO_OP    1: FAKE_LOST_AFTER leaves no compute.instances.preempted operation (a stop, not a preemption).
                     Otherwise the loss is one: `compute operations list --filter="operationType=compute.instances.
                     preempted AND targetLink~instances/<vm>$ AND insertTime>=<iso>"` prints its insertTime as GCP
                     does, in the zone's local offset (-08:00), when it is not older than <iso>
  FAKE_PACK_ADD      "arcname=local file,..."  more files in every packed out.tgz (a fetched verdicts file, say)
  FAKE_KIT_EXISTS    a VM name that already holds ~/da-kit/<session id>
  FAKE_ARM_FAIL      a VM name whose safety net's arming fails
  FAKE_SLOW_FETCH    seconds, or "vm:seconds": the scp of a host's out.tgz (of that VM only) takes that long, and so
                     does each range read of it (`dd` below)
  FAKE_PACK_PAD      bytes: every packed out.tgz also holds out/pad.bin of that many incompressible bytes (a pack of
                     several ranges)
  FAKE_PACK_FAIL     a VM name whose `host_step.sh pack` prints nothing and exits 1 (an IAP error, not an SSH 255)
  FAKE_RANGE_SHORT   "skip:n,...": the first n reads of the range at that skip (MiB) send half its bytes and exit 255
                     (a tunnel dropped mid-range)
  FAKE_RANGE_HANG    "skip:n:seconds,...": the first n reads of the range at that skip hang that long, then answer
  The ranged fetch of a host reached through IAP: `compute ssh <vm> --ssh-flag=-T --command "dd if=$HOME/da-kit/<id>/
  out.tgz bs=1M skip=<k> count=<c> status=none"` streams those bytes of the host's last packed out.tgz to stdout, as
  dd does (refused without --ssh-flag=-T: a pty would mangle the bytes). The pack prints "<sha256> <bytes>"
  FAKE_FETCH_FAIL    a VM name whose out.tgz scp fails
  FAKE_TERM_TAIL     "step:line"  the last line of the step's tail once the step was signalled (its own FAIL line);
                     the tail then exits 1, as host_step.sh tail does for a step that wrote no .rc
  FAKE_TAIL_ADD      "step:line"  a line of the step's tail before its end line (guest_up's CROSVM_BEFORE_LAUNCH, say)
  FAKE_RECEIPTS      the count `offer_check.sh receipts` reports for a window's app record (default 2)
  FAKE_APP_RECORD    a file in the app's record format: `receipts` then runs the real offer_check.sh receipts on a
                     capture holding it as app_record_warning.jsonl, with a restart record of pid FAKE_APP_PID (4242)
  FAKE_DESCRIBE_FLAKE   "vm:n"  once any stop call was made, the next n status reads of the VM fail (a transient
                        gcloud error: a token refresh, a network blip)
  FAKE_PORT_CLOSED   "port,..."  the p10-1 port test (`for p in <ports>; do ... </dev/tcp/<host>/$p ...`, not a step)
                     finds these CARLA ports closed; every other port it names answers. "*": the call prints nothing
  FAKE_CAPTURE_END   "capture_<w>:end,..."  how that display capture ends once its stop is asked (default stop;
                     error: as display_capture.sh END=error, capture.done says so). The guest host's captures are modeled: `display_capture.sh
                     start <out>/capture_<w>` records until a `display_capture.sh stop` of the same folder. A pack of
                     the guest host then holds, per capture, while it records only seg_1.pending and a growing
                     seg_1.mp4.part; once stopped capture.json, capture.done, app_record_warning.jsonl and seg_1.mp4.
                     The stop's answer (its run output or its tail) is capture.done's line
  FAKE_PATH_STOP_LINE  the JSON line a detached step whose command runs path_stop.sh prints in its tail (s1's stop
                     run; shared contract 3); default a good path_stopped line, "none": no line
  FAKE_REMOTE_FILES  a folder: `dd if=$HOME/da-kit/<id>/<path> bs=1M skip=<k> count=<c> status=none` of any <path> but
                     out.tgz streams those bytes of <folder>/<path> (fetch_chase.sh's ranges of a chase video);
                     FAKE_SLOW_FETCH slows each such read as it does a range of out.tgz
  FAKE_SCORE_GPU     the answer of the S-CORE host's nvidia-smi to the platform record's query (default the L4's,
                     "NVIDIA L4, 580.178.04"; "none": no nvidia-smi). Every S-CORE start's tail holds the SCORE_PLATFORM
                     and SCORE_GPU lines that the real score_platform_record.py prints for it
  FAKE_GUEST_IMAGES  none: guest_up's tail holds no GUEST_IMAGE line (default: one per guest, guest_up.sh's format)
"""
import fcntl
import hashlib
import io
import json
import os
import re
import shutil
import sys
import tarfile
import time

D = os.environ["FAKE_DIR"]
SF = os.path.join(D, "state.json")
argv = sys.argv[1:]
with open(os.path.join(D, "calls.log"), "a") as f:
    f.write(json.dumps([round(time.time(), 3)] + argv) + "\n")

def receipts_out(c):
    """The answer of a window's `offer_check.sh receipts <capture> [<restart record>]` step."""
    rec = os.environ.get("FAKE_APP_RECORD")
    if not rec:
        return "RECEIPTS %s\n" % os.environ.get("FAKE_RECEIPTS", "2")
    import subprocess
    import tempfile
    t = tempfile.mkdtemp(dir=D)
    cap = os.path.join(t, "cap")
    os.mkdir(cap)
    shutil.copy(rec, os.path.join(cap, "app_record_warning.jsonl"))
    args = ["bash", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "remote", "offer_check.sh"),
            "receipts", cap]
    if "app_restart_" in c:   # the session names the window's restart record: the fake writes one at its pid
        with open(os.path.join(t, "restart.txt"), "w") as f:
            f.write("pid %s 2026-11-19T10:00:00.000Z\n" % os.environ.get("FAKE_APP_PID", "4242"))
        args.append(os.path.join(t, "restart.txt"))
    return subprocess.run(args, capture_output=True, text=True).stdout


def score_platform_tail():
    """The S-CORE start's SCORE_PLATFORM and SCORE_GPU lines, made by the real producer (score-path/scripts/
    score_platform_record.py) from a bundle whose facts hold the S-CORE build's real lines (score-path/tests/
    fake_bundle.py) and an nvidia-smi that answers FAKE_SCORE_GPU (default the L4's answer; "none": not found)."""
    bench = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
    sys.path.insert(0, os.path.join(bench, "score-path", "scripts"))
    sys.path.insert(0, os.path.join(bench, "score-path", "tests"))
    import fake_bundle
    import score_platform_record as spr
    facts = os.path.join(D, "bundle", "facts")
    os.makedirs(facts, exist_ok=True)
    for name, text in (("score-mod-explain.txt", fake_bundle.FACTS_SCORE_MOD_EXPLAIN),
                       ("sources.txt", fake_bundle.FACTS_SOURCES)):
        with open(os.path.join(facts, name), "w") as f:
            f.write(text)
    answer = os.environ.get("FAKE_SCORE_GPU", fake_bundle.SMI_L4_ANSWER)
    smi = os.path.join(D, "nvidia-smi")
    if answer == "none":
        smi = os.path.join(D, "no", "nvidia-smi")
    else:
        with open(smi, "w") as f:
            f.write("#!/bin/bash\necho '%s'\n" % answer)
        os.chmod(smi, 0o755)
    from pathlib import Path
    return "".join(x + "\n" for x in spr.lines(spr.platform_facts(Path(facts)), spr.gpu_facts(smi)))


def guest_images_tail():
    """guest_up.sh's GUEST_IMAGE lines (its format: role, then serial, product, build_id, fingerprint, vbmeta_digest);
    FAKE_GUEST_IMAGES=none: none printed."""
    if os.environ.get("FAKE_GUEST_IMAGES") == "none":
        return ""
    rows = (("sdv_core", "0.0.0.0:6521", "sdv_core_cf", "1f"), ("ivi", "0.0.0.0:6522", "sdv_ivi_cf", "2e"))
    return "".join("GUEST_IMAGE %s serial=%s product=%s build_id=BP4A.251205.006 fingerprint=generic/%s/vsoc_x86_64:17/"
                   "BP4A.251205.006/eng.fake.20261117:eng/test-keys vbmeta_digest=%s\n" % (r, s, p, p, h * 32)
                   for r, s, p, h in rows)


VMS = {  # name: (project, accelerator, internal IP)
    "de4sdv-probe-g4-carla": ("de4sdv-carla-d19a", "nvidia-rtx-pro-6000", "10.10.0.2"),   # carla-net (D5)
    "de4sdv-probe-da8-carla": ("project-f2215f73-3d53-48a7-895", "nvidia-l4", "10.164.0.5"),
    "de4sdv-aaos-build": ("project-f2215f73-3d53-48a7-895", "", "10.164.0.6"),
}


def kv(name):
    return dict(x.split(":", 1) for x in os.environ.get(name, "").split(",") if ":" in x)


lockf = open(SF + ".lock", "a")
fcntl.flock(lockf, fcntl.LOCK_EX)
st = json.load(open(SF)) if os.path.exists(SF) else {}
if "vm" not in st:
    init = kv("FAKE_INIT")
    st = {"vm": {n: init.get(n, "TERMINATED") for n in VMS}, "calls": {}, "reads_after_up": {}, "preempted": [],
          "kit_sha": {}}


def save():
    # atomic: the session's trap may TERM a fake call mid-write (kill_tree); a truncated state.json then failed the
    # next call and the test's own read (a fixture flake the second review saw, and the S9 cap test hit)
    tmp = "%s.%d.tmp" % (SF, os.getpid())
    with open(tmp, "w") as f:
        json.dump(st, f)
    os.replace(tmp, SF)


def opt(name):
    for i, a in enumerate(argv):
        if a == name and i + 1 < len(argv):
            return argv[i + 1]
        if a.startswith(name + "="):
            return a.split("=", 1)[1]
    return None


def out(s, rc=0):
    save()
    sys.stdout.write(s)
    sys.stdout.flush()
    sys.exit(rc)


def err(s, rc=1):
    save()
    sys.stderr.write(s)
    sys.stderr.flush()
    sys.exit(rc)


def nth(key, spec):
    n = st["calls"].get(key, 0)
    st["calls"][key] = n + 1
    seq = spec.split("|")
    return seq[min(n, len(seq) - 1)]


project = opt("--project")
words = [a for a in argv if not a.startswith("-")]
# drop the values of options given as "--opt value"
for o in ("--zone", "--command", "--format", "--filter", "--project", "--configuration"):
    v = opt(o)
    if v is not None and v in words and ("%s=%s" % (o, v)) not in argv:
        words.remove(v)

if words[:3] == ["compute", "instances", "list"]:
    rows = []
    running_only = (opt("--filter") or "") == "status=RUNNING"
    for n, (p, acc, _) in VMS.items():
        if p != project:
            continue
        s = st["vm"][n]
        if running_only and s != "RUNNING":
            continue
        rows.append("%s\t%s" % (n, acc) if running_only else "%s\teurope-west4-a\t%s" % (n, s))
    g = kv("FAKE_GPU_RUNNING")
    if project in g:
        rows.append("%s\tnvidia-l4" % g[project] if running_only else "%s\teurope-west4-a\tRUNNING" % g[project])
    out("".join(r + "\n" for r in rows))

if words[:3] == ["compute", "operations", "list"]:
    # the preemption's own record (R12b): only with the filter the session must give, else nothing
    import datetime
    f = opt("--filter") or ""
    mv = re.search(r"targetLink~instances/([A-Za-z0-9-]+)\$", f)
    mt = re.search(r"insertTime>=(\S+)", f)
    t = st.get("preempted_at", {}).get(mv.group(1)) if mv else None
    if "operationType=compute.instances.preempted" not in f or not mt or t is None:
        out("")
    since = datetime.datetime.strptime(mt.group(1), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
    if t < since.timestamp():
        out("")
    tz = datetime.timezone(datetime.timedelta(hours=-8))
    out(datetime.datetime.fromtimestamp(t, tz).isoformat(timespec="milliseconds") + "\n")

if words[:3] == ["compute", "instances", "describe"]:
    n = words[3]
    if n not in st["vm"]:
        err("ERROR: (gcloud.compute.instances.describe) Could not fetch resource:\n - The resource was not found\n")
    fmt = opt("--format") or ""
    if "networkIP" in fmt:
        out(kv("FAKE_IP").get(n, VMS[n][2]) + "\n")
    flake = kv("FAKE_DESCRIBE_FLAKE")
    if n in flake and st.get("stop_seen") and st.setdefault("flaked", {}).get(n, 0) < int(flake[n]):
        st["flaked"][n] = st["flaked"].get(n, 0) + 1
        err("ERROR: (gcloud.compute.instances.describe) There was a problem refreshing your current auth tokens\n")
    s = st["vm"][n]
    pre = kv("FAKE_PREEMPT")
    if s == "RUNNING" and n in pre and n not in st["preempted"]:
        st["reads_after_up"][n] = st["reads_after_up"].get(n, 0) + 1
        if st["reads_after_up"][n] >= int(pre[n]):
            st["vm"][n] = s = "TERMINATED"
            st["preempted"].append(n)
    out(s + "\n")

if words[:3] == ["compute", "instances", "start"]:
    n = words[3]
    r = nth("start:" + n, kv("FAKE_START").get(n, "OK"))
    time.sleep(0.05)
    if r == "OK":
        st["vm"][n] = "RUNNING"
        st["reads_after_up"][n] = 0
        out("Updated [https://compute.googleapis.com/compute/v1/projects/%s/zones/europe-west4-a/instances/%s].\n"
            % (project, n))
    err({"STOCKOUT": "ERROR: (gcloud.compute.instances.start) Could not fetch resource:\n - state:STOCKOUT\n",
         "POOL": "ERROR: (gcloud.compute.instances.start) --- code: ZONE_RESOURCE_POOL_EXHAUSTED_WITH_DETAILS\n",
         "QUOTA": "ERROR: (gcloud.compute.instances.start) Could not fetch resource:\n - Quota 'PREEMPTIBLE_NVIDIA_L4_GPUS' "
                  "exceeded.  Limit: FAKE in region europe-west4.\n"}.get(r, "ERROR: start failed (fake)\n"))

if words[:3] == ["compute", "instances", "stop"]:
    n = words[3]
    st["stop_seen"] = True
    if os.environ.get("FAKE_NO_STOP") != n:
        st["vm"][n] = "TERMINATED"
    out("Stopping instance(s) %s (async).\n" % n)

if words[:2] == ["compute", "instances"] and len(words) > 2 and words[2] in ("delete", "create"):
    err("fake gcloud: %s is never expected from a session\n" % words[2], 3)

if words[:2] == ["compute", "ssh"]:
    n = words[2]
    c = opt("--command") or ""
    if st["vm"].get(n) != "RUNNING" or os.environ.get("FAKE_SSH_DOWN") == n or n in st.get("ssh_down", []):
        err("ssh: connect to host 192.0.2.10 port 22: Connection refused\n", 255)
    for vm, text in kv("FAKE_SSH_DOWN_AFTER").items():
        if text in c and vm not in st.setdefault("ssh_down", []):
            st["ssh_down"].append(vm)
    lost = kv("FAKE_LOST_AFTER")
    if n in lost and lost[n] in c and n not in st.setdefault("lost", []):
        if os.environ.get("FAKE_LOSS_AFTER_FAIL") == "1":
            # the loss in a later whole second than this call's arrival (see the knob above)
            arrived = time.time()
            while int(time.time()) <= int(arrived):
                time.sleep(int(arrived) + 1 - time.time() + 0.001)
        st["vm"][n] = os.environ.get("FAKE_LOST_STATUS", "TERMINATED")   # reclaimed after this call (it answers)
        st["lost"].append(n)
        st.setdefault("lost_at", {})[n] = now = time.time()   # FAKE_FAIL_AFTER_LOSS waits on it
        if os.environ.get("FAKE_LOST_NO_OP") != "1":
            st.setdefault("preempted_at", {})[n] = now
    if c == "true":
        out("")
    m = re.search(r"host_step\.sh (run|start|status|tail|signal|pack)\s*(\S*)", c)
    if "sha256sum /tmp/da-kit-" in c and os.environ.get("FAKE_KIT_EXISTS") == n:
        out("KIT_EXISTS\n", 3)
    if "sha256sum /tmp/da-kit-" in c:
        out("%s  /tmp/da-kit.tgz\n" % st["kit_sha"].get(n, "none"))
    if "shutdown -h" in c:
        mm = re.search(r"\+(\d+)", c)
        out("safety-net-%s\n" % (mm.group(1) if mm else "?"))
    mm = re.search(r"safety_net\.sh arm (\d+)", c)
    if mm:
        if os.environ.get("FAKE_ARM_FAIL") == n:
            out("sudo: a terminal is required to read the password\n", 1)
        out("timer: Thu 2026-11-19 12:00:00 UTC 4h left - - da-safety-net.timer\nsafety-net-%s\n" % mm.group(1))
    gfail = os.environ.get("FAKE_GUEST_STOP_FAIL", "")
    if "guest_stop.sh" in c:
        st["guest_stops"] = st.get("guest_stops", 0) + 1
        slow = os.environ.get("FAKE_SLOW_GUEST_STOP")
        if slow:
            save()
            fcntl.flock(lockf, fcntl.LOCK_UN)
            time.sleep(float(slow))
            fcntl.flock(lockf, fcntl.LOCK_EX)
            st = json.load(open(SF))
    left = "1" if gfail == "1" or (gfail == "once" and st.get("guest_stops", 0) < 2) else "0"
    if "guest_stop.sh" in c:
        out("crosvm_processes_after_stop: %s\n" % left)
    if "pgrep -c -x crosvm" in c:
        out(left + "\n")
    if c.startswith("test -e "):
        path = c.split()[2]
        nf = os.environ.get("FAKE_NO_FILE")
        if nf and nf in path:
            out("running\n")
        out("present\n")
    if c.startswith("touch "):
        out("touched\n")
    mm = re.match(r"for p in ([0-9 ]+); do .*</dev/tcp/", c)
    if mm and "host_step.sh" not in c:
        closed = os.environ.get("FAKE_PORT_CLOSED", "").split(",")
        if closed == ["*"]:
            out("")
        out("".join("tcp %s %s\n" % (p, "closed" if p in closed else "open") for p in mm.group(1).split()))
    if "sha256sum H.yaml" in c:
        files = st.get("files", {}).get(n, {})
        out("".join("%s  %s\n" % (files[b], b) for b in ("H.yaml", "homography_C_matrix.yaml") if b in files))
    cm = re.search(r"display_capture\.sh (start|stop) \S*/out/(capture_[A-Za-z0-9_]+)", c)
    done_line = ""
    if cm and n == "de4sdv-aaos-build":
        caps = st.setdefault("captures", {})
        if cm.group(1) == "start":
            caps[cm.group(2)] = "recording"
        else:
            if caps.get(cm.group(2)) == "recording":
                caps[cm.group(2)] = kv("FAKE_CAPTURE_END").get(cm.group(2), "stop")
            if cm.group(2) in caps:
                done_line = "capture ended (%s), 1 segment(s)\n" % caps[cm.group(2)]
            else:
                done_line = "no capture in %s\n" % cm.group(2)
    fm = re.fullmatch(r"dd if=\$HOME/da-kit/([^/ ]+)/(\S+) bs=1M skip=(\d+) count=(\d+) status=none", c)
    if fm and fm.group(2) != "out.tgz" and os.environ.get("FAKE_REMOTE_FILES"):
        if "--ssh-flag=-T" not in argv:
            err("fake gcloud: a byte stream read without --ssh-flag=-T (a pty would change the bytes)\n", 2)
        p = os.path.join(os.environ["FAKE_REMOTE_FILES"], fm.group(2))
        if not os.path.isfile(p):
            err("dd: failed to open: No such file or directory\n", 1)
        skip, count = int(fm.group(3)), int(fm.group(4))
        slow = os.environ.get("FAKE_SLOW_FETCH")   # "vm:seconds" (or seconds): each such range read takes that long
        if slow and ":" in slow:
            slow = slow.split(":", 1)[1] if slow.split(":", 1)[0] == n else None
        if slow:
            save()
            fcntl.flock(lockf, fcntl.LOCK_UN)
            time.sleep(float(slow))
            fcntl.flock(lockf, fcntl.LOCK_EX)
            st = json.load(open(SF))
        data = open(p, "rb").read()[skip * 1048576:(skip + count) * 1048576]
        save()
        sys.stdout.buffer.write(data)
        sys.stdout.flush()
        sys.exit(0)
    dm = re.fullmatch(r"dd if=\$HOME/da-kit/([^/ ]+)/out\.tgz bs=1M skip=(\d+) count=(\d+) status=none", c)
    if dm:
        if "--ssh-flag=-T" not in argv:
            err("fake gcloud: a byte stream read without --ssh-flag=-T (a pty would change the bytes)\n", 2)
        skip, count = int(dm.group(2)), int(dm.group(3))
        tries = st.setdefault("range_reads", {})
        key = "%s:%d" % (n, skip)
        tries[key] = tries.get(key, 0) + 1
        hang = None
        for spec in filter(None, os.environ.get("FAKE_RANGE_HANG", "").split(",")):
            k, times, secs = spec.split(":")
            if int(k) == skip and tries[key] <= int(times):
                hang = float(secs)
        slow = os.environ.get("FAKE_SLOW_FETCH")
        if slow and ":" in slow:
            slow = slow.split(":", 1)[1] if slow.split(":", 1)[0] == n else None
        wait = (hang or 0) + (float(slow) if slow else 0)
        if wait:
            save()
            fcntl.flock(lockf, fcntl.LOCK_UN)
            time.sleep(wait)
            fcntl.flock(lockf, fcntl.LOCK_EX)
            st = json.load(open(SF))
        p = os.path.join(D, "%s_out.tgz" % n)
        if not os.path.exists(p):
            err("dd: failed to open: No such file or directory\n", 1)
        data = open(p, "rb").read()[skip * 1048576:(skip + count) * 1048576]
        short = dict((int(k), int(v)) for k, v in (x.split(":") for x in
                                                   filter(None, os.environ.get("FAKE_RANGE_SHORT", "").split(","))))
        rc = 0
        if skip in short and tries[key] <= short[skip]:
            data, rc = data[:len(data) // 2], 255
        save()
        sys.stdout.buffer.write(data)
        sys.stdout.flush()
        sys.exit(rc)
    if m:
        action, step = m.group(1), m.group(2)
        fail = os.environ.get("FAKE_FAIL_STEP") == step
        code = int(kv("FAKE_STEP_RC").get(step, 1 if fail else 0))
        if action == "run":
            if " receipts " in c:
                sys.stdout.write(receipts_out(c))
            hang = kv("FAKE_HANG_STEP").get(step)
            if hang:
                save()
                fcntl.flock(lockf, fcntl.LOCK_UN)
                time.sleep(float(hang))
                fcntl.flock(lockf, fcntl.LOCK_EX)
                st = json.load(open(SF))
            out(done_line + "=== %s end rc=%d (fake)\n" % (step, 1 if fail else 0), 1 if fail else 0)
        key = "%s:%s" % (n, step)
        if action == "start":
            st.setdefault("started", {})[key] = time.time()
            if "start_score_side.sh" in c:   # the S-CORE start's two evidence lines, by the real producer
                st.setdefault("tails", {})[key] = score_platform_tail()
            if "guest_up.sh" in c:           # guest_up's GUEST_IMAGE lines, in guest_up.sh's format
                st.setdefault("tails", {})[key] = guest_images_tail()
            if " receipts " in c:
                st.setdefault("tails", {})[key] = receipts_out(c)
            if done_line:
                st.setdefault("tails", {})[key] = done_line
            if "path_stop.sh" in c:
                line = os.environ.get("FAKE_PATH_STOP_LINE", '{"runTarget":"path_stopped","stopInstantRealNs":'
                                      '1795000012000000000,"stopInstantMonoNs":4321000000,"rc":0}')
                st.setdefault("tails", {})[key] = "" if line == "none" else line + "\n"
            out("started %s pid 4242\n" % step)
        if action == "status":
            # a detached step runs for its FAKE_HANG_STEP seconds from its start (or ends at once), then reports
            if key in st.get("signalled", {}) and os.environ.get("FAKE_STEP_IGNORES_TERM") != step:
                out("rc 143\n")
            t0 = st.get("started", {}).get(key)
            hang = kv("FAKE_HANG_STEP").get(step)
            if t0 is not None and hang and time.time() - t0 < float(hang):
                out("running\n")
            if fail and os.environ.get("FAKE_FAIL_AFTER_LOSS") == "1":
                # the failure only after the loss, in a later whole second than the loss (see the knob above)
                lost_at = st.get("lost_at", {}).values()
                if not lost_at or int(time.time()) <= int(max(lost_at)):
                    out("running\n")
            out("rc %d\n" % code)
        if action == "tail":
            term = kv("FAKE_TERM_TAIL").get(step) if key in st.get("signalled", {}) else None
            if term:   # killed by its TERM: no .rc file, so host_step.sh tail exits 1 after the log's lines
                out(st.get("tails", {}).get(key, "") + term + "\n", 1)
            add = kv("FAKE_TAIL_ADD").get(step)
            out(st.get("tails", {}).get(key, "") + (add + "\n" if add else "") + "=== %s end rc=%d (fake)\n" % (step, code))
        if action == "signal":
            st.setdefault("signalled", {})[key] = c.split()[-1]
            out("signalled %s\n" % step)
        if action == "pack":
            if os.environ.get("FAKE_PACK_FAIL") == n:
                err("ERROR: (gcloud.compute.start-iap-tunnel) Error while connecting [4003: 'failed to connect to "
                    "backend'].\n", 1)
            sid = re.search(r"da-kit/([^/]+)/", c).group(1)
            if os.environ.get("FAKE_FOREIGN_FETCH") == "1":
                sid = "19700101T000000Z"
            buf = io.BytesIO()
            with tarfile.open(fileobj=buf, mode="w:gz") as t:
                files = [("out/session_id", (sid + "\n").encode()), ("out/FAKE.txt", b"fake\n")]
                for cap, state in (st.get("captures", {}) if n == "de4sdv-aaos-build" else {}).items():
                    if state == "recording":
                        files += [("out/%s/seg_1.pending" % cap, b"170000000\n"),
                                  ("out/%s/seg_1.mp4.part" % cap, b"part of a segment still recording\n")]
                    else:
                        files += [("out/%s/capture.json" % cap, json.dumps({"end": state}).encode()),
                                  ("out/%s/capture.done" % cap, b"capture ended (%s), 1 segment(s)\n" % state.encode()),
                                  ("out/%s/app_record_warning.jsonl" % cap, b'{"event":"receipt"}\n'),
                                  ("out/%s/seg_1.mp4" % cap, b"a whole segment\n")]
                pad = int(os.environ.get("FAKE_PACK_PAD", "0") or 0)
                if pad:
                    import random
                    files.append(("out/pad.bin", random.Random(7).randbytes(pad)))
                for spec in filter(None, os.environ.get("FAKE_PACK_ADD", "").split(",")):
                    arc, local = spec.split("=", 1)
                    files.append((arc, open(local, "rb").read()))
                for name, data in files:
                    ti = tarfile.TarInfo(name)
                    ti.size = len(data)
                    t.addfile(ti, io.BytesIO(data))
            p = os.path.join(D, "%s_out.tgz" % n)
            open(p, "wb").write(buf.getvalue())
            out("%s %d\n" % (hashlib.sha256(buf.getvalue()).hexdigest(), len(buf.getvalue())))
    out("")

if words[:2] == ["compute", "scp"]:
    pos = [a for a in argv[argv.index("scp") + 1:] if not a.startswith("-") and a != opt("--zone")]
    src, dst = pos[:-1], pos[-1]
    if ":" in dst:  # upload
        n = dst.split(":", 1)[0]
        if st["vm"].get(n) != "RUNNING":
            err("scp: connection refused (fake)\n", 1)
        for f in src:
            sha = hashlib.sha256(open(f, "rb").read()).hexdigest()
            if os.path.basename(f).startswith("kit.tgz") or "/tmp/da-kit-" in dst:
                st["kit_sha"][n] = sha
            else:
                st.setdefault("files", {}).setdefault(n, {})[os.path.basename(f)] = sha
        out("")
    n = src[0].split(":", 1)[0]
    if st["vm"].get(n) != "RUNNING":
        err("scp: connection refused (fake)\n", 1)
    slow = os.environ.get("FAKE_SLOW_FETCH")
    if slow and ":" in slow:
        slow = slow.split(":", 1)[1] if slow.split(":", 1)[0] == n else None
    if slow and any(x.endswith("/out.tgz") for x in src):
        save()
        fcntl.flock(lockf, fcntl.LOCK_UN)
        time.sleep(float(slow))
        fcntl.flock(lockf, fcntl.LOCK_EX)
        st = json.load(open(SF))
    for f in src:
        path = f.split(":", 1)[1]
        if path.endswith("/out.tgz"):
            if os.environ.get("FAKE_FETCH_FAIL") == n:
                err("scp: connection closed (fake)\n", 1)
            p = os.path.join(D, "%s_out.tgz" % n)
            if not os.path.exists(p):
                err("scp: no such file (fake)\n", 1)
            shutil.copy(p, os.path.join(dst, "out.tgz"))
        else:  # any other file: a stand-in with its remote path as content
            open(os.path.join(dst, os.path.basename(path)), "w").write("fake %s\n" % path)
    out("")

err("fake gcloud: unhandled call: %s\n" % " ".join(argv), 2)
