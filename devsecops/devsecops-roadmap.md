# DevSecOps Control Status

Last verified against the live repository: 2026-09-03.

| Control | Status | Next action |
|---|---|---|
| Protected `main` branch | Enabled | Keep PR, status-check, up-to-date-branch, and linear-history gates synchronized with governance |
| Secret scanning | Enabled | Review alerts through the repository security interface |
| Push protection | Enabled | Keep enabled; document any exceptional bypass |
| Required project test check | Partial | Run the complete project-owned pytest suite in the required `checks` job |
| Dependabot security updates | Not enabled | Enable after maintainer approval and document alert triage ownership |
| Private vulnerability reporting | Not enabled | Enable after maintainer approval or publish a functioning private reporting channel |
| Dependency review | Not implemented | Add when dependency manifests are part of the normal contribution path |
| Code scanning/static analysis | Not implemented | Select an owned, reviewable analysis path before enabling a noisy default |
| SBOM generation | Not implemented | Define release scope and consumer before producing an SBOM |
| Release evidence | Not implemented | Bind release notes, baseline register, public gates, and privileged validation to one commit |

This table reports repository controls, not vehicle-product security or
certification status.
