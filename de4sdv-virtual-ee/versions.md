# Virtual E/E testbed — component versions and licences

[`UPSTREAM.md`](../UPSTREAM.md) links here for component pins and provenance.
The build recipes, [`parts.yaml`](vehicle/parts.yaml) and
[`vxp.lock`](vehicle/vxp.lock) identify the executable inputs. The SBOM binding
under [`sbom/`](sbom/README.md) identifies the images actually scanned; a version
listed here is not evidence that an image contains only that component.

Upstream application source is fetched during builds rather than vendored in
this directory. Each component retains its own licence. The repository's
Apache-2.0 licence does not relicense third-party packages inside an image.

| Component | Pin | Licence | How it enters the testbed | Used for |
|---|---|---|---|---|
| [vxedge](https://github.com/vxedge/vxedge) | `0.30.0` (release tarball, verified against the release `SHA256SUMS`) | Apache-2.0 | prebuilt binaries on the testbed host | orchestration, gateway, slices, zones, services and signal plane |
| [KUKSA Databroker](https://github.com/eclipse-kuksa/kuksa-databroker) | `0.7.1` — `ghcr.io/eclipse-kuksa/kuksa-databroker@sha256:529d8c6d3cc223362667672978bcb8f92c4d356b25aedd336e7a2e004d7279bd` | Apache-2.0 | digest-pinned container image | VSS broker |
| [KUKSA CAN Provider](https://github.com/eclipse-kuksa/kuksa-can-provider) | `0.5.1` | Apache-2.0 | this recipe runs Python source fetched at the tag; upstream also publishes a container image | DBC ↔ VSS, both directions |
| [OpenBSW](https://github.com/eclipse-openbsw/openbsw) | commit `b9ad52761e87cd93f09fe002c6fc955e999dc4a0` (`posix-freertos` preset) | Apache-2.0 | built in a container builder stage; enabled by `ZONE_UDS_ECU=1` | lifecycle and UDS over DoCAN |
| [SDV Simulation 5](https://github.com/nsengupta/sdv_simulation_5) | `ca0c733` — inspected, not built or run | Apache-2.0 | historical design comparison only | private actuator codec considered before the DBC contract |
| [cannelloni](https://github.com/mguentner/cannelloni) | `v2.1.2` — historical dependency, absent from current build recipes | GPL-2.0-only (source headers and `gpl-2.0.txt`) | previously built and run as a separate executable | initial CAN-over-UDP transport; earlier comparison measurements retained |
| Ubuntu / GCP kernel | 24.04.5 LTS, `7.0.0-1017-gcp` | component-specific distribution licences | cloud host image | `netem`/`htb`, `vcan`/`vxcan`, Open vSwitch |
| [cosign](https://github.com/sigstore/cosign) | `v3.1.4` (release binary checked against `cosign_checksums.txt`) | Apache-2.0 | host tool | package signing and verification |
| [registry](https://github.com/distribution/distribution) | `2` — `docker.io/library/registry@sha256:46faa9a1ae6813194b53921a370f2f4f8c5e1aae228a89bceafef5847a6a3278` | Apache-2.0 | loopback host registry with TLS and operator-owned authentication | serves the DE4SDV images by digest |
| [syft](https://github.com/anchore/syft) | `v1.57.1` | Apache-2.0 | host tool | generates the inventories under `sbom/` |

[Ankaios](https://github.com/eclipse-ankaios/ankaios) `v1.1.0` (Apache-2.0)
was evaluated in the [`orchestration/`](orchestration/README.md) spike. It is not
a dependency of the vehicle package.

## CAN transport provenance

The first feasibility pass executed cannelloni as a separate program. It was
not linked into the plant or gateway Python sources. The current recipes no
longer build or run it. Attribution and the earlier buffering measurements are
retained because that prototype informed the transport decision.

[`transport/bridge.py`](transport/bridge.py) was introduced in commit
`3684d647a9f57dd572442ccbedc6dc538e436511` as a newly authored Python file under
the repository's Apache-2.0 licence. Its `D4E1` framing is a fixed 17-byte
single-frame protocol, not the cannelloni wire protocol. It deliberately omits
batching and CAN FD. Reducing the dependency surface and the obligations of
bundling an additional GPL executable were decision factors; replacing that
component does not remove other components' licence obligations.

The authoring record does not provide a source-by-source account of every input
consulted. A later comparison of the implementations is not retroactive proof
of independent authorship. No clean-room claim or legal clearance is made.
Any reused or adapted upstream material must retain its applicable terms and
attribution; a change of filename, language or framing does not settle that
question. Review provenance before distributing a replacement under new terms.

## What is inside the images

The images include copyleft components. Distinguish authored code, imported
libraries and separate programs rather than describing the stack as having one
licence.

| Component group | Licence record | Use |
|---|---|---|
| DE4SDV-authored plant, bridge, gateway and service code | Apache-2.0 declared by this repository | experiment implementation |
| OpenBSW, KUKSA CAN Provider and `kuksa-client` | Apache-2.0 | separate application and imported/run provider code |
| `python-can` | SBOM reports LGPL-3.0-only | imported by the plant and gateway; imports are not a licence exemption |
| `cantools`, `tini` | MIT | DBC parsing and process supervision |
| Debian packages including `iproute2`, `can-utils` and `git` | GPL and other package/binary-specific terms; see SBOM and package copyright files | unmodified separate programs |
| `libstdc++6` | GPL-3.0 with the GCC runtime exception; see package copyright | OpenBSW runtime library |

This is a summary, not the complete dependency graph or a publication verdict.
An SBOM is an inventory; scanner licence detection needs review and does not
prove compliance.

## Distribution boundary

The current deliverable is code and build recipes. Public image distribution
is a separate approval and review step. Before publishing an exact image:

1. Bind its SBOM and provenance to the immutable image digest and review the
   complete component inventory, not just the table above.
2. Carry applicable copyright, licence and NOTICE material for Apache/MIT and
   other included components, including modifications where relevant.
3. Establish and retain an applicable GPL corresponding-source distribution or
   offer procedure for the exact binaries distributed. A package copyright file
   and an ordinary link to a Debian mirror alone do not prove that procedure.
4. Review LGPL corresponding-source, modification and replacement requirements
   for the actual use and distribution of `python-can` and other LGPL packages.
   Licence text plus an import statement is not a complete compliance check.
5. Review the replacement transport's authoring provenance and any upstream
   adaptations before relying on the declared source licence.

Separate GPL executables can coexist with independently licensed programs;
container packaging neither automatically relicenses the separate sources nor
removes the bundled components' obligations. No certification, legal approval or
upstream endorsement is claimed by this record.
