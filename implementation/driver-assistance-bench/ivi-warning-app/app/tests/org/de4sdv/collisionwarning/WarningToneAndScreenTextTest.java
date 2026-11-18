// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// The sound's samples and the screen's text. Expected numbers are derived here from the
// parameters by hand arithmetic (48000 Hz x 150 ms = 7200 samples on, x 100 ms = 4800 off;
// a 2000 Hz sine crosses zero twice per period: 2 x 2000 x 0.150 = 600 crossings).
package org.de4sdv.collisionwarning;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import org.junit.Test;

public class WarningToneAndScreenTextTest {

    @Test
    public void thePatternIsOneBeepAndOnePause() {
        final short[] s = WarningTone.pattern();
        assertEquals(7200 + 4800, s.length);
        for (int i = 7200; i < s.length; i++) {
            assertEquals("pause sample " + i, 0, s[i]);
        }
        int peak = 0;
        for (int i = 0; i < 7200; i++) {
            peak = Math.max(peak, Math.abs(s[i]));
        }
        // amplitude 0.5 of full scale, reached away from the ramps
        assertTrue("peak " + peak, peak <= Math.round(0.5 * Short.MAX_VALUE) && peak > 16000);
    }

    @Test
    public void theBeepHasTheToneFrequency() {
        final short[] s = WarningTone.pattern();
        int crossings = 0;
        for (int i = 1; i < 7200; i++) {
            if ((s[i - 1] < 0 && s[i] >= 0) || (s[i - 1] >= 0 && s[i] < 0)) {
                crossings++;
            }
        }
        assertTrue("crossings " + crossings, Math.abs(crossings - 600) <= 4);
    }

    @Test
    public void theBeepStartsAndEndsAtSilence() {
        final short[] s = WarningTone.pattern();
        assertEquals(0, s[0]);
        assertEquals(0, s[7199]);
        // the ramp: the first 5 ms (240 samples) stay below the full amplitude's envelope
        for (int i = 0; i < 240; i++) {
            assertTrue("ramp sample " + i, Math.abs(s[i]) <= Math.ceil(0.5 * Short.MAX_VALUE * i / 240.0) + 1);
        }
    }

    @Test
    public void badParametersAreRefused() {
        final int[][] bad = {{0, 2000, 150, 100}, {48000, 24000, 150, 100}, {48000, 2000, 0, 100}, {48000, 2000, 150, -1}};
        for (int[] p : bad) {
            try {
                WarningTone.pattern(p[0], p[1], p[2], p[3], 0.5, 5);
                fail("expected a refusal for " + java.util.Arrays.toString(p));
            } catch (IllegalArgumentException expected) {
                // refused
            }
        }
        try {
            WarningTone.pattern(48000, 2000, 150, 100, 1.5, 5);
            fail("expected a refusal of amplitude 1.5");
        } catch (IllegalArgumentException expected) {
            // refused
        }
    }

    @Test
    public void theScreenTextIsPinnedWhole() {
        assertEquals("COLLISION WARNING", ScreenText.WARNING_TITLE);
        assertEquals("BRAKE", ScreenText.WARNING_ACTION);
        assertEquals("No collision warning", ScreenText.IDLE_TITLE);
        assertEquals("warning request topic: SUBSCRIBED   received 12   requests 2   refused 1",
                ScreenText.status("SUBSCRIBED", 12, 2, 1));
    }
}
