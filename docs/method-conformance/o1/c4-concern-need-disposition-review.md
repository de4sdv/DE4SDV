# O1 c4 — concern–need semantic disposition review: `derivesNeedFromConcern` retired without replacement

**Scope:** exactly one semantic identity — relationship `derivesNeedFromConcern`
(`Need -> Concern`). No class and no second predicate is part of c4.
`Concern`, `Need`, `Stakeholder`, `Viewpoint`, `View`, `addressesConcern`
(`EngineeringIncrement -> Concern`), native framed-concern semantics, and the
Need `source`/`rationale` provenance attributes were inspected as
supporting/grounding evidence only; none of them is a promoted, migrated, or
modified c4 row.

**Boundary:** O1 review record under `docs/method-conformance/o1/`
(PR #249, branch `feat/o1-semantic-authority-inventory`, base `e99f46d0` =
`origin/main` at task start). `authority_current` stays `legacy-yaml` — no O3
cutover, no runtime change, no model change, no semantic-authority change, no
authored-YAML removal (that removal belongs to its reviewed downstream gate),
and no privileged ingestion. The reviewed decision lives in
`authority-review-decisions.yaml`; the machine locks live in
`tests/test_o1_c4_concern_need_disposition.py`. The retirement-state schema
adjustment in `de4sdv/semantic/authority_inventory.py` is governance-only:
that module is runtime-inert (the semantic runtime never imports it) and the
adjustment changes no runtime semantics.

**Governing question:**

> Does DE4SDV actually require a first-class semantic relationship between
> Need and Concern, and if so, what exact engineering claim does it make?

**Reviewed answer (Outcome A):** No. `derivesNeedFromConcern` is retired
without replacement. It has no required engineering meaning in the target
architecture, no witness, and no consumer; Native Concern/Viewpoint semantics
plus the existing Need `source`/`rationale` provenance already answer every
current question. The pre-assumed predicate must not be emitted as an active
O2 Semantic Projection relation.

---

## 1. Claim decomposition — three claims that are NOT interchangeable

The pre-assumed row was evaluated against three distinct candidate claims.
Each claim was tested on its own evidence; no witness was used to justify a
different claim.

| # | Candidate claim | Exact meaning if modeled | Witness required |
|---|---|---|---|
| 1 | **Origin provenance** | "Need N originated from Concern C" | a real need whose recorded origin is a modeled concern usage |
| 2 | **Native framing / required constraint** | "Need N frames Concern C as a required constraint" | a need that frames a concern (FramedConcernMembership) |
| 3 | **Weak concern addressing** | "Need N addresses Concern C" | a concrete engineering/query need for the weak claim plus model witness semantics |

These meanings are distinct and none implies another: provenance says nothing
about required constraints; framing asserts a satisfaction condition, not an
origin; addressing is weaker than both. General machine-queryable provenance
remains deferred unless separately justified (no generic `traceToSource`
predicate in this batch).

---

## 2. Evidence review (exact current revision)

### 2.1 Concern definitions and usages — the concern-usage inventory

Scope counts for this review: **89 governed concern usages**; **23 governed
need usages** (all carrying source and rationale); **68 governed frame
sites**, all viewpoint-owned; zero requirement-owned frame sites; zero direct
need-to-concern links.

The c4 gate condition ("concern-usage inventory resolves endpoint semantics")
is resolved. Inspected by model scan over the governed packages:

- **Concern definitions (60):** 54 in `packages/methods/saf/SAF_Viewpoints.sysml`
  (the GfSE SAF concern/viewpoint library used by DE4SDV) and 6 in
  `packages/methods/de4sdv/de4sdv_method_concerns_and_viewpoints.sysml`
  (DE4SDV method-governance concerns).
- **Concern usages (89):** 81 in feature slices (`packages/features/aebs` 56,
  `packages/features/middleware` 25), 5 in architecture packages
  (`execution_environments` 2, `aaos_sdv_middleware_boundary` 1,
  `sdv_platform_stack` 1, `vehicle_sensing_boundary` 1), 1 in
  `de4sdv_method_process.sysml`, and 2 in
  `model-based-product-line-engineering/product-models/aebs_autoware_reference_product.sysml`.
- The feature-slice concern usages are the SAF stakeholder/method concerns for
  those slices (e.g. `stakeholderNeedsConcern : StakeholderNeedsConcern`,
  `requirementTraceConcern : RequirementTraceConcern`,
  `visualizationScenarioConcern : OperationalContextConcern`). They are
  slice-level declarations whose only semantic connection is through the
  `viewpoint` usages that frame them.
- **No concern usage is owned by, nested in, or framed by a requirement
  usage** — the one structural pattern that could ground claim 1 or 2 does not
  exist in the governed model.

### 2.2 Need usages and the recorded provenance practice

- **Real need usages (23):** `aebs_needs_requirements.sysml` 9,
  `aebs_visualization_needs_requirements.sysml` 5,
  `middleware_stakeholder_needs.sysml` 9 — all typed by
  `StakeholderNeedCandidate` specializations (requirement-like usages).
- **Every one of the 23 carries both `source` and `rationale`** (the adopted
  NRM Ch. 15 attribute practice via ADR 0009 and
  `RequirementsManagementAttributeBase`). Recorded sources name increments
  ("INC-MW-002 operational context and INC-MW-003 feature classification"),
  framing/context artifacts, feature classification, controlled regulation
  anchors (`SRC-UNECE-R152` source metadata), governance policy, QA-review
  baselines, and method workflow — **none names or links a modeled concern
  usage**. Two rationales mention "stakeholder concern" as prose ("a distinct
  stakeholder concern"), which is a risk-domain description in free text, not
  a semantic relation.
- The traceability need itself makes the obligation explicit in the model:
  N-MW-006 `needTraceabilityToOperationalContext` requires needs to "maintain
  trace links from stakeholder needs to the operational context scenarios
  defined in INC-MW-002 and the feature classifications defined in INC-MW-003"
  — the governed need-trace obligations target operational context and feature
  classification, not concerns. Derived requirements already trace to needs
  through the K `DerivesFromNeed` connection (reverse direction).

### 2.3 Native framing usage reality — `frame` scan

Full repository scan for `frame` concern usages (`.sysand` and `experiments/`
excluded):

| Population | Count | Owner |
|---|---|---|
| Governed `frame` sites | **68** | **all viewpoint-owned** (61 feature slices, 4 architecture packages, 1 method process, 2 MBPLE product models) |
| `frame` sites inside requirement/need usages | **0** | — |
| Typed `frame x : T;` declaration forms | **0** | — |
| Explicit `framedConcern` attribute writes in the model | **0** | — |
| Non-governed synthetic fixture sites | 2 | `tests/fixtures/sysml_viewer_model` (viewer test fixture; recorded for honesty, not governed content) |

**Actual Needs do not frame Concerns today.** No `frame concern` was added for
this review — no witness was manufactured.

### 2.4 The documented DE4SDV modeling rule

`methodologies/sysmod-sysmlv2/pilots/aebs-needs-requirements.md:214` (the
INC-AEBS-003 record): "Stakeholder needs are specified only as requirement-like
usages typed by `StakeholderNeedCandidate` specializations; **they are not
duplicated as concerns**." The rule stands unchanged and matches the model
scan above.

### 2.5 Pinned SysML library semantics — framing and required constraints

Inspected in the pinned standard library shipped with the locked toolchain
(`sysand-lock.toml`; local toolchain distribution of `Systems Library`,
`sensmetry-syside` library sources for the pinned version). Load-bearing
definition facts:

- `ConcernDefinition specializes RequirementDefinition`; `ConcernUsage
  specializes RequirementUsage` with `concernDefinition : ConcernDefinition[0..1]
  redefines requirementDefinition`. A concern is itself a requirement-like
  check (`ConcernCheck :> RequirementCheck` — "the base type of all
  ConcernDefinitions"; `concernChecks` — "the base feature of all
  ConcernUsages"; `concernChecks :> requirementChecks`).
- `RequirementConstraintMembership specializes FeatureMembership` with
  `kind : RequirementConstraintKind[1..1]` and
  `ownedConstraint`/`referencedConstraint : ConstraintUsage[1..1]`.
- `FramedConcernMembership specializes RequirementConstraintMembership` with
  `ownedConcern`/`referencedConcern : ConcernUsage[1..1]` redefining
  `ownedConstraint`/`referencedConstraint`.
- **`RequirementUsage::framedConcern : ConcernUsage[0..*] ordered subsets
  requiredConstraint`** (identically on `RequirementDefinition`). A framed
  concern is therefore one of the framing element's **required constraints**.
- `RequirementCheck::concerns[0..*] :> concernChecks, subrequirements` — "The
  checks of any concerns being addressed (as required constraints)."
- `ViewpointCheck` — "a RequirementCheck for checking if a View meets the
  concerns of viewpoint stakeholders."

**Semantic reading:** native framing asserts *concern as required constraint
of the framing element* — a satisfaction-condition claim. It is **not**
provenance ("originated from") and **not** weak addressing. The mechanism is
natively available for requirement-like owners, but its exact semantics must
match the engineering claim before selection — and it does not (see §3).

### 2.6 NRM source/provenance conclusion

- Concerns may be sources of stakeholder needs in particular cases; the NRM
  Ch. 15 A3 source catalog ("Trace to Source") is broader than concerns —
  "stakeholder interview, mission, goals, user story, organization department
  ..., analysis" — regulations, and standards.
- Every need requires source traceability; that obligation is carried by the
  adopted `source` (A3) and `rationale` (A1) attributes and is discharged in
  all 23 governed need usages.
- **Do not infer that every Need derives from a Concern** — and no repository
  evidence establishes that even one does. The claim "Need N originated from
  Concern C" is not established as necessary.

### 2.7 Consumer / query / runtime finding

Repository-wide scan for the `derivesNeedFromConcern` token (whole repo,
excluding `.git`/`.sysand`/`node_modules`): the authored ontology row, the O1
governance artifacts and their tests, and the historical R0 inventory CSV.
**Zero runtime, MCP query, ImpactService, viewer, conformance-evaluator, or
model-transformation consumers exist.** The runtime support state is
`vocabulary-only` (no `sysml_mapping`); there is no executable strategy, no
mapping, and no generated projection row.

---

## 3. Native framing boundary analysis — five distinctions

Requested distinctions, resolved explicitly:

1. **Sharing the native Concern concept/type** — true by construction: the
   model's concerns are native `concern def`/`concern` elements. Sharing the
   type is not a Need↔Concern relation and was never in question.
2. **Referencing the same Concern usage** — no need usage references any
   concern usage; the only referrers are viewpoints (68 governed frame sites)
   and the concerns' own declarations.
3. **Framing a Concern as a required constraint** — natively defined
   (`FramedConcernMembership`; `framedConcern subsets requiredConstraint`).
   **DE4SDV does not want this claim for needs**: it would assert that each
   framing need's satisfaction condition includes the concern. No such intent
   or witness exists, and the model's framing practice is exclusively
   viewpoint↔view semantics. Rejected as a non-exact fit — not merely absent.
4. **Weakly addressing a stakeholder concern** — no DE4SDV meaning exists for
   a per-need "addresses" claim; concerns are addressed by the engineering
   work and made visible by views (native viewpoint framing), not asserted per
   need. No consumer; no witness semantics statable without invention.
5. **Recording provenance/source origin** — the actual mechanism is the free
   (controlled) textual `source`/`rationale` record; it is broader than
   concerns and already mandatory. A Need→Concern edge would not be an
   instance of this mechanism, and no repository evidence requires narrowing
   any need's origin to a concern.

The test applied: do both endpoints' native types suffice to classify the
relation as native? No — classification follows the **exact claim**, and the
framing mechanism's claim (required constraint) is not the claim any candidate
scenario actually needs. Naming a relation "native" because both endpoints use
native SysML constructs would be exactly the metaclass-name reasoning the
plan forbids (UG-28).

---

## 4. Identifier collision analysis — `addressesConcern`

The ontology already contains `addressesConcern : EngineeringIncrement ->
Concern` (increment-level concern addressing; vocabulary-only, no mapping, no
consumer beyond governance). Consequences applied in c4:

- `addressesConcern` is **not** redefined as `Need -> Concern`, **not**
  generalized, and **not** changed: domain, range, stage, disposition, and
  targets remain exactly as recorded (`legacy-yaml -> model-authoritative`,
  `move-meaning-into-model`, `repository-evidenced`).
- Had a distinct Need-specific weak relation been justified, it would have
  required its own reviewed identity (e.g. `needAddressesConcern`) — that name
  is not pre-approved and c4 introduces nothing of the kind.
- `motivatesNeed` is not introduced in any direction. If an inverse were ever
  useful it would have to be a meaning-preserving inverse of the same fact —
  not applicable here, because no fact exists.

---

## 5. Minimalism test — the question battery

> What useful DE4SDV question would a Need↔Concern predicate answer that
> cannot already be handled by native Concern/Viewpoint semantics plus
> existing Need source/rationale provenance?

- "Which needs trace to concern C?" — no requester exists. Need visibility is
  delivered by the needs views whose viewpoints frame `stakeholderNeedsConcern`
  (whose own text: "Reviewers need stakeholder needs and validation intent to
  be visible as requirement-like usages, not generic prose") — a visibility
  concern answered by the view, not by per-need links. The governed
  traceability obligations target operational context, feature classification,
  and (via K) derived requirements.
- "Where did need N come from?" — answered by the `source` attribute (with
  `rationale` context); sources are heterogeneous and broader than concerns.
- "Does need N require concern C?" (framing) — not wanted; would overclaim.
- "Does need N weakly address concern C?" — no defined meaning, no consumer.

Result: **no concrete current query or consumer requires a first-class
Need↔Concern relation.** Per the task's minimalism rule, retirement with no
replacement is the preferred-simple outcome.

---

## 6. Disposition — Outcome A: retire without replacement

Why A and not the alternatives:

- **B (native framing exact fit) rejected:** the native mechanism exists and
  is precisely understood, but its claim (concern-as-required-constraint of
  the framing element) is not any claim DE4SDV wants for needs; actual needs
  do not frame concerns. Selecting it would create a false witness — exactly
  what the review forbids.
- **C (distinct weak concern-addressing relation) rejected:** no concrete
  engineering/query need was identified; there is no definable witness
  semantics beyond string heuristics; and the collision constraint forbids
  reusing `addressesConcern`.
- **D (narrow concern-origin provenance) rejected:** DE4SDV does not
  explicitly require "Need N originated from Concern C", and repository/source
  evidence does not establish why that claim would be necessary. It would not
  be universal (sources are broader), and it must not be confused with
  framing/addressing.
- **E (unresolved) rejected:** the evidence is decidable from the repository
  and the pinned library; nothing is missing.
- **Absence-only retirement check:** the decision does not rest on mere
  absence of a witness. It rests on **lack of required engineering
  meaning/query** (verified consumer/scan evidence) **and semantic
  inappropriateness** of each candidate claim (native framing's exact
  semantics mismatch; provenance not required; weak addressing undefined).

**Required conclusions (Outcome A), now recorded:**

1. `derivesNeedFromConcern` is an unnecessary / incorrectly pre-assumed
   vocabulary predicate for the target architecture.
2. Current `source`/`rationale` provenance remains; the authoring/review
   obligations are unchanged.
3. Native Concern/Viewpoint semantics remain.
4. The predicate must not be emitted as an active O2 Semantic Projection
   relation.
5. Eventual authored-YAML removal belongs to its reviewed downstream gate
   (recorded as forward-only required evidence).

---

## 7. Retirement representation (governance-schema adjustment)

Inspected schema/generator/test assumptions: the reviewed layer had no
representation for "intentionally retired, no target semantic authority"
(`authority_target` was a closed authority-location vocabulary; `unknown` means
target *undetermined*, `blocked` means a *gated* location target). Smallest
unambiguous representation added (governance-only; runtime-inert module):

- Target vocabulary: `authority_target` is now validated against
  `AUTHORITY_TARGETS = AUTHORITY_SOURCES + ("retired",)`.
  `authority_current` stays validated against `AUTHORITY_SOURCES`, so
  `authority_current: retired` is unrepresentable by construction.
- Disposition vocabulary: `retire-without-replacement` added and validated in
  **both directions** with the `retired` target.
- Validator rules: a retired identity must have `conditional_target: false`,
  no transition gate, and a decided evidence state (`blocked`/`unknown`
  rejected); a `retire-without-replacement` disposition without the `retired`
  target is rejected.
- Generated artifact: the inventory `dimensions` block now also declares
  `authority_target` (the artifact must not carry a value outside its declared
  vocabularies). No row other than `derivesNeedFromConcern` changes; counts
  shift exactly as recorded in the tests.

### Non-conflation — why the three states cannot be confused

| State | `authority_target` | `evidence_state` | `disposition` | gate | marked how |
|---|---|---|---|---|---|
| Target not yet determined (deferred unknown) | `unknown` | per-entry (e.g. `repository-evidenced`) | `defer` | optional | remains in the six deferred rows (`AssuranceClaim`, `allocatedTo`, `deployedTo`, `instantiatesCanonicalArchitecture`, `validatedBy`, `validatesFitnessForUse`) — untouched |
| Blocked target (gate pending) | a location, `conditional_target: true` | `blocked` | per-entry | **required** | the 13 remaining blocked rows (8 PLE-family + 5 T/E-style) — untouched |
| **Intentionally retired** | `retired` | decided (c4: `parity-reviewed`) | `retire-without-replacement` | **must be null** | exactly one row: `derivesNeedFromConcern` |

The retirement state is a reviewed decision with a complete evidence basis —
not an unknown, not a block, and not a disguised `legacy-yaml` target. The
machine locks assert all three shapes simultaneously, and the validator
rejects any mixed form.

---

## 8. Evidence-state decision

`evidence_state = parity-reviewed`: the reviewed disposition (Outcome A) and
the repository evidence **completely establish the c4 decision within O1** —
the concern-usage inventory is resolved, the claim decomposition is reviewed
against the pinned library, the model-wide scans (needs, framings, consumers)
are mechanical and reproducible, and the retirement representation is
machine-enforced. Not `exact-toolchain-validated` and not
`privileged-closure-proven`: no fresh revision-bound exact-toolchain proof
exists for c4, and no closure record is created. No privileged ingestion was
dispatched for c4; everything cited is repository evidence at the bound
revision.

---

## 9. Claim boundary and non-claims

- The retired identity claims nothing and must never be presented as a
  supported relation at any layer.
- Not an authority transition (`authority_current` stays `legacy-yaml`); the
  authored row is not removed in c4.
- Not O2 (no generated projection row; the retirement forbids one); not
  O3/O4 progress.
- No `.sysml` file changed; no ontology YAML row changed; no runtime module
  changed; no new modeled relationship; no new ontology class; no
  `motivatesNeed`, `needAddressesConcern`, or generic source predicate.
- Need `source`/`rationale` provenance remains required and is **not**
  declared satisfied by any concern link.
- `addressesConcern` is unchanged (`EngineeringIncrement -> Concern`).
- c1/c2/c3 rows, the K triple, the PLE-gated family, and c5 rows are
  unchanged; the intentional-retirement state is distinguishable from
  `unknown` and `blocked`.

---

## 10. Machine locks (`tests/test_o1_c4_concern_need_disposition.py`)

- c4 contains exactly one identity; the global parity-reviewed set advances
  exactly by this row (c1 7 + c2 2 + c3 1 + c4 1 = 11) and this file owns it.
- The final disposition is locked: `authority_target: retired`,
  `disposition: retire-without-replacement`, `evidence_state:
  parity-reviewed`, no conditional target, no gate, empty unknowns,
  forward-only required evidence.
- Retirement-state unit laws (schema): retired+wrong disposition,
  disposition without retired, retired+conditional, retired+gate,
  retired+blocked/unknown — each rejected; `authority_current: retired`
  rejected; valid retired row accepted.
- Non-conflation laws: exactly one retired row; the six `unknown` targets and
  the thirteen remaining `blocked` rows unchanged; `retired` never appears as
  a current-authority value or a conditional target.
- `addressesConcern` stays `EngineeringIncrement -> Concern` and unchanged;
  no Need repurposing; no `motivatesNeed`; no generic source predicate; no new
  relationship in the ontology contract.
- Model-scan law: zero `frame` sites owned by requirement/need usages in the
  governed model (the c4 finding stays machine-checked against drift).
- Need provenance law: the reviewed row does not declare source/rationale
  satisfied by a concern link; the attributes remain the mechanism.
- Framing / provenance / weak-addressing claims remain distinct in the
  reviewed record (fragment locks), and native framing is recorded as
  understood-but-not-selected.
- Generated artifact reproduces the reviewed decision (artifact-vs-source
  consistency; red between Commit A and Commit B by design), the artifact
  declares the target vocabulary, and the inventory remains runtime-inert
  (no projection row, no runtime reader).
- c1/c2/c3/K/PLE/c5 rows unchanged; no closure evidence; no new privileged
  claim; no privileged ingestion dispatched.

---

## 11. Binding

- Branch: `feat/o1-semantic-authority-inventory` (PR #249, Draft; continues
  only c4).
- Base: `e99f46d0` (exact `origin/main` at O1 task start).
- Commit A: this record + the reviewed-decision update + the retirement-state
  schema adjustment + focused c4 tests.
- Commit B: regenerated `semantic-authority-inventory.json` and
  `authority-inventory.md`, bound to Commit A.
- Commit C (test-only): base/c1/c2 later-batch pins updated to the executed c4
  state — deliberate, documented, never silent.
