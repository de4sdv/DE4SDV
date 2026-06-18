# ADR 0005: Use SysML v2 API repository as live model store

## Status

Proposed

## Context

DE4SDV needs a workflow where SysML v2-capable tools can work on one shared
model instead of exchanging disconnected exports. The SysML v2 API enables GUI
modeling tools, viewers, analysis scripts, and repository automation to read and
write model elements through a common model repository.

DE4SDV also needs an open-source review workflow. Contributors and maintainers
need pull requests, readable diffs, validation evidence, generated publication
artifacts, and stable documentation in GitHub. Treating a live model repository
as the only project record would weaken reviewability and make the public
baseline dependent on a specific running service.

The initial GUI tool choice for the DE4SDV pilot is Eclipse SysON. SysON is an
open-source, web-based graphical modeling tool for SysML v2. It is still an
active-development tool, so DE4SDV should adopt it through a reversible pilot
rather than a hard production dependency.

## Decision

DE4SDV will use a SysML v2 API repository as the authoritative store for the
live model graph.

GitHub remains the authoritative reviewed project baseline. GitHub stores the
reviewed textual snapshots, generated view artifacts, sync metadata,
documentation, ADRs, and validation evidence.

Modeling tools may read and write model elements through the SysML v2 API.
A controlled sync pipeline exports model snapshots, rendered views, and
traceability metadata into GitHub through pull requests. The pipeline must not
push generated model updates directly to `main`.

The first pilot slice is the DE4SDV ASELCM-aligned context model:

- System 1: configurable SDV product line and configured vehicle/software
  variants.
- System 2: DE4SDV life-cycle engineering and assurance system.
- System 3: DE4SDV open innovation ecosystem.

The first two generated/publication views are:

- `system-context`
- `lifecycle-engineering-system`

## Consequences

- SysML v2 GUI changes should land first in the model repository, then be
  exported into GitHub as generated artifacts in a draft pull request.
- GitHub changes to textual snapshots should be imported back into the model
  repository only after review and merge.
- Generated view images in GitHub are publication artifacts. They should be
  regenerated from the model repository and view definitions, not hand-edited.
- Markdown pages should embed stable generated image paths. The sync pipeline
  should update the image files and manifests, not rewrite Markdown links on
  every model change.
- Every generated snapshot and view artifact should identify the originating
  SysML project, branch, and commit.
- Public contributor validation must not require privileged model-repository
  write credentials or private tool tokens.
- SysON is the preferred GUI tool for the pilot, but the architecture should
  keep the SysML v2 API boundary clean enough to support other compliant tools
  later.

## Sync policy

### Model repository to GitHub

```text
SysON or API tool edit
  -> SysML v2 repository commit
  -> sync job detects or is given the commit
  -> export textual snapshot and generated views
  -> write manifests with source commit metadata
  -> open draft GitHub pull request
  -> CI and maintainer review
  -> merge to main
```

### GitHub to model repository

```text
Contributor edits textual snapshot or view definition in a pull request
  -> public CI validates what it can without secrets
  -> maintainer review and merge
  -> privileged/import job updates the model repository
  -> import commit records the Git SHA it came from
```

## Pilot acceptance criteria

The first pilot is successful when:

- the DE4SDV context model exists in the SysML v2 repository;
- SysON can create or edit the model slice through the live repository path;
- two views are rendered as SVG artifacts in GitHub;
- both views include source project, branch, and commit metadata;
- the GitHub update is proposed by pull request, not pushed directly to `main`;
- repository checks pass or clearly document any validation blocker.

## Non-decisions

This ADR does not:

- choose a production hosting model for the SysML v2 repository;
- require SysON for all future modeling work;
- define the final renderer or image export API;
- define the full textual SysML v2 export/import mapping;
- allow generated model updates to bypass pull request review; or
- claim certification, compliance approval, or homologation evidence.

## Links

- [ADR 0004: Adopt ASELCM three-system framing for DE4SDV](0004-adopt-aselcm-three-system-framing.md)
- [SysML v2 API pilot notes](../../sysmlv2-api/README.md)
- [Model views](../../textual-notation-of-model/views/README.md)
