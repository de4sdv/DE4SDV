# Generic Increment Workflow

This workflow turns the SYSMOD/SysML v2 method reference into a repeatable DE4SDV contribution pattern. It is generic: it can be used for a project-level System 2 increment, a product-line feature such as AEBS, a toolchain integration, or an evidence/assurance increment.

## Purpose

Each increment should answer one engineering question and leave behind reviewable artifacts. The workflow deliberately separates method, semantics, architecture views, and publication:

```text
SAF viewpoints        -> what concerns/views must be addressed
SYSMOD method flow    -> how modeling proceeds from context to architecture
DE4SDV ontology       -> what concepts and trace links mean
SysML v2 / Markdown   -> reviewable expression of the model and rationale
GitHub PR             -> reviewed publication baseline
```

## Increment entry criteria

Before starting an increment, define:

- increment name and owner,
- decision or engineering question,
- system/product-line scope,
- stakeholder concerns,
- selected SAF viewpoints,
- expected artifacts,
- out-of-scope boundaries,
- validation/review evidence expected for the PR,
- lifecycle decision to be supported by the increment.

If these cannot be stated, the increment is not ready.

### Declaring an increment in the model

The entry criteria are model content. An increment is declared in SysML in
this shape, which the method checks read:

- **Identity:** the increment usage carries its registered `INC` identifier
  as its declared short name, for example
  `part <'INC-AEBS-010'> incAEBS010 : VisualizationIncrement`. Its definition
  specializes `EngineeringIncrement`. A new increment's usage name is
  descriptive; existing usages such as `incAEBS010` keep theirs (naming
  conventions, §8).
  The repository check validates every short name against the identifier and
  subject registries of the
  [naming conventions](../../docs/naming/naming-conventions.md).
- **Charter declaration:** exactly one `IncrementCharter` usage references the
  increment. It declares the applicable phases and, as plain attributes, the
  owner, the expected artifacts and the expected review evidence.
- **Scope:** the checks evaluate the packages named in the charter's
  `expectedArtifacts`. Each value is the declared name of exactly one
  top-level package, and everything those packages own, through nested
  packages, is in scope; the framing checks read the package that owns the
  increment usage and its charter. Nothing else puts content in scope: a
  subject typed by the increment or a `references` to the increment usage
  does not. Content in a package that is not named is never evaluated, so an
  advisory check reports a package that holds increment content but is not
  named: the increment usage itself, elements connected by `DerivesFromNeed`
  to an element in scope, verification cases that verify an in-scope
  requirement, requirements verified by an in-scope verification case,
  allocations from an element of the named packages, and elements that
  reference the increment usage (a reference to any other increment element
  does not count). The architecture checks of phases 6 to 8 also count what
  those packages own at any depth and the elements their allocations name
  (rule 12).
- **System of interest:** the charter names it by reference to a usage,
  `ref part :>> systemOfInterest = <usage>;`, such as the test system or the
  product line the increment specifies, or by type,
  `ref part :>> systemOfInterest : <Definition>;`. The needs and
  requirements take that system of interest as their subject, never the
  increment: a requirement reads "the system shall ...", so its subject is
  the system it constrains. A subject matches when it is, narrows, or is
  typed by the declared system of interest's definition or a specialization
  of it; the match is type-level, so another usage of that definition also
  passes. An advisory check reports a need or requirement whose subject is
  the increment or is not the declared system of interest.
- **Charter content:** the problem statement, whose native subject is typed by
  the increment definition, with its stakeholders; the engineering question;
  the lifecycle decision; the assumptions; the scope and the out-of-scope
  items; and the concerns framed by a viewpoint of a view. All of them are
  owned by the package that owns the increment usage.
- **Files:** a new increment's model files go under
  `textual-notation-of-model/packages/features/<area>/`, one global package
  per file, named by engineering concern as the
  [naming conventions](../../docs/naming/naming-conventions.md) set out
  (file and directory naming, SysML naming, concern vocabulary). No
  registration is needed: the licensed export loads every `.sysml` file of
  the model project whether or not the sysand index (`.meta.json`) lists it.
  A folder whose files declare a view also publishes it: commit the folder's
  `VIEWS.md` (`python scripts/generate_view_index.py <folder>`) and the
  diagrams the licensed validation renders for it (the `syside-diagrams`
  artifact of its run); CI checks both.

### Method rules and the increment workflow model

These method rules apply to every increment:

1. **Increment.** Every increment is declared in the model with a short
   identifier and a charter: problem statement, engineering question,
   lifecycle decision, at least one assumption, at least one stakeholder, at
   least one concern framed by a viewpoint, scope and out-of-scope, and owner.
   It also declares which phases apply. Owner, expected artifacts and expected
   review evidence are plain attributes, not new kernel classes.
2. **Needs.** Each need owns a statement (a `require constraint` of its own;
   one inherited from its definition does not count), has at least one
   stakeholder, an ODE4HERA source and rationale, and at least one planned
   validation scenario. Its
   subject is the system of interest the charter declares, never the
   increment (advisory).
3. **Needs and concerns.** Only viewpoints frame concerns. A need doesn't
   frame the concern it comes from: a requirement that frames a concern is
   satisfied only when the whole concern is addressed, while a need usually
   covers only part of one. A need traces to the concerns behind it through
   its stakeholder, source and rationale (rule 2). No check or traversal
   reads a plain dependency from a need to a concern, so such a dependency
   only restates that provenance. A repository test checks that every
   `frame` in the model belongs to a viewpoint.
4. **Requirement to need.** Only the governed `DerivesFromNeed` connection
   counts. Plain dependencies don't.
5. **Requirement.** A requirement owns a statement (a `require constraint` of
   its own; one inherited from its definition does not count), has exactly
   one native subject and exactly one primary verification method from the
   standard kinds. Its
   subject is the system of interest the charter declares, never the
   increment (advisory). Requirements are shared assets. A requirement
   varies with the features that bring its system of interest into a member
   product.
   - **Links.** These existing links name such a feature:
     - a dependency of the requirement or of its system of interest on the
       feature;
     - such a dependency on a variant bound to the feature, on a variant
       that a derivation rule derives from it, or on that variant's
       definition;
     - the typing of the system of interest by the definition of such a
       variant.
   - **Named features.** A definition names a feature only when it types no
     other bound or derived variant. Otherwise, link to the variant itself.
     A derived variant names every premise of the rule that derives it.
     When the links name more than one feature, the requirement applies to
     a member product that selects all of them.
   - **Placement.** Declare these dependencies with the requirement or its
     system of interest, outside the feature-model and configuration
     documents.
   - **Core.** A requirement with no such link is core, common to every
     member product. An element that only restates such a link does not
     earn its place (rule 11). No check reads these links.
   - **Requirement variants.** The
     [PLEML configuration evaluator](../../docs/product-line-engineering/pleml-configuration-evaluation.md)
     binds only the variations of a feature model's projection owner, such
     as `SDVPlatformStack`, one per feature group. Binding a requirement
     variant to a feature in phase 9 therefore waits until the evaluator
     binds requirement variants.
6. **Verification.** Each verification case verifies at least one requirement
   of the increment, and every in-scope requirement is verified by at least
   one verification case.
7. **Advisory, not blocking.** The requirement's success criteria, evidence
   record or status, the subject of needs and requirements being the system
   of interest, the expected artifacts naming every package that holds
   increment content, and the architecture traces rule 12 marks advisory.
8. **Principle.** Structural checks block; judgment checks (wording,
   verifiability) are advisory.
9. **Operational context and story (phase 2).** A member product's
   operational context and story hold System 1 roles only: the system of
   interest and the actors and entities it meets in operation. Bench,
   reviewer and evidence roles belong to the engineering and assurance
   system (System 2) and stay out of them; an increment whose system of
   interest is a System 2 test system holds such roles in its own context.
   A use case's subject is the system of interest and its actors are the
   context parts around it: the use case usage binds its subject to the
   system-of-interest usage (`subject s = <usage>;`) and each actor to a
   context part (`actor a = <part>;`), standard SysML v2 subject and actor
   binding. INC-AEBS-002's vehicle-target story
   (`aebs_operational_context.sysml`) shows the complete binding form,
   although two of its actors are System 2 roles. INC-MW-011's two-domain
   story (`middleware_score_operational_context.sysml`) binds every use case
   to the parts of its `SystemContext`.
   - **Checks (blocking).** The increment has exactly one `SystemContext`
     usage. A part of it redefines its `systemOfInterest`. That part is,
     narrows or is bound to the system of interest the charter declares, or
     is typed by its definition. Each use case the increment's packages own
     binds its subject to that part. Each actor of each use case is bound
     to a part the context owns at any depth, around that part, not inside
     it.
   - **Use case parameters.** A use case has one subject: its own, else its
     definition's. Its actors are its own and those of its definitions
     that no own actor redefines. A bound value is the parameter's own
     `= <usage>`; a feature chain counts as its last feature.
   - **Left to review.** Whether a role is a System 1 or a System 2 role:
     the kernel classifies no role as either.
10. **Feature-model delta (phase 3).** Phase 3 records only what the
    increment adds to the feature model: each characteristic it records is
    a feature candidate (`ProductLineFeatureCandidate`). Core elements are
    common by default and get no record, so phase 3 instantiates no
    `CommonProductLineCapability` for them. Constraints go to the
    requirements (phase 5) and evidence to V&V (phase 10). An increment that
    adds no variability records nothing in phase 3. The basis is ISO/IEC
    26580: a feature differentiates member products, and the feature model
    covers variability only. Product-line scope the increment defers
    (`DeferredProductLineScope`), such as a gap, is no classification record
    and is allowed. The step's output is typed by the classification base
    `ProductLineCharacteristic`. So its check sees every product-line
    characteristic of the increment. One that is neither a feature candidate
    nor deferred scope blocks (`featureDeltaOnly`).
11. **Unconsumed elements (advisory).** Every element earns its place by
    the modeling rules in [AGENTS.md](../../AGENTS.md#model-elements-earn-their-place):
    a gate requires it, something consumes it, or it carries a decision,
    assumption or gap that a later phase acts on. An element in an
    increment's scope that no gate requires and nothing consumes is
    reported as unconsumed: it is the subject of none of the increment's
    checks, and no other element references it as a type, a specialized,
    redefined or subsetted feature, a relationship end, a feature value, a
    framed concern, or an exposed or imported member (ownership does not
    count). The report never blocks a phase; whether such an element
    carries a decision, assumption or gap stays the reviewer's judgment.
    The Method Check does not produce this report yet.
12. **Allocation chain (phases 6 to 8).** The increment has at least one
    function. Each functional requirement of the increment
    (`FunctionalRequirementCandidate`) is allocated to at least one function,
    each function of the increment to at least one logical element, and each
    logical element of the increment to at least one physical element. The
    trace is the `allocatedTo` relation: a native
    `allocation ... allocate <source> to <target>;`, typed or not, whose
    ends ground in one of its three end pairs. An end written as a feature
    chain (`a.b`) counts as its last feature. Plain dependencies, and
    allocations whose ends ground in no end pair, don't count: they are
    reported as near misses. Absence is not established while any allocation
    is unreadable: an element without a counting allocation is then reported
    as unreadable, never as a gap. The increment's functions, logical and
    physical elements are the usages of `AllocatableFunction`,
    `LogicalAllocationElement` and `PhysicalAllocationElement` its packages
    own at any depth (parameters, ends and references to other features,
    such as `perform` usages, aside), plus the elements its own allocations
    name, so a reused baseline element enters through the increment's
    allocation and its baseline chain is read where it is. A declared phase 6
    or 7 without a function, or a declared phase 8 without a logical element,
    blocks. Advisory: each requirement of the increment, functional or not,
    is allocated to a function or named as relevant by an architecture
    element (`hasRelevantArchitecture`: a dependency from a part or action
    usage or definition to it), so an unallocated functional requirement
    shows here as well as in the blocking check. One that is neither is
    reported with what else holds it: an allocation that grounds in no end
    pair, else its verification (rule 6), which then covers it alone, or no
    verification case yet. Also advisory: each function, logical and
    physical element of the increment receives an allocation from the layer
    before it. A requirement carried by neither, or an element without an
    allocation from the layer before it, is allowed: the advisory checks
    report it for review, and nothing is authored just to clear them. The
    content check of the expected artifacts counts an allocation as content
    of the increment whose packages own its source end, wherever it is
    declared: a later increment that allocates an earlier increment's
    element from its own package shows, in the earlier increment's check, as
    content outside that increment's expected artifacts. An allocation
    assigns responsibility only: it claims no satisfaction, realization,
    transitivity, deployment or execution. The flows, states, exchanges and
    interfaces of these phases, and phase 8's realization-readiness control
    below, stay with review; its signal-mapping control is rule 13. Until the
    `allocatedTo` relation's admission obligations are discharged (traversal
    evidence and the API closure of the allocation ends at an exact
    revision), the method tools report these phases as method side on an API
    revision binding; the pull-request Method Check evaluates them on the
    export.
13. **Signal mapping and VSS (phase 8, advisory).** Two advisory checks read
    the system-to-software signal-mapping control below. On an API revision
    binding they are method side while rule 12's are.
    - **Crossings.** A crossing is a physical element of the increment that
      realizes a logical element (`allocatedTo`) and has an information
      port: a port with a directed feature of its own, of its definition (a
      conjugated port `~P` reads `P`), of a feature it redefines or subsets,
      or of a port a connector connects it to. Any directed feature counts.
      The check reads structure, never names, so it cannot tell an
      information item from power or another physical flow; such a crossing
      gets a record with the `notApplicable` disposition. A physical element
      without an information port, or realizing no logical element, is no
      crossing and needs no record. A port whose definition is not in the
      revision, or that has no type, no feature, nothing it narrows and no
      connected port, cannot be read: the result is indeterminate, not "no
      crossing". So can a port without a directed feature of its own while
      a connector of the revision cannot be read, because its connected
      ports decide; an element without ports is unaffected.
    - **Mappings.** Each logical element a crossing realizes has a
      system-to-software signal mapping: an allocation typed
      `SystemToSoftwareSignalMappingCandidate` from the logical element to a
      physical element of the increment that realizes it, or to a port of
      one. A port the element has from its definition is written as a chain
      through the element (`<element>.<port>`): the definition's own port is
      every usage's, so an allocation to it covers no crossing. The mapping
      counts when a package of the increment owns it, as the
      `signalMappings` parameter counts it; a mapping in another package, or
      nested in a definition, is reported and does not count. Every
      `LogicalToSoftwareSignalMappingRecord` it owns states a disposition, an
      owner and a next action, and a `notApplicable` record states why in
      `evidenceOrGap`.
    - **Unit.** The check counts one mapping
      per realized logical element, and one mapping may cover the processes
      of that element's chain; its contract fields name the further
      contracts. Whether each interface-bearing information item that enters
      a software contract has its record stays with review (see the review
      checklist).
    - **Semantic source.** Each record of a signal mapping states the item's
      `semanticSource`, what the item is and why no VSS signal applies,
      unless the item at the mapping's port is VSS-typed: the port, or an
      item or attribute in it, is typed by a signal of COVESA VSS or of
      `DE4SDV_VSS_Extensions`, whose `@VssSignalMetadata` names its path. The
      check reads that metadata definition by identity: the loader of an
      export binds it by the file-mapped rule of the kernel bindings (its
      metatype, declared name and source document), and no other metadata
      counts. VSS typing is read at a port, never at an element: a mapping
      to an element states the source in its records.
    - **Stated values.** A record member that still holds a remedy's
      placeholder (`<…>`), or only TBD, TBC or TODO, states nothing. Any
      other text counts as stated, and what it says is not judged.
    - **Left to review.** The checks don't find an item without a record of
      its own when its logical element's mapping has a record for another
      item, read an untyped port only through its connections, and don't
      judge what a stated value says. A
      VSS path in a doc or a string is no VSS typing, a signal the pinned VSS
      snapshot lacks goes into `DE4SDV_VSS_Extensions` as a candidate, and
      whether an item is a vehicle signal stays the reviewer's judgment.
14. **Concerns (phase 1).** Each concern of the increment has a native
    stakeholder member. A viewpoint of a view in a package of the increment
    frames it. Both checks block. The concerns are the concern usages the
    increment's packages own. Their stakeholders are the native
    `stakeholder` members of the concerns, the problem statement and the
    needs. So no check counts stakeholder parts: such a part would only
    restate them (rule 11). A frame owned by a need or a requirement does
    not count (rule 3). Nor does a viewpoint of a view outside the
    increment's packages.
15. **Publication (phase 11).** Each view of the increment has a viewpoint,
    of its own or of its definition, that frames a concern. Each view, or a
    view it owns at any depth, exposes model content. A table or matrix view
    exposes through its row, column and cell views. Both checks block and
    judge the model only. The pull request, its review and the rendered
    diagrams are judged outside the model. CI checks the diagrams and each
    folder's `VIEWS.md`, and review judges the rest.
16. **Variability and the baseline decision (phases 9 and 12).** These two
    steps have no executable check, because what they declare cannot be
    checked deterministically:
    - **Phase 9.** Its parameters are untyped `part` usages, so a check
      would count every part usage of the scope. The kernel has no class
      for the configured product a phase-9 slice declares, and a native
      variation point has no selector. The lower bound 1 of
      `variationPoints` also contradicts accepted phase-9 work. A slice may
      configure a member from existing variability, and shared variation
      points live in shared-asset packages.
    - **Phase 12.** The baseline decision is typed like the framing step's
      lifecycle decision, which every scope holds. A count would pass on
      the framing decision alone, and a separate baseline decision would
      break the multiplicity `[1]`. `IncrementGap` states no disposition,
      owner or next action. The baseline register and the status of an
      architecture decision record are repository text, which the
      evaluation does not read.

    Review judges both steps, and their exits stay `BLOCKED` with
    `CONTRACT_UNAVAILABLE`, never passed.

[`DE4SDV_IncrementWorkflow`](../../textual-notation-of-model/packages/methods/de4sdv/de4sdv_increment_workflow.sysml)
models this workflow in the style of the SYSMOD default process. The
`IncrementWorkflow` action has one step per phase in method order. Increment
framing always applies, and each later step is optional: it applies when the
increment charter lists the step's phase. Each step definition states its
phase question, its phase, and the artifacts it reads and produces as typed
parameters.

The checks of these rules are `MethodCheck` metadata inside the step
definitions, one check per rule clause, each about the step parameter it
constrains. The check identifier names the evaluation, an unknown identifier
fails closed, and `advisory = true` marks the advisory checks. Every step
carries checks except variability and configuration (phase 9) and the
baseline decision (phase 12); rule 16 says why. The physical-architecture
step also checks rule 13. The phase-2 checks of rule 9 are about the
operational context, the parameter through which they reach it. They read the
story's use cases from there. Rule 11 is a report over the whole scope, not a
check of one step. Declaring a check is not evaluating it, and no check
result is a conformance, acceptance, or certification claim.

## Workflow phases

| Phase | Question | SAF domain | Main outputs |
|---|---|---|---|
| 0. Increment framing | What are we changing or learning? | Common | increment charter, scope, assumptions |
| 1. Concern framing | Who cares and why? | Common / Operational | stakeholders, concerns, viewpoint selection |
| 2. Operational context | What happens in the world? | Operational | context, actors, scenarios, operational processes |
| 3. Capability / feature semantics | Which characteristics distinguish member products? | DE4SDV ontology | feature candidates: the feature-model delta |
| 4. Needs | What stakeholder needs exist and how will the needs be validated? | Operational | needs, sources, rationale, validation intent |
| 5. Requirements | What shall the system or product line do and how will those requirements be verified? | Conceptual | design input requirements, constraints, verification methods, success criteria, trace links |
| 6. Functional architecture | What functions, flows, states, and interfaces are needed? | Conceptual | functional breakdown, interfaces, behavior slices |
| 7. Logical architecture | What technology-independent logical elements realize the functions? | Conceptual | logical structure, exchanges, allocation/mapping |
| 8. Physical / software realization | What software, hardware, deployment, or tool elements realize the system design? | Physical | physical/software structure, interfaces, mappings, readiness probes when required |
| 9. Variability and configuration | How does this vary across member products or configurations? | DE4SDV product-line layer | variation points, feature configurations, applicability |
| 10. V&V and evidence | How will requirement satisfaction and stakeholder fitness-for-use be checked? | Common / Conceptual | verification cases, validation scenarios, evidence records, open gaps |
| 11. Publication | What is reviewable now? | DE4SDV workflow | SysML v2, Markdown, YAML, generated views, reports, PR |
| 12. Baseline and next slice | What is accepted, deferred, or invalidated? | Common | baseline decision, open issues, next increment |

`System architecture` is the umbrella for the architecture of the system and
its coordinated views; it is not the name of Phase 7. Phases 6 through 8
elaborate functional architecture, logical architecture, and physical/software
realization artifacts. SAF's current `System*` names are viewpoint names in the
Conceptual Domain, not a replacement name for the logical-architecture artifact.

## Cross-phase system-to-software signal mapping control

Whenever a logical or semantic information item crosses into a concrete
software, service, topic, API, or physical interface, create an explicit
system-to-software signal mapping. This is a recurring control applied at
each applicable boundary, variant, and contract revision; it is not a new
lifecycle phase and it is not limited to VSS or VSIDL.

The mapping is required for interface-bearing information items, not for every
internal calculation, which needs no record. Rule 13 states which elements are
crossings. A crossing whose item crosses no software contract gets a record with
the `notApplicable` disposition, and its `evidenceOrGap` says why. If the
downstream contract is not pinned, record a candidate or deferred mapping and
its gap rather than treating the signal as unmapped.

A mapping is an allocation typed `SystemToSoftwareSignalMappingCandidate` from
the logical element to the port where its item enters the software contract,
owning one `LogicalToSoftwareSignalMappingRecord`. Together they identify:

- the stable mapping ID: the record's short name (`<'MAP-…'>`);
- the qualified logical or semantic source: the mapping's source end, and the
  VSS typing of the item at its target (a vehicle signal is typed with COVESA
  VSS or `DE4SDV_VSS_Extensions`); for an item that is no vehicle signal, the
  record's `semanticSource` states what it is;
- the software contract identity, in `softwareContractArtifact`,
  `softwareContractMessage` and `softwareContractField`: service, API or topic,
  message, field, and source artifact and revision, each marked exact or
  candidate;
- the physical or software adapter endpoints and the direction: the mapping's
  target end, its typed ports and directed items, and the connections, with
  the further contracts of the same item in the contract fields;
- datatype, unit, timing and freshness, quality, availability, and state
  semantics that matter at the boundary (`dataTypeAndUnit`,
  `timingQualityAndState`);
- the pass-through, unit conversion, derivation, filtering, or state rule
  (`transformationRule`);
- the disposition, owner and next action (`disposition`, `owner`,
  `nextAction`), and the open gap and the verification or evidence record that
  can demonstrate the mapping (`evidenceOrGap`).

SysML owns the semantic endpoints, typed ports/items, and trace relationships.
A machine-readable control artifact may carry exact contract fields and
status. `.proto`, `.vsidl`, generated bindings, implementation code, tests,
and runtime observations remain authoritative in their respective external
artifacts. A mapping is not a runtime-interoperability claim.

The physical/software realization exit rule asks that every applicable crossing
has a `mapped`, `candidate`, `deferred`, or `notApplicable` disposition with an
owner and next action. A generic dependency, same-name element, or port
allocation cannot substitute for the mapping. The Method Check checks rule 13
as advisory: it reports a crossing without a mapping whose records are
complete, and a mapping with a record that neither states its source nor maps
a VSS-typed item, but never closes or blocks a phase exit. It counts one
mapping per realized logical element; whether every item has its record, and
whether the records are right, stays with the review.

## Realization-readiness control

Phase 8 uses a realization-readiness probe when the candidate physical/software
realization depends on an enabling system such as a build host, toolchain,
hypervisor, runtime, simulator, or verification environment. This is a
cross-phase control, not an additional lifecycle phase.

Run the probe before expensive source synchronization, build, deployment, or
runtime evidence collection. Record:

- the realization question and candidate enabling system;
- the required resource, operating-system, toolchain, and runtime capabilities;
- the evidence status and retained observations;
- affected SysML constraints, assumptions, allocations, or gaps; and
- the disposition: proceed, re-scope, or defer.

A successful readiness probe establishes only that the enabling system passed
the stated gate. It does not prove target-runtime interoperability, product
acceptance, safety, certification, or production readiness.

## Increment sizes

Use the smallest size that produces useful evidence:

| Size | Meaning | Typical artifacts |
|---|---|---|
| XS | one correction or trace link | one file/snippet, short rationale |
| S | one feature/scenario/context slice | charter + one or two model/docs artifacts |
| M | cross-viewpoint increment | context + requirements + architecture + evidence links |
| L | end-to-end feature baseline | multiple views, model packages, evidence, generated artifacts |

Default to **S** until the method proves stable.

## Lifecycle decision framing

Every increment should state the lifecycle decision it supports. Examples:

- accept a stakeholder need as in scope,
- approve a requirement as a design input,
- select or defer a product-line feature,
- accept an architecture allocation,
- accept a verification result as evidence,
- baseline or reject a generated view/model artifact.

This keeps the method from producing decorative diagrams with no decision value.

## Required trace chain

Every substantial increment should try to establish this chain, even if some links are draft:

```text
Stakeholder concern
  -> Need (provenance: stakeholder, source, rationale; not framing or derivation)
  -> Requirement / constraint
  -> Feature, for a varying requirement only (a core requirement has none)
  -> Architecture element / function / interface
  -> System-to-software signal mapping (when a boundary is crossed)
  -> Physical/software realization or configuration
  -> Verification case and validation scenario
  -> Success criteria stated on the requirement
  -> Evidence artifact and evidence status
  -> Baseline or release decision
```

If a link is intentionally missing, record the gap instead of hiding it.

### Trace links live in SysML, not in pilot YAML

The trace chain is expressed as SysML `dependency` usages inside the increment
model files: each phase traces to the prior phase's accepted elements and to
source part definitions. Pilot YAML files carry framing metadata only — their
`trace_ids` list is an index of the SysML dependency usage names, never a
second trace artifact. Provenance for external sources (repository, revision,
path) lives in the source part definition's `doc` block in the model.

Consequences:

- A new increment phase adds its `dependency` usages in the corresponding
  `.sysml` file, not a `source_alignment` block in YAML.
- Renaming or deleting a dependency requires updating the referencing
  `trace_ids` index — the YAML must never describe a trace the model does not
  declare.
- Cross-increment baselines target the prior phase's accepted elements by
  qualified name (for example
  `dependency requirementNeedsTrace from ...reqProvideMiddlewareSignalAccess
  to ...needMiddlewareIntegration`), not a copy of the prior artifact.

## Needs, requirements, verification, and validation

Do not collapse these into one list. DE4SDV increments must keep the distinctions explicit:

| Concept | DE4SDV meaning | Typical question |
|---|---|---|
| Need | stakeholder problem-space intent | Is this what the stakeholder needs in context? |
| Requirement | verifiable design-input obligation or constraint | Can the system/design satisfy this? |
| Verification case | planned or executed check of requirement satisfaction | Did we build/specify it right? |
| Validation scenario | check of stakeholder fitness-for-use in context | Did we address the real need? |
| Success criteria | observable conditions, stated on a requirement, under which verification shows it is met | What result shows the requirement is met? |
| Evidence artifact | reviewable result supporting a decision | What can reviewers inspect? |
| Gap | known missing link, uncertainty, or unproven claim | What must not be treated as complete yet? |

For early increments, a planned verification/validation record is acceptable. Hiding that it is only planned is not.

## Feature/common-capability rule

A characteristic is a DE4SDV **feature** only when it distinguishes at least one member product from another member product in the product line. What all member products have is common, not a feature.

Phase 3 records only the feature-model delta (rule 10): the feature candidates the increment adds. Core elements are common by default and get no record. For example, an AEBS increment would:

- record VRU detection support as a feature candidate if only selected variants provide it,
- record performance level or sensor package as feature candidates if they differ between member products; phase 9 turns them into variation points,
- record nothing for baseline forward collision risk mitigation, which every member product has.

## Evidence status vocabulary

Use explicit evidence status values:

| Status | Meaning |
|---|---|
| `draft` | proposed and not reviewed |
| `planned` | intended but not executed |
| `simulated` | produced by simulation under stated assumptions |
| `tested` | produced by an executed test under stated conditions |
| `inspected` | reviewed by inspection/checklist |
| `analyzed` | supported by analysis/model calculation |
| `accepted` | accepted for the stated baseline or decision |
| `rejected` | reviewed and not accepted |
| `gap` | deliberately recorded missing evidence or trace link |

Avoid `certified`, `compliant`, or `approved` unless the responsible authority and scope are explicit.

## Review questions

Each increment PR should answer:

- What engineering question does this increment answer?
- Which SAF viewpoints were selected and why?
- Which stakeholder concerns are addressed?
- What is explicitly out of scope?
- Are needs separated from requirements?
- Does phase 3 record only the feature candidates the increment adds?
- Does every element earn its place: a gate, a consumer, or a decision, assumption or gap that a later phase acts on?
- What trace links exist and what gaps remain?
- What verification method, success criteria, validation scenario, and evidence status are recorded?
- Are compliance/certification claims avoided or clearly marked as not yet established?

## Publication rule

Generated views, reports, and model snapshots are publication artifacts. They are not automatically evidence of correctness. Each artifact must have enough metadata to show:

- source model or source document,
- generation command or manual source,
- date or baseline reference,
- known limitations,
- reviewer expectations.
