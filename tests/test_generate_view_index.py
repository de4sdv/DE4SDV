from pathlib import Path

from scripts.generate_view_index import (
    DIAGRAM_PUBLICATION_GAPS,
    artifact_filename,
    collect_views,
    parse_view_spec,
    render_markdown,
    _table_statement_notes,
)
from scripts.check_committed_view_artifacts import check_committed_view_artifacts


PUBLISHED_VIEW_FOLDERS = (
    Path("textual-notation-of-model/packages/architecture"),
    Path("textual-notation-of-model/packages/features/aebs"),
    Path("textual-notation-of-model/packages/features/middleware"),
    Path("textual-notation-of-model/packages/methods/de4sdv"),
    Path("model-based-product-line-engineering/product-models"),
)
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


def test_view_explanation_uses_framed_concern_doc(tmp_path: Path) -> None:
    folder = tmp_path / "aebs"
    folder.mkdir()
    (folder / "model.sysml").write_text(
        """
        concern reviewConcern : Concern {
          doc /* Reviewers need the selected boundary visible. More detail. */
        }
        view reviewView {
          viewpoint selected : GeneralViewpoint { frame reviewConcern; }
        }
        """,
        encoding="utf-8",
    )

    markdown = render_markdown(folder)

    assert "# AEBS Views" in markdown
    assert "Reviewers need the selected boundary visible." in markdown
    assert "More detail." not in markdown


def test_view_explanation_and_status_have_honest_fallbacks(tmp_path: Path) -> None:
    folder = tmp_path / "architecture"
    folder.mkdir()
    (folder / "model.sysml").write_text(
        """
        concern requirementTraceConcern : Concern { subject; }
        view traceView {
          viewpoint selected : GeneralViewpoint { frame requirementTraceConcern; }
        }
        """,
        encoding="utf-8",
    )

    markdown = render_markdown(folder)

    assert "Shows the requirement set and its trace links" in markdown
    assert "**Diagram status:** Not yet published in this folder." in markdown


def test_presentation_note_flags_svg_ellipsis(tmp_path: Path) -> None:
    folder = tmp_path / "models"
    diagrams = folder / "diagrams"
    diagrams.mkdir(parents=True)
    (folder / "model.sysml").write_text(
        "view structureView { render asTreeDiagram; }", encoding="utf-8"
    )
    (diagrams / "diagram-structureView.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><text>…</text></svg>',
        encoding="utf-8",
    )

    markdown = render_markdown(folder)

    assert "truncates at least one compartment" in markdown


def test_table_statement_note_reports_status_line_tables(tmp_path: Path) -> None:
    labels = [
        "ID",
        "Name",
        "Statement",
        "needExample",
        "StakeholderNeedCandidate, RequirementsManagementAttributeBase",
        "N-AEBS-009 draft System 2 need.",
        "reqExample",
        "FunctionalRequirementCandidate, RequirementCandidate",
        "REQ-AEBS-001 candidate.",
    ]

    notes = _table_statement_notes(labels)

    assert notes == [
        "Every Statement cell shows a short status line rather than the "
        "full need or requirement prose; the complete statements live in "
        "the source file and the viewer tooltips."
    ]
    assert _table_statement_notes(
        ["ID", "Name", "Statement", "needExample", "StakeholderNeedCandidate", "Platform engineers need the SDV product line to provide middleware integration."]
    ) == []


def test_anonymous_comment_boxes_get_attachment_note(tmp_path: Path) -> None:
    folder = tmp_path / "models"
    diagrams = folder / "diagrams"
    diagrams.mkdir(parents=True)
    (folder / "model.sysml").write_text(
        "view structureView { render asTreeDiagram; }", encoding="utf-8"
    )
    body = "".join(
        f'<text>«comment»</text><text>Section note {index}</text>'
        for index in range(4)
    )
    (diagrams / "diagram-structureView.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg">{body}</svg>',
        encoding="utf-8",
    )

    markdown = render_markdown(folder)

    assert (
        "anonymous «comment» boxes" in markdown
        and "does not attach them to the elements they annotate" in markdown
    )


def test_all_published_diagrams_match_current_view_sets() -> None:
    for folder in PUBLISHED_VIEW_FOLDERS:
        collected = collect_views(folder)
        expected = {
            artifact_filename(spec.name, spec.view_type)
            for _, views in collected
            for spec in views
            if spec.name not in DIAGRAM_PUBLICATION_GAPS
        }
        actual = {path.name for path in (folder / "diagrams").glob("*.svg")}

        assert actual == expected, folder


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


def test_committed_artifact_checker_allows_only_unrendered_gap(
    tmp_path: Path,
) -> None:
    model = tmp_path / "models"
    generated = tmp_path / "generated"
    model.mkdir()
    generated.mkdir()
    (model / "model.sysml").write_text(
        "view mappingView : MVD::MatrixView {}", encoding="utf-8"
    )
    expected = "diagram-matrix-mappingView.svg"

    assert check_committed_view_artifacts(
        model, generated, allowed_missing={expected}
    ) == []

    (generated / expected).write_text("<svg/>", encoding="utf-8")
    assert check_committed_view_artifacts(
        model, generated, allowed_missing={expected}
    ) == [f"missing committed diagram: {model / 'diagrams' / expected}"]


def test_committed_artifact_checker_allows_only_nonmaterialized_svg(
    tmp_path: Path,
) -> None:
    model = tmp_path / "models"
    generated = tmp_path / "generated"
    model.mkdir()
    generated.mkdir()
    (model / "model.sysml").write_text(
        "view emptyView { expose Package::*; }", encoding="utf-8"
    )
    expected = "diagram-emptyView.svg"
    generated_svg = generated / expected
    generated_svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<text>«view» emptyView</text><text>expose Package::*</text></svg>',
        encoding="utf-8",
    )

    assert check_committed_view_artifacts(
        model, generated, allowed_nonmaterialized={expected}
    ) == []

    generated_svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<text>«view» emptyView</text><text>«part» materialized</text></svg>',
        encoding="utf-8",
    )
    assert check_committed_view_artifacts(
        model, generated, allowed_nonmaterialized={expected}
    ) == [f"missing committed diagram: {model / 'diagrams' / expected}"]


def test_privileged_workflow_rejects_stale_committed_diagrams() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "Check published view collections" in workflow
    assert "scripts/check_committed_view_artifacts.py" in workflow
    assert "scripts/generate_view_index.py" in workflow
    assert "git diff --exit-code" in workflow
    assert "--allow-missing" in workflow
    assert "--allow-nonmaterialized" in workflow
    for folder in PUBLISHED_VIEW_FOLDERS:
        assert folder.as_posix() in workflow
