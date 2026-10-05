# Retained Gate A PLEML baseline export

`de4sdv-pleml-gate-a-export.json.xz` is the historical Gate A serializer export
used as the comparison baseline by the privileged PLE qualification workflow
(`.github/workflows/privileged-ple-qualification.yml`).

## Why it is committed

The original provider artifact expired on 2026-10-01, and the producing
pull-request run cannot be re-run. Without a retained copy, every
qualification run refuses at its origin step (run 37364717183). This file is
a byte-exact, compressed copy of the export from that artifact. It is not a
regenerated or edited baseline.

## Pinned identity

See `manifest.json`. The workflow refuses to run unless all of these hold:

- the compressed file's SHA-256 matches the manifest;
- the decompressed export's SHA-256 matches the manifest (the export digest
  recorded when the artifact was archived while still live);
- the export's `git_commit` is the frozen Gate A head;
- the original producing run still reports the recorded identity
  (`33543909037`, `pull_request`, success, frozen head, Gate A workflow).

## Status

Historical evidence input only. It does not qualify or adopt PLEML, change
the PLEML pin, or change configurator authority.
