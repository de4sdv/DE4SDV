// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// Numbers the screen derives from ONE plan, Android-free and tested.
//
// Every value here follows from the plan's own fields (ICD section 3, rows
// 17-22) and, for the plan's speed, from one VEHICLE_STATE speed:
//
//  * the sample period dt = plan_horizon_s / sample count (6.4 s / 64 = 0.1 s);
//    sample i stands for t = (i + 1) * dt, as in upstream's rollout
//    (Model/training/losses/control_rollout.py, "semi_implicit_unicycle_v1");
//  * the plan's speed: v(-1) = the given speed, v(i) = max(0, v(i-1) + a(i) * dt),
//    the same semi-implicit step and clamp as that rollout. It is the PLAN's
//    speed seen from that start speed, labelled so on screen; the model's own
//    start speed is not in the message;
//  * the curvature mean over the first second, as the field carries it
//    (positive = left), with no steering word attached: ICD amendment A27
//    records that the checkpoint's first curvature sample leans right while its
//    paths bend left, so a word derived from it would contradict the drawn path;
//  * points of the path exactly as published (the +1 s sample, the last
//    sample) and the path length (sum of the segment lengths from ego).
//
// No interpolation between samples and no smoothing: a value that cannot be
// computed from the fields is NaN, and the screen prints it as missing.
package org.de4sdv.drivingstate;

final class PlanKinematics {

    final int count;
    /** Seconds per sample; NaN when the horizon or the count is unusable. */
    final float dt;

    private final float[] a;
    private final float[] k;
    private final float[] x;
    private final float[] y;

    PlanKinematics(float horizonS, float[] acceleration, float[] curvature, float[] x, float[] y) {
        this.a = acceleration == null ? new float[0] : acceleration;
        this.k = curvature == null ? new float[0] : curvature;
        this.x = x == null ? new float[0] : x;
        this.y = y == null ? new float[0] : y;
        this.count = this.x.length == this.y.length ? this.x.length : 0;
        this.dt = (count > 0 && PlanGeometry.finite(horizonS) && horizonS > 0f)
                ? horizonS / count : Float.NaN;
    }

    /** Index of the sample that stands for time t (seconds), or -1. */
    int indexAt(float tSeconds) {
        if (!PlanGeometry.finite(dt) || count == 0) {
            return -1;
        }
        final int i = Math.round(tSeconds / dt) - 1;
        return (i < 0 || i >= count) ? -1 : i;
    }

    /** True when sample i stands for a whole second (1 s, 2 s, ...). */
    boolean isWholeSecond(int i) {
        if (!PlanGeometry.finite(dt) || i < 0 || i >= count) {
            return false;
        }
        final double t = (i + 1) * (double) dt;
        return t >= 0.999 && Math.abs(t - Math.rint(t)) < 1e-3;
    }

    /** Time of the last sample (the horizon), seconds; NaN if unknown. */
    float horizonS() {
        return PlanGeometry.finite(dt) ? dt * count : Float.NaN;
    }

    /**
     * The plan's speed profile from a start speed (m/s): one value per sample,
     * or an empty array when the acceleration array or dt is unusable.
     */
    float[] speedProfile(float startSpeedMps) {
        if (!PlanGeometry.finite(dt) || !PlanGeometry.finite(startSpeedMps) || a.length != count
                || count == 0) {
            return new float[0];
        }
        final float[] v = new float[count];
        float speed = startSpeedMps;
        for (int i = 0; i < count; i++) {
            if (!PlanGeometry.finite(a[i])) {
                return new float[0];
            }
            speed = Math.max(0f, speed + a[i] * dt);
            v[i] = speed;
        }
        return v;
    }

    /** The plan's speed at t (seconds) from a start speed; NaN if not computable. */
    float speedAt(float startSpeedMps, float tSeconds) {
        final float[] v = speedProfile(startSpeedMps);
        final int i = indexAt(tSeconds);
        return (v.length == 0 || i < 0) ? Float.NaN : v[i];
    }

    /** Mean of the curvature samples covering (0, t], 1/m; NaN if not computable. */
    float meanCurvature(float tSeconds) {
        final int last = indexAt(tSeconds);
        if (last < 0 || k.length != count) {
            return Float.NaN;
        }
        double sum = 0.0;
        for (int i = 0; i <= last; i++) {
            if (!PlanGeometry.finite(k[i])) {
                return Float.NaN;
            }
            sum += k[i];
        }
        return (float) (sum / (last + 1));
    }

    /** x of sample i (forward, m) or NaN. */
    float xAt(int i) {
        return (i < 0 || i >= count) ? Float.NaN : x[i];
    }

    /** y of sample i (left, m) or NaN. */
    float yAt(int i) {
        return (i < 0 || i >= count) ? Float.NaN : y[i];
    }

    /** Length of the path from ego through every sample, metres; NaN if a point is not finite. */
    float pathLengthM() {
        if (count == 0) {
            return Float.NaN;
        }
        double length = 0.0;
        float px = 0f;
        float py = 0f;
        for (int i = 0; i < count; i++) {
            if (!PlanGeometry.finite(x[i]) || !PlanGeometry.finite(y[i])) {
                return Float.NaN;
            }
            length += Math.hypot(x[i] - px, y[i] - py);
            px = x[i];
            py = y[i];
        }
        return (float) length;
    }
}
