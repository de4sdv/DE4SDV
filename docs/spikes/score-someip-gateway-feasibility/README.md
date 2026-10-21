# Spike: does the S-CORE SOME/IP gateway carry our cross-domain path?

Throwaway feasibility spike for INC-MW-011. It lives only on the branch
`spike/score-someip-gateway-feasibility` and never merges.

## Question

The owner decided on 2026-10-21 to replace the DE4SDV host relay of the
phase-8 model with the Eclipse S-CORE SOME/IP gateway, "if it actually works".
This spike answers that condition with executed evidence for our case: an
opaque, length-prefixed AEBS signal frame of at most 2048 bytes, offered as an
`mw::com` event on the host, carried by `gatewayd` and `someipd` as one SOME/IP
event (one service, one event, no method) to a COVESA vsomeip 3.7.6 client in a
separate network domain.

## What runs

The workflow `.github/workflows/spike-score-someip-gateway-feasibility.yml`
runs three jobs on GitHub-hosted `ubuntu-24.04` (x86_64) runners:

- `upstream-tests`: the gateway's own unit and component tests on an untouched
  checkout of `eclipse-score/inc_someip_gateway` at `951fbc09`.
- `qemu-integration`: its Linux QEMU integration and TC8 tests.
- `cross-domain`: the gateway daemons, the null serializer and the spike's
  publisher, built with Bazel from `.bazelversion`, plus vsomeip 3.7.6 and the
  client built with CMake; then the scenarios of `scripts/xdomain.py` in two
  network namespaces joined by one veth pair, and `scripts/analyze.py`.

## Layout

- `overlay/de4sdv_spike/`: the Bazel package added to the gateway checkout
  (new files only). The publisher follows the gateway's own pre-serialized
  echo server pattern.
- `config/`: the `mw::com` manifests, the gateway configuration, and the
  vsomeip configurations of the two domains.
- `client/`: the vsomeip 3.7.6 client of the guest domain.
- `scripts/`: runner preparation, builds, the scenario orchestrator, the
  capture reader and the analysis.
- `tests/`: local tests of the analysis tooling.

## Non-claims

This is draft, not-yet-validated evidence from a throwaway bench. A network
namespace is not the AAOS SDV guest under KVM, and the client does not re-serve
the INC-AEBS-010 ingress. Nothing here is a safety, cybersecurity or compliance
claim.
