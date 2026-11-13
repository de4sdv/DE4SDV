"""Checkpoint input history of drivingAgent (conditionInputs side), exactly as the CL harness built it.

The 64-row ego-motion history is computed from the vehicle's REF poses of frames k-65 .. k with the
harness's differences (numpy.gradient at 0.1 s, rows [1:-1], so the newest row is frame k-1):
[speed m/s, longitudinal acceleration m/s^2, yaw rate rad/s, curvature 1/m (the profile's rule)].

REQ-DRIVING-008 as amended (GAP-DRIVING-010): the checkpoint takes the copy whose yaw-rate and
curvature columns are 0; the measured rows stay for the record (C2 logs the copy the checkpoint took,
the measured yaw rate goes to the published ego-motion sample).

Camera history: seven frames 3.5 s .. 0.5 s before the step (k-35, k-30, ..., k-5), oldest first.
"""
from __future__ import annotations

import math

import numpy as np

STEP_S = 0.1
POSE_WINDOW = 66            # frames k-65 .. k
HISTORY_ROWS = 64
CAMERA_HISTORY = 7
CAMERA_HISTORY_STRIDE = 5   # 0.5 s


def camera_history_frames(k: int) -> list[int]:
    return [k - CAMERA_HISTORY_STRIDE * j for j in range(CAMERA_HISTORY, 0, -1)]


def pose_frames(k: int) -> range:
    return range(k - POSE_WINDOW + 1, k + 1)


def egomotion_rows(poses, curvature_rule) -> np.ndarray:
    """poses: the 66 REF poses (4x4, right-handed world) of frames k-65 .. k, oldest first."""
    if len(poses) != POSE_WINDOW:
        raise ValueError("need %d poses, got %d" % (POSE_WINDOW, len(poses)))
    xy = np.array([[T[0, 3], T[1, 3]] for T in poses])
    yaw = np.unwrap(np.array([math.atan2(T[1, 0], T[0, 0]) for T in poses]))
    vel = np.gradient(xy, STEP_S, axis=0)
    speed = np.linalg.norm(vel, axis=1)
    acc = np.gradient(speed, STEP_S)
    yr = np.gradient(yaw, STEP_S)
    return np.stack([speed, acc, yr, curvature_rule(yr, speed)], axis=1)[1:-1].astype(np.float32)


def checkpoint_rows(measured: np.ndarray) -> np.ndarray:
    """The copy the checkpoint takes: yaw rate and curvature given as 0 (REQ-DRIVING-008 as amended)."""
    rows = np.array(measured, dtype=np.float32, copy=True)
    rows[:, 2:] = 0.0
    return rows


class PoseRing:
    """REF poses by frame; frames older than the window are dropped."""

    def __init__(self, keep: int = 80):
        self.keep = keep
        self.pose: dict[int, np.ndarray] = {}

    def add(self, k: int, T: np.ndarray) -> None:
        self.pose[k] = np.asarray(T, dtype=np.float64).reshape(4, 4)
        for old in [j for j in self.pose if j < k - self.keep]:
            del self.pose[old]

    def complete(self, k: int) -> bool:
        return all(j in self.pose for j in pose_frames(k))

    def window(self, k: int) -> list[np.ndarray]:
        return [self.pose[j] for j in pose_frames(k)]
