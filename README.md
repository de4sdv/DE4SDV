# Contact
Get in touch with us: https://join.slack.com/t/sdv-sysmlv2/shared_invite/zt-3xeu04a3n-o7_6M46QNAoXKhEiLbb0gw

# Vision
DE4SDV envisions a digitally engineered, continuously certifiable software-defined vehicle product line that embraces ecosystem diversity rather than locking into a single stack.
Across domains such as ADAS, operating systems, and core software, multiple open-source alternatives already exist. DE4SDV applies product line engineering to model this variability explicitly as configurable architectures, enabling systematic comparison of alternatives, transparent trade-off decisions, and lifecycle-wide assurance.

In this future, OEM differentiation will extend beyond traditional choices such as color, trim packages, sensors, and assistance systems. A central differentiator will be **certified freedom**: the ability to customize vehicle features within clearly defined guardrails that preserve safety, security, and compliance. Equally important are openness and trust, including transparency over how vehicle and user data is handled, and meaningful user control over that data.

# System-of-Interest

The System of Interest is a project-governed, open-source, model-based SDV Product-Line Engineering and Assurance System. It incrementally realizes SDV use cases by specifying configurable product-line architectures, managing variability, integrating project-owned and selected external OSS assets through controlled interfaces and adapters, executing verification, validation, simulation, and digital-twin workflows, and maintaining continuous certification evidence baselines for SDV variants. Independently governed OSS projects remain outside the SoI unless they are forked, wrapped, configured, or baselined as part of the project-controlled architecture; otherwise, they interact with the SoI at the external ecosystem boundary.

# Digital Engineering for Software-Defined Vehicle

An open-source starter repository for **Digital Engineering of Software-Defined Vehicle (SDV)** with emphasis on:

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

This project welcomes contributions beyond code: documentation, examples, safety/security analysis, modeling patterns, feature models, test cases, issue triage, and standards mapping are all valuable.

Start here:

1. Read the practical contributor guide: [`CONTRIBUTING.md`](CONTRIBUTING.md)
2. Read [`AGENTS.md`](AGENTS.md) if you use an AI coding assistant
3. Read the [Project Charter](docs/project-goals/project-charter.md)
4. Open an issue using the templates in `.github/ISSUE_TEMPLATE/`
5. Submit a focused pull request using the PR checklist

## License

Default scaffold license: **Apache License 2.0**. Replace it if your project needs another license before publishing.
