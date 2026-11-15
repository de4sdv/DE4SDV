"""Contract checks use independent synthetic metadata, not a live broker."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load_checker():
    spec = importlib.util.spec_from_file_location("parent_contract_checker", ROOT / "checks/check_contract.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def configure_checker(tmp_path, monkeypatch, *, status_extra=False, command_missing=False):
    import cantools

    checker = load_checker()
    db = cantools.database.Database()
    db.add_dbc_file(str(ROOT / "dbc/wiper.dbc"))
    mapping = json.loads((ROOT / "vss/mapping/wiper.json").read_text())
    if status_extra:
        signal = next(s for m in db.messages for s in m.signals if s.name == "Wiper_Mode_State")
        signal.choices[7] = "SERVICE"
    if command_missing:
        signal = next(s for m in db.messages for s in m.signals if s.name == "Wiper_Mode_Req")
        signal.choices.pop(3)
    monkeypatch.setattr(checker, "load_contract", lambda: (db, mapping))
    monkeypatch.setattr(checker, "DEFAULTS", ROOT / "dbc/dbc_default_values.json")
    return checker


def test_status_labels_outside_vss_allowed_are_rejected(tmp_path, monkeypatch):
    checker = configure_checker(tmp_path, monkeypatch, status_extra=True)
    assert checker.main() == 1, "a DBC status label not accepted by VSS must fail the contract"


def test_command_labels_missing_from_dbc_are_rejected(tmp_path, monkeypatch):
    checker = configure_checker(tmp_path, monkeypatch, command_missing=True)
    assert checker.main() == 1, "a VSS actuator value not encodable by the DBC must fail"
