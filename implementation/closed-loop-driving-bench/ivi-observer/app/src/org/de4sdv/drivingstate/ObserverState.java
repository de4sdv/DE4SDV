// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// What the screen knows, Android-free: the newest receipt of each kind, the
// receipt clocks, and the counters. Mutated on the UI thread only (MainActivity
// posts every receipt there in arrival order), read by ScreenModel.
//
// It keeps values, never estimates: a kind that has not arrived is null and is
// shown as missing; a receipt with a contract problem is counted and shown, but
// does not replace the last good sample of its kind.
package org.de4sdv.drivingstate;

final class ObserverState {

    /**
     * The receiver rule in the rationale of REQ-DRIVING-017: with no HEALTH newer than this, what
     * the screen shows is marked stale. HEALTH is due at least every 200 ms, also while no plan is
     * produced, so it is the one stream whose silence means the state stopped arriving.
     */
    static final long HEALTH_STALE_AFTER_MS = 500L;

    /** A plan or a vehicle state older than this is marked in its own panel; a stale plan is not drawn. */
    static final long KIND_STALE_AFTER_MS = 1000L;

    StateRecord.Fields plan;
    StateRecord.Fields vehicle;
    StateRecord.Fields health;
    long planReceiptRealNs;
    long vehicleReceiptRealNs;
    long healthReceiptRealNs;

    /** The newest receipt of any kind (also one with a contract problem). */
    StateRecord.Fields last;
    long lastReceiptRealNs;

    long receipts;
    long contractProblems;
    String lastContractProblem = "";
    long allDefaultReceipts;
    long parseFailures;
    long gatewayDataLoss;
    long errors;
    String lastError = "";

    /** Per-kind newest sequence (index = kind 1..3) and the receipt-side gaps. */
    final long[] lastSequence = new long[4];
    long sequenceGaps;
    long sequenceRestarts;

    /** Link state of the subscriber: STARTING, WAITING, SUBSCRIBED, UNAVAILABLE. */
    String link = "STARTING";
    String linkDetail = "";
    String publisher = "";

    void onReceipt(MessageMapper.Mapped mapped, long tRealNs) {
        receipts++;
        last = mapped.fields;
        lastReceiptRealNs = tRealNs;
        if (mapped.allDefaults) {
            allDefaultReceipts++;
        }
        if (!mapped.ok()) {
            contractProblems++;
            lastContractProblem = mapped.contractProblem;
            return;
        }
        final StateRecord.Fields f = mapped.fields;
        if (f.kind < 1 || f.kind > 3) {
            // MessageMapper already reports this as a contract problem; never index with it.
            return;
        }
        final int kind = (int) f.kind;
        final long previous = lastSequence[kind];
        if (previous != 0) {
            if (f.sequence > previous + 1) {
                sequenceGaps += f.sequence - previous - 1;
            } else if (f.sequence <= previous) {
                sequenceRestarts++;
            }
        }
        lastSequence[kind] = f.sequence;
        switch (kind) {
            case 1:
                plan = f;
                planReceiptRealNs = tRealNs;
                break;
            case 2:
                vehicle = f;
                vehicleReceiptRealNs = tRealNs;
                break;
            default:
                health = f;
                healthReceiptRealNs = tRealNs;
                break;
        }
    }

    void onError(String reason) {
        errors++;
        lastError = reason;
    }

    void onParseFailure(String reason) {
        parseFailures++;
        lastError = reason;
    }

    void onDataLoss(String reason) {
        gatewayDataLoss++;
        lastError = reason;
    }

    void setLink(String state, String detail) {
        link = state;
        linkDetail = detail == null ? "" : detail;
    }

    /** Milliseconds since the newest HEALTH receipt, or -1 when none arrived. */
    long ageOfHealthMs(long nowRealMs) {
        return health == null ? -1L : nowRealMs - healthReceiptRealNs / 1_000_000L;
    }

    /**
     * True when no HEALTH is newer than HEALTH_STALE_AFTER_MS, whatever else still arrives: each
     * kind has a service unit of its own, so HEALTH can stop while PLAN and VEHICLE_STATE go on.
     */
    boolean stale(long nowRealMs) {
        final long age = ageOfHealthMs(nowRealMs);
        return age < 0 || age > HEALTH_STALE_AFTER_MS;
    }

    boolean planStale(long nowRealMs) {
        return plan == null || nowRealMs - planReceiptRealNs / 1_000_000L > KIND_STALE_AFTER_MS;
    }

    boolean vehicleStale(long nowRealMs) {
        return vehicle == null || nowRealMs - vehicleReceiptRealNs / 1_000_000L > KIND_STALE_AFTER_MS;
    }

    /**
     * Receipt lag of the newest receipt: IVI real time at the receipt minus the
     * message's publish real time, seconds. Two clocks (IVI and S-CORE real time):
     * meaningful only while the IVI clock is set (RUNBOOK step 10). NaN if none.
     */
    double receiptLagS() {
        if (last == null) {
            return Double.NaN;
        }
        return (lastReceiptRealNs - realNs(last.publishRealS, last.publishRealNs)) / 1e9;
    }

    /**
     * Age of the shown plan now, seconds: (IVI real now - plan publish real time),
     * two clocks, plus (plan publish monotonic - plan production monotonic), both
     * on the S-CORE host's monotonic clock. NaN when no plan or the stamps are zero.
     */
    double planAgeS(long nowRealMs) {
        if (plan == null || plan.publishRealS == 0) {
            return Double.NaN;
        }
        final double transport = (nowRealMs * 1_000_000L - realNs(plan.publishRealS, plan.publishRealNs)) / 1e9;
        if (plan.planProductionMonoS == 0 && plan.planProductionMonoNs == 0) {
            return Double.NaN;
        }
        final double atPublisher = (realNs(plan.publishMonoS, plan.publishMonoNs)
                - realNs(plan.planProductionMonoS, plan.planProductionMonoNs)) / 1e9;
        return transport + atPublisher;
    }

    static long realNs(long seconds, long nanos) {
        return seconds * 1_000_000_000L + nanos;
    }
}
