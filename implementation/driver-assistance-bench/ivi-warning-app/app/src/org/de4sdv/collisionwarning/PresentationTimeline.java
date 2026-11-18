// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// Which moments of one warning request the presentation logs, each once per request:
// the receipt that started it, the first frame drawn with the warning, the first frame
// committed to the display's swap chain, the call that starts the sound, and the sound's
// first evidence of playing. The model's budget of 0.1 s runs from the receipt to the first
// displayed frame and to the start of the sound (CollisionWarningPresentationApplication);
// the app logs the times, it judges nothing.
//
// Synchronized: the UI thread marks the frames, the sound thread marks the sound.
package org.de4sdv.collisionwarning;

final class PresentationTimeline {

    enum Mark {
        DRAWN("display_drawn"),
        COMMITTED("display_committed"),
        SOUND_PLAY("sound_play_called"),
        SOUND_HEAD("sound_head_moved"),
        SOUND_TIMESTAMP("sound_timestamp");

        final String event;

        Mark(String event) {
            this.event = event;
        }
    }

    private long request;
    private long receiptMonoNs;
    private boolean active;
    private final boolean[] marked = new boolean[Mark.values().length];

    /** A request started with the receipt taken at receiptMonoNs. */
    synchronized void onStart(long newRequest, long newReceiptMonoNs) {
        request = newRequest;
        receiptMonoNs = newReceiptMonoNs;
        active = true;
        java.util.Arrays.fill(marked, false);
    }

    /** The request ended; later marks of it are not logged. */
    synchronized void onClear(long endedRequest) {
        if (endedRequest == request) {
            active = false;
        }
    }

    /** True exactly once per mark and request, while that request is the current one. */
    synchronized boolean mark(Mark mark, long ofRequest) {
        if (!active || ofRequest != request || marked[mark.ordinal()]) {
            return false;
        }
        marked[mark.ordinal()] = true;
        return true;
    }

    /** Whether a mark of the current request was already logged. */
    synchronized boolean isMarked(Mark mark, long ofRequest) {
        return active && ofRequest == request && marked[mark.ordinal()];
    }

    /** Nanoseconds from the request's receipt to monoNs, on the IVI VM's monotonic clock. */
    synchronized long sinceReceiptNs(long monoNs) {
        return monoNs - receiptMonoNs;
    }

    synchronized long currentRequest() {
        return active ? request : 0;
    }
}
