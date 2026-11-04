"""A view shows every concern it frames: its own and the inherited ones.

The viewer used to read the first `frame` of a view block and drop the rest,
so a view that frames several concerns showed one. A view also inherits the
concerns its viewpoint definition frames (and those of that definition's
`:>` specializations), which the viewer did not read at all.

Synthetic hand-authored fixture under ``tests/fixtures/sysml_viewer_frames``
— original test data, not a copy of any real model file.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "sysml_viewer_frames"
ROOTS = ["textual-notation-of-model/packages"]
FILE_REL = "textual-notation-of-model/packages/features/frames/frames_feature.sysml"

sys.path.insert(0, str(REPO_ROOT))
from tools.sysml_html_viewer.generate import generate  # noqa: E402
from tools.sysml_html_viewer.model_parse import load_model, parse_file  # noqa: E402


@pytest.fixture(scope="module")
def views():
    return {
        v.name: v
        for mf in load_model(FIXTURE, ROOTS)
        for v in mf.views
    }


def test_every_own_frame_is_parsed_in_order(views):
    """Three frames in the view's own viewpoint usage: all three, in order."""
    view = views["severalOwnFramesView"]
    assert [f.name for f in view.frames] == [
        "alphaConcern", "betaConcern", "gammaConcern"]
    assert [f.viewpoint_definition for f in view.frames] == ["", "", ""]


def test_frame_concern_form_names_the_concern_and_its_definition(views):
    """`frame concern x : X;` frames x, typed by X; `frame x;` frames x
    without a declared concern definition (the keyword `concern` is never
    taken for the name)."""
    frames = views["severalOwnFramesView"].frames
    assert frames[0].name == "alphaConcern"
    assert frames[0].concern_def == ""
    assert frames[1].name == "betaConcern"
    assert frames[1].concern_def == "BetaConcern"
    assert frames[2].name == "gammaConcern"
    assert frames[2].concern_def == ""


def test_frames_of_the_viewpoint_definition_are_inherited(views):
    """A viewpoint usage typed by a definition that frames a concern shows
    that concern, labelled with the definition it comes from."""
    view = views["inheritedOnlyView"]
    assert [f.name for f in view.frames] == ["baseConcern"]
    assert [f.viewpoint_definition for f in view.frames] == [
        "BaseFramingViewpoint"]
    # the concern definition travels with the inherited frame
    assert view.frames[0].concern_def == "BaseConcern"


def test_inheritance_through_specialization_of_viewpoint_definitions(views):
    """Frames of a definition reached through `:>` are inherited too, after
    the frames of the nearer definition; the usage's own frame comes first."""
    view = views["inheritedAndOwnView"]
    assert [f.name for f in view.frames] == [
        "alphaConcern", "midConcern", "baseConcern"]
    assert [f.viewpoint_definition for f in view.frames] == [
        "", "MidFramingViewpoint", "BaseFramingViewpoint"]
    assert view.frames[1].concern_def == "MidConcern"
    assert view.frames[2].concern_def == "BaseConcern"


def test_frame_word_in_comments_is_no_frame(views):
    """`frame ghostConcern;` in a doc comment, a block comment or a line
    comment frames nothing."""
    view = views["commentFramesView"]
    assert [f.name for f in view.frames] == ["alphaConcern"]


def test_a_viewpoint_with_no_frames_has_none(views):
    view = views["noFramesView"]
    assert view.frames == []
    assert view.own_frames == []
    assert view.inherited_frames == []


def test_reframing_an_inherited_concern_shows_it_once(views):
    """A usage that frames a concern its viewpoint definition also frames
    shows the concern once, as its own frame."""
    view = views["reframedInheritedView"]
    assert [f.name for f in view.frames] == ["baseConcern"]
    assert view.frames[0].viewpoint_definition == ""
    assert view.inherited_frames == []


def _page(tmp_path) -> str:
    out = tmp_path / "site"
    assert generate(FIXTURE, out, ROOTS) == 0
    page = out / "pages" / (FILE_REL + ".html")
    return page.read_text(encoding="utf-8").replace("<wbr>", "")


_OWN = "<span class='muted frame-origin'>own frame</span>"


def _section(html: str, view_name: str) -> str:
    marker = f'<section class="view-section" id="view-{view_name}">'
    start = html.index(marker)
    end = html.index("</section>", start)
    return html[start:end]


def test_page_lists_own_and_inherited_frames_with_their_origin(tmp_path):
    """The page names every frame, and a reader can tell an own frame from one
    inherited from a viewpoint definition."""
    section = _section(_page(tmp_path), "inheritedAndOwnView")
    assert "Framed concerns" in section
    for name in ("alphaConcern", "midConcern", "baseConcern"):
        assert f"<code>{name}</code>" in section
    # the model order: own frame, then the nearer definition, then its general
    assert (section.index("alphaConcern")
            < section.index("midConcern")
            < section.index("baseConcern"))
    assert section.count(_OWN) == 1
    assert ("frame inherited from viewpoint definition "
            "<code>MidFramingViewpoint</code>") in section
    assert ("frame inherited from viewpoint definition "
            "<code>BaseFramingViewpoint</code>") in section


def test_page_lists_all_own_frames_of_a_view(tmp_path):
    """A view with three own frames lists three, none of them inherited."""
    section = _section(_page(tmp_path), "severalOwnFramesView")
    assert section.count("<li>") == 3
    assert section.count(_OWN) == 3
    assert "inherited from viewpoint definition" not in section
    assert "<code>betaConcern</code>" in section


def test_page_has_no_framed_concerns_row_without_frames(tmp_path):
    """A view whose viewpoint frames no concern gets no framed-concerns row:
    the viewer shows what the model states and invents nothing. The row is
    absent because that view frames nothing — not because the viewer never
    writes one."""
    html = _page(tmp_path)
    assert "Framed concerns" in _section(html, "severalOwnFramesView")
    assert "Framed concerns" not in _section(html, "noFramesView")


def test_parse_file_reports_own_frames_only():
    """`parse_file` reads the frames a view states itself; inheritance needs
    the model-wide definitions, which `load_model` resolves."""
    mf = parse_file(FIXTURE / FILE_REL, FIXTURE)
    views = {v.name: v for v in mf.views}
    assert [f.name for f in views["inheritedOnlyView"].own_frames] == []
    assert views["inheritedOnlyView"].inherited_frames == []
    # the compatibility alias is the first own frame (the view index lists one)
    assert views["severalOwnFramesView"].concern == "alphaConcern"
