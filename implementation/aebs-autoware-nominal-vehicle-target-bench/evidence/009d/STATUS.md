# INC-AEBS-009D evidence status

**Status: not live executed.**

The runtime, per-profile evidence builder, and independent replay validator are implemented for all six typed override profiles. No 009D run bundle or canonical verdict is retained in this change. Running `scripts/run_override_matrix.sh` performs six serial isolated runs; each profile is promoted only to its own `evidence/009d/profiles/<profile>/scenario-evidence.json` after independent replay validation.

This increment makes no safety, certification, compliance, homologation, or type-approval claim. Existing `evidence/009b` records are not an output target of the 009D runners.
