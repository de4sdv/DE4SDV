# Method conformance (moved)

This directory used to hold the method evaluation specification, the
semantic contract data and the ontology migration records. The specification
is in [`docs/method-evaluation/`](../method-evaluation/README.md), the data
the runtime reads is in
[`de4sdv/semantic/contract-data/`](../../de4sdv/semantic/contract-data/README.md),
and the migration records are archived at the
[`release-2026-10-11`](https://github.com/de4sdv/DE4SDV/tree/release-2026-10-11/docs/method-conformance)
tag.

One record stays here:
[`o4/external-reference-acceptance-review.md`](o4/external-reference-acceptance-review.md).
The external-reference profile pins its bytes, and it pins the profile's
reviewed payload, which names the paths the profile was accepted with. Moving
it means updating both digest records in a deliberate review.
