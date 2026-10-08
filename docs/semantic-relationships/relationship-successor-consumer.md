# Relationship successor: supplied-API consumer (draft)

The successor exposes actual responsibility, validation-planning and source-provenance
relationships without turning them into satisfaction, execution, deployment or compliance.
It was introduced as an explicitly selected **non-production** sidecar; since O4 Wave C2
it is part of the model-authority runtime (the only semantic authority).

## Model-backed scope

Existing AEBS function definitions specialize `AllocatableFunction`; existing logical
parts specialize `LogicalAllocationElement`. Seven new native requirement-to-function
allocations target the **same** `DE4SDV_AEBSLogicalArchitecture::functionalFlow`
occurrence that the ten existing function-to-logical allocations use. Existing
specification dependencies stay weaker specification/change-impact facts; no duplicate
relevance link is required for an allocation. A path is individual witnessed edges,
not an inferred/transitive allocation or a mandatory architecture chain.

`VAL-AEBS-001` is modeled as one `ValidationPlanningScenario` with a typed planning
association to `needCommonAEBSCapability`. The plan comes from the existing
`aebs-needs-requirements.yaml`; it carries no execution/result/verdict.
The existing controlled R152 identity is modeled as `ControlledRegulatorySource`
and associated with pedestrian/bicycle response requirements. Identity, revision and
location are taken from `aebs-regulatory-source.yaml`, not invented applicability.
No obligation, satisfaction condition, certification or homologation is established.

Native logical-to-physical allocations are visible only when their actual endpoints
have validated `LogicalAllocationElement` and `PhysicalAllocationElement` lineage.
Existing source-available/partial allocations, missing owners and blocked branches
retain their separate meanings; typing cannot upgrade their coverage. System 2
simulator/evidence assets and item-schema mappings are not physical responsibility
owners in this profile. Licensed validation/serialization and exact API readback
remain required for every authored model claim.

## Exact-pin ingestion and routing

The model-built kernel contract retains the predecessor native `Function`, `LogicalElement`,
`PhysicalElement` and `ValidationScenario` categories (lineage-pinned since O4 Wave C2). The explicit successor
lineage roots and two typed association definitions are separately mapped for
ingestion. Construction-only records and native-allocation end-pair descriptors
remain reasoned kernel exclusions; they are not extra predicates or native facts.
Normal licensed ingestion validates those mappings using serializer source-document
provenance and persists `kernel_bindings` with source file, declaration and API UUID.

At successor construction, each profile endpoint class (e.g. `Function`) is pinned
from the model-built contract's kernel mapping: the class's own `file` + `declaration`,
or, for a natively represented class, its unique file-mapped specialization (e.g.
`AllocatableFunction`). The SysML model carries no file-path records.
`route_successor_bindings` then matches each profile slot's
**exact file + declaration** against those already validated tuples. The matching
UUID is installed in a successor-only binding index under the slot (e.g. `Function`).
This is not UUID discovery by name, a source-text runtime parser, or rewriting the
original revision binding. Ambiguous or contradictory pins refuse construction;
missing pins produce incomplete query status, never guessed identities. Results echo
`binding_routes` including the ingestion class and exact routed UUID. The predecessor
index and all global authority selectors remain unchanged.

Discrimination requires every reachable typing/specialization branch to be
represented; one grounded branch cannot hide another dangling branch. An external
leaf needs a URI on its exact reference, not on unrelated data. Graph, flat and
inlined `referencedFeature` shapes are normalized together, with their API/property
witness retained; conflicting targets refuse rather than becoming absence.
Every supplied reference member must first have an interpretable identity. A
missing or blank endpoint, typing or specialization identity is incomplete
evidence, not a member that may be discarded before cardinality or lineage checks.

`relationship_successor_contract.py` extracts and verifies source-derived records
at bootstrap, through `composition_construction.py`. The live relationship service
cannot import that source-reading extractor; queries consume the constructed
profile and API binding only. The repository layering guard enforces this split.
Construction masks comments and both quoted-token forms together; comment markers
inside a literal remain literal content. Required record fields are checked before
use. These bounded lexical checks do not replace licensed SysML validation.
Declaration location and owned-body matching run through that same scan, so a
commented or quoted duplicate cannot move a record boundary, and a duplicated live
declaration refuses instead of silently supplying the first match.
Records and carriers must themselves belong directly to the governed package;
correct fields inside a foreign owner's block do not establish authority. Carrier
end qualifications must identify the pinned declaration in its exact source file
and owning namespace. A same-named foreign or unresolved type cannot satisfy a pin.
Bare cross-file end names also require a uniquely visible known pinned identity;
competing directly imported homonyms require canonical qualification, not a guess.
If known pins repeat the same qualified declaration in distinct files, even the
qualified spelling cannot choose a file and construction refuses.

## Runnable CLI and MCP

O4 Wave C2 retired the separate non-production sidecar CLI
(`scripts/relationship_successor.py`) together with its `legacy` and
`o3+definitions` predecessors: the successor relations are served by the
model-authority runtime as default predicates, and the retired names
(`realizedBy`, `deployedTo`, `validatedBy`, `validatesFitnessForUse`,
`constrainedBy`) are refused as `retired; use <successor>`. Query them
through the semantic MCP server (`scripts/semantic_mcp_server.py
--semantic-authority model --model-authority-bundle PATH
--model-authority-bundle-id mab-…`) or the impact CLI
(`scripts/query_model_impact.py`), both read-only. See
`docs/method-conformance/o4/model-authority-runtime.md`.

## Evidence boundary

`tests/test_relationship_successor_consumer.py` runs the real CLI subprocess and
real MCP stdio handshake/tool call over a local **synthetic** supplied HTTP API.
It proves transport, exact-pin routing and read-only behavior, not licensed model
closure or a production current-baseline observation. Model wiring tests are lexical.
Request maintainer-run privileged Syside validation and API ingestion/readback at
the reviewed exact head before promoting the model slice beyond draft. Parent owns
aggregate generation, frozen O3/projection/profile preservation proofs and W6.
