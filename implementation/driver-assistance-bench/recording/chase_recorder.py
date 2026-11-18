#!/usr/bin/env python3
"""Chase-view recorder of the INC-DRIVING-002 bench (brief row B14), run on the simulator host.

INC-DRIVING-001's recorder v3 (outputs/slice10b/WP2/session10_scripts/l4_recorder_v3.py), with these changes:
  * chase view B: x -10 m, z 5 m on the spring arm (SpringArmGhost), 15 degrees down. The arm already turns the camera
    to look from its offset at the car, atan2(z, -x) = 26.57 degrees down, and adds the camera's own pitch on top, so
    the own pitch is -15 + 26.57 = +11.57 degrees (the spring-arm pitch rule; SIM20-G4 views, round 2);
  * 1920x1080 at one image per simulation step: at the fixed step of 0.05 s that is 20 frames per second of
    simulation time, and the video is labelled 20 fps;
  * NVENC (h264_nvenc) after a 1 s test encode at the recording size, libx264 as the fallback, named in the summary;
  * the simulator's world first, for up to --sim-wait-s (120 s), as the hero check of INC-DRIVING-001's session did;
  * ffmpeg gets --ffmpeg-grace-s (20 s) to finish the file after its input ends, then it is killed;
  * <video>.frames.csv: one row per frame written to the encoder (video_index, carla_frame, sim_time_s,
    arrival_unix_s), so that a cut can place each frame at the simulation time and at the real time of its tick;
  * SIGTERM and SIGINT end the recording cleanly (the file is finished).
The camera stands for no sensor of the vehicle (the simulator server's doc in the phase 8 model). The recorder
attaches to the first hero that appears after it starts and ends when the world leaves synchronous mode, when the hero
or the camera is deleted, or at --max-s. Exit status 0 only if it attached and wrote frames (the lap rule needs a
recorder that wrote frames).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import queue
import signal
import subprocess
import threading
import time

VIEW_B = {"x": -10.0, "y": 0.0, "z": 5.0, "wanted_pitch_deg": -15.0}


def spring_arm_own_pitch(x: float, z: float, wanted_pitch_deg: float) -> float:
    """The camera's own pitch on a spring-arm mount that gives the wanted pitch (CARLA's ActorAttacher rule)."""
    return wanted_pitch_deg + math.degrees(math.atan2(z, -x))


def encoder_args(encoder: str, bitrate: str) -> list[str]:
    if encoder == "h264_nvenc":
        return ["-c:v", "h264_nvenc", "-preset", "p4", "-b:v", bitrate]
    if encoder == "libx264":
        return ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20"]
    raise ValueError("unknown encoder %r" % encoder)


def ffmpeg_command(width: int, height: int, fps: int, encoder: str, bitrate: str, video: str) -> list[str]:
    return ["ffmpeg", "-hide_banner", "-y", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", "%dx%d" % (width, height),
            "-r", str(fps), "-i", "-", *encoder_args(encoder, bitrate), "-pix_fmt", "yuv420p", video]


def nvenc_works(width: int, height: int, fps: int, bitrate: str, log_path: str) -> bool:
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
           "testsrc=size=%dx%d:rate=%d" % (width, height, fps), "-t", "1", *encoder_args("h264_nvenc", bitrate),
           "-pix_fmt", "yuv420p", "-f", "null", "-"]
    with open(log_path, "w") as log:
        return subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT).returncode == 0


def choose_encoder(requested: str, nvenc_ok) -> tuple[str, str | None]:
    """(encoder, fallback reason). 'auto' takes NVENC when its test encode works, else libx264, and says why."""
    if requested != "auto":
        return requested, None
    if nvenc_ok():
        return "h264_nvenc", None
    return "libx264", "the NVENC test encode failed: libx264 on the CPU (it loads the simulator host's CPU)"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--video", default="chase_view.mp4")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=2000)
    ap.add_argument("--role-name", default="hero")
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--fov", default="90")
    ap.add_argument("--fps", type=int, default=20, help="the label of the video: frames per second of simulation time")
    ap.add_argument("--sensor-tick", default="0.0", help="0.0: one image per simulation step")
    ap.add_argument("--encoder", default="auto", choices=("auto", "h264_nvenc", "libx264"))
    ap.add_argument("--bitrate", default="12M")
    ap.add_argument("--queue", type=int, default=60)
    ap.add_argument("--max-s", type=float, default=1800.0)
    ap.add_argument("--sim-wait-s", type=float, default=120.0)
    ap.add_argument("--ffmpeg-grace-s", type=float, default=20.0)
    a = ap.parse_args()

    import carla  # the simulator host's CARLA 1.0 wheel; imported here so that the helpers above test without it

    os.makedirs(a.out, exist_ok=True)
    video = os.path.join(a.out, a.video)
    t_start = time.time()
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    own_pitch = spring_arm_own_pitch(VIEW_B["x"], VIEW_B["z"], VIEW_B["wanted_pitch_deg"])
    st = {"version": 4, "view": dict(VIEW_B, own_pitch_deg=round(own_pitch, 2), attachment="SpringArmGhost",
                                      width=a.width, height=a.height, fov=a.fov, sensor_tick=a.sensor_tick, fps=a.fps),
          "ego_id": None, "frames": 0, "first_frame": None, "last_frame": None, "gaps": [], "size_errors": 0,
          "queued": 0, "dropped": 0, "written": 0, "write_errors": 0, "end": None}

    # 1. the simulator's world first: a restarted server listens before its map is loaded
    while True:
        try:
            client = carla.Client(a.host, a.port)
            client.set_timeout(10.0)
            world = client.get_world()
            break
        except RuntimeError:
            if time.time() - t_start > a.sim_wait_s or stop.is_set():
                st["end"] = "the simulator did not answer within %.0f s" % a.sim_wait_s
                json.dump(st, open(os.path.join(a.out, "summary.json"), "w"), indent=1)
                print(json.dumps(st))
                return 1
            time.sleep(2.0)
    st["sim_answered_after_s"] = round(time.time() - t_start, 1)
    print("the simulator answered after %.1f s" % st["sim_answered_after_s"], flush=True)

    def heroes():
        return [x for x in world.get_actors().filter("vehicle.*") if x.attributes.get("role_name") == a.role_name]

    pre = sorted(x.id for x in heroes())
    st["pre_existing_heroes"] = pre
    # the encoder after the list of heroes (a hero spawned during the test encode is new) and before the wait, so
    # that the camera attaches as soon as the hero appears
    enc, why = choose_encoder(a.encoder, lambda: nvenc_works(a.width, a.height, a.fps, a.bitrate,
                                                             os.path.join(a.out, "nvenc_test.log")))
    st["encoder"], st["encoder_fallback"] = enc, why
    ego = None
    while time.time() - t_start < a.max_s and not stop.is_set():
        new = [x for x in heroes() if x.id not in pre]
        if new:
            ego = new[0]
            break
        time.sleep(0.2)

    cmd = ffmpeg_command(a.width, a.height, a.fps, enc, a.bitrate, video)
    st["ffmpeg_command"] = cmd
    ff_log = open(os.path.join(a.out, "ffmpeg.log"), "w")
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=ff_log, stderr=subprocess.STDOUT)
    q: queue.Queue = queue.Queue(maxsize=a.queue)
    csv = open(video + ".frames.csv", "w")
    csv.write("video_index,carla_frame,sim_time_s,arrival_unix_s\n")

    def writer():
        while True:
            item = q.get()
            if item is None:
                return
            frame, sim_t, arrival, data = item
            try:
                ff.stdin.write(data)
                csv.write("%d,%d,%.6f,%.6f\n" % (st["written"], frame, sim_t, arrival))
                st["written"] += 1
            except (BrokenPipeError, OSError):
                st["write_errors"] += 1

    wt = threading.Thread(target=writer, daemon=True)
    wt.start()

    def on_view(img):
        arrival = time.time()
        st["frames"] += 1
        if st["first_frame"] is None:
            st["first_frame"] = img.frame
        elif img.frame != st["last_frame"] + 1:
            st["gaps"].append([st["last_frame"], img.frame])
        st["last_frame"] = img.frame
        if img.width != a.width or img.height != a.height:
            st["size_errors"] += 1
            return
        try:
            q.put_nowait((img.frame, img.timestamp, arrival, bytes(img.raw_data)))
            st["queued"] += 1
        except queue.Full:
            st["dropped"] += 1   # the stream callback never blocks; the drop is counted

    cam = None
    try:
        if ego is None:
            st["end"] = "stopped before a hero appeared" if stop.is_set() else "no new hero within --max-s"
        else:
            st["ego_id"] = ego.id
            bp = world.get_blueprint_library().find("sensor.camera.rgb")
            for k, v in (("image_size_x", str(a.width)), ("image_size_y", str(a.height)), ("fov", a.fov),
                         ("sensor_tick", a.sensor_tick), ("role_name", "recording_view")):
                bp.set_attribute(k, v)
            tf = carla.Transform(carla.Location(x=VIEW_B["x"], y=VIEW_B["y"], z=VIEW_B["z"]),
                                 carla.Rotation(pitch=own_pitch))
            cam = world.spawn_actor(bp, tf, attach_to=ego, attachment_type=carla.AttachmentType.SpringArmGhost)
            st["camera_id"] = cam.id
            cam.listen(on_view)
            st["attach_after_s"] = round(time.time() - t_start, 1)
            seen_sync = False
            while time.time() - t_start < a.max_s:
                if stop.wait(1.0):
                    st["end"] = "signal"
                    break
                sync = world.get_settings().synchronous_mode
                seen_sync = seen_sync or sync
                if seen_sync and not sync:
                    st["end"] = "world left synchronous mode (end of run)"
                    break
                actors = world.get_actors()
                if actors.find(ego.id) is None or actors.find(cam.id) is None:
                    st["end"] = "ego or camera deleted by another client"
                    break
            else:
                st["end"] = "max-s"
    finally:
        if cam is not None:
            try:
                cam.stop()
                cam.destroy()
            except RuntimeError as exc:
                st["stop_error"] = str(exc)
        q.put(None)
        wt.join(timeout=60)
        csv.close()
        try:
            ff.stdin.close()
        except OSError:
            pass
        try:
            st["ffmpeg_rc"] = ff.wait(timeout=a.ffmpeg_grace_s)
        except subprocess.TimeoutExpired:
            ff.kill()
            st["ffmpeg_rc"] = None
            st["ffmpeg_killed_after_grace_s"] = a.ffmpeg_grace_s
        st["ran_s"] = round(time.time() - t_start, 1)
        json.dump(st, open(os.path.join(a.out, "summary.json"), "w"), indent=1)
        print(json.dumps(st), flush=True)
    return 0 if st["ego_id"] is not None and st["written"] > 0 and st["ffmpeg_rc"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
