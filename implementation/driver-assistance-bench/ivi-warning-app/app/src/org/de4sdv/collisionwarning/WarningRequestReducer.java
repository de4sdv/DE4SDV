// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// The edge logic of the warning presentation (CollisionWarningPresentationApplication of
// driver_assistance_physical_software_realization.sysml): what one typed warning-request message
// does to what the driver is shown.
//
// The model (MAP-DRIVING-DA-WARNING-REQUEST, timingQualityAndState): "one event per plan; a request
// starts with the first event that is true after one that is false". So:
//
//   START      requested = 1 after 0 (or as the app's first message): show the warning, start the
//              sound. The app holds no request before its first message, as after a false event.
//   HOLD       requested = 1 while a request is shown: nothing is shown again.
//   CLEAR      requested = 0 while a request is shown: the request has ended; the warning is taken
//              off the display and the sound stops. The model states when a request starts, not
//              when the presentation ends: ending it with the request is this app's choice
//              (README, "Deviations").
//   IDLE       requested = 0 while nothing is shown.
//   STALE      issue_time_sim_ms not later than the last accepted message's: a repeated or
//              reordered plan (the gateway's last-message fetch on a resubscription delivers the
//              last message again). Refused; changes nothing.
//   MALFORMED  requested not 0 or 1 (the ICD carries the boolean as UINT32 0 or 1), or an issue
//              time outside uint32. Refused; changes nothing.
//
// Issue times are simulation milliseconds of one run. A new run restarts them, so the app is
// restarted before each window (am start -S), as the observer of INC-DRIVING-001 is.
//
// No Android and no protobuf import: a plain JVM test runs it on the build host and in the tree.
// One thread only (the subscriber's executor).
package org.de4sdv.collisionwarning;

final class WarningRequestReducer {

    static final long UINT32_MAX = 0xFFFFFFFFL;

    enum Verdict {
        START, HOLD, CLEAR, IDLE, STALE, MALFORMED;

        boolean shows() {
            return this == START;
        }

        boolean clears() {
            return this == CLEAR;
        }

        boolean accepted() {
            return this != STALE && this != MALFORMED;
        }
    }

    static final class Outcome {
        final Verdict verdict;
        /** The request number this message started, holds or ended (1, 2, ...); 0 for none. */
        final long request;
        /** Why a message was refused; empty when accepted. */
        final String reason;

        Outcome(Verdict verdict, long request, String reason) {
            this.verdict = verdict;
            this.request = request;
            this.reason = reason;
        }
    }

    private boolean active;
    private long lastIssueTimeSimMs = -1;
    private long requests;
    private final long[] counts = new long[Verdict.values().length];

    /** One message: requested and issue_time_sim_ms as unsigned values of protobuf's uint32. */
    Outcome onMessage(long requested, long issueTimeSimMs) {
        if (requested != 0 && requested != 1) {
            return count(new Outcome(Verdict.MALFORMED, 0, "requested=" + requested + " (0 or 1 expected)"));
        }
        if (issueTimeSimMs < 0 || issueTimeSimMs > UINT32_MAX) {
            return count(new Outcome(Verdict.MALFORMED, 0, "issue_time_sim_ms=" + issueTimeSimMs + " outside uint32"));
        }
        if (issueTimeSimMs <= lastIssueTimeSimMs) {
            return count(new Outcome(Verdict.STALE, active ? requests : 0,
                    "issue_time_sim_ms=" + issueTimeSimMs + " not after " + lastIssueTimeSimMs));
        }
        lastIssueTimeSimMs = issueTimeSimMs;
        if (requested == 1) {
            if (active) {
                return count(new Outcome(Verdict.HOLD, requests, ""));
            }
            active = true;
            requests++;
            return count(new Outcome(Verdict.START, requests, ""));
        }
        if (active) {
            active = false;
            return count(new Outcome(Verdict.CLEAR, requests, ""));
        }
        return count(new Outcome(Verdict.IDLE, 0, ""));
    }

    boolean active() {
        return active;
    }

    long requests() {
        return requests;
    }

    long lastIssueTimeSimMs() {
        return lastIssueTimeSimMs;
    }

    long count(Verdict verdict) {
        return counts[verdict.ordinal()];
    }

    private Outcome count(Outcome outcome) {
        counts[outcome.verdict.ordinal()]++;
        return outcome;
    }
}
