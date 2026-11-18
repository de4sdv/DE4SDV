#!/usr/bin/env python3
"""Fake adb for the tests of display_capture.sh and ivi_clock.sh (no Android involved).

State in $FAKE_ADB_DIR/state.json; every call appended to $FAKE_ADB_DIR/calls.log as a JSON list. The guest clock is
this host's clock plus an offset (FAKE_GUEST_OFFSET, default 0.25 s) until `toybox date -s @<t>` sets it. Two
displays. `screenrecord --time-limit N ... <file> &` starts a fake recording that ends after N s or on `kill -INT`;
`pull` of a segment copies $FAKE_SEG_MP4 (a real short video made by the test).
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
        st["recs"][str(pid)] = {"start": time.time(), "limit": lim, "path": path, "ended": False}
        done("%.9f\r\npid=%d\r\n%.9f\r\n" % (before, pid, guest_now()))
    m = re.search(r"kill -0 (\d+)", c)
    if m:
        r = st["recs"].get(m.group(1))
        alive = r and not r["ended"] and time.time() - r["start"] < r["limit"]
        done("alive\r\n" if alive else "")
    m = re.search(r"kill -INT (\d+)", c)
    if m:
        st["recs"][m.group(1)]["ended"] = True
        st["recs"][m.group(1)]["int"] = True
        done("")
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
