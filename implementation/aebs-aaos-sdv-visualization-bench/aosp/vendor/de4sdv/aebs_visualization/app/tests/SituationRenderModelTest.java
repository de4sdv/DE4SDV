package org.de4sdv.aebsvisualization;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import org.junit.Test;
import org.junit.runner.RunWith;
import org.junit.runners.JUnit4;

/**
 * Pure-JVM tests for the render model (plan Task 3).
 *
 * The render model converts accepted VisualizationFrame facts + reducer
 * disposition into a view-independent visual specification. It must never
 * output a disposition, and geometry must never encode risk decisions.
 * Failure modes required by the plan (§6 Task 3) are each pinned by a test.
 */
@RunWith(JUnit4.class)
public class SituationRenderModelTest {

    private static final float EPS = 1e-4f;

    // ------------------------------------------------------------------
    // State color comes exclusively from disposition (plan rules 1, 2, 3)
    // ------------------------------------------------------------------

    @Test
    public void warningUsesOrangeAndNeverInterventionRed() {
        SituationRenderModel m = model(VisualizationStateReducer.Disposition.WARNING,
                20f, 0f, 18f);
        assertEquals(0xFFA500, m.getStateColorRgb() & 0xFFFFFF); // orange 255,165,0
        assertFalse(isInterventionRed(m.getStateColorRgb()));
    }

    @Test
    public void interventionColorComesOnlyFromDisposition() {
        SituationRenderModel m = model(VisualizationStateReducer.Disposition.INTERVENTION,
                20f, 0f, 18f);
        assertEquals(0xCC0000, m.getStateColorRgb() & 0xFFFFFF); // red 204,0,0
        // Same geometry but monitoring disposition must NOT be red.
        SituationRenderModel monitoring = model(VisualizationStateReducer.Disposition.MONITORING,
                20f, 0f, 18f);
        assertFalse(isInterventionRed(monitoring.getStateColorRgb()));
    }

    @Test
    public void rssBelowFifteenDoesNotChangeStateColor() {
        // The removed renderer rule (rss < 15m -> red) must have no effect.
        SituationRenderModel lowRss = model(VisualizationStateReducer.Disposition.WARNING,
                20f, 0f, 10f);
        SituationRenderModel highRss = model(VisualizationStateReducer.Disposition.WARNING,
                20f, 0f, 40f);
        assertEquals(lowRss.getStateColorRgb(), highRss.getStateColorRgb());
        assertFalse(isInterventionRed(lowRss.getStateColorRgb()));
    }

    // ------------------------------------------------------------------
    // Target projection (rules: bounded top-down geometry)
    // ------------------------------------------------------------------

    @Test
    public void targetProjectionUsesRangeAndBearing() {
        // Range 30 m of 60 m max -> normalized 0.5; bearing 0 -> straight ahead.
        SituationRenderModel m = model(VisualizationStateReducer.Disposition.MONITORING,
                30f, 0f, 15f);
        assertTrue(m.isTargetVisible());
        assertEquals(0.5f, m.getTargetForwardNormalized(), EPS);
        assertEquals(0.0f, m.getTargetLateralNormalized(), EPS);

        // Bearing +90 deg (pi/2) points fully lateral (y-axis on the scope).
        // Forward coordinate is range*cos(theta); lateral is range*sin(theta).
        SituationRenderModel left = model(VisualizationStateReducer.Disposition.MONITORING,
                30f, (float) (Math.PI / 2), 15f);
        assertEquals(0.0f, left.getTargetForwardNormalized(), EPS);
        assertEquals(0.5f, left.getTargetLateralNormalized(), EPS);
    }

    @Test
    public void targetRangeClampsAtDisplayBound() {
        // Range beyond 60 m display bound: clamped to 1.0, not extrapolated.
        SituationRenderModel m = model(VisualizationStateReducer.Disposition.MONITORING,
                90f, 0f, 15f);
        assertTrue(m.isTargetVisible());
        assertEquals(1.0f, m.getTargetForwardNormalized(), EPS);
    }

    @Test
    public void targetBeyondBoundStillClampedNotHidden() {
        // Decision: > MAX_RANGE shows at the scope edge (clamped), consistent
        // with v2 renderer behavior; hidden only when fields absent.
        SituationRenderModel m = model(VisualizationStateReducer.Disposition.MONITORING,
                120f, 0f, 15f);
        assertTrue(m.isTargetVisible());
        assertEquals(1.0f, m.getTargetForwardNormalized(), EPS);
    }

    // ------------------------------------------------------------------
    // Absent fields hide marker + metric (rule 7)
    // ------------------------------------------------------------------

    @Test
    public void absentTargetHidesMarkerAndMetric() {
        SituationRenderModel m = model(VisualizationStateReducer.Disposition.MONITORING,
                null, null, 15f);
        assertFalse(m.isTargetVisible());
        assertEquals("—", m.getTargetRangeText());
    }

    @Test
    public void absentRssHidesBoundaryAndMetric() {
        SituationRenderModel m = model(VisualizationStateReducer.Disposition.MONITORING,
                30f, 0f, null);
        assertFalse(m.isRssBoundaryVisible());
        assertEquals("—", m.getRssDistanceText());
    }

    // ------------------------------------------------------------------
    // Fail-closed: degraded dispositions clear geometry (rule 6)
    // ------------------------------------------------------------------

    @Test
    public void staleClearsTargetAndRssGeometry() {
        assertDegradedClearsGeometry(VisualizationStateReducer.Disposition.STALE);
    }

    @Test
    public void invalidClearsTargetAndRssGeometry() {
        assertDegradedClearsGeometry(VisualizationStateReducer.Disposition.INVALID);
    }

    @Test
    public void unavailableClearsTargetAndRssGeometry() {
        assertDegradedClearsGeometry(VisualizationStateReducer.Disposition.UNAVAILABLE);
    }

    private static void assertDegradedClearsGeometry(VisualizationStateReducer.Disposition d) {
        SituationRenderModel m = model(d, 30f, 0f, 15f);
        assertFalse(m.isTargetVisible());
        assertFalse(m.isRssBoundaryVisible());
        assertTrue(m.isTrailVisible() == false);
        assertEquals("—", m.getTargetRangeText());
        assertEquals("—", m.getRssDistanceText());
    }

    // ------------------------------------------------------------------
    // Frame age drives health label only, is never rendered (rule: liveness
    // separate; review feedback: no age display anywhere)
    // ------------------------------------------------------------------

    @Test
    public void frameAgeDoesNotAppearInAnyRenderedText() {
        SituationRenderModel withAge = model(VisualizationStateReducer.Disposition.MONITORING,
                30f, 0f, 15f, 42);
        SituationRenderModel noAge = model(VisualizationStateReducer.Disposition.MONITORING,
                30f, 0f, 15f, -1);
        // No public String getter exposes an age value:
        for (java.lang.reflect.Method method : SituationRenderModel.class.getMethods()) {
            if (method.getReturnType() == String.class && method.getParameterCount() == 0) {
                try {
                    String value = (String) method.invoke(withAge);
                    assertFalse("age text must not be exposed: " + method.getName(),
                            value != null && value.matches(".*\\d+\\s*ms.*"));
                } catch (IllegalAccessException | java.lang.reflect.InvocationTargetException ignored) {
                    // Non-plain getters (e.g. toString variants) are not render surfaces.
                }
            }
        }
        // Geometry identical regardless of frame age:
        assertEquals(withAge.getTargetForwardNormalized(), noAge.getTargetForwardNormalized(), EPS);
        assertEquals(withAge.getRssForwardNormalized(), noAge.getRssForwardNormalized(), EPS);
    }

    @Test
    public void frameAgeOverTimeoutReportsStaleHealth() {
        SituationRenderModel m = model(VisualizationStateReducer.Disposition.MONITORING,
                30f, 0f, 15f, 1_500);
        assertEquals("STALE", m.getHealthLabel());
    }

    // ------------------------------------------------------------------
    // Render model must NEVER output a disposition (contract rule 5)
    // ------------------------------------------------------------------

    @Test
    public void renderModelNeverOutputsDisposition() {
        // The public API surface exposes only label/color/health tokens.
        // Compile-time proof: no method returns Disposition. Runtime probe:
        for (java.lang.reflect.Method method : SituationRenderModel.class.getMethods()) {
            assertFalse("render model must not return a Disposition",
                    method.getReturnType() == VisualizationStateReducer.Disposition.class);
        }
    }

    // ------------------------------------------------------------------
    // RSS boundary shares the range scale (rule 4)
    // ------------------------------------------------------------------

    @Test
    public void rssBoundarySharesRangeScale() {
        SituationRenderModel m = model(VisualizationStateReducer.Disposition.MONITORING,
                30f, 0f, 15f);
        assertEquals(15f / 60f, m.getRssForwardNormalized(), EPS);
    }

    @Test
    public void rssBoundaryClampsAtDisplayBound() {
        SituationRenderModel m = model(VisualizationStateReducer.Disposition.MONITORING,
                30f, 0f, 90f);
        assertEquals(1.0f, m.getRssForwardNormalized(), EPS);
    }

    // ------------------------------------------------------------------
    // Numeric metric text is exact, stepwise, not interpolated (rule 7)
    // ------------------------------------------------------------------

    @Test
    public void metricTextIsExactValue() {
        SituationRenderModel m = model(VisualizationStateReducer.Disposition.MONITORING,
                13.8f, 0f, 14.58f);
        assertEquals("13.8 m", m.getTargetRangeText());
        assertEquals("14.6 m", m.getRssDistanceText());
    }

    // ------------------------------------------------------------------
    // Fixture-true ego scale (contract §13.1, follow-up to merged #164)
    // ------------------------------------------------------------------

    @Test
    public void egoFootprintMatchesPinnedFixtureDimensions() {
        // The pinned 009B fixture footprint, in metres. If either side of the
        // scene renders the ego larger than this, visual contact with the
        // obstacle cloud becomes possible where the metric geometry has none.
        assertEquals(3.74f, SituationRenderModel.EGO_FRONT_M, EPS);
        assertEquals(1.03f, SituationRenderModel.EGO_REAR_M, EPS);
        assertEquals(1.83f, SituationRenderModel.EGO_WIDTH_M, EPS);
    }

    @Test
    public void egoFootprintIsFarSmallerThanNominalInterventionDistance() {
        // Presentation-scale guard: at the nominal warning/intervention
        // distances the fixture-true ego is tiny relative to the gap to the
        // obstacle. If the renderer multiplied the footprint (as the merged
        // #164 generation did at 2.5x), a ~20 m apparent gap shrinks below
        // the true separation and reads as contact during INTERVENTION.
        float footprintSpanM = SituationRenderModel.EGO_FRONT_M + SituationRenderModel.EGO_REAR_M;
        assertTrue(footprintSpanM < 5.0f);
        // The projected bounds are pinned numerically by
        // SituationSceneGeometryTest at the campaign viewport; here the guard
        // is consistency of the fixture constants themselves.
        assertEquals(3.74f, SituationRenderModel.EGO_FRONT_M, EPS);
        assertEquals(1.03f, SituationRenderModel.EGO_REAR_M, EPS);
    }

    // ------------------------------------------------------------------
    // Helpers
    // ------------------------------------------------------------------

    private static SituationRenderModel model(VisualizationStateReducer.Disposition disposition,
                                              Float targetRange, Float targetBearing,
                                              Float rssDistance) {
        return model(disposition, targetRange, targetBearing, rssDistance, 42);
    }

    private static SituationRenderModel model(VisualizationStateReducer.Disposition disposition,
                                              Float targetRange, Float targetBearing,
                                              Float rssDistance, long frameAgeMs) {
        SituationRenderModel.Builder b = new SituationRenderModel.Builder()
                .setDisposition(disposition)
                .setTarget(targetRange, targetBearing)
                .setRssDistance(rssDistance)
                .setFrameAgeMs(frameAgeMs);
        return b.build();
    }

    private static boolean isInterventionRed(int rgb) {
        int r = (rgb >> 16) & 0xFF;
        int g = (rgb >> 8) & 0xFF;
        int b = rgb & 0xFF;
        return r == 204 && g == 0 && b == 0;
    }
}
