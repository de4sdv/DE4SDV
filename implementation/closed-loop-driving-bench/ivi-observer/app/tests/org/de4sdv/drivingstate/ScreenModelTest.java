// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// The screen's content and its fit at 1080 x 600 (no Android).
//
// Fit is checked with the worst-case values each line can carry (10-digit
// counters, negative numbers, the longest mode and cause words, a refusal), at
// a monospace advance of 0.61 em.
package org.de4sdv.drivingstate;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public class ScreenModelTest {

    private static final long NOW_MS = 1762742400_000L + 500L;   // 2025-11-10T02:40:00.500Z

    private static MessageMapper.Mapped mapped(StateRecord.Fields f) {
        return new MessageMapper.Mapped(f, "", false);
    }

    private static StateRecord.Fields header(long kind, long sequence, long publishMs) {
        final StateRecord.Fields f = new StateRecord.Fields();
        f.schemaMajor = 2;
        f.kind = kind;
        f.sequence = sequence;
        f.producer = "statePublisher";
        f.publishRealS = publishMs / 1000L;
        f.publishRealNs = (publishMs % 1000L) * 1_000_000L;
        f.publishMonoS = 5000L;
        f.publishMonoNs = 40_000_000L;
        return f;
    }

    static StateRecord.Fields plan(long sequence, long publishMs) {
        final StateRecord.Fields f = header(1, sequence, publishMs);
        f.planFrameIndex = 1234;
        f.planCaptureMs = 123400;
        f.planProductionMonoS = 5000L;
        f.planProductionMonoNs = 10_000_000L;   // 30 ms before the publish
        f.planReference = "0123456789abcdef/1234";
        f.runRecord = "0123456789abcdef";
        f.planProducer = "drivingAgent/inferPlan";
        f.planSampleCount = 64;
        f.planHorizonS = 6.4f;
        f.planAcceleration = new float[64];
        f.planCurvature = new float[64];
        f.planX = new float[64];
        f.planY = new float[64];
        for (int i = 0; i < 64; i++) {
            f.planAcceleration[i] = 0.5f;
            f.planCurvature[i] = i < 10 ? -0.047f : 0.01f;
            f.planX[i] = 0.8f * (i + 1);
            f.planY[i] = 0.004f * (i + 1) * (i + 1) / 10f;
        }
        return f;
    }

    static StateRecord.Fields vehicle(long sequence, long publishMs, float kmh) {
        final StateRecord.Fields f = header(2, sequence, publishMs);
        f.speedKmh = kmh;
        f.sampleCaptureMs = 123400;
        return f;
    }

    static StateRecord.Fields health(long sequence, long publishMs, long mode, long cause) {
        final StateRecord.Fields f = header(3, sequence, publishMs);
        f.mode = mode;
        f.cause = cause;
        f.modeSource = "superviseLoop";
        return f;
    }

    private static ObserverState live() {
        final ObserverState s = new ObserverState();
        s.setLink("SUBSCRIBED", "instance1:de4sdv-driving-operational-state");
        s.onReceipt(mapped(health(1, NOW_MS - 120, 1, 0)), (NOW_MS - 100) * 1_000_000L);
        s.onReceipt(mapped(vehicle(1, NOW_MS - 90, 36f)), (NOW_MS - 60) * 1_000_000L);
        s.onReceipt(mapped(plan(1, NOW_MS - 80)), (NOW_MS - 40) * 1_000_000L);
        return s;
    }

    @Test
    public void provenanceStatesTheRealPathExactly() {
        assertEquals("S-CORE statePublisher \u2192 SOME/IP \u2192 SDV Core broker \u2192 typed topic \u2192 this app",
                ScreenModel.PROVENANCE);
        final ScreenModel.Line[] footer = new ScreenModel(live(), NOW_MS).footerLines();
        assertEquals(ScreenModel.PROVENANCE, footer[footer.length - 1].text);
    }

    @Test
    public void theModelNameIsNotPrintedBecauseNoFieldCarriesIt() {
        for (String text : allText(new ScreenModel(live(), NOW_MS))) {
            assertFalse(text, text.toLowerCase().contains("autoe2e"));
        }
        assertTrue(String.join("|", allText(new ScreenModel(live(), NOW_MS))).contains("drivingAgent/inferPlan"));
    }

    @Test
    public void liveStateShowsSpeedPlanSpeedAndBothClocks() {
        final ScreenModel m = new ScreenModel(live(), NOW_MS);
        assertEquals("\u25cf LIVE \u00b7 stale > 1.0 s", m.chip().text);
        assertNull(m.planAbsence());
        assertEquals("10.00 m/s  36.0 km/h", m.speedLines()[0].text);
        // 10 m/s + 0.5 m/s^2 over 1 s, 3 s and 6.4 s: the plan's speed from this speed.
        assertEquals("plan v +1s 10.5 \u00b7 +3s 11.5 \u00b7 +6.4s 13.2", m.speedLines()[2].text);
        assertEquals("plan v in m/s: this speed + \u222b plan acceleration", m.speedLines()[3].text);
        final ScreenModel.Line[] clocks = m.clockLines();
        assertEquals("IVI now  02:40:00.500 UTC", clocks[0].text);
        assertEquals("publish  02:40:00.420 UTC", clocks[1].text);   // the newest receipt (the plan)
        // lag: receipt NOW-40 minus publish NOW-80 = 0.040 s; age: now minus publish (0.080 s)
        // plus publish mono minus production mono (0.030 s) = 0.110 s.
        assertEquals("receipt lag 0.040 s \u00b7 plan age 0.110 s", clocks[2].text);
        assertEquals("frame 1234 \u00b7 image sim 123.4 s", m.factLines()[0].text);
        assertEquals("points 64 \u00b7 sample_count 64", m.factLines()[1].text);
        assertEquals("+1 s: 8.0 m ahead, 0.0 m lateral", m.factLines()[2].text);
        assertEquals("curvature 0-1 s: -0.047 1/m (+ = left)", m.factLines()[3].text);
    }

    @Test
    public void missingValuesShowAsMissingNeverAsZero() {
        final ObserverState empty = new ObserverState();
        final ScreenModel m = new ScreenModel(empty, NOW_MS);
        assertEquals("NO DATA \u00b7 STARTING", m.chip().text);
        assertEquals("NO HEALTH YET", m.modeLines()[0].text);
        assertEquals("speed \u2014", m.speedLines()[0].text);
        assertEquals("plan v \u2014", m.speedLines()[2].text);
        assertEquals("publish  \u2014 UTC", m.clockLines()[1].text);
        assertEquals("receipt lag \u2014 s \u00b7 plan age \u2014 s", m.clockLines()[2].text);
        assertEquals("no plan received yet", m.planAbsence());
        // No sample of a kind yet: its sequence is missing, not 0. Counters of the app are counts.
        assertTrue(m.footerLines()[0].text, m.footerLines()[0].text.startsWith(
                "seq P \u2014 V \u2014 H \u2014 \u00b7 receipts 0 \u00b7 gaps 0"));
        for (String text : allText(m)) {
            assertFalse("a zero stands in for a missing value: " + text, text.contains(" 0.00 m/s"));
        }
    }

    @Test
    public void staleIsVisibleAndClearsThePlan() {
        final ObserverState s = live();
        final long later = NOW_MS + 3_000L;
        final ScreenModel m = new ScreenModel(s, later);
        assertTrue(m.stale);
        assertEquals("STALE 3.04 s (> 1.0 s)", m.chip().text);
        assertEquals(ScreenModel.C_STALE, m.chip().color);
        assertEquals("DRIVING", m.modeLines()[0].text);
        assertEquals(ScreenModel.C_GREY, m.modeLines()[0].color);
        assertEquals("STALE: last HEALTH 3.1 s ago", m.modeLines()[2].text);
        assertEquals("PLAN STALE \u00b7 frame 1234, 3.0 s ago", m.planAbsence());
        assertEquals("plan v \u2014", m.speedLines()[2].text);
        assertEquals("receipt lag 0.040 s \u00b7 plan age \u2014 s", m.clockLines()[2].text);
        // The stale plan is not drawn, so no plan numbers stand under the empty grid.
        final PlanGeometry g = PlanGeometry.fit(0f, 0f, 540f, 396f, null, null);
        assertEquals("horizon \u2014 \u00b7 grid 5 m", m.planCaption(g).text);
    }

    @Test
    public void staleStartsAfterTheStatedLimitAndNotBefore() {
        final ObserverState s = live();
        final long lastMs = NOW_MS - 40;
        assertFalse(new ScreenModel(s, lastMs + ObserverState.STALE_AFTER_MS).stale);
        assertTrue(new ScreenModel(s, lastMs + ObserverState.STALE_AFTER_MS + 1).stale);
    }

    @Test
    public void eachModeHasItsOwnLabelAndColourAndTheColourHasOneAuthority() {
        final Set<String> labels = new HashSet<>();
        final Set<Integer> colours = new HashSet<>();
        final String[] expected = {"STARTING", "DRIVING", "STOP RESPONSE", "STANDSTILL", "REFUSED"};
        for (int mode = 0; mode <= 4; mode++) {
            final ObserverState s = live();
            s.onReceipt(mapped(health(2 + mode, NOW_MS - 30, mode, mode == 0 ? 0 : 8)), (NOW_MS - 20) * 1_000_000L);
            final ScreenModel m = new ScreenModel(s, NOW_MS);
            final ScreenModel.Line top = m.modeLines()[0];
            assertEquals(expected[mode], top.text);
            labels.add(top.text);
            colours.add(top.color);
            // The plan, the speed and the clocks never take the mode colour.
            assertTrue(m.speedLines()[0].color == ScreenModel.C_TEXT);
        }
        assertEquals(5, labels.size());
        assertEquals(5, colours.size());
        final ObserverState s = live();
        s.onReceipt(mapped(health(9, NOW_MS - 30, 7, 0)), (NOW_MS - 20) * 1_000_000L);
        assertEquals("MODE 7", new ScreenModel(s, NOW_MS).modeLines()[0].text);
    }

    @Test
    public void causeAndRefusalAreWords() {
        final ObserverState s = live();
        final StateRecord.Fields h = health(2, NOW_MS - 30, 4, 11);
        h.refusalReason = "mismatch";
        h.causeSinceMonoS = 4999;
        h.causeSinceMonoNs = 250_000_000L;
        s.onReceipt(mapped(h), (NOW_MS - 20) * 1_000_000L);
        final ScreenModel.Line[] lines = new ScreenModel(s, NOW_MS).modeLines();
        assertEquals("cause: checkpoint refused (mismatch)", lines[1].text);
        assertEquals("source superviseLoop \u00b7 since 4999.250 s", lines[2].text);
        assertEquals("route empty", ScreenModel.causeWords(7));
        assertEquals("code 99", ScreenModel.causeWords(99));
    }

    @Test
    public void countersCountGapsAndContractProblemsAreShown() {
        final ObserverState s = live();
        s.onReceipt(mapped(health(5, NOW_MS - 30, 1, 0)), (NOW_MS - 20) * 1_000_000L);   // 2..4 missing
        assertEquals(3, s.sequenceGaps);
        final String counters = new ScreenModel(s, NOW_MS).footerLines()[0].text;
        assertTrue(counters, counters.startsWith("seq P 1 V 1 H 5 \u00b7 receipts 4 \u00b7 gaps 3"));
        s.onReceipt(new MessageMapper.Mapped(header(1, 2, NOW_MS), "schema_major_3", false), NOW_MS * 1_000_000L);
        final ScreenModel.Line bad = new ScreenModel(s, NOW_MS).footerLines()[0];
        assertTrue(bad.text, bad.text.startsWith("CONTRACT schema_major_3"));
        assertEquals(ScreenModel.C_FAULT, bad.color);
        // A receipt with a contract problem does not replace the shown plan.
        assertEquals(1, s.plan.sequence);
    }

    @Test
    public void gatewayErrorsAreShownWithTheirMessage() {
        final ObserverState s = new ObserverState();
        s.setLink("UNAVAILABLE", "initComms/discovery: google.sdv.gateway.ISdvGateway/default not declared"
                + " (statusCode 9: FAILED_PRECONDITION)");
        final ScreenModel m = new ScreenModel(s, NOW_MS);
        assertEquals("GATEWAY UNAVAILABLE", m.chip().text);
        final ScreenModel.Line e = m.errorLine();
        assertNotNull(e);
        // 121 characters: the line keeps its head and its tail (the status) and fits the header.
        assertTrue(e.text, e.text.startsWith("UNAVAILABLE: initComms/discovery: google.sdv.gateway.ISdvGateway/"));
        assertEquals(ScreenModel.ERROR_CHARS, e.text.length());
        assertTrue(ScreenLayout.fitsWidth(ScreenLayout.HEADER, e.text, e.size));
        assertTrue(e.text, e.text.endsWith("(statusCode 9: FAILED_PRECONDITION)"));
    }

    // ------------------------------------------------------------------ fit at 1080 x 600

    @Test
    public void everyLineFitsItsBoxAt1080x600WithWorstCaseValues() {
        for (ObserverState s : worstCases()) {
            for (long now : new long[] {NOW_MS, NOW_MS + 99_999_000L}) {
                final ScreenModel m = new ScreenModel(s, now);
                checkBox(ScreenLayout.MODE_BOX, m.modeLines());
                checkBox(ScreenLayout.SPEED_BOX, m.speedLines());
                checkBox(ScreenLayout.FACTS_BOX, m.factLines());
                checkBox(ScreenLayout.CLOCKS_BOX, m.clockLines());
                checkBox(ScreenLayout.FOOTER, m.footerLines());
                // Header: the title and the chip share the first row; the status line is the second.
                final ScreenModel.Line chip = m.chip();
                final float row = ScreenLayout.textWidth(ScreenModel.TITLE, ScreenLayout.TITLE) + 24f
                        + ScreenLayout.textWidth(chip.text, chip.size) + 16f;
                assertTrue("header row " + row, row <= ScreenLayout.HEADER.width);
                final ScreenModel.Line error = m.errorLine();
                final float[] sizes = error == null ? new float[] {ScreenLayout.TITLE}
                        : new float[] {ScreenLayout.TITLE, error.size};
                assertTrue(ScreenLayout.stackHeight(sizes, ScreenLayout.HEADER_PAD) <= ScreenLayout.HEADER.height);
                if (error != null) {
                    assertTrue(error.text, ScreenLayout.fitsWidth(ScreenLayout.HEADER, error.text, error.size));
                }
                final String absence = m.planAbsence();
                if (absence != null) {
                    assertTrue(absence, ScreenLayout.fitsWidth(ScreenLayout.PLAN_PLOT, absence, ScreenLayout.BODY));
                }
                final PlanGeometry g = PlanGeometry.fit(ScreenLayout.PLAN_PLOT.left, ScreenLayout.PLAN_PLOT.top,
                        ScreenLayout.PLAN_PLOT.width, ScreenLayout.PLAN_PLOT.height, null, null);
                final ScreenModel.Line caption = m.planCaption(g);
                assertTrue(caption.text, ScreenLayout.fitsWidth(ScreenLayout.PLAN, caption.text, caption.size));
                assertTrue(ScreenLayout.fitsWidth(ScreenLayout.PLAN, m.planTitle().text, m.planTitle().size));
            }
        }
    }

    @Test
    public void boxesStayOnTheScreenAndDoNotOverlap() {
        for (int i = 0; i < ScreenLayout.ALL.length; i++) {
            final ScreenLayout.Box a = ScreenLayout.ALL[i];
            assertTrue(a.left >= 0f && a.top >= 0f);
            assertTrue(a.right() <= ScreenLayout.REF_W && a.bottom() <= ScreenLayout.REF_H);
            for (int j = i + 1; j < ScreenLayout.ALL.length; j++) {
                assertTrue("boxes " + i + " and " + j + " overlap", ScreenLayout.disjoint(a, ScreenLayout.ALL[j]));
            }
        }
        // The plot and the panel's caption strips sit inside the plan box, one under the other.
        assertEquals(ScreenLayout.PLAN.top, ScreenLayout.PLAN_TITLE.top, 0f);
        assertEquals(ScreenLayout.PLAN_TITLE.bottom(), ScreenLayout.PLAN_PLOT.top, 0f);
        assertEquals(ScreenLayout.PLAN_PLOT.bottom(), ScreenLayout.PLAN_CAPTION.top, 0f);
        assertEquals(ScreenLayout.PLAN.bottom(), ScreenLayout.PLAN_CAPTION.bottom(), 0f);
    }

    @Test
    public void noTextIsSmallerThanTheMinimum() {
        for (ObserverState s : worstCases()) {
            final ScreenModel m = new ScreenModel(s, NOW_MS);
            for (ScreenModel.Line[] lines : new ScreenModel.Line[][] {
                    m.modeLines(), m.speedLines(), m.factLines(), m.clockLines(), m.footerLines()}) {
                for (ScreenModel.Line line : lines) {
                    assertTrue(line.text + " " + line.size, line.size >= ScreenLayout.MIN_TEXT);
                }
            }
        }
        assertTrue(ScreenLayout.NOTE >= ScreenLayout.MIN_TEXT);
        // The key values are large: mode 40 px, speed 30 px, clocks 21 px at 1080 x 600.
        assertTrue(ScreenLayout.MODE >= 40f && ScreenLayout.SPEED >= 30f && ScreenLayout.CLOCK >= 21f);
    }

    private static void checkBox(ScreenLayout.Box box, ScreenModel.Line[] lines) {
        final float[] sizes = new float[lines.length];
        for (int i = 0; i < lines.length; i++) {
            sizes[i] = lines[i].size;
            assertTrue("does not fit (" + ScreenLayout.textWidth(lines[i].text, lines[i].size) + " > "
                    + (box.width - 2f * ScreenLayout.PAD) + "): " + lines[i].text,
                    ScreenLayout.fitsWidth(box, lines[i].text, lines[i].size));
        }
        assertTrue("stack " + ScreenLayout.stackHeight(sizes) + " > " + box.height,
                ScreenLayout.stackHeight(sizes) <= box.height);
    }

    private static List<ObserverState> worstCases() {
        final List<ObserverState> out = new ArrayList<>();
        out.add(new ObserverState());
        out.add(live());
        final ObserverState big = new ObserverState();
        big.setLink("SUBSCRIBED", "instance1:de4sdv-driving-operational-state");
        final StateRecord.Fields h = health(4294967295L, NOW_MS, 2, 11);
        h.modeSource = "actuationAdapter";
        h.causeSinceMonoS = 4294967295L;
        h.causeSinceMonoNs = 999_999_999L;
        h.droppedSamples = 4294967295L;
        h.refusalReason = "mismatch";
        big.onReceipt(mapped(h), NOW_MS * 1_000_000L);
        final StateRecord.Fields v = vehicle(4294967295L, NOW_MS, -999.9f);
        v.sampleCaptureMs = 4294967295L;
        big.onReceipt(mapped(v), NOW_MS * 1_000_000L);
        final StateRecord.Fields p = plan(4294967295L, NOW_MS);
        p.planFrameIndex = 4294967295L;
        p.planCaptureMs = 4294967295L;
        p.planSampleCount = 4294967295L;
        p.planHorizonS = -99.9f;
        for (int i = 0; i < 64; i++) {
            p.planX[i] = -999.9f;
            p.planY[i] = -999.9f;
            p.planCurvature[i] = -9.999f;
        }
        big.onReceipt(mapped(p), NOW_MS * 1_000_000L);
        // App-side counters at 7 digits: 10^7 receipts are 3.8 days at the topic's ~30 Hz.
        // Message fields (u32) at their maximum.
        big.receipts = 9_999_999L;
        big.sequenceGaps = 9_999_999L;
        big.gatewayDataLoss = 9_999_999L;
        big.parseFailures = 9_999_999L;
        out.add(big);
        final ObserverState refused = live();
        final StateRecord.Fields r = health(3, NOW_MS, 4, 11);
        r.modeSource = "actuationAdapter";
        r.refusalReason = "no_pin";
        r.causeSinceMonoS = 4294967295L;
        refused.onReceipt(mapped(r), NOW_MS * 1_000_000L);
        refused.onReceipt(new MessageMapper.Mapped(header(2, 2, NOW_MS), "producer_empty", true), NOW_MS * 1_000_000L);
        refused.contractProblems = 9_999_999L;
        refused.allDefaultReceipts = 9_999_999L;
        refused.onError("read: INTERNAL: " + "x".repeat(300));
        out.add(refused);
        final ObserverState down = new ObserverState();
        down.setLink("UNAVAILABLE", "subscribe instance1:de4sdv-driving-operational-state: PERMISSION_DENIED: "
                + "y".repeat(300));
        out.add(down);
        return out;
    }

    private static List<String> allText(ScreenModel m) {
        final List<String> out = new ArrayList<>();
        out.add(ScreenModel.TITLE);
        out.add(m.chip().text);
        for (ScreenModel.Line[] lines : new ScreenModel.Line[][] {
                m.modeLines(), m.speedLines(), m.factLines(), m.clockLines(), m.footerLines()}) {
            for (ScreenModel.Line line : lines) {
                out.add(line.text);
            }
        }
        return out;
    }
}
