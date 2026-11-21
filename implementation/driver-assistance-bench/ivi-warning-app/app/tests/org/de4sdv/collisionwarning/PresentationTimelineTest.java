// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// Each moment of a request is logged once: a second frame drawn with the same warning, a
// repeated true and a mark of an ended or older request log nothing.
package org.de4sdv.collisionwarning;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class PresentationTimelineTest {

    @Test
    public void eachMarkIsTrueOncePerRequest() {
        final PresentationTimeline t = new PresentationTimeline();
        t.onStart(1, 1_000L);
        for (PresentationTimeline.Mark mark : PresentationTimeline.Mark.values()) {
            assertTrue(mark.name(), t.mark(mark, 1));
            assertFalse(mark.name() + " again", t.mark(mark, 1));
        }
    }

    @Test
    public void nothingIsMarkedBeforeAStartOrAfterTheClear() {
        final PresentationTimeline t = new PresentationTimeline();
        assertFalse(t.mark(PresentationTimeline.Mark.DRAWN, 0));
        assertFalse(t.mark(PresentationTimeline.Mark.DRAWN, 1));
        t.onStart(1, 0);
        t.onClear(1);
        assertFalse(t.mark(PresentationTimeline.Mark.DRAWN, 1));
        assertEquals(0, t.currentRequest());
    }

    @Test
    public void aNewRequestIsMarkedAfreshAndTheOldOneNoMore() {
        final PresentationTimeline t = new PresentationTimeline();
        t.onStart(1, 0);
        assertTrue(t.mark(PresentationTimeline.Mark.SOUND_PLAY, 1));
        t.onClear(1);
        t.onStart(2, 500L);
        assertFalse(t.mark(PresentationTimeline.Mark.SOUND_PLAY, 1));
        assertTrue(t.mark(PresentationTimeline.Mark.SOUND_PLAY, 2));
        assertEquals(2, t.currentRequest());
    }

    @Test
    public void aClearOfAnOlderRequestDoesNotEndTheCurrentOne() {
        final PresentationTimeline t = new PresentationTimeline();
        t.onStart(2, 0);
        t.onClear(1);
        assertTrue(t.mark(PresentationTimeline.Mark.COMMITTED, 2));
    }

    @Test
    public void isMarkedFollowsTheCurrentRequestOnly() {
        final PresentationTimeline t = new PresentationTimeline();
        t.onStart(1, 0);
        assertFalse(t.isMarked(PresentationTimeline.Mark.DRAWN, 1));
        t.mark(PresentationTimeline.Mark.DRAWN, 1);
        assertTrue(t.isMarked(PresentationTimeline.Mark.DRAWN, 1));
        assertFalse(t.isMarked(PresentationTimeline.Mark.DRAWN, 2));
        t.onStart(2, 10);
        assertFalse(t.isMarked(PresentationTimeline.Mark.DRAWN, 2));
        assertFalse(t.isMarked(PresentationTimeline.Mark.DRAWN, 1));
    }

    @Test
    public void timeSinceReceiptIsOnTheMonotonicClock() {
        final PresentationTimeline t = new PresentationTimeline();
        t.onStart(1, 5_000_000_000L);
        assertEquals(42_000_000L, t.sinceReceiptNs(5_042_000_000L));
    }

    @Test
    public void theEventNamesAreTheOnesTheReadmeLists() {
        assertEquals("display_drawn", PresentationTimeline.Mark.DRAWN.event);
        assertEquals("display_committed", PresentationTimeline.Mark.COMMITTED.event);
        assertEquals("sound_play_called", PresentationTimeline.Mark.SOUND_PLAY.event);
        assertEquals("sound_head_moved", PresentationTimeline.Mark.SOUND_HEAD.event);
        assertEquals("sound_timestamp", PresentationTimeline.Mark.SOUND_TIMESTAMP.event);
    }
}
