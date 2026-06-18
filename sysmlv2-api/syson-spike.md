# SysON DE4SDV round-trip spike

## Project

- SysON URL: <http://localhost:8080>
- SysON version/image: `eclipsesyson/syson:v2026.5.0`
- SysON project name: `DE4SDV`
- SysON project ID: `e71112e1-978f-4372-9f48-14857768fb08`
- SysON editing context ID: `87bfdce0-4794-40b3-a05a-40e3175ea50b`

## Source slice

- Source file: `textual-notation-of-model/snapshots/de4sdv-context-spike.sysml`
- Scope: minimal context and engineering-assets slice for the GUI round-trip
  spike.
- Naming correction made during the spike:
  - `DE4SDV_LifecycleEngineeringSystem` was renamed to
    `LifecycleEngineeringSystem`.
  - `DE4SDV_OpenInnovationEcosystem` was renamed to
    `OpenInnovationEcosystem`.
  - The package formerly named `LifecycleEngineeringSystem` was renamed to
    `EngineeringAssets` to avoid a package/part-definition naming collision.

## Import result

- Command:

  ```bash
  python scripts/syson_exchange.py \
    --url http://localhost:8080 \
    import-document e71112e1-978f-4372-9f48-14857768fb08 \
    textual-notation-of-model/snapshots/de4sdv-context-spike.sysml
  ```

- Import succeeded: yes
- SysON upload operation ID: `bbfb6cdd-e338-4354-8d45-a04bb4fddcb2`
- SysON document ID observed in the backing database:
  `8c397141-fed6-4e24-9cc7-ca3b799d8f33`
- Import report: empty string
- Visible elements in UI: confirmed manually during view creation

## View creation and SVG export

Two SysON General Views were created and exported manually as SVG:

- `system-context`
  - Representation ID: `f7aad90b-c396-4784-988a-5b28cca3eb16`
  - Representation metadata ID:
    `87bfdce0-4794-40b3-a05a-40e3175ea50b#f7aad90b-c396-4784-988a-5b28cca3eb16`
  - Exported file:
    `textual-notation-of-model/views/system-context/system-context.svg`

- `lifecycle-engineering-system`
  - Representation ID: `4c6023fd-2c8b-4e13-b90c-9b1e85606802`
  - Representation metadata ID:
    `87bfdce0-4794-40b3-a05a-40e3175ea50b#4c6023fd-2c8b-4e13-b90c-9b1e85606802`
  - Exported file:
    `textual-notation-of-model/views/lifecycle-engineering-system/lifecycle-engineering-system.svg`

The exported SVG files replaced the prior bootstrap placeholders.

## Relationship-palette finding

SysON General View exposed a limited relationship palette for this slice. During
this spike, only dependency-style links were usable for the intended context
relations.

- `New Subclassification` was intentionally not used because the modeled
  elements are not specializations of one another.
- `New Dependency` was used as a lightweight visual relationship.
- Dependency labels describe intent only; they should not be treated as final
  containment, allocation, or formal product-line semantics.

Labels used in the views include:

- `governs / evolves`
- `engineers / assures`
- `manages model baselines`
- `executes validation`
- `maintains assurance evidence`

## Textual export/download result

The current helper could not download the imported document through its assumed
HTTP endpoint:

```bash
python scripts/syson_exchange.py \
  --url http://localhost:8080 \
  download-document e71112e1-978f-4372-9f48-14857768fb08 \
  8c397141-fed6-4e24-9cc7-ca3b799d8f33 \
  textual-notation-of-model/snapshots/de4sdv-context-syson-export.sysml
```

Result:

```text
error: Download HTTP 404:
```

The document row and content are present in SysON's backing database. The
public/download route used by the helper is not correct for this SysON release.
This is a spike finding: document ID discovery and textual export/download need
an updated GraphQL or REST path before automation can claim round-trip support.

## Validation result

Local validation is blocked on this ARM64 host. The repository wrapper attempted
to run the x86_64 SysIDE CLI and failed with:

```text
qemu-x86_64: Could not open '/lib64/ld-linux-x86-64.so.2': No such file or directory
```

The spike model is therefore an unvalidated draft until checked with a working
SysIDE validation environment.

## Interim assessment

SysON is viable for manual GUI view creation and SVG export in this minimal
DE4SDV slice. The automation story is not complete yet: textual import works,
representation discovery works, but textual export/download through the helper
is still unresolved.
