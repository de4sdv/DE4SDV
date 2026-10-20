"""Tests for the repository-wide SysIDE validation wrapper."""

import io
import unittest
from pathlib import Path
from unittest import mock

from scripts import validate_sysml


class TestValidateSysML(unittest.TestCase):
    def test_checks_all_model_roots_together(self):
        completed = mock.Mock(returncode=0)

        with (
            mock.patch.object(validate_sysml.shutil, "which", return_value="/usr/bin/syside"),
            mock.patch.object(validate_sysml.subprocess, "run", return_value=completed) as run,
            mock.patch("sys.stdout", new_callable=io.StringIO),
        ):
            self.assertEqual(validate_sysml.main(), 0)

        run.assert_called_once_with(
            [
                "/usr/bin/syside",
                "check",
                "textual-notation-of-model",
                "model-based-product-line-engineering/product-models",
                "model-based-product-line-engineering/scoping",
                "model-based-product-line-engineering/feature-models",
                "model-based-product-line-engineering/feature-configurations",
                "--exclude",
                "**/fixtures/**",
            ],
            cwd=Path(validate_sysml.__file__).resolve().parents[1],
        )

    def test_lists_the_model_files_without_the_fixtures(self):
        """The invalid configuration and the parity probes are no production model
        files; the privileged PLE authority workflow validates them."""
        root = Path(validate_sysml.__file__).resolve().parents[1]
        configurations = Path("model-based-product-line-engineering/feature-configurations")
        listed = [path.relative_to(root).as_posix()
                  for path in validate_sysml.model_files(root, configurations)]
        fixtures = sorted((root / configurations / "fixtures").rglob("*.sysml"))
        self.assertEqual(len(fixtures), 18)
        self.assertEqual(len(listed), 7)
        self.assertFalse([path for path in listed if "/fixtures/" in path])

    def test_propagates_syside_failure(self):
        completed = mock.Mock(returncode=7)

        with (
            mock.patch.object(validate_sysml.shutil, "which", return_value="/usr/bin/syside"),
            mock.patch.object(validate_sysml.subprocess, "run", return_value=completed),
            mock.patch("sys.stdout", new_callable=io.StringIO),
        ):
            self.assertEqual(validate_sysml.main(), 7)

    def test_fails_when_an_expected_model_root_has_no_sysml(self):
        with (
            mock.patch.object(
                validate_sysml,
                "MODEL_PATHS",
                (Path("textual-notation-of-model"), Path("missing-product-models")),
            ),
            mock.patch.object(validate_sysml.shutil, "which") as which,
            mock.patch("sys.stderr", new_callable=io.StringIO) as stderr,
        ):
            self.assertEqual(validate_sysml.main(), 1)

        which.assert_not_called()
        self.assertIn("missing-product-models", stderr.getvalue())

    def test_fails_when_syside_is_unavailable(self):
        with (
            mock.patch.object(validate_sysml.shutil, "which", return_value=None),
            mock.patch("sys.stderr", new_callable=io.StringIO) as stderr,
        ):
            self.assertEqual(validate_sysml.main(), 1)

        self.assertIn("was not found on PATH", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
