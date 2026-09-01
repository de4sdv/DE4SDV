package org.de4sdv.aebsvisualization;

import androidx.annotation.Nullable;

/**
 * Pure render model for the DE4SDV AEBS forward-situation view (plan Task 3).
 *
 * Converts one accepted frame's facts + the reducer's current disposition
 * into a view-independent visual specification. Java/Android-free of Canvas
 * APIs so all geometry and color rules are unit-testable on the JVM
 * (SituationRenderModelTest).
 *
 * Contract (VISUALIZATION-CONTRACT.md):
 * - State color comes exclusively from the disposition; geometry can never
 *   change it (the removed `rss < 15 m -> red` rule stays dead).
 * - Target: closest obstacle point projected from the filtered obstacle
 *   cloud; clamped at the 60 m display bound; hidden when absent.
 * - RSS boundary: native Autoware metric on the shared range scale; never
 *   triggers or influences state.
 * - Degraded dispositions (stale/invalid/unavailable) clear all live geometry.
 * - Frame age is health text only; it never enters geometry.
 * - The model NEVER outputs a Disposition (enforced by reflection test).
 */
public final class SituationRenderModel {

    /** Display scale bound in metres (display-only, not a data bound). */
    public static final float MAX_RANGE_M = 60.0f;

    /** Stale threshold for the health chip (matches AO-AEBS-010-005 bound). */
    public static final long STALE_HEALTH_MS = 1_000L;

    /** State colors; single authority is the disposition. */
    private static final int COLOR_MONITORING = 0xFF0066CC; // rgb(0,102,204)
    private static final int COLOR_WARNING = 0xFFFFA500;    // rgb(255,165,0)
    private static final int COLOR_INTERVENTION = 0xFFCC0000; // rgb(204,0,0)
    private static final int COLOR_RELEASED = 0xFF009933;   // rgb(0,153,51)
    private static final int COLOR_RESTORED = 0xFF009933;   // transient
    private static final int COLOR_DEGRADED = 0xFF9E9E9E;   // gray

    private final VisualizationStateReducer.Disposition disposition;
    private final boolean targetVisible;
    private final float targetForwardNormalized;
    private final float targetLateralNormalized;
    private final boolean rssBoundaryVisible;
    private final float rssForwardNormalized;
    private final String targetRangeText;
    private final String rssDistanceText;
    private final String frameAgeText;
    private final String healthLabel;
    private final boolean trailVisible;
    private final String egoSpeedText;
    /** Flattened cluster points [f0,l0,f1,l1,...] in display units (0..1 scaled). */
    private final float[] clusterPointsDisplay;
    private final boolean clusterVisible;

    private SituationRenderModel(Builder b) {
        this.disposition = b.disposition;
        boolean degraded = isDegraded(disposition);

        // Fail-closed: degraded dispositions clear live geometry entirely.
        if (degraded) {
            this.targetVisible = false;
            this.targetForwardNormalized = 0f;
            this.targetLateralNormalized = 0f;
            this.rssBoundaryVisible = false;
            this.rssForwardNormalized = 0f;
            this.trailVisible = false;
            this.egoSpeedText = "—";
            this.clusterPointsDisplay = new float[0];
            this.clusterVisible = false;
            this.targetRangeText = "—";
            this.rssDistanceText = "—";
        } else {
            if (b.targetRange != null && b.targetBearing != null) {
                float frac = clamp(b.targetRange / MAX_RANGE_M);
                // Screen-forward fraction (up = forward); lateral from bearing.
                double angleRad = b.targetBearing;
                this.targetVisible = true;
                this.targetForwardNormalized = frac * (float) Math.cos(angleRad);
                this.targetLateralNormalized = frac * (float) Math.sin(angleRad);
            } else {
                this.targetVisible = false;
                this.targetForwardNormalized = 0f;
                this.targetLateralNormalized = 0f;
            }
            if (b.rssDistance != null) {
                this.rssBoundaryVisible = true;
                this.rssForwardNormalized = clamp(b.rssDistance / MAX_RANGE_M);
            } else {
                this.rssBoundaryVisible = false;
                this.rssForwardNormalized = 0f;
            }
            this.trailVisible = targetVisible; // trail only with live target
            this.egoSpeedText = b.egoSpeed != null
                    ? String.format(java.util.Locale.US, "%.0f", b.egoSpeed * 3.6f) : "—";
            if (b.targetPoints != null && b.targetPoints.length >= 2) {
                this.clusterPointsDisplay = new float[b.targetPoints.length];
                for (int i = 0; i + 1 < b.targetPoints.length; i += 2) {
                    this.clusterPointsDisplay[i] = clamp(b.targetPoints[i] / MAX_RANGE_M);
                    this.clusterPointsDisplay[i + 1] =
                            clampAbs(b.targetPoints[i + 1] / (MAX_RANGE_M / 2f));
                }
                this.clusterVisible = true;
            } else {
                this.clusterPointsDisplay = new float[0];
                this.clusterVisible = false;
            }
            this.targetRangeText = b.targetRange != null
                    ? formatMetres(b.targetRange) : "—";
            this.rssDistanceText = b.rssDistance != null
                    ? formatMetres(b.rssDistance) : "—";
        }

        this.frameAgeText = b.frameAgeMs >= 0 ? (b.frameAgeMs + " ms") : "—";
        this.healthLabel = (b.frameAgeMs >= 0 && b.frameAgeMs > STALE_HEALTH_MS)
                ? "STALE" : healthLabelFor(disposition);
    }

    // -- state (single authority: disposition) ------------------------------

    /** State color token; derived ONLY from the disposition. */
    public int getStateColorRgb() {
        switch (disposition) {
            case WARNING: return COLOR_WARNING;
            case INTERVENTION: return COLOR_INTERVENTION;
            case RELEASED: return COLOR_RELEASED;
            case RESTORED: return COLOR_RESTORED;
            case STALE:
            case INVALID:
            case UNAVAILABLE: return COLOR_DEGRADED;
            case MONITORING:
            default: return COLOR_MONITORING;
        }
    }

    /** State label for the progression panel (lowercase display form). */
    public String getStateLabel() {
        return VisualizationStateReducer.label(disposition);
    }

    /** State icon token for the panel (color is never the only cue). */
    public String getStateIconToken() {
        switch (disposition) {
            case WARNING: return "△";
            case INTERVENTION: return "⬢";
            case RELEASED: return "✓";
            case RESTORED: return "↺";
            case STALE: return "‖";
            case INVALID: return "✕";
            case UNAVAILABLE: return "○";
            case MONITORING:
            default: return "◉";
        }
    }

    /** True when the disposition is one of the four AEBS stages. */
    public boolean isOperationalStage() {
        return disposition == VisualizationStateReducer.Disposition.MONITORING
                || disposition == VisualizationStateReducer.Disposition.WARNING
                || disposition == VisualizationStateReducer.Disposition.INTERVENTION
                || disposition == VisualizationStateReducer.Disposition.RELEASED;
    }

    /** True for health overlays that gray the scene. */
    public boolean isDegradedState() {
        return isDegraded(disposition);
    }

    // -- target geometry -----------------------------------------------------

    public boolean isTargetVisible() {
        return targetVisible;
    }

    /** Forward-axis position, 0..1 from origin (clamped at display bound). */
    public float getTargetForwardNormalized() {
        return targetForwardNormalized;
    }

    /** Lateral position, -1..1 (positive = left of forward axis). */
    public float getTargetLateralNormalized() {
        return targetLateralNormalized;
    }

    // -- RSS boundary geometry -------------------------------------------------

    public boolean isRssBoundaryVisible() {
        return rssBoundaryVisible;
    }

    /** Forward-axis position of the boundary, 0..1 (same scale as target). */
    public float getRssForwardNormalized() {
        return rssForwardNormalized;
    }

    public boolean isTrailVisible() {
        return trailVisible;
    }

    /** Cluster projection visible (schema_minor 1 rich scene). */
    public boolean isClusterVisible() {
        return clusterVisible;
    }

    /** Flattened display-space cluster points [f0,l0,f1,l1,...]. */
    public float[] getClusterPointsDisplay() {
        return clusterPointsDisplay;
    }

    /** Ego speed in km/h, display-rounded; "—" when absent. */
    public String getEgoSpeedText() {
        return egoSpeedText;
    }

    // -- metric text ------------------------------------------------------------

    public String getTargetRangeText() {
        return targetRangeText;
    }

    public String getRssDistanceText() {
        return rssDistanceText;
    }

    public String getFrameAgeText() {
        return frameAgeText;
    }

    /** Health chip label: LIVE/STALE/INVALID/UNAVAILABLE/RESTORED. */
    public String getHealthLabel() {
        return healthLabel;
    }

    public int getHealthColorRgb() {
        return "STALE".equals(healthLabel) ? COLOR_DEGRADED : getStateColorRgb();
    }

    // -- helpers -----------------------------------------------------------------

    private static boolean isDegraded(VisualizationStateReducer.Disposition d) {
        return d == VisualizationStateReducer.Disposition.STALE
                || d == VisualizationStateReducer.Disposition.INVALID
                || d == VisualizationStateReducer.Disposition.UNAVAILABLE;
    }

    private static String healthLabelFor(VisualizationStateReducer.Disposition d) {
        switch (d) {
            case STALE: return "STALE";
            case INVALID: return "INVALID";
            case UNAVAILABLE: return "UNAVAILABLE";
            case RESTORED: return "RESTORED";
            default: return "LIVE";
        }
    }

    private static float clamp(float v) {
        return Math.max(0f, Math.min(1f, v));
    }

    private static float clampAbs(float v) {
        return Math.max(-1f, Math.min(1f, v));
    }

    private static String formatMetres(float v) {
        return String.format(java.util.Locale.US, "%.1f m", v);
    }

    /** Builder for one frame snapshot. */
    public static final class Builder {
        private VisualizationStateReducer.Disposition disposition =
                VisualizationStateReducer.Disposition.UNAVAILABLE;
        @Nullable private Float targetRange;
        @Nullable private Float targetBearing;
        @Nullable private Float rssDistance;
        @Nullable private Float egoSpeed;
        /** Bounded cluster projection: pairs of forward/lateral metres. */
        @Nullable private float[] targetPoints;
        private long frameAgeMs = -1;

        public Builder setDisposition(VisualizationStateReducer.Disposition d) {
            this.disposition = d;
            return this;
        }

        public Builder setTarget(@Nullable Float rangeM, @Nullable Float bearingRad) {
            this.targetRange = rangeM;
            this.targetBearing = bearingRad;
            return this;
        }

        public Builder setRssDistance(@Nullable Float rssM) {
            this.rssDistance = rssM;
            return this;
        }

        public Builder setEgoSpeed(@Nullable Float speedMps) {
            this.egoSpeed = speedMps;
            return this;
        }

        public Builder setTargetPoints(@Nullable float[] pointsFlattened) {
            this.targetPoints = pointsFlattened;
            return this;
        }

        public Builder setFrameAgeMs(long ageMs) {
            this.frameAgeMs = ageMs;
            return this;
        }

        public SituationRenderModel build() {
            return new SituationRenderModel(this);
        }
    }
}
