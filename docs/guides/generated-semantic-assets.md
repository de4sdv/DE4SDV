# Generate semantic assets with the source change

A model edit should not need a second commit or a repair PR after a squash
merge. Live projection/profile files are deterministic outputs of the current
working tree. Their generators' check modes compare the complete regenerated
output with the stored file; missing, altered or stale output fails.

## Edit, regenerate, check, commit once

From the repository root, with the repository's pinned dependencies installed:

```bash
sysand sync
python scripts/generate_definition_projection.py --batch all
python scripts/generate_semantic_projection_o2p.py
python scripts/generate_vocabulary_carriers.py
python scripts/check_model_projection_coverage.py --write-baseline
python scripts/check_repo.py
python scripts/smoke_test.py
python tools/check_markdown_links.py
python -m pytest tests -q -p no:cacheprovider
python tools/run_bench_unit_tests.py
```

Run the generators in the listed order. Vocabulary relationships validate
their end types against the generated class-source pairs; their generator
never reads its own output files. Regenerate class-source pairs first if
they are missing or stale, then regenerate vocabulary output, without an
intermediate source commit.

Stage the intended source changes and regenerated live files together, then
make one commit. Do not pass a source revision or create an intermediate
source-only commit for generation. `check_repo.py` runs each live freshness
check and the coverage-baseline comparison; regeneration cannot admit a
residual identity, unaccounted kernel declaration or duplicate provider.

Model-owned documentation stays in the model. Admission manifests retain
reviewed scope and representation fields, not duplicate kernel definition
text. Removing that duplicate text oracle does not admit new identities,
change runtime support or turn review evidence into certification.

## Historical records are different

The [frozen records](../method-conformance/frozen-records.md) and their manifest
remain byte-identical. `scripts/verify_generated_chain.py` checks their bytes,
record set, historical source revisions and references only. Never regenerate
those records against current source. Their historical references to a deleted
input are evidence, not a live authority.

The closed consumer ledger is retired. Its replacement guard prevents the
deleted ontology file and ledger from being restored and scans live tracked
files case-insensitively, without extension filtering or content truncation.
Historical documentation, test references and the retained historical review
helper are explicitly outside live consumption; their mentions remain intact.

## Identity and release boundary

Semantic-authority identity represents semantic contract content, not application
code provenance. Incidental Git commits or runtime source-file bytes must not
change that identity. A semantic payload change must change it. The deployment's
application revision and validated-export binding remain separate startup guards;
this is not permission to substitute unreviewed code or an unvalidated model.

The successor digest selects `schema`, `supersedes`, `classes`, `carriers`,
`relations` and `retired`. The authority digest includes declared provider
records, projection/profile meaning, served class and relationship mappings,
refusal strings, lineage ownership and that full successor payload. File paths
label the semantic layer digests; the digest values are not raw file checksums.

Explicit record provenance exclusions are `wave`, `register_wave`, `review_ref`,
`accepted_ref` and `api_identity`; profile provenance also excludes
`mechanics_source` and `mechanics_refs`. Within semantic records only
`representation.toolchain` and `external_reference.accepted_ref` are excluded.
Other nested meaning remains covered, including documentation, declaration
witnesses, subtype/disjointness constraints, endpoint direction, strength,
discriminator pins, representation metaclasses and serializer rules. Unknown
record fields refuse instead of silently becoming metadata. Object/record
ordering is incidental; nested semantic-list ordering remains significant.

Live document wrappers are closed by layer and role. Every wrapper admits
`schema`, `status` and `warning`; definition, batch-2 and O2+ projections also
admit `scope` and `rows`, while vocabulary projections admit `candidates`,
`admitted` and `rows`. Profiles admit `entries`, not projection fields. These
wrapper meanings, including complete nested scope and population declarations,
enter the live semantic digest. Legacy `binding` is allowed only as incidental
provenance and remains excluded. Unknown wrapper fields refuse before decoding.
The frozen O2 document loaders and their semantic digest contract are unchanged.

Live rows and profile entries must be object lists with unique, nonempty,
unambiguous string identities. Live JSON object keys must be unique at every
depth; duplicate keys refuse before decoding instead of choosing a last value.
Duplicate record identities refuse even if they agree;
conflicting duplicates cannot select a last-wins serializer mapping. Entries
must join to a projection row. Definition, batch-2 and vocabulary pairs require
one entry per row. O2+ requires entries only for modeled API-profile outputs
(`outputs.api_profile_entry`, or `outputs.api_profile_required` when supplied):
its current eight rows have only the `Variant` and `VariationPoint` entries.
Unmarked synthetic O2+ rows may have no entry. The optional absent batch-2 pair
remains optional. Consumed enum/string, object and list shapes are validated
before provider lookups; malformed JSON inputs raise `ModelAuthorityRefused`,
not incidental Python type errors. This is a bounded JSON-input contract, not
a replacement SysML parser or a frozen-history migration.

The next privileged run must mint a deployment binding with the new identity.
Ship this change with that next release, never hot-apply it to a deployment that
uses an older binding. This workflow does not dispatch a release, approve a
production environment or change kernel bindings.
