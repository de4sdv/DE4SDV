// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// The record format: both clocks on every line, the fields in the order given, strings quoted,
// and the same content in the JSONL line and the logcat line.
package org.de4sdv.collisionwarning;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import org.junit.Test;

public class WarningRecordTest {

    @Test
    public void aReceiptLineCarriesBothClocksAndTheMessage() {
        assertEquals("{\"event\":\"receipt\",\"t_mono_ns\":123456789,\"t_real_ns\":1763500000123000000,"
                        + "\"seq\":4,\"requested\":1,\"issue_time_sim_ms\":12350,\"verdict\":\"START\",\"request\":1}",
                WarningRecord.json(123456789L, 1763500000123000000L, "receipt",
                        "seq", 4L, "requested", 1L, "issue_time_sim_ms", 12350L, "verdict", "START", "request", 1L));
        assertEquals("event=receipt t_mono_ns=123456789 t_real_ns=1763500000123000000 seq=4 requested=1"
                        + " issue_time_sim_ms=12350 verdict=START request=1",
                WarningRecord.logcat(123456789L, 1763500000123000000L, "receipt",
                        "seq", 4L, "requested", 1L, "issue_time_sim_ms", 12350L, "verdict", "START", "request", 1L));
    }

    @Test
    public void stringsWithSpacesOrQuotesAreQuoted() {
        assertEquals("{\"event\":\"error\",\"t_mono_ns\":1,\"t_real_ns\":2,\"reason\":\"parse: \\\"bad\\\"\\n\"}",
                WarningRecord.json(1, 2, "error", "reason", "parse: \"bad\"\n"));
        assertEquals("event=error t_mono_ns=1 t_real_ns=2 reason=\"parse: \\\"bad\\\"\" empty=\"\"",
                WarningRecord.logcat(1, 2, "error", "reason", "parse: \"bad\"", "empty", ""));
    }

    @Test
    public void booleansAndNumbersAreBareInJson() {
        assertEquals("{\"event\":\"sound_timestamp\",\"t_mono_ns\":5,\"t_real_ns\":6,\"ok\":true,\"since_receipt_ns\":-3}",
                WarningRecord.json(5, 6, "sound_timestamp", "ok", true, "since_receipt_ns", -3L));
    }

    @Test
    public void controlCharactersAreEscaped() {
        assertEquals("a\\u0001b\\tc", WarningRecord.quote("a\u0001b\tc"));
    }

    @Test
    public void anOddNumberOfItemsIsRefused() {
        try {
            WarningRecord.json(1, 2, "receipt", "seq");
            fail("expected IllegalArgumentException");
        } catch (IllegalArgumentException expected) {
            assertTrue(expected.getMessage().contains("pairs"));
        }
        try {
            WarningRecord.logcat(1, 2, "receipt", 3, 4);
            fail("expected IllegalArgumentException");
        } catch (IllegalArgumentException expected) {
            assertTrue(expected.getMessage().contains("String"));
        }
    }

    @Test
    public void theTagAndFileAreTheOnesTheScriptsRead() {
        assertEquals("DE4SDV_COLLISION_WARNING", WarningRecord.TAG);
        assertEquals("warning.jsonl", WarningRecord.FILE);
    }
}
