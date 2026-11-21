// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// The record of the warning presentation: one JSONL line per event in
// files/warning.jsonl and the same content as one logcat line under DE4SDV_COLLISION_WARNING.
// The model asks the application to log the receipt, the displayed frame and the start of the
// sound with their times for phase 10 (CollisionWarningPresentationApplication).
//
// Every line carries the IVI VM's two clocks:
//   t_mono_ns  CLOCK_MONOTONIC of the IVI VM (System.nanoTime on Android), for differences on
//              this VM: receipt to displayed frame, receipt to sound;
//   t_real_ns  the IVI VM's real time at millisecond granularity (System.currentTimeMillis * 1e6),
//              for the cross-host path share against the publisher's send. The guest clock
//              free-runs: the session sets it immediately before each window and carries the bound.
// The app computes no cross-host latency.
//
// No Android import: a plain JVM test pins the format.
package org.de4sdv.collisionwarning;

final class WarningRecord {

    static final String TAG = "DE4SDV_COLLISION_WARNING";
    static final String FILE = "warning.jsonl";

    private WarningRecord() {}

    /** One JSONL line: {"event":..,"t_mono_ns":..,"t_real_ns":..,<key>:<value>...}. */
    static String json(long monoNs, long realNs, String event, Object... keyValues) {
        checkPairs(keyValues);
        final StringBuilder line = new StringBuilder(160);
        line.append("{\"event\":\"").append(quote(event)).append('"');
        line.append(",\"t_mono_ns\":").append(monoNs);
        line.append(",\"t_real_ns\":").append(realNs);
        for (int i = 0; i < keyValues.length; i += 2) {
            line.append(",\"").append(quote((String) keyValues[i])).append("\":");
            final Object value = keyValues[i + 1];
            if (value instanceof Number || value instanceof Boolean) {
                line.append(value);
            } else {
                line.append('"').append(quote(String.valueOf(value))).append('"');
            }
        }
        return line.append('}').toString();
    }

    /** The same content as one logcat line: event=<e> t_mono_ns=.. t_real_ns=.. key=value ... */
    static String logcat(long monoNs, long realNs, String event, Object... keyValues) {
        checkPairs(keyValues);
        final StringBuilder line = new StringBuilder(160);
        line.append("event=").append(event);
        line.append(" t_mono_ns=").append(monoNs);
        line.append(" t_real_ns=").append(realNs);
        for (int i = 0; i < keyValues.length; i += 2) {
            line.append(' ').append(keyValues[i]).append('=');
            final String value = String.valueOf(keyValues[i + 1]);
            if (value.isEmpty() || value.indexOf(' ') >= 0 || value.indexOf('"') >= 0) {
                line.append('"').append(quote(value)).append('"');
            } else {
                line.append(value);
            }
        }
        return line.toString();
    }

    static String quote(String text) {
        final StringBuilder out = new StringBuilder(text.length() + 8);
        for (int i = 0; i < text.length(); i++) {
            final char c = text.charAt(i);
            switch (c) {
                case '"':
                    out.append("\\\"");
                    break;
                case '\\':
                    out.append("\\\\");
                    break;
                case '\n':
                    out.append("\\n");
                    break;
                case '\r':
                    out.append("\\r");
                    break;
                case '\t':
                    out.append("\\t");
                    break;
                default:
                    if (c < 0x20) {
                        out.append(String.format(java.util.Locale.US, "\\u%04x", (int) c));
                    } else {
                        out.append(c);
                    }
            }
        }
        return out.toString();
    }

    private static void checkPairs(Object[] keyValues) {
        if (keyValues.length % 2 != 0) {
            throw new IllegalArgumentException("key/value pairs expected, got " + keyValues.length + " items");
        }
        for (int i = 0; i < keyValues.length; i += 2) {
            if (!(keyValues[i] instanceof String)) {
                throw new IllegalArgumentException("key " + i / 2 + " is not a String");
            }
        }
    }
}
