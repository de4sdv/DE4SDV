// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// Everything the screen writes, as plain strings and colour tokens, built from
// ObserverState and the IVI's real time. Android-free and tested
// (ScreenModelTest): every visible number maps to a field of the typed message,
// to the IVI's own receipt clock, or to a stated combination of the two.
//
// Rules it follows (HMI design rules, the brief):
//  * the state colour has exactly one authority, HEALTH's `mode`; nothing else
//    colours the mode box, and every colour comes with its text;
//  * a missing value prints MISSING ("—"), never a zero or a guess;
//  * STALE (no receipt for ObserverState.STALE_AFTER_MS) is always visible in the
//    header and greys the mode; a stale plan is not drawn (fail closed);
//  * stepwise values: the newest receipt, never an interpolation or an average
//    across receipts;
//  * the two real-time clocks are printed side by side, each with its source;
//  * the model's name is not printed: no field of the message carries it.
package org.de4sdv.drivingstate;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;

final class ScreenModel {

    static final String MISSING = "\u2014";

    /** The one provenance line: the real path of every value on this screen. */
    static final String PROVENANCE =
            "S-CORE statePublisher \u2192 SOME/IP \u2192 SDV Core broker \u2192 typed topic \u2192 this app";

    static final String TITLE = "DRIVING PLAN \u00b7 IVI observer (read-only)";

    /** The stale limit as printed. */
    static final String LIMIT = String.format(Locale.US, "%.1f", ObserverState.STALE_AFTER_MS / 1000.0);

    // Colour tokens (ARGB). The view uses them as they are.
    static final int C_TEXT = 0xFFE8ECF1;
    static final int C_DIM = 0xFF9AA4B1;
    static final int C_GREY = 0xFF7A7F87;
    static final int C_STARTING = 0xFF8FA3B8;
    static final int C_DRIVING = 0xFF4CC38A;
    static final int C_STOP = 0xFFF5A623;
    static final int C_STANDSTILL = 0xFFE5484D;
    static final int C_REFUSED = 0xFFD14CD1;
    static final int C_LIVE = 0xFF4CC38A;
    static final int C_STALE = 0xFFF5A623;
    static final int C_FAULT = 0xFFE5484D;

    static final class Line {
        final String text;
        final float size;
        final int color;

        Line(String text, float size, int color) {
            this.text = text;
            this.size = size;
            this.color = color;
        }
    }

    /** The mode box's look: one per HEALTH mode value, plus "no HEALTH yet". */
    enum ModeStyle {
        NONE("NO HEALTH YET", C_GREY),
        STARTING("STARTING", C_STARTING),
        DRIVING("DRIVING", C_DRIVING),
        STOP_RESPONSE("STOP RESPONSE", C_STOP),
        STANDSTILL("STANDSTILL", C_STANDSTILL),
        REFUSED("REFUSED", C_REFUSED),
        UNKNOWN("MODE ?", C_GREY);

        final String label;
        final int color;

        ModeStyle(String label, int color) {
            this.label = label;
            this.color = color;
        }

        static ModeStyle of(StateRecord.Fields health) {
            if (health == null) {
                return NONE;
            }
            switch ((int) health.mode) {
                case 0:
                    return STARTING;
                case 1:
                    return DRIVING;
                case 2:
                    return STOP_RESPONSE;
                case 3:
                    return STANDSTILL;
                case 4:
                    return REFUSED;
                default:
                    return UNKNOWN;
            }
        }
    }

    final ObserverState state;
    final long nowRealMs;
    final boolean stale;
    final boolean planStale;

    ScreenModel(ObserverState state, long nowRealMs) {
        this.state = state;
        this.nowRealMs = nowRealMs;
        this.stale = state.stale(nowRealMs);
        this.planStale = state.planStale(nowRealMs);
    }

    // ------------------------------------------------------------------ header

    /** The freshness chip, always shown. */
    Line chip() {
        if (state.last == null) {
            if ("UNAVAILABLE".equals(state.link)) {
                return new Line("GATEWAY UNAVAILABLE", ScreenLayout.CHIP, C_FAULT);
            }
            return new Line("NO DATA \u00b7 " + state.link, ScreenLayout.CHIP, C_GREY);
        }
        if (stale) {
            return new Line("STALE " + age2(state.ageOfLastReceiptMs(nowRealMs) / 1000.0) + " s (> " + LIMIT + " s)",
                    ScreenLayout.CHIP, C_STALE);
        }
        return new Line("\u25cf LIVE \u00b7 stale > " + LIMIT + " s", ScreenLayout.CHIP, C_LIVE);
    }

    // ------------------------------------------------------------------ plan panel

    Line planTitle() {
        return new Line("PLANNED PATH \u00b7 x forward \u2191  y left \u2190", ScreenLayout.SMALL, C_DIM);
    }

    /** Null when the plan is drawn; otherwise the text the empty panel shows. */
    String planAbsence() {
        if (state.plan == null) {
            return "no plan received yet";
        }
        if (planStale) {
            return "PLAN STALE \u00b7 frame " + state.plan.planFrameIndex + ", "
                    + age((nowRealMs - state.planReceiptRealNs / 1_000_000L) / 1000.0) + " s ago";
        }
        if (state.plan.planX.length == 0 || state.plan.planX.length != state.plan.planY.length) {
            return "plan has no points (" + state.plan.planX.length + " x, " + state.plan.planY.length + " y)";
        }
        return null;
    }

    Line planCaption(PlanGeometry g) {
        if (state.plan == null || planAbsence() != null) {
            // Nothing drawn: no plan numbers under an empty grid.
            return new Line("horizon " + MISSING + " \u00b7 grid " + num(g.gridM, 0) + " m", ScreenLayout.SMALL, C_DIM);
        }
        final PlanKinematics k = kinematics(state.plan);
        return new Line("horizon " + num(state.plan.planHorizonS, 1) + " s \u00b7 path " + num(k.pathLengthM(), 1)
                + " m \u00b7 grid " + num(g.gridM, 0) + " m", ScreenLayout.SMALL, C_DIM);
    }

    // ------------------------------------------------------------------ mode box

    ModeStyle modeStyle() {
        return ModeStyle.of(state.health);
    }

    Line[] modeLines() {
        final StateRecord.Fields h = state.health;
        final ModeStyle style = modeStyle();
        final int color = stale ? C_GREY : style.color;
        final String label = style == ModeStyle.UNKNOWN && h != null ? "MODE " + h.mode : style.label;
        if (h == null) {
            return new Line[] {
                new Line(label, ScreenLayout.MODE, color),
                new Line("cause " + MISSING, ScreenLayout.CAUSE, C_DIM),
                new Line("source " + MISSING, ScreenLayout.SMALL, C_DIM),
            };
        }
        String cause = "cause: " + causeWords(h.cause);
        if (h.mode == 4 && !h.refusalReason.isEmpty()) {
            cause = cause + " (" + h.refusalReason + ")";
        }
        String third = "source " + (h.modeSource.isEmpty() ? MISSING : h.modeSource);
        if (h.causeSinceMonoS != 0 || h.causeSinceMonoNs != 0) {
            third = third + String.format(Locale.US, " \u00b7 since %d.%03d s",
                    h.causeSinceMonoS, h.causeSinceMonoNs / 1_000_000L);
        }
        if (stale) {
            third = "STALE: last HEALTH " + age((nowRealMs - state.healthReceiptRealNs / 1_000_000L) / 1000.0)
                    + " s ago";
        }
        return new Line[] {
            new Line(label, ScreenLayout.MODE, color),
            new Line(cause, ScreenLayout.CAUSE, stale ? C_GREY : C_TEXT),
            new Line(third, ScreenLayout.SMALL, stale ? C_STALE : C_DIM),
        };
    }

    static String causeWords(long cause) {
        switch ((int) cause) {
            case 0:
                return "none";
            case 1:
                return "camera missing";
            case 2:
                return "camera invalid";
            case 3:
                return "camera stale";
            case 4:
                return "motion invalid";
            case 5:
                return "motion stale";
            case 6:
                return "route stale";
            case 7:
                return "route empty";
            case 8:
                return "plan stale";
            case 9:
                return "plan invalid";
            case 10:
                return "command timeout";
            case 11:
                return "checkpoint refused";
            case 12:
                return "run end";
            default:
                return "code " + cause;
        }
    }

    // ------------------------------------------------------------------ speed box

    Line[] speedLines() {
        final StateRecord.Fields v = state.vehicle;
        final int color = stale ? C_GREY : C_TEXT;
        final String now;
        final String sample;
        if (v == null || !PlanGeometry.finite(v.speedKmh)) {
            now = "speed " + MISSING;
            sample = v == null ? "no VEHICLE_STATE yet" : "speed_kmh not finite";
        } else {
            now = num(v.speedKmh / 3.6f, 2) + " m/s  " + num(v.speedKmh, 1) + " km/h";
            sample = "vehicle state sim " + simSeconds(v.sampleCaptureMs) + " s \u00b7 seq " + v.sequence;
        }
        return new Line[] {
            new Line(now, ScreenLayout.SPEED, color),
            new Line(sample, ScreenLayout.SMALL, C_DIM),
            new Line(planSpeedText(), ScreenLayout.BODY, color),
            new Line("plan v in m/s: this speed + \u222b plan acceleration", ScreenLayout.NOTE, C_DIM),
        };
    }

    /** The plan's speed at +1 s, +3 s and the horizon, from the newest speed. */
    String planSpeedText() {
        final StateRecord.Fields p = state.plan;
        final StateRecord.Fields v = state.vehicle;
        if (p == null || planStale || v == null || !PlanGeometry.finite(v.speedKmh)) {
            return "plan v " + MISSING;
        }
        final PlanKinematics k = kinematics(p);
        final float start = v.speedKmh / 3.6f;
        final float end = k.horizonS();
        return "plan v +1s " + num(k.speedAt(start, 1f), 1) + " \u00b7 +3s " + num(k.speedAt(start, 3f), 1)
                + " \u00b7 +" + num(end, 1) + "s " + num(k.speedAt(start, end), 1);
    }

    // ------------------------------------------------------------------ plan facts

    Line[] factLines() {
        final StateRecord.Fields p = state.plan;
        final int color = (stale || planStale) ? C_GREY : C_TEXT;
        if (p == null) {
            return new Line[] {
                new Line("frame " + MISSING + " \u00b7 image sim " + MISSING, ScreenLayout.BODY, C_DIM),
                new Line("points " + MISSING, ScreenLayout.BODY, C_DIM),
                new Line("+1 s: " + MISSING, ScreenLayout.BODY, C_DIM),
                new Line("curvature 0-1 s " + MISSING, ScreenLayout.BODY, C_DIM),
            };
        }
        final PlanKinematics k = kinematics(p);
        final int i1 = k.indexAt(1f);
        return new Line[] {
            new Line("frame " + p.planFrameIndex + " \u00b7 image sim " + simSeconds(p.planCaptureMs) + " s",
                    ScreenLayout.BODY, color),
            new Line("points " + k.count + " \u00b7 sample_count " + p.planSampleCount, ScreenLayout.BODY,
                    p.planSampleCount == k.count ? color : C_STALE),
            new Line("+1 s: " + num(k.xAt(i1), 1) + " m ahead, " + lateral(k.yAt(i1)), ScreenLayout.BODY, color),
            new Line("curvature 0-1 s: " + num(k.meanCurvature(1f), 3) + " 1/m (+ = left)", ScreenLayout.BODY, color),
        };
    }

    static String lateral(float yLeft) {
        if (!PlanGeometry.finite(yLeft)) {
            return MISSING;
        }
        if (Math.abs(yLeft) < 0.05f) {
            return "0.0 m lateral";
        }
        return num(Math.abs(yLeft), 1) + (yLeft > 0 ? " m left" : " m right");
    }

    // ------------------------------------------------------------------ clocks

    Line[] clockLines() {
        final StateRecord.Fields last = state.last;
        final String publish = last == null || last.publishRealS == 0 ? MISSING + " UTC"
                : clock(ObserverState.realNs(last.publishRealS, last.publishRealNs) / 1_000_000L);
        final double lag = state.receiptLagS();
        final double age = state.planAgeS(nowRealMs);
        return new Line[] {
            new Line("IVI now  " + clock(nowRealMs), ScreenLayout.CLOCK, C_TEXT),
            new Line("publish  " + publish, ScreenLayout.CLOCK, stale ? C_GREY : C_TEXT),
            new Line("receipt lag " + seconds(lag) + " s \u00b7 plan age " + seconds(planStale ? Double.NaN : age) + " s",
                    ScreenLayout.SMALL, stale ? C_GREY : C_TEXT),
            new Line("lag, age: IVI vs S-CORE real time (two clocks)", ScreenLayout.NOTE, C_DIM),
        };
    }

    // ------------------------------------------------------------------ footer

    Line[] footerLines() {
        final ObserverState s = state;
        String counters = String.format(Locale.US,
                "seq P %s V %s H %s \u00b7 receipts %d \u00b7 gaps %d \u00b7 parse fail %d",
                seq(s.plan, s.lastSequence[1]), seq(s.vehicle, s.lastSequence[2]), seq(s.health, s.lastSequence[3]),
                s.receipts, s.sequenceGaps,
                s.parseFailures);
        int counterColor = C_DIM;
        if (s.contractProblems > 0 || s.allDefaultReceipts > 0) {
            counters = String.format(Locale.US, "CONTRACT %s \u00b7 problems %d \u00b7 all-default %d \u00b7 receipts %d",
                    s.lastContractProblem.isEmpty() ? "ok" : s.lastContractProblem, s.contractProblems,
                    s.allDefaultReceipts, s.receipts);
            counterColor = C_FAULT;
        }
        final StateRecord.Fields p = s.plan;
        final StateRecord.Fields any = s.last;
        final String identity = "drops pub " + (s.health == null ? MISSING : Long.toString(s.health.droppedSamples))
                + " gw " + s.gatewayDataLoss
                + " \u00b7 run " + (p == null || p.runRecord.isEmpty() ? MISSING : p.runRecord)
                + " \u00b7 producer " + (p == null || p.planProducer.isEmpty() ? MISSING : p.planProducer)
                + " \u00b7 schema " + (any == null ? MISSING : any.schemaMajor + "." + any.schemaMinor);
        return new Line[] {
            new Line(counters, ScreenLayout.SMALL, counterColor),
            new Line(identity, ScreenLayout.SMALL, C_DIM),
            new Line(PROVENANCE, ScreenLayout.NOTE, C_DIM),
        };
    }

    /** Characters of the header's status line (fits 1036 px at 15 px, 0.61 em). */
    static final int ERROR_CHARS = 110;

    /**
     * The link state or the newest error, for the header's second line (never hidden). A long
     * message keeps its head and its tail (where the gateway puts "(statusCode N: NAME)");
     * the record file has it in full.
     */
    Line errorLine() {
        if ("UNAVAILABLE".equals(state.link) || "WAITING".equals(state.link)) {
            final String detail = state.linkDetail.isEmpty() ? state.link : state.link + ": " + state.linkDetail;
            return new Line(shortenMiddle(detail, ERROR_CHARS), ScreenLayout.NOTE,
                    "UNAVAILABLE".equals(state.link) ? C_FAULT : C_STALE);
        }
        if (!state.lastError.isEmpty()) {
            return new Line(shortenMiddle("last error: " + state.lastError, ERROR_CHARS), ScreenLayout.NOTE, C_STALE);
        }
        return null;
    }

    // ------------------------------------------------------------------ helpers

    static PlanKinematics kinematics(StateRecord.Fields p) {
        return new PlanKinematics(p.planHorizonS, p.planAcceleration, p.planCurvature, p.planX, p.planY);
    }

    static String num(double value, int decimals) {
        if (Double.isNaN(value) || Double.isInfinite(value)) {
            return MISSING;
        }
        return String.format(Locale.US, "%." + decimals + "f", value);
    }

    /** A kind's newest sequence, or MISSING when no sample of that kind was accepted. */
    static String seq(StateRecord.Fields newest, long sequence) {
        return newest == null ? MISSING : Long.toString(sequence);
    }

    /** Seconds with two decimals (the stale chip: "1.04 s (> 1.0 s)", never "1.0 s (> 1.0 s)"). */
    static String age2(double secondsValue) {
        if (Double.isNaN(secondsValue)) {
            return MISSING;
        }
        return secondsValue > 999.99 ? ">999.99" : String.format(Locale.US, "%.2f", secondsValue);
    }

    /** Seconds with one decimal, capped at 999.9 so a long outage keeps its line width. */
    static String age(double secondsValue) {
        if (Double.isNaN(secondsValue)) {
            return MISSING;
        }
        return secondsValue > 999.9 ? ">999.9" : String.format(Locale.US, "%.1f", secondsValue);
    }

    /** Seconds with three decimals (ms), capped at +-999.999 for a clock that is far off. */
    static String seconds(double value) {
        if (Double.isNaN(value) || Double.isInfinite(value)) {
            return MISSING;
        }
        if (value >= 999.9995) {
            return ">999.999";
        }
        if (value <= -999.9995) {
            return "<-999.999";
        }
        return String.format(Locale.US, "%.3f", value);
    }

    static String simSeconds(long millis) {
        return String.format(Locale.US, "%.1f", millis / 1000.0);
    }

    static String clock(long epochMillis) {
        final SimpleDateFormat format = new SimpleDateFormat("HH:mm:ss.SSS", Locale.US);
        format.setTimeZone(TimeZone.getTimeZone("UTC"));
        return format.format(new Date(epochMillis)) + " UTC";
    }

    static String shortenMiddle(String value, int limit) {
        if (value.length() <= limit) {
            return value;
        }
        final int tail = (limit - 1) * 2 / 5;
        final int head = limit - 1 - tail;
        return value.substring(0, head) + "\u2026" + value.substring(value.length() - tail);
    }
}
