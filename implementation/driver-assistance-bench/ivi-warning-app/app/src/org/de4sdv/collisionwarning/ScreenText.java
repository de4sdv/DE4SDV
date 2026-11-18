// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// The text on the display. What the screen says is part of the recording, so every line is
// pinned whole by ScreenTextTest; a change here is a change to what the video claims.
// The warning names no component and no path; the status line names only what the app itself
// knows (its link to the warning-request topic and its own counts).
package org.de4sdv.collisionwarning;

import java.util.Locale;

final class ScreenText {

    static final String WARNING_TITLE = "COLLISION WARNING";
    static final String WARNING_ACTION = "BRAKE";
    static final String IDLE_TITLE = "No collision warning";

    private ScreenText() {}

    /** The small status line at the bottom of the screen. */
    static String status(String link, long receipts, long requests, long refused) {
        return String.format(Locale.US, "warning request topic: %s   received %d   requests %d   refused %d",
                link, receipts, requests, refused);
    }
}
