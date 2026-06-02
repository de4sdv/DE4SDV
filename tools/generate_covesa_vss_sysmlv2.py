#!/usr/bin/env python3
"""Generate the draft COVESA VSS SysML v2 library.

Usage:
    python tools/generate_covesa_vss_sysmlv2.py /path/to/vehicle_signal_specification

The input path must point to a clone of:
https://github.com/COVESA/vehicle_signal_specification

This script intentionally maps VSS unit tokens to SysML v2 standard
quantity/unit references and does not import VSS `units.yaml` or
`quantities.yaml`.
"""

from __future__ import annotations

from pathlib import Path
import argparse
import re
import subprocess

import yaml


UNIT_MAP: dict[str, tuple[str, str]] = {
    "A": ("ISQ::electricCurrent", "SI::ampere"),
    "Ah": ("ISQ::electricCharge", "SI::ampereHour"),
    "Celsius": ("ISQ::thermodynamicTemperature", "SI::degreeCelsius"),
    "N": ("ISQ::force", "SI::newton"),
    "Nm": ("ISQ::momentOfForce", "SI::newtonMetre"),
    "Pa": ("ISQ::pressure", "SI::pascal"),
    "kPa": ("ISQ::pressure", "SI::kilopascal"),
    "V": ("ISQ::electricPotential", "SI::volt"),
    "W": ("ISQ::power", "SI::watt"),
    "kW": ("ISQ::power", "SI::kilowatt"),
    "bpm": ("ISQ::frequency", "SI-derived beats/minute"),
    "cpm": ("ISQ::frequency", "SI-derived cycles/minute"),
    "cm^3": ("ISQ::volume", "SI::cubicCentimetre"),
    "degrees": ("ISQ::planeAngle", "SI::degree"),
    "degrees/s": ("ISQ::angularVelocity", "SI::degreePerSecond"),
    "g/km": ("ISQ::linearDensity", "SI-derived gram/kilometre"),
    "g/s": ("ISQ::massFlowRate", "SI::gramPerSecond"),
    "h": ("ISQ::time", "SI::hour"),
    "inch": ("ISQ::length", "USCustomaryUnits::inch"),
    "iso8601": ("n/a", "ISO 8601 lexical date/time string"),
    "kWh": ("ISQ::energy", "SI::kilowattHour"),
    "kWh/100km": ("ISQ::energyPerDistance", "SI-derived kilowattHourPer100Kilometre"),
    "kg": ("ISQ::mass", "SI::kilogram"),
    "km": ("ISQ::length", "SI::kilometre"),
    "km/h": ("ISQ::speed", "SI::kilometrePerHour"),
    "km/l": ("ISQ::fuelEfficiency", "SI-derived kilometre/litre"),
    "l": ("ISQ::volume", "SI::litre"),
    "l/100km": ("ISQ::fuelConsumption", "SI-derived litrePer100Kilometre"),
    "m": ("ISQ::length", "SI::metre"),
    "m/s^2": ("ISQ::acceleration", "SI::metrePerSecondSquared"),
    "mm": ("ISQ::length", "SI::millimetre"),
    "ms": ("ISQ::time", "SI::millisecond"),
    "percent": ("ISQ::dimensionless", "SI::percent"),
    "rad/s": ("ISQ::angularVelocity", "SI::radianPerSecond"),
    "rpm": ("ISQ::angularVelocity", "SI-derived revolutionPerMinute"),
    "s": ("ISQ::time", "SI::second"),
}


def add_prefix(name: str, prefix: str | None) -> str:
    if not prefix:
        return name
    if name == prefix or name.startswith(prefix + "."):
        return name
    return f"{prefix}.{name}" if name else prefix


def resolve_include(spec_root: Path, base_file: str, include_path: str) -> str:
    candidate = (Path(base_file).parent / include_path).as_posix()
    if (spec_root / candidate).exists():
        return candidate
    return Path(include_path).as_posix()


def load_vspec(spec_root: Path, rel_path: str, prefix: str | None = None) -> dict[str, dict]:
    text = (spec_root / rel_path).read_text(encoding="utf-8")
    data = yaml.safe_load(text) or {}
    items: dict[str, dict] = {}
    if isinstance(data, dict):
        for key, value in data.items():
            items[add_prefix(str(key), prefix)] = value or {}

    include_re = re.compile(r"^#include[^\S\r\n]+(\S+)(?:[^\S\r\n]+(\S+))?[^\S\r\n]*$", re.M)
    for match in include_re.finditer(text):
        include_file = resolve_include(spec_root, rel_path, match.group(1))
        include_prefix = add_prefix(match.group(2) or "", prefix)
        items.update(load_vspec(spec_root, include_file, include_prefix))
    return items


def sysml_identifier(path: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", path)


def sysml_scalar_type(vss_datatype: str) -> str:
    if vss_datatype == "boolean":
        return "Boolean"
    if vss_datatype in {"string", "string[]"}:
        return "String"
    if vss_datatype in {"float", "double", "float[]"}:
        return "Real"
    if re.fullmatch(r"u?int(8|16|32|64)", vss_datatype or ""):
        return "Integer"
    return "ScalarValues::ScalarValue"


def compact(value: object) -> str:
    return " ".join(str(value or "").split())


def git_commit(repo: Path) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def generate(vss_repo: Path, output: Path) -> tuple[int, int, str]:
    spec_root = vss_repo / "spec"
    items = load_vspec(spec_root, "VehicleSignalSpecification.vspec")
    branches = {key: value for key, value in items.items() if value.get("type") == "branch"}
    leaves = {key: value for key, value in items.items() if value.get("type") != "branch"}
    commit = git_commit(vss_repo)

    lines: list[str] = [
        "/*",
        " * SPDX-License-Identifier: MPL-2.0",
        " * Generated SysML v2 textual library for COVESA Vehicle Signal Specification (VSS).",
        f" * Source: https://github.com/COVESA/vehicle_signal_specification/tree/{commit}/spec",
        " * Scope: leaf VSS attributes, sensors, and actuators reachable from spec/VehicleSignalSpecification.vspec.",
        " * Unit policy: VSS unit/quantity YAML files are not imported; unit references below point to SysML v2 standard",
        " * quantity/unit libraries (ISQ/SI/USCustomaryUnits) or derived expressions over those libraries.",
        " */",
        "",
        "package COVESA_VSS {",
        "",
        "import ScalarValues::*;",
        "import ISQ::*;",
        "import SI::*;",
        "import USCustomaryUnits::*;",
        "",
        "package SignalDefinitions {",
    ]

    for path in sorted(leaves):
        value = leaves[path]
        unit = value.get("unit", "")
        quantity_ref, unit_ref = UNIT_MAP.get(unit, ("", "")) if unit else ("", "")
        lines.append(f"  /* VSS path: {path}")
        lines.append(f"   * VSS kind: {value.get('type', 'unspecified')}")
        lines.append(f"   * VSS datatype: {value.get('datatype', 'unspecified')}")
        if unit:
            lines.append(f"   * Standard quantity reference: {quantity_ref}")
            lines.append(f"   * Standard unit reference: {unit_ref}")
        if compact(value.get("description")):
            lines.append(f"   * Description: {compact(value.get('description'))}")
        if compact(value.get("comment")):
            lines.append(f"   * Comment: {compact(value.get('comment'))}")
        if "allowed" in value:
            lines.append(f"   * Allowed values: {value['allowed']}")
        if "min" in value or "max" in value:
            lines.append(f"   * Value range: min={value.get('min', '')}, max={value.get('max', '')}")
        lines.append("   */")
        lines.append(f"  attribute def {sysml_identifier(path)} : {sysml_scalar_type(value.get('datatype', ''))};")
        lines.append("")

    lines.extend(["}", "", "package BranchDefinitions {"])
    for path in sorted(branches):
        suffix = f" — {compact(branches[path].get('description'))}" if compact(branches[path].get("description")) else ""
        lines.append(f"  /* VSS branch: {path}{suffix} */")
        lines.append(f"  part def {sysml_identifier(path)};")
    lines.extend([
        "}",
        "",
        "package SignalPathIndex {",
        "  /* Human-readable aliases for SysML-safe signal definition names. */",
    ])
    for path in sorted(leaves):
        safe = sysml_identifier(path)
        lines.append(f"  alias {safe} for SignalDefinitions::{safe};")
    lines.extend(["}", "", "}"])

    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(leaves), len(branches), commit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("vss_repo", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("textual-notation-of-model/libraries/covesa-vss-sysmlv2/COVESA_VSS.sysml"),
    )
    args = parser.parse_args()
    leaves, branches, commit = generate(args.vss_repo, args.output)
    print(f"Generated {leaves} leaf definitions and {branches} branch definitions from {commit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
