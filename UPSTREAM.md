# Upstream projects

DE4SDV builds on other projects: SysML v2 libraries, an architecture
framework, vehicle software, a simulator and modeling tools. Their links and
versions are recorded where each one is used, in model files, decision records
and bench folders. This page lists them in one place.

Each row links the project, says what DE4SDV uses it for and says where the
version in use is recorded. The version is not repeated here, so this page
cannot disagree with that record.

A project is listed because DE4SDV uses or names it. The listing does not say
that its maintainers endorse DE4SDV.

## Model libraries and method sources

| Project | What DE4SDV uses it for | Version recorded in | Read more |
|---|---|---|---|
| [SYSMOD](https://github.com/MBSE4U/sysmod-sysmlv2) (MBSE4U) | Method library. DE4SDV uses selected concepts through its own adapter. | [`.project.json`](.project.json), [`sysand-lock.toml`](sysand-lock.toml) | [Upstream record](methodologies/sysmod-sysmlv2/upstream.md), [ADR 0002](docs/architecture-decisions/0002-adopt-sysmod-sysmlv2-library.md), [ADR 0007](docs/architecture-decisions/0007-pin-sysmod-sysand-dependency.md) |
| [PLEML](https://github.com/MBSE4U/PLEML) (MBSE4U) | Product-line library. The feature models and feature configurations import it. | [`.project.json`](.project.json), [`sysand-lock.toml`](sysand-lock.toml), [`pleml_package.py`](de4sdv/semantic/pleml_package.py) | [ADR 0022](docs/architecture-decisions/0022-adopt-pleml-as-product-line-authority.md) |
| [Requirements Management](https://github.com/ode4hera/SysML-v2-Requirements-Management) (ODE4HERA) | Attributes of requirements, such as rationale, source and status. | [`.project.json`](.project.json), [`sysand-lock.toml`](sysand-lock.toml) | [ADR 0009](docs/architecture-decisions/0009-adopt-ode4hera-requirements-attributes.md) |
| [Syside Views](https://sysand.com/projects/sensmetry/syside-views/) (Sensmetry) | Tables and matrices that the model defines as views. | [`.project.json`](.project.json), [`sysand-lock.toml`](sysand-lock.toml) | [`CONTRIBUTING`](CONTRIBUTING.md) |
| System Architecture Framework, SAF (GfSE): [viewpoint pages](https://saf.gfse.org/userdoc/viewpoints.html), [specification](https://github.com/GfSE/SAF-Specification), [SysML v2 projection](https://github.com/GfSE/SAF-SysMLV2) | Viewpoint and concern catalogue of the method. The specification is the content source. The projection is read for SysML v2 mechanics only. | [`saf-source.yaml`](methodologies/sysmod-sysmlv2/pilots/saf-source.yaml) | [Upstream record](methodologies/sysmod-sysmlv2/upstream.md), section "SAF reference catalogue lineage" |
| [COVESA VSS](https://github.com/COVESA/vehicle_signal_specification) | Source of the generated vehicle-signal library. | [Library README](textual-notation-of-model/libraries/covesa-vss-sysmlv2/README.md) | [ADR 0003](docs/architecture-decisions/0003-package-covesa-vss-as-sysmlv2-library.md), [ADR 0008](docs/architecture-decisions/0008-publish-covesa-vss-sysand-package.md), [`NOTICE`](NOTICE) |
| [COVESA IFEX](https://github.com/COVESA/ifex) | Classification of interfaces in the middleware model as Property, Method or Event. It is read as a source and is not used as a generator or binding. | Source record in [`middleware_variability_configuration.sysml`](textual-notation-of-model/packages/features/middleware/middleware_variability_configuration.sysml) | The same record |
| [SysML v2 Release](https://github.com/Systems-Modeling/SysML-v2-Release) (Systems Modeling) | Reference for SysML v2 constructs. Model files and ADR 0006 cite its examples. | Cited, not installed. Each citing file names the example it read. | [ADR 0006](docs/architecture-decisions/0006-variant-selection-construct-and-ple-adequacy.md) |

## Vehicle software and simulation

The benches under [`implementation/`](implementation/README.md) build or run
these projects.

| Project | What DE4SDV uses it for | Version recorded in | Read more |
|---|---|---|---|
| [Autoware](https://github.com/autowarefoundation/autoware) (Autoware Foundation): [universe](https://github.com/autowarefoundation/autoware_universe), [launch](https://github.com/autowarefoundation/autoware_launch), [simple planning simulator](https://github.com/autowarefoundation/autoware_simple_planning_simulator), [core](https://github.com/autowarefoundation/autoware_core) | Vehicle application of the AEBS benches. | `runtime-lock.yaml` of the [executable](implementation/aebs-autoware-executable-bench/runtime-lock.yaml), [nominal vehicle target](implementation/aebs-autoware-nominal-vehicle-target-bench/runtime-lock.yaml) and [stationary target](implementation/aebs-autoware-stationary-target-bench/runtime-lock.yaml) benches. Parameter files taken from Autoware name their source in a header comment. | [Implementations](implementation/README.md) |
| [AutoE2E](https://github.com/autowarefoundation/auto_e2e) (Autoware Foundation) and its [checkpoint repository](https://huggingface.co/AutowareFoundation/auto_e2e) | Planner of the closed-loop driving bench. | [Driving upstream record](textual-notation-of-model/packages/features/driving/upstream.md), [navigation README](implementation/closed-loop-driving-bench/navigation/README.md) | [Bench README](implementation/closed-loop-driving-bench/README.md) |
| [VisionPilot](https://github.com/autowarefoundation/vision_pilot) (Autoware Foundation) and its object-detection network [AutoSpeed](https://github.com/autowarefoundation/auto_speed) | Candidate application of the driver-assistance increment. It is read for the framing. No bench builds or runs it. | [Driving upstream record](textual-notation-of-model/packages/features/driving/upstream.md) | [Increment guide](docs/guides/driver-assistance-increment.md) |
| [CARLA](https://github.com/carla-simulator/carla) | Simulator of the closed-loop driving bench. | [Driving upstream record](textual-notation-of-model/packages/features/driving/upstream.md) for the revision inspected during framing. [Bench README](implementation/closed-loop-driving-bench/README.md) for the release the bench runs. | The same two files |
| Eclipse S-CORE: [reference integration](https://github.com/eclipse-score/reference_integration), [communication](https://github.com/eclipse-score/communication), [lifecycle](https://github.com/eclipse-score/lifecycle), [baselibs](https://github.com/eclipse-score/baselibs), [FEO](https://github.com/eclipse-score/feo), [SOME/IP gateway](https://github.com/eclipse-score/inc_someip_gateway), [score](https://github.com/eclipse-score/score) | Middleware of the S-CORE benches and of the driving agent. | Model: [`middleware_score_framing.sysml`](textual-notation-of-model/packages/features/middleware/middleware_score_framing.sysml), [`closed_loop_driving_physical_software_realization.sysml`](textual-notation-of-model/packages/features/driving/closed_loop_driving_physical_software_realization.sysml). CI: [`score-reference-interop-bench.yml`](.github/workflows/score-reference-interop-bench.yml) | [Interop bench](implementation/score-reference-interop-bench/README.md), [agent workspace](implementation/closed-loop-driving-bench/agent/workspace/README.md), [driving upstream record](textual-notation-of-model/packages/features/driving/upstream.md) |
| AAOS SDV (Android Open Source Project): [documentation](https://source.android.com/docs/automotive/sdv/getting-started), [manifest repository](https://android.googlesource.com/platform/manifest) | SDV Core and IVI guests of the AAOS benches. | [`aaos-cuttlefish-cloud-proof.yaml`](implementation/aaos-sdv-reference-interop-bench/evidence/aaos-cuttlefish-cloud-proof.yaml), [runbook](docs/runbooks/windows-aaos-sdv-reference-proof.md) | [ADR 0025](docs/architecture-decisions/0025-end-someip-in-an-sdv-core-vm.md), [boundary model](textual-notation-of-model/packages/architecture/aaos_sdv_middleware_boundary.sysml) |

Supporting software that these projects need, such as ROS 2 and Bazel, is
installed and pinned by the bench scripts and container images. It is not
listed here.

## Virtual E/E testbed

The software zonal E/E testbed under
[`de4sdv-virtual-ee/`](de4sdv-virtual-ee/README.md) runs these projects. None of
them is vendored: each is fetched as a pinned release, built inside a container
image from a pinned tag, or built from source at a pinned commit.

| Project | What DE4SDV uses it for | Version recorded in | Read more |
|---|---|---|---|
| [vxedge](https://github.com/vxedge/vxedge) and its [documentation](https://github.com/vxedge/docs) | Orchestration of the software E/E: gateway, slices, zones, services and signal plane. | [Components and licences](de4sdv-virtual-ee/versions.md) | [Testbed README](de4sdv-virtual-ee/README.md) |
| [KUKSA Databroker](https://github.com/eclipse-kuksa/kuksa-databroker) | VSS broker of the signal plane. | The same record | The same README |
| [KUKSA CAN Provider](https://github.com/eclipse-kuksa/kuksa-can-provider) | DBC ↔ VSS bridge inside each zone, both directions. | The same record | The same README |
| [cannelloni](https://github.com/mguentner/cannelloni) | Carried CAN over UDP in the first pass; replaced by DE4SDV's own [`transport/bridge.py`](de4sdv-virtual-ee/transport/bridge.py), so the stack carries no copyleft. GPL-2.0, which is why it was replaced rather than kept. | The same record | The same README |
| [OpenBSW](https://github.com/eclipse-openbsw/openbsw) | Reference ECU on a virtual bus: lifecycle and UDS over DoCAN. | The same record | The same README |
| [SDV Simulation 5](https://github.com/nsengupta/sdv_simulation_5) | Inspected only: its private actuator codec is what the modelled signal contract replaces. It is not built and not run. | The same record | The same README |
| [Distribution](https://github.com/distribution/distribution) | Registry image on the testbed host. It holds the two DE4SDV images by digest, so a moved tag cannot change what runs. | The same record | [`deploy/README.md`](de4sdv-virtual-ee/deploy/README.md) |
| [cosign](https://github.com/sigstore/cosign) | Signs the `vxp/1` package. The host verifies the record before provisioning anything. | The same record | [`deploy/README.md`](de4sdv-virtual-ee/deploy/README.md) |
| [syft](https://github.com/anchore/syft) | Generates the CycloneDX SBOMs committed under [`sbom/`](de4sdv-virtual-ee/sbom/README.md). | The same record | [`sbom/README.md`](de4sdv-virtual-ee/sbom/README.md) |

The licence of every component, and what a copyleft component means for a
distributed image, is stated in that one record rather than repeated here.

## Surveyed and not adopted

[`landscape.md`](de4sdv-virtual-ee/landscape.md) classifies every Eclipse SDV
project as use, track or skip. The rows below are named there and in the
testbed's documents. None of them is built or run: the row records a decision,
not a dependency.

| Project | Why it is named and not used |
|---|---|
| [Eclipse Ankaios](https://github.com/eclipse-ankaios/ankaios) | A second orchestrator was tried against the same workloads; vxedge was kept for its networking, supply chain and measurements. The spike is in [`de4sdv-virtual-ee/orchestration/`](de4sdv-virtual-ee/orchestration/README.md). |
| [Eclipse BlueChi](https://github.com/eclipse-bluechi/bluechi) | Tracked: systemd/D-Bus service control across nodes, not container orchestration. |
| [Eclipse Leda](https://github.com/eclipse-leda/leda) | Tracked: a distribution image for a target, not part of this testbed. |
| [Eclipse openDuT](https://github.com/eclipse-opendut/opendut) | Tracked: distributed test benches; its trigger is the two-host CARLA bench, not this one. |
| [Eclipse OpenSOVD](https://github.com/eclipse-opensovd/opensovd) | The next candidate for the diagnostic surface. Not integrated. |
| [Eclipse OpenXilEnv](https://github.com/eclipse-openxilenv/openxilenv) | Tracked: a SIL environment that overlaps the plant models this testbed writes itself. |
| [vsomeip](https://github.com/COVESA/vsomeip) (COVESA) | Candidate for the SOME/IP service plane of the backbone increment. Not adopted: the increment's scope prefers an owned subset. MPL-2.0. |
| [Vector SIL Kit](https://github.com/vectorgrp/sil-kit) | Tracked: simulation-time synchronisation and Vector tool interop. Adopting it means replacing the SocketCAN path, so it waits for that trigger. |

## Modeling tools

| Project | What DE4SDV uses it for | Version recorded in | Read more |
|---|---|---|---|
| [Syside](https://docs.sensmetry.com/) (Sensmetry) | Validates the SysML v2 text and renders the model diagrams. It needs a licence. | [`privileged-syside-validation.yml`](.github/workflows/privileged-syside-validation.yml) | [`CONTRIBUTING`](CONTRIBUTING.md) |
| [Sysand](https://github.com/sensmetry/sysand) (Sensmetry) and its [package index](https://sysand.com/) | Installs the SysML v2 libraries that the lock file pins. | The workflows that install it, for example [`ci.yml`](.github/workflows/ci.yml) | [`CONTRIBUTING`](CONTRIBUTING.md) |
| [SysML v2 API Services](https://github.com/Systems-Modeling/SysML-v2-API-Services) (Systems Modeling) | Service behind the public read-only model API. | [`Dockerfile`](deployment/sysml2-api/Dockerfile) | [ADR 0013](docs/architecture-decisions/0013-deploy-experimental-readonly-public-sysml-api.md), [deployment README](deployment/README.md) |
| [Eclipse SysON](https://github.com/eclipse-syson/syson) | Local pilot of a graphical SysML v2 editor. Contributors do not need it. | [`compose.yaml`](tools/syson/compose.yaml) | [SysON README](tools/syson/README.md) |

Build tools, container images, Python packages and GitHub Actions are pinned
or named in the files that use them: the files under
[`deployment/`](deployment/README.md),
[`requirements-mcp.txt`](requirements-mcp.txt) and the workflow files. They
are not listed here.

## Also named in the model

The model names more projects than the rows above cover.

- [KUKSA Databroker](https://github.com/eclipse-kuksa/kuksa-databroker) is
  recorded as a candidate that is not selected. Its source record is in
  [`middleware_variability_configuration.sysml`](textual-notation-of-model/packages/features/middleware/middleware_variability_configuration.sysml).
- [`sdv_platform_stack.sysml`](textual-notation-of-model/packages/architecture/sdv_platform_stack.sysml)
  names the candidates of each stack layer, with their licence terms. Several
  have no row above, among them Openpilot, Apollo, AUTOSAR Adaptive, QNX, ACRN
  and KVM. DE4SDV has recorded no source link for them.

## Other sources

Sources that are documents, not projects, are recorded elsewhere:

- method and literature sources in
  [`source-notes.md`](docs/references/source-notes.md);
- the UN regulation text that AEBS requirements cite as a source, in
  [`aebs-regulatory-source.yaml`](methodologies/sysmod-sysmlv2/pilots/aebs-regulatory-source.yaml).
  The model treats it as provenance, not as compliance evidence.

## Keeping this page current

A pull request that adds, removes or replaces an upstream project updates this
page. A pull request that only changes a version does not. It updates the
record named in the row.

CI checks that every GitHub repository named in a tracked file has an entry on
this page. [`CONTRIBUTING`](CONTRIBUTING.md) says how to run the check and
what to do when it fails.
