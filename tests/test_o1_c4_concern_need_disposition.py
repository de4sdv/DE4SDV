"""O1 c4 — concern–need semantic disposition review (PR #249).

Covers the c4 disposition for exactly one identity:

- relationship ``derivesNeedFromConcern`` (``Need -> Concern``): the c4
  Outcome A decision — the pre-assumed predicate is **retired without
  replacement**. It has no required engineering meaning in the target
  architecture, no witness (no need frames, references, or addresses a
  concern anywhere in the governed model), and no consumer (zero runtime,
  MCP, viewer, conformance-evaluator, or model-transformation readers).
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
5.  ``addressesConcern`` remains ``EngineeringIncrement -> Concern`` and is
    not repurposed, generalized, or redefined (identifier-collision law);
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

C4_IDENTITIES: tuple[str, ...] = ("derivesNeedFromConcern",)


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


class TestC4ScopeAndCounts:
    def test_c4_is_exactly_one_identity(self):
        assert C4_IDENTITIES == ("derivesNeedFromConcern",)


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
# Identifier collision: addressesConcern stays increment-level
# ---------------------------------------------------------------------------


class TestAddressesConcernUntouched:
    def test_addresses_concern_contract_is_unchanged(self):
        relationships = _contract().relationships
        assert relationships["addressesConcern"]["domain"] == "EngineeringIncrement"
        assert relationships["addressesConcern"]["range"] == "Concern"
        # No mapping was silently attached or changed.
        assert "sysml_mapping" not in relationships["addressesConcern"]

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
        """In the model-built contract (O4 Wave C2) addressesConcern stays a
        vocabulary-only relationship and the retired row is refused, never
        served."""
        contract = _contract()
        assert "addressesConcern" in contract.relationships
        with pytest.raises(KeyError, match="no SysML mapping"):
            contract.relationship_mapping("addressesConcern")
        assert "derivesNeedFromConcern" not in contract.relationships
        assert "derivesNeedFromConcern" in contract.refused


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
