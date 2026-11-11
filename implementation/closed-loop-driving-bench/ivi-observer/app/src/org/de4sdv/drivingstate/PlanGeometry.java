// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// The plan panel's geometry, Android-free so the JVM tests can pin it.
//
// Frame: the plan's own vehicle frame as ICD section 3 states it (rows 21-22):
// x forward, y left, metres, ego at the origin at the plan's capture time.
// Screen: x forward points UP, y left points LEFT, so the picture reads like a
// map seen from above with the car driving up the screen. One scale for both
// axes (isotropic), never stretched to fill the panel.
//
// The visible range is a pure function of the current plan: the smallest
// "nice" forward range that holds every point with 10 % headroom, enlarged
// further when a point would leave the panel sideways. No smoothing, no memory
// of the previous plan: when the range changes, it changes in one step, and the
// grid labels say so.
package org.de4sdv.drivingstate;

final class PlanGeometry {

    /** Forward ranges the panel may show, metres. */
    static final float[] RANGES_M = {10f, 20f, 30f, 40f, 60f, 80f, 100f, 120f, 160f, 200f};
    /** Part of the forward range drawn behind ego, so the marker is not on the edge. */
    static final float REAR_FRACTION = 0.12f;
    /** Headroom on the largest forward extent. */
    static final float HEADROOM = 1.10f;

    final float left;
    final float top;
    final float width;
    final float height;
    /** Forward range shown above ego, metres. */
    final float rangeM;
    /** Metres shown behind ego. */
    final float rearM;
    /** Pixels per metre, the same on both axes. */
    final float scale;
    /** Ego (plan origin) on screen. */
    final float originX;
    final float originY;
    /** Grid spacing, metres, the same on both axes. */
    final float gridM;

    private PlanGeometry(float left, float top, float width, float height, float rangeM) {
        this.left = left;
        this.top = top;
        this.width = width;
        this.height = height;
        this.rangeM = rangeM;
        this.rearM = rangeM * REAR_FRACTION;
        this.scale = height / (rangeM + rearM);
        this.originX = left + width / 2f;
        this.originY = top + height - rearM * scale;
        this.gridM = gridFor(rangeM);
    }

    /**
     * The geometry for a panel and a plan. Non-finite points are ignored for the
     * range (they are not drawn either); an empty plan gets the smallest range.
     */
    static PlanGeometry fit(float left, float top, float width, float height, float[] x, float[] y) {
        float maxForward = 0f;
        float maxLateral = 0f;
        final int n = (x == null || y == null) ? 0 : Math.min(x.length, y.length);
        for (int i = 0; i < n; i++) {
            if (!finite(x[i]) || !finite(y[i])) {
                continue;
            }
            maxForward = Math.max(maxForward, x[i]);
            maxForward = Math.max(maxForward, -x[i] / REAR_FRACTION); // a point behind ego must fit too
            maxLateral = Math.max(maxLateral, Math.abs(y[i]));
        }
        for (float range : RANGES_M) {
            if (range < maxForward * HEADROOM) {
                continue;
            }
            final PlanGeometry g = new PlanGeometry(left, top, width, height, range);
            if (maxLateral * HEADROOM <= g.halfWidthM()) {
                return g;
            }
        }
        return new PlanGeometry(left, top, width, height, RANGES_M[RANGES_M.length - 1]);
    }

    /** Lateral metres visible on each side of ego. */
    float halfWidthM() {
        return (width / 2f) / scale;
    }

    /** Screen x of a vehicle-frame point: y left goes to the screen's left. */
    float screenX(float xForward, float yLeft) {
        return originX - yLeft * scale;
    }

    /** Screen y of a vehicle-frame point: x forward goes up the screen. */
    float screenY(float xForward, float yLeft) {
        return originY - xForward * scale;
    }

    /** True when the point is inside the panel (drawn); false points are clipped. */
    boolean inside(float xForward, float yLeft) {
        if (!finite(xForward) || !finite(yLeft)) {
            return false;
        }
        final float sx = screenX(xForward, yLeft);
        final float sy = screenY(xForward, yLeft);
        return sx >= left && sx <= left + width && sy >= top && sy <= top + height;
    }

    /** Grid lines across the forward axis, metres from ego (0 included). */
    float[] forwardGridM() {
        final int first = (int) Math.ceil(-rearM / gridM);
        final int last = (int) Math.floor(rangeM / gridM);
        final float[] out = new float[Math.max(0, last - first + 1)];
        for (int i = 0; i < out.length; i++) {
            out[i] = (first + i) * gridM;
        }
        return out;
    }

    /** Grid lines across the lateral axis, metres from ego, both sides (0 included). */
    float[] lateralGridM() {
        final int k = (int) Math.floor(halfWidthM() / gridM);
        final float[] out = new float[2 * k + 1];
        for (int i = 0; i < out.length; i++) {
            out[i] = (i - k) * gridM;
        }
        return out;
    }

    static float gridFor(float rangeM) {
        if (rangeM <= 20f) {
            return 5f;
        }
        if (rangeM <= 60f) {
            return 10f;
        }
        if (rangeM <= 120f) {
            return 20f;
        }
        return 40f;
    }

    static boolean finite(float v) {
        return !Float.isNaN(v) && !Float.isInfinite(v);
    }
}
