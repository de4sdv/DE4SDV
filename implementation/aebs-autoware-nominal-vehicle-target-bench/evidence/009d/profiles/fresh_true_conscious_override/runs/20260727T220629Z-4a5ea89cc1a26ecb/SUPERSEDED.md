# Superseded validated profile run

This isolated `fresh_true_conscious_override` run passed its contract and independent replay at repository head `19b8d02a9cee1d85c65d977824567694b8b76db4`.

It is not canonical for the final matrix because subsequent execution exposed that stale, missing, malformed, and future-stamped inputs were incorrectly modeled as braking suppressors. The matrix and coordinator were changed so only an exact fresh conscious override suppresses braking; every non-override disposition authorizes fail-safe braking while retaining its exact diagnostic classification.

The validated evidence bytes remain in `scenario-evidence.validated-superseded.json` with SHA-256 `95e1e847132f533a5b3d4bd74b56a05061f948db820c216b4c475efff428b894`. This run must not be aggregated with executions from the corrected matrix head.
