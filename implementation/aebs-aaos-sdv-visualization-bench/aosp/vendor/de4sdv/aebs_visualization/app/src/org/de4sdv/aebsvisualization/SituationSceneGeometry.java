package org.de4sdv.aebsvisualization;

/**
 * Scene geometry for the DE4SDV AEBS forward-situation view.
 *
 * Pure-Java, Android-free scene math extracted from ForwardSituationView so
 * projection bounds and placement rules are unit-testable on the JVM
 * (SituationSceneGeometryTest), exactly like the pure render model. ONE
 * isotropic metre-per-pixel factor governs ego footprint, filtered obstacle
 * points, and range ticks alike, so unequal scaling can never introduce a
 * visual overlap that the metric geometry does not contain
 * (VISUALIZATION-CONTRACT.md §13.1).
 *
 * Scene layout (1080×600 reference): ego REAR bumper sits at originY; the
 * 0..MAX_RANGE_M band occupies the usable height above it; x is centered.
 */
public final class SituationSceneGeometry {

    /** Display scale bound in metres (display-only, not a data bound). */
    public static final float MAX_RANGE_M = SituationRenderModel.MAX_RANGE_M;

    /** Minimum pixel gap between the EGO glyphs and the silhouette boundary. */
    public static final float EGO_LABEL_CLEARANCE_PX = 5f;

    private final float originX;
    private final float originY;
    private final float usableHeightPx;
    private final float metresPerPx;

    public SituationSceneGeometry(int widthPx, int heightPx) {
        this.originX = widthPx / 2f;
        this.originY = heightPx * 0.90f;          // ego rear bumper
        this.usableHeightPx = heightPx * 0.74f;   // 0..60 m band above origin
        this.metresPerPx = MAX_RANGE_M / usableHeightPx;
    }

    /** Ego rear-bumper origin (screen px). */
    public float originX() {
        return originX;
    }

    public float originY() {
        return originY;
    }

    /** The one isotropic metres-per-pixel factor for the whole scene. */
    public float metresPerPx() {
        return metresPerPx;
    }

    /** Forward metres above the ego rear bumper to screen y. */
    public float forwardToY(float metresForward) {
        return originY - (metresForward / MAX_RANGE_M) * usableHeightPx;
    }

    /** Lateral metres (positive = left of the forward axis) to screen x. */
    public float lateralToX(float metresLateral) {
        return originX + metresLateral / metresPerPx;
    }

    /**
     * Ego footprint rect in screen px: {left, top, right, bottom}, from the
     * TRUE fixture dimensions via the shared isotropic factor. The renderer
     * draws this rect unmodified — no presentation multiplier. Both
     * longitudinal bounds are fixture-true: the rear bumper sits at
     * EGO_REAR_M behind the origin, unshortened.
     */
    public float[] egoFootprintRectPx() {
        final float carFront = SituationRenderModel.EGO_FRONT_M / metresPerPx;
        final float carRear = SituationRenderModel.EGO_REAR_M / metresPerPx;
        final float carWpx = SituationRenderModel.EGO_WIDTH_M / metresPerPx;
        return new float[]{
                originX - carWpx / 2f,
                originY - carFront,
                originX + carWpx / 2f,
                originY + carRear,
        };
    }

    /**
     * EGO label baseline below the silhouette bottom edge: glyph top sits
     * exactly EGO_LABEL_CLEARANCE_PX below the boundary. Callers pass the
     * actual glyph ascent from the label paint's font bounds (positive px).
     */
    public float egoLabelBaselinePx(float rectBottomPx, float glyphAscentPx) {
        return rectBottomPx + EGO_LABEL_CLEARANCE_PX + glyphAscentPx;
    }
}
