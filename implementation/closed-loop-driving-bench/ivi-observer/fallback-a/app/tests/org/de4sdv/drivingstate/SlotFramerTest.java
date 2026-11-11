// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// JVM test of the slot framer (no Android, no protobuf). Run on the build host:
//   m De4sdvDrivingStateSlotFramerTest
//   out/host/linux-x86/nativetest64/... or the java_test runner of the tree
package org.de4sdv.drivingstate;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;

import org.junit.Test;

public final class SlotFramerTest {

    @Test
    public void directPayloadIsFramedDirect() {
        final byte[] payload = {0x08, 0x01, 0x18, 0x01};
        final SlotFramer.Framed framed = SlotFramer.frame(payload);
        assertEquals(SlotFramer.Layout.DIRECT, framed.layout);
        assertEquals(0, framed.offset);
        assertEquals(4, framed.length);
        assertArrayEquals(payload,
                java.util.Arrays.copyOfRange(payload, framed.offset, framed.offset + framed.length));
    }

    @Test
    public void carrierWithZeroFillIsFramedAsCarrier() {
        final byte[] slot = {0x0A, 0x04, 0x08, 0x01, 0x18, 0x01, 0x00, 0x00, 0x00};
        final SlotFramer.Framed framed = SlotFramer.frame(slot);
        assertEquals(SlotFramer.Layout.CARRIER, framed.layout);
        assertEquals(2, framed.offset);
        assertEquals(4, framed.length);
    }

    @Test
    public void carrierWithoutFillIsFramedAsCarrier() {
        final byte[] slot = {0x0A, 0x04, 0x08, 0x01, 0x18, 0x01};
        final SlotFramer.Framed framed = SlotFramer.frame(slot);
        assertEquals(SlotFramer.Layout.CARRIER, framed.layout);
        assertEquals(2, framed.offset);
        assertEquals(4, framed.length);
    }

    @Test
    public void rawSlotWithLengthPrefixAndFillIsFramedAsSlot() {
        // length 6, 0x0A, length 4, payload, two bytes of fill
        final byte[] slot = {0x06, 0x0A, 0x04, 0x08, 0x01, 0x18, 0x01, 0x00, 0x00};
        final SlotFramer.Framed framed = SlotFramer.frame(slot);
        assertEquals(SlotFramer.Layout.SLOT, framed.layout);
        assertEquals("slot_length_prefix", framed.reason);
        assertEquals(3, framed.offset);
        assertEquals(4, framed.length);
    }

    @Test
    public void rawSlotWithBytesAfterTheFieldIsInvalid() {
        final byte[] slot = {0x06, 0x0A, 0x02, 0x08, 0x01, 0x7F};
        final SlotFramer.Framed framed = SlotFramer.frame(slot);
        assertEquals(SlotFramer.Layout.INVALID, framed.layout);
        assertEquals("slot_bytes_after_field", framed.reason);
    }

    @Test
    public void carrierLengthBeyondTheBytesIsInvalid() {
        final byte[] slot = {0x0A, 0x40, 0x08, 0x01};
        final SlotFramer.Framed framed = SlotFramer.frame(slot);
        assertEquals(SlotFramer.Layout.INVALID, framed.layout);
        assertEquals("carrier_length_exceeds_bytes", framed.reason);
    }

    @Test
    public void carrierBytesAfterTheFieldIsInvalid() {
        final byte[] slot = {0x0A, 0x02, 0x08, 0x01, 0x7F};
        final SlotFramer.Framed framed = SlotFramer.frame(slot);
        assertEquals(SlotFramer.Layout.INVALID, framed.layout);
        assertEquals("carrier_bytes_after_field", framed.reason);
    }

    @Test
    public void carrierZeroLengthIsInvalid() {
        final byte[] slot = {0x0A, 0x00, 0x00};
        final SlotFramer.Framed framed = SlotFramer.frame(slot);
        assertEquals(SlotFramer.Layout.INVALID, framed.layout);
    }

    @Test
    public void emptyIsEmpty() {
        assertEquals(SlotFramer.Layout.EMPTY, SlotFramer.frame(null).layout);
        assertEquals(SlotFramer.Layout.EMPTY, SlotFramer.frame(new byte[0]).layout);
    }

    @Test
    public void unexpectedFirstByteIsInvalid() {
        final SlotFramer.Framed framed = SlotFramer.frame(new byte[] {0x22, 0x01, 0x41});
        assertEquals(SlotFramer.Layout.INVALID, framed.layout);
        assertEquals("unexpected_first_byte_0x22", framed.reason);
    }

    @Test
    public void hexPrefixPrintsTheFirstBytes() {
        assertEquals("08 01 18", SlotFramer.hexPrefix(new byte[] {0x08, 0x01, 0x18, 0x7F}, 3));
    }
}
