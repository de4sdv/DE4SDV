package org.de4sdv.aebsvisualization;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.util.AttributeSet;
import android.view.View;

/**
 * DE4SDV AEBS 010 situation radar (display-derived presentation only).
 *
 * Renders the situation derived from the live VisualizationFrame fields:
 * target blip from target_range/target_bearing (native obstacle cloud,
 * projected by the bridge), safety-envelope arc from rss_distance (native
 * AEB stopping-distance metric), ego marker at bottom center. The rotating
 * sweep is a presentation animation with no data meaning and is labeled as
 * such in the provenance footer. No data, no blip: absent target fields
 * render an empty scope, never a synthetic target. Fails closed: the view
 * draws only what the last validated frame contained (REQ-AEBS-S2-005/006).
 */
public class SituationRadarView extends View {

    /** Max rendered range in meters (display scale bound, not a data bound). */
    private static final float MAX_RANGE_M = 60.0f;

    private final Paint scopePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint ringPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint sweepPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint egoPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint targetPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint trailPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint envelopePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint readoutPaint = new Paint(Paint.ANTI_ALIAS_FLAG);

    /** Latest validated frame snapshot; null until the first frame arrives. */
    private Float targetRangeM;
    private Float targetBearingRad;
    private Float rssDistanceM;
    private boolean interventionActive;
    private long sweepStartMs;

    /** Small ring buffer of recent target positions for the motion trail. */
    private static final int TRAIL_MAX = 24;
    private final float[] trailX = new float[TRAIL_MAX];
    private final float[] trailY = new float[TRAIL_MAX];
    private int trailCount;
    private int trailHead;

    public SituationRadarView(Context context) {
        super(context);
        init();
    }

    public SituationRadarView(Context context, AttributeSet attrs) {
        super(context, attrs);
        init();
    }

    public SituationRadarView(Context context, AttributeSet attrs, int defStyleAttr) {
        super(context, attrs, defStyleAttr);
        init();
    }

    private void init() {
        scopePaint.setStyle(Paint.Style.FILL);
        scopePaint.setColor(Color.rgb(8, 14, 12));

        ringPaint.setStyle(Paint.Style.STROKE);
        ringPaint.setStrokeWidth(2f);
        ringPaint.setColor(Color.rgb(0, 160, 90));

        sweepPaint.setStyle(Paint.Style.STROKE);
        sweepPaint.setStrokeWidth(4f);
        sweepPaint.setColor(Color.argb(140, 0, 220, 130));

        egoPaint.setStyle(Paint.Style.FILL);
        egoPaint.setColor(Color.rgb(120, 200, 255));

        targetPaint.setStyle(Paint.Style.FILL);
        targetPaint.setColor(Color.rgb(255, 190, 60));

        trailPaint.setStyle(Paint.Style.FILL);
        trailPaint.setColor(Color.argb(90, 255, 190, 60));

        envelopePaint.setStyle(Paint.Style.STROKE);
        envelopePaint.setStrokeWidth(8f);

        readoutPaint.setColor(Color.rgb(140, 230, 170));
        readoutPaint.setTextSize(30f);
        readoutPaint.setFontFeatureSettings("tnum");
    }

    /**
     * Updates the rendered situation from one validated frame. Called on the
     * UI thread from MainActivity; values may be null (field absent upstream).
     */
    public void onFrame(Float targetRangeM, Float targetBearingRad,
                        Float rssDistanceM, boolean interventionActive) {
        this.targetRangeM = targetRangeM;
        this.targetBearingRad = targetBearingRad;
        this.rssDistanceM = rssDistanceM;
        this.interventionActive = interventionActive;
        if (targetRangeM != null && targetBearingRad != null
                && targetRangeM <= MAX_RANGE_M) {
            pushTrail();
        }
        if (sweepStartMs == 0) {
            sweepStartMs = android.os.SystemClock.elapsedRealtime();
        }
        invalidate();
    }

    /** Clears live data (stale/unavailable/invalid): empty scope, no blip. */
    public void clear() {
        targetRangeM = null;
        targetBearingRad = null;
        rssDistanceM = null;
        interventionActive = false;
        trailCount = 0;
        trailHead = 0;
        invalidate();
    }

    private void pushTrail() {
        // Bearing is CCW-positive from +x (base_link); the scope renders
        // straight up as forward, so screen angle = -bearing.
        final double angle = -targetBearingRad;
        final float frac = Math.min(targetRangeM / MAX_RANGE_M, 1.0f);
        final float[] scope = scopeGeometry();
        trailX[trailHead] = scope[0] + frac * scope[2] * (float) Math.sin(angle);
        trailY[trailHead] = scope[1] - frac * scope[2] * (float) Math.cos(angle);
        trailHead = (trailHead + 1) % TRAIL_MAX;
        if (trailCount < TRAIL_MAX) {
            trailCount++;
        }
    }

    /** Returns {centerX, centerY, radiusPx}. */
    private float[] scopeGeometry() {
        final float w = getWidth();
        final float h = getHeight();
        final float cx = w / 2f;
        final float cy = h * 0.88f;
        final float radius = Math.min(w / 2f - 24f, h * 0.8f);
        return new float[]{cx, cy, radius};
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        final float[] scope = scopeGeometry();
        final float cx = scope[0];
        final float cy = scope[1];
        final float radius = scope[2];

        canvas.drawCircle(cx, cy, radius, scopePaint);
        for (int i = 1; i <= 3; i++) {
            canvas.drawCircle(cx, cy, radius * i / 3f, ringPaint);
        }
        canvas.drawLine(cx, cy, cx, cy - radius, ringPaint);
        canvas.drawLine(cx - radius, cy, cx + radius, cy, ringPaint);

        // Presentation sweep (no data meaning; labeled in the footer).
        final long now = android.os.SystemClock.elapsedRealtime();
        final float sweepAngleDeg = ((now - sweepStartMs) / 12f) % 360f;
        canvas.drawLine(cx, cy,
                cx + radius * (float) Math.cos(Math.toRadians(sweepAngleDeg - 90)),
                cy + radius * (float) Math.sin(Math.toRadians(sweepAngleDeg - 90)),
                sweepPaint);

        // Motion trail (only real historical target positions).
        for (int i = 0; i < trailCount; i++) {
            final int idx = (trailHead - 1 - i + TRAIL_MAX * 2) % TRAIL_MAX;
            final float alpha = 90f * (1f - (float) i / TRAIL_MAX);
            trailPaint.setAlpha((int) alpha);
            canvas.drawCircle(trailX[idx], trailY[idx], 5f, trailPaint);
        }

        // Safety envelope arc from the native RSS stopping distance.
        if (rssDistanceM != null) {
            final float rssFrac = Math.min(rssDistanceM / MAX_RANGE_M, 1.0f);
            final boolean tight = interventionActive || rssDistanceM < 15f;
            envelopePaint.setColor(tight ? Color.rgb(255, 60, 60) : Color.rgb(0, 200, 100));
            canvas.drawCircle(cx, cy, Math.max(rssFrac * radius, 18f), envelopePaint);
        }

        // Target blip (only from real frame fields; never synthesized).
        if (targetRangeM != null && targetBearingRad != null
                && targetRangeM <= MAX_RANGE_M) {
            final double angle = -targetBearingRad;
            final float frac = Math.min(targetRangeM / MAX_RANGE_M, 1.0f);
            final float tx = cx + frac * radius * (float) Math.sin(angle);
            final float ty = cy - frac * radius * (float) Math.cos(angle);
            canvas.drawCircle(tx, ty, 14f, targetPaint);
        }

        // Ego marker at scope origin.
        canvas.drawCircle(cx, cy, 9f, egoPaint);

        // Numeric readout (monospace-ish via tabular figures).
        final StringBuilder sb = new StringBuilder();
        if (targetRangeM != null) {
            sb.append(String.format("RNG %5.1f m ", targetRangeM));
        }
        if (rssDistanceM != null) {
            sb.append(String.format("RSS %5.1f m", rssDistanceM));
        }
        if (sb.length() > 0) {
            canvas.drawText(sb.toString(), 24f, 40f, readoutPaint);
        }
    }
}
