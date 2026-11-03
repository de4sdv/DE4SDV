"""The doc of every concern of a live increment names the parties that hold it.

Owner decision of 2026-11-02: a concern names as its stakeholders the parties
whose interest it states, and a need is held by those it serves. The doc of a
concern is what its framing view shows, so the doc names the same parties:

- every declared stakeholder member's role appears in the doc;
- no doc gives the concern to unnamed "reviewers" (the role is the
  open-source reviewer, and the doc says so).

A concern without a doc shows no text that could name the wrong party, so it is
not checked; the count of documented concerns is pinned so that deleting a doc
cannot make the check pass.

The scope is the live increments, read from the packages their charters list
in ``expectedArtifacts``. The earlier increments INC-AEBS-003 and INC-MW-004
wait for their own cleanup.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ROOT / "textual-notation-of-model" / "packages"

#: increment -> (file declaring the charter, charter name, test-id prefix, documented concerns at least)
CHARTERS = {
    "INC-DRIVING-001": ("features/driving/closed_loop_driving_framing.sysml",
                        "closedLoopDrivingCharter", "DRIVING001", 12),
    "INC-AEBS-010": ("features/aebs/aebs_visualization_framing.sysml",
                     "visualizationTraceObligations", "AEBS010", 7),
    "INC-MW-011": ("features/middleware/middleware_score_framing.sysml",
                   "scoreMiddlewareCharter", "MW011", 17),
}

#: kernel stakeholder role -> the words a doc uses for it (singular; plurals contain it)
ROLE_WORDS = {
    "SystemsEngineer": "systems engineer",
    "SystemArchitect": "system architect",
    "SoftwareDeveloper": "software developer",
    "HardwareDeveloper": "hardware developer",
    "Maintainer": "maintainer",
    "VerificationEngineer": "verification engineer",
    "SafetyExpert": "safety expert",
    "SecurityExpert": "security expert",
    "ComplianceEngineer": "compliance engineer",
    "ProductLineEngineer": "product-line engineer",
    "OpenSourceReviewer": "open-source reviewer",
    "VehicleOccupant": "occupant",
    "RoadUser": "road user",
    "Supplier": "supplier",
    "ProjectManager": "project manager",
}

GENERIC_REVIEWERS = re.compile(r"(?<!open-source )\breviewers?\b", re.IGNORECASE)
STAKEHOLDER = re.compile(r"\bstakeholder\s+\w+\s*:\s*([\w:]+)\s*;")
CONCERN_WITH_BODY = re.compile(r"\bconcern\s+(\w+)\s*:\s*[\w:]+\s*\{")
CONCERN_WITHOUT_BODY = re.compile(r"\bconcern\s+(\w+)\s*:\s*[\w:]+\s*;")
DOC = re.compile(r"\bdoc\s*/\*(.*?)\*/", re.DOTALL)


def _body(text: str, open_brace: int) -> str:
    depth, index = 1, open_brace + 1
    while depth and index < len(text):
        depth += {"{": 1, "}": -1}.get(text[index], 0)
        index += 1
    assert depth == 0, "unbalanced braces"
    return text[open_brace + 1:index - 1]


def _package_files() -> dict[str, Path]:
    files: dict[str, list[Path]] = {}
    for path in PACKAGES.rglob("*.sysml"):
        for name in re.findall(r"^\s*(?:public\s+|private\s+)?package\s+(\w+)\s*\{", path.read_text(encoding="utf-8"),
                               re.MULTILINE):
            files.setdefault(name, []).append(path)
    return {name: paths[0] for name, paths in files.items() if len(paths) == 1}


def _expected_artifacts(charter_file: str, charter: str) -> list[str]:
    text = (PACKAGES / charter_file).read_text(encoding="utf-8")
    declaration = re.search(rf"\b{charter}\b[^;{{]*\{{", text)
    assert declaration, f"charter {charter} not found in {charter_file}"
    artifacts = re.search(r"expectedArtifacts\s*=\s*\((.*?)\);", _body(text, declaration.end() - 1), re.DOTALL)
    assert artifacts, f"charter {charter} lists no expectedArtifacts"
    return re.findall(r'"(\w+)"', artifacts.group(1))


def _doc_text(raw: str) -> str:
    return " ".join(line.strip().lstrip("*").strip() for line in raw.splitlines()).strip()


def _concerns() -> list[tuple[str, str, Path, list[str], str | None]]:
    package_files = _package_files()
    found = []
    for increment, (charter_file, charter, _prefix, _least) in CHARTERS.items():
        for package in _expected_artifacts(charter_file, charter):
            path = package_files[package]
            text = path.read_text(encoding="utf-8")
            for match in CONCERN_WITH_BODY.finditer(text):
                body = _body(text, match.end() - 1)
                holders = [role.split("::")[-1] for role in STAKEHOLDER.findall(body)]
                doc = DOC.search(body)
                found.append((increment, match.group(1), path, holders, _doc_text(doc.group(1)) if doc else None))
    return found


CONCERNS = _concerns()
DOCUMENTED = [concern for concern in CONCERNS if concern[4]]


def test_every_charter_package_resolves_to_one_file():
    package_files = _package_files()
    for increment, (charter_file, charter, _prefix, _least) in CHARTERS.items():
        artifacts = _expected_artifacts(charter_file, charter)
        assert artifacts, increment
        missing = [package for package in artifacts if package not in package_files]
        assert not missing, f"{increment}: packages declared in no single file: {missing}"


def test_every_live_increment_keeps_its_documented_concerns_in_scope():
    for increment, (_file, _charter, _prefix, least) in CHARTERS.items():
        names = [name for inc, name, *_rest in DOCUMENTED if inc == increment]
        assert len(names) >= least, f"{increment}: {len(names)} documented concerns, expected at least {least}"


def test_every_concern_usage_has_a_body():
    package_files = _package_files()
    for increment, (charter_file, charter, _prefix, _least) in CHARTERS.items():
        for package in _expected_artifacts(charter_file, charter):
            text = package_files[package].read_text(encoding="utf-8")
            assert not CONCERN_WITHOUT_BODY.findall(text), f"{increment}: a concern usage without holders or doc"


@pytest.mark.parametrize(
    "increment,name,path,holders,doc",
    DOCUMENTED,
    ids=[f"{CHARTERS[inc][2]}__{name}" for inc, name, *_rest in DOCUMENTED],
)
def test_the_concern_doc_names_its_holders(increment, name, path, holders, doc):
    where = f"{increment} {name} ({path.relative_to(ROOT)})"
    assert holders, f"{where}: no stakeholder member"
    unknown = [role for role in holders if role not in ROLE_WORDS]
    assert not unknown, f"{where}: add the words for {unknown} to ROLE_WORDS"
    unnamed = [role for role in holders if ROLE_WORDS[role] not in doc.lower()]
    assert not unnamed, f"{where}: the doc does not name {unnamed}: {doc[:120]}"
    generic = GENERIC_REVIEWERS.search(doc)
    assert not generic, f"{where}: the doc gives the concern to unnamed reviewers: {doc[:120]}"
