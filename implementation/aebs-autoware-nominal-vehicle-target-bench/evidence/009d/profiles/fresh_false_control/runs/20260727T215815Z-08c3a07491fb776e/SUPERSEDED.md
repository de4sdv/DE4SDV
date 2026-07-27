# Superseded validated profile run

This isolated `fresh_false_control` run passed its contract and independent replay at repository head `d4408f0f08d1314d3296fd5f9e25efc9182d9959`.

It is not canonical for the final matrix. The subsequent `fresh_true_conscious_override` run proved that warning generation was incorrectly gated on control-clear state, making conscious-override warning evidence impossible. The coordinator was changed so warning transition is risk-driven and independent of override disposition.

The validated evidence bytes remain in `scenario-evidence.validated-superseded.json` with SHA-256 `2c7e906e3118275e148d28a2d628d9ec22460e2313fff86af9687863b005111e`. This run must not be aggregated with executions from the repaired head.
