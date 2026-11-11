#!/usr/bin/env python3
"""Validate the AEBS VSS-to-simulation realization map."""

from __future__ import annotations

import re
from collections import Counter

# The generated COVESA VSS library states the commit it was generated from in its header.
_LIBRARY_SOURCE_COMMIT = re.compile(
    r"^ \* Source: https://github\.com/COVESA/vehicle_signal_specification/tree/([0-9a-f]{40})/spec$",
    re.MULTILINE,
)
# A signal's VSS path is the first field of its signal metadata.
_SIGNAL_PATH = re.compile(r'@VssSignalMetadata\s+about\s+\w+\s*\{\s*path\s*=\s*"([^"]+)"\s*;')
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)


def validate_source_baseline(realization: dict, library_text: str) -> list[str]:
    """Return an error when the map's COVESA VSS commit is not the library's source commit."""
    stated = _LIBRARY_SOURCE_COMMIT.findall(library_text)
    if len(stated) != 1:
        return [f"library states {len(stated)} source commits, expected 1"]
    commit = realization["source_baselines"]["covesa_vss"]["commit"]
    if commit != stated[0]:
        return [f"covesa_vss commit {commit} is not the library's source commit {stated[0]}"]
    return []


def validate_vss_paths(realization: dict, library_text: str, extensions_text: str) -> list[str]:
    """Return an error for each mapped VSS path that the library of its origin does not declare."""
    declared = {
        "covesa": set(_SIGNAL_PATH.findall(_BLOCK_COMMENT.sub("", library_text))),
        "de4sdv_candidate": set(_SIGNAL_PATH.findall(_BLOCK_COMMENT.sub("", extensions_text))),
    }
    errors = []
    for entry in realization["mappings"]:
        origin = entry.get("vss_origin")
        if origin not in declared:
            errors.append(f"unknown vss_origin: {entry['id']} -> {origin}")
        elif entry["vss_path"] not in declared[origin]:
            errors.append(f"vss_path is not a signal of the {origin} library: {entry['id']} -> {entry['vss_path']}")
    return errors


def validate_mapping(functional: dict, realization: dict) -> list[str]:
    """Return validation errors for a functional catalog and realization map."""
    expected_counts = Counter(
        (entry["item"], entry["attribute"], entry["vss_path"])
        for entry in functional["signal_classification"]
    )
    actual_counts = Counter(
        (
            entry["functional_item"],
            entry["functional_attribute"],
            entry["vss_path"],
        )
        for entry in realization["mappings"]
    )
    expected = set(expected_counts)
    actual = set(actual_counts)
    errors = [
        f"missing mapping: {item}.{attribute} -> {vss_path}"
        for item, attribute, vss_path in sorted(expected - actual)
    ]
    errors.extend(
        f"extra mapping: {item}.{attribute} -> {vss_path}"
        for item, attribute, vss_path in sorted(actual - expected)
    )
    errors.extend(
        f"duplicate functional trace: {item}.{attribute} -> {vss_path} ({count} occurrences)"
        for (item, attribute, vss_path), count in sorted(expected_counts.items())
        if count > 1
    )
    errors.extend(
        f"duplicate mapping trace: {item}.{attribute} -> {vss_path} ({count} occurrences)"
        for (item, attribute, vss_path), count in sorted(actual_counts.items())
        if count > 1
    )
    id_counts = Counter(entry["id"] for entry in realization["mappings"])
    errors.extend(
        f"duplicate mapping id: {mapping_id}"
        for mapping_id, count in sorted(id_counts.items())
        if count > 1
    )
    declared_kinds = set(realization["mapping_policy"]["mapping_kinds"])
    errors.extend(
        f"undeclared mapping kind: {entry['id']} -> {entry['mapping_kind']}"
        for entry in realization["mappings"]
        if entry["mapping_kind"] not in declared_kinds
    )
    return errors
