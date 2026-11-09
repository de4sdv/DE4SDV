// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// The plan on screen: plan_x / plan_y of the typed message, drawn in the vehicle
// frame the ICD states -- x forward, y left, metres. Ego is the origin, the
// forward axis points up, nothing is smoothed and no point is dropped: the view
// scales the whole 64-point plan into the panel and draws a 10 m grid so the
// scale is readable.
//
// It shows geometry only. It computes no time and no derived number, and it does
// not draw the vehicle itself anywhere but the origin.
package org.de4sdv.drivingstate;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.view.View;

final class PlanPathView extends View {

    private float[] x = new float[0];
    private float[] y = new float[0];
    private Paint gridPaint;
    private Paint axisPaint;
    private Paint pathPaint;
    private Paint pointPaint;
    private Paint labelPaint;

    PlanPathView(Context context) {
        super(context);
        gridPaint = stroke(Color.rgb(34, 40, 48), 1f);
        axisPaint = stroke(Color.rgb(70, 80, 95), 2f);
        pathPaint = stroke(Color.rgb(120, 230, 140), 3f);
        pointPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
        pointPaint.setColor(Color.rgb(200, 255, 200));
        pointPaint.setStyle(Paint.Style.FILL);
        labelPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
        labelPaint.setColor(Color.rgb(150, 160, 175));
        labelPaint.setTextSize(24f);
        labelPaint.setTypeface(android.graphics.Typeface.MONOSPACE);
    }

    private Paint stroke(int color, float width) {
        final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        paint.setColor(color);
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeWidth(width);
        return paint;
    }

    /** Points in the vehicle frame; a null or short array clears the panel. */
    void setPlan(float[] planX, float[] planY) {
        if (planX == null || planY == null || planX.length < 2 || planX.length != planY.length) {
            x = new float[0];
            y = new float[0];
        } else {
            x = planX.clone();
            y = planY.clone();
        }
        invalidate();
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        final float width = getWidth();
        final float height = getHeight();
        if (width <= 0 || height <= 0) {
            return;
        }
        canvas.drawColor(Color.rgb(14, 17, 21));

        // Bounds in the vehicle frame, with the origin always inside so ego is on
        // screen even when the plan is one-sided.
        float minX = 0f;
        float maxX = 0f;
        float minY = 0f;
        float maxY = 0f;
        for (int index = 0; index < x.length; index++) {
            minX = Math.min(minX, x[index]);
            maxX = Math.max(maxX, x[index]);
            minY = Math.min(minY, y[index]);
            maxY = Math.max(maxY, y[index]);
        }
        final float spanX = Math.max(maxX - minX, 1f);
        final float spanY = Math.max(maxY - minY, 1f);
        final float pad = 28f;
        final float scale = Math.min((width - 2 * pad) / spanX, (height - 2 * pad) / spanY);
        final float originPx = pad + (0f - minX) * scale;
        final float originPy = height - pad - (0f - minY) * scale;

        // 10 m grid, aligned with ego, so the spacing is a known number of metres.
        final float gridStep = 10f * scale;
        for (float offset = 0f; originPx + offset < width; offset += gridStep) {
            canvas.drawLine(originPx + offset, 0f, originPx + offset, height, gridPaint);
        }
        for (float offset = 0f; originPx - offset > 0f; offset += gridStep) {
            canvas.drawLine(originPx - offset, 0f, originPx - offset, height, gridPaint);
        }
        for (float offset = 0f; originPy - offset > 0f; offset += gridStep) {
            canvas.drawLine(0f, originPy - offset, width, originPy - offset, gridPaint);
        }
        for (float offset = 0f; originPy + offset < height; offset += gridStep) {
            canvas.drawLine(0f, originPy + offset, width, originPy + offset, gridPaint);
        }
        // Ego axes: forward up, left to the left.
        canvas.drawLine(originPx, originPy, originPx, originPy - 40f, axisPaint);
        canvas.drawLine(originPx, originPy, originPx - 40f, originPy, axisPaint);

        if (x.length < 2) {
            canvas.drawText("plan path: no plan yet", pad, height / 2f, labelPaint);
            return;
        }

        final Path path = new Path();
        for (int index = 0; index < x.length; index++) {
            final float px = originPx + x[index] * scale;
            final float py = originPy - y[index] * scale;
            if (index == 0) {
                path.moveTo(px, py);
            } else {
                path.lineTo(px, py);
            }
        }
        canvas.drawPath(path, pathPaint);
        for (int index = 0; index < x.length; index++) {
            canvas.drawCircle(originPx + x[index] * scale, originPy - y[index] * scale, 2.5f,
                    pointPaint);
        }
        // The last point is the end of the horizon: a ring, so it reads at a glance.
        final int last = x.length - 1;
        canvas.drawCircle(originPx + x[last] * scale, originPy - y[last] * scale, 7f, pathPaint);
        canvas.drawText(String.format(java.util.Locale.US,
                        "%d points   x %.1f..%.1f m   y %.1f..%.1f m   10 m grid",
                        x.length, minX, maxX, minY, maxY),
                pad, height - 10f, labelPaint);
    }
}
