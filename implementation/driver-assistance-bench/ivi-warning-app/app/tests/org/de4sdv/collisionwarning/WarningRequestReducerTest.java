// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// The warning request's edge logic (MAP-DRIVING-DA-WARNING-REQUEST: "a request starts with the
// first event that is true after one that is false"): what the presentation does with each
// typed message it reads, and which messages it refuses.
package org.de4sdv.collisionwarning;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class WarningRequestReducerTest {

    private static WarningRequestReducer.Verdict v(WarningRequestReducer r, long requested, long issueMs) {
        return r.onMessage(requested, issueMs).verdict;
    }

    @Test
    public void anEdgeFromFalseToTrueStartsARequest() {
        final WarningRequestReducer r = new WarningRequestReducer();
        assertEquals(WarningRequestReducer.Verdict.IDLE, v(r, 0, 50));
        final WarningRequestReducer.Outcome start = r.onMessage(1, 100);
        assertEquals(WarningRequestReducer.Verdict.START, start.verdict);
        assertEquals(1, start.request);
        assertTrue(start.verdict.shows());
        assertTrue(r.active());
    }

    @Test
    public void theFirstTrueAfterTheAppStartsIsAStart() {
        // Before its first message the app holds no request, as after a false event.
        final WarningRequestReducer r = new WarningRequestReducer();
        assertEquals(WarningRequestReducer.Verdict.START, v(r, 1, 0));
    }

    @Test
    public void aRepeatedTrueDoesNotShowAgain() {
        final WarningRequestReducer r = new WarningRequestReducer();
        r.onMessage(0, 50);
        assertEquals(WarningRequestReducer.Verdict.START, v(r, 1, 100));
        for (long t = 150; t <= 1000; t += 50) {
            final WarningRequestReducer.Outcome hold = r.onMessage(1, t);
            assertEquals(WarningRequestReducer.Verdict.HOLD, hold.verdict);
            assertFalse(hold.verdict.shows());
            assertEquals(1, hold.request);
        }
        assertEquals(1, r.requests());
    }

    @Test
    public void falseEndsTheRequestAndTheNextTrueStartsANewOne() {
        final WarningRequestReducer r = new WarningRequestReducer();
        r.onMessage(1, 100);
        final WarningRequestReducer.Outcome clear = r.onMessage(0, 150);
        assertEquals(WarningRequestReducer.Verdict.CLEAR, clear.verdict);
        assertEquals(1, clear.request);
        assertTrue(clear.verdict.clears());
        assertFalse(r.active());
        assertEquals(WarningRequestReducer.Verdict.IDLE, v(r, 0, 200));
        final WarningRequestReducer.Outcome again = r.onMessage(1, 250);
        assertEquals(WarningRequestReducer.Verdict.START, again.verdict);
        assertEquals(2, again.request);
    }

    @Test
    public void aRepeatedOrOlderIssueTimeIsStaleAndChangesNothing() {
        final WarningRequestReducer r = new WarningRequestReducer();
        r.onMessage(1, 100);
        // The same plan again and an older one.
        assertEquals(WarningRequestReducer.Verdict.STALE, v(r, 1, 100));
        assertEquals(WarningRequestReducer.Verdict.STALE, v(r, 0, 100));
        assertEquals(WarningRequestReducer.Verdict.STALE, v(r, 0, 50));
        assertTrue(r.active());
        assertEquals(100, r.lastIssueTimeSimMs());
        assertEquals(WarningRequestReducer.Verdict.HOLD, v(r, 1, 150));
    }

    @Test
    public void aStaleTrueAfterAClearDoesNotShowAgain() {
        final WarningRequestReducer r = new WarningRequestReducer();
        r.onMessage(1, 100);
        r.onMessage(0, 150);
        assertEquals(WarningRequestReducer.Verdict.STALE, v(r, 1, 120));
        assertFalse(r.active());
        assertEquals(1, r.requests());
    }

    @Test
    public void aRequestedValueOtherThanZeroOrOneIsMalformedAndChangesNothing() {
        final WarningRequestReducer r = new WarningRequestReducer();
        final WarningRequestReducer.Outcome bad = r.onMessage(2, 100);
        assertEquals(WarningRequestReducer.Verdict.MALFORMED, bad.verdict);
        assertFalse(bad.verdict.shows());
        assertTrue(bad.reason.contains("requested=2"));
        // u32 0xFFFFFFFF as the unsigned value of protobuf's int.
        assertEquals(WarningRequestReducer.Verdict.MALFORMED, v(r, 0xFFFFFFFFL, 120));
        assertFalse(r.active());
        // A malformed message does not move the issue time: the same time is still fresh.
        assertEquals(-1, r.lastIssueTimeSimMs());
        assertEquals(WarningRequestReducer.Verdict.START, v(r, 1, 100));
    }

    @Test
    public void anIssueTimeOutsideUint32IsMalformed() {
        final WarningRequestReducer r = new WarningRequestReducer();
        assertEquals(WarningRequestReducer.Verdict.MALFORMED, v(r, 1, -1));
        assertEquals(WarningRequestReducer.Verdict.MALFORMED, v(r, 1, 0x1_0000_0000L));
        assertEquals(WarningRequestReducer.Verdict.START, v(r, 1, 0xFFFFFFFFL));
    }

    @Test
    public void countsAreKeptPerVerdict() {
        final WarningRequestReducer r = new WarningRequestReducer();
        r.onMessage(0, 50);   // IDLE
        r.onMessage(1, 100);  // START
        r.onMessage(1, 150);  // HOLD
        r.onMessage(1, 150);  // STALE
        r.onMessage(7, 200);  // MALFORMED
        r.onMessage(0, 250);  // CLEAR
        assertEquals(1, r.count(WarningRequestReducer.Verdict.IDLE));
        assertEquals(1, r.count(WarningRequestReducer.Verdict.START));
        assertEquals(1, r.count(WarningRequestReducer.Verdict.HOLD));
        assertEquals(1, r.count(WarningRequestReducer.Verdict.STALE));
        assertEquals(1, r.count(WarningRequestReducer.Verdict.MALFORMED));
        assertEquals(1, r.count(WarningRequestReducer.Verdict.CLEAR));
    }
}
