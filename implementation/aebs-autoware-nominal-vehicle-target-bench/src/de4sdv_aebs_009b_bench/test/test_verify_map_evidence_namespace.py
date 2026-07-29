import importlib.util
import sys
from pathlib import Path

import pytest

BENCH = Path(__file__).parents[3]


def _module():
    path = BENCH / "scripts/verify_map.py"
    sys.path.insert(0, str(path.parent))
    try:
        spec = importlib.util.spec_from_file_location("verify_map_under_test", path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(path.parent))


def test_map_evidence_write_is_confined_to_explicit_increment_namespace(tmp_path):
    module = _module()
    bench = tmp_path / "bench"
    output_009d = bench / "evidence/009d/profiles/control/runs/run/map-runtime.json"
    output_009d.parent.mkdir(parents=True)

    module.atomic_evidence_write(output_009d, {"status": "ok"}, bench, "009d")
    assert output_009d.is_file()

    output_009b = bench / "evidence/009b/map-runtime.json"
    output_009b.parent.mkdir(parents=True)
    with pytest.raises(ValueError, match="009d evidence"):
        module.atomic_evidence_write(output_009b, {"status": "wrong namespace"}, bench, "009d")


def test_map_evidence_namespace_is_closed_and_rejects_symlink_escape(tmp_path):
    module = _module()
    bench = tmp_path / "bench"
    evidence = bench / "evidence"
    evidence.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()

    with pytest.raises(ValueError, match="unsupported map evidence namespace"):
        module.atomic_evidence_write(evidence / "custom/map-runtime.json", {}, bench, "custom")

    (evidence / "009d").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        module.atomic_evidence_write(evidence / "009d/map-runtime.json", {}, bench, "009d")
