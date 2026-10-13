"""A failed export records why, for the method-check report (--diagnostics).

``scripts/export_sysml_api_baseline.py`` runs in the licensed job. With
``--diagnostics`` it writes, when it fails, its own refusal text verbatim
(Syside's model diagnostics included, with repository-relative paths) and any
other error by its type only: such a message comes from the toolchain, so it
stays in the job log and never reaches an artifact. A Syside stand-in replaces
the licensed package; no licence, no network.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts.export_sysml_api_baseline as exporter
from de4sdv.sysml_api.baseline import BaselineManifest, BaselineSource

GIT = "a" * 40
DIAGNOSTIC = (
    "textual-notation-of-model/packages/features/area/area_framing.sysml:122:5: error "
    "(requirement-usage-subject-parameter-position): Subject must be the first input parameter"
)


class _Diagnostics:
    def __init__(self, text: str) -> None:
        self.text = text

    def contains_errors(self, **_options) -> bool:
        return True

    def __str__(self) -> str:
        return self.text


def _stand_in(monkeypatch, root: Path, load) -> None:
    monkeypatch.setitem(sys.modules, "syside", SimpleNamespace(try_load_model=load))
    monkeypatch.setattr(exporter, "ROOT", root)
    monkeypatch.setattr(exporter, "_git_head", lambda: GIT)
    manifest = BaselineManifest((BaselineSource("model.sysml", "reviewed", "f" * 64, 1),))
    monkeypatch.setattr(BaselineManifest, "discover", lambda _root: manifest)


def _export(tmp_path: Path, *extra: str, commit: str = GIT) -> int:
    return exporter.main(["--git-commit", commit, "--output", str(tmp_path / "export.json"), *extra])


def test_a_syside_rejection_records_the_model_diagnostics(monkeypatch, tmp_path: Path) -> None:
    # Syside reports absolute paths of the runner's checkout; the record is repository-relative.
    _stand_in(monkeypatch, tmp_path, lambda paths: (None, _Diagnostics(f"{tmp_path}/{DIAGNOSTIC}")))
    diagnostics = tmp_path / "method-check-diagnostics" / "export-diagnostics.txt"
    with pytest.raises(exporter.ExportRefused, match="Syside rejected the reviewed baseline"):
        _export(tmp_path, "--diagnostics", str(diagnostics))
    assert diagnostics.read_text(encoding="utf-8") == (
        f"Syside rejected the reviewed baseline:\n{DIAGNOSTIC}\n"
    )
    assert not (tmp_path / "export.json").exists()


def test_the_licence_value_never_reaches_the_diagnostics(monkeypatch, tmp_path: Path) -> None:
    licence = "FAKE-LICENCE-0000-REVIEW"
    monkeypatch.setenv(exporter.LICENCE_VARIABLE, licence)
    _stand_in(monkeypatch, tmp_path, lambda paths: (None, _Diagnostics(f"licence {licence} rejected")))
    diagnostics = tmp_path / "export-diagnostics.txt"
    with pytest.raises(exporter.ExportRefused):
        _export(tmp_path, "--diagnostics", str(diagnostics))
    recorded = diagnostics.read_text(encoding="utf-8")
    assert licence not in recorded
    assert "licence *** rejected" in recorded


def test_a_refusal_before_the_model_loads_is_recorded(monkeypatch, tmp_path: Path) -> None:
    _stand_in(monkeypatch, tmp_path, lambda paths: pytest.fail("the model must not load"))
    diagnostics = tmp_path / "export-diagnostics.txt"
    with pytest.raises(exporter.ExportRefused, match="does not match checked-out HEAD"):
        _export(tmp_path, "--diagnostics", str(diagnostics), commit="b" * 40)
    assert f"requested Git commit {'b' * 40} does not match" in diagnostics.read_text(encoding="utf-8")


def test_any_other_error_is_recorded_by_its_type_only(monkeypatch, tmp_path: Path) -> None:
    def load(paths):
        raise ValueError("licence token 0123-not-for-artifacts was refused")

    _stand_in(monkeypatch, tmp_path, load)
    diagnostics = tmp_path / "export-diagnostics.txt"
    with pytest.raises(ValueError):
        _export(tmp_path, "--diagnostics", str(diagnostics))
    text = diagnostics.read_text(encoding="utf-8")
    assert "ValueError" in text and "job log" in text
    assert "0123" not in text and "licence token" not in text


def test_the_refusals_stay_runtime_errors_for_existing_callers() -> None:
    assert issubclass(exporter.ExportRefused, RuntimeError)


def test_nothing_is_recorded_on_success(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(exporter, "export_baseline", lambda output, git_commit: {"git_commit": git_commit})
    diagnostics = tmp_path / "export-diagnostics.txt"
    assert _export(tmp_path, "--diagnostics", str(diagnostics)) == 0
    assert not diagnostics.exists()


def test_the_environment_names_the_file_when_the_option_is_absent(monkeypatch, tmp_path: Path) -> None:
    # The Method Check passes the path this way: a head whose export script
    # predates the option ignores the variable and still exports.
    diagnostics = tmp_path / "from-environment.txt"
    monkeypatch.setenv(exporter.DIAGNOSTICS_VARIABLE, str(diagnostics))
    _stand_in(monkeypatch, tmp_path, lambda paths: (None, _Diagnostics(f"{tmp_path}/{DIAGNOSTIC}")))
    with pytest.raises(exporter.ExportRefused):
        _export(tmp_path)
    assert diagnostics.read_text(encoding="utf-8") == f"Syside rejected the reviewed baseline:\n{DIAGNOSTIC}\n"


def test_without_the_option_or_the_variable_a_failure_records_nothing(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv(exporter.DIAGNOSTICS_VARIABLE, raising=False)
    _stand_in(monkeypatch, tmp_path, lambda paths: (None, _Diagnostics(f"{tmp_path}/{DIAGNOSTIC}")))
    with pytest.raises(exporter.ExportRefused):
        _export(tmp_path)
    assert [path for path in tmp_path.rglob("*") if path.is_file()] == []
