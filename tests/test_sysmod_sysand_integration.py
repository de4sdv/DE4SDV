from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import tomllib

from tools.sysml_html_viewer.model_parse import parse_file


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / ".project.json"
LOCK = ROOT / "sysand-lock.toml"
ADAPTER = (
    ROOT
    / "textual-notation-of-model/packages/methods/de4sdv/de4sdv_sysmod_adapter.sysml"
)
INCREMENT_WORKFLOW = ROOT / "methodologies/sysmod-sysmlv2/increment-workflow.md"
PROCESS_MAPPING = ROOT / "methodologies/sysmod-sysmlv2/process-mapping.md"
METHOD_PROCESS = (
    ROOT
    / "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_process.sysml"
)
SAF_VIEWPOINTS = (
    ROOT / "textual-notation-of-model/packages/methods/saf/SAF_Viewpoints.sysml"
)
AEBS_LOGICAL = (
    ROOT
    / "methodologies/sysmod-sysmlv2/pilots/aebs-logical-architecture.yaml"
)
METHOD_CONTEXT = (
    ROOT
    / "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml"
)
AEBS_OPERATIONAL = (
    ROOT
    / "textual-notation-of-model/packages/features/aebs/aebs_operational_context.sysml"
)
MW_OPERATIONAL = (
    ROOT
    / "textual-notation-of-model/packages/features/middleware/mw_operational_context.sysml"
)
METHOD_README = ROOT / "methodologies/sysmod-sysmlv2/README.md"
PROCESS_SET_README = ROOT / "approach/process-set/README.md"
UPSTREAM = ROOT / "methodologies/sysmod-sysmlv2/upstream.md"
UPSTREAM_REPORT = (
    ROOT / "methodologies/sysmod-sysmlv2/upstream-compatibility-report.md"
)
ADOPTION_ADR = (
    ROOT / "docs/architecture-decisions/0007-pin-sysmod-sysand-dependency.md"
)


def _tracked_files() -> list[Path]:
    output = subprocess.check_output(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
    ).decode()
    return [ROOT / relative for relative in output.split("\0") if relative]


def test_sysmod_dependency_is_exactly_pinned_and_locked() -> None:
    project = json.loads(PROJECT.read_text(encoding="utf-8"))
    usages = {
        usage["resource"]: usage["versionConstraint"]
        for usage in project["usage"]
    }
    assert usages["pkg:sysand/mbse4u/sysmod"] == "=5.1.1"

    lock = tomllib.loads(LOCK.read_text(encoding="utf-8"))
    sysmod_projects = [
        entry
        for entry in lock["project"]
        if "pkg:sysand/mbse4u/sysmod" in entry.get("identifiers", [])
    ]
    assert len(sysmod_projects) == 1
    assert sysmod_projects[0]["version"] == "5.1.1"

    de4sdv = next(entry for entry in lock["project"] if entry["name"] == "de4sdv-model")
    assert "pkg:sysand/mbse4u/sysmod" in de4sdv["usages"]


def test_adapter_is_the_only_sysmod_import_boundary() -> None:
    adapter = ADAPTER.read_text(encoding="utf-8")
    assert "package DE4SDV_SYSMODAdapter" in adapter
    expected_imports = {
        "private import SYSMOD::ExtendedStakeholder;",
        "private import SYSMOD::ExtendedRequirement;",
        "private import SYSMOD::SystemUseCase;",
        "private import SYSMOD::ConstrainedOccurrence;",
    }
    for expected in expected_imports:
        assert expected in adapter
    assert "private import SYSMOD::*;" not in adapter

    expected_seams = {
        "part def SYSMODStakeholderBase :> ExtendedStakeholder",
        "requirement def SYSMODRequirementBase :> ExtendedRequirement",
        "use case def SYSMODSystemUseCaseBase :> SystemUseCase",
        "occurrence def SYSMODConstrainedOccurrenceBase :> ConstrainedOccurrence",
    }
    for expected in expected_seams:
        assert expected in adapter

    imported_from = []
    qualified_from = []
    for path in sorted((ROOT / "textual-notation-of-model").rglob("*.sysml")):
        text = path.read_text(encoding="utf-8")
        if re.search(r"\bimport\s+SYSMOD(?:::|\b)", text):
            imported_from.append(path.relative_to(ROOT).as_posix())
        if "SYSMOD::" in text:
            qualified_from.append(path.relative_to(ROOT).as_posix())

    assert imported_from == [ADAPTER.relative_to(ROOT).as_posix()]
    assert qualified_from == [ADAPTER.relative_to(ROOT).as_posix()]


def test_viewer_parser_exposes_supported_adapter_seams_and_source() -> None:
    parsed = parse_file(ADAPTER, ROOT)
    members = {member.name: member for member in parsed.members}
    expected = {
        "SYSMODStakeholderBase": "part def",
        "SYSMODRequirementBase": "requirement def",
        "SYSMODSystemUseCaseBase": "use case def",
    }
    for name, kind in expected.items():
        assert members[name].kind == kind
        assert members[name].doc

    source = ADAPTER.read_text(encoding="utf-8")
    assert "occurrence def SYSMODConstrainedOccurrenceBase" in source
    assert "explicit preconditions and postconditions" in source


def test_upstream_source_is_not_vendored_and_project_root_is_not_adopted() -> None:
    tracked = {path.relative_to(ROOT).as_posix() for path in _tracked_files()}
    assert not any(path.endswith("/SYSMOD.sysml") or path == "SYSMOD.sysml" for path in tracked)

    adapter = ADAPTER.read_text(encoding="utf-8")
    for excluded in (
        "SYSMOD::Project",
        "SYSMOD::AIProject",
        "RequirementBoilderplates",
        "requirement def MinValue",
        "requirement def MinAvailability",
    ):
        assert excluded not in adapter


def test_method_uses_saf_domains_independently_from_architecture_artifact_kinds() -> None:
    workflow = INCREMENT_WORKFLOW.read_text(encoding="utf-8")
    expected_rows = (
        "| 5. Requirements | What shall the system or product line do and how will those requirements be verified? | Conceptual |",
        "| 6. Functional architecture | What functions, flows, states, and interfaces are needed? | Conceptual |",
        "| 7. Logical architecture | What technology-independent logical elements realize the functions? | Conceptual |",
        "| 8. Physical / software realization | What software, hardware, deployment, or tool elements realize the system design? | Physical |",
    )
    for expected in expected_rows:
        assert expected in workflow
    assert "Common / Functional" not in workflow
    assert "it is not the name of Phase 7" in workflow
    assert "not a replacement name for the logical-architecture artifact" in workflow

    mapping = PROCESS_MAPPING.read_text(encoding="utf-8")
    assert "Phase 7: Logical architecture" in mapping
    assert "### Phase 7 — Logical architecture" in mapping
    assert "Phase 7: Conceptual architecture" not in mapping
    assert "### Phase 7 — Conceptual architecture" not in mapping

    method = METHOD_PROCESS.read_text(encoding="utf-8")
    assert "phase7_logicalArchitecture" in method
    assert "phase7_systemArchitecture" not in method
    for phase in ("phase5Domain", "phase6Domain", "phase7Domain"):
        assert f'attribute {phase} : ScalarValues::String = "Conceptual";' in method

    for path in (METHOD_README, PROCESS_MAPPING, PROCESS_SET_README):
        text = path.read_text(encoding="utf-8")
        assert "13-phase increment workflow" in text
        assert "12-phase increment workflow" not in text


def test_provenance_separates_historical_source_review_from_current_package() -> None:
    upstream = UPSTREAM.read_text(encoding="utf-8")
    assert "Historically inspected commit: `644065e`" in upstream
    assert "Resource: `pkg:sysand/mbse4u/sysmod`" in upstream
    assert "Exact version constraint: `=5.1.1`" in upstream
    assert "DE4SDV does not copy or" in upstream
    assert "vendor the package source" in upstream

    adr = ADOPTION_ADR.read_text(encoding="utf-8")
    assert "Proposed" in adr
    assert "confine upstream imports to `DE4SDV_SYSMODAdapter`" in adr
    assert "does **not** adopt or specialize upstream `Project`" in adr

    report = UPSTREAM_REPORT.read_text(encoding="utf-8")
    assert "Status: **draft; not sent upstream**" in report
    assert "Candidate upstream findings" in report


def test_active_method_artifacts_do_not_use_retired_saf_domain_labels() -> None:
    stale_patterns = (
        re.compile(r"\bfunctional-domain\b", re.IGNORECASE),
        re.compile(r"\blogical domain\b", re.IGNORECASE),
        re.compile(r"Functional and Logical domains merged", re.IGNORECASE),
    )
    roots = (
        ROOT / "methodologies/sysmod-sysmlv2",
        ROOT / "textual-notation-of-model",
    )
    stale = []
    for root in roots:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix not in {".md", ".sysml", ".yaml", ".yml"}:
                continue
            text = path.read_text(encoding="utf-8")
            for line_number, line in enumerate(text.splitlines(), 1):
                if any(pattern.search(line) for pattern in stale_patterns):
                    stale.append(f"{path.relative_to(ROOT)}:{line_number}:{line.strip()}")
    assert stale == []

    logical = AEBS_LOGICAL.read_text(encoding="utf-8")
    assert "source_id: SAF-CONCEPTUAL-DOMAIN" in logical
    assert "source_id: SAF-LOGICAL-DOMAIN" not in logical

    saf = SAF_VIEWPOINTS.read_text(encoding="utf-8")
    assert "// ─── Conceptual Domain ───" in saf
    assert "System requirements, functional architecture," in saf
    assert "technology-independent" in saf
    assert "functional architecture, and logical architecture" in saf
    assert "they do not rename the logical" in saf


def test_requirement_candidate_specializes_sysmod_requirement_base() -> None:
    text = METHOD_CONTEXT.read_text(encoding="utf-8")
    assert "private import DE4SDV_SYSMODAdapter::*;" in text
    assert "requirement def RequirementCandidate :> SYSMODRequirementBase" in text


def test_aebs_use_case_specializes_sysmod_use_case_base_with_semantics() -> None:
    text = AEBS_OPERATIONAL.read_text(encoding="utf-8")
    assert "private import DE4SDV_SYSMODAdapter::*;" in text
    normalized = " ".join(text.split())
    assert (
        "use case def MitigateVehicleTargetForwardCollisionRisk "
        ":> SYSMODSystemUseCaseBase" in normalized
    )
    assert "attribute ucMotivation : ScalarValues::String =" in text
    assert "attribute ucTrigger : ScalarValues::String =" in text
    assert "attribute ucResult : ScalarValues::String =" in text


def test_middleware_use_case_def_specializes_sysmod_use_case_base() -> None:
    text = MW_OPERATIONAL.read_text(encoding="utf-8")
    assert "private import DE4SDV_SYSMODAdapter::*;" in text
    assert (
        "use case def IntegrateADASWithVehiclePlatform :> SYSMODSystemUseCaseBase"
        in text
    )
    assert (
        "use case 'integrate ADAS with vehicle platform' "
        ": IntegrateADASWithVehiclePlatform" in text
    )
