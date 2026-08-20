# DE4SDV — Digital Engineering for Software-Defined Vehicle

An open-source project for **digitally engineered, configurable, continuously
certifiable software-defined vehicle (SDV) product lines**. DE4SDV applies
product-line engineering and model-based systems engineering — SysML v2,
feature-based product-line engineering, digital continuity, simulation
interoperability, and continuous compliance — so that SDV variability across
subsystems (ADAS, operating systems, core software) is modeled explicitly as
configurable architectures, enabling systematic comparison of alternatives,
transparent trade-off decisions, and lifecycle-wide assurance.

DE4SDV is a workstream within the INCOSE Automotive Working Group.

## Vision

In the SDV future, OEM differentiation will extend beyond traditional choices
such as color, trim packages, sensors, and assistance systems. A central
differentiator will be **certified freedom**: the ability to customize vehicle
features within clearly defined guardrails that preserve safety, security, and
compliance. Equally important are openness and trust, including transparency
over how vehicle and user data is handled, and meaningful user control over
that data.

DE4SDV embraces ecosystem diversity rather than locking into a single stack:
across subsystems, multiple open-source alternatives already exist, and the
project models that variability instead of hiding it.

## Explore the model

The core artifact is the SysML v2 systems model under
[`textual-notation-of-model/`](textual-notation-of-model/README.md). Explore
it in the live viewer:

- **https://viewer.de4sdv.org** — the public, read-only HTML viewer: model
  tree, member documentation, and every declared view with the diagram SysIDE
  renders from it — including hover tooltips on elements and connections,
  go-to-definition, branch/PR revision picking, and diagram fullscreen.
- Running it locally serves **your own working tree and unmerged branches**:

```bash
python -m tools.sysml_html_viewer.serve --repo . --port 8787
# open http://127.0.0.1:8787/
```

See the [model viewer how-to](docs/guides/model-viewer.md) for every feature,
or click **Help** / **Elements** in the viewer header (the guides are
published on the viewer website too).

## Getting started

New here? The [getting started guide](docs/getting-started/README.md) walks
you through: what DE4SDV works on, the three-system framing, repository
layout, exploring the model, understanding the increment process, running the
checks, and making a first contribution.

To read the model source itself, the
[model element guide](docs/guides/sysml-elements.md) explains the SysML v2
element kinds used across the model and why DE4SDV uses them — from the
increment shell and views to the verification/evidence chain.

## System-of-Interest

DE4SDV uses the ASELCM three-system framing to keep product, engineering, and
ecosystem scopes distinct:

- **System 1: configurable SDV product line and configured vehicle/software
  variants.** The engineered system managed by DE4SDV: SDV vehicle
  architecture variants, feature configurations, product models, software and
  hardware alternatives, interfaces, operational behavior, and
  variant-specific safety, security, and compliance constraints.
- **System 2: DE4SDV life-cycle engineering and assurance system.** The
  primary repository System-of-Interest: a project-governed, open-source,
  model-based SDV product-line engineering and assurance management system
  that specifies configurable architectures, manages variability, integrates
  project-owned and selected external OSS assets through controlled interfaces
  and adapters, executes verification, validation, simulation, and digital-twin
  workflows, and maintains continuous-certification evidence baselines for SDV
  variants.
- **System 3: DE4SDV open innovation ecosystem.** The governance, standards,
  methodology, contributor, toolchain, and upstream ecosystem that evolves
  System 2: maintainers, contributors, ADRs, review workflows, standards
  communities, external OSS projects, and methodology owners.

Inside the System 2 boundary:

- Product-line architecture and variability definitions under DE4SDV governance
- Project-controlled integration assets, including adapters, wrappers, interface
  contracts, and baselines
- Verification, validation, simulation, and digital-twin workflow assets managed
  by the project
- Lifecycle evidence, metadata, and traceability artifacts needed for continuous
  certification claims

Outside the System 2 boundary, but connected through interfaces:

- Independently governed upstream OSS projects and external toolchains
- Partner, supplier, enterprise, or ecosystem systems not governed by DE4SDV
- Runtime or operational environments that consume System 2 outputs but are not
  project-controlled

**Boundary rule:** an element is part of System 2 only when DE4SDV governs its
configuration, change control, and evidence or traceability obligations.
Otherwise it is treated as an external system at the ecosystem boundary,
integrated through explicit interface and assurance contracts. This boundary
definition aligns the project with digital-twin reference-model practice by
making the managed twin boundary explicit.

## Repository map

| Area | Purpose |
|---|---|
| `docs/` | Human-facing documentation: getting-started, guides, terminology, ADRs, runbooks, plans |
| `approach/` | Process set, framework, ontology, viewpoints |
| `methodologies/` | Method guidance and reusable engineering methods |
| `textual-notation-of-model/` | System model assets and examples |
| `model-based-product-line-engineering/` | Feature models, configurations, shared assets, product models |
| `implementation/` | Reference implementations with reproducible evidence (see `implementation/README.md`) |
| `compliance/` | Safety, security, UNECE, homologation-related evidence placeholders |
| `continuous-homologation/` | Continuous compliance and approval evidence workflow |
| `configuration-management/` | Baselines, change control, versioning, release evidence |
| `standards/` | Standards map and interpretation notes |
| `digital-continuity/` | OSLC, digital thread, traceability, lifecycle integration |
| `digital-twin/` | Digital twin concepts, parameters, and runtime alignment |
| `simulation/` | FMI/FMU/SSP simulation integration assets |
| `sysmlv2-api/` | SysML v2 API clients, examples, integration notes |
| `devsecops/` | CI/CD, security automation, SBOM, threat-model automation |
| `experiments/` | Spikes and exploration results (not maintained assets) |
| `tools/` | Scripts, utilities, and development tooling |
| `scripts/` | Repository checks, smoke tests, SysML validation wrapper |
| `tests/` | Test suite for repository scripts and tooling |
| `.github/agents/` | Task-specific AI agent instructions |

The full index lives in [`docs/repository-tree.md`](docs/repository-tree.md).

## Contributing

This project welcomes contributions beyond code: documentation, examples,
safety/security analysis, modeling patterns, feature models, test cases, issue
triage, and standards mapping are all valuable.

1. Read the [getting started guide](docs/getting-started/README.md) for
   orientation
2. Read the practical contributor guide: [`CONTRIBUTING`](CONTRIBUTING.md)
3. Read [`AGENTS`](AGENTS.md) if you use an AI coding assistant
4. Read the [Project Charter](docs/project-goals/project-charter.md)
5. Open an issue using the templates in `.github/ISSUE_TEMPLATE/`
6. Submit a focused pull request using the PR checklist

## Contact

Use GitHub issues and pull requests for project work, questions, proposals,
and decisions that need a durable public record. DE4SDV also uses Mattermost
for lightweight coordination at <https://chat.de4sdv.org> (invite-only;
request an invite through the **Mattermost invite request** issue template).
See [`COMMUNICATION`](COMMUNICATION.md) for the full communication policy.

## License

Except where otherwise noted, original DE4SDV content is licensed under the
[Apache License 2.0](LICENSE). This repository also contains third-party or
derived material under other licenses; in particular, the generated
[`COVESA_VSS.sysml`](textual-notation-of-model/libraries/covesa-vss-sysmlv2/COVESA_VSS.sysml)
library is licensed under the Mozilla Public License 2.0. Per-file SPDX
identifiers and accompanying license files identify the license applicable to
such material. See [`NOTICE`](NOTICE) for the bundled-material summary.

## References

- [ASELCM three-system framing](docs/architecture-decisions/0004-adopt-aselcm-three-system-framing.md)
- [SYSMOD adoption and tailoring](methodologies/sysmod-sysmlv2/de4sdv-tailoring.md)
- [COVESA VSS as SysML v2 library](docs/architecture-decisions/0003-package-covesa-vss-as-sysmlv2-library.md)
- [SysML v2 API repository as live model store](docs/architecture-decisions/0005-use-sysml-v2-api-repository-as-live-model-store.md)

See also [`docs/references/source-notes`](docs/references/source-notes.md) for detailed source attributions.
