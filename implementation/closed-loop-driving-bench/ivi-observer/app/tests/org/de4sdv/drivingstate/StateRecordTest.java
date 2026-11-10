// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// JVM test of the record builder: no Android, no protobuf, no device.
//
// It holds the record to ICD v2 section 6 and to the section 3 field order, which
// is the half of the app that is worth testing off the VM: if a field is renamed,
// dropped or reordered here, the evaluators silently read nothing, and a runtime
// check on the guest cannot tell that apart from a quiet car.
//
// Run in the tree:   m De4sdvDrivingStateObserverTests, then JUnitCore (RUNBOOK step 8)
// Run anywhere else: javac StateRecord.java StateRecordTest.java && java ...
package org.de4sdv.drivingstate;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.util.Arrays;
import java.util.List;

public class StateRecordTest {

    /** The 43 ICD names, in ICD section 3 order. */
    private static final List<String> ICD_FIELDS = Arrays.asList(
            "schema_major", "schema_minor", "kind", "sequence", "producer",
            "publish_real_s", "publish_real_ns", "publish_mono_s", "publish_mono_ns",
            "plan_frame_index", "plan_capture_ms", "plan_production_mono_s",
            "plan_production_mono_ns", "plan_reference", "run_record", "plan_producer",
            "plan_sample_count", "plan_horizon_s", "plan_acceleration", "plan_curvature",
            "plan_x", "plan_y",
            "speed_kmh", "longitudinal_acceleration", "lateral_acceleration", "yaw_rate_dps",
            "sample_capture_ms", "sample_receipt_mono_s", "sample_receipt_mono_ns",
            "mode", "cause", "mode_source", "cause_since_mono_s", "cause_since_mono_ns",
            "last_plan_frame_index", "last_plan_capture_ms", "step_capture_ms",
            "last_plan_production_mono_s", "last_plan_production_mono_ns", "dropped_samples",
            "checkpoint_expected_sha256", "checkpoint_actual_sha256", "refusal_reason");

    private static StateRecord.Fields planFields() {
        final StateRecord.Fields f = new StateRecord.Fields();
        f.schemaMajor = 2;
        f.kind = 1;
        f.sequence = 7;
        f.producer = "statePublisher";
        f.publishRealS = 1762742400L;
        f.publishRealNs = 123456789L;
        f.planFrameIndex = 1234;
        f.planCaptureMs = 123400;
        f.planReference = "0123456789abcdef/1234";
        f.runRecord = "0123456789abcdef";
        f.planSampleCount = 64;
        f.planX = new float[64];
        f.planY = new float[64];
        for (int index = 0; index < 64; index++) {
            f.planX[index] = 0.75f * index;
            f.planY[index] = -0.125f * index;
        }
        return f;
    }

    @Test
    public void allFortyThreeFieldsAreInTheRecordInIcdOrder() {
        final String data = StateRecord.data(planFields());
        int previous = -1;
        for (String name : ICD_FIELDS) {
            final int at = data.indexOf("\"" + name + "\":");
            assertTrue("missing field " + name, at >= 0);
            assertTrue("field " + name + " is out of ICD order", at > previous);
            previous = at;
        }
        // The record adds only these two, and they are labelled as such.
        assertTrue(data.contains("\"kind_name\":\"PLAN\""));
        assertTrue(data.contains("\"clocks\":"));
    }

    @Test
    public void clocksCoverEveryTimeField() {
        for (String name : ICD_FIELDS) {
            final boolean time = name.endsWith("_ms") || name.endsWith("_mono_s")
                    || name.endsWith("_mono_ns") || name.endsWith("_real_s")
                    || name.endsWith("_real_ns");
            if (!time) {
                continue;
            }
            assertTrue("no clock for " + name,
                    StateRecord.CLOCKS_JSON.contains("\"" + name + "\":"));
        }
        assertTrue(StateRecord.CLOCKS_JSON.contains("\"sample_capture_ms\":\"simulation\""));
        assertTrue(StateRecord.CLOCKS_JSON.contains("\"publish_real_s\":\"real\""));
        assertTrue(StateRecord.CLOCKS_JSON.contains("\"publish_mono_s\":\"monotonic\""));
    }

    @Test
    public void valuesAreTranscribedNotReshaped() {
        final StateRecord.Fields f = planFields();
        final String data = StateRecord.data(f);
        assertTrue(data.contains("\"plan_capture_ms\":123400"));
        assertTrue(data.contains("\"plan_frame_index\":1234"));
        assertTrue(data.contains("\"publish_real_s\":1762742400"));
        assertTrue(data.contains("\"publish_real_ns\":123456789"));
        assertTrue(data.contains("\"plan_reference\":\"0123456789abcdef/1234\""));
        assertEquals(1, countOccurrences(data, "\"plan_x\":["));
        // The arrays are written in full, 64 values each, and every value reads
        // back to the same float32 (StateRecord writes 9 significant digits,
        // "%.9g", which round-trips any float exactly; the previous version of this test
        // expected the shortest form "0,0.75,1.5", which the code never wrote).
        final float[] x = floatArray(data, "plan_x");
        final float[] y = floatArray(data, "plan_y");
        assertEquals(64, x.length);
        assertEquals(64, y.length);
        for (int i = 0; i < 64; i++) {
            assertEquals("plan_x[" + i + "]", Float.floatToIntBits(f.planX[i]), Float.floatToIntBits(x[i]));
            assertEquals("plan_y[" + i + "]", Float.floatToIntBits(f.planY[i]), Float.floatToIntBits(y[i]));
        }
        assertTrue(data.contains("\"plan_x\":[0.00000000,0.750000000,1.50000000,"));
    }

    @Test
    public void nonFiniteIsJsonNull() {
        final StateRecord.Fields f = planFields();
        f.speedKmh = Float.NaN;
        f.lateralAcceleration = Float.POSITIVE_INFINITY;
        final String data = StateRecord.data(f);
        assertTrue(data.contains("\"speed_kmh\":null"));
        assertTrue(data.contains("\"lateral_acceleration\":null"));
        assertTrue(!data.contains("NaN"));
    }

    @Test
    public void unsignedValuesAboveTwoPow31StayPositive() {
        final StateRecord.Fields f = planFields();
        f.planFrameIndex = 4000000000L;   // > Integer.MAX_VALUE, a legal uint32
        assertTrue(StateRecord.data(f).contains("\"plan_frame_index\":4000000000"));
    }

    @Test
    public void stringsAreEscaped() {
        assertEquals("a\\\"b\\\\c\\nd", StateRecord.quote("a\"b\\c\nd"));
    }

    @Test
    public void envelopeCarriesTheSectionSixKeys() {
        final String line = StateRecord.line(123456789L, 1762742400123000000L, 9, planFields());
        for (String key : new String[] {"\"t_mono_ns\":", "\"t_real_ns\":", "\"host\":\"guest\"",
                "\"component\":\"observer\"", "\"event\":\"in.operational_state\"",
                "\"seq\":9", "\"data\":{"}) {
            assertTrue("missing " + key, line.contains(key));
        }
        assertTrue(line.endsWith("}}"));
    }

    private static int countOccurrences(String haystack, String needle) {
        int count = 0;
        int at = haystack.indexOf(needle);
        while (at >= 0) {
            count++;
            at = haystack.indexOf(needle, at + 1);
        }
        return count;
    }

    private static float[] floatArray(String data, String name) {
        final int start = data.indexOf("\"" + name + "\":[") + name.length() + 4;
        final int end = data.indexOf(']', start);
        final String[] parts = data.substring(start, end).split(",");
        final float[] out = new float[parts.length];
        for (int i = 0; i < parts.length; i++) {
            out[i] = Float.parseFloat(parts[i]);
        }
        return out;
    }

    /** Runs without JUnit, for a host that only has a JDK. */
    public static void main(String[] args) {
        final StateRecordTest test = new StateRecordTest();
        test.allFortyThreeFieldsAreInTheRecordInIcdOrder();
        test.clocksCoverEveryTimeField();
        test.valuesAreTranscribedNotReshaped();
        test.nonFiniteIsJsonNull();
        test.unsignedValuesAboveTwoPow31StayPositive();
        test.stringsAreEscaped();
        test.envelopeCarriesTheSectionSixKeys();
        System.out.println("StateRecordTest: 7 checks passed");
    }
}
