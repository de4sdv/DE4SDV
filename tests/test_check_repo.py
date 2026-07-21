"""Tests for repository health checks."""

import tempfile
import unittest
from pathlib import Path

from scripts import check_repo


class TestCheckRepo(unittest.TestCase):
    def test_reports_duplicate_global_packages_across_model_roots(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "textual-notation-of-model" / "first.sysml"
            second = (
                root
                / "model-based-product-line-engineering"
                / "product-models"
                / "second.sysml"
            )
            first.parent.mkdir(parents=True)
            second.parent.mkdir(parents=True)
            first.write_text("package DuplicatePackage {\n}\n")
            second.write_text("package DuplicatePackage {\n}\n")

            self.assertEqual(
                check_repo.find_duplicate_global_packages(root),
                {
                    "DuplicatePackage": [
                        "textual-notation-of-model/first.sysml:1",
                        "model-based-product-line-engineering/product-models/second.sysml:1",
                    ]
                },
            )

    def test_ignores_nested_comment_and_string_package_text(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "textual-notation-of-model" / "first.sysml"
            second = root / "textual-notation-of-model" / "second.sysml"
            first.parent.mkdir(parents=True)
            first.write_text(
                "package ActualPackage {\n"
                "package NestedWithoutIndent {\n}\n"
                "}\n"
            )
            second.write_text(
                "/*\npackage ActualPackage {\n}\n*/\n"
                'doc "package ActualPackage { }"\n'
            )

            self.assertEqual(check_repo.find_duplicate_global_packages(root), {})

    def test_detects_multiline_and_same_line_global_packages(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "textual-notation-of-model" / "first.sysml"
            second = root / "textual-notation-of-model" / "second.sysml"
            first.parent.mkdir(parents=True)
            first.write_text("package First {} package Duplicate\n{\n}\n")
            second.write_text("package Duplicate {}\n")

            self.assertEqual(
                check_repo.find_duplicate_global_packages(root),
                {
                    "Duplicate": [
                        "textual-notation-of-model/first.sysml:1",
                        "textual-notation-of-model/second.sysml:1",
                    ]
                },
            )

    def test_allows_distinct_global_sysml_packages(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "textual-notation-of-model" / "first.sysml"
            second = root / "textual-notation-of-model" / "second.sysml"
            first.parent.mkdir(parents=True)
            first.write_text("package FirstPackage {\n}\n")
            second.write_text("package SecondPackage {\n}\n")

            self.assertEqual(check_repo.find_duplicate_global_packages(root), {})


if __name__ == "__main__":
    unittest.main()
