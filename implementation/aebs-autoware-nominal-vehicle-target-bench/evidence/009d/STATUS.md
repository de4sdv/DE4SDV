# INC-AEBS-009D evidence status

**Status: executed and independently replay-validated; pending exact-head review.**

All six typed override profiles were executed separately against the pinned runtime at repository head `01d9f586865bf7fb4bc0b3f76be2b5a916451da4`. Each immutable run has its own canonical record under `evidence/009d/profiles/<profile>/scenario-evidence.json`, and all six records pass independent retained-evidence replay:

- `fresh_false_control`: `20260727T222251Z-4707ce355b002877` — exact fresh false input, native intervention, and braking observed.
- `fresh_true_conscious_override`: `20260727T222325Z-d6cda4ace4b3a9ca` — exact fresh true input, native intervention observed, and coordinator braking suppressed through the closed window.
- `stale`: `20260727T222349Z-6e37a8918a5c1c0d` — stale input classified and fail-safe braking observed.
- `missing`: `20260727T222413Z-f0ea050ad48a6ddc` — missing input classified and fail-safe braking observed.
- `malformed`: `20260727T222437Z-55a2f68f1d7f4392` — malformed zero-stamped input classified and fail-safe braking observed.
- `future_stamped`: `20260727T222501Z-41ec851352de2276` — future-stamped input classified and fail-safe braking observed.

Only a fresh, source-bound true input is treated as a conscious override. False, missing, stale, malformed, and future-stamped inputs are not overrides and do not suppress fail-safe braking.

This bounded campaign remains pending exact-head independent review. It makes no broad safety, certification, compliance, homologation, or type-approval claim. Existing `evidence/009b` records are not an output target of the 009D runners.
