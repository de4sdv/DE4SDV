package org.de4sdv.aebsvisualization;

import androidx.annotation.NonNull;

import java.util.Locale;

/**
 * Pure presentation-state reducer for the DE4SDV AEBS 010 visualization.
 *
 * Mirrors the SysML VisualizationPresentationMachine exactly: monitoring,
 * warning, intervention, released, plus fail-closed stale / unavailable /
 * invalid dispositions and the bounded restored transient. No Android or
 * Gateway dependency, so the full transition contract is unit-testable
 * (VisualizationStateReducerTest) and the Activity only renders what the
 * reducer emits.
 */
public final class VisualizationStateReducer {

    /** Presentation dispositions aligned with SysML VisualizationHealthKind. */
    public enum Disposition {
        UNAVAILABLE,
        MONITORING,
        WARNING,
        INTERVENTION,
        RELEASED,
        STALE,
        INVALID,
        RESTORED
    }

    /** One accepted frame's display-relevant facts; built by the subscriber. */
    public static final class FrameInput {
        public final long sequence;
        public final boolean nativeIntervention;
        public final boolean warningRequest;
        public final boolean brakingRequest;
        @NonNull public final String lifecycleState; // armed|braking_latched|released_verified_stop

        public FrameInput(long sequence, boolean nativeIntervention, boolean warningRequest,
                          boolean brakingRequest, @NonNull String lifecycleState) {
            this.sequence = sequence;
            this.nativeIntervention = nativeIntervention;
            this.warningRequest = warningRequest;
            this.brakingRequest = brakingRequest;
            this.lifecycleState = lifecycleState;
        }
    }

    private static final int RESTORE_CONSECUTIVE_FRAMES = 3;   // AO-AEBS-010-006 target
    private static final long RESTORED_HOLD_MS = 2_000L;      // transient RESTORED duration

    @NonNull private Disposition disposition = Disposition.UNAVAILABLE;
    private int validStreak = 0;
    private long restoredUntilElapsed = Long.MIN_VALUE;
    private long lastSequence = Long.MIN_VALUE;

    /** Current presentation disposition (never null). */
    @NonNull
    public Disposition disposition() {
        return disposition;
    }

    /**
     * Feed one accepted, validated frame. Sequence monotonicity and freshness
     * are enforced upstream (ingress validator); this reducer owns only the
     * presentation state machine.
     */
    @NonNull
    public Disposition onFrame(@NonNull FrameInput frame, long nowElapsedMs) {
        if (frame.sequence <= lastSequence) {
            // Duplicates/replays are invalid input upstream; fail closed here too.
            return transition(Disposition.INVALID, nowElapsedMs);
        }
        lastSequence = frame.sequence;
        validStreak++;

        Disposition next;
        if ("released_verified_stop".equals(frame.lifecycleState)) {
            next = Disposition.RELEASED;
        } else if (frame.nativeIntervention) {
            next = Disposition.INTERVENTION;
        } else if (frame.brakingRequest) {
            next = Disposition.INTERVENTION;
        } else if (frame.warningRequest) {
            next = Disposition.WARNING;
        } else {
            next = Disposition.MONITORING;
        }

        if (disposition == Disposition.UNAVAILABLE || disposition == Disposition.STALE
                || disposition == Disposition.INVALID) {
            if (validStreak < RESTORE_CONSECUTIVE_FRAMES) {
                // Not enough consecutive frames yet: stay in the degraded state.
                return disposition;
            }
            validStreak = 0;
            transition(Disposition.RESTORED, nowElapsedMs);
            restoredUntilElapsed = nowElapsedMs + RESTORED_HOLD_MS;
            return disposition;
        }
        return transition(next, nowElapsedMs);
    }

    /** No valid frame accepted within the stale timeout. */
    @NonNull
    public Disposition onStale(long nowElapsedMs) {
        return transition(Disposition.STALE, nowElapsedMs);
    }

    /** No source or service at all. */
    @NonNull
    public Disposition onUnavailable(long nowElapsedMs) {
        return transition(Disposition.UNAVAILABLE, nowElapsedMs);
    }

    /** A frame was rejected by validation. */
    @NonNull
    public Disposition onInvalid(long nowElapsedMs) {
        validStreak = 0;
        return transition(Disposition.INVALID, nowElapsedMs);
    }

    /** Periodic tick: expires the transient RESTORED indication. */
    @NonNull
    public Disposition onTick(long nowElapsedMs) {
        if (disposition == Disposition.RESTORED && nowElapsedMs >= restoredUntilElapsed) {
            return transition(Disposition.MONITORING, nowElapsedMs);
        }
        return disposition;
    }

    @NonNull
    private Disposition transition(@NonNull Disposition next, long nowElapsedMs) {
        disposition = next;
        return next;
    }

    /** Human-readable label for the view; display-derived presentation only. */
    @NonNull
    public static String label(@NonNull Disposition disposition) {
        return disposition.name().toLowerCase(Locale.ROOT);
    }
}
