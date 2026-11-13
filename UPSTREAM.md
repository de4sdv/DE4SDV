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
