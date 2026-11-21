"""A fake `carla` module for the chase recorder's tests: just the calls the recorder makes.

Knobs (environment): FAKE_CARLA_LOAD_S (get_world raises CARLA's time-out error until then), FAKE_HERO_AFTER_S (a new
hero appears that long after the world first answered), FAKE_CARLA_FRAMES (images the camera delivers, one per 0.05 s of simulation time, then the world
leaves synchronous mode), FAKE_CARLA_SPAWN_LOG (a JSON file the camera's spawn is written to), FAKE_CARLA_FIRST_LIST_S
(the first get_actors call takes that long before it reads the actors).
Each image is one tick: the world's on_tick callbacks get a snapshot of the hero and the camera first. A synchronous
world that pauses between ticks is modelled by the world side's fake (paused_world.py).
"""
import json
import os
import threading
import time

_T0 = time.time()
_STATE = {"sync": True, "hero": None, "cam": None, "world_t": None, "on_tick": {}}


class AttachmentType:
    Rigid = "Rigid"
    SpringArm = "SpringArm"
    SpringArmGhost = "SpringArmGhost"


class Location:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x, self.y, self.z = x, y, z


class Rotation:
    def __init__(self, pitch=0.0, yaw=0.0, roll=0.0):
        self.pitch, self.yaw, self.roll = pitch, yaw, roll


class Transform:
    def __init__(self, location=None, rotation=None):
        self.location, self.rotation = location or Location(), rotation or Rotation()


class _Actor:
    def __init__(self, actor_id, role):
        self.id = actor_id
        self.attributes = {"role_name": role}


class _Actors(list):
    def filter(self, pattern):
        return _Actors(x for x in self if pattern != "vehicle.*" or isinstance(x, _Actor))

    def find(self, actor_id):
        for x in self:
            if x.id == actor_id:
                return x
        return None


class _Snapshot:
    def __init__(self, frame):
        self.frame = frame
        self._ids = [x.id for x in (_STATE["hero"], _STATE["cam"]) if x is not None]

    def find(self, actor_id):
        return object() if actor_id in self._ids else None


class _Image:
    def __init__(self, frame, w, h):
        self.frame, self.width, self.height = frame, w, h
        self.timestamp = frame * 0.05
        level = (frame * 7) % 256
        self.raw_data = bytes([level, level, level, 255]) * (w * h)


class _Camera:
    def __init__(self, attrs):
        self.id = 900
        self.attrs = attrs
        self._stop = False

    def listen(self, cb):
        n = int(os.environ.get("FAKE_CARLA_FRAMES", "30"))
        w, h = int(self.attrs["image_size_x"]), int(self.attrs["image_size_y"])

        def run():
            for i in range(n):
                if self._stop:
                    return
                for tick_cb in list(_STATE["on_tick"].values()):
                    tick_cb(_Snapshot(1000 + i))
                cb(_Image(1000 + i, w, h))
                time.sleep(0.05)   # the world side ticks at 0.05 s of wall time
            _STATE["sync"] = False   # the world side ends the run

        threading.Thread(target=run, daemon=True).start()

    def stop(self):
        self._stop = True

    def destroy(self):
        _STATE["cam"] = None


class _Blueprint:
    def __init__(self):
        self.attrs = {}

    def set_attribute(self, k, v):
        self.attrs[k] = v


class _Settings:
    @property
    def synchronous_mode(self):
        return _STATE["sync"]


class _World:
    def get_actors(self):
        slow = float(os.environ.get("FAKE_CARLA_FIRST_LIST_S", "0") or 0)
        if slow and not _STATE.get("listed"):   # a slow first actor list (the recorder's list of heroes already there)
            _STATE["listed"] = True
            time.sleep(slow)
        acts = _Actors()
        if time.time() - _STATE["world_t"] >= float(os.environ.get("FAKE_HERO_AFTER_S", "0.5")):
            if _STATE["hero"] is None:
                _STATE["hero"] = _Actor(77, "hero")
            acts.append(_STATE["hero"])
        if _STATE["cam"] is not None:
            acts.append(_STATE["cam"])
        return acts

    def get_settings(self):
        return _Settings()

    def on_tick(self, cb):
        n = len(_STATE["on_tick"]) + 1
        _STATE["on_tick"][n] = cb
        return n

    def remove_on_tick(self, n):
        _STATE["on_tick"].pop(n, None)

    def get_blueprint_library(self):
        class _Lib:
            def find(self, name):
                assert name == "sensor.camera.rgb"
                return _Blueprint()
        return _Lib()

    def spawn_actor(self, bp, tf, attach_to=None, attachment_type=None):
        cam = _Camera(bp.attrs)
        _STATE["cam"] = cam
        log = os.environ.get("FAKE_CARLA_SPAWN_LOG")
        if log:
            json.dump({"attrs": bp.attrs, "x": tf.location.x, "y": tf.location.y, "z": tf.location.z,
                       "pitch": tf.rotation.pitch, "attach_to": attach_to.id, "attachment": attachment_type},
                      open(log, "w"))
        return cam


class Client:
    def __init__(self, host, port):
        self.timeout = None

    def set_timeout(self, s):
        self.timeout = s

    def get_world(self):
        if time.time() - _T0 < float(os.environ.get("FAKE_CARLA_LOAD_S", "0")):
            time.sleep(min(0.2, self.timeout or 0.2))
            raise RuntimeError("time-out of 10000ms while waiting for the simulator")
        if _STATE["world_t"] is None:
            _STATE["world_t"] = time.time()
        return _World()
