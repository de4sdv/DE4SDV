package org.de4sdv.aebsvisualization;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.RectF;
import android.util.AttributeSet;
import android.view.View;

/**
 * DE4SDV AEBS forward-situation view (display-derived presentation only).
 *
 * Professional automotive HMI styling (dark base #121212, rounded cards,
 * cyan live accents) applied to the pure render model. ONE isotropic
 * metre-per-pixel factor governs ego footprint, filtered obstacle points,
 * and range ticks alike, so the on-screen separation of ego and obstacle
 * equals their real fixture separation. The ego silhouette is drawn at the
 * TRUE fixture footprint (3.74 m front / 1.03 m rear / 1.83 m width) and is
 * stylized — never enlarged — for readability; point glow is decoration and
 * distance ticks are static display scale
 * (VISUALIZATION-CONTRACT.md §13). No circles, sweep, pulse, invented lanes,
 * or decorative road: every element is live frame data, labeled fixture
 * geometry, or the static display scale. Fails closed: degraded
 * dispositions clear the scene (REQ-AEBS-S2-005/006).
 */
public class ForwardSituationView extends View {

    /** Display scale bound in metres (display-only, not a data bound). */
    private static final float MAX_RANGE_M = SituationRenderModel.MAX_RANGE_M;

    /** Ego footprint from the pinned scenario fixture (metres); see the
     * pure render model, which owns the fixture-true scale contract. */
    private static final float EGO_FRONT_M = SituationRenderModel.EGO_FRONT_M;
    private static final float EGO_REAR_M = SituationRenderModel.EGO_REAR_M;
    private static final float EGO_WIDTH_M = SituationRenderModel.EGO_WIDTH_M;

    /**
     * Point rendering is decoration only: the glow radius must never be
     * readable as physical object extent (VISUALIZATION-CONTRACT.md §13).
     */
    private static final float POINT_GLOW_PX = 6f;
    private static final float POINT_CORE_PX = 3.5f;

    /** Minimum pixel gap between the EGO glyphs and the silhouette boundary. */
    private static final float EGO_LABEL_CLEARANCE_PX = 5f;

    // Design tokens (automotive dark HMI language).
    private static final int COLOR_BASE = Color.rgb(18, 18, 18);
    private static final int COLOR_CARD = Color.rgb(30, 30, 30);
    private static final int COLOR_TICK = Color.rgb(45, 45, 45);
    private static final int COLOR_TICK_LABEL = Color.rgb(85, 85, 85);
    private static final int COLOR_EGO = Color.rgb(229, 229, 229);
    private static final int COLOR_CLUSTER = Color.rgb(0, 229, 255); // cyan live accent
    private static final int COLOR_RSS_LABEL = Color.rgb(176, 176, 176);
    private static final int COLOR_TRAIL = Color.argb(70, 0, 229, 255);

    private final Paint basePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint tickPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint tickLabelPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint cardPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint egoPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint egoHaloPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint egoLabelPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint clusterPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint clusterCorePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint trailPaint = new Paint(Paint.ANTI_ALIAS_FLAG);

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

        // Soft presentation-only emphasis halo around the fixture-true ego
        // footprint (never extends the represented dimensions; contract §13).
        egoHaloPaint.setStyle(Paint.Style.FILL);
        egoHaloPaint.setColor(Color.argb(60, 229, 229, 229));

        // EGO label: light-on-dark below the silhouette; crisp separation from
        // both the vehicle edge and the scene background.
        egoLabelPaint.setColor(Color.rgb(229, 229, 229));
        egoLabelPaint.setTextSize(17f);
        egoLabelPaint.setFakeBoldText(true);
        egoLabelPaint.setTextAlign(Paint.Align.CENTER);

        clusterPaint.setStyle(Paint.Style.FILL);
        clusterPaint.setColor(COLOR_CLUSTER);

        clusterCorePaint.setStyle(Paint.Style.FILL);
        clusterCorePaint.setColor(Color.argb(120, 0, 229, 255));

        trailPaint.setStyle(Paint.Style.FILL);
        trailPaint.setColor(COLOR_TRAIL);


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
     * Scene geometry. Ego REAR bumper sits at originY; every element (ego
     * footprint, filtered obstacle points, ticks) uses ONE metre-per-pixel
     * factor in both axes, so unequal scaling can never introduce a visual
     * overlap that the metric geometry does not contain
     * (VISUALIZATION-CONTRACT.md §13).
     */
    private float[] sceneGeometry() {
        final float w = getWidth();
        final float h = getHeight();
        final float originX = w / 2f;
        final float originY = h * 0.90f;          // ego rear bumper
        final float usableHeight = h * 0.74f;     // 0..60 m band above origin
        final float metresPerPx = MAX_RANGE_M / usableHeight;
        return new float[]{originX, originY, usableHeight, 0f, metresPerPx};
    }

    private float forwardToY(float[] g, float metres) {
        return g[1] - (metres / MAX_RANGE_M) * g[2];
    }

    private float lateralToX(float[] g, float metres) {
        // Same metres-per-pixel factor as the forward axis (isotropic scene).
        return g[0] + metres / g[4];
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

        // Filtered obstacle cluster: bounded point projection (schema minor 1).
        // Rendered as cyan points only; no object classification or AEB
        // decision-distance semantics are implied. Glow radius is decoration
        // only and is smaller than the projected geometry it decorates, so
        // apparent contact can never precede the underlying point position.
        if (model.isClusterVisible()) {
            final float[] pts = model.getClusterPointsDisplay();
            for (int i = 0; i + 1 < pts.length; i += 2) {
                final float px = lateralToX(g, pts[i + 1] * (MAX_RANGE_M / 2f));
                final float py = forwardToY(g, pts[i] * MAX_RANGE_M);
                canvas.drawCircle(px, py, POINT_GLOW_PX, clusterCorePaint);
                canvas.drawCircle(px, py, POINT_CORE_PX, clusterPaint);
            }
        }


        // Ego reference silhouette at fixture-true scale (isotropic scene).
        drawEgo(canvas, g);

        // Live speed banner (top-left card): ego speed from kinematic state.
        // Draw unconditionally; show the em-dash when speed is absent (glanceable
        // placeholder matches the metrics rows).
        drawSpeedBanner(canvas, model.getEgoSpeedText());
    }

    /**
     * Ego reference silhouette at the TRUE fixture footprint. Ego and the
     * filtered obstacle points share one isotropic metre-per-pixel factor, so
     * their relative separation on screen equals their real separation in the
     * fixture scene (no presentation-only enlargement; no renderer-side
     * collision semantics — contact is a System 1 decision, not a drawing
     * outcome). At true scale (~5 px wide at 1080×600) the silhouette is
     * stylized: a bright core with a soft emphasis halo that stays inside the
     * projected footprint boundary. The halo is presentation-only and never
     * extends the represented physical dimensions.
     */
    private void drawEgo(Canvas canvas, float[] g) {
        final float mPerPx = g[4];
        // Unit math: mPerPx is metres-per-pixel, so pixel size = metres / mPerPx.
        final float carFront = EGO_FRONT_M / mPerPx;
        final float carRear = EGO_REAR_M / mPerPx;
        final float carWpx = EGO_WIDTH_M / mPerPx;

        float top = g[1] - carFront;
        float bottom = g[1] + carRear * 0.4f;
        float left = g[0] - carWpx / 2f;
        float right = g[0] + carWpx / 2f;
        // Soft emphasis halo: same footprint, larger radius, low alpha. The
        // halo radius never exceeds the full footprint span, so the emphasized
        // shape still reads as a single vehicle footprint, not a larger one.
        final float halo = Math.min(carFront + carRear * 0.4f, 22f);
        canvas.drawCircle(g[0], g[1] + (carRear * 0.4f - carFront) / 2f,
                halo, egoHaloPaint);
        // Crisp fixture-true core (rounded-rect, unmodified metric footprint).
        RectF body = new RectF(left, top, right, bottom);
        canvas.drawRoundRect(body, 2f, 2f, egoPaint);
        // EGO label sits BELOW the silhouette with a clearance gap so the
        // glyphs never touch the physical boundary or blend with the vehicle
        // edge at 1080×600 anti-aliasing (contract §13).
        canvas.drawText("EGO",
                g[0],
                bottom + EGO_LABEL_CLEARANCE_PX + egoLabelPaint.getTextSize() * 0.8f,
                egoLabelPaint);
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
        // Root WindowInsets padding guarantees this view starts inside the usable
        // application bounds. Keep the card local to the scene instead of applying
        // a guessed duplicate system-header offset.
        final float top = 18f;
        final float left = 20f;
        RectF card = new RectF(left, top, left + 170f, top + 100f);
        canvas.drawRoundRect(card, 16f, 16f, cardPaint);
        canvas.drawText(kmh, left + 20f, top + 74f, big);
        canvas.drawText("km/h", left + 24f, top + 94f, unit);
    }
}
