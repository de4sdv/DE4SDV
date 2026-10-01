# Explicit runtime composition (non-production)

The definition-only path could not serve the reviewed O3 relationships at
once. `de4sdv/semantic/composition_construction.py` verifies both components
against one exact revision binding before assembling the real binder,
traversal, query and impact services.

Bootstrap verification is separate from live query code in
`de4sdv/semantic/runtime_composition.py`. The query module receives constructed
authorities and imports no definition-construction or governance module. The
existing layer guard remains in force; only the bootstrap module is classified
as construction machinery.

Routing is disjoint: frozen O3 identities use O3, admitted definition classes
use the verified definition pair, and unmigrated identities use the explicit
remaining authored fallback. A failed migrated request never retries the
fallback. Vocabulary-only admissions add no relationships or traversal.
`hasStakeholder` is not admitted; decision 11 remains outstanding.

## Explicit consumers

MCP and API impact CLIs accept `--runtime-composition o3+definitions` together
with `--semantic-authority o3`, `--o3-authority-bundle` and
`--o3-authority-bundle-id`. The full-model semantic-query validation CLI uses
the same arguments and constructor. The viewer's `_runtime` accepts explicit
composition/bundle arguments for non-production construction; the deployed
viewer request handler does not select this path. Existing default legacy and
production O3 environment choices remain unchanged. No composition selector
is read from the environment.

The composite identity covers the O3 bundle, complete definition content and
binding inputs, exact API binding bytes, and a separate current implementation
manifest. Its nine files cover both composition modules, the definition loader,
migration and provider, API client/repository, and model-edge/relationship
helpers. Executed sources must resolve to those repository files; an external
provider substitution refuses before any query runtime can serve. This does
not extend or alter the frozen O3 runtime-build input set.
Query/impact provenance identifies both components and the remaining fallback;
it also retains the implementation manifest. Viewer snapshot/cache identity
uses the composite authority id, including every manifest file digest.

Composition always remains activation-blocked. A production or
`require_activation_eligible` request enforces O3 eligibility and then refuses
composition itself. Closed but ineligible O3 bundles may be compared only in
the explicit non-production path; incomplete definition closure is refused.

## Evidence boundary

Synthetic fixture tests exercise real constructors and entrypoints, with only
API transport/stdio serving replaced. They do not prove privileged closure.
Retained ingestion run 36781390352 can be replayed read-only with its exact
`7ac059d5d619d4e47017a582f9f79dd2b33b7ced` binding. Such replay does not establish
closure for `d51438c837c49aae460b37b76f8b3ea911672852` or a future landing commit.
The frozen runtime, O3 bundle implementation, traversal, impact and governed
inputs are not modified. Historical O3 bundle verification is not weakened;
any later change to a recorded runtime-build input requires fresh bundle and
post-merge evidence at the actual revision.

Whole-consumer retirement remains pending. The MCP proof-side native-subject
construction, ingestion validators and other remaining consumers still need
shared-contract wiring and exact-revision verification. Independent review,
current permanent-revision evidence and separately authorized activation are
not supplied by this package.
