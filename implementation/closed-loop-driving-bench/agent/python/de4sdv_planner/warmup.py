"""inferPlan's warm-up of the checkpoint's camera history cache while the agent primes.

The checkpoint keeps one StatefulCameraFPNCache stream per 100 ms phase. A call is warm only when its
stream holds the 7 history frames and its last commit was exactly 0.5 s earlier; otherwise the model
re-encodes the 7 history frames from the raw tiles, which on the G4 takes longer than a frame (119 ms
against 91 ms warm). FEO runs the agent's activities as one chain per frame event, and the bench's
event trigger merges a backlog into one chain for the newest frame, so a run of cold calls loses a
frame, and a lost frame breaks the 66-pose ego history.

While the agent primes (camera history complete, ego history not yet), inferPlan calls the engine on the
frame's phase stream with the real tiles and timestamps and discards the output (the cache holds only
camera pyramids, so the placeholder ego history leaves it exactly as a planning call would). This
scheduler decides whether to call: a call that keeps a warm stream warm costs less than a frame and
always runs; a call that primes a cold stream runs only when the lag it leaves stays within
`lag_limit_ms`, so the chain never falls a frame behind. By the first plan every stream is warm.
"""


class WarmupScheduler:
    def __init__(self, period_ms=100.0, lag_limit_ms=50.0, chain_ms=5.0, cold_ms=121.0, warm_ms=91.3,
                 alpha=0.2):
        self.period_ms = float(period_ms)
        self.lag_limit_ms = float(lag_limit_ms)
        self.chain_ms = float(chain_ms)          # the chain without an engine call
        self.cost_ms = {"cold": float(cold_ms), "warm": float(warm_ms)}
        self.alpha = float(alpha)
        self.lag_ms = 0.0
        self._prev = None

    def observe_step_start(self, frame, t_s):
        """At the start of every chain (conditionInputs' call): how far the chain start trails the
        frame grid. Merged frames count as on schedule, so the lag is the chain's own delay."""
        if self._prev is not None and frame > self._prev[0]:
            prev_frame, prev_t = self._prev
            self.lag_ms = max(0.0, self.lag_ms + (t_s - prev_t) * 1000.0 - self.period_ms * (frame - prev_frame))
        self._prev = (frame, t_s)

    def predicted_lag_ms(self, kind):
        """The lag at the next chain start after a call of this kind (the next frame 100 ms later)."""
        return max(0.0, self.lag_ms + self.chain_ms + self.cost_ms[kind] - self.period_ms)

    def decide(self, frame, stream_warm):
        """('warm' | 'cold' | 'skip', reason) for the frame's phase stream."""
        kind = "warm" if stream_warm else "cold"
        predicted = self.predicted_lag_ms(kind)
        if predicted > self.lag_limit_ms and predicted > self.lag_ms:
            return "skip", "predicted lag %.0f ms after a %s call, limit %.0f ms" % (predicted, kind, self.lag_limit_ms)
        return kind, "keeps the stream warm" if stream_warm else "primes the stream"

    def record(self, kind, ms):
        """The measured duration of a call (moving average)."""
        self.cost_ms[kind] = (1.0 - self.alpha) * self.cost_ms[kind] + self.alpha * float(ms)
