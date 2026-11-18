#!/usr/bin/env python3
"""Fake gcloud for the dry runs of da_session.sh (local control-flow tests only; never touches the cloud).

Derived from the SIM20-G4 dry-run fake. State in $FAKE_DIR/state.json (file-locked); every call is appended to
$FAKE_DIR/calls.log as one JSON list of its arguments. Scenario knobs (environment):
  FAKE_INIT          "vm:STATUS,..."  status before the session (default TERMINATED for the three bench VMs)
  FAKE_START         "vm:R1|R2|...,..."  results of successive start calls (OK STOCKOUT POOL QUOTA ERROR; last repeats)
  FAKE_PREEMPT       "vm:n"  the n-th status read after the VM came up returns TERMINATED (once)
  FAKE_GPU_RUNNING   "project:name"  another GPU VM running in that project
  FAKE_FAIL_STEP     a step name whose `host_step.sh run|status` fails
  FAKE_HANG_STEP     "step:seconds"  `host_step.sh run <step>` sleeps that long before answering
  FAKE_SSH_DOWN      a VM name that never answers SSH
  FAKE_GUEST_STOP_FAIL  1: a crosvm process stays after every guests' stop; once: after the first stop only
  FAKE_IP            "vm:ip,..."  internal IPs other than the defaults (the session must read them from gcloud)
  FAKE_NO_FILE       a substring: `test -e <path>` of a matching path never finds it (the step keeps "running")
  FAKE_FOREIGN_FETCH    1: a fetched tarball carries another session's id
  FAKE_NO_STOP       a VM name that stays RUNNING after a stop
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
    json.dump(st, open(SF, "w"))


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

if words[:3] == ["compute", "instances", "describe"]:
    n = words[3]
    if n not in st["vm"]:
        err("ERROR: (gcloud.compute.instances.describe) Could not fetch resource:\n - The resource was not found\n")
    fmt = opt("--format") or ""
    if "networkIP" in fmt:
        out(kv("FAKE_IP").get(n, VMS[n][2]) + "\n")
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
    if os.environ.get("FAKE_NO_STOP") != n:
        st["vm"][n] = "TERMINATED"
    out("Stopping instance(s) %s (async).\n" % n)

if words[:2] == ["compute", "instances"] and len(words) > 2 and words[2] in ("delete", "create"):
    err("fake gcloud: %s is never expected from a session\n" % words[2], 3)

if words[:2] == ["compute", "ssh"]:
    n = words[2]
    c = opt("--command") or ""
    if st["vm"].get(n) != "RUNNING" or os.environ.get("FAKE_SSH_DOWN") == n:
        err("ssh: connect to host 192.0.2.10 port 22: Connection refused\n", 255)
    if c == "true":
        out("")
    m = re.search(r"host_step\.sh (run|start|status|signal|pack)\s*(\S*)", c)
    if "sha256sum /tmp/da-kit-" in c:
        out("%s  /tmp/da-kit.tgz\n" % st["kit_sha"].get(n, "none"))
    if "shutdown -h" in c:
        mm = re.search(r"\+(\d+)", c)
        out("safety-net-%s\n" % (mm.group(1) if mm else "?"))
    mm = re.search(r"safety_net\.sh arm (\d+)", c)
    if mm:
        out("safety-net-%s\n" % mm.group(1))
    gfail = os.environ.get("FAKE_GUEST_STOP_FAIL", "")
    if "guest_stop.sh" in c:
        st["guest_stops"] = st.get("guest_stops", 0) + 1
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
    if "sha256sum H.yaml" in c:
        files = st.get("files", {}).get(n, {})
        out("".join("%s  %s\n" % (files[b], b) for b in ("H.yaml", "homography_C_matrix.yaml") if b in files))
    if m:
        action, step = m.group(1), m.group(2)
        fail = os.environ.get("FAKE_FAIL_STEP") == step
        if action == "run":
            hang = kv("FAKE_HANG_STEP").get(step)
            if hang:
                save()
                fcntl.flock(lockf, fcntl.LOCK_UN)
                time.sleep(float(hang))
                fcntl.flock(lockf, fcntl.LOCK_EX)
                st = json.load(open(SF))
            out("=== %s end rc=%d (fake)\n" % (step, 1 if fail else 0), 1 if fail else 0)
        if action == "start":
            out("started %s pid 4242\n" % step)
        if action == "status":
            out("rc %d\n" % (1 if fail else 0))
        if action == "signal":
            out("signalled %s\n" % step)
        if action == "pack":
            sid = re.search(r"da-kit/([^/]+)/", c).group(1)
            if os.environ.get("FAKE_FOREIGN_FETCH") == "1":
                sid = "19700101T000000Z"
            buf = io.BytesIO()
            with tarfile.open(fileobj=buf, mode="w:gz") as t:
                for name, data in (("out/session_id", (sid + "\n").encode()), ("out/FAKE.txt", b"fake\n")):
                    ti = tarfile.TarInfo(name)
                    ti.size = len(data)
                    t.addfile(ti, io.BytesIO(data))
            p = os.path.join(D, "%s_out.tgz" % n)
            open(p, "wb").write(buf.getvalue())
            out(hashlib.sha256(buf.getvalue()).hexdigest() + "\n")
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
    for f in src:
        path = f.split(":", 1)[1]
        if path.endswith("/out.tgz"):
            p = os.path.join(D, "%s_out.tgz" % n)
            if not os.path.exists(p):
                err("scp: no such file (fake)\n", 1)
            shutil.copy(p, os.path.join(dst, "out.tgz"))
        else:  # any other file: a stand-in with its remote path as content
            open(os.path.join(dst, os.path.basename(path)), "w").write("fake %s\n" % path)
    out("")

err("fake gcloud: unhandled call: %s\n" % " ".join(argv), 2)
