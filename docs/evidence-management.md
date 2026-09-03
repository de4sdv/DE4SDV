# Evidence Management

Evidence exists to support a bounded engineering claim. A file is not evidence
merely because it is stored under an `evidence/` directory.

## What may be tracked in Git

Track an artifact only when all of these are true:

- it supports a named requirement, verification case, acceptance criterion, or
  explicit engineering decision;
- its producer, capture method, source revision, capture time, and claim status
  are recorded;
- a reviewer can interpret it without an undocumented local environment;
- it is small, diffable or independently inspectable, and needed for review.

Machine-readable observations, logs, dispositions, checksum manifests, and
small load-bearing still images are preferred. A still image must identify the
state or acceptance point it demonstrates. Decorative, transient, duplicated,
or obsolete screenshots are documentation material or cleanup candidates, not
technical evidence.

## What stays outside Git

Video, audio, large binary captures, and other non-diffable recordings belong
in a controlled external artifact store. The repository keeps a manifest with:

- the former or logical artifact name;
- a cryptographic checksum and byte count;
- capture time and source revision;
- owner, access/location status, and retention status;
- the bounded claim and evidence disposition;
- links to the correlated machine-readable records retained in Git.

A missing external location must be written as `not_available`, never implied by
a filename. A locally held maintainer archive is not public evidence.

## Invalid and empty artifacts

Delete media that has no provenance, no acceptance relationship, misleading or
superseded semantics, or no maintained reviewer use. Preserve its disposition
and checksum only when the correction history remains relevant.

A zero-byte file is not evidence. The only exception is a manifest-declared
sentinel whose empty content has a defined machine meaning. Empty command or
journal output should be represented as structured status (`records: 0`, exit
code, command/filter, and timestamp), not as an unexplained empty log.

## Claim boundary

Repository presence proves only that an artifact is controlled at a revision.
It does not prove runtime behavior, safety, compliance, certification, or
acceptance. Those claims require the corresponding verification logic and an
honest disposition such as `observed_bounded` or `deferred_not_proven`.

## Project metadata is not evidence

The root `.meta.json` is Sysand source-package metadata used to build the model
archive. Empty source checksum values are populated in the generated archive by
`sysand build`; the source file is retained and is not an evidence manifest.
