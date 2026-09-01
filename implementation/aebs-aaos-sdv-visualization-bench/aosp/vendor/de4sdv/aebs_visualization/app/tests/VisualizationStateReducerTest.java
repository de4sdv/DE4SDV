package org.de4sdv.aebsvisualization;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import org.junit.Test;
import org.junit.runner.RunWith;
import org.junit.runners.JUnit4;

/** Pure-JVM tests for the presentation state machine (mirrors the SysML machine). */
@RunWith(JUnit4.class)
public class VisualizationStateReducerTest {

    private static final long T0 = 1_000L;

    private static VisualizationStateReducer.FrameInput frame(long seq, boolean intervention,
                                                              boolean warning, boolean braking,
                                                              String lifecycle) {
        return new VisualizationStateReducer.FrameInput(seq, intervention, warning, braking, lifecycle);
    }

    @Test
    public void startsUnavailable() {
        VisualizationStateReducer reducer = new VisualizationStateReducer();
        assertEquals(VisualizationStateReducer.Disposition.UNAVAILABLE, reducer.disposition());
    }

    @Test
    public void threeConsecutiveFramesLeaveUnavailableIntoMonitoring() {
        VisualizationStateReducer reducer = new VisualizationStateReducer();
        reducer.onFrame(frame(1, false, false, false, "armed"), T0);
        assertEquals(VisualizationStateReducer.Disposition.UNAVAILABLE, reducer.disposition());
        reducer.onFrame(frame(2, false, false, false, "armed"), T0 + 10);
        // Third consecutive frame exits UNAVAILABLE into the transient RESTORED
        // indication (SysML VisualizationPresentationMachine); MONITORING comes
        // after the RESTORED hold expires via onTick.
        assertEquals(VisualizationStateReducer.Disposition.RESTORED,
                reducer.onFrame(frame(3, false, false, false, "armed"), T0 + 20));
        assertEquals(VisualizationStateReducer.Disposition.MONITORING,
                reducer.onTick(T0 + 20 + 2_000 + 1));
    }

    @Test
    public void warningPrecedesIntervention() {
        VisualizationStateReducer reducer = healthy();
        assertEquals(VisualizationStateReducer.Disposition.WARNING,
                reducer.onFrame(frame(4, false, true, false, "armed"), T0 + 30));
        assertEquals(VisualizationStateReducer.Disposition.INTERVENTION,
                reducer.onFrame(frame(5, true, true, false, "braking_latched"), T0 + 40));
    }

    @Test
    public void releasedOnlyFromCoordinatorLifecycle() {
        VisualizationStateReducer reducer = healthy();
        reducer.onFrame(frame(4, true, true, true, "braking_latched"), T0 + 30);
        assertEquals(VisualizationStateReducer.Disposition.INTERVENTION, reducer.disposition());
        // UI does not invent release before the coordinator publishes it.
        assertEquals(VisualizationStateReducer.Disposition.RELEASED,
                reducer.onFrame(frame(5, false, false, false, "released_verified_stop"), T0 + 40));
    }

    @Test
    public void staleSuppressesPresentation() {
        VisualizationStateReducer reducer = healthy();
        assertEquals(VisualizationStateReducer.Disposition.STALE, reducer.onStale(T0 + 5_000));
        // Frames during stale do not immediately restore.
        reducer.onFrame(frame(6, false, false, false, "armed"), T0 + 5_100);
        assertEquals(VisualizationStateReducer.Disposition.STALE, reducer.disposition());
    }

    @Test
    public void restoredIsTransientAfterConsecutiveFrames() {
        VisualizationStateReducer reducer = healthy();
        reducer.onStale(T0 + 5_000);
        reducer.onFrame(frame(6, false, false, false, "armed"), T0 + 5_100);
        reducer.onFrame(frame(7, false, false, false, "armed"), T0 + 5_200);
        assertEquals(VisualizationStateReducer.Disposition.RESTORED,
                reducer.onFrame(frame(8, false, false, false, "armed"), T0 + 5_300));
        // Hold expires -> back to live source state.
        assertEquals(VisualizationStateReducer.Disposition.MONITORING,
                reducer.onTick(T0 + 7_300 + 1));
    }

    @Test
    public void invalidFramesFailClosed() {
        VisualizationStateReducer reducer = healthy();
        assertEquals(VisualizationStateReducer.Disposition.INVALID, reducer.onInvalid(T0 + 100));
    }

    @Test
    public void duplicateSequenceFailsClosed() {
        VisualizationStateReducer reducer = healthy();
        assertEquals(VisualizationStateReducer.Disposition.INVALID,
                reducer.onFrame(frame(3, false, false, false, "armed"), T0 + 50));
    }

    @Test
    public void labelsAreDisplayDerived() {
        assertTrue(VisualizationStateReducer.label(
                VisualizationStateReducer.Disposition.INTERVENTION).contains("intervention"));
    }

    private static VisualizationStateReducer healthy() {
        VisualizationStateReducer reducer = new VisualizationStateReducer();
        reducer.onFrame(frame(1, false, false, false, "armed"), T0);
        reducer.onFrame(frame(2, false, false, false, "armed"), T0 + 10);
        reducer.onFrame(frame(3, false, false, false, "armed"), T0 + 20);
        return reducer;
    }
}
