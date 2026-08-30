package org.de4sdv.aebsvisualization;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RectF;
import android.util.AttributeSet;
import android.view.View;

/**
 * DE4SDV AEBS forward-situation view (display-derived presentation only).
 *
 * Professional automotive HMI styling (dark base #121212, rounded cards,
 * cyan live accents) applied to the pure render model: car-shaped ego at the
 * bottom (fixture footprint 3.74 m front / 1.03 m rear / 1.83 m width),
 * the filtered obstacle cluster rendered as a bounded point cluster (the
 * fixture target is vehicle-shaped: 4.2 x 1.8 m, so the cluster reads as a
 * vehicle), the labeled RSS boundary, and subdued distance ticks every 10 m
 * up to 60 m. No circles, sweep, pulse, invented lanes, or decorative road:
 * every element is live frame data, labeled fixture geometry, or the static
 * display scale (VISUALIZATION-CONTRACT.md). Fails closed: degraded
 * dispositions clear the scene (REQ-AEBS-S2-005/006).
 */
public class ForwardSituationView extends View {

    /** Display scale bound in metres (display-only, not a data bound). */
    private static final float MAX_RANGE_M = SituationRenderModel.MAX_RANGE_M;

    /** Ego footprint from the pinned scenario fixture (metres). */
    private static final float EGO_FRONT_M = 3.74f;
    private static final float EGO_REAR_M = 1.03f;
    private static final float EGO_WIDTH_M = 1.83f;

    // Design tokens (automotive dark HMI language).
    private static final int COLOR_BASE = Color.rgb(18, 18, 18);
    private static final int COLOR_CARD = Color.rgb(30, 30, 30);
    private static final int COLOR_TICK = Color.rgb(45, 45, 45);
    private static final int COLOR_TICK_LABEL = Color.rgb(85, 85, 85);
    private static final int COLOR_EGO = Color.rgb(229, 229, 229);
    private static final int COLOR_CLUSTER = Color.rgb(0, 229, 255); // cyan live accent
    private static final int COLOR_RSS = Color.rgb(0, 229, 255);
    private static final int COLOR_RSS_LABEL = Color.rgb(176, 176, 176);
    private static final int COLOR_TRAIL = Color.argb(70, 0, 229, 255);

    private final Paint basePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint tickPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint tickLabelPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint cardPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint egoPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint egoOutlinePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint clusterPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint clusterCorePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint trailPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint rssPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint rssLabelPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint bannerPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint bannerTextPaint = new Paint(Paint.ANTI_ALIAS_FLAG);

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
        basePaint.setStyle(Paint.Style.FILL);
        basePaint.setColor(COLOR_BASE);

        tickPaint.setStyle(Paint.Style.STROKE);
        tickPaint.setStrokeWidth(1.5f);
        tickPaint.setColor(COLOR_TICK);

        tickLabelPaint.setColor(COLOR_TICK_LABEL);
        tickLabelPaint.setTextSize(20f);

        cardPaint.setStyle(Paint.Style.FILL);
        cardPaint.setColor(COLOR_CARD);

        egoPaint.setStyle(Paint.Style.FILL);
        egoPaint.setColor(COLOR_EGO);

        egoOutlinePaint.setStyle(Paint.Style.STROKE);
        egoOutlinePaint.setStrokeWidth(2f);
        egoOutlinePaint.setColor(Color.argb(90, 229, 229, 229));

        clusterPaint.setStyle(Paint.Style.FILL);
        clusterPaint.setColor(COLOR_CLUSTER);

        clusterCorePaint.setStyle(Paint.Style.FILL);
        clusterCorePaint.setColor(Color.argb(120, 0, 229, 255));

        trailPaint.setStyle(Paint.Style.FILL);
        trailPaint.setColor(COLOR_TRAIL);

        rssPaint.setStyle(Paint.Style.STROKE);
        rssPaint.setStrokeWidth(5f);
        rssPaint.setColor(COLOR_RSS);

        rssLabelPaint.setColor(COLOR_RSS_LABEL);
        rssLabelPaint.setTextSize(20f);

        bannerPaint.setStyle(Paint.Style.FILL);
        bannerPaint.setColor(Color.argb(200, 30, 30, 30));
        bannerPaint.setStrokeWidth(2f);
        bannerPaint.setAntiAlias(true);

        bannerTextPaint.setColor(Color.WHITE);
        bannerTextPaint.setTextSize(22f);
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

    /** Clears live geometry (degraded dispositions): empty scene. */
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

    /**
     * Scene geometry. Ego REAR bumper sits at originY; the ego car shape is
     * drawn to scale against the same metre-per-pixel factor as the range
     * axis so the cluster, ego, and RSS boundary share one physical scale.
     */
    private float[] sceneGeometry() {
        final float w = getWidth();
        final float h = getHeight();
        final float originX = w / 2f;
        final float originY = h * 0.90f;          // ego rear bumper
        final float usableHeight = h * 0.74f;     // 0..60 m band above origin
        final float usableHalfWidth = w * 0.44f;
        final float metresPerPx = MAX_RANGE_M / usableHeight;
        return new float[]{originX, originY, usableHeight, usableHalfWidth, metresPerPx};
    }

    private float forwardToY(float[] g, float metres) {
        return g[1] - (metres / MAX_RANGE_M) * g[2];
    }

    private float lateralToX(float[] g, float metres) {
        return g[0] + (metres / (MAX_RANGE_M / 2f)) * g[3];
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        final float w = getWidth();
        final float h = getHeight();
        final float[] g = sceneGeometry();

        canvas.drawRect(0, 0, w, h, basePaint);

        // Subdued distance ticks every 10 m up to the display bound.
        for (int m = 10; m <= (int) MAX_RANGE_M; m += 10) {
            final float y = forwardToY(g, m);
            canvas.drawLine(g[0] - 12f, y, g[0] + 12f, y, tickPaint);
            canvas.drawText(m + " m", g[0] + 18f, y + 6f, tickLabelPaint);
        }

        if (model == null) {
            drawEgo(canvas, g);
            return;
        }

        // RSS boundary: one labeled line on the shared scale.
        if (model.isRssBoundaryVisible()) {
            final float rssY = forwardToY(g, model.getRssForwardNormalized() * MAX_RANGE_M);
            rssPaint.setColor(model.getStateColorRgb());
            canvas.drawLine(24f, rssY, w - 24f, rssY, rssPaint);
            canvas.drawText("RSS " + model.getRssDistanceText(), 30f, rssY - 10f, rssLabelPaint);
        }

        // Trail: real historical target positions, oldest first.
        for (int i = 0; i < trailCount; i++) {
            final int idx = (trailHead - 1 - i + TRAIL_MAX * 2) % TRAIL_MAX;
            final float alpha = 70f * (1f - (float) i / TRAIL_MAX);
            trailPaint.setAlpha((int) alpha);
            canvas.drawCircle(
                    lateralToX(g, trailLx[idx] * (MAX_RANGE_M / 2f)),
                    forwardToY(g, trailFx[idx] * MAX_RANGE_M),
                    6f, trailPaint);
        }

        // Filtered obstacle cluster: bounded point projection (schema minor 1).
        // Rendered as glowing cyan points over a soft core so the vehicle-
        // shaped fixture target reads as a car-like silhouette.
        if (model.isClusterVisible()) {
            final float[] pts = model.getClusterPointsDisplay();
            for (int i = 0; i + 1 < pts.length; i += 2) {
                final float px = lateralToX(g, pts[i + 1] * (MAX_RANGE_M / 2f));
                final float py = forwardToY(g, pts[i] * MAX_RANGE_M);
                canvas.drawCircle(px, py, 11f, clusterCorePaint);
                canvas.drawCircle(px, py, 5f, clusterPaint);
            }
        }

        // Closest-point marker + label (unchanged semantics).
        if (model.isTargetVisible()) {
            final float tx = lateralToX(g, model.getTargetLateralNormalized() * (MAX_RANGE_M / 2f));
            final float ty = forwardToY(g, model.getTargetForwardNormalized() * MAX_RANGE_M);
            canvas.drawCircle(tx, ty, 7f, clusterPaint);
            String label = "Closest obstacle " + model.getTargetRangeText();
            float labelX = Math.min(tx + 14f, w - 320f);
            float labelY = Math.max(ty - 16f, 34f);
            drawPillLabel(canvas, label, labelX, labelY);
        }

        // Ego: car-shaped to fixture scale (side view silhouette, centered).
        drawEgo(canvas, g);

        // Live speed banner (top-left card): ego speed from kinematic state.
        // Draw unconditionally; show the em-dash when speed is absent (glanceable
        // placeholder matches the metrics rows).
        drawSpeedBanner(canvas, model.getEgoSpeedText());
    }

    private void drawEgo(Canvas canvas, float[] g) {
        final float mPerPx = g[4];
        // Visual emphasis: fixture-true footprint renders ~50px (unreadable as a car on
        // a 600px surface), so the silhouette is drawn at 2.5x the physical scale. Labeled
        // fixture geometry (contract section 10); range scale of cluster/RSS is unchanged.
        // Unit math: mPerPx is metres-per-pixel, so pixel size = metres / mPerPx.
        final float emph = 2.5f;
        final float carFront = (EGO_FRONT_M / mPerPx) * emph;
        final float carRear = (EGO_REAR_M / mPerPx) * emph;
        final float carWpx = (EGO_WIDTH_M / mPerPx) * emph * 1.4f;

        Path car = new Path();
        float top = g[1] - carFront;
        float bottom = g[1] + carRear * 0.4f;
        float left = g[0] - carWpx / 2f;
        float right = g[0] + carWpx / 2f;
        RectF body = new RectF(left, top, right, bottom);
        car.addRoundRect(body, 14f, 14f, Path.Direction.CW);
        canvas.drawPath(car, egoPaint);
        canvas.drawPath(car, egoOutlinePaint);
        // Cabin hint: darker windshield band (fixture geometry, stylized).
        Paint cabin = new Paint(Paint.ANTI_ALIAS_FLAG);
        cabin.setStyle(Paint.Style.FILL);
        cabin.setColor(Color.argb(70, 18, 18, 18));
        RectF cabinRect = new RectF(left + carWpx * 0.14f, top + carFront * 0.28f,
                right - carWpx * 0.14f, top + carFront * 0.52f);
        canvas.drawRoundRect(cabinRect, 8f, 8f, cabin);
    }

    private void drawPillLabel(Canvas canvas, String text, float x, float y) {
        float textW = bannerTextPaint.measureText(text);
        RectF pill = new RectF(x - 8f, y - 30f, x + textW + 16f, y + 6f);
        canvas.drawRoundRect(pill, 10f, 10f, bannerPaint);
        canvas.drawText(text, x, y - 9f, bannerTextPaint);
    }

    private void drawSpeedBanner(Canvas canvas, String kmh) {
        // Big glanceable speed readout (automotive HMI focal point).
        Paint big = new Paint(Paint.ANTI_ALIAS_FLAG);
        big.setColor(Color.WHITE);
        big.setTextSize(74f);
        big.setFakeBoldText(true);
        Paint unit = new Paint(Paint.ANTI_ALIAS_FLAG);
        unit.setColor(COLOR_RSS_LABEL);
        unit.setTextSize(22f);
        // Anchor inside the guaranteed-visible band: below any system header overlap
        // and above the RSS/scene content. Position relative to the view's usable
        // height so it lands consistently across window insets.
        final float top = getHeight() * 0.06f + 56f;  // clear of status/header overlap
        final float left = 20f;
        RectF card = new RectF(left, top, left + 170f, top + 100f);
        canvas.drawRoundRect(card, 16f, 16f, cardPaint);
        canvas.drawText(kmh, left + 20f, top + 74f, big);
        canvas.drawText("km/h", left + 24f, top + 94f, unit);
    }
}
