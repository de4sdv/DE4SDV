# W2 batch 7 review — `ProductLineCharacteristic` definitions parity and `Scenario` bounded pattern grounding

Scope: two retained, ungated W2 `MODEL_AUTHORITY_PARITY` rows of the O4
execution register (`docs/method-conformance/o4/o4-execution-register.json`),
treated together as W2 batch 7 on branch `feat/o4-accelerated-safe-set-2`.
O1 authority decisions change for exactly these two rows
(`docs/method-conformance/o1/authority-review-decisions.yaml`); no other
decision row moves.

## 1. Why the #293 exclusion reasons are conservative, not gates

The accelerated safe-set 1 admission manifest pinned both rows with reason
keywords (`docs/method-conformance/o2plus/o2p-admission.yaml`):

| row | #293 reason | actual finding |
| --- | --- | --- |
| `ProductLineCharacteristic` | "depends on the decision-bound Feature/CommonCapability pair" | The dependency direction is inverted: the row is the classification **base**; `Feature`/`CommonCapability` are its decision-14-bound branches. The base row itself carries no open owner decision — its only open item was bounded documentation work. |
| `Scenario` | "no model-side declaration; treatment/model-representation decision outstanding" | The absence of a declaration is a representation fact, not an owner decision. The register's own desired target already bounds the treatment: "scenario-identity enum + operational-context pattern documented". That treatment uses machinery that already exists and needs no new modeling decision. |

Both rows are therefore treated as engineering. The admission manifest itself
is a shared binding owned by the parent integration (the conservative reason
strings become stale with this batch and must be refreshed there).

## 2. `ProductLineCharacteristic` — definitions parity (normalized-exact)

Treatment: the model doc is aligned to the reviewed definition text verbatim.
The four branches the register asked to document are the definition's own
content (common capability, feature candidate, deferred scope, native SysML v2
variation choice); no additional prose is added — extra sentences would break
normalized-exact parity.

- Model: `textual-notation-of-model/packages/methods/de4sdv/de4sdv_product_line.sysml`,
  `part def ProductLineCharacteristic` — doc now reads "The product-line
  classification base: a characteristic is a common capability, a feature
  candidate, deferred scope, or a native SysML v2 variation choice."
  (the reviewed definition in `approach/framework/ontology/de4sdv-basic-ontology.yaml`,
  `classes:ProductLineCharacteristic`).
- Machine check: `authority_inventory.doc_text_observation(...)` returns
  `normalized-exact` for that declaration — equality after cosmetic
  normalization only, no fuzzy comparison.
- Boundaries preserved: declaration name, classification-root position (no
  specialization), the four branch declarations, the native variation
  mechanism (`variation part def DeferredProductLineVariation` /
  `variant part deferredChoice;`) — all pinned by tests.
- O1 decision row: stage `o4-w2 batch 7 (definitions parity)`,
  `semantic_text_equivalence: null` (exact text needs no manual equivalence
  record), `authority_current` stays `legacy-yaml`, `evidence_state` stays
  `repository-evidenced`; the only residual is O2 admission.

## 3. `Scenario` — bounded pattern grounding (no native claim, no reviewed-equivalent)

The register's desired target for this row is "model-authoritative after
parity (scenario-identity enum + operational-context pattern documented)".
The honest treatment is exactly that pattern documentation — nothing stronger:

- Representation anchors already in the model: five scenario-identity enum
  declarations (`MiddlewareScenarioIdentity`,
  `OverrideScenarioIdentity`, `NonActivationScenarioIdentity`,
  `DegradedInputScenarioIdentity`, `RegulatoryCriterionScenarioIdentity`) plus
  the operational-context part pattern
  (`de4sdv_operational_context.sysml`: `OperationalEntity` and its
  specializations).
- Existing machinery: `scripts/check_model_sync.py` sync point 1
  (`SCENARIO_IDENTITY_MAP`) binds the three AEB scenario-identity enums to the
  evaluator enums; the review runs that check in-process and requires zero
  errors.
- Claim boundary: representation is not semantics. The row keeps
  `authority_current: legacy-yaml` (no native promotion), keeps
  `semantic_text_equivalence: null`, and claims no reviewed-equivalent
  record — there is no model-side declaration to review, and
  `REVIEWED_EQUIVALENT_OBSERVATIONS` permits the reviewed-equivalent state
  only for a differing doc observation. "No model-side declaration" is
  therefore recorded as an open, forward obligation, not silently converted
  into parity.
- O1 decision row: stage `o4-w2 batch 7 (bounded pattern grounding)`,
  confidence stays `medium`, required evidence stays forward-only
  (O2 admission from the reviewed pattern representation; definition-level
  parity stays open until a model-side declaration exists).

## 4. Machine locks

`tests/test_o4_accelerated_safe_set_2.py` — per-row precision matrix:
batch scope, exact stages, the machine-checked parity observation, the
bounded Scenario state, the sync point 1 binding, classification-root and
native-variation boundaries, O3 exact-thirteen and projection non-promotion,
prior-batch stage pins, and the Commit-B artifact-vs-source consistency gate
(expected red until the inventory is regenerated).

Older pins updated deliberately (later-batch convention):
`tests/test_o4_w2_batch6_definitions_parity.py` no longer asserts the old
`ProductLineCharacteristic` doc text or its pre-parity stage.

## 5. Remaining requirements (parent integration)

1. Regenerate the O1 inventory (`semantic-authority-inventory.json` and
   `authority-inventory.md`) from these sources; the artifact-consistency
   test in the batch test file is the Commit-B gate. The same regeneration
   rebinds the artifacts that also record `de4sdv_product_line.sysml` as a
   bound input (O2 semantic projections v1.1 / v1.2, O2+ projection) — the
   `check_repo.py` binding gates stay red until that rebind.
2. Distribution lock updated in this batch:
   `tests/test_semantic_authority_inventory.py`
   (`TestTextParity::test_doc_observations_recomputed_from_source`) now
   expects differs 18 / normalized-exact 20 (doc-absent 1 / doc-absent
   bodyless 1 unchanged), with the W2 batch 7 movement recorded in its
   running commentary. No further lock change is needed.
3. Refresh the admission manifest reason strings for both rows
   (`o2plus/o2p-admission.yaml`) and the safe-set 1 exclusion pins
   (`tests/test_o4_accelerated_safe_set_1.py::EXCLUDED_REASON_KEYWORDS`) as
   part of the shared integration.
4. Regenerate the O4 execution register only if its generation input
   (governed review) changes; this batch changes O1 decisions, not the
   review.
5. No new dependencies, no runtime change, no O3 migration, no privileged
   validation scope change (the model edit is doc-only inside a declaration
   whose name and structure are unchanged; check the Privileged Syside
   Validation diagram step for the middleware product-line classification
   view — the committed diagram does not embed the edited doc text, so no
   diagram tail is expected).
