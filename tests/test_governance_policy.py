import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


class TestGovernancePolicy(unittest.TestCase):
    def test_generic_issue_form_covers_every_contribution_lane_and_size(self) -> None:
        form = yaml.safe_load(
            (
                ROOT
                / ".github"
                / "ISSUE_TEMPLATE"
                / "question-contribution.yml"
            ).read_text(encoding="utf-8")
        )
        fields = {item.get("id"): item for item in form["body"] if item.get("id")}
        self.assertEqual(
            {
                "unsure",
                "docs",
                "modeling",
                "simulation",
                "methodology",
                "traceability",
                "compliance",
                "devsecops",
                "community",
            },
            set(fields["lane"]["attributes"]["options"]),
        )
        self.assertEqual(
            {"not applicable (question)", "XS", "S", "M", "L"},
            set(fields["size"]["attributes"]["options"]),
        )

    def test_code_ownership_routes_to_the_live_administrator_identity(self) -> None:
        codeowners = (ROOT / ".github" / "CODEOWNERS").read_text(encoding="utf-8")
        self.assertIn("* @de4sdv", codeowners)
        self.assertNotIn("@orkunyilmaz", codeowners.lower())

    def test_governance_keeps_independent_review_normal_and_bypass_exceptional(self) -> None:
        governance = (ROOT / "GOVERNANCE.md").read_text(encoding="utf-8")
        self.assertIn('who is **not the author** reviews and approves', governance)
        self.assertIn("Exceptional administrator merges (temporary)", governance)
        self.assertIn("must not be used to bypass disagreement", governance)

    def test_support_uses_the_enabled_discussions_channel(self) -> None:
        support = (ROOT / "SUPPORT.md").read_text(encoding="utf-8")
        self.assertIn("Discussions are enabled", support)
        self.assertNotIn("once enabled", support)


if __name__ == "__main__":
    unittest.main()
