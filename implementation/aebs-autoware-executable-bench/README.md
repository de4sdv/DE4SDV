# INC-AEBS-009A Autoware executable bench

This directory contains the runtime-verified INC-AEBS-009A headless Autoware
integration bench. On the target ARM64 Jetson, the selected pinned-source overlay
builds, the map-enabled chain launches, and the readiness collector receives live
typed messages from all locked 009A readiness endpoints, including the exact AEB diagnostic
identity.

009A does **not** execute a collision scenario or establish braking behavior.
The bounded follow-on ownership is:

- INC-AEBS-009B owns nominal moving-vehicle-target evidence;
- INC-AEBS-009C owns partial stationary-target native intervention-to-MRM/gate evidence;
- INC-AEBS-009D owns conscious driver override;
- INC-AEBS-009E owns non-activation and false-reaction scenarios;
- INC-AEBS-009F owns failed and degraded operation;
- INC-AEBS-009G owns pedestrian-target scenarios;
- INC-AEBS-009H owns bicycle-target scenarios; and
- INC-AEBS-009I owns source-backed quantified criteria.

## Proven 009A boundary

The verified composition includes:

- map loaders and map projection;
- simple planning simulator with typed initialization inputs;
- autonomous emergency braking node;
- diagnostic graph aggregator and converter;
- MRM handler and emergency-stop operator;
- selected legacy vehicle command gate;
- live typed readiness collection across map, simulator, diagnostics, MRM,
  emergency command, and gate output.

The fixture publishes only initialization inputs: initial pose, engage state,
API/system operation-mode state, Autoware driving state, nominal control/gear/
light commands, and an empty structured point cloud. It does not publish MRM
state, emergency commands, selected gate output, obstacles, or braking evidence.

## Reproduce

Run from this directory:

```bash
python ../../scripts/validate_aebs_executable_bench.py
python scripts/fetch_map.py --cache "${HOME}/.cache/de4sdv/autoware/maps"
python scripts/verify_container.py
scripts/prepare_workspace.sh
scripts/build.sh
scripts/smoke.sh
```

The image is pinned and checked by exact OCI index and ARM64 platform digests,
inspected as `linux/arm64`, and bound to the locked repository index through the
local image object's inspect-derived `RepoDigests`. All three source overlays
must match independently pinned commit and Git-tree IDs with a clean worktree.
Map extraction uses an exact member
allowlist after streaming SHA-256 verification; every extracted file is hashed
again immediately before launch. The selected overlay build uses one worker for
the 8 GiB ARM64 target.

The build selects exactly eight packages: six pinned Universe packages, pinned
`tier4_map_launch`, and the DE4SDV bench package. Dependencies outside the three
overlays come from the independently digest-pinned Autoware container underlay;
the three repositories are not a complete standalone Autoware source closure.

Sanitized machine-readable runtime JSON is retained under `evidence/`; verbose
logs remain ignored. Every retained document carries a canonical execution-
manifest digest covering the runtime lock, compose/DDS/repository manifests,
every runtime script, and the complete packaged ROS source/config/launch tree.
Repository validation recomputes that digest and rejects exact source, image,
map, build, launch, diagnostic-identity, locked-endpoint, or impossible receipt-
timing mismatches. Source commit/tree/cleanliness is rechecked immediately before
`colcon build`; receipt ages must be finite, non-negative, and within the pinned
collection window. A
successful strict smoke records:

- `built=true` in `build-status.json`;
- `launched=true` in `launch-status.json`;
- `ready=true` in `readiness.json`;
- exact diagnostic identity match;
- live typed receipt for every locked endpoint;
- `scenario_executed=false`.

## Configuration provenance

The package installs byte-matched runtime copies of the authoritative AEB and
diagnostic-graph controls because ROS package data cannot safely reference files
outside the package. Tests enforce equality with the authoritative controls.

Three map parameter files are exact pinned copies. The point-cloud loader file
has one explicit, lock-recorded override: partial loading is disabled because the
verified sample map contains no point-cloud metadata file.

The wrapper directly instantiates AEB, the emergency-stop operator, and the
legacy vehicle gate where pinned upstream wrappers have undeclared substitutions,
colliding generic launch arguments, or incomplete remaps. These deviations are
covered by regression tests and retain the pinned node implementations.

CycloneDDS uses repository-owned localhost unicast configuration. The bench does
not add `NET_ADMIN`, run privileged, or depend on multicast being enabled on
loopback.

## Non-claims

No stationary-target intervention, braking performance, safety acceptance,
compliance, certification, homologation, or production readiness is claimed.
The provisional diagnostic timeout and hysteresis values still require timing
and fault-injection review in later increments.
