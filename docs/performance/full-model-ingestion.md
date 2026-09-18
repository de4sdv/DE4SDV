# Full-Model Ingestion — Baseline Performance Report

Status: `draft` — historical privileged baseline plus a measured local HTTP replay.
**No privileged end-to-end speedup is claimed.** The implementation removes a duplicate
read-back and adds out-of-band instrumentation; the replay evidence is below.

- Investigation starting revision (not the measured run): `d7344c6cde503b22a14ceea0a8944f0864d0e1b7` (worktree
  `perf/full-model-ingestion`; predates the #275 rebind — the known
  pre-rebind ancestry `check_repo.py` failure is unrelated to this report, `smoke_test.py` passes).
- Canonical run: `35203768046` at `020d1d20e5c03542f67f38b1cc716f4332478538`
  (workflow `privileged-full-model-api-ingestion.yml`, run 115, success).
- Workflow timeout cap in effect: **360 minutes** (not 180; see cap history below).
- The workflow comment at line 22 claims “~35-60 min serialized”. Measured runs take
  **175–300 minutes**, so the comment is stale and must not be used for planning.

## Evidence sources

All measurements below are read-only reconstructions from retained evidence:

- GitHub Actions run/job/step JSON for runs `35203768046`, `35172409514`,
  `35121352783`, `35082429369` (fetched via `gh api` into a local audit workspace).
- Full job logs (`log-35203768046.txt`, 2 842 lines, plus the other three runs).
- Retained canonical artifact (`full-model-api-ingestion-020d1d20…`, 41 934 299 bytes
  compressed) downloaded into a local audit workspace.
- Parsed step matrix kept alongside those local copies.

## Runs measured

| Run | Revision | Event | Result | Wall time |
|-----|----------|-------|--------|-----------|
| 35203768046 (canonical) | `020d1d20` | workflow_dispatch | success | 175.2 min (09:11:34 → 12:06:46) |
| 35172409514 | `bc2b65a` | workflow_dispatch | success | 206.5 min (01:55:25 → 05:21:55) |
| 35121352783 | `b8450f1` | workflow_dispatch | success | 299.6 min (16:21:19 → 21:20:56) |
| 35082429369 | `62d1a435` | workflow_dispatch | cancelled | 180.8 min (09:58:45 → 12:59:31); cancelled during step 24 after 2 291 s |

All four runs executed the same 26 main steps (31 job steps including post-steps) in the
`ingest-and-validate` job.

## Model size and artifact volume (canonical run)

| Quantity | Value | Source |
|----------|-------|--------|
| Documents | 62 | Syside export step output |
| Elements | 82 102 | export step output; identical in all import/validation outputs |
| Internal references | 291 704 | baseline import validation output |
| External references | 33 022 | Syside export step output |
| Ontology summary (import) | ambiguous 0, external 4, mapped 40, native 15, unresolved 0 | baseline import validation output |
| Full-model export JSON | 67 061 549 B (64.0 MiB) | retained artifact |
| Candidate export JSON (each) | 67 061 549 B; both candidates byte-identical (`sha256 6de3e8f5…`) | retained artifact |
| Semantic validation JSON | 11 343 709 B | retained artifact |
| API service log (trimmed) | exactly 100 000 000 B — hit the trim cap | retained artifact |
| Uploaded evidence artifact | 41 934 299 B compressed | `gh api` artifact metadata |
| Peak RSS | **unavailable** — no RSS was captured in run logs or artifacts | — |

## Exact per-step durations (seconds)

Columns are the four measured runs. `62d1a435` is the cancelled run (step 24 killed).

| # | Step | 020d1d20 | bc2b65a | b8450f1 | 62d1a435† |
|---|------|---------:|--------:|--------:|----------:|
| 1 | Set up job | 2 | 2 | 1 | 2 |
| 2 | Initialize containers | 23 | 28 | 25 | 22 |
| 3 | Run actions/checkout@v4 | 3 | 4 | 3 | 3 |
| 4 | Validate exact-revision checkout | 0 | 0 | 0 | 0 |
| 5 | Run actions/setup-python@v5 | 1 | 0 | 0 | 1 |
| 6 | Run actions/setup-java@v4 | 0 | 0 | 0 | 0 |
| 7 | Install Sysand and pinned model dependencies | 5 | 5 | 4 | 2 |
| 8 | Install official Syside Automator serializer | 6 | 7 | 7 | 9 |
| 9 | Export reviewed baseline with Syside | 6 | 6 | 6 | 6 |
| 10 | Build pinned Systems Modeling API service | 199 | 218 | 185 | 170 |
| 11 | Start pinned Systems Modeling API service | 57 | 76 | 70 | 67 |
| 12 | Import and validate exact API revision | 1260 | 1419 | 1977 | 1457 |
| 13 | Exercise three production semantic concerns | 430 | 501 | 695 | 504 |
| 14 | Validate governed product-line scope (API identity) | 417 | 487 | 672 | 489 |
| 15 | Exercise read-only semantic MCP tools | 854 | 989 | 1380 | 988 |
| 16 | Produce isolated candidate export (txn 1) | 7 | 11 | 9 | 9 |
| 17 | Produce 2nd independent serialization (MC-14) | 4 | 6 | 7 | 6 |
| 18 | Import candidate transaction 1 into a distinct API project | 1173 | 1329 | 1882 | 1383 |
| 19 | Import candidate txn 2 into 2nd distinct project | 1206 | 1378 | 1937 | 1396 |
| 20 | MC-14 correspondence across two txns | 851 | 993 | 1410 | 1000 |
| 21 | Verify pilot read-back against candidate transaction 1 | 430 | 511 | 708 | 513 |
| 22 | Run production-ingestion tests | 5 | 6 | 6 | 7 |
| 23 | Build O3 candidate bundle + VerificationCase grounding | 427 | 502 | 704 | 505 |
| 24 | Run same-revision O3 runtime equivalence | 3130 | 3897 | 6276 | 2291 (cancelled) |
| 25 | Trim API service log for upload | 0 | 0 | 1 | 0 |
| 26 | Upload exact-head ingestion evidence | 6 | 5 | 5 | 7 |

† cancelled mid-step; the sum for 62d1a435 excludes the killed remainder.

Stage buckets, canonical run (sum of steps 1–26 = 10 502 s = 175.0 min):

| Bucket | Seconds | Share |
|--------|--------:|------:|
| Setup + service build/start (1–11) | 302 | 2.9% |
| Baseline import + validators (12–15) | 2 961 | 28.2% |
| Candidate serialization (16–17) | 11 | 0.1% |
| Candidate imports + MC-14 + pilot (18–21) | 3 660 | 34.9% |
| Tests + O3 bundle (22–23) | 432 | 4.1% |
| O3 equivalence compare (24) | 3 130 | 29.8% |
| Trim + upload (25–26) | 6 | 0.1% |

## Substage timing: mostly unavailable from logs

Step-level times are exact. **Substage times are unavailable** because the scripts emit no
timing markers; the following could not be recovered and must be instrumented to be measured:

- Baseline import (step 12): split between JSON encoding, HTTP upload, server-side commit
  processing, database writes, response serialization — import steps print nothing until the end.
- Complete read-back (inside steps 12, 18, 19, 21): page size, page count, server latency,
  transfer volume, Python decode cost — no markers.
- Reference validation (inside steps 12/18/19): recursive-walker costs over the
  291 704 internal references — no markers.
- API service log: **zero timestamps** (pure Hibernate SQL, 175 840 `Hibernate:` lines);
  no request-level timing recoverable from it.
- O3 step 24: the equivalence report artifact is timestamped `11:21:33Z` while the step ran
  11:14:25 → 12:06:35 (3 130 s); the post-report remainder (~45 min) has no finer markers,
  so the internal sweep split is only indirectly bounded, not measured.

Indirect DB-pressure evidence (canonical run, from the Postgres service log): checkpoints
during the step-12 window — 09:16:50→09:21:20 (6 224 buffers, 38.0%) and
09:21:50→09:26:20 (8 123 buffers, 49.6%), consistent with heavy database write load during
baseline import.

## Bottlenecks (canonical run, ranked)

1. **Step 24 — O3 runtime equivalence: 3 130 s (52.2 min, 29.8%)**, and 3 897–6 276 s in the
   other runs. Single largest cost. Prior read-only investigation of the cost model:
   `de4sdv/semantic/traversal.py` `traverse()` rebuilds the full ~82k-element by-id index and
   full-scans the element corpus **per subject**; the canonical sweep covers 1 137 subjects
   (70 + 70 + 333 + 578 + 86) plus a 140-row K-comparison matrix. This suggests structural O(N·S)
   repetition; its share of this step is **not measured**. HTTP read-back and
   repeated subprocess invocation also need attribution before changing traversal. O3 equivalence-scope/bundle semantics are **forbidden to modify** under the
   parallel-work safety boundary; any fix must stay inside traversal/runtime code and prove
   equivalence parity.
2. **Steps 18+19 — the two candidate imports: 2 379 s (39.7 min, 22.6%)** combined;
   1 173/1 206 s canonical, up to 1 882/1 937 s in the slowest run. These are full baseline-size
   imports into two separate API projects and currently run sequentially.
3. **Step 12 — baseline import + complete validation: 1 260 s (21.0 min, 12.0%)**; 1 419–1 977 s
   across runs.
4. **Step 15 — semantic MCP tools: 854 s (8.1%)**, steps 13+14: 847 s, step 20: 851 s,
   step 21: 430 s, step 23: 427 s — all full-corpus validators/read-backs, individually
   7–14 min.
5. Setup + API build/start is only 302 s (5.0 min total); Syside export is 6 s in every run.
   Toolchain/setup work is **not** the bottleneck at current model size.

## Investigation classes A–I — classifications

Classification of each investigation class from the original task, using only the collected
evidence. “Measured” = backed by the runs above; “unavailable” = no marker/metric exists yet.

| Class | Subject | Classification |
|-------|---------|----------------|
| A | API Services build caching | **Measured, small win available.** Step 10 = 170–218 s per run (185 s in the slowest run, 199 s canonical) for the pinned JVM/SBT `stage` build; SBT packaging completes ~3.3 min into the run. A content-addressed exact-key cache or pinned prebuilt image has a theoretical upper bound of the measured build duration (not a measured saving); key must cover everything affecting the binary (never silently stale). Not implemented in baseline. |
| B | Sysand/tool dependency caching | **Measured, marginal.** Steps 7+8 total 11 s canonical (worst 12 s). Any cache still needs provenance/integrity verification and saves at most seconds; low priority. |
| C | Export efficiency | **Measured, not a bottleneck.** Step 9 = 6 s in all four runs; output 62 documents / 82 102 elements / 33 022 external refs / 67 061 549 B. Deep CPU/memory profiling of the exporter was not completed in this evidence set; no measurement justifies changes. |
| D | Candidate serialization | **Measured, negligible cost, required repetition.** Steps 16+17 = 11 s canonical (worst 18 s). MC-14 requires two genuinely independent serializer transactions; sharing checkout/dependencies can only save seconds, and the cost of a concurrency/independence mistake exceeds the measured benefit. |
| E | API import throughput | **Measured as dominant cost; substage split unavailable.** Step 12 = 1 260–1 977 s; candidate imports = 1 173–1 937 s each. No split available between JSON encoding / HTTP upload / server commit / DB writes / response; instrument first. Postgres checkpoints (6 224 / 8 123 buffers at ~38–50% during the import window) indicate real DB write pressure. Do not bypass the standard API/database model. |
| F | Complete API read-back | **Unavailable (unquantified), must stay complete.** Read-back is embedded in steps 12/18/19/21; page size/page count/latency/volume are not logged. Sampling is explicitly forbidden; only standards-supported page-size/query changes with exact verification may be considered after measurement. |
| G | Reference validation efficiency | **Unavailable (unquantified), exact semantics required.** 291 704 internal references validated inside steps 12/18/19; recursive walker costs not instrumented. No probabilistic validation permitted. |
| H | Duplicate candidate imports | **Measured, largest repeatable chunk, concurrency candidate not yet proven.** Steps 18+19 = 39.7 min canonical (up to 63.7 min combined in the slowest run), sequential. Separate project/commit identities are contract-required; concurrency is only acceptable if measured benefit exists and independence remains clear — not implemented, not benchmarked. |
| I | Snapshot acceleration | **Not wired; no policy changes.** Snapshot machinery exists (`de4sdv/semantic/snapshot.py`, `scripts/run_snapshot_parity.py` — a local Lane-D tool with timing/RSS instrumentation), but the privileged workflow has **no snapshot step** and does not invoke it. Per constraints, if snapshot reuse requires changing governing semantics or evidence policy, it must stop and be reported rather than implemented — that is the current status. Any future use requires a provenance-validated reuse key (source manifest, pinned deps, Syside version, serializer digest, options, ontology/kernel inputs, API Services revision where applicable) with stale/corrupt-cache rejection tests. |

Additional cross-cutting finding: the O3 sweep’s per-subject full-corpus index rebuild
(see Bottlenecks #1) is **accidental algorithmic repetition** inside a step whose
evidence semantics must not change; fixing it is code-level (traversal/runtime), not
policy-level.

## Required repetition vs caching / concurrency

Classification per the task’s Phase-4 categories:

| Operation (steps) | Classification |
|-------------------|----------------|
| Exact-revision checkout + validation (3–4) | Required every run; cheap (3 s); no change |
| Syside licensed export (9) | Required every run; cheap (6 s); must stay official serializer |
| Baseline import + full read-back + identity/reference/ontology validation (12) | Required every run; dominant cost; cacheable only via validated snapshot (I), otherwise instrumentation-led |
| Semantic-query / PLE-scope / MCP validators (13–15) | Required every run; full-corpus; 1 701 s combined in the canonical run; no reduction without semantics-preserving rework |
| Two independent serializer transactions (16–17) | **Required every run (MC-14)**; cannot collapse to one serialization imported twice; cost already negligible |
| Candidate imports into distinct projects (18–19) | Required every run (separate project/commit identities); **suitable for concurrency** only with measured benefit and clear independence — unproven |
| MC-14 correspondence + pilot read-back (20–21) | Required every run; full-corpus comparisons |
| Production-ingestion tests (22) | Required every run; 5–7 s |
| O3 bundle + equivalence (23–24) | Required for evidence/O3 closure; biggest cost; **nightly health vs release/evidence separation is a policy question** — must be explicitly proposed/tested, never silently weakened |
| API Services build + dependency installs (7, 8, 10) | Required only when pinned inputs change; **suitable for exact-key caching** (A, B) |
| Snapshot reuse (I) | Suitable for validated caching only after parity proof; **not wired, no policy change** |

Accidental duplication confirmed in import code: `import_baseline()` performs a complete
API read-back, then `run_import()` fetches the same immutable project/commit again for
ontology validation. The implementation reuses the first verified API values within that
transaction, never the export. The two serializations and two candidate imports remain
contract-required. Traversal/index optimization is a separate follow-up pending attribution;
no O3 scope, bundle, or equivalence semantics are changed here.

## Workflow cap and nightly schedule

- Cap history (verified via `git log -L 38,38`): 45 → 75 → 180 → **300** (`b8450f1`, #260)
  → **360** (`bc2b65a`, #261). Current `timeout-minutes: 360`.
- Run `35121352783` finished at 299.6 min, i.e. it consumed the entire 300-min cap that was
  in effect then; the cap was raised again partly because of that pressure.
- Nightly schedule: `cron "30 2 * * *"` is declared, but the job condition is
  `if: github.event_name == 'workflow_dispatch' || github.event.pull_request.head.repo.full_name == github.repository`.
  For `schedule` events neither clause holds (no PR context), so **scheduled nightly runs are
  skipped** — observed in the run list (`35319989917` schedule completed/skipped, `35196985870`
  schedule completed/skipped, and older schedule runs likewise). Nightly ingestion has not
  actually been executing.

## What remains unavailable / not claimed

- **End-to-end after-timing: unavailable.** No optimized workflow run exists; this report
  contains local replay measurements only, not a privileged end-to-end comparison.
- Historical privileged peak RSS, pagination counts, and per-substage import splits remain
  unavailable. The changed pipeline now captures those metrics for the next run.
- All A–I changes above are classifications/opportunities only; none is implemented in the
  baseline, and none may alter exact-SHA binding, licensed Syside export authority, UUID
  preservation, complete read-back, MC-14 independence, or O3 exact-revision evidence.

## Implemented change and local replay

`import_baseline()` returns its verified API read-back for the newly created immutable
project/commit. `run_import()` passes those values directly to ontology validation instead
of issuing a second full HTTP listing. No cross-run cache, snapshot, export substitution,
or change to serialization, project isolation, kernel binding construction, or O3 meaning
is involved. Missing/duplicate read-back identities now fail closed explicitly rather than
being silently collapsed by dictionary construction. Required internal-reference preservation
uses the original comparison unchanged (the server may expose additional derived references).

Reproduce with `python scripts/benchmark_ingestion_readback.py --export <retained-export>
--repeat 3 --out-dir <results-directory>` (one shell command). The benchmark runs each mode
in a fresh process against a loopback HTTP fixture with the retained full corpus and no
injected delay. It does **not** model JVM/database cost. “Before” releases the first parsed
read-back before the second fetch, matching the original lifetime. An earlier experiment
retained both and overstated RSS savings; it is superseded and not acceptance evidence.

| Local replay metric (three runs per mode) | Before | After |
|---|---:|---:|
| Mean measured wall time, including parity hashing | 17.793 s | 16.363 s |
| Complete HTTP listing requests | 905 | 822 |
| GET response body bytes | 69,163,136 | 34,581,568 |
| Mean process peak RSS | 480.95 MiB | 480.81 MiB |

There is **no material peak-memory improvement** in the corrected measurement. The useful
result is elimination of one complete transfer per import, with identical UUID, internal
reference-path, complete content, and ontology-result digests across all six replay runs.
The ontology result remains 40 mapped, 15 native, 4 external, no ambiguous/unresolved entries.
See [machine-readable replay results](readback-replay-summary.json) for counts and digests.
This does not prove production API representation or privileged end-to-end parity; that
requires the exact-head privileged run. The latest historical run and this branch also
have different source revisions, so their total durations are not a controlled A/B test.

No binary/tool/snapshot cache is introduced: setup is a small measured contributor, and
complete reproducible binary identity for upstream transitive dependencies was not proven.
No cache invalidation claim is made and cache mutation tests are therefore inapplicable.
No concurrency or page-size change is introduced without live throughput evidence. Candidate
transaction 2 already shares the detached checkout and skips dependency sync while still
launching a fresh serializer process. The three imports remain separate and sequential.

Instrumentation writes to `DE4SDV_INGESTION_TIMINGS` outside the evidence payloads. It records
monotonic elapsed time, process-lifetime peak RSS, JSON request/response bytes, page and
element counts, model loading, document serialization/decoding, normalization, candidate
checkout/sync, required-reference comparison, and ontology validation. Nested measurements
overlap: do not sum them. HTTP exchange time combines upload, server/database work and
response transfer; client timings cannot honestly separate those components.
