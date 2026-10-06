# Acceptance decision registry

The maintainer activated
[`de4sdv.acceptance.maintainer-decision.v1`](../method-conformance/acceptance-policy.md)
as written on 2026-10-05. This registry currently contains **zero acceptance
decisions**; activation is not acceptance of the INC-AEBS-009D campaign.

The scanner reads only `.yaml`, `.yml`, and `.json` decision records. This
README is ignored. A complete scan of this README-only registry is
`scanned-clean` with zero decisions: uncovered profiles are
`ASSESSED`/`COMPLETE`/`FAIL` (`ACCEPTANCE_AUTHORITY_MISSING`), not PASS and not
missing-input INDETERMINATE.

Only Orkun Yilmaz acting as DE4SDV maintainer may authorize and commit a
decision under the active policy. Synthetic test records belong in temporary
fixtures, never in this registry.
