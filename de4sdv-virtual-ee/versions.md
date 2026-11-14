# Virtual E/E testbed — component versions and licences

This file is the version record that [`UPSTREAM.md`](../UPSTREAM.md) points at for
the virtual E/E testbed. It is the single place a pin is written; the upstream
page links here instead of repeating a number, so the two cannot disagree.

Nothing here is vendored. Every component is either fetched as a prebuilt
release, built inside a container image from a pinned tag, or built from source
at a pinned commit. The repository contains no upstream source file.

| Component | Pin | Licence | How it enters the testbed | Used for |
|---|---|---|---|---|
| [vxedge](https://github.com/vxedge/vxedge) | `0.30.0` (release tarball, verified against the release `SHA256SUMS`) | Apache-2.0 | prebuilt binary, installed on the testbed host | gateway, slices, zones, services, signal plane |
| [KUKSA Databroker](https://github.com/eclipse-kuksa/kuksa-databroker) | `0.7.1` — `ghcr.io/eclipse-kuksa/kuksa-databroker@sha256:529d8c6d3cc223362667672978bcb8f92c4d356b25aedd336e7a2e004d7279bd` | Apache-2.0 | container image, digest-pinned, pulled by the vehicle manifest | signal plane (VSS broker) |
| [KUKSA CAN Provider](https://github.com/eclipse-kuksa/kuksa-can-provider) | `0.5.1` (git tag; the project publishes neither a PyPI package nor a registry image) | Apache-2.0 | cloned and run from source inside the zone image | DBC ↔ VSS bridge, both directions |
| [cannelloni](https://github.com/mguentner/cannelloni) | `v2.1.2` (git tag, built in a container builder stage) | **GPL-2.0** (`gpl-2.0.txt`; GitHub's detector reports none because the file is not named `LICENSE`) | built from source inside the zone and gateway images | SocketCAN-over-UDP transport between a zone and the gateway |
| [OpenBSW](https://github.com/eclipse-openbsw/openbsw) | commit `b9ad527` (`posix-freertos` preset) | Apache-2.0 | built from source on the testbed host | reference ECU: lifecycle, UDS over DoCAN |
| [SDV Simulation 5](https://github.com/nsengupta/sdv_simulation_5) | `ca0c733` — inspected, **not used** | Apache-2.0 | not built, not run | its private CMD/ACK/NACK codec was the thing this contract replaces |
| Ubuntu / GCP kernel | 24.04.5 LTS, `7.0.0-1017-gcp` | — | cloud image | host: `netem`/`htb`, `vcan`/`vxcan`, Open vSwitch |

## Licence consequences worth stating

- **cannelloni is GPL-2.0 and is the only copyleft component.** It runs as a
  separate process and is never linked into DE4SDV code, so DE4SDV's own sources
  stay Apache-2.0. But a *distributed* container image that bundles the compiled
  cannelloni binary would carry GPL-2.0 obligations (source availability and
  licence text). Nothing in this repository distributes that binary; the images
  are built locally from the recipe.
- **Everything else is Apache-2.0**, which is compatible with DE4SDV's licence,
  including running inside a distributed image with attribution.
- **Attribution lives in `UPSTREAM.md`**, one row per project, and in the notice
  of any distribution that includes a component. No upstream maintainer has
  endorsed DE4SDV; the listing says only that DE4SDV uses the project.

## What this means for the deliverable form

Two coherent product forms, and the choice belongs to the owner:

1. **Recipe-only (current).** The repository ships DE4SDV's own code plus build
   recipes that fetch upstream at the pins above. Operators build their own
   images. Copyleft never enters a distributed artifact.
2. **Distributable images.** DE4SDV would publish images. That requires replacing
   cannelloni with an Apache-2.0 transport (a small UDP bridge we own — the
   payload is plain CAN frames), or accepting and satisfying GPL-2.0 for the
   image that contains it.

Form 1 is what the tree already does; form 2 is a decision, not a cleanup.
