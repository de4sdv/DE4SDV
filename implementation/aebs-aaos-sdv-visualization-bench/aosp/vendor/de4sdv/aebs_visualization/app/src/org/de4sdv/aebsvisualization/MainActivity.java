package org.de4sdv.aebsvisualization;

import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
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
    private HandlerThread tickerThread;
    private Handler tickerHandler;
    private long lastFrameElapsedMs;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        reducer = new VisualizationStateReducer();
        dispositionView = findViewById(R.id.disposition);
        provenanceView = findViewById(R.id.provenance);

        tickerThread = new HandlerThread("aebs010-tick");
        tickerThread.start();
        tickerHandler = new Handler(tickerThread.getLooper());
        tickerHandler.postDelayed(this::tick, 200);
        render();
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
        super.onDestroy();
    }
}
