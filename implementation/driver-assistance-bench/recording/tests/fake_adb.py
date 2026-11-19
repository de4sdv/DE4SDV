#!/usr/bin/env python3
"""Fake adb for the tests of display_capture.sh and ivi_clock.sh (no Android involved).

State in $FAKE_ADB_DIR/state.json; every call appended to $FAKE_ADB_DIR/calls.log as a JSON list. The guest clock is
this host's clock plus an offset (FAKE_GUEST_OFFSET, default 0.25 s) until `toybox date -s @<t>` sets it. Two
displays. `screenrecord --time-limit N ... <file> &` starts a fake recording that ends after N s or on `kill -INT`;
`pull` of a segment copies $FAKE_SEG_MP4 (a real short video made by the test).

Knobs that let a test order the events itself, with no reliance on the host's speed:
  FAKE_LIMIT_DIR      the n-th recording (in launch order) reaches its time limit when $FAKE_LIMIT_DIR/limit_<n>
                      exists, not after --time-limit seconds of this host's clock
  FAKE_HOLD_PULL      "<n>:<path>": the pull of seg_<n>.mp4 returns only once <path> exists (at most 60 s), as a
                      long pull of a large segment during which a stop request comes
  FAKE_HOLD_POLL      "<n>:<path>": a poll (kill -0) of the n-th recording answers only once <path> exists (at most
                      60 s), as a stop request that comes just when the recording reaches its time limit
  FAKE_HOLD_INT       "<n>:<path>": the kill -INT of the n-th recording is answered only once <path> exists (at most
                      60 s), as a recording that reaches its time limit between the alive poll and the signal
  FAKE_CALL_DELAY_S   every call takes this much longer (a loaded host)
  FAKE_PULL_DELAY_S   every pull of a segment takes this much longer (a large segment over a slow link)
  FAKE_PULL_FAIL      "<n>": the pull of seg_<n>.mp4 fails
  FAKE_DF_AVAIL_KB    the free space df -k reports for /data (default 4000000)
  FAKE_ALIVE_TAIL_S   a poll (kill -0) of a live recording writes "alive", then after this many seconds one more
                      empty line: adb's output still coming after the match (a reader that stops at the match, such
                      as grep -q, makes that write fail with SIGPIPE, and adb's status non-zero)
  FAKE_POLL_FAIL      "<n>:<from>[-<to>]": the polls (kill -0) number <from> to <to> (default: every later one) of
                      the n-th recording get no answer: nothing on stdout, adb's "error: closed", rc 1
  FAKE_DEAD_FROM      "<n>": the n-th recording and every later one end at once (a full /data, a display gone)
  FAKE_HANG           "<text>:<path>": once <path> exists, a call whose words contain <text> hangs (120 s), as a
                      shell on a device that went offline
  FAKE_PULL_GROW      "<n>:<s>": the pull of seg_<n>.mp4 writes its file in 10 parts over <s> seconds
FAKE_HOLD_PULL takes "*" for <n>: every segment's pull is held. A poll whose command carries `|| echo ended` is
answered `ended <guest clock>` for a recording that ended.
"""
import fcntl
import json
import os
import re
import shutil
import sys
import time

D = os.environ["FAKE_ADB_DIR"]
SF = os.path.join(D, "state.json")
argv = sys.argv[1:]
with open(os.path.join(D, "calls.log"), "a") as f:
    f.write(json.dumps([round(time.time(), 4)] + argv) + "\n")
time.sleep(float(os.environ.get("FAKE_CALL_DELAY_S", "0")))


def hold(knob, matches):
    """Wait, before the call is answered, until the knob's file exists (at most 60 s)."""
    v = os.environ.get(knob, "")
    if v and matches(v.split(":", 1)[0]):
        until = time.time() + 60
        while not os.path.exists(v.split(":", 1)[1]) and time.time() < until:
            time.sleep(0.01)


hold("FAKE_HOLD_PULL", lambda n: "pull" in argv and any(re.search(r"/seg_%s\.mp4$" % (r"\d+" if n == "*" else n), a)
                                                           for a in argv))
if os.environ.get("FAKE_HANG"):
    _text, _path = os.environ["FAKE_HANG"].split(":", 1)
    if os.path.exists(_path) and _text in " ".join(argv):
        time.sleep(120)
hold("FAKE_HOLD_POLL", lambda n: any(re.search(r"kill -0 %d\b" % (3999 + int(n)), a) for a in argv))
hold("FAKE_HOLD_INT", lambda n: any(re.search(r"kill -INT %d\b" % (3999 + int(n)), a) for a in argv))
if "pull" in argv and argv[-2].endswith(".mp4"):
    time.sleep(float(os.environ.get("FAKE_PULL_DELAY_S", "0")))
lockf = open(SF + ".lock", "a")
fcntl.flock(lockf, fcntl.LOCK_EX)
st = json.load(open(SF)) if os.path.exists(SF) else {"offset": float(os.environ.get("FAKE_GUEST_OFFSET", "0.25")),
                                                    "recs": {}, "next_pid": 4000}
DISPLAYS = ["4619827259835644672", "4619827551948147201"]


def done(s="", rc=0):
    json.dump(st, open(SF, "w"))
    sys.stdout.write(s)
    sys.exit(rc)


def guest_now():
    return time.time() + st["offset"]


def alive(r):
    if not r or r["ended"]:
        return False
    if os.environ.get("FAKE_DEAD_FROM") and r["n"] >= int(os.environ["FAKE_DEAD_FROM"]):
        return False
    if os.environ.get("FAKE_LIMIT_DIR"):
        return not os.path.exists(os.path.join(os.environ["FAKE_LIMIT_DIR"], "limit_%d" % r["n"]))
    return time.time() - r["start"] < r["limit"]


if argv[:1] == ["-s"]:
    argv = argv[2:]
if argv[:1] == ["shell"]:
    c = " ".join(argv[1:])
    if c.strip() == "date +%s.%N":
        done("%.9f\r\n" % guest_now())
    if "dumpsys SurfaceFlinger --display-id" in c:
        done("".join("Display %s (HWC display %d): port=%d pnpId=GGL displayName=\"Fake\"\r\n" % (d, i, i)
                     for i, d in enumerate(DISPLAYS)))
    if "screenrecord" in c:
        lim = float(re.search(r"--time-limit (\d+)", c).group(1))
        path = re.search(r"(\S+\.mp4)", c).group(1)
        pid = st["next_pid"]
        st["next_pid"] += 1
        before = guest_now()
        st["recs"][str(pid)] = {"start": time.time(), "limit": lim, "path": path, "ended": False,
                                "n": pid - 3999}
        out = "%.9f\r\npid=%d\r\n%.9f\r\n" % (before, pid, guest_now())
        if re.search(r"\bdf -k /data\b", c):
            out += "Filesystem     1K-blocks    Used Available Use%% Mounted on\r\n/dev/block/dm-9 8000000 100 %s 1%% /data\r\n" \
                % os.environ.get("FAKE_DF_AVAIL_KB", "4000000")
        done(out)
    m = re.search(r"kill -0 (\d+)", c)
    if m:
        r = st["recs"].get(m.group(1))
        if r is not None:
            r["polls"] = r.get("polls", 0) + 1
            f = os.environ.get("FAKE_POLL_FAIL", "")
            if f and int(f.split(":")[0]) == r["n"]:
                lo, _, hi = f.split(":")[1].partition("-")
                if int(lo) <= r["polls"] <= (int(hi) if hi else 10 ** 9):
                    sys.stderr.write("error: closed\n")
                    done("", 1)
        live = alive(r)
        tail = float(os.environ.get("FAKE_ALIVE_TAIL_S", "0"))
        if live and tail > 0:
            json.dump(st, open(SF, "w"))
            fcntl.flock(lockf, fcntl.LOCK_UN)
            sys.stdout.write("alive\r\n")
            sys.stdout.flush()
            time.sleep(tail)
            sys.stdout.write("\r\n")
            sys.stdout.flush()   # a reader that is gone: BrokenPipeError, a non-zero exit, as adb's SIGPIPE
            sys.exit(0)
        done("alive\r\n" if live else ("ended %.9f\r\n" % guest_now() if "echo ended" in c else ""))
    m = re.search(r"kill -INT (\d+)", c)
    if m:   # a guest shell `kill -INT <pid> 2>/dev/null && echo sent`: the signal reaches a live recording only
        r = st["recs"][m.group(1)]
        live = alive(r)
        r["ended"] = True
        r["int"] = live
        done("sent\r\n" if live and "echo sent" in c else "")
    m = re.search(r"stat -c %s (\S+\.mp4)", c)
    if m:
        done("%d\r\n" % os.path.getsize(os.environ["FAKE_SEG_MP4"]))
    if re.search(r"\bdf -k /data\b", c):
        done("Filesystem     1K-blocks    Used Available Use%% Mounted on\r\n/dev/block/dm-9 8000000 %d %s 1%% /data\r\n"
             % (100, os.environ.get("FAKE_DF_AVAIL_KB", "4000000")))
    m = re.search(r"toybox date -s @([0-9.]+)", c)
    if m:
        st["offset"] = float(m.group(1)) - time.time()
        done("")
    if c.strip() == "am get-current-user":
        done("10\r\n")   # an AAOS IVI runs its apps as a secondary user
    if "dumpsys media.audio_flinger" in c:
        done("Libraries loaded:\r\n Output thread 0x7 type 0 (MIXER):\r\n  Standby: yes\r\n")
    done("")
if argv[:3] == ["exec-out", "screencap", "-d"]:
    sys.stdout.buffer.write(b"\x89PNG\r\n\x1a\nfake-" + argv[3].encode())
    done("")
if argv[:1] == ["pull"]:
    src, dst = argv[1], argv[2]
    if src.endswith(".mp4"):
        if os.environ.get("FAKE_PULL_FAIL") and src.endswith("/seg_%s.mp4" % os.environ["FAKE_PULL_FAIL"]):
            data = open(os.environ["FAKE_SEG_MP4"], "rb").read()
            open(dst, "wb").write(data[:len(data) // 2])   # a cut pull leaves a part of the file behind
            sys.stderr.write("adb: error: failed to copy '%s': connection reset\n" % src)
            done("", 1)
        g = os.environ.get("FAKE_PULL_GROW", "")
        if g and src.endswith("/seg_%s.mp4" % g.split(":")[0]):
            json.dump(st, open(SF, "w"))
            fcntl.flock(lockf, fcntl.LOCK_UN)
            data = open(os.environ["FAKE_SEG_MP4"], "rb").read()
            with open(dst, "wb") as w:
                for i in range(10):
                    w.write(data[i * len(data) // 10:(i + 1) * len(data) // 10])
                    w.flush()
                    time.sleep(float(g.split(":")[1]) / 10)
            done("1 file pulled\n")
        shutil.copy(os.environ["FAKE_SEG_MP4"], dst)
        done("1 file pulled\n")
    if os.environ.get("FAKE_APP_RECORD") and src.endswith(os.path.basename(os.environ["FAKE_APP_RECORD"])):
        shutil.copy(os.environ["FAKE_APP_RECORD"], dst)
        done("1 file pulled\n")
    sys.stderr.write("adb: error: remote object '%s' does not exist\n" % src)
    done("", 1)
if argv[:1] == ["logcat"]:
    done("%.3f  1000  1000 I CollisionWarning: receipt requested=1 (fake)\n" % guest_now())
sys.stderr.write("fake adb: unhandled %s\n" % argv)
done("", 2)
