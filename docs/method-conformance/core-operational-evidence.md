# Method Core operational evidence

Implementation tests alone do not establish operational acceptance. A blocked
pilot is a legitimate engine result; it must not be rewritten as acceptance.

## Delivered checker status — 2026-10-05

Orkun Yilmaz defines **V1 Core (A–D) delivered** as checker proof by honest real
009D disposition plus independent MC-30 agreement, separate from later 009D
campaign acceptance. The retained evidence meets that delivery definition:

- Permanent-main hosted workflow delivery:
  [Core run 37209640874](https://github.com/de4sdv/DE4SDV/actions/runs/37209640874),
  artifact `11306160460` (archive digest
  `001cde66883659707d3a6e1aeeb0805b5c8a7fcfb1545bef79257b5deba9ed86`).
  Workflow source is permanent-main squash `b4346bcf36368cf8e300a8fb15d462458e47dd4b`;
  the verified executor/model input remains
  `4d2f3ae0144e414a97a3602d98ea105ec038d552`, from ingestion `37144085070`.
  This proves hosted workflow delivery, not ingestion of the later squash or
  of the present closure changes.
- Independent MC-30 agreement: **11 obligations / 51 children** all agree;
  pilot **7 PASS / 1 FAIL / 3 INDETERMINATE**, readiness **BLOCKED**. The
  independent derivation is retained in
  `/home/mrk/.hermes/outputs/ingestion-37144085070/independent-pilot-review/`
  (`derived-facts.json`, `expected-table.json`, `comparison.json`), with the
  separate review binding at
  `/home/mrk/.hermes/outputs/post-pr324/mc30-review-binding/independent-review-record.json`.
  Agreement binds evaluation key
  `94a96fd8fc339e3a41f1fc9fd51e5c5fef598d5f24c14c712c7a1bda0a93d57e`
  at the verified input revision above. It does not rewrite the hosted
  receipt's missing independent-review field or auto-acceptance flags.

This is a **not-yet-accepted campaign**. These historical dispositions stay
unchanged; they are not current-candidate evidence. Policy activation now makes
an actually complete empty-registry scan FAIL with `ACCEPTANCE_AUTHORITY_MISSING`,
not INDETERMINATE. The metadata export repair still needs licensed exact-head
export/import and readback; scope equality still requires a fresh bench campaign.
See [pilot-scope.md](pilot-scope.md#closure-diagnosis--2026-10-05).

Delivery remains **ADVISORY**; no required check or branch protection is changed.
O4 and PLE remain outstanding: the unified plan is incomplete. No safety,
certification, compliance, homologation or product acceptance is claimed.

The present uncommitted closure is **not a ready delivery head**: its evaluator
and pilot-policy data change inputs bound by the committed O1 inventory.
Repository/generated-chain gates correctly report stale source-revision/content
bindings. Regeneration needs a real reviewed commit containing the input bytes
and a governed downstream recovery; staging is not a commit. The native model,
O2/O3 artifacts and pins are unchanged; a gratuitous model-status text edit is
not needed to activate its externally referenced policy. No artifact,
source-revision pin or gate is rewritten/bypassed to conceal the O1 red state.
This does not change the historical delivered-checker milestone above.

## Executable path

`scripts/run_core_operational_exit.py` runs the existing
`scripts/run_snapshot_parity.py` modes in **four fresh subprocesses**: build,
verify, offline, tamper. It retains commands, actual exits, report digests,
canonical evaluation-key/payload agreement, the complete refusal matrix, and the
underlying process measurements. It never ingests, deploys, merges or approves.
A fresh output directory is mandatory so stale reports cannot mask a failed run.

Example, using already-downloaded exact-run artifacts:

```bash
python scripts/run_core_operational_exit.py \
  --repo . --artifacts /path/to/retained-ingestion \
  --validation-run RUN_ID --expected-revision EXACT_SHA \
  --out /path/to/new-receipt-directory
```

`RUN_ID` must be numeric and `EXACT_SHA` a full lowercase Git SHA. Input revision,
export identity, digest, element count and validated binding must agree.
Historical diagnostic replay additionally requires `--allow-historical` and is
explicitly labeled historical. It is never permanent provenance or current-main
closure. An optional `--independent-review` binds a separate JSON record's
`evaluation_key`, `git_commit`, `contract_digest`, `parity`, and `source`;
**record-bound is not reviewer authorization, independence or MC-30 acceptance**.
Those facts still require an independent engineering review.

The receipt separates `model_repo_git_head` (`--repo`) from the executing
script checkout's `executor_git_head` and `executor_source_dirty`. Current
classification requires the artifact to match both checkout revisions;
a differing executor revision requires explicit historical replay even when
`--repo` matches the retained artifact.

Exit 0 means the replay battery produced consistent evidence. It does **not**
mean that the pilot, product, Core milestone or certification is accepted.
Exit 2 means input refusal or a failed battery; detailed receipts/logs remain.

## Intended runner

`Method Core Operational Evidence` is a manually triggered advisory workflow on
`ubuntu-latest`, using the same Python family as public CI. It requires an exact
permanent main-history revision and an already successful exact-revision
`Privileged Full-Model API Ingestion` run. Before download it verifies the
provider-side workflow identity, source SHA, successful dispatched run, complete
artifact inventory, unique unexpired artifact and recorded artifact origin.
It downloads that exact artifact object, not a latest artifact or moving branch.
The provider-origin record and runner context are retained beside the receipts.
No model ingestion or privileged secrets are used by this replay workflow.

Downloaded inputs and all generated origin, tested-input, battery and advisory
receipts stay under the runner's temporary directory, outside the selected Git
checkout. This preserves honest `executor_source_dirty` reporting: generated
evidence must not contaminate its own executor or be hidden by an ignore-rule
exception. A green run with a dirty executor is not clean-executor evidence;
repair workspace isolation and replay the same verified ingestion artifact.
Failure receipts remain uploadable after path initialization. If setup fails
before that initialization, upload is skipped rather than expanding an unset
evidence-directory context to the filesystem root.

The validated pilot scope may name a tested execution commit outside main's
history. The workflow reads that exact `executionHead` from the validated
retained export and fetches the missing Git object without switching the
selected executor checkout. An invalid, unresolved or unavailable tested
commit refuses replay. The retained `tested-git-input.json` labels this object
as a declared tested execution input, **not** permanent executor provenance,
approval or evidence carry-forward. No model value or acceptance gate changes.

An optional PR number executes the existing read-only delivery observer against
live GitHub state. It does not attach historical conformance to a different PR
head or invent an independent cross-check. Missing conformance/review authority,
draft state or protection-read access may legitimately block/refuse that
observation. A green replay workflow does not close delivery acceptance.

## Claim boundaries and remaining acceptance

- `api_export_parse_seconds` measures **retained export parsing**, not live API
  pagination, fetch latency or service ingestion. API/snapshot equality is
  equality of those verified semantic inputs, not fresh production deployment.
- Offline metrics come from the separate snapshot-only process. The runner
  retains load/evaluation time and RSS; it does not invent an adopted budget or
  declare suitability automatically. Full-baseline/live-load measurements and
  a reviewed intended-runner budget remain separate acceptance evidence.
- Local receipt checks establish consistency, not trusted artifact origin. The
  workflow/provider record supplies a separate origin boundary.
- Historical replay, changed executor sources and an unsigned review file do
  not establish current permanent-revision acceptance.
- The retained independent MC-30 agreement above establishes checker delivery
  for those evaluated inputs only. New evaluated inputs require a new independent
  comparison; the receipt never sets `mc30_accepted` or `core_accepted` true.
- Existing branch protection and required reviews remain authoritative. No
  semantic-authority selection, O3 scope or authored-YAML retirement changes.
