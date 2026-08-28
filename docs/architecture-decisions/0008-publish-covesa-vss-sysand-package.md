# ADR 0008: Publish the COVESA VSS SysML v2 library on the Sysand Index

## Status

Proposed

## Context

[ADR 0003](0003-package-covesa-vss-as-sysmlv2-library.md) packaged the
generated COVESA VSS SysML v2 library as a draft Sysand interchange project
under `textual-notation-of-model/libraries/covesa-vss-sysmlv2/`. The package
is now complete for publication:

- `.project.json` identifies it as `de4sdv/covesa-vss-sysmlv2` version
  `0.1.0`, license `MPL-2.0`;
- the metamodel is set to `https://www.omg.org/spec/SysML/20250201`;
- `.meta.json` carries SHA256 source checksums via `sysand build --update-meta`;
- the built `.kpar` contains `.project.json`, `.meta.json`, `README.md`,
  `CHANGELOG.md`, `COVESA_VSS.sysml`, and `LICENSES/MPL-2.0.txt`.

The Sysand Index (`sysand.com`) is the public package index for SysML v2 and
KerML projects. Publishing makes the package installable by any Sysand client
as `pkg:sysand/de4sdv/covesa-vss-sysmlv2`.

Publishing is irreversible on the index: a published version can never be
overwritten, replaced, or removed. The only recovery path for a defective
release is publishing a fixed release under a new version number.

## Decision

DE4SDV will publish the generated library on the Sysand Index under the
project ID `de4sdv/covesa-vss-sysmlv2`, starting with version `0.1.0`.

The published package contains the generated `COVESA_VSS.sysml` snapshot
only. It does **not** contain `DE4SDV_VSS_Extensions.sysml`. DE4SDV candidate
extension signals are separately authored DE4SDV vocabulary; they stay in the
repository until they are proposed to and accepted by COVESA upstream, and
must not be presented as upstream COVESA VSS signals.

The package retains the pinned COVESA source commit
(`6fb1dac2630a8910ee996863b2af02b310dcd7ce`) in its README and changelog as
source provenance. Publication is a redistribution of a derived, attributed
work under MPL-2.0; it does not imply COVESA review, endorsement, or
acceptance of this SysML v2 rendering.

Publisher namespace: `de4sdv` on `sysand.com`, created as an organization and
reviewed by Sysand staff before it becomes publishable. Releases are made
with an account API token held by the maintainer; automated releases should
later move to trusted publishing from CI.

## Consequences

- Any Sysand client can install the library with
  `sysand add de4sdv/covesa-vss-sysmlv2`, making downstream use and external
  review practical.
- Every published version is permanent. Regenerating the library from a new
  pinned VSS commit therefore requires a new version number, an updated
  changelog entry, and a fresh review before upload.
- The `de4sdv` namespace must exist and be approved on `sysand.com` before
  the first upload; organization approval is not instant.
- DE4SDV candidate extensions remain repository-internal and are excluded
  from the package by design.
- The package remains a draft redistribution of upstream source material, not
  a validated normative dependency; registry validation is supporting
  evidence only.

## Publication procedure

```bash
cd textual-notation-of-model/libraries/covesa-vss-sysmlv2
sysand build --update-meta
sysand publish --index https://sysand.com
```

Verify after upload that `https://sysand.com/projects/de4sdv/covesa-vss-sysmlv2/`
renders the intended version, README, changelog, and license.

## Validation

- Repository checks and smoke test pass on the packaging change.
- `COVESA_VSS.sysml` is byte-identical to the version already validated in
  earlier model PRs; no new SysML validation claim is introduced by this
  packaging change.
- Sysand Index performs its own `.kpar` archive validation at upload time and
  rejects invalid packages.
