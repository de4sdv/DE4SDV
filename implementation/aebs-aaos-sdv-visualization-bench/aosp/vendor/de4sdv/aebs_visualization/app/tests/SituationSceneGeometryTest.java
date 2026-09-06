package org.de4sdv.aebsvisualization;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import org.junit.Test;
import org.junit.runner.RunWith;
import org.junit.runners.JUnit4;

/**
 * Behavioral scene-geometry tests for the forward-situation view
 * (VISUALIZATION-CONTRACT.md §13.1/§13.3).
 *
 * These assert projected bounds and containment numerically at the campaign
 * reference viewport (1080×600) — they do not inspect source strings. They
 * pin: one isotropic metre-per-pixel factor, fixture-true ego front/rear/
 * width bounds (no presentation multiplier), EGO label clearance with actual
 * glyph ascent, and no false visual contact between the obstacle glow and
 * the ego footprint at the fixture's minimum separation.
 */
@RunWith(JUnit4.class)
public class SituationSceneGeometryTest {

    private static final float EPS = 1e-3f;
    private static final int VIEW_W = 1080;
    private static final int VIEW_H = 600;

    /** Fixture minimum footprint separation from PR #164 evidence (metres). */
    private static final float MIN_FOOTPRINT_SEPARATION_M = 3.59f;

    /** Cluster point glow radius in px (§13.2; ForwardSituationView). */
    private static final float POINT_GLOW_PX = 6f;

    private static SituationSceneGeometry geometry() {
        return new SituationSceneGeometry(VIEW_W, VIEW_H);
    }

    // ------------------------------------------------------------------
    // One scene scale: isotropic projection (§13.1)
    // ------------------------------------------------------------------

    @Test
    public void projectionIsIsotropicAcrossAxes() {
        SituationSceneGeometry g = geometry();
        float forwardPxPerM = g.originY() - g.forwardToY(1f);
        float lateralPxPerM = g.lateralToX(1f) - g.lateralToX(0f);
        assertEquals("one metre must span the same pixels on both axes",
                forwardPxPerM, lateralPxPerM, EPS);
        // The shared factor really is metres-per-pixel.
        assertEquals(1f, g.metresPerPx() * forwardPxPerM, EPS);
    }

    @Test
    public void rangeTickScaleMatchesObstacleProjection() {
        // A point at 30 m and the 30 m range tick must land on the same y.
        SituationSceneGeometry g = geometry();
        assertEquals(g.forwardToY(30f),
                g.forwardToY(SituationSceneGeometry.MAX_RANGE_M / 2f), EPS);
    }

    // ------------------------------------------------------------------
    // Fixture-true ego footprint bounds (§13.1, no presentation multiplier)
    // ------------------------------------------------------------------

    @Test
    public void egoFrontBoundIsFixtureTrue() {
        SituationSceneGeometry g = geometry();
        float[] r = g.egoFootprintRectPx();
        assertEquals(g.originY() - SituationRenderModel.EGO_FRONT_M / g.metresPerPx(),
                r[1], EPS);
    }

    @Test
    public void egoRearBoundIsFullFixtureRear() {
        SituationSceneGeometry g = geometry();
        float[] r = g.egoFootprintRectPx();
        // The bottom bound is the FULL fixture rear, unshortened by any
        // presentation factor (defect: bottom = originY + rear * 0.4).
        assertEquals(g.originY() + SituationRenderModel.EGO_REAR_M / g.metresPerPx(),
                r[3], EPS);
    }

    @Test
    public void egoWidthBoundsAreFixtureTrueAndSymmetric() {
        SituationSceneGeometry g = geometry();
        float[] r = g.egoFootprintRectPx();
        float halfW = SituationRenderModel.EGO_WIDTH_M / g.metresPerPx() / 2f;
        assertEquals(g.originX() - halfW, r[0], EPS);
        assertEquals(g.originX() + halfW, r[2], EPS);
        assertEquals("projected width equals fixture width in metres",
                SituationRenderModel.EGO_WIDTH_M, (r[2] - r[0]) * g.metresPerPx(), EPS);
    }

    @Test
    public void egoFootprintStaysInsideTheDisplayBand() {
        SituationSceneGeometry g = geometry();
        float[] r = g.egoFootprintRectPx();
        assertTrue("front edge must stay below the display top", r[1] > 0f);
        assertTrue("rear edge must stay above the display bottom", r[3] < VIEW_H);
    }

    // ------------------------------------------------------------------
    // Decoration containment (§13.1 halo rule)
    // ------------------------------------------------------------------

    @Test
    public void minimumFootprintSeparationExceedsGlowReachAtReferenceViewport() {
        // At the fixture's closest approach the obstacle point's glow must
        // not reach the ego front bumper in projected scene metres: smaller
        // circle constants alone do not establish this; the projection does.
        SituationSceneGeometry g = geometry();
        float glowReachM = POINT_GLOW_PX * g.metresPerPx();
        float glowLeadingEdgeM =
                SituationRenderModel.EGO_FRONT_M + MIN_FOOTPRINT_SEPARATION_M - glowReachM;
        assertTrue("glow edge must stay ahead of the ego front bumper",
                glowLeadingEdgeM > SituationRenderModel.EGO_FRONT_M);
    }

    // ------------------------------------------------------------------
    // EGO label clearance with actual glyph ascent (§13.3)
    // ------------------------------------------------------------------

    @Test
    public void egoLabelClearanceHoldsWithActualGlyphAscent() {
        SituationSceneGeometry g = geometry();
        float[] r = g.egoFootprintRectPx();
        // The view passes the real ascent from the label paint's font bounds;
        // a Roboto-like conservative ascent is used here as the actual bound.
        float glyphAscentPx = 0.95f * 17f;
        float baseline = g.egoLabelBaselinePx(r[3], glyphAscentPx);
        assertEquals("glyph top must sit exactly one clearance below the boundary",
                r[3] + SituationSceneGeometry.EGO_LABEL_CLEARANCE_PX,
                baseline - glyphAscentPx, EPS);
        assertTrue("label baseline must stay on screen at 1080x600", baseline < VIEW_H);
    }
}
