// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// The observer's screen, drawn on one canvas. It only draws: every string and
// colour comes from ScreenModel, every region from ScreenLayout and every plan
// coordinate from PlanGeometry, all three Android-free and pinned by JVM tests.
//
// Regions (1080 x 600 reference, scaled uniformly): header with the freshness
// chip; the plan panel on the left (vehicle frame, x forward up, y left left,
// one scale for both axes, metric grid, ego marker at the plan's origin); mode,
// speed, plan facts and the two clocks on the right; counters, identity and the
// provenance line at the bottom.
//
// No smoothing, no interpolation, nothing drawn that the message does not carry:
// a stale or missing plan clears the path and says why.
package org.de4sdv.drivingstate;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Insets;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.Typeface;
import android.util.Log;
import android.view.View;
import android.view.WindowInsets;

final class ObserverView extends View {

    private static final int C_BACKGROUND = 0xFF080A0C;
    private static final int C_PANEL = 0xFF12161B;
    private static final int C_GRID = 0xFF263040;
    private static final int C_GRID_LABEL = 0xFF8592A6;
    private static final int C_AXIS = 0xFF4A5868;
    private static final int C_PATH = 0xFF5FD3F3;
    private static final int C_POINT = 0xFFCFF4FF;
    private static final int C_EGO = 0xFFFFFFFF;

    private final ObserverState state;
    private final Paint text = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint fill = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint stroke = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Path path = new Path();

    ObserverView(Context context, ObserverState state) {
        super(context);
        this.state = state;
        text.setTypeface(Typeface.MONOSPACE);
        fill.setStyle(Paint.Style.FILL);
        stroke.setStyle(Paint.Style.STROKE);
        setKeepScreenOn(true);
    }

    // What the system bars cover of this view's edges, px. The window is laid out edge to
    // edge, so without these the header lies under the status bar and the footer under the
    // navigation bar.
    private int barLeft;
    private int barTop;
    private int barRight;
    private int barBottom;

    @Override
    protected void onAttachedToWindow() {
        super.onAttachedToWindow();
        requestApplyInsets();
    }

    @Override
    public WindowInsets onApplyWindowInsets(WindowInsets insets) {
        final Insets bars = insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout());
        if (bars.left != barLeft || bars.top != barTop || bars.right != barRight || bars.bottom != barBottom) {
            barLeft = bars.left;
            barTop = bars.top;
            barRight = bars.right;
            barBottom = bars.bottom;
            Log.i("DE4SDV_DRIVING_STATE", "screen insets left=" + barLeft + " top=" + barTop + " right=" + barRight
                    + " bottom=" + barBottom + " view=" + getWidth() + "x" + getHeight());
            invalidate();
        }
        return insets;
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        final float w = getWidth();
        final float h = getHeight();
        canvas.drawColor(C_BACKGROUND);
        final ScreenLayout.Placement place = ScreenLayout.place(w, h, barLeft, barTop, barRight, barBottom);
        final float s = place.scale;
        if (s <= 0f) {
            return;
        }
        final ScreenModel model = new ScreenModel(state, System.currentTimeMillis());
        canvas.save();
        canvas.translate(place.left, place.top);

        // Header: title left, freshness chip right, the newest link/error state below.
        final ScreenLayout.Box hb = ScreenLayout.HEADER;
        final float row1 = hb.top + ScreenLayout.HEADER_PAD + ScreenLayout.TITLE;
        drawText(canvas, s, ScreenModel.TITLE, hb.left, row1, ScreenLayout.TITLE, ScreenModel.C_TEXT, hb.width / 2f);
        final ScreenModel.Line chip = model.chip();
        final float chipWidth = ScreenLayout.textWidth(chip.text, chip.size) + 16f;
        fill.setColor(0xFF1B2128);
        canvas.drawRect(s * (hb.right() - chipWidth), s * (hb.top + 2f), s * hb.right(), s * (row1 + 7f), fill);
        drawText(canvas, s, chip.text, hb.right() - chipWidth + 8f, row1, chip.size, chip.color, chipWidth);
        final ScreenModel.Line error = model.errorLine();
        if (error != null) {
            drawText(canvas, s, error.text, hb.left, row1 + ScreenLayout.NOTE * ScreenLayout.LINE_SPACING + 2f,
                    error.size, error.color, hb.width);
        }

        drawPlan(canvas, s, model);
        drawBox(canvas, s, ScreenLayout.MODE_BOX, model.modeLines(), model.stale ? 0xFF7A7F87 : model.modeStyle().color);
        drawBox(canvas, s, ScreenLayout.SPEED_BOX, model.speedLines(), 0);
        drawBox(canvas, s, ScreenLayout.FACTS_BOX, model.factLines(), 0);
        drawBox(canvas, s, ScreenLayout.CLOCKS_BOX, model.clockLines(), 0);
        drawBox(canvas, s, ScreenLayout.FOOTER, model.footerLines(), 0);
        canvas.restore();
    }

    private void drawPlan(Canvas canvas, float s, ScreenModel model) {
        final ScreenLayout.Box box = ScreenLayout.PLAN;
        fill.setColor(C_PANEL);
        canvas.drawRect(s * box.left, s * box.top, s * box.right(), s * box.bottom(), fill);
        final ScreenModel.Line title = model.planTitle();
        drawText(canvas, s, title.text, box.left + ScreenLayout.PAD, ScreenLayout.PLAN_TITLE.top + 20f,
                title.size, title.color, box.width - 2f * ScreenLayout.PAD);

        final ScreenLayout.Box plot = ScreenLayout.PLAN_PLOT;
        final String absence = model.planAbsence();
        final StateRecord.Fields plan = absence == null ? state.plan : null;
        final PlanGeometry g = PlanGeometry.fit(s * plot.left, s * plot.top, s * plot.width, s * plot.height,
                plan == null ? null : plan.planX, plan == null ? null : plan.planY);

        // Metric grid, one spacing on both axes, labelled in metres from ego.
        stroke.setStrokeWidth(Math.max(1f, s));
        stroke.setColor(C_GRID);
        text.setTextSize(s * ScreenLayout.NOTE);
        text.setColor(C_GRID_LABEL);
        final float labelTop = g.top + (ScreenLayout.NOTE + 4f) * s;   // keeps labels off the panel title
        for (float m : g.forwardGridM()) {
            final float y = g.screenY(m, 0f);
            canvas.drawLine(g.left, y, g.left + g.width, y, stroke);
            if (m > 0f && y - 3f * s >= labelTop) {
                canvas.drawText(Math.round(m) + " m", g.left + 4f * s, y - 3f * s, text);
            }
        }
        for (float m : g.lateralGridM()) {
            final float x = g.screenX(0f, m);
            canvas.drawLine(x, g.top, x, g.top + g.height, stroke);
        }
        stroke.setColor(C_AXIS);
        stroke.setStrokeWidth(Math.max(1f, 1.5f * s));
        canvas.drawLine(g.originX, g.top, g.originX, g.top + g.height, stroke);
        canvas.drawLine(g.left, g.originY, g.left + g.width, g.originY, stroke);

        if (plan != null) {
            // The 64 points as published, joined in order; nothing smoothed or resampled.
            path.reset();
            path.moveTo(g.originX, g.originY);
            for (int i = 0; i < plan.planX.length; i++) {
                if (!PlanGeometry.finite(plan.planX[i]) || !PlanGeometry.finite(plan.planY[i])) {
                    continue;
                }
                path.lineTo(g.screenX(plan.planX[i], plan.planY[i]), g.screenY(plan.planX[i], plan.planY[i]));
            }
            stroke.setColor(C_PATH);
            stroke.setStrokeWidth(3f * s);
            canvas.save();
            canvas.clipRect(g.left, g.top, g.left + g.width, g.top + g.height);
            canvas.drawPath(path, stroke);
            fill.setColor(C_POINT);
            final PlanKinematics k = ScreenModel.kinematics(plan);
            for (int i = 0; i < plan.planX.length; i++) {
                if (g.inside(plan.planX[i], plan.planY[i])) {
                    final float r = k.isWholeSecond(i) ? 4f * s : 2f * s; // the samples at 1 s, 2 s, ... larger
                    canvas.drawCircle(g.screenX(plan.planX[i], plan.planY[i]),
                            g.screenY(plan.planX[i], plan.planY[i]), r, fill);
                }
            }
            canvas.restore();
        } else {
            drawText(canvas, s, absence, plot.left + 2f * ScreenLayout.PAD, plot.top + plot.height / 3f,
                    ScreenLayout.BODY, model.planStale && state.plan != null ? ScreenModel.C_STALE : ScreenModel.C_DIM,
                    plot.width - 4f * ScreenLayout.PAD);
        }

        // Ego marker at the plan origin: a chevron pointing forward (up).
        path.reset();
        path.moveTo(g.originX, g.originY - 12f * s);
        path.lineTo(g.originX - 8f * s, g.originY + 8f * s);
        path.lineTo(g.originX, g.originY + 3f * s);
        path.lineTo(g.originX + 8f * s, g.originY + 8f * s);
        path.close();
        fill.setColor(C_EGO);
        canvas.drawPath(path, fill);

        final ScreenModel.Line caption = model.planCaption(g);
        drawText(canvas, s, caption.text, box.left + ScreenLayout.PAD, ScreenLayout.PLAN_CAPTION.top + 19f,
                caption.size, caption.color, box.width - 2f * ScreenLayout.PAD);
    }

    /** A panel with a stack of lines; a non-zero accent draws the state bar on its left. */
    private void drawBox(Canvas canvas, float s, ScreenLayout.Box box, ScreenModel.Line[] lines, int accent) {
        fill.setColor(C_PANEL);
        canvas.drawRect(s * box.left, s * box.top, s * box.right(), s * box.bottom(), fill);
        float inset = ScreenLayout.PAD;
        if (accent != 0) {
            fill.setColor(accent);
            canvas.drawRect(s * box.left, s * box.top, s * (box.left + 8f), s * box.bottom(), fill);
            inset += 6f;
        }
        float baseline = box.top + ScreenLayout.PAD_Y;
        for (ScreenModel.Line line : lines) {
            baseline += line.size * ScreenLayout.LINE_SPACING;
            drawText(canvas, s, line.text, box.left + inset, baseline - line.size * 0.25f, line.size, line.color,
                    box.width - inset - ScreenLayout.PAD);
        }
    }

    /** Draws one line; shrinks it only if the device font is wider than the tested advance. */
    private void drawText(Canvas canvas, float s, String value, float xRef, float baselineRef, float sizeRef,
            int color, float maxWidthRef) {
        text.setColor(color);
        text.setTextSize(s * sizeRef);
        final float measured = text.measureText(value);
        final float limit = s * maxWidthRef;
        if (measured > limit && measured > 0f) {
            text.setTextSize(s * sizeRef * limit / measured);
        }
        canvas.drawText(value, s * xRef, s * baselineRef, text);
    }
}
