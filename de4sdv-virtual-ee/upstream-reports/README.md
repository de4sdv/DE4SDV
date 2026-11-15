# Upstream observations — local notes only

Three observations from the pinned testbed build. These are local working notes,
not reviewed issue text, commitments, or evidence of an upstream defect on the
current default branch. Declared limitations and unimplemented fields need to be
distinguished from broken promises before any report is proposed. No upstream
contact or contribution is part of this change.

## 1. vxedge: `resources:` is validated but never applied

**What the schema promises.** A device may declare `resources: { cpu, memory }`
(`vehicle.yaml`, and the scaffold uses it: `hpc1: { …, resources: { cpu: 4, memory: 8 } }`).
`vxedge` parses it into `model::Resources { cpu, memory_gb, gpu }` and validates it.

**What happens.** Nothing applies it. With `zone-fl: { resources: { cpu: 1, memory: 2 } }`
in the manifest and the vehicle up:

```text
vx-zone-fl-payload   CpuQuota=0            Memory=0
vx-zone-fl-infra     CpuQuota=0 NanoCpus=0 Memory=0
```

In the 0.30.0 source, `Resources` has no consumer outside `model/`: no container
backend reads `cpu` or `memory_gb` to set `--cpus`/`--memory`, and no VM backend
reads them to size a domain.

**Why it matters.** A declared limit that is silently dropped is worse than no field:
the descriptor looks like it partitions resources, and a node that escapes its
ceiling takes the rest of the vehicle with it.

**Possible report, not sent:** schema and backend disagree; either apply it on the container
backend or refuse the block with a typed error.

## 2. vxedge: `up` has no post-start health gate

**What happens.** A package whose payload dies on start still converges:

```text
[100%] experiment.up experiment `de4sdv-virtual-ee` up — … 3 zone(s) …
experiment.up: succeeded
```

while the rear zone's process tree was already gone:

```text
[provider] FileNotFoundError: … /opt/zone/dbc/wiper-v2.dbc
[zone] a child exited; taking the zone down
podman inspect … status=exited exit=0
```

**Why it matters.** The orchestrator's own status is the only signal a deployment can
act on. If `up` reports success for a dead zone, an update has no failure to roll
back from, and a monitoring system built on vxAPI sees a healthy vehicle.

**What the testbed does about it.** `checks/update_with_rollback.sh` probes the zone's
own status frame and reverts. That is a workaround at the caller, not a fix.

**Possible report, not sent:** a staged converge could verify each node is running before the job
reports success — at minimum, a node whose container exits during `up` should fail
the converge with a typed reason rather than report `succeeded`.

## 3. vxedge: two more model fields that read like constraints and are not

`resources:` (report 1) is not the only one. Two more fields are parsed, validated
and then never consumed by a plan:

- **`channels:`** — `Channel { id, from, to, protocol, qos, carried_by }`, where
  `protocol` is one of `Dds | SomeIp | Zenoh | Can | Udp | Tcp` and `qos` carries
  `deadline_ms`, `reliability` and `rate_hz`. `carried_by` is validated against the
  links, which reads as a reachability check. In 0.30.0 the field appears only in
  `model/`, `entities.rs` (listing) and `workspace.rs` (inventory); no provisioning
  code reads it. Declaring a SOME/IP channel with a 10 ms deadline changes nothing
  about the run.
- **`asil:`** on a function — present in the workspace model and never used
  downstream.

**Why it matters.** The same reason as `resources`: a descriptor that a reader takes
as a constraint silently becomes decoration, and a measurement attributed to "the
channel's QoS" is then attributed to nothing. The `carried_by` validation makes this
worse rather than better, because a checked reference suggests the rest is checked
too.

**Possible report, not sent:** either implement the three fields or reject them at load with a
typed error — a manifest that declares a deadline should not load silently when no
backend will honour it.

## What is not drafted here

- **No control-plane identity.** vxedge's own documentation states that its Unix
  socket has filesystem permissions but no peer-credential check, and that audit
  records carry no caller identity. That is a known, documented gap, not a new one —
  reporting it would be noise.
- **`vxota-probe` missing from the release tarball.** The crate is in the upstream
  repository, but the 0.30.0 install ships only `vxota`. Worth mentioning in a
  release note rather than filing a defect; the fetch path was exercised with a
  plain HTTP client and content addressing.
- **`vxota publish --signing-key` help says "hex-encoded … seed" while the argument
  is a file path.** One-line documentation fix; the error is `Os { code: 2 }` with no
  hint, which cost a debugging cycle. Worth a doc issue.
