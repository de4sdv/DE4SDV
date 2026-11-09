// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// The IVI observer application of INC-DRIVING-001 (phase 8, decision 4).
//
// It subscribes to the typed Data Tunnel topic that carries the driving
// operational state from the SOME/IP broker of the SDV Core VM, appends one JSONL
// record per receipt to /data/data/org.de4sdv.drivingstate/files/observer.jsonl,
// mirrors a summary of each receipt to logcat (tag DE4SDV_DRIVING_STATE) and draws
// the state and the two clocks on screen.
//
// The message arrives typed: the broker translated the SOME/IP struct in
// REFLECTION mode, and this process reads protobuf fields. Nothing here decodes a
// byte payload, and no DE4SDV relay sits between the platform's topic and this
// app; the app publishes nothing back.
//
// The APK is installed over adb on the IVI VM (scripts/stage_ivi_observer.sh); the
// record file is pulled by the same script (adb root, or run-as on a debuggable
// build).
package org.de4sdv.drivingstate;

import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.WindowManager;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.util.Locale;

public final class MainActivity extends Activity implements TypedStateSubscriber.Sink {

    private static final String TAG = "DE4SDV_DRIVING_STATE";
    private static final String RECORD_TAG = TAG;
    private static final String RECORD_FILE = "observer.jsonl";
    private static final long kStatusPeriodMs = 5000L;

    private final Handler main = new Handler(Looper.getMainLooper());
    private ObserverView view;
    private TypedStateSubscriber subscriber;
    private BufferedWriter record;
    private long receipts;
    private long errors;
    private String lastStatus = "starting";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        view = new ObserverView(this);
        setContentView(view);

        try {
            final File file = new File(getFilesDir(), RECORD_FILE);
            record = new BufferedWriter(new OutputStreamWriter(
                    new FileOutputStream(file, false), StandardCharsets.UTF_8));
            Log.i(TAG, "record file " + file.getAbsolutePath());
        } catch (IOException error) {
            Log.e(TAG, "cannot open the record file", error);
        }

        lifecycle("start", "subject", TypedStateSubscriber.SUBJECT_PACKAGE + "."
                + TypedStateSubscriber.SUBJECT_BUNDLE);
        lifecycle("config", "topic", TypedStateSubscriber.TOPIC_NAME);
        lifecycle("config", "message", TypedStateSubscriber.MESSAGE_NAME);
        lifecycle("config", "translation", "REFLECTION at the SDV Core SOME/IP broker");

        subscriber = new TypedStateSubscriber(this);
        subscriber.start();

        main.postDelayed(this::statusTick, kStatusPeriodMs);
    }

    @Override
    protected void onDestroy() {
        lifecycle("stop", "receipts", Long.toString(receipts));
        if (subscriber != null) {
            subscriber.stop();
        }
        closeRecord();
        main.removeCallbacksAndMessages(null);
        super.onDestroy();
    }

    // --- TypedStateSubscriber.Sink, called on the subscriber's thread ---------

    @Override
    public void onState(MessageMapper.Mapped mapped, long tMonoNs, long tRealNs) {
        receipts++;
        writeRecord(StateRecord.line(tMonoNs, tRealNs, receipts, mapped.fields));
        Log.i(RECORD_TAG, summary(receipts, mapped));
        main.post(() -> view.onState(mapped, tRealNs));
    }

    @Override
    public void onError(String reason, long tMonoNs, long tRealNs) {
        errors++;
        Log.w(RECORD_TAG, "error reason=" + reason);
        writeRecord(StateRecord.envelope(tMonoNs, tRealNs, "error",
                "\"reason\":\"" + StateRecord.quote(reason) + "\""));
        main.post(() -> view.onError(reason));
    }

    @Override
    public void onSubscriptionActive() {
        lastStatus = "SUBSCRIBED";
        lifecycle("ready", "topic", TypedStateSubscriber.TOPIC_NAME);
        main.post(() -> view.setLink("SUBSCRIBED"));
    }

    @Override
    public void onUnavailable(String reason) {
        lastStatus = "UNAVAILABLE";
        Log.w(TAG, "gateway unavailable: " + reason);
        lifecycle("error", "gateway", reason);
        main.post(() -> view.setLink("UNAVAILABLE"));
    }

    // --- records -------------------------------------------------------------

    /** One logcat line, short enough not to be truncated (the file has the arrays). */
    private static String summary(long receiptSeq, MessageMapper.Mapped mapped) {
        final StateRecord.Fields f = mapped.fields;
        final StringBuilder line = new StringBuilder(256);
        line.append("seq=").append(receiptSeq);
        line.append(" kind=").append(StateRecord.kindName(f.kind));
        line.append(" sequence=").append(f.sequence);
        line.append(" schema=").append(f.schemaMajor).append('.').append(f.schemaMinor);
        line.append(" publish_real=").append(f.publishRealS).append('.').append(f.publishRealNs);
        switch ((int) f.kind) {
            case 1:
                line.append(" frame=").append(f.planFrameIndex);
                line.append(" plan_capture_ms=").append(f.planCaptureMs);
                line.append(" points=").append(f.planX.length);
                line.append(" run_record=").append(f.runRecord);
                break;
            case 2:
                line.append(" speed_kmh=").append(String.format(Locale.US, "%.2f", f.speedKmh));
                line.append(" sample_capture_ms=").append(f.sampleCaptureMs);
                break;
            case 3:
                line.append(" mode=").append(f.mode).append('(')
                        .append(StateRecord.modeName(f.mode)).append(')');
                line.append(" cause=").append(f.cause).append('(')
                        .append(StateRecord.causeName(f.cause)).append(')');
                line.append(" cause_since_s=").append(f.causeSinceMonoS);
                break;
            default:
                break;
        }
        if (!mapped.ok()) {
            line.append(" contract=").append(mapped.contractProblem);
        }
        if (mapped.allDefaults) {
            line.append(" all_defaults=1");
        }
        return line.toString();
    }

    private void statusTick() {
        Log.i(RECORD_TAG, String.format(Locale.US,
                "status link=%s receipts=%d errors=%d", lastStatus, receipts, errors));
        main.postDelayed(this::statusTick, kStatusPeriodMs);
    }

    private void lifecycle(String event, String key, String value) {
        final long tMonoNs = System.nanoTime();
        final long tRealNs = System.currentTimeMillis() * 1_000_000L;
        Log.i(RECORD_TAG, "lifecycle " + event + " " + key + "=" + value);
        writeRecord(StateRecord.envelope(tMonoNs, tRealNs, event,
                "\"" + key + "\":\"" + StateRecord.quote(value) + "\""));
    }

    private synchronized void writeRecord(String line) {
        if (record == null) {
            return;
        }
        try {
            record.write(line);
            record.write('\n');
            record.flush();
        } catch (IOException error) {
            Log.e(TAG, "record write failed", error);
        }
    }

    private synchronized void closeRecord() {
        if (record == null) {
            return;
        }
        try {
            record.close();
        } catch (IOException error) {
            Log.w(TAG, "record close failed", error);
        } finally {
            record = null;
        }
    }
}
