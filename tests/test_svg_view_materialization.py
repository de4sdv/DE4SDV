from pathlib import Path
import subprocess
import sys


SCRIPT = Path("scripts/check_svg_view_materialization.py")
WORKFLOW = Path(".github/workflows/privileged-syside-validation.yml")


def _run(svg: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(svg), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def test_accepts_required_graph_labels_and_flow_count(tmp_path: Path) -> None:
    svg = tmp_path / "materialized.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg">
        <text>«view» exampleView</text>
        <text>expose Example::participant</text>
        <text>«part» participant : ExamplePart</text>
        <text>portOut : ExamplePort</text>
        <text>«flow»</text>
        </svg>""",
        encoding="utf-8",
    )

    result = _run(
        svg,
        "--view-name",
        "exampleView",
        "--require-label",
        "participant : ExamplePart",
        "--require-label",
        "portOut : ExamplePort",
        "--min-flow-count",
        "1",
    )

    assert result.returncode == 0, result.stderr
    assert "materialization check passed" in result.stdout


def test_rejects_forbidden_graph_label(tmp_path: Path) -> None:
    svg = tmp_path / "leaky.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg">
        <text>«view» exampleView</text>
        <text>«part» system1 : CandidateSystem</text>
        <text>«part» system2 : EvidenceSystem</text>
        </svg>""",
        encoding="utf-8",
    )

    result = _run(
        svg,
        "--view-name",
        "exampleView",
        "--forbid-label",
        "system2 : EvidenceSystem",
    )

    assert result.returncode == 1
    assert "forbidden graph label materialized" in result.stderr


def test_rejects_more_than_the_allowed_flow_count(tmp_path: Path) -> None:
    svg = tmp_path / "extra-flow.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg">
        <text>«view» exampleView</text>
        <text>«flow»</text>
        <text>«flow»</text>
        </svg>""",
        encoding="utf-8",
    )

    result = _run(
        svg,
        "--view-name",
        "exampleView",
        "--max-flow-count",
        "1",
    )

    assert result.returncode == 1
    assert "above allowed 1" in result.stderr


def test_privileged_workflow_gates_aebs_context_exchange_artifact() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "Check critical view materialization" in workflow
    assert "scripts/check_svg_view_materialization.py" in workflow
    assert "diagram-aebsSimulationPhysicalContextExchangeView.svg" in workflow
    assert "candidateVehicleSystem1 : AEBSystem1CandidateDeployment" in workflow
    assert "simulationEvidenceSystem2 : AEBSystem2SimulationAssets" in workflow
    assert "--min-flow-count 21" in workflow
    assert "--max-flow-count 21" in workflow
    assert "diagram-mwFunctionalInterfaceView.svg" in workflow
    assert "VehicleSignalAccessInbound" in workflow
    assert "diagram-mwPhysicalInterfaceView.svg" not in workflow
    assert "diagram-mwPhysicalStructureView.svg" in workflow
    assert "adapter : AutowareToAAOSSDVAdapterPhysical" in workflow
    assert "aaosSdvBoundary : SDVCoreBoundary" in workflow


def test_privileged_workflow_removes_native_grid_placeholders() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert 'for csv in grid-csv/*.csv; do' in workflow
    assert 'view="${view#matrix-}"' in workflow
    assert 'view="${view#table-}"' in workflow
    assert 'rm -f "diagrams/diagram-${view}.svg"' in workflow
