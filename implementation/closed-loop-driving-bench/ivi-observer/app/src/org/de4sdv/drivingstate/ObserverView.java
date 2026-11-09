// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// The observer's screen: the operational state and, side by side, the two clocks
// the owner's decision names -- the IVI's own real time at the receipt, and the
// real time the message carries from its publisher. Each panel is labelled with
// the field it shows, because the two are read on different machines: a reader
// must never have to guess which clock a number belongs to.
//
// Below them: health (mode, cause, when the stop began, its source), the vehicle
// state, the newest plan with its frame index and image capture time, and the
// plan's path in the vehicle frame.
//
// Nothing here is computed across time domains: the screen formats the stamps the
// record holds. No latency, no offset, no difference between the clocks.
package org.de4sdv.drivingstate;

import android.content.Context;
import android.graphics.Color;
import android.graphics.Typeface;
import android.util.TypedValue;
import android.view.Gravity;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;

final class ObserverView extends LinearLayout {

    private final TextView linkLine;
    private final TextView iviClock;
    private final TextView iviSource;
    private final TextView publishClock;
    private final TextView publishSource;
    private final TextView healthLine;
    private final TextView vehicleLine;
    private final TextView planLine;
    private final PlanPathView planPath;
    private final TextView countersLine;

    private long receipts;
    private long errors;
    private String linkState = "STARTING";

    ObserverView(Context context) {
        super(context);
        setOrientation(VERTICAL);
        setBackgroundColor(Color.rgb(8, 10, 12));
        final int pad = dp(18);
        setPadding(pad, pad, pad, pad);

        addView(title("DE4SDV DRIVING OPERATIONAL STATE   typed SOME/IP \u2192 VSIDL topic",
                17, Color.rgb(150, 200, 255)));
        linkLine = text("link " + linkState, 15, Color.rgb(255, 200, 0));
        addView(linkLine);

        // The two clocks, side by side.
        final LinearLayout clocks = new LinearLayout(context);
        clocks.setOrientation(HORIZONTAL);
        clocks.setPadding(0, dp(12), 0, dp(8));

        final LinearLayout iviPanel = panel(context);
        iviPanel.addView(text("IVI REAL TIME AT RECEIPT", 13, Color.rgb(150, 200, 255)));
        iviClock = text("--:--:--.---", 34, Color.WHITE);
        iviClock.setTypeface(Typeface.MONOSPACE, Typeface.BOLD);
        iviPanel.addView(iviClock);
        iviSource = text("t_real_ns of the record (ms granularity)", 12, Color.rgb(170, 170, 170));
        iviPanel.addView(iviSource);

        final LinearLayout publishPanel = panel(context);
        publishPanel.addView(text("MESSAGE PUBLISH REAL TIME", 13, Color.rgb(150, 200, 255)));
        publishClock = text("--:--:--.---", 34, Color.WHITE);
        publishClock.setTypeface(Typeface.MONOSPACE, Typeface.BOLD);
        publishPanel.addView(publishClock);
        publishSource = text("publish_real_s . publish_real_ns", 12, Color.rgb(170, 170, 170));
        publishPanel.addView(publishSource);

        final LinearLayout.LayoutParams half =
                new LinearLayout.LayoutParams(0, LayoutParams.WRAP_CONTENT, 1f);
        half.setMargins(dp(6), 0, dp(6), 0);
        clocks.addView(iviPanel, half);
        clocks.addView(publishPanel, half);
        addView(clocks);

        healthLine = text("health: mode --   cause --", 19, Color.rgb(255, 170, 130));
        vehicleLine = text("vehicle: --", 19, Color.rgb(200, 255, 200));
        planLine = text("newest plan: --", 17, Color.rgb(210, 210, 210));
        addView(healthLine);
        addView(vehicleLine);
        addView(planLine);

        planPath = new PlanPathView(context);
        final LinearLayout.LayoutParams pathParams =
                new LinearLayout.LayoutParams(LayoutParams.MATCH_PARENT, 0, 1f);
        pathParams.setMargins(0, dp(6), 0, dp(6));
        addView(planPath, pathParams);

        countersLine = text("receipts 0   errors 0", 12, Color.rgb(170, 170, 170));
        addView(countersLine);
    }

    void setLink(String state) {
        linkState = state;
        linkLine.setText("link " + linkState + "   receipts " + receipts + "   errors " + errors);
        linkLine.setTextColor("SUBSCRIBED".equals(state)
                ? Color.rgb(120, 230, 140) : Color.rgb(255, 200, 0));
    }

    void onState(MessageMapper.Mapped mapped, long tRealNs) {
        receipts++;
        final StateRecord.Fields f = mapped.fields;

        iviClock.setText(clock(tRealNs / 1_000_000_000L, tRealNs % 1_000_000_000L));
        publishClock.setText(clock(f.publishRealS, f.publishRealNs));
        publishSource.setText("publish_real_s . publish_real_ns   ("
                + StateRecord.kindName(f.kind) + " seq " + f.sequence + ")");

        healthLine.setText(String.format(Locale.US,
                "health: mode %d %s   cause %d %s   since %s s   source %s   step %s s",
                f.mode, StateRecord.modeName(f.mode),
                f.cause, StateRecord.causeName(f.cause),
                secondsWait(f.causeSinceMonoS, f.causeSinceMonoNs),
                f.modeSource.isEmpty() ? "-" : f.modeSource,
                simulationSeconds(f.stepCaptureMs)));
        vehicleLine.setText(String.format(Locale.US,
                "vehicle: %s km/h   long %s   lat %s   yaw %s deg/s   sample %s s",
                number(f.speedKmh), number(f.longitudinalAcceleration),
                number(f.lateralAcceleration), number(f.yawRateDps),
                simulationSeconds(f.sampleCaptureMs)));

        if (f.kind == 1) {
            planLine.setText(String.format(Locale.US,
                    "newest plan: frame %d   capture %s s   %d points   horizon %s s   reference %s",
                    f.planFrameIndex, simulationSeconds(f.planCaptureMs), f.planX.length,
                    number(f.planHorizonS), shorten(f.planReference, 30)));
            planPath.setPlan(f.planX, f.planY);
        } else if (f.kind == 3) {
            planLine.setText(String.format(Locale.US,
                    "last plan seen: frame %d   capture %s s   (this message is HEALTH)",
                    f.lastPlanFrameIndex, simulationSeconds(f.lastPlanCaptureMs)));
        } else {
            planLine.setText(String.format(Locale.US,
                    "last plan seen: frame %d   capture %s s   (this message is VEHICLE_STATE)",
                    f.lastPlanFrameIndex, simulationSeconds(f.lastPlanCaptureMs)));
        }

        countersLine.setText(String.format(Locale.US,
                "receipts %d   errors %d   schema %d.%d   sequence %d   dropped %d%s",
                receipts, errors, f.schemaMajor, f.schemaMinor, f.sequence, f.droppedSamples,
                mapped.ok() ? "" : "   CONTRACT " + mapped.contractProblem));
        countersLine.setTextColor(Color.rgb(170, 170, 170));
        if (mapped.allDefaults) {
            countersLine.setText(countersLine.getText()
                    + "   ALL-DEFAULTS (field names may not match)");
            countersLine.setTextColor(Color.rgb(255, 140, 120));
        }
        setLink(linkState);
    }

    void onError(String reason) {
        errors++;
        countersLine.setText("receipts " + receipts + "   errors " + errors + "   last " + reason);
        countersLine.setTextColor(Color.rgb(255, 120, 120));
    }

    /** Seconds of simulation time, from the ICD's `_ms` field. */
    private static String simulationSeconds(long millis) {
        return String.format(Locale.US, "%.1f", millis / 1000.0);
    }

    /** An `_s`/`_ns` pair as a decimal of seconds, not as a reformatted clock. */
    private static String secondsWait(long seconds, long nanos) {
        return String.format(Locale.US, "%d.%09d", seconds, nanos);
    }

    private static String clock(long seconds, long nanos) {
        final long millis = seconds * 1000L + nanos / 1_000_000L;
        final SimpleDateFormat format = new SimpleDateFormat("HH:mm:ss.SSS", Locale.US);
        format.setTimeZone(TimeZone.getTimeZone("UTC"));
        return format.format(new Date(millis));
    }

    private static String number(float value) {
        if (Float.isNaN(value) || Float.isInfinite(value)) {
            return "null";
        }
        return String.format(Locale.US, "%.2f", value);
    }

    private static String shorten(String value, int limit) {
        if (value.isEmpty()) {
            return "-";
        }
        return value.length() <= limit ? value : value.substring(0, limit) + "...";
    }

    private TextView title(String value, int sp, int color) {
        final TextView view = text(value, sp, color);
        view.setPadding(0, 0, 0, dp(4));
        return view;
    }

    private TextView text(String value, int sp, int color) {
        final TextView view = new TextView(getContext());
        view.setText(value);
        view.setTextSize(TypedValue.COMPLEX_UNIT_SP, sp);
        view.setTextColor(color);
        view.setTypeface(Typeface.MONOSPACE);
        view.setGravity(Gravity.START);
        return view;
    }

    private LinearLayout panel(Context context) {
        final LinearLayout panel = new LinearLayout(context);
        panel.setOrientation(VERTICAL);
        panel.setBackgroundColor(Color.rgb(20, 24, 30));
        panel.setPadding(dp(12), dp(10), dp(12), dp(10));
        return panel;
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
