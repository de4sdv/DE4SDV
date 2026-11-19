// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// CollisionWarningPresentationApplication of driver_assistance_physical_software_realization.sysml
// (INC-DRIVING-002): on the IVI VM, it subscribes to the warning-request topic through the SDV
// Gateway and, when a request starts, shows the collision warning on the display and starts a
// warning sound. It sends nothing to the candidate. It logs the receipt, the displayed frame and the
// start of the sound with their times for phase 10. It is not the informational visualization of
// the AEBS visualization increment.
//
// The 0.1 s of the presentation runs from the receipt to the first displayed frame with the
// warning and to the start of the sound (MAP-DRIVING-DA-WARNING-REQUEST). So the start is handled
// where the message is read: the reducer and AudioTrack.play() run on the subscriber's thread, and
// the screen change is posted to the front of the UI queue.
//
// Records: one JSONL line per event in files/warning.jsonl and the same line in logcat under
// DE4SDV_COLLISION_WARNING (WarningRecord). The file is appended to, never truncated, and written by
// RecordWriter's own thread: no file I/O on the UI thread or in front of play(). Each start of the
// activity writes a lifecycle start line with the process id. The events:
//   lifecycle            start, configuration, link changes, stop
//   receipt              every message read: seq, requested, issue_time_sim_ms, verdict, request
//   display_drawn        the first onDraw with the warning of a request
//   display_committed    the frame-commit callback of that frame (submitted to the swap chain)
//   sound_play_called / sound_head_moved / sound_timestamp   WarningSound
//   display_cleared, sound_stopped                            the request ended (requested = 0)
//   error, drop          a slot that did not parse, a read failure, a gateway DATA_LOSS
package org.de4sdv.collisionwarning;

import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.Process;
import android.util.Log;
import android.view.WindowManager;

import java.io.File;
import java.io.IOException;

public final class MainActivity extends Activity
        implements WarningRequestSubscriber.Sink, WarningView.DrawListener, WarningSound.Listener {

    private static final String TAG = WarningRecord.TAG;
    private static final long STATUS_PERIOD_MS = 1000L;
    private static final long STATUS_LOG_EVERY = 5;

    private final Handler main = new Handler(Looper.getMainLooper());
    private final PresentationTimeline timeline = new PresentationTimeline();
    // Subscriber thread only.
    private final WarningRequestReducer reducer = new WarningRequestReducer();
    private volatile long receipts;
    private volatile long requests;
    private volatile long refused;
    private volatile String link = WarningRequestSubscriber.LINK_WAITING;
    private long statusTicks;

    private WarningView view;
    private WarningSound sound;
    private WarningRequestSubscriber subscriber;
    private volatile RecordWriter record;

    private final Runnable statusTick = new Runnable() {
        @Override
        public void run() {
            if (view != null) {
                view.setStatus(ScreenText.status(link, receipts, requests, refused));
            }
            if (++statusTicks % STATUS_LOG_EVERY == 0) {
                record("status", "link", link, "receipts", receipts, "requests", requests, "refused", refused);
            }
            main.postDelayed(this, STATUS_PERIOD_MS);
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        view = new WarningView(this, this);
        setContentView(view);

        try {
            final File file = new File(getFilesDir(), WarningRecord.FILE);
            record = new RecordWriter(file, (what, error) -> Log.e(TAG, "record " + what + " failed", error));
            Log.i(TAG, "record file " + file.getAbsolutePath() + " (appended)");
        } catch (IOException error) {
            Log.e(TAG, "cannot open the record file", error);
        }

        record("lifecycle", "phase", "start", "pid", Process.myPid(),
                "subject", WarningRequestSubscriber.SUBJECT_PACKAGE + "." + WarningRequestSubscriber.SUBJECT_BUNDLE,
                "message", WarningRequestSubscriber.MESSAGE_NAME,
                "publisher", WarningRequestSubscriber.PUBLISHER_PACKAGE + "." + WarningRequestSubscriber.PUBLISHER_BUNDLE,
                "unit", WarningRequestSubscriber.UNIT,
                "translation", "REFLECTION at the SDV Core SOME/IP broker",
                "poll_ms", WarningRequestSubscriber.POLL_PERIOD_MS);

        sound = new WarningSound(this, timeline, this);
        sound.prepare();
        subscriber = new WarningRequestSubscriber(this);
        subscriber.start();
        main.post(statusTick);
    }

    @Override
    protected void onDestroy() {
        record("lifecycle", "phase", "stop", "receipts", receipts, "requests", requests, "refused", refused);
        if (subscriber != null) {
            subscriber.stop();
        }
        if (sound != null) {
            sound.release();
        }
        main.removeCallbacksAndMessages(null);
        closeRecord();
        super.onDestroy();
    }

    // --- WarningRequestSubscriber.Sink: the subscriber's thread -----------------------------

    @Override
    public void onMessage(long requested, long issueTimeSimMs, long tMonoNs, long tRealNs) {
        receipts++;
        final WarningRequestReducer.Outcome outcome = reducer.onMessage(requested, issueTimeSimMs);
        if (!outcome.verdict.accepted()) {
            refused++;
        }
        final WarningRequestReducer.Verdict verdict = outcome.verdict;
        final long request = outcome.request;
        if (verdict.shows()) {
            requests = reducer.requests();
            timeline.onStart(request, tMonoNs);
            // The screen change is posted first (it does not block), then the sound starts here.
            main.postAtFrontOfQueue(() -> {
                view.show(request);
                view.getViewTreeObserver().registerFrameCommitCallback(() -> onWarningCommitted(request));
            });
            sound.start(request);
        } else if (verdict.clears()) {
            timeline.onClear(request);
            main.postAtFrontOfQueue(() -> {
                view.clear();
                record("display_cleared", "request", request);
            });
            sound.stop(request);
        }
        // The receipt line after the start calls: writing it first would delay the warning.
        recordAt(tMonoNs, tRealNs, "receipt", "seq", receipts, "requested", requested,
                "issue_time_sim_ms", issueTimeSimMs, "verdict", verdict.name(), "request", request,
                "reason", outcome.reason);
    }

    @Override
    public void onError(String reason, long tMonoNs, long tRealNs) {
        refused++;
        recordAt(tMonoNs, tRealNs, "error", "reason", reason);
    }

    @Override
    public void onDataLoss(String reason, long tMonoNs, long tRealNs) {
        recordAt(tMonoNs, tRealNs, "drop", "reason", reason);
    }

    @Override
    public void onLink(String state, String detail) {
        link = state;
        record("lifecycle", "phase", "link", "link", state, "detail", detail);
    }

    @Override
    public void onConfig(String key, String value) {
        record("lifecycle", "phase", "config", "key", key, "value", value);
    }

    // --- the display: UI thread --------------------------------------------------------------

    @Override
    public void onWarningDrawn(long request) {
        final long now = System.nanoTime();
        if (timeline.mark(PresentationTimeline.Mark.DRAWN, request)) {
            recordAt(now, realNowNs(), PresentationTimeline.Mark.DRAWN.event, "request", request,
                    "since_receipt_ns", timeline.sinceReceiptNs(now));
        }
    }

    private void onWarningCommitted(long request) {
        final long now = System.nanoTime();
        // Only the commit of a frame that was drawn with the warning counts.
        if (timeline.isMarked(PresentationTimeline.Mark.DRAWN, request)
                && timeline.mark(PresentationTimeline.Mark.COMMITTED, request)) {
            recordAt(now, realNowNs(), PresentationTimeline.Mark.COMMITTED.event, "request", request,
                    "since_receipt_ns", timeline.sinceReceiptNs(now));
        }
    }

    // --- the sound: subscriber or sound thread ------------------------------------------------

    @Override
    public void onSoundMark(PresentationTimeline.Mark mark, long request, long monoNs, Object... details) {
        final Object[] fields = new Object[4 + details.length];
        fields[0] = "request";
        fields[1] = request;
        fields[2] = "since_receipt_ns";
        fields[3] = timeline.sinceReceiptNs(monoNs);
        System.arraycopy(details, 0, fields, 4, details.length);
        recordAt(monoNs, realNowNs(), mark.event, fields);
    }

    @Override
    public void onSoundNote(String event, Object... details) {
        record(event, details);
    }

    // --- records -------------------------------------------------------------------------------

    private static long realNowNs() {
        return System.currentTimeMillis() * 1_000_000L;
    }

    private void record(String event, Object... keyValues) {
        recordAt(System.nanoTime(), realNowNs(), event, keyValues);
    }

    // Any thread: the line is formatted here and handed to the writer thread.
    private void recordAt(long monoNs, long realNs, String event, Object... keyValues) {
        Log.i(TAG, WarningRecord.logcat(monoNs, realNs, event, keyValues));
        final RecordWriter writer = record;
        if (writer != null) {
            writer.write(WarningRecord.json(monoNs, realNs, event, keyValues));
        }
    }

    private void closeRecord() {
        final RecordWriter writer = record;
        record = null;
        if (writer != null) {
            writer.close();
        }
    }
}
