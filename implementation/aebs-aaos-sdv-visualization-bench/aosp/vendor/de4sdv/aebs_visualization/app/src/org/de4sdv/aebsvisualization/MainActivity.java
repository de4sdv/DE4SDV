package org.de4sdv.aebsvisualization;

import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
import android.util.Log;
import android.os.Handler;
import android.os.HandlerThread;
import android.widget.TextView;

/**
 * DE4SDV AEBS 010 center-display activity.
 *
 * System 2 engineering visualization: renders the presentation disposition
 * emitted by {@link VisualizationStateReducer} plus the current frame's
 * per-field provenance badges. Display-derived presentation only — the app
 * derives no AEBS decision and publishes nothing (REQ-AEBS-S2-005).
 *
 * The Gateway subscription is bound by the runtime lock (AO-AEBS-010-007/008)
 * using the documented SDV Gateway Java client; the subscription wiring is
 * finalized in the runtime segment on the bench (Phase 10), because service
 * unit descriptors must match the pinned ingress build.
 */
public class MainActivity extends Activity {

    private VisualizationStateReducer reducer;
    private TextView dispositionView;
    private TextView provenanceView;
    private SituationRadarView radarView;
    private HandlerThread tickerThread;
    private Handler tickerHandler;
    private long lastFrameElapsedMs;
    private GatewayFrameSubscriber gatewaySubscriber;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        reducer = new VisualizationStateReducer();
        dispositionView = findViewById(R.id.disposition);
        provenanceView = findViewById(R.id.provenance);
        radarView = findViewById(R.id.radar);

        tickerThread = new HandlerThread("aebs010-tick");
        tickerThread.start();
        tickerHandler = new Handler(tickerThread.getLooper());
        tickerHandler.postDelayed(this::tick, 200);
        render();
        // Live Data Tunnel subscription (PF-004 proven path). Read-only.
        gatewaySubscriber = new GatewayFrameSubscriber();
        gatewaySubscriber.setListeners(this::onGatewayFrame, new GatewayFrameSubscriber.StateListener() {
            @Override
            public void onUnavailable() {
                runOnUiThread(() -> onDisposition(reducer.onUnavailable(
                        android.os.SystemClock.elapsedRealtime())));
            }

            @Override
            public void onInvalid() {
                runOnUiThread(() -> onDisposition(reducer.onInvalid(
                        android.os.SystemClock.elapsedRealtime())));
            }

            @Override
            public void onSubscriptionActive() {
                Log.i("MainActivity", "Gateway subscription active");
            }
        });
        gatewaySubscriber.start();
    }

    private void onGatewayFrame(de4sdv.aebs.visualization.VisualizationFrame frame,
                                long receivedElapsedMs) {
        // Map the wire frame onto the reducer's input. The wire schema uses
        // FieldValue oneofs with per-field provenance; boolean/enum fields
        // carry the coordinator decisions and the native intervention flag.
        // Validation (sequence, freshness, finiteness) mirrors the bridge sink
        // contract; the exact FQIN/topic pin is recorded in runtime-lock.yaml.
        final boolean intervention = frame.hasNativeIntervention()
                && frame.getNativeIntervention().hasBoolValue()
                && frame.getNativeIntervention().getBoolValue();
        final boolean warning = frame.hasDe4SdvWarningRequest()
                && frame.getDe4SdvWarningRequest().hasBoolValue()
                && frame.getDe4SdvWarningRequest().getBoolValue();
        final boolean braking = frame.hasDe4SdvBrakingRequest()
                && frame.getDe4SdvBrakingRequest().hasBoolValue()
                && frame.getDe4SdvBrakingRequest().getBoolValue();
        final String lifecycle = frame.hasDe4SdvLifecycleState()
                && frame.getDe4SdvLifecycleState().hasEnumValue()
                ? frame.getDe4SdvLifecycleState().getEnumValue()
                : "armed";
        // Live perception fields for the situation radar (may be absent).
        final Float targetRange = frame.hasTargetRange()
                && frame.getTargetRange().hasNumericValue()
                ? (float) frame.getTargetRange().getNumericValue() : null;
        final Float targetBearing = frame.hasTargetBearing()
                && frame.getTargetBearing().hasNumericValue()
                ? (float) frame.getTargetBearing().getNumericValue() : null;
        final Float rssDistance = frame.hasRssDistance()
                && frame.getRssDistance().hasNumericValue()
                ? (float) frame.getRssDistance().getNumericValue() : null;
        Log.i("MainActivity", "onGatewayFrame: frame seq=" + frame.getSequence()
                + " intervention=" + intervention + " warning=" + warning
                + " braking=" + braking + " lifecycle=" + lifecycle
                + " range=" + targetRange + " bearing=" + targetBearing
                + " rss=" + rssDistance);
        runOnUiThread(() -> {
            radarView.onFrame(targetRange, targetBearing, rssDistance, intervention);
            onFrame(new VisualizationStateReducer.FrameInput(
                    frame.getSequence(), intervention, warning, braking, lifecycle));
        });
    }


    private void tick() {
        final long now = android.os.SystemClock.elapsedRealtime();
        // Fail-closed: presentation goes stale when frames stop arriving.
        if (lastFrameElapsedMs > 0 && now - lastFrameElapsedMs > 1_000L) {
            onDisposition(reducer.onStale(now));
        }
        onDisposition(reducer.onTick(now));
        tickerHandler.postDelayed(this::tick, 200);
    }

    /** Called by the Gateway subscription when a validated frame arrives. */
    void onFrame(VisualizationStateReducer.FrameInput frame) {
        lastFrameElapsedMs = android.os.SystemClock.elapsedRealtime();
        onDisposition(reducer.onFrame(frame, lastFrameElapsedMs));
    }

    private void onDisposition(VisualizationStateReducer.Disposition disposition) {
        runOnUiThread(() -> renderDisposition(disposition));
    }

    private void render() {
        renderDisposition(reducer.disposition());
    }

    private void renderDisposition(VisualizationStateReducer.Disposition disposition) {
        dispositionView.setText(VisualizationStateReducer.label(disposition));
        // Fail-closed radar: no live data -> empty scope (no synthetic blip).
        if (disposition == VisualizationStateReducer.Disposition.STALE
                || disposition == VisualizationStateReducer.Disposition.INVALID
                || disposition == VisualizationStateReducer.Disposition.UNAVAILABLE) {
            radarView.clear();
        }
        final int color;
        switch (disposition) {
            case WARNING:
                color = Color.rgb(255, 165, 0);
                break;
            case INTERVENTION:
                color = Color.rgb(204, 0, 0);
                break;
            case RELEASED:
            case RESTORED:
                color = Color.rgb(0, 153, 51);
                break;
            case STALE:
            case INVALID:
            case UNAVAILABLE:
                color = Color.GRAY;
                break;
            case MONITORING:
            default:
                color = Color.rgb(0, 102, 204);
                break;
        }
        dispositionView.setTextColor(color);
        provenanceView.setText(getString(R.string.provenance_footer));
    }

    @Override
    protected void onDestroy() {
        tickerHandler.removeCallbacksAndMessages(null);
        tickerThread.quitSafely();
        if (gatewaySubscriber != null) {
            gatewaySubscriber.stop();
            gatewaySubscriber = null;
        }
        super.onDestroy();
    }
}
