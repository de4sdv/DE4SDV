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

The package retains the pinned COVESA source release (`v6.0`, commit
`20c609bf95c73b51d483fb8f81a099d1d5b73066`) in its README and changelog as
source provenance. Publication is a redistribution of a derived, attributed
work under MPL-2.0; it does not imply COVESA review, endorsement, or
acceptance of this SysML v2 rendering.

Publisher namespace: the `de4sdv` user namespace on `sysand.com` (maintainer
account `de4sdv`). Releases are made with an account API token held by the
maintainer; automated releases should later move to trusted publishing from
CI. If the project later adopts an organization namespace, that is a new,
separate project on the index — namespaces cannot be migrated.

## Consequences

- Any Sysand client can install the library with
  `sysand add de4sdv/covesa-vss-sysmlv2`, making downstream use and external
  review practical.
- Every published version is permanent. Regenerating the library from a new
  pinned VSS commit therefore requires a new version number, an updated
  changelog entry, and a fresh review before upload.
- The `de4sdv` user namespace exists on `sysand.com` (maintainer account
  registered as `de4sdv`); the first upload requires only an account API
  token.
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
