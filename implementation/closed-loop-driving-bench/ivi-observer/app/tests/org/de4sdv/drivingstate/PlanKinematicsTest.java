// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// Numeric pins of what the screen derives from one plan (no Android).
package org.de4sdv.drivingstate;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class PlanKinematicsTest {

    private static final float EPS = 1e-4f;

    /** A plan built the way upstream's rollout builds it (semi-implicit unicycle, dt 0.1 s). */
    private static PlanKinematics rollout(float v0, float a, float kappa, float[] xOut, float[] yOut) {
        final float[] acc = new float[64];
        final float[] cur = new float[64];
        float speed = v0;
        float heading = 0f;
        float x = 0f;
        float y = 0f;
        for (int i = 0; i < 64; i++) {
            acc[i] = a;
            cur[i] = kappa;
            speed = Math.max(0f, speed + a * 0.1f);
            heading += speed * kappa * 0.1f;
            x += speed * (float) Math.cos(heading) * 0.1f;
            y += speed * (float) Math.sin(heading) * 0.1f;
            xOut[i] = x;
            yOut[i] = y;
        }
        return new PlanKinematics(6.4f, acc, cur, xOut, yOut);
    }

    @Test
    public void samplePeriodIsHorizonOverCount() {
        final PlanKinematics k = rollout(10f, 0f, 0f, new float[64], new float[64]);
        assertEquals(64, k.count);
        assertEquals(0.1f, k.dt, EPS);
        assertEquals(6.4f, k.horizonS(), EPS);
        assertEquals(9, k.indexAt(1f));      // sample i stands for t = (i + 1) dt
        assertEquals(29, k.indexAt(3f));
        assertEquals(63, k.indexAt(6.4f));
        assertEquals(-1, k.indexAt(0f));
        assertEquals(-1, k.indexAt(7f));
        assertTrue(k.isWholeSecond(9));
        assertTrue(k.isWholeSecond(59));
        assertFalse(k.isWholeSecond(10));
        assertFalse(k.isWholeSecond(63));    // 6.4 s
    }

    @Test
    public void planSpeedIntegratesTheAccelerationFromTheGivenSpeed() {
        final PlanKinematics k = rollout(10f, 0.5f, 0f, new float[64], new float[64]);
        assertEquals(10.5f, k.speedAt(10f, 1f), EPS);   // 10 + 0.5 * 1 s
        assertEquals(11.5f, k.speedAt(10f, 3f), EPS);
        assertEquals(13.2f, k.speedAt(10f, 6.4f), 1e-3f);
        // From another start speed the same plan gives another profile: it is the plan's
        // acceleration seen from that speed, as the screen labels it.
        assertEquals(5.5f, k.speedAt(5f, 1f), EPS);
    }

    @Test
    public void planSpeedNeverGoesBelowZeroLikeTheRollout() {
        final PlanKinematics k = rollout(2f, -4f, 0f, new float[64], new float[64]);
        assertEquals(0f, k.speedAt(2f, 1f), 0f);
        assertEquals(0f, k.speedAt(2f, 6.4f), 0f);
        assertEquals(1.2f, k.speedProfile(2f)[1], EPS);
    }

    @Test
    public void theRolloutsPathAndTheIntegratedSpeedAgree() {
        // The step from sample i-1 to i of an upstream rollout is speed(i) * dt long, so a plan's
        // own path confirms the integration when the start speed is the plan's.
        final float[] x = new float[64];
        final float[] y = new float[64];
        final PlanKinematics k = rollout(8f, 0.3f, 0.01f, x, y);
        final float[] v = k.speedProfile(8f);
        for (int i = 1; i < 64; i++) {
            final float step = (float) Math.hypot(x[i] - x[i - 1], y[i] - y[i - 1]);
            assertEquals("sample " + i, v[i] * 0.1f, step, 1e-4f);
        }
    }

    @Test
    public void curvatureMeanCoversTheFirstSecondOnly() {
        final float[] acc = new float[64];
        final float[] cur = new float[64];
        final float[] x = new float[64];
        final float[] y = new float[64];
        for (int i = 0; i < 64; i++) {
            cur[i] = i < 10 ? -0.05f : 0.02f;   // the first second leans right, then left
            x[i] = i + 1;
        }
        final PlanKinematics k = new PlanKinematics(6.4f, acc, cur, x, y);
        assertEquals(-0.05f, k.meanCurvature(1f), EPS);
        assertEquals((10 * -0.05f + 20 * 0.02f) / 30f, k.meanCurvature(3f), EPS);
    }

    @Test
    public void pathLengthStartsAtEgo() {
        final float[] x = {3f, 6f};
        final float[] y = {4f, 8f};
        final PlanKinematics k = new PlanKinematics(0.2f, new float[2], new float[2], x, y);
        assertEquals(10f, k.pathLengthM(), EPS);
        assertEquals(0.1f, k.dt, EPS);
        assertEquals(3f, k.xAt(0), 0f);
        assertTrue(Float.isNaN(k.xAt(2)));
    }

    @Test
    public void missingOrBrokenFieldsGiveNaNNotZero() {
        final PlanKinematics none = new PlanKinematics(6.4f, null, null, null, null);
        assertEquals(0, none.count);
        assertTrue(Float.isNaN(none.dt));
        assertTrue(Float.isNaN(none.speedAt(10f, 1f)));
        assertTrue(Float.isNaN(none.meanCurvature(1f)));
        assertTrue(Float.isNaN(none.pathLengthM()));

        final float[] x = new float[64];
        final PlanKinematics noHorizon = new PlanKinematics(0f, new float[64], new float[64], x, new float[64]);
        assertTrue(Float.isNaN(noHorizon.dt));
        assertTrue(Float.isNaN(noHorizon.speedAt(10f, 1f)));

        final PlanKinematics shortAcc = new PlanKinematics(6.4f, new float[10], new float[64], x, new float[64]);
        assertTrue("acceleration shorter than the path", Float.isNaN(shortAcc.speedAt(10f, 1f)));

        final float[] acc = new float[64];
        acc[3] = Float.NaN;
        final PlanKinematics nanAcc = new PlanKinematics(6.4f, acc, new float[64], x, new float[64]);
        assertTrue(Float.isNaN(nanAcc.speedAt(10f, 1f)));
        assertTrue(Float.isNaN(nanAcc.speedAt(Float.NaN, 1f)));

        final PlanKinematics mismatched = new PlanKinematics(6.4f, new float[64], new float[64], x, new float[63]);
        assertEquals(0, mismatched.count);
    }
}
