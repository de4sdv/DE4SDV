# Deployment plane — what a production SDV does, and what this testbed does

Status: **analysis, not a compliance claim.** Nothing here says the testbed is
certifiable, and none of it may be quoted as evidence for R155/R156, ISO 21434 or
ISO 26262. It records where the deployment mechanics stand.

The E/E architecture in this directory is credible: zonal topology, slice
isolation, a per-frame gateway policy, a DBC ↔ VSS signal contract, and an ECU
answering UDS across the routed path. The **deployment plane** around it is a lab
harness. Those are different claims and the second one is the gap.

vxedge makes no secret of this. Its own architecture document calls it a
research-grade orchestration platform, and its control plane is a Unix socket with
filesystem permissions — no peer-credential check exists in the code yet. Using it
does not make a deployment production-like; it makes it reproducible.

## Where the deployment descriptor lives

`vehicle/vehicle.yaml` and `vehicle/parts.yaml` are the composition and the software
baseline, copied verbatim from the testbed that produced the gate results. Until
this directory existed, the descriptor lived only on the VM, so the vehicle could
not be rebuilt from the repository at all. The split is the same one a production
program uses: structure is one document, software is another, and an update campaign
changes the second without touching the first.

## The gap, by deployment concern

| Concern | Production practice | Here | Evidence |
|---|---|---|---|
| Artifact identity | Images referenced by digest and signed; admission refuses anything else | Our own images are referenced by **local tag** (`localhost/de4sdv/zone-ecu:9`) and are unsigned | `vehicle/parts.yaml` |
| Dependency locking | A lockfile pins every reference; builds and deployments use it | `vxp.lock` was never generated; every `vehicle up` ran with **`--unlocked`** | run history |
| Admission policy | A trust policy names who may sign what; unsigned parts are refused | No `/etc/vxedge/trust.yaml` existed, which vxedge documents as "any package runs" | vxedge §6.0.8 |
| Updates (UCM / SUMS) | Signed update packages, A/B banks, rollback, campaign management, software identified per RxSWIN | The `vxota` service starts, and **no update was ever applied**. No A/B, no rollback, no campaign | vehicle.yaml `services.ota` |
| Health & fault management | Supervised process tree with machine states, watchdogs, DTCs, degraded modes | `tini` plus an `alive()` loop; the provider now restarts if the broker drops | `zones/entrypoint.sh` |
| Resource isolation | CPU/memory partitioning per ECU, QoS, hypervisor separation | The schema supports `resources: {cpu, memory}` per device; **none is declared**. Containers share the host kernel | `vehicle/vehicle.yaml` |
| Identity & access | Per-caller identity, IAM, audit of who changed what | Socket permissions only; vxedge's audit record carries no caller identity | vxedge §5.3 |
| Observability | DLT or structured logs, metrics, fault memory, traces | stdout piped through `sed` for a prefix; vxtelemetry exists and was never used | zone logs |
| Safety partition | ASIL decomposition, memory protection, separated execution | None. The schema takes `asil:` on a function; our functions declare nothing | `vehicle/vehicle.yaml` |

Two of those are not vxedge's fault and are squarely ours: **no digest or signature
on our own images**, and **no declared resource limits**. Both are one-line changes
in the descriptor that were simply never made.

## What this testbed can and cannot support

Supported by measurements in this directory: zonal topology, slice isolation under
impairment, per-frame gateway routing, DBC ↔ VSS both directions, an OpenBSW ECU
with an independent lifecycle answering UDS through the router, and hop latencies
with sample counts.

Not supported by anything here: secure boot, signed artifacts, update safety or
rollback, resource partitioning, fault-tolerant supervision, timing guarantees, or
any certification statement. A single host with virtual buses and one userspace
router cannot carry those claims.

## Single host, by construction

The daemon listens on `unix://` only — "TCP+mTLS arrives with the auth work" — so
no second host can join a vehicle, and `network.time_sync` cannot span hosts: its
follower reads the host clock and only measures the path. That is a platform
boundary, not a configuration to find. [`time-sync.md`](time-sync.md) measures what
a cross-host claim would cost (0.198 ms just after boot, 44 µs in steady state)
and what it would need.

## What has been closed since

Items 1–4 of the list below are done and proven on the testbed. The two that
changed what the host enforces:

- **The vehicle is a locked, signed `vxp/1` package.** `vehicle/vxp.lock` pins the
  five files; `vxedge pkg pack` produces `sha256:3886296e…`; the package is signed
  with a host-local cosign key and verified, which writes a record keyed by that
  digest.
- **The host requires signatures.** `/etc/vxedge/trust.yaml` carries
  `require_signed: true` and the lab public key. A package whose files changed
  without a new lock is refused as `LOCK_MISMATCH`; one that was changed, re-locked
  and never signed is refused as `SIGNATURE_INVALID`. Both refused before anything
  was provisioned.
- **The daemon runs as a systemd user unit** with `Restart=on-failure` and linger,
  and after a restart it reconciled the gateway (`state=3`, 4/4 endpoints) with the
  policy still loaded.

Closed since this page was written:

- **Images are pinned by digest.** A registry on the host (`127.0.0.1:5000`) holds
  both: `localhost:5000/de4sdv/zone-ecu@sha256:7d2a051e…` and `…/can-gw@sha256:1a85cad1…`.
  Proven twice over: moving the tag to a different image left the running digest
  unchanged, and deleting the local refs made the converge pull them back.
- **The registry is no longer a lab fixture in the ways that mattered.** It runs TLS
  with a private CA and htpasswd auth — unauthenticated `GET /v2/` is 401,
  authenticated is 200 — and the digests did not change when the transport did. What
  remains operator-owned is the CA and the credential, which is where they belong.
- **An update can be applied, rejected and rolled back.** Two signed packages name
  the same vehicle: A (`sha256:4f801214…`) runs, B (`sha256:fb741dae…`) dies on a
  missing DBC. The orchestrator reports both as `up`, so the gate that catches B is
  ours — `checks/update_with_rollback.sh` probes the zone's own status frame, fails
  the candidate, re-applies A, and confirms the zone publishes again (exit 2).
- **The update travels over the air.** The artifact and its signature are published
  into the `vxota` store, fetched from inside a zone over the adas slice
  (`11 776` and `387` bytes, both digest-checked against `targets.json`), verified
  against the host key, and unpacked to the same digest that was published.
- **Both images have an SBOM.** CycloneDX 1.7 via `syft`, committed gzipped —
  5 427 components for the zone image, 3 474 for the gateway — regenerated by
  `checks/make_sbom.sh`.
- **The daemon exports metrics.** `/metrics` on `127.0.0.1:9469` answers 200 with
  per-entity CPU and memory; nothing scrapes it, but the surface is there.

Still open, with the reason each way:

- **`resources:` is declarative only.** The descriptor declares per-device CPU and
  memory and vxedge validates it, but nothing in 0.30.0 applies it: `podman inspect`
  reports `CpuQuota=0 Memory=0` on every payload and infra container, and the
  `Resources` struct has no consumer outside the model. Upstream defect; declared
  anyway, because it is the right document, and the claim is not made.
- **No post-start health gate upstream.** Ours exists and is what the rollback runs
  on; the orchestrator still reports `succeeded` for a dead zone. Upstream defect.
- **No control-plane identity.** vxedge's own documentation states the socket has
  filesystem permissions but no peer-credential check, and audit records carry no
  caller. Documented upstream gap, not ours to patch.
- **No A/B banks, no automatic revert inside an ECU update manager.** The revert here
  is an orchestrated converge of the previous package. That is architectural, not a
  missing script.
- **No ASIL partition or safety argument.** A single-host testbed with a shared
  kernel cannot carry one, and nothing here claims it.

Both upstream defects are drafted in
[`upstream-reports/`](upstream-reports/README.md) — written, not filed.

The runbook for all of it is [`deploy/README.md`](deploy/README.md).

## The gap, ranked, as originally found

1. **Lock the baseline** (`vxedge pkg lock`) and stop passing `--unlocked`. Minutes.
2. **Digest-pin our own images** in `parts.yaml`, then sign them and add a trust
   policy so an unsigned part is refused. This proves the admission path exists
   rather than asserting it does.
3. **Declare `resources:` per device.** The schema already supports it.
4. **Run the daemon under systemd** instead of a detached process, so it survives a
   reboot and restarts on failure.
5. **An OTA campaign with a forced rollback.** Ship one zone image update through
   `vxota`, let it apply, then make the new image fail and roll back to the previous
   baseline. This is the only item on the list that changes what the project can
   say about update management — and it is the one an automotive reviewer will ask
   for first.
6. **An SBOM per image**, attached where the images are published.

Items 1–4 are one session's work and mostly descriptor edits. Item 5 is a real
increment with a scope of its own.

## What to adopt rather than invent

- **Update and lifecycle semantics**: AUTOSAR Adaptive's UCM/PHM/State Management, or
  the equivalent from Eclipse S-CORE, rather than a bespoke updater.
- **Supply chain**: digest + signature + policy, the pattern every container
  ecosystem already converged on; there is nothing to design here.
- **Compliance**: R155/R156 are process obligations with evidence trails, not
  features to implement in a testbed. When the project makes such a claim it needs
  the trail, not a script that passed.
