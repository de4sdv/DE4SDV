// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// Numeric pins of the plan panel's projection (no Android): one scale on both
// axes, x forward up, y left left, the grid in metres, the range a pure
// function of the current plan.
package org.de4sdv.drivingstate;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class PlanGeometryTest {

    // The plot box of ScreenLayout at 1080 x 600 (scale 1).
    private static final float L = ScreenLayout.PLAN_PLOT.left;
    private static final float T = ScreenLayout.PLAN_PLOT.top;
    private static final float W = ScreenLayout.PLAN_PLOT.width;
    private static final float H = ScreenLayout.PLAN_PLOT.height;
    private static final float EPS = 1e-3f;

    private static PlanGeometry straight(float lengthM) {
        final float[] x = new float[64];
        final float[] y = new float[64];
        for (int i = 0; i < 64; i++) {
            x[i] = lengthM * (i + 1) / 64f;
        }
        return PlanGeometry.fit(L, T, W, H, x, y);
    }

    @Test
    public void bothAxesUseOneScale() {
        final PlanGeometry g = straight(47f);
        final float forwardPx = g.screenY(0f, 0f) - g.screenY(10f, 0f);   // 10 m ahead: up
        final float lateralPx = g.screenX(0f, 0f) - g.screenX(0f, 10f);   // 10 m left: left
        assertEquals(10f * g.scale, forwardPx, EPS);
        assertEquals(forwardPx, lateralPx, EPS);
    }

    @Test
    public void tenAheadThreeLeftLandsUpAndLeftOfEgo() {
        final PlanGeometry g = straight(47f);   // 47 m * 1.1 = 51.7 -> range 60 m
        assertEquals(60f, g.rangeM, 0f);
        assertEquals(H / (60f * 1.12f), g.scale, EPS);
        final float sx = g.screenX(10f, 3f);
        final float sy = g.screenY(10f, 3f);
        assertEquals(g.originX - 3f * g.scale, sx, EPS);
        assertEquals(g.originY - 10f * g.scale, sy, EPS);
        // Concretely at 1080 x 600: the plot is 540 x 396 px at (12, 82); 60 m + 7.2 m behind
        // ego fill its height, so 5.893 px/m, and ego sits at (282, 478 - 7.2 m * 5.893 px/m).
        assertEquals(5.892857f, g.scale, 1e-5f);
        assertEquals(282f, g.originX, EPS);
        assertEquals(435.57144f, g.originY, 1e-3f);
        assertTrue("left of ego", sx < g.originX);
        assertTrue("above ego", sy < g.originY);
        assertEquals(264.32144f, sx, 1e-3f);   // 282 - 3 m * 5.893
        assertEquals(376.64288f, sy, 1e-3f);   // 435.571 - 10 m * 5.893
    }

    @Test
    public void gridSpacingIsTheSameNumberOfPixelsOnBothAxes() {
        final PlanGeometry g = straight(47f);
        assertEquals(10f, g.gridM, 0f);
        final float[] fwd = g.forwardGridM();
        final float[] lat = g.lateralGridM();
        assertEquals(0f, fwd[1] - fwd[0] - g.gridM, EPS);
        assertEquals(0f, lat[1] - lat[0] - g.gridM, EPS);
        final float fwdPx = g.screenY(fwd[0], 0f) - g.screenY(fwd[1], 0f);
        final float latPx = g.screenX(0f, lat[0]) - g.screenX(0f, lat[1]);
        assertEquals(fwdPx, latPx, EPS);
        assertEquals(10f * g.scale, fwdPx, EPS);
        // 0 m is a grid line on both axes, and the forward lines run from behind ego to the range.
        assertTrue(contains(fwd, 0f));
        assertTrue(contains(lat, 0f));
        assertEquals(60f, fwd[fwd.length - 1], EPS);
        // Half width at range 60 m: 270 px / 5.893 px/m = 45.8 m, so the lateral lines are +-40 m.
        assertEquals(45.818f, g.halfWidthM(), 1e-2f);
        assertArrayEquals(new float[] {-40f, -30f, -20f, -10f, 0f, 10f, 20f, 30f, 40f}, lat, EPS);
    }

    @Test
    public void rangeIsTheSmallestNiceRangeWithHeadroom() {
        assertEquals(10f, straight(0f).rangeM, 0f);
        assertEquals(10f, straight(9f).rangeM, 0f);     // 9.9 <= 10
        assertEquals(20f, straight(9.2f).rangeM, 0f);   // 10.12 > 10
        assertEquals(80f, straight(64f).rangeM, 0f);    // 6.4 s at 10 m/s
        assertEquals(120f, straight(96f).rangeM, 0f);   // 6.4 s at 15 m/s
        assertEquals(5f, PlanGeometry.gridFor(20f), 0f);
        assertEquals(20f, PlanGeometry.gridFor(80f), 0f);
    }

    @Test
    public void aWideTurnEnlargesTheRangeInsteadOfLeavingThePanel() {
        final float[] x = {5f, 10f, 15f};
        final float[] y = {5f, 15f, 30f};   // 30 m left at 15 m ahead
        final PlanGeometry g = PlanGeometry.fit(L, T, W, H, x, y);
        assertTrue(30f * 1.1f <= g.halfWidthM());
        for (int i = 0; i < x.length; i++) {
            assertTrue("point " + i + " inside", g.inside(x[i], y[i]));
        }
        // 15 m ahead alone needs 20 m; 33 m sideways needs the 60 m range (45.8 m half width;
        // 40 m gives 30.5 m).
        assertEquals(60f, g.rangeM, 0f);
    }

    @Test
    public void everyPointOfAPlanIsInsideThePanel() {
        final float[] x = new float[64];
        final float[] y = new float[64];
        for (int i = 0; i < 64; i++) {
            x[i] = 0.9f * (i + 1);
            y[i] = 0.002f * (i + 1) * (i + 1);   // bends left, 8.3 m at the end
        }
        final PlanGeometry g = PlanGeometry.fit(L, T, W, H, x, y);
        for (int i = 0; i < 64; i++) {
            assertTrue("point " + i, g.inside(x[i], y[i]));
        }
        assertFalse(g.inside(Float.NaN, 0f));
    }

    @Test
    public void aPointBehindEgoStillFits() {
        final PlanGeometry g = PlanGeometry.fit(L, T, W, H, new float[] {-3f}, new float[] {0f});
        assertTrue(g.inside(-3f, 0f));
        assertTrue(g.rearM >= 3f);
    }

    @Test
    public void scalesUniformlyWithTheView() {
        final float s = ScreenLayout.scaleFor(1920f, 1080f);
        assertEquals(1.7777778f, s, 1e-5f);
        assertEquals(1f, ScreenLayout.scaleFor(1080f, 600f), 0f);
        final PlanGeometry small = PlanGeometry.fit(L, T, W, H, new float[] {47f}, new float[] {0f});
        final PlanGeometry big = PlanGeometry.fit(s * L, s * T, s * W, s * H, new float[] {47f}, new float[] {0f});
        assertEquals(small.rangeM, big.rangeM, 0f);
        assertEquals(small.scale * s, big.scale, 1e-3f);
    }

    @Test
    public void withoutBarsTheLayoutFillsTheReferenceView() {
        final ScreenLayout.Placement p = ScreenLayout.place(1080f, 600f, 0f, 0f, 0f, 0f);
        assertEquals(1f, p.scale, 0f);
        assertEquals(0f, p.left, 0f);
        assertEquals(0f, p.top, 0f);
    }

    @Test
    public void theLayoutStaysInsideTheSystemBars() {
        // The IVI centre display with its status bar and navigation bar shown.
        final float barTop = 57f;
        final float barBottom = 76f;
        final ScreenLayout.Placement p = ScreenLayout.place(1080f, 600f, 0f, barTop, 0f, barBottom);
        assertEquals((600f - barTop - barBottom) / 600f, p.scale, 1e-6f);
        for (ScreenLayout.Box b : ScreenLayout.ALL) {
            assertTrue(p.top + p.scale * b.top >= barTop);
            assertTrue(p.top + p.scale * b.bottom() <= 600f - barBottom + 1e-3f);
            assertTrue(p.left + p.scale * b.left >= 0f);
            assertTrue(p.left + p.scale * b.right() <= 1080f);
        }
        // centred in the free width, flush with the status bar when the height decides the scale
        assertEquals((1080f - p.scale * 1080f) / 2f, p.left, 1e-3f);
        assertEquals(barTop, p.top, 1e-3f);
    }

    @Test
    public void noFreeAreaDrawsNothing() {
        assertEquals(0f, ScreenLayout.place(1080f, 600f, 0f, 300f, 0f, 300f).scale, 0f);
        assertEquals(0f, ScreenLayout.place(0f, 0f, 0f, 0f, 0f, 0f).scale, 0f);
    }

    private static boolean contains(float[] values, float v) {
        for (float value : values) {
            if (Math.abs(value - v) < EPS) {
                return true;
            }
        }
        return false;
    }
}
