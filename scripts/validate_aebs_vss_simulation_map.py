#!/usr/bin/env python3
"""Validate the AEBS VSS-to-simulation realization map."""

from __future__ import annotations

from collections import Counter


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
