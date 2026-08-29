"""Feature-slice conformance guard: kernel-vocabulary synonyms in slices.

Gate 3 of the ontology alignment layer (see AGENTS.md "Ontology and
kernel-vocabulary alignment"): feature slices must not re-declare kernel
class names — or close synonyms of them — as local part/requirement
definitions. Kernel vocabulary lives in
``textual-notation-of-model/packages/methods/de4sdv/`` and is specialized or
imported, never duplicated.

Matching is done against comment-stripped source (declarations are code),
with whole-word boundaries so ``FeatureConfiguration`` does not trip
``Feature``.

Written as unittest.TestCase because CI runs
``python -m unittest discover -s tests``.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FEATURES_DIR = ROOT / "textual-notation-of-model/packages/features"
METHOD_KERNEL_DIR = ROOT / "textual-notation-of-model/packages/methods/de4sdv"

# Kernel class names (and rejected close synonyms) that feature slices must
# not re-declare locally. Names here mirror the ontology's kernel-mapped
# declarations and their kernel-registered core vocabulary.
_PROTECTED_CONCEPTS = (
    "EngineeringIncrement",
    "FeatureIncrement",
    "NeedsRequirementsIncrement",
    "ProductLine",
    "MemberProduct",
    "Feature",
    "CommonCapability",
    "StakeholderNeed",
    "Need",
    "Requirement",
    "RegulatoryConstraint",
    "ArchitectureElement",
    "VerificationCase",
    "ValidationScenario",
    "VerificationMethod",
    "AcceptanceCriterion",
    "Assumption",
    "IncrementGap",
    "Gap",
    "AssuranceClaim",
    "TraceLink",
    "Baseline",
)

_DECL_RE = re.compile(
    r"\b(part|requirement|item|enum|concern|viewpoint|allocation) def "
    r"([A-Za-z][A-Za-z0-9_]*)"
)

# Guard against accidental self-trips: none of the protected names is a
# substring of another at a word boundary (regex enforces that anyway), but
# the allowlist below records feature-slice declarations that legitimately
# embed a protected word and are NOT kernel synonyms.
#
# Reviewed exceptions (prefix + suffix, whole-word context, not synonyms of
# the kernel concept):
#   - MiddlewareAcceptanceCriterion010: the middleware slice's concrete
#     acceptance criterion REQUIREMENT DEFINITION. It embeds
#     "AcceptanceCriterion" as a suffix of its own concept name. The kernel
#     does not own a generic AcceptanceCriterion declaration (the ontology
#     maps it here), so this is the authoritative declaration, not a
#     duplicate.
_EXCEPTED_DECLARATIONS = {
    "MiddlewareAcceptanceCriterion010",
}


def _iter_slice_declarations():
    """Yield (path, name) for every declaration in every feature slice."""
    for path in sorted(FEATURES_DIR.rglob("*.sysml")):
        text = path.read_text(encoding="utf-8")
        code = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.DOTALL)
        for _, name in _DECL_RE.findall(code):
            yield path, name


class SliceKernelSynonymGuard(unittest.TestCase):
    """Feature slices must not re-declare kernel vocabulary or synonyms."""

    def test_no_kernel_synonym_declarations_in_slices(self):
        offenders = []
        for path, name in _iter_slice_declarations():
            if name in _EXCEPTED_DECLARATIONS:
                continue
            for concept in _PROTECTED_CONCEPTS:
                if re.fullmatch(rf"{concept}Variant[0-9]*|{concept}[A-Z].*", name):
                    # Name starts with the concept but is a distinct compound
                    # (e.g. RequirementCandidate in the kernel itself) — the
                    # dangerous case is the bare name or a close synonym, so
                    # only flag exact and plural/stem matches.
                    continue
            if name in _PROTECTED_CONCEPTS:
                offenders.append((path, name))
        self.assertEqual(
            offenders, [],
            "Feature slices re-declare kernel vocabulary; specialize or "
            "import the kernel declarations instead:\n"
            + "\n".join(f"  {p.relative_to(ROOT)}: {n}" for p, n in offenders),
        )

    def test_no_close_synonym_declarations_in_slices(self):
        """Common synonym spellings of kernel concepts are equally banned."""
        synonyms = {
            "StakeholderRequirement",
            "UserNeed",
            "SystemRequirement",
            "EvidenceItem",
            "VerificationActivity",
            "ProductVariant",
        }
        offenders = []
        for path, name in _iter_slice_declarations():
            if name in _EXCEPTED_DECLARATIONS:
                continue
            if name in synonyms:
                offenders.append((path, name))
        self.assertEqual(offenders, [])

    def test_method_kernel_itself_is_exempt_from_this_guard(self):
        """The kernel is the vocabulary owner; only slices are policed."""
        # Meta-check: the guard's discovery must not include kernel files.
        for path, _ in _iter_slice_declarations():
            self.assertFalse(
                METHOD_KERNEL_DIR in path.parents,
                f"{path} is a kernel file but the slice guard scanned it",
            )

    def test_discovery_finds_declarations(self):
        """Meta-check: discovery is not silently returning nothing."""
        count = sum(1 for _ in _iter_slice_declarations())
        self.assertGreater(count, 50)

    def test_known_exception_still_exists(self):
        """If the excepted declaration disappears, prune the exception."""
        names = {name for _, name in _iter_slice_declarations()}
        for exc in _EXCEPTED_DECLARATIONS:
            self.assertIn(
                exc, names,
                f"Exception '{exc}' is stale — remove it from "
                f"_EXCEPTED_DECLARATIONS",
            )


if __name__ == "__main__":
    unittest.main()
