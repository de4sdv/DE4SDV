# DE4SDV Naming Conventions

This document is the authoritative repository-wide convention for DE4SDV
naming, identifiers, and lifecycle terminology. It defines how canonical
semantic names, lifecycle identities, abbreviations, and artifact names are
chosen and enforced. A contributor should be able to read
`INC-AEBS-010`, `REQ-AEBS-014`, `N-AEBS-009`, `REQ-AEBS-S2-001`, `AC-MW-010-02`,
`E-MW-011`, `EVID-AEBS-001`, `BL-MW-010`, `VC-MW-010-01`, `GAP-MW-022`,
`SC-AEBS-010-01`, and `SRC-UNECE-R152` without reverse-engineering the
repository.

Normative language: **must** = enforced or review-blocking; **should** =
default with documented exceptions; **may** = contributor choice.

## 1. Increment, phase, and record identities

These three concepts are distinct and must not be conflated:

- **Engineering increment** — one bounded engineering question/change with its
  own identity (`INC-<SUBJECT>-<SEQ>`). A DE4SDV increment traverses the
  13-phase workflow (phases 0–12). Do not treat phases as separate increments.
- **Phase** — one step of the DE4SDV method executed inside an increment
  (0 Increment framing, 1 Concern framing, 2 Operational context,
  3 Capability/feature semantics, 4 Needs, 5 Requirements,
  6 Functional architecture, 7 Logical architecture, 8 Physical/software
  realization, 9 Variability and configuration, 10 V&V and evidence,
  11 Publication, 12 Baseline and next slice). Phases are workflow steps;
  they never receive identifiers of their own and never appear as the naming
  basis of enduring model partitions.
- **Record** — an identity-bearing artifact tied to a specific increment,
  verification activity, runtime, configuration, or decision: evidence
  records, acceptance criteria, baselines, configured product projections,
  retained campaigns. Records keep stable lifecycle identities.

## 2. Canonical semantic names vs lifecycle identities

Use **semantic names for reusable/canonical concepts** and **lifecycle
identifiers only for records whose identity actually depends on the lifecycle
event**.

Canonical semantic names name the enduring engineering concern:

- `aebs_operational_context.sysml`
- `aebs_requirements.sysml`
- `aebs_logical_architecture.sysml`
- `middleware_requirements.sysml`
- `middleware_logical_architecture.sysml`
- `DE4SDV_AEBSLogicalArchitecture`
- `DE4SDV_MiddlewareLogicalArchitecture`

Identity-bearing names are legitimate when the artifact intentionally is that
exact lifecycle record:

- evidence slices of a bounded increment (`DE4SDV_Middleware010VerificationEvidence`,
  the immutable closure record of INC-MW-010);
- an evidence record tied to a specific evidence ID (`E-MW-011`);
- an exact configuration projection for one increment;
- a baseline identity (`BL-MW-010`);
- a verification slice that realizes a specific increment's acceptance criteria.

Avoid lifecycle numbers in reusable definitions
(`EvidenceOutcome009H`, `ScenarioIdentity009F`, `BicycleTargetBench009H`,
`DE4SDV_AEBS010VisualizationLogicalArchitecture`) unless the definition
intentionally exists only as an immutable representation of that exact
lifecycle record. Historical 009-series verification slices retain their
increment-suffixed declarations because they are the immutable evidence
records of those increments; do not copy the pattern into new canonical work.

The same rule covers **system-role shorthand**. When the package or the owning
definition already establishes the System 1 / System 2 role — for example
`DE4SDV_AEBSVisualizationVerificationEvidence` is, by its package and doc
contract, the System 2 read-only AEBS visualization test system's evidence
slice — locally declared names must not repeat the role as an embedded
`S2`/`s2` shorthand (`VisualizationVandVBenchS2`,
`s2VisualizationInstrumentationClaim`). Drop the shorthand where the remaining
name is already descriptive (`VisualizationAcceptanceCriterion`); where the
remainder would be generic or could shadow an imported declaration, add the
concern qualifier instead (`verificationSystem` →
`visualizationVerificationSystem`,
`argumentationAssuranceConcern` →
`visualizationArgumentationAssuranceConcern`). This is a **name-only rule**:
hyphenated trace IDs (`EVID-AEBS-S2-001`, `AC-AEBS-S2-004`) are registered
identity records and keep the `S2` namespace (same status as `MW` in §3), and
doc prose that must state the system role explicitly ("System 1 subject /
System 2 instrumentation") keeps spelling the role out. The role semantics
never move — only the redundant shorthand in the identifier goes.

### Dependency declarations

Active canonical dependencies use semantic source/target concern names,
not compact trace-number stems such as `req001`, `reqS2001`, `s2002`, or
`need001`. For example, `reqSourceFidelityDerivedFromLiveVisualizationOnAAOS`
is a declaration name; its requirement and need IDs remain separate stable
records. Renames are scoped by owning file/package, never by an ambiguous
repository-wide bare-name substitution.

The naming gate inspects declaration names (including `dependency`) across
active project-owned package, product-model, and product-line scoping roots.
It rejects compact trace-number stems and redundant role shorthand, including
numeric continuations. It preserves technology tokens such as `ROS2` and
`PointCloud2`, explicit architectural roles, and lifecycle record identities.
Upstream libraries, snapshots and synthetic fixtures are excluded. This is
lexical naming lint over ASCII and single-quoted declaration names, not a
SysML semantic parser or a claim that every naming policy is machine-proven.
Comments and double-quoted literals are not declaration names.

## 3. Abbreviation policy

### Established domain/technology acronyms (keep)

These are natural engineering terms and must not be expanded for style:
AEBS, ADAS, SDV, AAOS, ROS 2 (identifier syntax: `ROS2`), AUTOSAR, ECU, VSS,
FMI, FMU, SSP, HIL, SIL, MIL, V&V (prose), UNECE.

### Project-local shorthand (avoid in canonical semantic names)

| Avoid | Use instead |
|---|---|
| `mw` / `MW` | `middleware` / `Middleware` |
| `reqs` | `requirements` |
| `cfg` | `configuration` |
| `viz` | `visualization` |
| `arch` | `architecture` |
| `ver` | `verification` |
| `S1` / `S2` embedded role shorthand | Omit when the owning package/definition already establishes the role. Add a concern qualifier when the remainder would be generic. Preserve registered trace IDs and technology names such as `ROS2`. Explicit role names such as `system2Instrumentation` remain valid when needed to distinguish architectural roles. |

`MW` as a **registered subject-namespace code** (see §6) remains valid inside
governed trace IDs (`E-MW-011`, `BL-MW-010`, legacy `REQ-MW-001`). It is not
valid in new filenames, package names, or type names. Never perform a blind
`MW → Middleware` replacement: `MW` occurs inside stable evidence IDs and
registered trace-ID namespaces.

## 4. Identifier grammar

```text
<TYPE>-<SUBJECT>-<SEQUENCE>[-<SUBSEQUENCE>]

TYPE      registered prefix from the identifier-prefix registry (§5)
SUBJECT   registered subject-namespace code from §6
SEQUENCE  zero-padded integer, monotonic per (TYPE, SUBJECT) family
SUBSEQUENCE  optional letter or nested segment (e.g. 009A..009I, 010-02)
```

Rules:

- Prefixes and subject codes come only from the registries below. A newcomer
  must never have to guess whether `E` means Evidence, Element, Event, or
  Error — hence `E` is a retired grammar retained only as grandfathered
  identities (§5.1) and `EVID` is the readable form; likewise `N` is retired
  and `NEED` is the readable form for new need IDs.
- Sequence numbers are never renumbered or reused. Superseded IDs keep their
  identity; new work allocates the next free number.
- Before allocating any ID, sweep all existing IDs across every `.sysml`,
  YAML, and implementation `increments.yaml` source (this is enforced by
  guard tests, not by memory). Sub-sequences (009A..009I) and per-phase series
  consume ranges.
- System 2 (engineering/assurance) sub-series use a role segment, e.g.
  `REQ-AEBS-S2-001` — System 2 requirement, subject AEBS.

## 5. Identifier-prefix registry

Every registered family carries exactly one classification:

- **CANONICAL** — the grammar is readable and owned; new identities may use
  it.
- **EXTERNAL** — domain/standard identity owned outside DE4SDV; registered
  only so it is never mistaken for a project ID.
- **GRANDFATHERED** — a legacy grammar that is readable-but-superseded or
  externally referenced; only the exact enumerated identities remain valid
  (§5.1), and creating sibling identities under the retired grammar fails
  the naming check deterministically. Grandfathering is never a license to
  extend the legacy pattern.
- **RETIRED→MIGRATE** — internal, unbound, and still cheap to change; the
  migration manifest lists the rename. (No family currently sits here; the
  class exists so future findings have a declared path.)

Two registry groups exist. **Strict prefixes** form `<TYPE>-<SUBJECT>-<SEQ>`
trace IDs whose subject must be registered (§6). **Free-form prefixes** are
registered codes whose remainder is a meaningful but free-form name (role
names, index entries, catalog records, bench identities, standard anchors) —
they are documented here so a newcomer never has to guess, but their segments
are not syntax-validated.

### Strict prefixes (`<TYPE>-<SUBJECT>-<SEQ>[-<SUBSEQ>]`)

| Code | Meaning | Artifact/entity type | Example | Class / new IDs |
|---|---|---|---|---|
| `INC` | Engineering increment | Increment charter/parts | `INC-AEBS-010` | CANONICAL |
| `REQ` | Requirement | Design-input requirement | `REQ-AEBS-014` | CANONICAL |
| `NEED` | Stakeholder need (readable form) | Stakeholder need usage | *(none yet)* | CANONICAL — use for new need IDs |
| `N` | Stakeholder need (legacy spelling) | Stakeholder need usage | `N-AEBS-009` | GRANDFATHERED (§5.1) — use `NEED` |
| `AC` | Acceptance criterion | Criterion on a verification case | `AC-MW-010-02` | CANONICAL |
| `VC` | Verification case | Verification activity | `VC-MW-010-01` | CANONICAL |
| `EVID` | Evidence | Retained evidence record | `EVID-AEBS-001` | CANONICAL |
| `E` | Evidence (retired spelling) | Retained evidence record | `E-MW-011` | GRANDFATHERED (§5.1) — use `EVID` |
| `GAP` | Gap | Deferred scope / open gap | `GAP-MW-022` | CANONICAL |
| `BL` | Baseline | Baseline decision record | `BL-MW-010-P12` | CANONICAL |
| `SC` | Validation scenario | Bounded validation scenario | `SC-AEBS-010-01` | CANONICAL |

### 5.1 Grandfathered legacy identities (closed sets)

The retired grammars below are enforced **deterministically**:
`scripts/check_naming.py` keeps the exact identity sets as allowlists. An
enumerated identity remains valid wherever it is referenced; any sibling
spelling (`E-MW-999`, `N-AEBS-015`, `N-MW-010`) is rejected like an
unregistered prefix. New identities must use the canonical grammar.

`E-<SUBJECT>-<SEQ>` — retained evidence chain of the closed INC-MW-010
verification record. These IDs are bound inside retained evidence YAML,
SysML evidence/provenance prose, and the INC-AEBS-010 predecessor
alignment; renaming them would break provenance-bearing records for zero
semantic gain. The set is closed:

`E-MW-008`, `E-MW-010`, `E-MW-011`, `E-MW-012`, `E-MW-013`, `E-MW-014`.

`N-<SUBJECT>-<SEQ>` — need identities already anchored in bench
configuration matrices, evidence records, and the AEBS operational-context
pilot (traceability would silently rot if renumbered). The set is closed:

`N-AEBS-001`…`N-AEBS-014`, `N-AEBS-OP-001`…`N-AEBS-OP-005`,
`N-MW-001`…`N-MW-009`.

New need IDs use `NEED-<SUBJECT>-<SEQ>`; new evidence IDs use
`EVID-<SUBJECT>-<SEQ>`.

### Free-form prefixes (registered; remainder is a meaningful name)

Class column: **CANONICAL** = project-owned grammar, new identities may use
it; **EXTERNAL** = identity owned outside DE4SDV, registered only so it is
never mistaken for a project ID.

| Code | Meaning | Where used | Example | Class |
|---|---|---|---|---|
| `AO` | Acceptance objective | increment pilot index | `AO-AEBS-010-004` | CANONICAL |
| `ASM` | Assumption | pilot index | `ASM-MW-016` | CANONICAL |
| `ACT` | Actor | pilot index | `ACT-SUBJECT-VEHICLE` | CANONICAL |
| `ALT` | Realization alternative | pilot index | `ALT-MW-KUKSA-001` | CANONICAL |
| `BLK` | Physical element block | pilot index | `BLK-AEBS-PHY-001` | CANONICAL |
| `CAP` | Capability | pilot index | `CAP-AEBS-FCRM` | CANONICAL |
| `CC` | Common capability | pilot index | `CC-MW-001` | CANONICAL |
| `CLS` | Classification record | pilot index | `CLS-AEBS-010-001` | CANONICAL |
| `DEC` | Decision record | pilot index | `DEC-AEBS-LOG-001` | CANONICAL |
| `DEF` | Deferral | pilot index | `DEF-AEBS-PHY-001` | CANONICAL |
| `EC` | Evidence criterion (executed acceptance observation) | pilot index | `EC-AEBS-009B-01` | CANONICAL |
| `FEAT` | Feature | pilot index | `FEAT-AEBS-VEHICLE-TARGET` | CANONICAL |
| `FUNC` | Function | pilot index | `FUNC-AEBS-001` | CANONICAL |
| `ITEM` | Information item | pilot index | `ITEM-INTERNAL-001` | CANONICAL |
| `LCOMP` | Logical component | pilot index | `LCOMP-AEBS-001` | CANONICAL |
| `LPORT` | Logical port | pilot index | `LPORT-AEBS-IN-001` | CANONICAL |
| `MAP` | Signal mapping record | pilot index | `MAP-MW-008-VEHICLE-SPEED` | CANONICAL |
| `MODEL` | Model artifact index entry | pilot index | `MODEL-AEBS-010-VARIABILITY-CONFIGURATION-SYSML` | CANONICAL |
| `PORT` | Port | pilot index | `PORT-AEBS-IN-001` | CANONICAL |
| `PROBE` | Realization-readiness probe | pilot index | `PROBE-MW-008-AAOS-CUTTLEFISH-BOOT` | CANONICAL |
| `PF` | Bench preflight check | bench tooling | `PF-004` | CANONICAL |
| `QF` | Qualification finding | pilot index | `QF-AEBS-REQ-001` | CANONICAL |
| `REAL` | Realization record | pilot index | `REAL-MW-DIRECT-001` | CANONICAL |
| `SCN` | Bench scenario identity | bench tooling / pilots | `SCN-AEBS-009D-STALE` | CANONICAL |
| `SET` | Needs/requirements set | pilot index | `SET-AEBS-S1-NEEDS` | CANONICAL |
| `C` | Common capability node | feature model | `C-CAPABILITY-AEBS-VEHICLE-TARGET` | CANONICAL (feature-model namespace — see note) |
| `D` | Derived asset | feature model | `D-ASSET-APPLICATION-MIDDLEWARE-ADAPTER` | CANONICAL (feature-model namespace — see note) |
| `F` | Feature node | feature model | `F-PLATFORM-STACK` | CANONICAL (feature-model namespace — see note) |
| `PL` | Product line | feature-model root | `PL-DE4SDV` | CANONICAL (feature-model namespace — see note) |
| `CLM` | Claim (assurance argumentation) | middleware evidence slice + guide | `CLM-MW-010-01` | CANONICAL |
| `AGT` | Assurance argument (argumentation) | middleware evidence slice + guide | `AGT-MW-010-01` | CANONICAL |
| `CCM` | Counter-claim (argumentation) | middleware evidence slice + guide | `CCM-MW-010-01` | CANONICAL |
| `VM` | Campaign bench virtual-machine host label | bench docs/code | `VM-A`, `VM-B` | CANONICAL (infrastructure label; single-suffix shape sits outside the strict grammar) |
| `H` | Hazard (compliance safety) | hazard analysis artifacts | `H-001` | CANONICAL (domain-standard hazard-ID form) |
| `T` | Threat (compliance security) | threat model artifacts | `T-001` | CANONICAL (domain-standard threat-ID form) |
| `SRC` | External source anchor | model + pilots | `SRC-UNECE-R152` | CANONICAL |
| `STK` | Stakeholder index entry | pilot index | `STK-PRODUCT-LINE-ENGINEER` | CANONICAL |
| `STORY` | Operational story | pilot index | `STORY-AEBS-VEHICLE-TARGET-001` | CANONICAL |
| `SYSML` | External spec anchor (pinned spec/release) | pilots | `SYSML-V2-RELEASE-3f895b7` | EXTERNAL |
| `SAF` | External SAF anchor | pilots | `SAF-CONCEPTUAL-DOMAIN` | EXTERNAL |
| `UNECE` | External regulation anchor | pilots/docs | `UNECE-R152` | EXTERNAL |
| `VAL` | Validation scenario (pilot table index) | pilot index | `VAL-AEBS-001` | CANONICAL |
| `VP` | Viewpoint selection | pilot index | `VP-AEBS-SENSOR-PACKAGE` | CANONICAL |
| `VSS` | VSS source/simulation mapping record | model + pilots | `VSS-SIM-AEBS-001` | CANONICAL (records *about* the external VSS domain; VSS paths themselves are external identifiers and are never renamed) |
| `DE4SDV` | DE4SDV project artifact reference | pilots/docs | `DE4SDV-VSS-EXT` | CANONICAL |

Feature-model namespace note (`F`/`C`/`D`/`PL`): these codes are parsed by
the product-line tooling (`tools/configure_variant.py`, feature-model
YAML) and are bound into committed feature configurations and generated
product models. They are short, but they are the established feature-model
namespace — renaming them is a PLE model-and-tooling change, not a naming
migration. If the PLE workstream later revises the feature-model grammar,
that revision owns the rename; this registry is updated the same day.

### Subject-first configuration identities

Configuration identities use the subject-first form
`<SUBJECT>-CONFIG-<SEQ>` (optionally with a sub-sequence):
`MW-CONFIG-001` is the accepted middleware reference-member configuration
(bound as `configurationIdentity` in the INC-MW-010 evidence record);
`AEBS-CONFIG-010-001` is the INC-AEBS-010 test-article configuration
decision. These are stable configuration identities — do not renumber.

### External names that merely look like IDs (not registry entries)

`S-CORE`, `SAF-SysMLV2`, `SYSML-V2-SPEC-7`, `MBSE4U-SYSMOD-PROBLEM-STATEMENT`,
`COVESA-VSS-VEHICLE-SPEED` are external project/spec/library names. They are
exempt from registry validation; new external names are added to the checker's
exempt list deliberately, never silently.

Unregistered prefixes or subjects fail `scripts/check_naming.py`.

# Subject-namespace registry

| Code | Meaning | Scope notes |
|---|---|---|
| `AEBS` | Autonomous Emergency Braking System | System 1 AEBS product-line subject; includes the AEBS visualization System 2 test system |
| `MW` | Middleware | Registered compact trace namespace: `MW = Middleware` inside identifiers (`INC-MW-010`, `REQ-MW-*`, `AC-MW-010-02`, `MW-CONFIG-001`). Canonical semantic names never use it: filenames use `middleware_*`, SysML packages use `Middleware` (batch 1 migrated these). New trace-ID families SHOULD pick a readable subject code; `MW` is retained because existing AC/VC/EVID/E/GAP/BL/CLM/AGT/CCM/REQ/N families for the middleware subject are stable, provenance-bearing identities. |
| `UNECE` | UNECE regulation anchor | Subject of the `SRC-UNECE-R152` form (`TYPE=SRC`, `SUBJECT=UNECE`, remainder `R152` is the free-form rest segment, not a subject) |

New subjects (e.g. a future `PER` perception subject) must be added here in
the same commit that first uses them.

## 7. File and directory naming

| Artifact | Convention | Example |
|---|---|---|
| Project-owned SysML filenames | `lower_snake_case.sysml` | `aebs_logical_architecture.sysml` |
| Python modules | `lower_snake_case.py` | `check_model_sync.py` |
| Directories | `lower-kebab-case` | `feature-configurations/` |
| YAML artifact/config filenames | `lower-kebab-case.yaml` | `middleware-v-and-v-evidence.yaml` (legacy) → `middleware-v-and-v-evidence.yaml` |
| Conventional docs | fixed names | `README.md`, `VIEWS.md`, `AGENTS.md` |
| Topic docs | `lower-kebab-case.md` | `bounded-phase12-closure.md` |
| Generated diagrams | produced by the generator from the view identity | `diagram-aebsLogicalStructureView.svg` |

Lifecycle status words (`candidate`, `draft`, `invalid`) must live in
metadata, not in stable filenames, except where the name states the artifact
class (a deliberate example fixture is `example-…`; a deliberately invalid
fixture lives under a `fixtures/` location).

Increment numbers must not define the filesystem structure of canonical
engineering concerns. `aebs_010_visualization_framing.sysml` is the canonical
counter-example that scheduled migration (see the migration manifest) removes;
new work must never follow it.

## 8. SysML naming

- **Filenames:** `lower_snake_case.sysml`, named for the enduring engineering
  concern (framing, operational context, stakeholder needs, requirements,
  functional architecture, logical architecture, physical/software
  realization, variability/configuration, verification/evidence) — or,
  for immutable increment records, explicitly by that record.
- **Global packages:** one unique semantic package per file, PascalCase with
  the `DE4SDV_` project prefix: `DE4SDV_AEBSLogicalArchitecture`. The legacy
  inner nesting `package Features { package AEBS { … } }` inside older slices
  is tolerated but not canonical; new files use the flat unique global
  package only, and nested shapes must not be propagated.
- **Definitions (`part def`, `requirement def`, enums, …):** semantic
  PascalCase, no lifecycle numbers unless the definition intentionally is
  that lifecycle record.
- **Usages/instances:** lowerCamelCase (`incMW002`, `memberProduct`).
  Usage names of increment records (`incMW002`, `incAEBS010`) keep their
  identity.
- **Views:** lowerCamelCase semantic identity
  (`aebsLogicalStructureView`). A view that is an enduring canonical view
  introduced by an increment takes the semantic name and keeps the increment
  as provenance in its doc; only a view that is intentionally an immutable
  snapshot of one increment keeps the increment in its identity.
- **Upstream/vendor-owned naming is never normalized:** ROS 2 topic/service
  names, Autoware package names, AAOS APIs, VSS paths, AUTOSAR identifiers,
  external standards identifiers, and Sysand library files (`.sysand/lib/…`)
  keep their exact external spelling.

## 9. Canonical engineering-concern vocabulary

Enduring concern partitions per subject (AEBS shown; middleware uses the
middleware spelling):

| Concern | File | Global package |
|---|---|---|
| Framing | `aebs_framing.sysml` | `DE4SDV_AEBSFraming` |
| Operational context | `aebs_operational_context.sysml` | `DE4SDV_AEBSOperationalContext` |
| Stakeholder needs / requirements | `aebs_needs_requirements.sysml` | `DE4SDV_AEBSNeedsRequirements` |
| Functional architecture | `aebs_functional_architecture.sysml` | `DE4SDV_AEBSFunctionalArchitecture` |
| Logical architecture | `aebs_logical_architecture.sysml` | `DE4SDV_AEBSLogicalArchitecture` |
| Physical/software realization | `aebs_physical_software_realization.sysml` | `DE4SDV_AEBSPhysicalSoftwareRealization` |
| Variability/configuration | `aebs_variability_configuration.sysml` | `DE4SDV_AEBSVariabilityConfiguration` |
| Verification evidence | `*_verification*.sysml` / `*_evidence.sysml` — one convention, stable semantic modules allowed | — |

Notes:

- Scenario-specific verification files (bicycle, pedestrian, degraded input,
  override, non-activation, partial intervention, regulatory criterion) are
  stable semantic modules and keep their own files.
- `aebs_needs_requirements.sysml` combines stakeholder needs and requirements
  in one slice by deliberate history (the increment delivered both). Splitting
  needs from requirements is a model-architecture change, not a rename; it is
  recorded as a recommendation in the migration manifest, not silently done
  here.
- Do not force every verification concern into one huge file, and do not
  create parallel "increment-numbered" architecture models next to canonical
  concern models.

## 10. Authority of artifact classes

- **SysML** owns engineering semantics: definitions, usages, requirements,
  needs, concerns, views, allocations, gaps, evidence contracts.
- **YAML** owns increment identity/status, framing indexes, source-alignment
  references, and additive planning/evidence metadata. It must not duplicate
  SysML semantics and is never the sole semantic source.
- **Generated artifacts** (`VIEWS.md`, `diagrams/*.svg`, scenario manifests,
  product-model projections, `.meta.json`) follow their generator and their
  canonical source identities; never hand-rename generated output while the
  generator still emits the old name.
- **Code, scripts, tests, CI** reference canonical paths and identities
  literally; they are migrated with the same commit as the rename they
  reference.

Historical ADRs, retained evidence, baseline registers, and merged-PR
descriptions preserve the terminology of their revision; history is not
rewritten.

## 11. Enforcement — governed textual surface

`scripts/check_naming.py` (wired into `scripts/check_repo.py`) validates the
objective rules: project-owned SysML filename shape, unexplained
increment-number patterns in canonical concern filenames, the abbreviation
policy for new names, registered identifier prefixes and subject namespaces,
and stale generated-diagram filenames.

### Governed textual surface (identifier scanning)

Identifier scanning covers the project-owned text artifacts where governed
IDs actually live — `.sysml`, `.yaml`/`.yml`, and `.md` under:

`textual-notation-of-model/packages`, `methodologies/sysmod-sysmlv2`,
`approach/`, `model-based-product-line-engineering/`, `implementation/`,
`configuration-management/`, `continuous-homologation/`, `compliance/`,
`devsecops/`, `simulation/`, `sysmlv2-api/`, `docs/`.

Artifact-aware rules (small and explicit, no heuristic parser):

- **SysML**: comments, doc blocks, and quoted strings are scrubbed before
  scanning — SysML prose is not a governed identifier surface; code tokens
  are. Governed IDs appear in YAML/MD companions, not SysML prose.
- **YAML**: scanned raw — identifiers inside normal scalar values, including
  quoted values, are governed data (`requirement_id: "REQ-AEBS-001"` is
  checked).
- **Markdown**: fenced code blocks are illustrative examples and are
  stripped; inline and prose text stays governed.

**Deliberately not token-scanned (normative narrowing):**

- **Python sources** (`*.py`) — executable realizations whose string
  literals include regex fragments and test fixtures; tests deliberately
  contain invalid examples. Governed identities appearing in Python are
  covered by the migration guard tests instead. This is documented policy,
  not an omission.
- **Named path exemptions**: upstream/vendored libraries
  (`**/libraries/`), historical snapshots (`**/snapshots/`), synthetic
  fixtures (`**/fixture/`, `**/fixtures/`), generated diagrams
  (`**/diagrams/`), retained-evidence directories
  (`implementation/*/evidence/`), immutable ADR history
  (`docs/architecture-decisions/`), retained raw bench-evidence JSON
  (`scenario-evidence.json`, `run-metadata.json`), placeholder example
  templates (the `draft/example` hazard/threat/evidence-register
  templates), the historical 009C–009I implementation-plan record, and the
  naming QA/manifest docs (which quote unregistered forms as
  counterexamples). The conventions doc itself stays fully governed.
- **Non-governed look-alikes**: hash-algorithm names (`SHA-256`, `SHA-1`),
  GitHub line anchors (`#L743-L754`), charset fragments, mixed-case prose
  (`SERVER-IPv4`, `AI-Ready`), external project names (`S-CORE`,
  `SAF-SysMLV2`, …), and retained evidence-index filenames
  (`VIDEO-EVIDENCE-DISPOSITION.md`, an artifact label of the INC-AEBS-010
  campaign, not a project identity) are outside the grammar by construction
  or by the named external list.

**What the checker cannot do (honest boundary):** it validates syntax
against the registries plus the enumerated grandfathered identity sets
(§5.1). Retired grammars (`E-`, `N-`) are therefore enforced
deterministically — enumerated identities pass, sibling spellings fail —
but provenance rules that cannot be enumerated, such as subject selection
for a brand-new increment family, remain **review policy**, stated here and
checked by human review.

Violations are fixed by migration with an explicit old → new mapping in the
migration manifest — never by weakening the checker.
