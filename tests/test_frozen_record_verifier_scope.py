"""Historical verification is independent of current-source generated outputs."""
import json

from scripts.verify_generated_chain import verify_generated_chain
from tests.test_verify_generated_chain import (  # noqa: F401 (``synthetic_frozen_records`` is a fixture)
    FROZEN_A,
    FROZEN_B,
    FROZEN_NOTE,
    MANIFEST,
    _frozen_fixture,
    synthetic_frozen_records,
)


def test_live_outputs_are_not_historical_revision_evidence(synthetic_frozen_records, tmp_path):
    root, _, _ = _frozen_fixture(tmp_path)
    live = root / "live/definition-projection.json"
    live.parent.mkdir(parents=True, exist_ok=True)
    live.write_text(json.dumps({"binding": {"source_revision": "f" * 40}}))

    report = verify_generated_chain(root, include_passing=True)
    expected = {FROZEN_A, FROZEN_B, FROZEN_NOTE, MANIFEST}
    assert len(expected) == 4
    assert {entry["artifact"] for entry in report} == expected
    assert all(entry["ok"] for entry in report), report
