from pathlib import Path

from scripts.generate_view_index import (
    artifact_filename,
    collect_views,
    parse_view_spec,
    render_markdown,
)
from scripts.check_committed_view_artifacts import check_committed_view_artifacts


MIDDLEWARE = Path("textual-notation-of-model/packages/features/middleware")
WORKFLOW = Path(".github/workflows/privileged-syside-validation.yml")


def test_matrix_view_uses_generated_review_grid_name(tmp_path: Path) -> None:
    folder = tmp_path / "models"
    diagrams = folder / "diagrams"
    diagrams.mkdir(parents=True)
    (folder / "model.sysml").write_text(
        """
        package Example {
          view allocationView : MVD::MatrixView {
            viewpoint selected : SystemFunctionMappingViewpoint {
              frame mappingConcern;
            }
          }
        }
        """,
        encoding="utf-8",
    )
    (diagrams / "diagram-matrix-allocationView.svg").write_text(
        "<svg/>", encoding="utf-8"
    )

    markdown = render_markdown(folder)

    assert artifact_filename("allocationView", "MVD::MatrixView") == (
        "diagram-matrix-allocationView.svg"
    )
    assert "![allocationView](diagrams/diagram-matrix-allocationView.svg)" in markdown
    assert "diagram-allocationView.svg" not in markdown


def test_action_flow_view_keeps_native_diagram_name() -> None:
    assert artifact_filename("processView", "ActionFlowView") == (
        "diagram-processView.svg"
    )


def test_quoted_expose_target_is_not_truncated() -> None:
    spec = parse_view_spec(
        """
        view traceView : GeneralView {
          expose OperationalContext::'integrate ADAS with vehicle platform';
        }
        """,
        "traceView",
    )

    assert spec is not None
    assert spec.exposes == [
        "OperationalContext::'integrate ADAS with vehicle platform'"
    ]


def test_committed_middleware_diagrams_match_current_view_set() -> None:
    collected = collect_views(MIDDLEWARE)
    expected = {
        artifact_filename(spec.name, spec.view_type)
        for _, views in collected
        for spec in views
    }
    actual = {path.name for path in (MIDDLEWARE / "diagrams").glob("*.svg")}

    assert actual == expected


def test_committed_artifact_checker_detects_stale_content(tmp_path: Path) -> None:
    model = tmp_path / "models"
    tracked = model / "diagrams"
    generated = tmp_path / "generated"
    tracked.mkdir(parents=True)
    generated.mkdir()
    (model / "model.sysml").write_text(
        "view exampleView { render asTreeDiagram; }", encoding="utf-8"
    )
    expected = "diagram-exampleView.svg"
    (tracked / expected).write_text("<svg>old</svg>", encoding="utf-8")
    (generated / expected).write_text("<svg>new</svg>", encoding="utf-8")

    errors = check_committed_view_artifacts(model, generated)

    assert errors == [f"stale committed diagram content: {tracked / expected}"]


def test_privileged_workflow_rejects_stale_committed_diagrams() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "Check committed view index and diagrams" in workflow
    assert "scripts/check_committed_view_artifacts.py" in workflow
    assert "scripts/generate_view_index.py" in workflow
    assert "git diff --exit-code" in workflow
