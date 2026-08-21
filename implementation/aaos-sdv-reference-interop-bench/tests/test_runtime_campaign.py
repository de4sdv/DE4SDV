from pathlib import Path
import sys

import pytest

BENCH = Path(__file__).parents[1]
sys.path.insert(0, str(BENCH / "src"))
sys.path.insert(0, str(BENCH.parents[0] / "vss-vehicle-speed-adapter" / "src"))

from de4sdv_aaos_sdv_reference_bench import (  # noqa: E402
    CampaignContext,
    HostBackend,
    LocalRehearsalBackend,
    run_campaign,
)
from de4sdv_aaos_sdv_reference_bench.runtime_campaign import (  # noqa: E402
    BLOCKED,
    FAIL,
    GATE_NAMES,
    NOT_CLAIMED,
    PASS,
)


def _ctx(**kw) -> CampaignContext:
    kw.setdefault("speed_kmh", 36.0)
    kw.setdefault("expected_mps", 10.0)
    return CampaignContext(**kw)


def test_local_campaign_all_gates_report():
    backend = LocalRehearsalBackend(BENCH)
    report = run_campaign(backend, _ctx(), mode="rehearsal")

    assert len(report.gates) == len(GATE_NAMES) == 8
    outcomes = {g.outcome for g in report.gates}
    assert outcomes <= {PASS, NOT_CLAIMED}
    # gates 1-7 pass in rehearsal; gate 8 unclaimed by default
    assert report.summary()["counts"][PASS] == 7
    assert report.summary()["counts"][NOT_CLAIMED] == 1
    # gate 8 is conditional (bidirectional claim); NOT_CLAIMED does not
    # block a passed campaign for what was claimed
    assert report.summary()["status"] == "passed"


def test_local_campaign_observer_gate_verifies_known_speed():
    backend = LocalRehearsalBackend(BENCH)
    report = run_campaign(backend, _ctx(speed_kmh=72.0, expected_mps=20.0), "rehearsal")
    gate6 = next(g for g in report.gates if g.gate == 6)
    assert gate6.outcome == PASS
    assert "72.0 km/h -> 20.0 m/s" in gate6.detail
    assert gate6.payload == {"speed_kmh": 72.0, "mps": 20.0}


def test_local_campaign_fault_gate_rejects_bad_samples():
    backend = LocalRehearsalBackend(BENCH)
    report = run_campaign(backend, _ctx(), "rehearsal")
    gate7 = next(g for g in report.gates if g.gate == 7)
    assert gate7.outcome == PASS
    assert gate7.payload["rejected"] == ["stale", "invalid", "negative"]


def test_claim_bidirectional_enables_gate8():
    backend = LocalRehearsalBackend(BENCH)
    report = run_campaign(
        backend, _ctx(claim_bidirectional=True), "rehearsal"
    )
    gate8 = next(g for g in report.gates if g.gate == 8)
    assert gate8.outcome == PASS


def test_evidence_yaml_and_json_consistent():
    backend = LocalRehearsalBackend(BENCH)
    report = run_campaign(backend, _ctx(), "rehearsal")
    report.finished_at = "2026-08-19T00:00:00+00:00"

    data = report.to_json()
    assert data["schema"] == "de4sdv.executable-integration-evidence.v1"
    assert data["mode"] == "rehearsal"
    assert len(data["gates"]) == 8
    assert data["gates"][0]["name"] == GATE_NAMES[1]

    yaml_text = report.to_yaml()
    assert "schema: de4sdv.executable-integration-evidence.v1" in yaml_text
    assert "mode: rehearsal" in yaml_text
    assert "- gate: 8" in yaml_text
    assert "outcome: not_claimed" in yaml_text


def test_host_backend_blocked_when_command_missing():
    def run(_cmd):
        raise OSError("no such tool")

    backend = HostBackend(run=run)
    report = run_campaign(backend, _ctx(), "runtime")
    # every host probe that cannot execute reports BLOCKED, never FAIL/PASS
    assert all(g.outcome == BLOCKED for g in report.gates[:5])
    assert report.summary()["status"] == "partial"


def test_host_backend_fail_when_contract_missing():
    calls = []

    def run(cmd):
        calls.append(cmd)
        if cmd[0] == "ros2":
            return 0, "nothing"
        return 0, "no logs"

    backend = HostBackend(run=run)
    report = run_campaign(backend, _ctx(), "runtime")
    # gate 5 expects the field name in the topic echo -> FAIL
    gate5 = next(g for g in report.gates if g.gate == 5)
    assert gate5.outcome == FAIL
    assert report.summary()["status"] == "failed"


def test_host_backend_pass_when_contract_matches():
    def run(cmd):
        if cmd[0] == "ros2":
            return 0, "longitudinal_velocity: 10.0"
        if cmd[0] == "ssh":
            return 0, "rejected AAOS Vehicle.Speed record: bad keys"
        if "ps" in cmd:
            return 0, "VehicleSpeedProvider:instance"
        if "service" in cmd:
            return 0, "IServiceRegistrationAgent/default"
        if "logcat" in cmd:
            return 0, "DE4SDV_VEHICLE_SPEED_PUBLISHED speed_kmh=36 TCP egress connected"
        if cmd[0] == "grep":
            return 0, "DE4SDV_ADB_LOGCAT_FORWARD_ACCEPTED count=1"
        return 0, ""

    backend = HostBackend(run=run)
    report = run_campaign(backend, _ctx(), "runtime")
    assert report.summary()["counts"][PASS] == 7
    assert report.summary()["status"] == "passed"  # gate 8 unclaimed
