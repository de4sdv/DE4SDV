#!/usr/bin/env python3
"""Minimal repository health checks for DE4SDV."""

from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from pathlib import Path
import re

try:
    from scripts import validate_aebs_executable_bench
except ImportError:  # Direct execution sets scripts/ as sys.path[0].
    import validate_aebs_executable_bench

try:
    from scripts import check_model_sync
except ImportError:  # Direct execution sets scripts/ as sys.path[0].
    import check_model_sync

try:
    from scripts import generate_scenario_manifest
except ImportError:  # Direct execution sets scripts/ as sys.path[0].
    import generate_scenario_manifest

REQUIRED_FILES = [
    "README.md",
    "CONTRIBUTING.md",
    "GOVERNANCE.md",
    "SECURITY.md",
    "SUPPORT.md",
    "CODE_OF_CONDUCT.md",
    "docs/terminology/glossary.md",
]

SYSML_MODEL_PATHS = (
    Path("textual-notation-of-model"),
    Path("model-based-product-line-engineering/product-models"),
    Path("model-based-product-line-engineering/scoping"),
)

IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|[{}]|[^\s]")


def _scrub_comments_and_strings(text: str) -> str:
    """Replace comments and quoted text while preserving positions and newlines."""
    result: list[str] = []
    index = 0
    state = "code"
    quote = ""

    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""

        if state == "line_comment":
            if char == "\n":
                result.append(char)
                state = "code"
            else:
                result.append(" ")
        elif state == "block_comment":
            if char == "*" and next_char == "/":
                result.extend((" ", " "))
                index += 1
                state = "code"
            else:
                result.append("\n" if char == "\n" else " ")
        elif state == "string":
            if char == "\\" and next_char:
                result.extend((" ", "\n" if next_char == "\n" else " "))
                index += 1
            elif char == quote:
                result.append(" ")
                state = "code"
            else:
                result.append("\n" if char == "\n" else " ")
        elif char == "/" and next_char == "/":
            result.extend((" ", " "))
            index += 1
            state = "line_comment"
        elif char == "/" and next_char == "*":
            result.extend((" ", " "))
            index += 1
            state = "block_comment"
        elif char in {'"', "'"}:
            result.append(" ")
            quote = char
            state = "string"
        else:
            result.append(char)

        index += 1

    return "".join(result)


def find_duplicate_global_packages(root: Path) -> dict[str, list[str]]:
    """Find repeated simple-name package declarations at lexical brace depth zero.

    This bounded lexical check prevents a known repository regression. It is not
    SysML syntax or semantic validation; licensed SysIDE remains authoritative.
    """
    declarations: dict[str, list[str]] = defaultdict(list)

    for model_path in SYSML_MODEL_PATHS:
        absolute_path = root / model_path
        if not absolute_path.exists():
            continue
        for sysml_file in sorted(absolute_path.rglob("*.sysml")):
            scrubbed = _scrub_comments_and_strings(sysml_file.read_text())
            tokens = list(TOKEN.finditer(scrubbed))
            newlines = [
                index for index, character in enumerate(scrubbed) if character == "\n"
            ]
            brace_depth = 0

            for index, token_match in enumerate(tokens):
                token = token_match.group(0)
                if (
                    brace_depth == 0
                    and token == "package"
                    and index + 2 < len(tokens)
                    and IDENTIFIER.match(tokens[index + 1].group(0))
                    and tokens[index + 2].group(0) == "{"
                ):
                    relative = sysml_file.relative_to(root).as_posix()
                    line_number = bisect_right(newlines, token_match.start()) + 1
                    declarations[tokens[index + 1].group(0)].append(
                        f"{relative}:{line_number}"
                    )

                if token == "{":
                    brace_depth += 1
                elif token == "}":
                    brace_depth -= 1

    return {
        name: locations
        for name, locations in declarations.items()
        if len(locations) > 1
    }


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    missing = [rel for rel in REQUIRED_FILES if not (root / rel).exists()]
    duplicate_packages = find_duplicate_global_packages(root)
    aebs_bench_errors = validate_aebs_executable_bench.validate_bench(root)
    model_sync_errors = check_model_sync.run_all_checks()
    manifest_errors = generate_scenario_manifest.run_check_errors()

    if missing:
        print("Repository check failed. Missing required files:")
        for rel in missing:
            print(f"- {rel}")

    if duplicate_packages:
        print("Repository check failed. Duplicate global SysML package declarations:")
        for name, locations in sorted(duplicate_packages.items()):
            print(f"- {name}")
            for location in locations:
                print(f"  - {location}")

    if aebs_bench_errors:
        print("Repository check failed. AEBS executable bench errors:")
        for error in aebs_bench_errors:
            print(f"- {error}")

    if model_sync_errors:
        print("Repository check failed. Model sync errors:")
        for error in model_sync_errors:
            print(f"- {error}")

    if manifest_errors:
        print("Repository check failed. Scenario manifest errors:")
        for error in manifest_errors:
            print(f"- {error}")

    if missing or duplicate_packages or aebs_bench_errors or model_sync_errors or manifest_errors:
        return 1

    print("Repository check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
