# Model views

This directory holds DE4SDV publication views generated from the live SysML v2
model repository.

The Markdown files in this repository should embed stable image paths from this
directory. A sync pipeline should update the generated images and manifests when
the SysML v2 repository changes, then open a draft pull request for review.

## Pilot views

- [`system-context`](system-context/) — context view for the ASELCM System 1,
  System 2, and System 3 framing.
- [`lifecycle-engineering-system`](lifecycle-engineering-system/) — focused view
  of DE4SDV as the System 2 life-cycle engineering and assurance system.

## Generated artifact rule

Files named `*.svg`, `*.png`, and `manifest.json` in each view directory are
publication artifacts. Do not hand-edit them except during an explicitly marked
bootstrap placeholder step.

The intended steady-state update path is:

```text
SysML v2 repository commit
  -> view renderer
  -> SVG/PNG + manifest
  -> GitHub draft pull request
```

## View definition rule

`view.yaml` captures DE4SDV viewpoint intent: purpose, source model slice,
expected renderer, and Markdown embedding targets. These files are reviewable
project assets and may be edited through normal pull requests.
