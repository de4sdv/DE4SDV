package org.de4sdv.aebsvisualization;

import android.content.Context;
import android.util.Log;

import com.google.protobuf.Parser;

import java.util.List;
import java.util.concurrent.Executor;
import java.util.concurrent.Executors;

import de4sdv.aebs.visualization.VisualizationFrame;
import google.sdv.gateway.client.SdvGatewayClient;
import google.sdv.gateway.client.Subscriber;
import google.sdv.gateway.client.SubscriberDescriptor;
import google.sdv.gateway.client.SubscriberOptions;

/**
 * Gateway Data Tunnel subscriber for the INC-AEBS-010 visualization frame.
 *
 * Subscribes to the `aebs-visualization-frame` topic (unit type
 * de4sdv.aebs_visualization.VisualizationFrame; proven PF-004, where the
 * publisher's topic defaults to the service unit name) using the documented
 * Java client (google.sdv.gateway.client). Read-only: the app publishes
 * nothing back (REQ-AEBS-S2-005).
 *
 * Bench identity per PF-004 runtime findings:
 *   package: de4sdv.aebs_visualization
 *   bundle:  AebsVisualization (FQIN bundle must start [A-Z])
 */
final class GatewayFrameSubscriber {

    private static final String TAG = "AebsFrameSubscriber";

    static final String PACKAGE_NAME = "de4sdv.aebs_visualization";
    static final String SERVICE_BUNDLE_NAME = "AebsVisualization";
    static final String TOPIC_NAME = "aebs-visualization-frame";
    static final String MESSAGE_NAME = "VisualizationFrame";

    /** Delivery callback: parsed frame + elapsed-received timestamp (ms). */
    interface FrameListener {
        void onFrame(VisualizationFrame frame, long receivedElapsedMs);
    }

    /** Connection/state callback for diagnostics rendering. */
    interface StateListener {
        void onUnavailable();

        void onSubscriptionActive();
    }

    private SdvGatewayClient client;
    private Subscriber<VisualizationFrame> subscriber;
    private final Executor executor = Executors.newSingleThreadExecutor();
    private FrameListener frameListener;
    private StateListener stateListener;
    private boolean started;

    void setListeners(FrameListener frameListener, StateListener stateListener) {
        this.frameListener = frameListener;
        this.stateListener = stateListener;
    }

    /**
     * Starts the subscription. Safe from the UI thread; Gateway work happens
     * on the executor. Failures are reported via onUnavailable and never crash
     * the app (System 2 instrumentation must fail closed).
     */
    synchronized void start() {
        if (started) {
            return;
        }
        started = true;
        executor.execute(this::run);
    }

    synchronized void stop() {
        if (!started) {
            return;
        }
        started = false;
        executor.execute(() -> {
            try {
                if (subscriber != null) {
                    subscriber.dispose();
                    subscriber = null;
                }
                client = null; // GC closes; close() typechecks against a class missing from javac classpath
            } catch (Throwable t) {
                Log.w(TAG, "shutdown error", t);
            }
        });
    }

    private void run() {
        try {
            client = new SdvGatewayClient();
            client.initComms(PACKAGE_NAME, SERVICE_BUNDLE_NAME);
            Log.i(TAG, "initComms ok");

            Parser<VisualizationFrame> parser =
                    VisualizationFrame.parser();

            SubscriberDescriptor<VisualizationFrame> descriptor =
                    new SubscriberDescriptor.Builder<VisualizationFrame>()
                            .setTopicName(TOPIC_NAME)
                            .setMessageName(MESSAGE_NAME)
                            .setParser(parser)
                            .build();

            subscriber = Subscriber.create(client, descriptor,
                    new SubscriberOptions.Builder().build());

            subscriber.registerOnMessagesAvailableListener(executor, this::onMessagesAvailable);

            Log.i(TAG, "subscribed to topic=" + TOPIC_NAME);
            StateListener listener = stateListener;
            if (listener != null) {
                listener.onSubscriptionActive();
            }
        } catch (Throwable t) {
            Log.e(TAG, "Gateway subscription failed", t);
            closeQuietly();
            StateListener listener = stateListener;
            if (listener != null) {
                listener.onUnavailable();
            }
        }
    }

    private void onMessagesAvailable() {
        FrameListener listener = frameListener;
        if (listener == null || subscriber == null) {
            return;
        }
        try {
            List<VisualizationFrame> frames = subscriber.readNextMessages(16);
            long now = android.os.SystemClock.elapsedRealtime();
            for (VisualizationFrame frame : frames) {
                listener.onFrame(frame, now);
            }
        } catch (Throwable t) {
            Log.w(TAG, "frame read failed", t);
        }
    }

    private void closeQuietly() {
        try {
            if (subscriber != null) {
                subscriber.dispose();
            }
        } catch (Throwable t) {
            Log.w(TAG, "close error", t);
        } finally {
            subscriber = null;
            client = null;
        }
    }
}
