# Contact

Use GitHub issues and pull requests for project work, questions, proposals,
and decisions that need a durable public record.

DE4SDV also uses Mattermost for lightweight coordination at
<https://chat.de4sdv.org>. Access is invite-only. To request an invite, open a
GitHub issue using the **Mattermost invite request** template and briefly say who
you are, what you want to contribute or discuss, and why chat access would help.

See [`COMMUNICATION.md`](COMMUNICATION.md) for the full communication policy.

# Vision

Digital Engineering for Software-defined Vehicle (DE4SDV) envisions a digitally
engineered, continuously certifiable software-defined vehicle product line that
embraces ecosystem diversity rather than locking into a single stack.
Across subsystems such as ADAS, operating systems, and core software, multiple
open-source alternatives already exist. DE4SDV applies product line engineering
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

## Repository map

| Area | Purpose |
|---|---|
| `docs/` | Human-facing documentation, terminology, roadmap, references |
| `compliance/` | Safety, security, UNECE, homologation-related evidence placeholders |
| `standards/` | Standards map and interpretation notes |
| `approach/` | Process set, framework, ontology, viewpoints |
| `methodologies/` | Method guidance and reusable engineering methods |
| `textual-notation-of-model/` | System model assets and examples |
| `digital-continuity/` | OSLC, digital thread, traceability, lifecycle integration |
| `digital-twin/` | Digital twin concepts, parameters, and runtime alignment |
| `simulation/` | FMI/FMU/SSP simulation integration assets |
| `implementation/` | Reference implementation code will live here |
| `model-based-product-line-engineering/` | Feature models, configurations, shared assets, product models |
| `configuration-management/` | Baselines, change control, versioning, release evidence |
| `continuous-homologation/` | Continuous compliance and approval evidence workflow |
| `devsecops/` | CI/CD, security automation, SBOM, threat-model automation |
| `sysmlv2-api/` | SysML v2 API clients, examples, integration notes |
| `tools/` | Scripts, utilities, and development tooling |
| `specs/` | Short, current specifications for humans and AI agents |
| `.github/agents/` | Task-specific AI agent instructions |

## Contribution model

This project welcomes contributions beyond code: documentation, examples,
safety/security analysis, modeling patterns, feature models, test cases, issue
triage, and standards mapping are all valuable.

Start here:

1. Read the practical contributor guide: [`CONTRIBUTING.md`](CONTRIBUTING.md)
2. Read [`AGENTS.md`](AGENTS.md) if you use an AI coding assistant
3. Read the [Project Charter](docs/project-goals/project-charter.md)
4. Open an issue using the templates in `.github/ISSUE_TEMPLATE/`
5. Submit a focused pull request using the PR checklist

## License

**Apache License 2.0**.
