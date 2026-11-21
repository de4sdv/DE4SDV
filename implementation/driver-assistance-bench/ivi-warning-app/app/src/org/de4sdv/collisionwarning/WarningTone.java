// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// The warning sound's samples: one period of a beep pattern, looped by the AudioTrack while
// a request is shown. 16-bit mono PCM, a sine at TONE_HZ for ON_MS, then silence for OFF_MS,
// with a short linear ramp at both ends of the beep so the loop does not click.
// The pattern is the bench's choice; the model asks for a warning sound, not for its form.
package org.de4sdv.collisionwarning;

final class WarningTone {

    static final int SAMPLE_RATE = 48000;
    static final int TONE_HZ = 2000;
    static final int ON_MS = 150;
    static final int OFF_MS = 100;
    static final double AMPLITUDE = 0.5;
    static final int RAMP_MS = 5;

    private WarningTone() {}

    static short[] pattern() {
        return pattern(SAMPLE_RATE, TONE_HZ, ON_MS, OFF_MS, AMPLITUDE, RAMP_MS);
    }

    static short[] pattern(int sampleRate, int toneHz, int onMs, int offMs, double amplitude, int rampMs) {
        if (sampleRate <= 0 || toneHz <= 0 || onMs <= 0 || offMs < 0 || rampMs < 0) {
            throw new IllegalArgumentException("non-positive tone parameter");
        }
        if (amplitude <= 0 || amplitude > 1) {
            throw new IllegalArgumentException("amplitude outside (0, 1]: " + amplitude);
        }
        if (2 * toneHz >= sampleRate) {
            throw new IllegalArgumentException("tone at or above the Nyquist frequency");
        }
        final int on = sampleRate * onMs / 1000;
        final int off = sampleRate * offMs / 1000;
        final int ramp = Math.min(sampleRate * rampMs / 1000, on / 2);
        final short[] samples = new short[on + off];
        for (int i = 0; i < on; i++) {
            double gain = amplitude;
            if (ramp > 0 && i < ramp) {
                gain *= (double) i / ramp;
            } else if (ramp > 0 && i >= on - ramp) {
                gain *= (double) (on - 1 - i) / ramp;
            }
            samples[i] = (short) Math.round(gain * Short.MAX_VALUE * Math.sin(2 * Math.PI * toneHz * i / sampleRate));
        }
        return samples;
    }
}
