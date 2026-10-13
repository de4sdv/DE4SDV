"""Historical verification is independent of current-source generated outputs."""
import json

from scripts.verify_generated_chain import verify_generated_chain
from tests.test_verify_generated_chain import (
    FROZEN_O1,
    FROZEN_O1_NOTE,
    FROZEN_O2,
    FROZEN_O3,
    _frozen_fixture,
    _manifest_path,
)


def test_live_outputs_are_not_historical_revision_evidence(tmp_path):
    root, _, _ = _frozen_fixture(tmp_path)
    live = root / "docs/method-conformance/o4/definition-projection.json"
    live.parent.mkdir(parents=True, exist_ok=True)
    live.write_text(json.dumps({"binding": {"source_revision": "f" * 40}}))

    report = verify_generated_chain(root, include_passing=True)
    expected = {FROZEN_O1, FROZEN_O1_NOTE, FROZEN_O2, FROZEN_O3, _manifest_path()}
    assert len(expected) == 5
    assert {entry["artifact"] for entry in report} == expected
    assert all(entry["ok"] for entry in report), report
