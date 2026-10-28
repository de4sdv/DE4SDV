# Spike: does the S-CORE SOME/IP gateway carry our cross-domain path?

Throwaway feasibility spike for INC-MW-011. The first run lives on the branch
`spike/score-someip-gateway-feasibility`, the rerun of 2026-10-27 on the branch
`spike/score-someip-gateway-rerun-348`. Neither branch merges.

## Question

The owner decided on 2026-10-21 to replace the DE4SDV host relay of the
phase-8 model with the Eclipse S-CORE SOME/IP gateway, "if it actually works".
This spike answers that condition with executed evidence for our case: an
opaque, length-prefixed AEBS signal frame of at most 2048 bytes, offered as an
`mw::com` event on the host, carried by `gatewayd` and `someipd` as one SOME/IP
event (one service, one event, no method) to a COVESA vsomeip 3.7.6 client in a
separate network domain.

## What runs

The first run (`.github/workflows/spike-score-someip-gateway-feasibility.yml` on
the first branch) ran three jobs on GitHub-hosted `ubuntu-24.04` (x86_64)
runners, all at `eclipse-score/inc_someip_gateway` `951fbc09`:

- `upstream-tests`: the gateway's own unit and component tests on an untouched
  checkout.
- `qemu-integration`: its Linux QEMU integration and TC8 tests.
- `cross-domain`: the gateway daemons, the null serializer and the spike's
  publisher, built with Bazel from `.bazelversion`, plus vsomeip 3.7.6 and the
  client built with CMake; then the scenarios of `scripts/xdomain.py` in two
  network namespaces joined by one veth pair, and `scripts/analyze.py`.

## Rerun after #348 (2026-10-27)

The rerun (`.github/workflows/spike-score-someip-gateway-rerun-348.yml`) runs
only the `cross-domain` job, once per pin:

- `main-a4dce403`: inc_someip_gateway main at `a4dce403`, which includes #348.
  Both daemons still use the `message_passing` IPC binding there.
- `pr375-723119c4`: the head of the open PR #375, which switches both daemons
  to the `mw::com` IPC binding. someipd then takes only an `mw::com` manifest
  (`-s`, `config/mw_com_config_someipd.json`), and gatewayd's manifest adds the
  `SomeipdService` entry (`config/mw_com_config_gatewayd*_mwcom.json`).

`paths.json` names the binding of the pin (`ipc_binding`), and `xdomain.py`
uses it for the command lines, the manifests and the log lines it waits for.
Two scenario changes follow from #375:

- `s05-late-gatewayd`: someipd offers the SOME/IP service only after gatewayd
  sent its configuration, so at the #375 pin the guest subscribes after
  gatewayd connected, not before gatewayd started. gatewayd still subscribes
  to the publisher late.
- `s18-start-order-spawn-only` (new, both pins): the start order of the
  Launch Manager rule, someipd, then gatewayd, then the publisher, each 100 ms
  after the previous spawn, with the publisher sending from its offer on.

The `analyze.py` summaries of the s04 family, s07 and s15 now say what the
first run's summaries hid: the s04 family and s15 count the events with wrong
bytes after the restart as well as the correct ones, s15 also counts the
samples of the first publisher instance that arrive after the restart, and s07
ignores vsomeip's initial availability callback.

## Rerun at d9eac670 (2026-10-28)

PR #375 merged on 2026-10-27 as inc_someip_gateway main `d9eac670`. Its
sources equal the tested PR head `723119c4`. Only `MODULE.bazel`
(score_baselibs 0.2.15 to 0.2.16, and three development or documentation
dependencies), `MODULE.bazel.lock` and two socom unit tests differ.
`.bazelversion` stays 8.6.0. The workflow
`.github/workflows/spike-score-someip-gateway-rerun-d9eac670.yml` on the
branch `spike/score-someip-gateway-d9eac670` runs the same scenarios with the
mw::com IPC binding, twice, on two runners (`main-d9eac670-r1`,
`main-d9eac670-r2`), so the results compare one to one with the two earlier
runs per pin. It changes no scenario, script, overlay or configuration. It
adds one measurement step that records the disk and memory use after the
build.

## Layout

- `overlay/de4sdv_spike/`: the Bazel package added to the gateway checkout
  (new files only). The publisher follows the gateway's own pre-serialized
  echo server pattern.
- `config/`: the `mw::com` manifests, the gateway configuration, and the
  vsomeip configurations of the two domains.
- `client/`: the vsomeip 3.7.6 client of the guest domain.
- `scripts/`: runner preparation, builds, the scenario orchestrator, the
  capture reader and the analysis.
- `tests/`: local tests of the analysis tooling, and a dry run of the
  orchestrator with stand-in processes (`run_local_dry_run.sh <out> [scenarios]
  [message_passing|mw_com]`).

Comments in the files use our internal IDs (INC-MW-011, REQ-MW-019, phase 8).
They do not change what the scripts do.

## Non-claims

This is draft, not-yet-validated evidence from a throwaway bench. A network
namespace is not the AAOS SDV guest under KVM, and the client does not re-serve
the INC-AEBS-010 ingress. PR #375 is open and can change before it merges.
Nothing here is a safety, cybersecurity or compliance claim.
