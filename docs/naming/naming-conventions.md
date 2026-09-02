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
  Error — hence `E` is legacy-only and `EVID` is the readable form for new
  evidence IDs.
- Sequence numbers are never renumbered or reused. Superseded IDs keep their
  identity; new work allocates the next free number.
- Before allocating any ID, sweep all existing IDs across every `.sysml`,
  YAML, and implementation `increments.yaml` source (this is enforced by
  guard tests, not by memory). Sub-sequences (009A..009I) and per-phase series
  consume ranges.
- System 2 (engineering/assurance) sub-series use a role segment, e.g.
  `REQ-AEBS-S2-001` — System 2 requirement, subject AEBS.

## 5. Identifier-prefix registry

Two registry groups exist. **Strict prefixes** form `<TYPE>-<SUBJECT>-<SEQ>`
trace IDs whose subject must be registered (§6). **Free-form prefixes** are
registered codes whose remainder is a meaningful but free-form name (role
names, index entries, catalog records, bench identities, standard anchors) —
they are documented here so a newcomer never has to guess, but their segments
are not syntax-validated.

### Strict prefixes (`<TYPE>-<SUBJECT>-<SEQ>[-<SUBSEQ>]`)

| Code | Meaning | Artifact/entity type | Example | New IDs may use |
|---|---|---|---|---|
| `INC` | Engineering increment | Increment charter/parts | `INC-AEBS-010` | yes |
| `REQ` | Requirement | Design-input requirement | `REQ-AEBS-014` | yes |
| `N` | Stakeholder need | Stakeholder need usage | `N-AEBS-009` | yes |
| `AC` | Acceptance criterion | Criterion on a verification case | `AC-MW-010-02` | yes |
| `VC` | Verification case | Verification activity | `VC-MW-010-01` | yes |
| `E` | Evidence (legacy spelling) | Retained evidence record | `E-MW-011` | **no** — use `EVID` |
| `EVID` | Evidence | Retained evidence record | `EVID-AEBS-001` | yes |
| `GAP` | Gap | Deferred scope / open gap | `GAP-MW-022` | yes |
| `BL` | Baseline | Baseline decision record | `BL-MW-010-P12` | yes |
| `SC` | Validation scenario | Bounded validation scenario | `SC-AEBS-010-01` | yes |

### Free-form prefixes (registered; remainder is a meaningful name)

| Code | Meaning | Where used | Example |
|---|---|---|---|
| `AO` | Acceptance objective | increment pilot index | `AO-AEBS-010-004` |
| `ASM` | Assumption | pilot index | `ASM-MW-016` |
| `ACT` | Actor | pilot index | `ACT-SUBJECT-VEHICLE` |
| `ALT` | Realization alternative | pilot index | `ALT-MW-KUKSA-001` |
| `BLK` | Physical element block | pilot index | `BLK-AEBS-PHY-001` |
| `CAP` | Capability | pilot index | `CAP-AEBS-FCRM` |
| `CC` | Common capability | pilot index | `CC-MW-001` |
| `CLS` | Classification record | pilot index | `CLS-AEBS-010-001` |
| `DEC` | Decision record | pilot index | `DEC-AEBS-LOG-001` |
| `DEF` | Deferral | pilot index | `DEF-AEBS-PHY-001` |
| `EC` | Evidence criterion (executed acceptance observation) | pilot index | `EC-AEBS-009B-01` |
| `FEAT` | Feature | pilot index | `FEAT-AEBS-VEHICLE-TARGET` |
| `FUNC` | Function | pilot index | `FUNC-AEBS-001` |
| `ITEM` | Information item | pilot index | `ITEM-INTERNAL-001` |
| `LCOMP` | Logical component | pilot index | `LCOMP-AEBS-001` |
| `LPORT` | Logical port | pilot index | `LPORT-AEBS-IN-001` |
| `MAP` | Signal mapping record | pilot index | `MAP-MW-008-VEHICLE-SPEED` |
| `MODEL` | Model artifact index entry | pilot index | `MODEL-AEBS-010-VARIABILITY-CONFIGURATION-SYSML` |
| `PORT` | Port | pilot index | `PORT-AEBS-IN-001` |
| `PROBE` | Realization-readiness probe | pilot index | `PROBE-MW-008-AAOS-CUTTLEFISH-BOOT` |
| `PF` | Bench preflight check | bench tooling | `PF-004` |
| `QF` | Qualification finding | pilot index | `QF-AEBS-REQ-001` |
| `REAL` | Realization record | pilot index | `REAL-MW-DIRECT-001` |
| `SCN` | Bench scenario identity | bench tooling / pilots | `SCN-AEBS-009D-STALE` |
| `SET` | Needs/requirements set | pilot index | `SET-AEBS-S1-NEEDS` |
| `SRC` | External source anchor | model + pilots | `SRC-UNECE-R152` |
| `STK` | Stakeholder index entry | pilot index | `STK-PRODUCT-LINE-ENGINEER` |
| `STORY` | Operational story | pilot index | `STORY-AEBS-VEHICLE-TARGET-001` |
| `SYSML` | External spec anchor (pinned spec/release) | pilots | `SYSML-V2-RELEASE-3f895b7` |
| `SAF` | External SAF anchor | pilots | `SAF-CONCEPTUAL-DOMAIN` |
| `UNECE` | External regulation anchor | pilots/docs | `UNECE-R152` |
| `VAL` | Validation scenario (pilot table index) | pilot index | `VAL-AEBS-001` |
| `VP` | Viewpoint selection | pilot index | `VP-AEBS-SENSOR-PACKAGE` |
| `VSS` | VSS source/simulation mapping record | model + pilots | `VSS-SIM-AEBS-001` |
| `DE4SDV` | DE4SDV project artifact reference | pilots/docs | `DE4SDV-VSS-EXT` |

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

## 6. Subject-namespace registry

| Code | Meaning | Scope notes |
|---|---|---|
| `AEBS` | Autonomous Emergency Braking System | System 1 AEBS product-line subject; includes the AEBS visualization System 2 test system |
| `MW` | Middleware | Legacy registered code for the middleware integration subject; canonical spelling `middleware` in filenames/packages; `MW` remains valid only inside trace IDs created before this convention |
| `UNECE-R152` | UNECE regulation anchor | Used only with the `SRC-` prefix |

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

## 11. Enforcement

`scripts/check_naming.py` (wired into `scripts/check_repo.py`) validates the
objective rules: project-owned SysML filename shape, unexplained
increment-number patterns in canonical concern filenames, the abbreviation
policy for new names, registered identifier prefixes and subject namespaces,
and stale generated-diagram filenames. It explicitly exempts upstream/vendor
assets (`.sysand/`, `tests/fixtures/`, `experiments/`), externally stable
identifiers, historical records, retained-evidence filenames bound to
evidence IDs, and artifacts under documented scheduled migration.

Violations are fixed by migration with an explicit old → new mapping in the
migration manifest — never by weakening the checker.
