// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// The screen of the warning presentation on the display: the whole screen red with the
// collision warning while a request is shown, dark with a quiet line otherwise, and one status
// line at the bottom. The text is ScreenText's. UI thread only.
//
// onDraw reports the first frame it draws with the warning of a request; MainActivity logs it as
// display_drawn and logs display_committed from the frame-commit callback of the same frame.
package org.de4sdv.collisionwarning;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.view.View;

final class WarningView extends View {

    interface DrawListener {
        void onWarningDrawn(long request);
    }

    private static final int WARNING_RED = Color.rgb(200, 0, 0);
    private static final int IDLE_BACKGROUND = Color.rgb(16, 18, 22);

    private final DrawListener listener;
    private final Paint title = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint action = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint idle = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint status = new Paint(Paint.ANTI_ALIAS_FLAG);
    private boolean active;
    private long request;
    private String statusLine = "";

    WarningView(Context context, DrawListener listener) {
        super(context);
        this.listener = listener;
        title.setColor(Color.WHITE);
        title.setTextAlign(Paint.Align.CENTER);
        title.setFakeBoldText(true);
        action.setColor(Color.WHITE);
        action.setTextAlign(Paint.Align.CENTER);
        action.setFakeBoldText(true);
        idle.setColor(Color.rgb(120, 126, 136));
        idle.setTextAlign(Paint.Align.CENTER);
        status.setColor(Color.rgb(150, 156, 166));
        status.setTextAlign(Paint.Align.LEFT);
    }

    void show(long newRequest) {
        active = true;
        request = newRequest;
        invalidate();
    }

    void clear() {
        active = false;
        invalidate();
    }

    void setStatus(String line) {
        if (!line.equals(statusLine)) {
            statusLine = line;
            invalidate();
        }
    }

    @Override
    protected void onDraw(Canvas canvas) {
        final int w = getWidth();
        final int h = getHeight();
        final float unit = Math.min(w, h) / 600f;
        if (active) {
            canvas.drawColor(WARNING_RED);
            title.setTextSize(96f * unit);
            action.setTextSize(140f * unit);
            canvas.drawText(ScreenText.WARNING_TITLE, w / 2f, h * 0.40f, title);
            canvas.drawText(ScreenText.WARNING_ACTION, w / 2f, h * 0.70f, action);
        } else {
            canvas.drawColor(IDLE_BACKGROUND);
            idle.setTextSize(40f * unit);
            canvas.drawText(ScreenText.IDLE_TITLE, w / 2f, h * 0.50f, idle);
        }
        status.setTextSize(18f * unit);
        canvas.drawText(statusLine, 16f * unit, h - 16f * unit, status);
        if (active) {
            listener.onWarningDrawn(request);
        }
    }
}
