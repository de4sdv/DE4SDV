# O4 definition-candidate loader

## Problem

The admitted definition family of `docs/method-conformance/o4/definition-admission.yaml`
is published as a generated pair — `definition-projection.json` (definition
meaning + grounding) and `definition-profile.json` (representation mechanics).
Candidate consumers need to read that pair offline without re-implementing its
validation rules, and a corrupted or stale pair must never load silently.

## Solution

`de4sdv/semantic/definition_candidate.py` exposes one fail-closed, read-only
loader:

```python
from de4sdv.semantic.definition_candidate import load_definition_candidate

candidate = load_definition_candidate(root)          # verified load
candidate.identities                                  # admitted identities
candidate.row_for(identity)                           # published projection row
candidate.entry_for(identity)                         # published profile entry
```

The loader creates no semantics: rows and entries are returned exactly as
published, no traversal is implemented or claimed, and no runtime module reads
them. It is not an authority transition and not a support promotion.

## Fail-closed rules

* Both artifacts must exist, parse as JSON objects, and carry their published
  schemas (`de4sdv.o4-definition-projection/v1`, `de4sdv.o4-definition-profile/v1`)
  with status `admitted`.
* The pair must share one identical binding and one identical identity set in
  both directions across rows, profile entries, and `scope.admitted`; missing
  entries, duplicates, scope drift, and a per-row `profile_identity` mismatch
  are refused.
* Every projection row's kernel binding contract must agree with its profile
  entry echo (source file + declaration).
* The pair must not overlap the frozen O3 migrated identity set, imported from
  `de4sdv.semantic.o3_bundle` — never a second hard-coded list.
* The recorded revision binding is always
  validated through the existing `authority_inventory.validate_source_binding`,
  and the committed bytes are checked against regeneration through the existing
  `definition_projection.run_check_errors`; a tampered artifact or a stale
  revision is refused instead of loaded. There is no public verification bypass.
  Synthetic structural tests mock the validators only within the test context;
  the real-repository test executes both validators.
* Returned mappings are recursively immutable, including binding metadata and
  nested definitions/profile entries. Nested lists are exposed as tuples;
  the published values are preserved.
* The candidate uses slots to prevent instance-dictionary replacement. The pair
  is read again after validation and must equal the initially parsed documents.
  This detects observed snapshot drift; it is not an atomic filesystem lock.

## Non-claims

Offline candidate consumption only. This loader does not migrate consumers, does
not retire authored governance YAML, does not select a runtime authority, and
is not wired into the repository check yet.
