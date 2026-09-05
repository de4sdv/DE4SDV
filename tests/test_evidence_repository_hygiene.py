import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = (
    ROOT
    / "implementation"
    / "aebs-aaos-sdv-visualization-bench"
    / "evidence"
    / "010"
)
RETENTION_MANIFEST = EVIDENCE_ROOT / "external-media.yaml"


class TestEvidenceRepositoryHygiene(unittest.TestCase):
    def test_video_bytes_are_not_tracked_in_repository_tree(self) -> None:
        videos = sorted(
            path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*.mp4")
        )
        self.assertEqual([], videos)

    def test_evidence_files_are_not_empty_placeholders(self) -> None:
        observed = {
            path
            for path in EVIDENCE_ROOT.rglob("*")
            if path.is_file() and path.stat().st_size == 0
        }
        self.assertEqual(set(), observed)

    def test_removed_media_manifest_has_complete_identity(self) -> None:
        manifest = yaml.safe_load(RETENTION_MANIFEST.read_text(encoding="utf-8"))
        artifacts = manifest["artifacts"]
        self.assertEqual(15, len(artifacts))
        self.assertEqual(15, len({entry["former_path"] for entry in artifacts}))
        for entry in artifacts:
            self.assertRegex(entry["sha256"], r"^[0-9a-f]{64}$")
            self.assertGreater(entry["bytes"], 0)
            self.assertIn("disposition", entry)
            self.assertIn("availability", entry)
            self.assertFalse((EVIDENCE_ROOT / entry["former_path"]).exists())


if __name__ == "__main__":
    unittest.main()
