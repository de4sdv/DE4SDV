# Acceptance record — repaired virtual E/E, 2026-11-15

**Verdict: NOT ACCEPTED.** The demo and service plane passed three consecutive
runs on the repaired images, and the signed-package accept/rollback/foreign-refusal
chain passed. The routed failure matrix did not: one repetition ran, link-loss
recovery failed, and teardown left two gateway ports behind. The matrix is
incomplete and its failure is retained, not averaged away.

## Executed identity

| item | value |
|---|---|
| executed source | `d6190a889253beb736abad45554d668991f5588a` |
| code under review | `5a7d2fa793edab14d781b8b5ff1681387564a4d6` (same code; adds the two SBOM guard tests) |
| source tree | `4fd601ddc139300614d210a5ca3059f41ee0007a` |
| scope tree | `2bebbbbd017757500197d1daf60861b04c7f5449` |
| `zone-ecu` | `localhost:5000/de4sdv/zone-ecu@sha256:d51b87895690d7bca6bd6fb5d519b66e8b4d64f1b8c34836000e4aefaf2b0e14` (config `42ff989956a68588594845e01a61ace6c21cdb18701c89f02d2ddd39d379e81f`) |
| `can-gw` | `localhost:5000/de4sdv/can-gw@sha256:b7ed54a23abeb0dec5a5a257c5953ae1bd2a34f25061b526be3cb21abdff45b0` (config `efaa34d9ffb8f85ba69551479e7f1eade883b1ccfa150f68c4b26c076b3bc68c`) |
| package | signed `de4sdv-virtual-ee-0.1.0.vxp`, digest `sha256:a1e6c7238f943c838794ac4708b87eea07e7c56b018fae1e99f0d0defab33705`, signer `sha256:5a2e2d2b71c9f9ef3119e75b48e18bbf2940b90cbce694cda28e327e965909ae` |

The images were built from `f7fd7a8f26ce432329ee353b731aad785becab3f`. All 17
runtime-affecting input files at the executed commit have the same SHA-256 as the
build inputs; the two commits differ only in tests and generated image pins. Every
run below re-verified the same source before and after (`identity-after.json`,
`differences: []`), and each payload was inspected live: `ImageName` carried the
locked digest above and `Image`/config ID matched the built image.

## Passed

### CAN demo — three runs

| run | verdict | transitions | leaks | routed status | diagnostic | pcap |
|---|---|---:|---|---|---|---|
| `20261115T174918Z-d6190a889253` | pass | 12/12 | 0 / 0 | 648 front→rear, 649 rear→front | `0x7E0` 1, `0x7E8` 1 | present |
| `20261115T175052Z-d6190a889253` | pass | 12/12 | 0 / 0 | 648 / 649 | 1 / 1 | present |
| `20261115T175227Z-d6190a889253` | pass | 12/12 | 0 / 0 | 648 / 648 | 1 / 1 | present |

Each run primed both plants, drove eight transitions per function, captured four
buses plus the bridge datagrams, and judged every declared transition, both routed
directions, both denied directions and the UDS request/response by payload. The
archive identity check (`check-archive --repo`) passed for each.

### SOME/IP service plane — three runs

| run | method n | method median | events received | missing in span | deadline / period misses |
|---|---:|---:|---:|---:|---:|
| `…T175402Z…-backbone` | 69 | 0.317 ms | 340 | 0 | 0 / 0 |
| `…T175458Z…-backbone` | 69 | 0.317 ms | 342 | 0 | 0 / 0 |
| `…T175554Z…-backbone` | 69 | 0.367 ms | 341 | 0 | 0 / 0 |

One host, one kernel clock. These are functional numbers, not production Ethernet.

### Signed-package deployment — `20261115T180159Z-d6190a889253-rollback`

| case | exit | observed |
|---|---:|---|
| healthy package accepted | 0 | fresh container `ced4de29…`, `ImageName` = locked zone digest, its own `0x281` frame in 0.42 s |
| broken candidate (`ZONE_DBC` names an absent file) | 2 | candidate `4856bed1…` never running; fallback `70a4a62f…` healthy in 0.35 s |
| foreign workspace active | 3 | `ERROR_REASON_WRONG_WORKSPACE` for both up attempts; container ID unchanged `fb3c600e…`; **0** `podman exec` calls |

## Failed

### Routed failure matrix — one repetition only

`20261115T175901Z-d6190a889253-gate2`, executed source above, 60 records
(50 command, 10 isolation), all 10 expected isolation pairs present, **0**
forbidden command frames in every capture, routed status present in every capture.

| scenario | result |
|---|---|
| baseline | 12/12 converged, both isolation records clean |
| impairment (20 ms ± 5 ms, 1 % loss) | 12/12 converged, clean |
| concurrency | 12/12 converged, clean |
| restart | down-record correctly did not converge; six up-records converged at KUKSA **with `cmd_seen=false`** (the pre-restart tap had ended, so bus frames were not observable); clean |
| link-loss | down-record correctly did not converge; **3 of 6 up-records did not converge** (`idx` 0, 2, 4 — every `true` transition); exit 1 |

The link-loss failure is a real recovery finding, not a missing-capture verdict:
the client wrote the target and read the value back unchanged, while every `false`
transition converged. Repetitions 2 and 3 did not run.

### Teardown after the failed matrix

`vxedge experiment down` exited 1: `vz-hpc1` and `vz-zone-fl` still existed 5 s
after their namespaces were removed. The vehicle was left partially torn down.
This is a teardown defect (or a namespace holder), and it blocked a clean restart
of the matrix on the same VM inside the approved window.

## Retained evidence

The raw archives are committed as deterministic tarballs beside this record, so
their text logs keep their exact bytes (including trailing whitespace) without
polluting the repository diff:

| archive | sha256 |
|---|---|
| `results/20261115T174918Z-d6190a889253.tar.gz` | `b6585829077cac5d06e2829525dd29b7e317b7abba52ddd5c207fb2389830597` |
| `results/20261115T175402Z-d6190a889253-backbone.tar.gz` | `36f65b17c994caf31e51731cb46701e9774347daf156bc1b30a0820e28ce7810` |
| `results/20261115T175901Z-d6190a889253-gate2.tar.gz` | `df166d3f85262deee3ee555cb78cff967da7b83ca69bd0359d010479477cb77e` |
| `results/20261115T180159Z-d6190a889253-rollback.tar.gz` | `2b63941badd96aae7c48745599c48ca7a40611d74e6d12b0b1af78e96a9a7325` |

Extract a tarball under `de4sdv-virtual-ee/results/` and run
`python3 checks/run_identity.py check-archive --repo de4sdv-virtual-ee <dir>`
to reproduce the identity result. The second and third demo/backbone runs are
not committed: their summaries are quoted above and their full archives are
held with the maintainer. A missing archive never counts as a pass.

The run identity binds committed inputs, native image identities and archive
metadata. It does not sign or attest execution, and it does not prove that the
results were produced by those inputs: anyone with Git access can build a
coherent archive at a commit.

## Not run / not claimed

- Repetitions 2–3 of the five-scenario matrix (the VM stopped at its approved
  deadline; the failure above was preserved instead of retried).
- A restart capture that survives the restart boundary: the current tap is started
  before `podman start` and ends with the old container, so restart-up bus
  evidence is unavailable by construction. Say so rather than counting KUKSA
  convergence as bus evidence.
- Signed execution or attestation. The run identity binds committed inputs,
  native image identities and archive metadata; it does not prove the results were
  produced by those inputs, and anyone with Git access can build a valid archive.
- External UDS tool provenance beyond its recorded SHA-256.
- Public distribution, legal clearance, or any claim that the images are
  copyleft-free. `sbom/inventory.json` is inventory, not a licence verdict.
