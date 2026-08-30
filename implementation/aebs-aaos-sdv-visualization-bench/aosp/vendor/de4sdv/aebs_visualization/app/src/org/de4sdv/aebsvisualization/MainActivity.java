package org.de4sdv.aebsvisualization;

import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.os.HandlerThread;
import android.widget.TextView;
import android.util.Log;

/**
 * DE4SDV AEBS 010 center-display activity.
 *
 * System 2 engineering visualization: renders the presentation disposition
 * emitted by {@link VisualizationStateReducer} through the pure
 * {@link SituationRenderModel}. Display-derived presentation only — the app
 * derives no AEBS decision and publishes nothing (REQ-AEBS-S2-005).
 *
 * Layout contract (VISUALIZATION-CONTRACT.md): the forward-situation view
 * carries scene geometry only; state progression, exact metrics, and data
 * health live in the side panel and health chip so liveness can never be
 * confused with risk geometry. The state color authority is the reducer;
 * no renderer rule can recolor a state.
 */
public class MainActivity extends Activity {

    private VisualizationStateReducer reducer;
    private ForwardSituationView situationView;
    private TextView healthChip;
    private TextView stateMonitoring;
    private TextView stateWarning;
    private TextView stateIntervention;
    private TextView stateReleased;
    private TextView metricTargetRange;
    private TextView metricRssDistance;
    private TextView metricEgoSpeed;
    private TextView metricFrameAge;
    private TextView provenanceView;
    private HandlerThread tickerThread;
    private Handler tickerHandler;
    private long lastFrameElapsedMs;
    private long lastFrameAgeMs = -1;
    private GatewayFrameSubscriber gatewaySubscriber;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        reducer = new VisualizationStateReducer();
        situationView = findViewById(R.id.situation_view);
        healthChip = findViewById(R.id.health_chip);
        stateMonitoring = findViewById(R.id.state_monitoring);
        stateWarning = findViewById(R.id.state_warning);
        stateIntervention = findViewById(R.id.state_intervention);
        stateReleased = findViewById(R.id.state_released);
        metricTargetRange = findViewById(R.id.metric_target_range);
        metricRssDistance = findViewById(R.id.metric_rss_distance);
        metricEgoSpeed = findViewById(R.id.metric_ego_speed);
        metricFrameAge = findViewById(R.id.metric_frame_age);
        provenanceView = findViewById(R.id.provenance);

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
        // Live perception fields for the situation view (may be absent).
        final Float targetRange = frame.hasTargetRange()
                && frame.getTargetRange().hasNumericValue()
                ? (float) frame.getTargetRange().getNumericValue() : null;
        final Float targetBearing = frame.hasTargetBearing()
                && frame.getTargetBearing().hasNumericValue()
                ? (float) frame.getTargetBearing().getNumericValue() : null;
        final Float rssDistance = frame.hasRssDistance()
                && frame.getRssDistance().hasNumericValue()
                ? (float) frame.getRssDistance().getNumericValue() : null;
        // schema_minor 1: cluster projection + ego speed (display-presentational).
        final Float egoSpeed = frame.hasEgoSpeed()
                && frame.getEgoSpeed().hasNumericValue()
                ? (float) frame.getEgoSpeed().getNumericValue() : null;
        final float[] targetPoints;
        if (frame.getTargetPointsCount() > 0) {
            targetPoints = new float[frame.getTargetPointsCount() * 2];
            for (int i = 0; i < frame.getTargetPointsCount(); i++) {
                targetPoints[i * 2] = frame.getTargetPoints(i).getForwardM();
                targetPoints[i * 2 + 1] = frame.getTargetPoints(i).getLateralM();
            }
        } else {
            targetPoints = null;
        }
        Log.i("MainActivity", "onGatewayFrame: frame seq=" + frame.getSequence()
                + " intervention=" + intervention + " warning=" + warning
                + " braking=" + braking + " lifecycle=" + lifecycle
                + " range=" + targetRange + " bearing=" + targetBearing
                + " rss=" + rssDistance);
        runOnUiThread(() -> {
            lastFrameElapsedMs = android.os.SystemClock.elapsedRealtime();
            sceneModel.setTarget(targetRange, targetBearing);
            sceneModel.setRssDistance(rssDistance);
            sceneModel.setEgoSpeed(egoSpeed);
            sceneModel.setTargetPoints(targetPoints);
            sceneModel.setFrameAgeMs(0); // fresh at receipt; ticker ages it
            situationView.render(sceneModel.build());
            renderMetrics(targetRange, rssDistance, 0, egoSpeed);
            onFrame(new VisualizationStateReducer.FrameInput(
                    frame.getSequence(), intervention, warning, braking, lifecycle));
        });
    }

    private final SituationRenderModel.Builder sceneModel = new SituationRenderModel.Builder();

    private void tick() {
        final long now = android.os.SystemClock.elapsedRealtime();
        // Fail-closed: presentation goes stale when frames stop arriving.
        if (lastFrameElapsedMs > 0 && now - lastFrameElapsedMs > 1_000L) {
            onDisposition(reducer.onStale(now));
        }
        onDisposition(reducer.onTick(now));
        // Age the health chip; geometry stays untouched by age (pure test 10).
        if (lastFrameElapsedMs > 0) {
            lastFrameAgeMs = now - lastFrameElapsedMs;
            // Re-render chip + metric with the aged value (geometry unaffected).
            final long age = lastFrameAgeMs;
            runOnUiThread(() -> metricFrameAge.setText("Frame age  " + age + " ms"));
        }
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
        // Fail-closed scene: no live data -> empty scene (no synthetic marker).
        sceneModel.setDisposition(disposition);
        if (disposition == VisualizationStateReducer.Disposition.STALE
                || disposition == VisualizationStateReducer.Disposition.INVALID
                || disposition == VisualizationStateReducer.Disposition.UNAVAILABLE) {
            sceneModel.setTarget(null, null);
            sceneModel.setRssDistance(null);
            situationView.clearTrail();
        }
        SituationRenderModel model = sceneModel.build();
        situationView.render(model);
        renderStatePanel(disposition, model);
        renderHealthChip(model);
        provenanceView.setText(getString(R.string.provenance_chain));
    }

    private void renderStatePanel(VisualizationStateReducer.Disposition disposition,
                                  SituationRenderModel model) {
        // Panel color/icon authority is the model (reducer-driven only).
        final int color = model.getStateColorRgb();
        final String icon = model.getStateIconToken();
        setActiveState(stateMonitoring,
                VisualizationStateReducer.Disposition.MONITORING == disposition, color, icon);
        setActiveState(stateWarning,
                VisualizationStateReducer.Disposition.WARNING == disposition, color, icon);
        setActiveState(stateIntervention,
                VisualizationStateReducer.Disposition.INTERVENTION == disposition, color, icon);
        setActiveState(stateReleased,
                VisualizationStateReducer.Disposition.RELEASED == disposition, color, icon);
    }

    private void setActiveState(TextView view, boolean active, int color, String icon) {
        if (active) {
            // Color + icon + text: never color alone (contract §4).
            view.setTextColor(color);
            view.setText(icon + "  " + plainLabel(view));
        } else {
            view.setTextColor(Color.rgb(90, 100, 105));
        }
    }

    private static String plainLabel(TextView view) {
        // Strip the leading icon glyph from the string resource label.
        String text = view.getText().toString();
        int space = text.indexOf("  ");
        return space >= 0 ? text.substring(space + 2) : text;
    }

    private void renderHealthChip(SituationRenderModel model) {
        healthChip.setText("● " + model.getHealthLabel()
                + " · 10 Hz · age " + model.getFrameAgeText());
        healthChip.setTextColor(model.getHealthColorRgb());
    }

    private void renderMetrics(Float targetRange, Float rssDistance, long frameAgeMs, Float egoSpeed) {
        metricTargetRange.setText("Target range  "
                + (targetRange != null ? String.format(java.util.Locale.US, "%.1f m", targetRange) : "—"));
        metricRssDistance.setText("RSS distance  "
                + (rssDistance != null ? String.format(java.util.Locale.US, "%.1f m", rssDistance) : "—"));
        metricEgoSpeed.setText("Ego speed  "
                + (egoSpeed != null ? String.format(java.util.Locale.US, "%.0f km/h", egoSpeed * 3.6f) : "—"));
        metricFrameAge.setText("Frame age  "
                + (frameAgeMs >= 0 ? frameAgeMs + " ms" : "—"));
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
