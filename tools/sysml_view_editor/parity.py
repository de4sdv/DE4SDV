"""Parity gate for the DE4SDV view editor.

The parity gate is the contract between the authoritative SysML source and
any rendered artifact. A render is only acceptable when:

- the semantic graph contains exactly the expected roles, ports, and flows;
- every flow endpoint is an exact authoritative endpoint path;
- every payload type matches the expected set;
- no unexpected semantic elements were added by the tooling.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .graph import SemanticGraph


@dataclass
class ParityResult:
    passed: bool
    errors: list[str] = field(default_factory=list)

    def add(self, error: str) -> None:
        self.errors.append(error)
        self.passed = False


@dataclass
class ParityExpectation:
    """The expected semantic content of a view, hand-authored from the source."""

    roles: list[str]
    ports: list[str]
    flows: list[tuple[str, str]]
    payloads: list[str]


def check_parity(
    graph: SemanticGraph,
    expected: ParityExpectation,
) -> ParityResult:
    """Compare the extracted graph against the hand-authored expectation."""
    result = ParityResult(passed=True)

    actual_roles = set(graph.role_ids)
    expected_roles = set(expected.roles)
    if actual_roles != expected_roles:
        missing = sorted(expected_roles - actual_roles)
        extra = sorted(actual_roles - expected_roles)
        if missing:
            result.add(f"missing roles: {missing}")
        if extra:
            result.add(f"unexpected roles: {extra}")

    actual_ports = set(graph.port_ids)
    expected_ports = set(expected.ports)
    if actual_ports != expected_ports:
        missing = sorted(expected_ports - actual_ports)
        extra = sorted(actual_ports - expected_ports)
        if missing:
            result.add(f"missing ports: {missing}")
        if extra:
            result.add(f"unexpected ports: {extra}")

    actual_flows = {(f.source, f.target) for f in graph.flows}
    expected_flows = set(expected.flows)
    if actual_flows != expected_flows:
        missing = sorted(expected_flows - actual_flows)
        extra = sorted(actual_flows - expected_flows)
        if missing:
            result.add(f"missing flows: {missing}")
        if extra:
            result.add(f"unexpected flows: {extra}")

    actual_payloads = {f.payload for f in graph.flows}
    expected_payloads = set(expected.payloads)
    if actual_payloads != expected_payloads:
        result.add(
            f"payload mismatch: got {sorted(actual_payloads)}, "
            f"expected {sorted(expected_payloads)}"
        )

    return result
