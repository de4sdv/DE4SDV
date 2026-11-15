# SBOMs for the two images

The committed CycloneDX inventories are licence/component inventories, not
permission to distribute an image. See [`versions.md`](../versions.md) for the
component and distribution boundaries.

## Generate and verify

From the repository root, with the declared check dependencies installed and
`syft` available on the machine that can resolve the private testbed images:

```bash
sh de4sdv-virtual-ee/checks/make_sbom.sh
python3 de4sdv-virtual-ee/checks/sbom_inventory.py check
```

The generator resolves `zone-ecu` and `can-gw` from
[`parts.yaml`](../vehicle/parts.yaml), checks their digests against
[`vxp.lock`](../vehicle/vxp.lock), and scans those **immutable references**. It
has no mutable-tag defaults or image override environment variables.

Both CycloneDX and Syft's native source metadata are produced by the same scan.
The generator rejects a source whose manifest digest or requested reference does
not match the baseline. `inventory.json` retains the scanner version, manifest
digest, image/config ID, architecture, OS, component count and SHA-256 of each
compressed CycloneDX file. Raw image config and environment are not retained.
Both scans must succeed before either previous inventory is replaced.

The offline check verifies the exact current baseline, source binding and file
hashes. It does not rescan image contents, provide a signed attestation, audit
licence detection, or establish compliance.

## Historical inventories

The pair originally committed with this increment described `zone-ecu:10`
(5,427 components) and `can-gw:4` (3,474 components). That zone inventory predates
the service-plane baseline's zone image 11 and is **not** an inventory of that
later image. Those original counts must not be quoted for a new baseline.
A current acceptance claim requires regenerated inventories and a passing
`sbom_inventory.py check`; a missing `inventory.json` deliberately fails.

GPL/LGPL components are present, including distribution tools and `python-can`.
No distinction between Python imports and separate programs eliminates the
applicable component's obligations. An SBOM answers an inventory question; it
does not, by itself, answer whether the exact image may be published.
