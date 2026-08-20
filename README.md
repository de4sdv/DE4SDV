# Contact

Use GitHub issues and pull requests for project work, questions, proposals,
and decisions that need a durable public record.

DE4SDV also uses Mattermost for lightweight coordination at
<https://chat.de4sdv.org>. Access is invite-only. To request an invite, open a
GitHub issue using the **Mattermost invite request** template and briefly say who
you are, what you want to contribute or discuss, and why chat access would help.

See [`COMMUNICATION`](COMMUNICATION.md) for the full communication policy.

# Vision

Digital Engineering for Software-Defined Vehicle (DE4SDV) envisions a digitally
engineered, continuously certifiable software-defined vehicle product line that
embraces ecosystem diversity rather than locking into a single stack.
Across subsystems such as ADAS, operating systems, and core software, multiple
open-source alternatives already exist. DE4SDV applies product-line engineering
to model this variability explicitly as configurable architectures, enabling
systematic comparison of alternatives, transparent trade-off decisions, and
lifecycle-wide assurance.

In this future, OEM differentiation will likely extend beyond traditional choices
such as color, trim packages, sensors, and assistance systems. A central
differentiator will likely be **certified freedom**: the ability to customize
vehicle features within clearly defined guardrails that preserve safety,
security, and compliance. Equally important are openness and trust, including
transparency over how vehicle and user data is handled, and meaningful user
control over that data.

DE4SDV is also a workstream within the INCOSE Automotive Working Group and
regularly discussed.

# System-of-Interest

DE4SDV uses the ASELCM three-system framing to keep product, engineering, and
ecosystem scopes distinct.

- **System 1: configurable SDV product line and configured vehicle/software
  variants.** This is the engineered system managed by DE4SDV. It includes SDV
  vehicle architecture variants, feature configurations, product models,
  software and hardware alternatives, interfaces, operational behavior, and
  variant-specific safety, security, and compliance constraints.
- **System 2: DE4SDV life-cycle engineering and assurance system.** This is the
  primary repository System-of-Interest. It is a project-governed, open-source,
  model-based SDV product-line engineering and assurance management system. It
  specifies configurable architectures, manages variability, integrates
  project-owned and selected external OSS assets through controlled interfaces
  and adapters, executes verification, validation, simulation, and digital-twin
  workflows, and maintains continuous-certification evidence baselines for SDV
  variants.
- **System 3: DE4SDV open innovation ecosystem.** This is the governance,
  standards, methodology, contributor, toolchain, and upstream ecosystem that
  evolves System 2. It includes maintainers, contributors, ADRs, review
  workflows, standards communities, external OSS projects, and methodology
  owners.

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

Boundary rule: an element is part of System 2 only when DE4SDV governs its
configuration, change control, and evidence or traceability obligations.
Otherwise, it is treated as an external system at the ecosystem boundary and is
integrated through explicit interface and assurance contracts.

This boundary definition aligns the project with digital-twin reference-model
practice by making the managed twin boundary explicit and by separating internal
consistency-management responsibilities from external business and ecosystem
processes.

# Digital Engineering for Software-Defined Vehicle

An open-source starter repository for **Digital Engineering of Software-Defined
Vehicle (SDV)** with emphasis on:

- SysML v2 modeling and SysML v2 API integration
- Feature-based Product Line Engineering / Model-Based Product Line Engineering
- Digital continuity, OSLC, digital thread, and digital twin readiness
- FMI / FMU and SSP-based simulation interoperability
- Safety, security, UNECE-oriented compliance, and continuous homologation
- DevSecOps practices for regulated cyber-physical systems

# Getting started

- **New to DE4SDV?** Read the [getting started guide](docs/getting-started/README.md) — what this project is, how the repository is organized, and how the process works.
- **Read the model** — [how to read the SysML v2 model](docs/guides/sysml-elements.md): the element kinds and why DE4SDV uses them.
- **Explore the model** in the [model viewer](#model-viewer) or serve your own working tree locally.
- **Want to contribute?** Follow the [contribution model](#contribution-model).

# Model viewer

A live viewer is deployed at **https://viewer.de4sdv.org** — the public,
read-only HTML viewer for the SysML v2 systems model: model tree, member
documentation, and every declared view with the diagram SysIDE renders from
it — including hover tooltips on elements and connections, go-to-definition,
branch/PR revision picking, and diagram fullscreen.

Running it locally on localhost serves **your own working tree and unmerged
branches** — use it for your own work and direct feedback before anything is
published:

```bash
python -m tools.sysml_html_viewer.serve --repo . --port 8787
# open http://127.0.0.1:8787/
```

See the [model viewer how-to](docs/guides/model-viewer.md) for every feature,
or click **Help** in the viewer header (the same guide is published on the
viewer website).

## Repository map

| Area | Purpose |
|---|---|
| `docs/` | Human-facing documentation: getting-started, guides, terminology, ADRs, runbooks, plans |
| `compliance/` | Safety, security, UNECE, homologation-related evidence placeholders |
| `standards/` | Standards map and interpretation notes |
| `approach/` | Process set, framework, ontology, viewpoints |
| `methodologies/` | Method guidance and reusable engineering methods |
| `textual-notation-of-model/` | System model assets and examples |
| `digital-continuity/` | OSLC, digital thread, traceability, lifecycle integration |
| `digital-twin/` | Digital twin concepts, parameters, and runtime alignment |
| `simulation/` | FMI/FMU/SSP simulation integration assets |
| `implementation/` | Reference implementations with reproducible evidence (see `implementation/README.md`) |
| `experiments/` | Spikes and exploration results (not maintained assets) |
| `model-based-product-line-engineering/` | Feature models, configurations, shared assets, product models |
| `configuration-management/` | Baselines, change control, versioning, release evidence |
| `continuous-homologation/` | Continuous compliance and approval evidence workflow |
| `devsecops/` | CI/CD, security automation, SBOM, threat-model automation |
| `sysmlv2-api/` | SysML v2 API clients, examples, integration notes |
| `tools/` | Scripts, utilities, and development tooling |
| `scripts/` | Repository checks, smoke tests, SysML validation wrapper |
| `tests/` | Test suite for repository scripts and tooling |
| `.github/agents/` | Task-specific AI agent instructions |

## Contribution model

This project welcomes contributions beyond code: documentation, examples,
safety/security analysis, modeling patterns, feature models, test cases, issue
triage, and standards mapping are all valuable.

Start here:

0. New here? Read the [getting started guide](docs/getting-started/README.md)
1. Read the practical contributor guide: [`CONTRIBUTING`](CONTRIBUTING.md)
2. Read [`AGENTS`](AGENTS.md) if you use an AI coding assistant
3. Read the [Project Charter](docs/project-goals/project-charter.md)
4. Open an issue using the templates in `.github/ISSUE_TEMPLATE/`
5. Submit a focused pull request using the PR checklist

## License

Except where otherwise noted, original DE4SDV content is licensed under the
[Apache License 2.0](LICENSE).

This repository also contains third-party or derived material under other
licenses. In particular, the generated
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
