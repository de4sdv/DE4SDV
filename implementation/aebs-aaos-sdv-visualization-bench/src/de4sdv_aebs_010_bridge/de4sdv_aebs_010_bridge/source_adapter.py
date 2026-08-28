"""ROS 2 source adapter and frame server for the 010 visualization bridge.

Wires the pure core (:mod:`frame_assembler`) to the pinned 009B bench topics.
Subscriptions only: this node publishes nothing on ROS topics. The only
output is the outbound length-delimited frame stream served to the AAOS
ingress (new port; the INC-MW-010 port is not used).

ROS 2 is imported lazily so the pure core and its tests run on hosts without
a ROS installation.
"""

from __future__ import annotations

import json
import socket
import struct
import threading
from typing import Any

from .frame_assembler import (
    FrameAssembler,
    FrameValidator,
    PresentationWatchdog,
    SourceObservation,
)

TOPIC_RSS = "/control/autonomous_emergency_braking/debug/rss_distance"
TOPIC_CLOUD = "/control/autonomous_emergency_braking/debug/obstacle_pointcloud"
TOPIC_DIAGNOSTICS = "/diagnostics"
TOPIC_WARNING = "/de4sdv/aebs_009b/warning_request"
TOPIC_BRAKING = "/de4sdv/aebs_009b/emergency_braking_request"
TOPIC_LIFECYCLE = "/de4sdv/aebs_009b/coordination_state"

DIAGNOSTIC_NAME = "autonomous_emergency_braking: aeb_emergency_stop"
INTERVENTION_MESSAGE = "[AEB]: Emergency Brake"


def _stamp_ns(stamp: Any) -> int:
    """Convert a ROS Header/builtin stamp to integer nanoseconds (0 if unset)."""
    sec = int(getattr(stamp, "sec", 0) or 0)
    nanosec = int(getattr(stamp, "nanosec", 0) or 0)
    if sec <= 0 or not 0 <= nanosec < 1_000_000_000:
        return 0
    return sec * 1_000_000_000 + nanosec


def _stamp_ns_from_int(msg: Any) -> int:
    value = int(getattr(msg, "data", 0) or 0) if hasattr(msg, "data") else 0
    stamp = getattr(msg, "stamp", None)
    ns = _stamp_ns(stamp) if stamp is not None else 0
    return ns if ns > 0 else 0


class SourceAdapter:
    """ROS-agnostic subscription handlers; one method per pinned source topic.

    The ROS node class calls these with decoded messages; unit tests call
    them directly with simple stand-ins. No ROS import is required.
    """

    def __init__(self, assembler: FrameAssembler, now_ns) -> None:  # noqa: ANN001 - callable
        self._assembler = assembler
        self._now_ns = now_ns
        self._last_cloud_projection: tuple[float, float] | None = None

    # -- native AEB ---------------------------------------------------------

    def on_rss_distance(self, msg: Any) -> None:
        stamp_ns = _stamp_ns(getattr(msg, "stamp", None))
        if stamp_ns <= 0:
            return
        self._assembler.observe_rss_distance(
            SourceObservation(TOPIC_RSS, {"source_timestamp_ns": stamp_ns}, self._now_ns()),
            getattr(msg, "data", float("nan")),
        )

    def on_obstacle_pointcloud(self, msg: Any) -> None:
        stamp_ns = _stamp_ns(getattr(msg, "header", None) and msg.header.stamp)
        if stamp_ns <= 0:
            return
        projection = project_closest_point_range_bearing(msg)
        if projection is None:
            return
        range_m, bearing_rad = projection
        self._assembler.observe_obstacle_projection(
            SourceObservation(TOPIC_CLOUD, {"source_timestamp_ns": stamp_ns}, self._now_ns()),
            range_m, bearing_rad,
        )

    def on_diagnostics(self, msg: Any) -> None:
        stamp_ns = _stamp_ns(getattr(msg, "header", None) and msg.header.stamp)
        if stamp_ns <= 0:
            return
        for status in getattr(msg, "status", []):
            if getattr(status, "name", "") != DIAGNOSTIC_NAME:
                continue
            self._assembler.observe_native_intervention(
                SourceObservation(TOPIC_DIAGNOSTICS, {"source_timestamp_ns": stamp_ns}, self._now_ns()),
                status.name, status.level_name if hasattr(status, "level_name") else _level_name(status.level),
                getattr(status, "message", ""),
            )

    # -- DE4SDV coordinator -------------------------------------------------

    def on_warning_request(self, msg: Any) -> None:
        stamp_ns = _stamp_ns(getattr(msg, "stamp", None))
        if stamp_ns <= 0:
            return
        self._assembler.observe_warning_request(
            SourceObservation(TOPIC_WARNING, {"source_timestamp_ns": stamp_ns}, self._now_ns()),
            bool(getattr(msg, "data", False)),
        )

    def on_emergency_braking_request(self, msg: Any) -> None:
        stamp_ns = _stamp_ns(getattr(msg, "stamp", None))
        if stamp_ns <= 0:
            return
        longitudinal = getattr(getattr(msg, "longitudinal", None), "acceleration", None)
        active = longitudinal is not None and float(longitudinal) < 0.0
        self._assembler.observe_braking_request(
            SourceObservation(TOPIC_BRAKING, {"source_timestamp_ns": stamp_ns}, self._now_ns()),
            active,
        )

    def on_coordination_state(self, msg: Any) -> None:
        stamp_ns = _stamp_ns(getattr(msg, "stamp", None))
        if stamp_ns <= 0:
            return
        self._assembler.observe_lifecycle_state(
            SourceObservation(TOPIC_LIFECYCLE, {"source_timestamp_ns": stamp_ns}, self._now_ns()),
            str(getattr(msg, "data", "")),
        )


def _level_name(level: int) -> str:
    # diagnostic_msgs/msg/DiagnosticStatus levels.
    return {0: "OK", 1: "WARN", 2: "ERROR", 3: "STALE"}.get(level, "UNKNOWN")


def project_closest_point_range_bearing(msg: Any) -> tuple[float, float] | None:
    """Project the closest point of a sensor_msgs/PointCloud2 to (range, bearing).

    Pure geometry over the raw point-step layout, mirroring the 009B
    coordinator's x-field extraction. Returns None when no finite positive
    point exists.
    """
    fields = getattr(msg, "fields", None) or []
    x_field = next((f for f in fields if getattr(f, "name", "") == "x"), None)
    y_field = next((f for f in fields if getattr(f, "name", "") == "y"), None)
    point_step = int(getattr(msg, "point_step", 0) or 0)
    if x_field is None or y_field is None or point_step <= 0:
        return None
    import math
    import struct

    endian = ">" if getattr(msg, "is_bigendian", False) else "<"
    raw = bytes(getattr(msg, "data", b"") or b"")
    best: tuple[float, float] | None = None
    for offset in range(0, len(raw) - point_step + 1, point_step):
        try:
            x = struct.unpack_from(endian + "f", raw, offset + x_field.offset)[0]
            y = struct.unpack_from(endian + "f", raw, offset + y_field.offset)[0]
        except struct.error:
            break
        if math.isfinite(x) and math.isfinite(y) and x > 0.0:
            range_m = math.hypot(x, y)
            if best is None or range_m < best[0]:
                best = (range_m, math.atan2(y, x))
    return best


class FrameServer:
    """Length-delimited frame stream server (one client at a time).

    The AAOS ingress initiates the outbound connection to this server; bytes
    flow ROS/Autoware -> AAOS only. The server never reads commands.
    """

    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port
        self._lock = threading.Lock()
        self._client: socket.socket | None = None

    def serve_once(self) -> socket.socket:
        """Accept exactly one client connection and return it."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self._host, self._port))
        server.listen(1)
        try:
            client, _addr = server.accept()
        finally:
            server.close()
        with self._lock:
            self._client = client
        return client

    def send_frame(self, frame_bytes: bytes) -> int:
        """Send one length-delimited frame; returns bytes written."""
        if len(frame_bytes) > 1_048_576:
            raise ValueError("frame exceeds the 1 MiB transport bound")
        with self._lock:
            client = self._client
        if client is None:
            raise ConnectionError("no client connected")
        payload = struct.pack("<I", len(frame_bytes)) + frame_bytes
        return client.sendall(payload) and len(payload) or len(payload)

    def close(self) -> None:
        with self._lock:
            client = self._client
            self._client = None
        if client is not None:
            try:
                client.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            client.close()


def encode_frame_json(frame: dict) -> bytes:
    """Encode a frame as compact JSON bytes (development encoding).

    The protobuf contract (interface/aebs_visualization.proto) is the
    production wire schema; JSON is accepted only for deterministic local
    testing and is never used as AAOS evidence.
    """
    return json.dumps(frame, sort_keys=True, separators=(",", ":")).encode("utf-8")
