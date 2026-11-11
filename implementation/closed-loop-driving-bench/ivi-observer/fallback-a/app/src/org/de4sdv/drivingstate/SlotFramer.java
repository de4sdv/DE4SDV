// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// Locates the de4sdv.driving.v1.DrivingOperationalState message inside the
// bytes that the SDV Gateway delivers for the SOME/IP broker's bytes
// publication (topic de4sdv-driving-operational-state, type
// com.android.sdv.someip.De4sdvDrivingOperationalStateFrame, bytes data = 1).
//
// Three layouts are possible on this path and the observer must name the one it
// saw, because only one of them is expected and the others are diagnostics:
//
//   DIRECT   the payload the broker forwarded, unchanged: the protobuf of
//            DrivingOperationalState. The S-CORE publisher always writes
//            schema_major = 1 first, so the payload starts 0x08 0x01.
//            This is the expected layout.
//   CARRIER  the carrier's own field framing is still around the payload --
//            0x0A, a varint length, the payload -- optionally followed by the
//            broker's zero fill to the slot size. The AEBS frame relay parsed
//            exactly this envelope off the raw C API (broker_wrapper.cpp), so it
//            is what a raw slot holds; a typed subscriber should not see it.
//   SLOT     the raw queue slot: a varint message length first, then the
//            carrier envelope, then the broker's zero fill. The AEBS frame
//            relay's C API read exactly this (broker_wrapper.cpp); a typed
//            subscriber should not see it, and if it does, the reason is named
//            "slot_length_prefix" so the framing question is answered by the
//            record rather than guessed at.
//   INVALID  none of the three; the record carries the first bytes in hex so
//            the cause is visible in the log instead of guessed.
//
// No Android and no protobuf import: this class is JVM-testable as it stands
// (app/tests/org/de4sdv/drivingstate/SlotFramerTest.java).
package org.de4sdv.drivingstate;

final class SlotFramer {

    enum Layout {
        DIRECT,
        CARRIER,
        SLOT,
        EMPTY,
        INVALID
    }

    static final class Framed {
        final Layout layout;
        final int offset;
        final int length;
        final String reason;

        private Framed(Layout layout, int offset, int length, String reason) {
            this.layout = layout;
            this.offset = offset;
            this.length = length;
            this.reason = reason;
        }

        static Framed direct(int length) {
            return new Framed(Layout.DIRECT, 0, length, "ok");
        }

        static Framed carrier(int offset, int length) {
            return new Framed(Layout.CARRIER, offset, length, "carrier_envelope");
        }

        static Framed empty() {
            return new Framed(Layout.EMPTY, 0, 0, "empty");
        }

        static Framed slot(int offset, int length) {
            return new Framed(Layout.SLOT, offset, length, "slot_length_prefix");
        }

        static Framed invalid(String reason) {
            return new Framed(Layout.INVALID, 0, 0, reason);
        }
    }

    /** The tag byte of field 1 of DrivingOperationalState: field 1, varint. */
    private static final int kSchemaMajorTag = 0x08;
    /** The tag byte of field 1 of the carrier: field 1, length-delimited. */
    private static final int kCarrierDataTag = 0x0A;

    private SlotFramer() {}

    static Framed frame(byte[] bytes) {
        if (bytes == null || bytes.length == 0) {
            return Framed.empty();
        }
        final int first = bytes[0] & 0xFF;

        if (first == kCarrierDataTag) {
            long[] varint = readVarint(bytes, 1);
            if (varint == null) {
                return Framed.invalid("carrier_length_varint_invalid");
            }
            final long payloadBytes = varint[0];
            final int payloadOffset = (int) varint[1];
            if (payloadBytes <= 0) {
                return Framed.invalid("carrier_length_zero");
            }
            if (payloadOffset + payloadBytes > bytes.length) {
                return Framed.invalid("carrier_length_exceeds_bytes");
            }
            final int end = (int) (payloadOffset + payloadBytes);
            if (!allZero(bytes, end)) {
                return Framed.invalid("carrier_bytes_after_field");
            }
            return Framed.carrier(payloadOffset, (int) payloadBytes);
        }

        // A raw slot: a varint message length, then the carrier envelope.
        if (first != kCarrierDataTag && first != kSchemaMajorTag) {
            final long[] slotLength = readVarint(bytes, 0);
            if (slotLength != null) {
                final long messageBytes = slotLength[0];
                final int messageStart = (int) slotLength[1];
                if (messageBytes > 0 && messageStart + messageBytes <= bytes.length
                        && (bytes[messageStart] & 0xFF) == kCarrierDataTag) {
                    final long messageEnd = messageStart + messageBytes;
                    final long[] inner = readVarint(bytes, messageStart + 1);
                    if (inner != null && inner[0] > 0 && inner[1] + inner[0] <= messageEnd) {
                        final int payloadOffset = (int) inner[1];
                        final int end = (int) (payloadOffset + inner[0]);
                        if (allZero(bytes, end)) {
                            return Framed.slot(payloadOffset, (int) inner[0]);
                        }
                        return Framed.invalid("slot_bytes_after_field");
                    }
                    return Framed.invalid("slot_inner_envelope_invalid");
                }
            }
        }

        if (first == kSchemaMajorTag) {
            // The publisher writes schema_major = 1 (ICD section 3); a payload
            // that starts with the tag but not the value is still handed to the
            // parser, which reports the field-level problem.
            return Framed.direct(bytes.length);
        }

        return Framed.invalid("unexpected_first_byte_0x" + Integer.toHexString(first));
    }

    /**
     * Reads the varint at {@code start}. Returns {value, nextOffset}, or null
     * when it is truncated, longer than five bytes, or above 2^32 - 1.
     */
    private static long[] readVarint(byte[] bytes, int start) {
        long value = 0;
        for (int index = 0; index < 5; index++) {
            final int position = start + index;
            if (position >= bytes.length) {
                return null;
            }
            final int b = bytes[position] & 0xFF;
            value |= ((long) (b & 0x7F)) << (7 * index);
            if ((b & 0x80) == 0) {
                if (value > 0xFFFFFFFFL) {
                    return null;
                }
                return new long[] {value, position + 1L};
            }
        }
        return null;
    }

    private static boolean allZero(byte[] bytes, int from) {
        for (int index = from; index < bytes.length; index++) {
            if (bytes[index] != 0) {
                return false;
            }
        }
        return true;
    }

    /** The first bytes in hex, for a record's failure line. */
    static String hexPrefix(byte[] bytes, int limit) {
        if (bytes == null) {
            return "";
        }
        final StringBuilder text = new StringBuilder();
        final int count = Math.min(bytes.length, limit);
        for (int index = 0; index < count; index++) {
            if (index > 0) {
                text.append(' ');
            }
            text.append(String.format("%02x", bytes[index] & 0xFF));
        }
        return text.toString();
    }
}
