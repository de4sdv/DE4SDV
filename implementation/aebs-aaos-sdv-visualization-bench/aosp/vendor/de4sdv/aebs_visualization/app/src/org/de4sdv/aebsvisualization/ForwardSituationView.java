package org.de4sdv.aebsvisualization;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.util.AttributeSet;
import android.view.View;

/**
 * DE4SDV AEBS forward-situation view (display-derived presentation only).
 *
 * Renders a bounded top-down forward scene from the pure render model:
 * ego origin at bottom center, subdued distance ticks every 10 m up to
 * 60 m, the closest obstacle point from target_range/target_bearing
 * (native filtered obstacle cloud projected by the bridge), a labeled
 * horizontal RSS-distance boundary from the native AEB metric, and a
 * short trail of real historical target positions. No circles, sweep, or
 * expanding pulse: liveness lives in the separate health chip, never in
 * scene geometry. No data, no marker: absent target fields render an
 * empty scene, never a synthetic one. Fails closed: the view draws only
 * what the last validated frame contained (REQ-AEBS-S2-005/006).
 */
public class ForwardSituationView extends View {

    private final Paint groundPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint tickPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint tickLabelPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint egoPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint targetPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint trailPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint rssPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint rssLabelPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint targetLabelPaint = new Paint(Paint.ANTI_ALIAS_FLAG);

    /** Latest visual specification from the pure render model. */
    private SituationRenderModel model;

    /** Small ring buffer of recent target positions for the trail. */
    private static final int TRAIL_MAX = 12;
    private final float[] trailFx = new float[TRAIL_MAX];
    private final float[] trailLx = new float[TRAIL_MAX];
    private int trailCount;
    private int trailHead;

    public ForwardSituationView(Context context) {
        super(context);
        init();
    }

    public ForwardSituationView(Context context, AttributeSet attrs) {
        super(context, attrs);
        init();
    }

    public ForwardSituationView(Context context, AttributeSet attrs, int defStyleAttr) {
        super(context, attrs, defStyleAttr);
        init();
    }

    private void init() {
        groundPaint.setStyle(Paint.Style.FILL);
        groundPaint.setColor(Color.rgb(10, 14, 12));

        tickPaint.setStyle(Paint.Style.STROKE);
        tickPaint.setStrokeWidth(1.5f);
        tickPaint.setColor(Color.rgb(40, 70, 55));

        tickLabelPaint.setColor(Color.rgb(90, 140, 110));
        tickLabelPaint.setTextSize(22f);

        egoPaint.setStyle(Paint.Style.FILL);
        egoPaint.setColor(Color.rgb(120, 200, 255));

        targetPaint.setStyle(Paint.Style.FILL);
        targetPaint.setColor(Color.rgb(255, 190, 60));

        trailPaint.setStyle(Paint.Style.FILL);
        trailPaint.setColor(Color.argb(70, 255, 190, 60));

        rssPaint.setStyle(Paint.Style.STROKE);
        rssPaint.setStrokeWidth(6f);
        rssPaint.setColor(Color.rgb(120, 200, 255));

        rssLabelPaint.setColor(Color.rgb(140, 200, 255));
        rssLabelPaint.setTextSize(24f);

        targetLabelPaint.setColor(Color.rgb(255, 200, 90));
        targetLabelPaint.setTextSize(24f);
    }

    /**
     * Updates the rendered scene from the pure render model. Called on the
     * UI thread; the model carries the fail-closed clearing decisions.
     */
    public void render(SituationRenderModel model) {
        this.model = model;
        if (model.isTrailVisible()) {
            pushTrail(model.getTargetForwardNormalized(), model.getTargetLateralNormalized());
        } else if (model.isDegradedState()) {
            clearTrail();
        }
        invalidate();
    }

    /** Clears live geometry (degraded dispositions): empty scene, no marker. */
    public void clearTrail() {
        trailCount = 0;
        trailHead = 0;
    }

    private void pushTrail(float forward, float lateral) {
        trailFx[trailHead] = forward;
        trailLx[trailHead] = lateral;
        trailHead = (trailHead + 1) % TRAIL_MAX;
        if (trailCount < TRAIL_MAX) {
            trailCount++;
        }
    }

    /** Returns {originX, originY, usableHeight, usableHalfWidth}. */
    private float[] sceneGeometry() {
        final float w = getWidth();
        final float h = getHeight();
        final float originX = w / 2f;
        final float originY = h * 0.92f;
        final float usableHeight = h * 0.80f;
        final float usableHalfWidth = w * 0.42f;
        return new float[]{originX, originY, usableHeight, usableHalfWidth};
    }

    private float forwardToY(float[] g, float normalizedForward) {
        return g[1] - normalizedForward * g[2];
    }

    private float lateralToX(float[] g, float normalizedLateral) {
        return g[0] + normalizedLateral * g[3];
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        final float w = getWidth();
        final float h = getHeight();
        final float[] g = sceneGeometry();
        final float originX = g[0];
        final float originY = g[1];

        canvas.drawRect(0, 0, w, h, groundPaint);

        // Subdued distance ticks every 10 m up to the 60 m display bound.
        for (int m = 10; m <= (int) SituationRenderModel.MAX_RANGE_M; m += 10) {
            final float y = forwardToY(g, m / SituationRenderModel.MAX_RANGE_M);
            canvas.drawLine(originX - 14f, y, originX + 14f, y, tickPaint);
            canvas.drawText(m + " m", originX + 20f, y + 7f, tickLabelPaint);
        }

        if (model == null) {
            drawEgo(canvas, originX, originY);
            return;
        }

        // RSS boundary: one labeled horizontal line on the shared scale.
        if (model.isRssBoundaryVisible()) {
            final float rssY = forwardToY(g, model.getRssForwardNormalized());
            rssPaint.setColor(model.getStateColorRgb());
            canvas.drawLine(24f, rssY, w - 24f, rssY, rssPaint);
            canvas.drawText("RSS " + model.getRssDistanceText(),
                    28f, rssY - 10f, rssLabelPaint);
        }

        // Trail: real historical target positions, oldest first.
        for (int i = 0; i < trailCount; i++) {
            final int idx = (trailHead - 1 - i + TRAIL_MAX * 2) % TRAIL_MAX;
            final float alpha = 70f * (1f - (float) i / TRAIL_MAX);
            trailPaint.setAlpha((int) alpha);
            canvas.drawCircle(
                    lateralToX(g, trailLx[idx]),
                    forwardToY(g, trailFx[idx]),
                    6f, trailPaint);
        }

        // Current closest obstacle point (only from real frame fields).
        if (model.isTargetVisible()) {
            final float tx = lateralToX(g, model.getTargetLateralNormalized());
            final float ty = forwardToY(g, model.getTargetForwardNormalized());
            canvas.drawCircle(tx, ty, 14f, targetPaint);
            canvas.drawText("Closest obstacle point " + model.getTargetRangeText(),
                    Math.min(tx + 20f, w - 380f), Math.max(ty - 18f, 30f),
                    targetLabelPaint);
        }

        // Ego/reference origin at the bottom center.
        drawEgo(canvas, originX, originY);
    }

    private void drawEgo(Canvas canvas, float originX, float originY) {
        canvas.drawCircle(originX, originY, 9f, egoPaint);
        canvas.drawText("ego", originX + 16f, originY + 7f, tickLabelPaint);
    }
}
