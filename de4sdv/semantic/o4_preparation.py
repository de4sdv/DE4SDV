"""Offline O4 preparation accounting. Never grants authority or closure."""
from __future__ import annotations


class PreparationError(ValueError):
    """Malformed or incomplete preparation evidence."""


def unique_index(rows: list[dict], source: str) -> dict[str, dict]:
    """Reject malformed/duplicate identities before constructing an index."""
    result = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("identity"), str) or not row["identity"]:
            raise PreparationError(f"{source}: missing identity")
        identity = row["identity"]
        if identity in result:
            raise PreparationError(f"{source}: duplicate identity {identity}")
        result[identity] = row
    return result


def build_accounting(register: list[dict], inventory: list[dict], migrated: set[str],
                     projection: set[str], profile: set[str], grounding: set[str]) -> dict:
    """Account for output coverage separately from recorded treatment and retirement.

    Inputs must have passed their own canonical generator checks. This function
    validates joins and frozen scope; it never upgrades an evidence state.
    """
    reg = unique_index(register, "register")
    inv = unique_index(inventory, "inventory")
    if set(reg) != set(inv):
        raise PreparationError("inventory identity set differs from register")
    frozen = {n for n, r in reg.items() if r.get("o3_complete") is True}
    if frozen != migrated:
        raise PreparationError("frozen O3 set differs from MIGRATED_IDENTITIES")
    outputs = projection | profile | grounding
    if outputs - set(reg):
        raise PreparationError(f"unknown output identities: {sorted(outputs - set(reg))}")
    rows = []
    waves = {}
    for name, row in reg.items():
        reviewed = inv[name]["reviewed"]
        membership = row["membership"]
        if membership not in {"o3-complete", "o4-target", "merged", "removed"}:
            raise PreparationError(f"unknown membership: {name}")
        if (membership == "o3-complete") != (name in frozen):
            raise PreparationError(f"frozen membership mismatch: {name}")
        item = {
            "identity": name, "membership": membership,
            "wave": row.get("base_wave"), "held": row.get("gate_wave") == "W7",
            "recorded_stage": reviewed.get("stage"),
            "authority_current": reviewed.get("authority_current"),
            "remaining_evidence": reviewed.get("required_evidence", []),
            "projection_output": name in projection,
            "profile_output": name in profile, "grounding_record": name in grounding,
            "retirement_proven": False,
        }
        rows.append(item)
        if membership != "o4-target":
            continue
        wave = waves.setdefault(row["base_wave"], {
            "targets": [], "held": [], "projection_outputs": [], "profile_outputs": [],
            "grounding_records": [], "recorded_treatment": [],
        })
        wave["targets"].append(name)
        for flag, bucket in [(item["held"], "held"), (name in projection, "projection_outputs"),
                             (name in profile, "profile_outputs"), (name in grounding, "grounding_records")]:
            if flag:
                wave[bucket].append(name)
        # Stage is an explicit governance label, not inferred completion.
        if str(reviewed.get("stage", "")).startswith("o4-"):
            wave["recorded_treatment"].append(name)
    for wave in waves.values():
        for values in wave.values():
            values.sort()
    return {"schema": "de4sdv.o4-preparation-accounting/v1", "closure_proven": False,
            "warning": "Coverage and recorded treatment are not authority retirement or closure.",
            "frozen_o3": sorted(frozen), "waves": waves, "rows": rows}
