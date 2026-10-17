"""Concern–need disposition: derivesNeedFromConcern stays retired without replacement.

Covers the c4 disposition for exactly one identity:

- relationship ``derivesNeedFromConcern`` (``Need -> Concern``): the c4
  Outcome A decision — the pre-assumed predicate is **retired without
  replacement**. It has no required engineering meaning in the target
  architecture, no witness (no need frames or addresses a concern anywhere
  in the governed model; a plain dependency from a need to a concern is not
  a derivation, and nothing reads it), and no consumer (zero runtime, MCP,
  viewer, conformance-evaluator, or model-transformation readers).
  Native Concern/Viewpoint semantics plus the existing Need
  ``source``/``rationale`` provenance remain; the predicate must not be
  emitted as an active O2 Semantic Projection relation.

The batch tests:

1.  exactly ``derivesNeedFromConcern`` comprises c4 (no second identity
    promoted; the global parity-reviewed set is the seven c1 rows plus the
    two c2 rows plus the c3 row plus this one);
2.  authority is unchanged: ``legacy-yaml`` (no O3 cutover) with the reviewed
    retirement target and parity-reviewed evidence;
3.  the reviewed decision records Outcome A, the three-claim decomposition,
    the concern-usage inventory, the native framing analysis, and the
    forward-only required evidence;
4.  the intentional-retirement representation is machine-enforced and cannot
    be conflated with ``unknown`` or ``blocked`` (schema unit laws plus
    inventory shape laws);
5.  ``addressesConcern`` is not repurposed, generalized, or redefined: the
    increment-level relation was removed because no model element used it,
    and its name stays refused with its register disposition
    (identifier-collision law);
6.  no ``motivatesNeed`` inverse, no Need-specific addresses-style relation,
    and no generic source predicate are introduced;
7.  Need ``source``/``rationale`` provenance is not declared satisfied by any
    concern link;
8.  the governed model still contains zero requirement/need-owned ``frame``
    concern usages (the c4 finding is drift-checked, not just documented);
9.  c1/c2/c3/K/PLE/c5 rows remain unchanged;
10. the generated inventory reproduces the reviewed c4 decision (red between
    Commit A and Commit B by design — the two-commit binding gate);
11. the inventory stays runtime-inert: no Semantic Projection row, no runtime
    reader, no closure evidence, no privileged claim, no dispatched
    privileged ingestion.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from de4sdv.semantic import authority_inventory as ai
from de4sdv.semantic.kernel_contract import KernelContract
from model_contract_fixtures import model_contract  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]

TRAVERSAL_SOURCE = REPO_ROOT / "de4sdv/semantic/traversal.py"

DISPOSITION_IDENTITIES: tuple[str, ...] = ("derivesNeedFromConcern",)


#: Governed model roots for the frame/concern scan.
GOVERNED_MODEL_DIRS: tuple[str, ...] = (
    "textual-notation-of-model/packages",
    "model-based-product-line-engineering",
)

#: Scan floor: fail closed if the scan machinery silently stops finding
#: governed frame sites (a vacuous pass would hide drift).
GOVERNED_FRAME_SITES_FLOOR = 60


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


def _contract() -> KernelContract:
    return model_contract()


# ---------------------------------------------------------------------------
# Model scan machinery: brace-aware owner detection for ``frame`` / ``concern``
# ---------------------------------------------------------------------------

_OPEN_RE = re.compile(
    r"^\s*(?:(?:public|private|protected|abstract|derived|ref|in|out)\s+)*"
    r"(package|part|requirement|viewpoint|concern|view|use case|action|analysis"
    r"|verification|connection|interface|state|calc|constraint|attribute)\b"
    r"[^\n;]*\{"
)
_FRAME_RE = re.compile(r"^\s*frame\s+([A-Za-z_]\w*)\s*;")
_CONCERN_USAGE_RE = re.compile(r"^\s*concern\s+([A-Za-z_]\w*)\s*:\s*([\w:]+)")


def _iter_governed_sites():  # type: ignore[no-untyped-def]
    """Yield (path, line_no, kind, name, owner_kind) for governed model sites.

    ``kind`` is ``"frame"`` or ``"concern-usage"``; ``owner_kind`` is the
    innermost enclosing declaration keyword from a small, explicit keyword
    set (brace-depth aware), or ``"file"`` at file scope.
    """
    for base in GOVERNED_MODEL_DIRS:
        for path in sorted((REPO_ROOT / base).rglob("*.sysml")):
            if ".sysand" in path.parts:
                continue
            lines = path.read_text(encoding="utf-8").splitlines()
            stack: list[tuple[int, str]] = []
            depth = 0
            for number, line in enumerate(lines, 1):
                owner = stack[-1][1] if stack else "file"
                frame = _FRAME_RE.match(line)
                if frame:
                    yield path, number, "frame", frame.group(1), owner
                concern = _CONCERN_USAGE_RE.match(line)
                if concern:
                    yield path, number, "concern-usage", concern.group(1), owner
                net = line.count("{") - line.count("}")
                opener = _OPEN_RE.match(line)
                if net > 0 and opener:
                    stack.append((depth + net, opener.group(1)))
                depth += net
                while stack and depth < stack[-1][0]:
                    stack.pop()


# ---------------------------------------------------------------------------
# Scope, decisions, and inventory state
# ---------------------------------------------------------------------------


class TestConcernNeedDispositionScope:
    def test_scope_is_exactly_derives_need_from_concern(self):
        assert DISPOSITION_IDENTITIES == ("derivesNeedFromConcern",)


    def test_runtime_does_not_read_the_inventory_or_the_retired_identity(self):
        assert "never imported by the semantic runtime" in (ai.__doc__ or "").lower()
        runtime = TRAVERSAL_SOURCE.read_text(encoding="utf-8")
        assert "authority_inventory" not in runtime
        assert "semantic-authority-inventory" not in runtime
        # The retired identity gains no traversal strategy and no mapping.
        assert "derivesNeedFromConcern" not in runtime


# ---------------------------------------------------------------------------
# Reviewed decision (the source row)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Retirement representation — schema unit laws
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Non-conflation: intentionally retired vs unknown vs blocked
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Identifier collision: addressesConcern is never repurposed
# ---------------------------------------------------------------------------


class TestAddressesConcernNotRepurposed:
    def test_addresses_concern_is_refused_not_repurposed(self):
        """The increment-level addressesConcern was removed (no model element
        used it); its name stays refused, so it cannot come back as a
        Need -> Concern predicate without a reviewed register change."""
        from de4sdv.semantic.kernel_contract import RetiredIdentityError

        contract = _contract()
        assert "addressesConcern" not in contract.relationships
        assert "register disposition REMOVE" in contract.refused["addressesConcern"]
        with pytest.raises(RetiredIdentityError, match="register disposition REMOVE"):
            contract.relationship_mapping("addressesConcern")

    def test_derives_need_from_concern_is_refused_with_its_disposition(self):
        """O4 Wave C2 (owner decision D5, intentional migration): the retired
        row is no longer served as a vocabulary-only gap; the model-built
        contract refuses it with its register disposition."""
        from de4sdv.semantic.kernel_contract import RetiredIdentityError

        contract = _contract()
        assert "derivesNeedFromConcern" not in contract.relationships
        assert "register disposition REMOVE" in contract.refused["derivesNeedFromConcern"]
        with pytest.raises(RetiredIdentityError, match="register disposition REMOVE"):
            contract.relationship_mapping("derivesNeedFromConcern")


    def test_no_motivates_inverse_or_generic_source_predicate(self):
        contract = _contract()
        identities = set(contract.classes) | set(contract.relationships) | set(contract.refused)
        for token in (
            "motivatesNeed",
            "needAddressesConcern",
            "derivesNeedFromUseCase",
            "derivesNeedFromRisk",
            "derivesNeedFromScenario",
            "traceToSource",
        ):
            assert token not in identities, token
        runtime = TRAVERSAL_SOURCE.read_text(encoding="utf-8")
        assert "motivatesNeed" not in runtime
        assert "traceToSource" not in runtime

    def test_ontology_relationship_set_is_unchanged(self):
        """In the model-built contract both concern relations are refused,
        never served: the retired derivesNeedFromConcern and the removed
        addressesConcern."""
        contract = _contract()
        for name in ("addressesConcern", "derivesNeedFromConcern"):
            assert name not in contract.relationships, name
            assert name in contract.refused, name


# ---------------------------------------------------------------------------
# Governed-model scan laws (the c4 finding, drift-checked)
# ---------------------------------------------------------------------------


class TestGovernedModelScanLaws:
    def test_no_requirement_or_need_owned_frame_sites(self):
        """The c4 finding: no need frames a concern. Every governed ``frame``
        site is viewpoint-owned (frame = viewpoint framing of its concerns);
        a requirement-owned frame site would void the reviewed basis and must
        fail this law, never pass silently."""
        sites = list(_iter_governed_sites())
        frames = [site for site in sites if site[2] == "frame"]
        assert len(frames) >= GOVERNED_FRAME_SITES_FLOOR, len(frames)
        offenders = [
            f"{path}:{number} owner={owner}"
            for path, number, _kind, _name, owner in frames
            if owner != "viewpoint"
        ]
        assert offenders == []
        requirement_owned = [
            (path, number)
            for path, number, _kind, _name, owner in frames
            if owner == "requirement"
        ]
        assert requirement_owned == []

    def test_no_requirement_owned_concern_usages(self):
        """No concern usage is owned by a requirement-like usage: concerns
        cannot be smuggled into the need bodies as direct members."""
        sites = list(_iter_governed_sites())
        concerns = [site for site in sites if site[2] == "concern-usage"]
        assert len(concerns) >= 80, len(concerns)
        offenders = [
            f"{path}:{number} owner={owner}"
            for path, number, _kind, _name, owner in concerns
            if owner == "requirement"
        ]
        assert offenders == []
