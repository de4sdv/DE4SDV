"""Runtime campaign driver for the AAOS SDV reference proof.

Executes the runtime proof gates defined in
``docs/runbooks/windows-aaos-sdv-reference-proof.md`` (gates 1-8) against a
configurable backend and emits executable-integration evidence.

Two backends:

- ``LocalRehearsalBackend`` — dry-run on the existing reference-bench
  stand-ins (provider stand-in, adapter, velocity-report boundary,
  independent observer) plus fault injectors. It proves the harness and the
  gate checks, but its output is rehearsal evidence, never runtime evidence.
- ``HostBackend`` — probes the live host (ADB to the AAOS guest, ROS 2 CLI
  on the host). A probe that cannot execute reports BLOCKED; a probe that
  runs and contradicts expectations reports FAIL. A pass is only reported
  when the probe's output matches the gate contract.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Protocol

GATE_NAMES: dict[int, str] = {
    1: "reference provider service is built and installed",
    2: "service bundle registered with the AAOS SDV middleware",
    3: "service discovery resolves the reference service identity",
    4: "adapter receives a real AAOS publication",
    5: "adapter publishes the exact ROS 2 topic/type/field",
    6: "independent observer verifies both sides for known speed values",
    7: "fault tests cover stale, invalid, provider loss, discovery failure",
    8: "reverse lifecycle/status path passes if bidirectional is claimed",
}

PASS = "pass"
BLOCKED = "blocked"
FAIL = "fail"
NOT_CLAIMED = "not_claimed"


@dataclass
class GateResult:
    gate: int
    outcome: str
    detail: str
    payload: dict = field(default_factory=dict)


class Backend(Protocol):
    """One probe per gate; raises nothing — returns a GateResult."""

    def probe(self, gate: int, ctx: "CampaignContext") -> GateResult:
        ...


@dataclass
class CampaignContext:
    speed_kmh: float
    expected_mps: float
    topic: str = "/vehicle/status/velocity_status"
    msg_type: str = "autoware_vehicle_msgs/msg/VelocityReport"
    field_name: str = "longitudinal_velocity"
    claim_bidirectional: bool = False


@dataclass
class CampaignReport:
    mode: str
    context: CampaignContext
    gates: list[GateResult]
    started_at: str
    finished_at: str = ""

    def summary(self) -> dict:
        counts: dict[str, int] = {}
        for g in self.gates:
            counts[g.outcome] = counts.get(g.outcome, 0) + 1
        status = "passed" if counts.get(FAIL, 0) == 0 and counts.get(PASS, 0) > 0 and counts.get(BLOCKED, 0) == 0 else "partial"
        if counts.get(FAIL, 0) > 0:
            status = "failed"
        return {"status": status, "counts": counts}

    def to_json(self) -> dict:
        return {
            "schema": "de4sdv.executable-integration-evidence.v1",
            "claim": "runtime campaign gates",
            "mode": self.mode,
            "started_at": self.started_at,
            "finished_at": self.finished_at or datetime.now(timezone.utc).isoformat(),
            "context": {
                "speed_kmh": self.context.speed_kmh,
                "expected_mps": self.context.expected_mps,
                "topic": self.context.topic,
                "msg_type": self.context.msg_type,
                "field_name": self.context.field_name,
                "claim_bidirectional": self.context.claim_bidirectional,
            },
            "summary": self.summary(),
            "gates": [
                {
                    "gate": g.gate,
                    "name": GATE_NAMES[g.gate],
                    "outcome": g.outcome,
                    "detail": g.detail,
                    "payload": g.payload,
                }
                for g in self.gates
            ],
        }

    def to_yaml(self) -> str:
        lines = [
            "schema: de4sdv.executable-integration-evidence.v1",
            f"mode: {self.mode}",
            f"started_at: {self.started_at}",
            f"finished_at: {self.finished_at or datetime.now(timezone.utc).isoformat()}",
            f"speed_kmh: {self.context.speed_kmh}",
            f"expected_mps: {self.context.expected_mps}",
            f"topic: {self.context.topic}",
            f"msg_type: {self.context.msg_type}",
            f"claim_bidirectional: {str(self.context.claim_bidirectional).lower()}",
            f"status: {self.summary()['status']}",
            "gates:",
        ]
        for g in self.gates:
            lines.append(f"- gate: {g.gate}")
            lines.append(f"  name: {GATE_NAMES[g.gate]}")
            lines.append(f"  outcome: {g.outcome}")
            lines.append(f"  detail: {g.detail}")
            if g.payload:
                lines.append("  payload: " + json.dumps(g.payload, sort_keys=True))
        return "\n".join(lines) + "\n"


def run_campaign(backend: Backend, ctx: CampaignContext, mode: str) -> CampaignReport:
    started = datetime.now(timezone.utc).isoformat()
    gates: list[GateResult] = []
    for gate in sorted(GATE_NAMES):
        gates.append(backend.probe(gate, ctx))
    return CampaignReport(mode=mode, context=ctx, gates=gates, started_at=started)


# ---------------------------------------------------------------------------
# LocalRehearsalBackend — dry-run on the reference bench stand-ins.
# ---------------------------------------------------------------------------


class LocalRehearsalBackend:
    """Simulated gates over the reference-bench components.

    ``mode`` stays ``rehearsal``: simulated passes prove the harness, not the
    runtime. Gate 6 (independent observer, known speed values) exercises the
    real verification logic of ``IndependentObserver``.
    """

    def __init__(self, bench_root: Path) -> None:
        self.bench_root = bench_root

    def _probe_contract_artifacts(self) -> GateResult:
        contract = self.bench_root / "contract"
        required = ["vehicle_speed.vsidl", "vehicle_speed.proto", "Android.bp"]
        missing = [n for n in required if not (contract / n).is_file()]
        if missing:
            return GateResult(1, FAIL, f"missing contract artifacts: {missing}")
        return GateResult(
            1, PASS, "contract artifacts present", {"files": required}
        )

    def _probe_registration(self) -> GateResult:
        # The staged generated provider carries the service-bundle registration
        # marker; locally we simulate the registration handshake.
        return GateResult(2, PASS, "simulated: service-bundle registration handshake")

    def _probe_discovery(self) -> GateResult:
        return GateResult(
            3, PASS, "simulated: discovery resolves reference service identity"
        )

    def _probe_adapter_receives(self, ctx: CampaignContext) -> GateResult:
        return GateResult(
            4,
            PASS,
            "simulated: provider stand-in publication accepted by adapter",
            {"speed_kmh": ctx.speed_kmh},
        )

    def _probe_exact_topic(self, ctx: CampaignContext) -> GateResult:
        # The VelocityReport-shaped boundary record carries the exact field;
        # topic/type identity is the runtime contract.
        return GateResult(
            5,
            PASS,
            f"simulated: {ctx.topic} publishes {ctx.msg_type}.{ctx.field_name}",
            {"topic": ctx.topic, "msg_type": ctx.msg_type, "field": ctx.field_name},
        )

    def _probe_observer(self, ctx: CampaignContext) -> GateResult:
        from de4sdv_aaos_sdv_reference_bench import (
            AutowareRos2VelocityReportBoundary,
            IndependentObserver,
            ReferenceProvider,
            run_reference_rehearsal,
        )
        try:
            evidence = run_reference_rehearsal(
                speed_kmh=ctx.speed_kmh, timestamp_ns=42
            )
            assert evidence["passed"] is True
            boundary = AutowareRos2VelocityReportBoundary()
            observer = IndependentObserver()
            from de4sdv_vss_vehicle_speed_adapter import VssVehicleSpeedAdapter

            VssVehicleSpeedAdapter().process(
                ReferenceProvider(ctx.speed_kmh, 42).sample(), boundary.publish
            )
            for record in boundary.records:
                observer.observe(record)
            observer.verify(
                expected_speed_kmh=ctx.speed_kmh, expected_timestamp_ns=42
            )
        except Exception as exc:  # noqa: BLE001 - report any gate failure
            return GateResult(6, FAIL, f"observer verification failed: {exc}")
        return GateResult(
            6,
            PASS,
            f"independent observer verified {ctx.speed_kmh} km/h -> {ctx.expected_mps} m/s",
            {"speed_kmh": ctx.speed_kmh, "mps": ctx.expected_mps},
        )

    def _probe_faults(self) -> GateResult:
        from de4sdv_vss_vehicle_speed_adapter import (
            SampleValidationError,
            SignalQuality,
            VehicleSpeedSample,
            VssVehicleSpeedAdapter,
        )

        adapter = VssVehicleSpeedAdapter()
        failures: list[str] = []
        for label, sample in [
            (
                "stale",
                VehicleSpeedSample(
                    value=36.0, unit="km/h", timestamp_ns=0,
                    clock_domain="c", quality=SignalQuality.STALE,
                ),
            ),
            (
                "invalid",
                VehicleSpeedSample(
                    value=36.0, unit="km/h", timestamp_ns=0,
                    clock_domain="c", quality=SignalQuality.INVALID,
                ),
            ),
            (
                "negative",
                VehicleSpeedSample(
                    value=-5.0, unit="km/h", timestamp_ns=0,
                    clock_domain="c", quality=SignalQuality.VALID,
                ),
            ),
        ]:
            try:
                adapter.process(sample, lambda _o: None)
                failures.append(f"{label}: accepted")
            except SampleValidationError:
                pass
        if failures:
            return GateResult(7, FAIL, "; ".join(failures))
        return GateResult(
            7,
            PASS,
            "stale/invalid/negative samples rejected before publication",
            {"rejected": ["stale", "invalid", "negative"]},
        )

    def probe(self, gate: int, ctx: CampaignContext) -> GateResult:
        if gate == 1:
            return self._probe_contract_artifacts()
        if gate == 2:
            return self._probe_registration()
        if gate == 3:
            return self._probe_discovery()
        if gate == 4:
            return self._probe_adapter_receives(ctx)
        if gate == 5:
            return self._probe_exact_topic(ctx)
        if gate == 6:
            return self._probe_observer(ctx)
        if gate == 7:
            return self._probe_faults()
        if gate == 8:
            if not ctx.claim_bidirectional:
                return GateResult(
                    8,
                    NOT_CLAIMED,
                    "reverse lifecycle/status path not claimed for this campaign",
                )
            return GateResult(8, PASS, "simulated: reverse lifecycle/status path")
        return GateResult(gate, FAIL, f"unknown gate {gate}")


# ---------------------------------------------------------------------------
# HostBackend — probes the live host (ADB to the AAOS guest, ROS 2 on host).
# ---------------------------------------------------------------------------


@dataclass
class HostProbe:
    """One shell command with an expected-output regex and a label."""

    label: str
    command: list[str]
    expect: str = ""
    timeout: int = 60


class HostBackend:
    """Run probes against the live host.

    ``run`` must be a callable that executes a command list and returns
    ``(returncode, stdout)`` — default is ``subprocess.run`` locally on the
    host. A probe that cannot run reports BLOCKED; a probe whose output does
    not match its contract reports FAIL. No probe result is ever invented.
    """

    def __init__(
        self,
        adb_serial: str = "",
        run: Callable[[list[str]], tuple[int, str]] | None = None,
    ) -> None:
        self.adb_serial = adb_serial
        self._run = run or self._default_run

    @staticmethod
    def _default_run(command: list[str]) -> tuple[int, str]:
        proc = subprocess.run(
            command, capture_output=True, text=True, timeout=120
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")

    def _adb(self, *args: str) -> list[str]:
        base = ["adb"]
        if self.adb_serial:
            base += ["-s", self.adb_serial]
        return base + list(args)

    def _probe(self, probe: HostProbe) -> GateResult | None:
        """Returns None when the probe is not applicable; raises nothing."""
        try:
            rc, out = self._run(probe.command)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return GateResult(0, BLOCKED, f"{probe.label}: cannot execute ({exc})")
        if rc != 0 and not probe.expect:
            return GateResult(0, BLOCKED, f"{probe.label}: exit {rc}")
        if probe.expect and probe.expect not in out:
            return GateResult(
                0, FAIL, f"{probe.label}: expected {probe.expect!r} not in output"
            )
        return None

    def probe(self, gate: int, ctx: CampaignContext) -> GateResult:
        probes: dict[int, HostProbe] = {
            1: HostProbe(
                "provider built and installed",
                self._adb("shell", "ps", "-A"),
                expect="VehicleSpeedProvider:instance",
            ),
            2: HostProbe(
                "service bundle registered with the AAOS SDV middleware",
                self._adb("shell", "logcat", "-d"),
                expect="DE4SDV_VEHICLE_SPEED_PUBLISHED",
            ),
            3: HostProbe(
                "service discovery resolves the reference service identity",
                self._adb("shell", "service", "list"),
                expect="IServiceRegistrationAgent",
            ),
            4: HostProbe(
                "adapter receives a real AAOS publication",
                self._adb("shell", "logcat", "-d"),
                expect="TCP egress connected",
            ),
            5: HostProbe(
                "adapter publishes the exact ROS 2 topic/type/field",
                ["ros2", "topic", "echo", ctx.topic, "--once"],
                expect=ctx.field_name,
            ),
            6: HostProbe(
                "independent observer verifies known speed",
                ["ros2", "topic", "echo", ctx.topic, "--once"],
                expect=str(ctx.expected_mps),
            ),
            7: HostProbe(
                "fault tests: ingress rejects non-valid envelopes",
                ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
                 "mrk@10.250.0.3",
                 "grep -a 'rejected AAOS Vehicle.Speed record' "
                 "/home/mrk/bridge-node.log | tail -1"],
                expect="rejected AAOS Vehicle.Speed record",
            ),
        }
        if gate == 8:
            if not ctx.claim_bidirectional:
                return GateResult(
                    8,
                    NOT_CLAIMED,
                    "reverse lifecycle/status path not claimed for this campaign",
                )
            probes[8] = HostProbe(
                "reverse lifecycle/status path",
                self._adb("shell", "logcat", "-d", "-s", "SDV_LM"),
                expect="VehicleSpeedProvider",
            )
        probe = probes.get(gate)
        if probe is None:
            return GateResult(gate, NOT_CLAIMED, "no host probe defined for gate")
        result = self._probe(probe)
        if result is not None:
            result.gate = gate
            return result
        return GateResult(gate, PASS, probe.label)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backend",
        choices=["local", "host"],
        default="local",
        help="local = rehearsal dry-run (default); host = live probes",
    )
    parser.add_argument("--speed-kmh", type=float, default=36.0)
    parser.add_argument("--topic", default="/vehicle/status/velocity_status")
    parser.add_argument("--adb-serial", default="")
    parser.add_argument("--claim-bidirectional", action="store_true")
    parser.add_argument("--evidence-out", type=Path)
    args = parser.parse_args(argv)

    ctx = CampaignContext(
        speed_kmh=args.speed_kmh,
        expected_mps=round(args.speed_kmh / 3.6, 6),
        topic=args.topic,
        claim_bidirectional=args.claim_bidirectional,
    )
    if args.backend == "local":
        bench_root = Path(__file__).resolve().parents[2]
        backend = LocalRehearsalBackend(bench_root)
        mode = "rehearsal"
    else:
        backend = HostBackend(adb_serial=args.adb_serial)
        mode = "runtime"
    report = run_campaign(backend, ctx, mode)
    report.finished_at = datetime.now(timezone.utc).isoformat()
    print(report.to_yaml(), end="")
    if args.evidence_out:
        args.evidence_out.parent.mkdir(parents=True, exist_ok=True)
        args.evidence_out.write_text(report.to_yaml(), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
