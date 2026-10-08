"""Retired O3 authority-bundle machinery: frozen identity list only.

O4 Wave C2 deleted the O3 bundle, its facade, its verification and its
selector (they required the retired authored ontology). This module name
survives only because the O2+ generator (``projection_o2p.py``, a bound input
of the live O2+ projection pair, which C2 does not regenerate) imports the
frozen O3-migrated identity list from it. The list itself lives in
:mod:`de4sdv.semantic.model_contract` (the frozen O2-chain layer); nothing
here is runtime authority.
"""
from __future__ import annotations

from .model_contract import (
    O2_CHAIN_CLASSES as MIGRATED_CLASSES,
    O2_CHAIN_IDENTITIES as MIGRATED_IDENTITIES,
    O2_CHAIN_RELATIONSHIPS as MIGRATED_RELATIONSHIPS,
)

__all__ = ["MIGRATED_CLASSES", "MIGRATED_IDENTITIES", "MIGRATED_RELATIONSHIPS"]
