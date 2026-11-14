# Virtual E/E testbed — component versions and licences

This file is the version record that [`UPSTREAM.md`](../UPSTREAM.md) points at for
the virtual E/E testbed. It is the single place a pin is written; the upstream
page links here instead of repeating a number, so the two cannot disagree.

Nothing here is vendored. Every upstream component is either fetched as a
prebuilt release, built inside a container image from a pinned tag, or built from
source at a pinned commit. The repository contains no upstream source file.

| Component | Pin | Licence | How it enters the testbed | Used for |
|---|---|---|---|---|
| [vxedge](https://github.com/vxedge/vxedge) | `0.30.0` (release tarball, verified against the release `SHA256SUMS`) | Apache-2.0 | prebuilt binary, installed on the testbed host | gateway, slices, zones, services, signal plane |
| [KUKSA Databroker](https://github.com/eclipse-kuksa/kuksa-databroker) | `0.7.1` — `ghcr.io/eclipse-kuksa/kuksa-databroker@sha256:529d8c6d3cc223362667672978bcb8f92c4d356b25aedd336e7a2e004d7279bd` | Apache-2.0 | container image, digest-pinned, pulled by the vehicle manifest | signal plane (VSS broker) |
| [KUKSA CAN Provider](https://github.com/eclipse-kuksa/kuksa-can-provider) | `0.5.1` (git tag; the project publishes neither a PyPI package nor a registry image) | Apache-2.0 | cloned and run from source inside the zone image | DBC ↔ VSS bridge, both directions |
| [OpenBSW](https://github.com/eclipse-openbsw/openbsw) | commit `b9ad52761e87cd93f09fe002c6fc955e999dc4a0` (`posix-freertos` preset) | Apache-2.0 | built inside the zone image from a pinned commit, started only with `ZONE_UDS_ECU=1` | reference ECU on a zone bus: lifecycle and UDS over DoCAN |
| [SDV Simulation 5](https://github.com/nsengupta/sdv_simulation_5) | `ca0c733` — inspected, **not used** | Apache-2.0 | not built, not run | its private CMD/ACK/NACK codec was the thing this contract replaces |
| [cannelloni](https://github.com/mguentner/cannelloni) | `v2.1.2` — **replaced, no longer used** | **GPL-2.0** (`gpl-2.0.txt`; GitHub's detector reports none because the file is not named `LICENSE`) | was built from source inside the images; now only the comparison numbers in the README survive | the first pass carried CAN over UDP with it; `transport/bridge.py` replaced it |
| Ubuntu / GCP kernel | 24.04.5 LTS, `7.0.0-1017-gcp` | — | cloud image | host: `netem`/`htb`, `vcan`/`vxcan`, Open vSwitch |
| [cosign](https://github.com/sigstore/cosign) | `v3.1.4` (release binary, SHA-256 checked against the release's `cosign_checksums.txt`) | Apache-2.0 | host tool, not in any image | signs and verifies the packed package |
| [registry](https://github.com/distribution/distribution) | `2` — `docker.io/library/registry@sha256:46faa9a1ae6813194b53921a370f2f4f8c5e1aae228a89bceafef5847a6a3278` | Apache-2.0 | container on the testbed host, `127.0.0.1:5000`, TLS with a private CA and htpasswd auth | holds the two DE4SDV images so the baseline can name them by digest |
| [syft](https://github.com/anchore/syft) | `v1.57.1` (release binary) | Apache-2.0 | host tool, not in any image | generates the CycloneDX SBOMs in `sbom/` |

Evaluated, not used: [Ankaios](https://github.com/eclipse-ankaios/ankaios) `v1.1.0`
(Apache-2.0) hosted the same three workloads during a spike —
[`orchestration/README.md`](orchestration/README.md). Nothing in this stack depends on
it, which is why it is not in the table above.

## What is inside the images

The stack is not "GPL-free"; it is **free of copyleft in code DE4SDV writes and
links**. Those are different claims and only the second one is true.

| Inside the zone image | Licence | How it is used |
|---|---|---|
| DE4SDV code (`zone_ecu.py`, `bridge.py`) | Apache-2.0 | ours |
| OpenBSW reference application | Apache-2.0 | compiled in, run as a process |
| KUKSA CAN Provider, `kuksa-client` | Apache-2.0 | imported / run |
| `python-can` | **LGPL-3.0** | imported by the plant model and the gateway router |
| `cantools` | MIT | imported |
| `tini` | MIT | PID 1 in the container |
| `iproute2`, `can-utils`, `git` | **GPL-2.0** | unmodified Debian packages, invoked as programs |
| `libstdc++6` | GPL-3.0 with the GCC runtime exception | shared library the OpenBSW build needs |

What follows if DE4SDV publishes an image:

- **Apache-2.0 components** need their licence and NOTICE carried with the
  distribution — OpenBSW and the KUKSA pieces each have one.
- **`python-can` is LGPL-3.0.** It is imported, not linked into a compiled binary,
  and it is replaceable source, so the relinking condition is satisfied as long as
  its licence text ships and the package stays swappable. Do not vendor a patched
  copy.
- **The GPL-2.0 tools are unmodified distribution packages.** Debian ships their
  copyright files in `/usr/share/doc/*/copyright`; a published image carries those
  unchanged and points at the Debian archive for source.
- **No copyleft is linked into DE4SDV code**, and the only component that was
  (cannelloni, GPL-2.0) was replaced rather than shipped.

`transport/bridge.py` is DE4SDV's own code, not an upstream component: about 200
lines, Apache-2.0 like the rest of the repository.

## Licence consequences worth stating

- **The stack now carries no copyleft.** Every running component is Apache-2.0 or
  DE4SDV's own, so an image DE4SDV publishes can be distributed under the
  repository's licence with attribution and nothing else.
- **cannelloni was GPL-2.0 and was the one exception.** It ran as a separate
  process and was never linked into DE4SDV code, but a distributed image bundling
  the compiled binary would have carried GPL-2.0 obligations. It was replaced
  rather than complied with, because the payload is plain CAN frames and the
  transport is ~200 lines.
- **Attribution lives in `UPSTREAM.md`**, one row per project, and in the notice
  of any distribution that includes a component. No upstream maintainer has
  endorsed DE4SDV; the listing says only that DE4SDV uses the project.

## What this means for the deliverable form

Both forms are now open, and the choice is the owner's:

1. **Recipe-only.** The repository ships DE4SDV's code plus build recipes that
   fetch upstream at the pins above; operators build their own images.
2. **Distributable images.** Nothing blocks it on licence grounds any more. What
   remains is operational: a published image has to be built, tagged and scanned,
   and its upstream attribution has to travel with it.

The second is a decision about effort, not about permissions.
