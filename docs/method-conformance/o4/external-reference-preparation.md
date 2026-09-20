# External evidence-reference contract — preparation (O4 W5 boundary rows)

Status: **PREPARED — typed-reference schema/profile contract only; no boundary
crossing, no row closure.** This package does not activate traversal, does not
mirror content, does not keep a baseline list, and does not change any governed
state.

## Determination requested by the execution strategy: A (machinery gap)

The execution strategy asked whether the missing contract for
`EvidenceArtifact`, `hasEvidence` and `capturedInBaseline` is

- **A** — already semantically governed, merely missing implementation
  machinery; or
- **B** — genuinely missing an owner semantic decision.

Determination: **A for the validation contract and the typed-reference
schema/profile entries implemented here.** The reviewed definitions already
state exactly what a reference must carry and what it must not imply:

- `hasEvidence`: "Verification case is associated with an externally retained
  evidence artifact whose identity, digest, run and tested scope are explicit;
  association implies neither pass nor acceptance."
- `capturedInBaseline`: "Evidence artifact version is explicitly included in an
  immutable identified baseline manifest; inclusion does not itself approve
  evidence."
- `EvidenceArtifact`: "A reviewable artifact that supports a verification,
  validation, assurance, or release decision." External evidence systems hold
  the content; the model owns only the typed reference schema.
- `Baseline` (the referenced boundary identity): "A reviewed and controlled
  state of model, evidence, configuration, or publication artifacts,
  referenced without implying accepted evidence. (Keep; content stays
  external.)"

No either/or semantic choice remains open in those statements. What was
missing is (a) fail-closed machinery that validates supplied records against
them and (b) the reviewed **typed-reference schema/profile entries** the W5
exit requires — implemented in `de4sdv/semantic/external_reference_contract.py`
and recorded in `docs/method-conformance/o4/external-reference-profile.yaml`.

**Explicit non-determinations (kept out of this package):** any traversal or
representation activation remains governed by the review's "T/E
evidence-reference design (boundary retained until reviewed)" evidence item —
that design remains the gate for stronger claims, and these rows stay open. The
machinery adds no authority; it only refuses malformed, claim-inflating or
foreign-shaped records.

## Contract (supplied records)

| function | validates | guarantees |
| --- | --- | --- |
| `validate_typed_reference` (alias `validate_evidence_reference`) | case identity, artifact identity, exact revision, sha256 digest, run, non-empty tested scope; `@` is refused inside identity/revision so the version identity stays unambiguous | normalized record with the exact version identity; `implies_pass`/`implies_verification`/`implies_acceptance` machine-locked `False`; `traversal` `False`; `runtime_support` `external`; `content_mirrored` `False` |
| `validate_baseline_manifest` | baseline identity, manifest digest, non-empty immutable version-identity entries | normalized manifest; `second_baseline_list` `False` |
| `baseline_inclusion` | exact version-identity membership (`<artifact_identity>@<artifact_revision>`) in the identified manifest | `included` is explicit; a different revision is **not** included (no carry-forward); `implies_approval`/`implies_pass`/`implies_acceptance` machine-locked `False` |
| `association_state` | reference validity | the only state an association may expose; no verdict fields |
| `external_boundary_state` | row identity | the blocked-state surface a query must report: external facts retained, no traversal, no mirroring |

## Prepared profile artifact (`external-reference-profile.yaml`)

- `typed_reference_schema: de4sdv.evidence-reference/v1` — the six reviewed
  fields, the exact version-identity form, the forbidden record fields
  (verdict/pass/acceptance/approval/status/traversal/`sysml_mapping`/implied
  flags), and the machine-locked boundary values.
- `baseline_manifest_schema: de4sdv.baseline-manifest-reference/v1` — identity,
  manifest digest, version-identity entries, exact-membership rule, no second
  baseline list.
- `profile_entries` — one entry per family row: `external-reference-record` for
  `EvidenceArtifact`/`hasEvidence`/`capturedInBaseline` (mechanics only, no API
  element identity claimed) and `model-resident-boundary-identity` for
  `Baseline` (the existing `part def DE4SDVEvidenceBaseline`, parity only, no
  rename).
- **Family lock:** `expected_rows` is *derived* from the governed register —
  every row with `KEEP_EXTERNAL_REFERENCE`, `dependency_flags.evidence_lineage
  true`, no projection/profile requirement, no traversal, external runtime
  target. The derived set is exactly `Baseline`, `EvidenceArtifact`,
  `capturedInBaseline`, `hasEvidence`; `scope_rows` names the three W5 rows.
  A register/review edit that adds or removes such a row breaks generation
  instead of silently changing the contract.

## Fail-closed properties (test-locked)

- Missing/malformed case identity, artifact identity, revision, digest
  (non-sha256 or wrong length), run, scope (empty or non-string items) refuse.
- Any supplied record carrying a claim-inflating or traversal-overloading field
  refuses (`verdict`, `passed`, `accepted`, `approval`, `status`, `traversal`,
  `sysml_mapping`, `implies_*`).
- A baseline manifest without identity or entries refuses; membership of a
  different revision refuses (not included).
- The prepared profile refuses: family drift, weakened schema blocks, unknown
  profile-entry keys, entries outside the family, missing entries for family
  rows, missing declarations, and reviewed disposition/flag changes
  (`REDESIGN`, traversal, projection/profile required, non-external runtime
  target).
- No output ever carries verdict/pass/acceptance/approval fields; the contract
  never fetches content (source-scan test) and is read-only; it is never
  imported by the runtime.

## W5 exit mapping (register: "contract docs + profile entries; no traversal; blocked-state surfaced wherever queried")

| exit element | state |
| --- | --- |
| contract docs | this document + the profile artifact |
| profile entries | `profile_entries` for all four derived family rows, machine-locked |
| no traversal | `traversal: false` in the schema block, in every profile row and in every output; `sysml_mapping`/traversal record fields refused |
| blocked-state surfaced | `external_boundary_state` + external/no-traversal fields on every association output |

The three rows keep their reviewed external-boundary state and their "T/E
evidence-reference design" evidence item. **No row is closed by this package.**

## Exact remaining integration changes (parent)

1. Wire `de4sdv/semantic/external_reference_contract.py:run_check_errors` into
   `scripts/check_repo.py` next to the other O4 checks (the hook is the only
   integration point this package does not add).
2. Regenerate the O4 execution register / O1 inventory evidence rows for
   `EvidenceArtifact`, `hasEvidence`, `capturedInBaseline` (and `Baseline` as
   the referenced identity) under the two-commit pattern, recording this
   contract + profile as their evidence.
3. Record the reviewed acceptance of the typed-reference schema/profile entries
   (retirement precondition of the three YAML rows); this artifact is the
   prepared design that acceptance would consume — it is not that acceptance.
4. Row closure stays open until the reviewed evidence items resolve; any future
   traversal/representation change for these rows goes through the normal
   reviewed path.
