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
    import yaml

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


def enum_type_name(path: str) -> str:
    return f"{sysml_identifier(path)}_AllowedValue"


def enum_literal_name(value: object) -> str:
    literal = re.sub(r"[^A-Za-z0-9_]", "_", compact(value)).strip("_")
    literal = re.sub(r"_+", "_", literal)
    if not literal:
        literal = "VALUE"
    if not re.match(r"[A-Za-z_]", literal):
        literal = f"V_{literal}"
    return literal


def allowed_values(value: dict) -> list[object]:
    allowed = value.get("allowed") or []
    if not isinstance(allowed, list):
        allowed = [allowed]
    return allowed


def enum_definition_block(path: str, allowed: list[object]) -> list[str]:
    lines = [f"  enum def {enum_type_name(path)} {{"]
    used: dict[str, int] = {}
    for item in allowed:
        literal = enum_literal_name(item)
        count = used.get(literal, 0)
        used[literal] = count + 1
        if count:
            literal = f"{literal}_{count + 1}"
        lines.append(f"    {literal};")
    lines.append("  }")
    return lines


def has_allowed_values(value: dict) -> bool:
    return bool(allowed_values(value))


def sysml_type(path: str, value: dict) -> str:
    if has_allowed_values(value):
        return enum_type_name(path)
    return sysml_scalar_type(value.get("datatype", ""))


def datatype_token(vss_datatype: str) -> str:
    return vss_datatype or "unspecified"


def kind_token(vss_kind: str) -> str:
    return vss_kind or "unspecified"


def compact(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def sysml_string(value: object) -> str:
    text = compact(value)
    return '"' + text.replace('\\', '\\\\').replace('"', '\\"') + '"'


def doc_block(text: str, indent: str = "    ") -> list[str]:
    if not text:
        return []
    return [f"{indent}doc /* {text.replace('*/', '* /')} */"]


def metadata_block(value: dict, path: str, safe_name: str, quantity_ref: str, unit_ref: str) -> list[str]:
    about = safe_name
    lines = [
        f"  @VssSignalMetadata about {about} {{",
        f"    path = {sysml_string(path)};",
        f"    kind = {sysml_string(kind_token(value.get('type', 'unspecified')))};",
        f"    datatype = {sysml_string(datatype_token(value.get('datatype', '')))};",
        f"    sourceDescription = {sysml_string(value.get('description', ''))};",
        f"    sourceComment = {sysml_string(value.get('comment', ''))};",
        "  }",
    ]
    if quantity_ref or unit_ref:
        lines.extend([
            f"  @VssQuantityMetadata about {about} {{",
            f"    quantityReference = {sysml_string(quantity_ref)};",
            f"    unitReference = {sysml_string(unit_ref)};",
            "  }",
        ])
    if "min" in value or "max" in value:
        lines.extend([
            f"  @VssRangeMetadata about {about} {{",
            f"    minValue = {sysml_string(value.get('min', ''))};",
            f"    maxValue = {sysml_string(value.get('max', ''))};",
            "  }",
        ])
    if "allowed" in value:
        allowed = allowed_values(value)
        lines.extend([
            f"  @VssAllowedValuesMetadata about {about} {{",
            f"    allowedValues = {sysml_string(', '.join(str(item) for item in allowed))};",
            "  }",
        ])
    return lines


def git_commit(repo: Path) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def metadata_definitions() -> list[str]:
    return [
        "package MetadataDefinitions {",
        "  metadata def VssSignalMetadata :> SemanticMetadata {",
        "    ref :>> annotatedElement : SysML::AttributeDefinition;",
        "    attribute path : String;",
        "    attribute kind : String;",
        "    attribute datatype : String;",
        "    attribute sourceDescription : String;",
        "    attribute sourceComment : String;",
        "  }",
        "",
        "  metadata def VssQuantityMetadata :> SemanticMetadata {",
        "    ref :>> annotatedElement : SysML::AttributeDefinition;",
        "    attribute quantityReference : String;",
        "    attribute unitReference : String;",
        "  }",
        "",
        "  metadata def VssRangeMetadata :> SemanticMetadata {",
        "    ref :>> annotatedElement : SysML::AttributeDefinition;",
        "    attribute minValue : String;",
        "    attribute maxValue : String;",
        "  }",
        "",
        "  metadata def VssAllowedValuesMetadata :> SemanticMetadata {",
        "    ref :>> annotatedElement : SysML::AttributeDefinition;",
        "    attribute allowedValues : String;",
        "  }",
        "}",
        "",
    ]


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
        " * Semantics policy: VSS path, kind, datatype, description, comment, quantity/unit, range, and allowed-value",
        " * fields are promoted into SysML metadata annotations instead of being kept only in comments.",
        " */",
        "",
        "package COVESA_VSS {",
        "",
        "private import ScalarValues::*;",
        "private import ISQ::*;",
        "private import SI::*;",
        "private import USCustomaryUnits::*;",
        "private import Metaobjects::SemanticMetadata;",
        "",
    ]
    lines.extend(metadata_definitions())
    lines.extend([
        "package AllowedValueDefinitions {",
    ])
    for path in sorted(leaves):
        value = leaves[path]
        allowed = allowed_values(value)
        if allowed:
            lines.extend(enum_definition_block(path, allowed))
            lines.append("")
    lines.extend([
        "}",
        "",
        "package SignalDefinitions {",
        "  private import COVESA_VSS::MetadataDefinitions::*;",
        "  private import COVESA_VSS::AllowedValueDefinitions::*;",
        "",
    ])

    for path in sorted(leaves):
        value = leaves[path]
        unit = value.get("unit", "")
        quantity_ref, unit_ref = UNIT_MAP.get(unit, ("", "")) if unit else ("", "")
        safe = sysml_identifier(path)
        lines.append(f"  attribute def {safe} :> {sysml_type(path, value)};")
        lines.extend(metadata_block(value, path, safe, quantity_ref, unit_ref))
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
