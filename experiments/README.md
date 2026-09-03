# Experiments

Use this directory for controlled experiments that evaluate a specific
engineering question and end with a decision: adopt, reject, or defer.

Name each folder with an ISO 8601 date followed by a short description. Every
experiment must record:

- the engineering question and owner;
- start date and planned expiry or review date;
- method, inputs, source revision, and observations;
- result, decision, and follow-up issue, if any.

Experiments without an owner, decision, or review date are stale and should be
closed or removed. Canonical video/audio recordings and large binary captures
stay outside Git; retain only the checksum, byte count, provenance, access
status, and bounded disposition in an artifact manifest. See
[`Evidence Management`](../docs/evidence-management.md).

The 2026-08-11 BaLUS-to-SysIDE experiment retains three contextual stills. Its
uncontrolled video was removed and recorded in `artifact-manifest.yaml`.
