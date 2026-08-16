"""Tests for the DE4SDV static HTML model viewer (tools/sysml_html_viewer).

Uses a synthetic hand-authored fixture under
``tests/fixtures/sysml_viewer_model`` — original test data, not a copy of any
real model file.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "sysml_viewer_model"

sys.path.insert(0, str(REPO_ROOT))
from tools.sysml_html_viewer.generate import generate  # noqa: E402
from tools.sysml_html_viewer.model_parse import (  # noqa: E402
    artifact_filename,
    build_member_index,
    build_tree,
    load_model,
    parse_file,
)
from tools.sysml_html_viewer import svg_info  # noqa: E402

# scripts/generate_view_index.py must stay in agreement with the viewer's
# view parsing; the parity test imports it directly.
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import generate_view_index  # noqa: E402


@pytest.fixture()
def model_files():
    return load_model(FIXTURE, ["textual-notation-of-model/packages"])


@pytest.fixture()
def fixture_sysml():
    return FIXTURE / "textual-notation-of-model/packages/features/fixture/fixture_feature.sysml"


def test_parse_members(fixture_sysml):
    mf = parse_file(fixture_sysml, FIXTURE)
    kinds = {m.kind for m in mf.members}
    assert {"package", "part def", "part", "requirement", "concern", "view"} <= kinds
    names = {m.name for m in mf.members}
    assert "FixtureSystem" in names
    assert "fixtureSystem" in names
    assert "'quoted part'" in names
    assert "FixtureAbstractPart" in names


def test_member_doc_attachment(fixture_sysml):
    mf = parse_file(fixture_sysml, FIXTURE)
    by_name = {m.name: m for m in mf.members}
    sys = by_name["FixtureSystem"]
    assert sys.doc.startswith("A synthetic system part definition")
    assert by_name["fixtureRequirement"].doc.startswith("Synthetic requirement")
    # nested ports are children of the part def
    assert {c.name for c in sys.children} == {"signalIn", "signalOut"}
    # view doc comes through the member declaration
    view_member = by_name["fixtureStructureView"]
    assert view_member.doc.startswith("Synthetic structure view")


def test_doc_attachment_no_leak_and_star_stripping(fixture_sysml):
    """Regression: a doc nested inside `require constraint` must not leak
    onto the next member, and block-comment ` * ` markers are stripped."""
    mf = parse_file(fixture_sysml, FIXTURE)
    by_name = {m.name: m for m in mf.members}
    # the constraint doc belongs to the constraint, not the concern
    assert by_name["fixtureAdjacentConcern"].doc == ""
    # the next concern keeps its own real doc, clean of comment markers
    assert by_name["fixtureTargetConcern"].doc == (
        "The real doc of the target concern, with a\nsecond line."
    )


def test_view_parsing(fixture_sysml):
    mf = parse_file(fixture_sysml, FIXTURE)
    views = {v.name: v for v in mf.views}
    assert set(views) == {"fixtureStructureView", "fixtureMatrixView"}
    sv = views["fixtureStructureView"]
    assert sv.viewpoint == "selectedFixtureViewpoint"
    assert sv.viewpoint_type == "FixtureViewpoint"
    assert sv.concern == "fixtureStructureConcern"
    assert sv.exposes == ["FixtureSystem"]
    assert sv.render == "asTreeDiagram"
    mv = views["fixtureMatrixView"]
    assert mv.view_type == "MVD::MatrixView"
    assert artifact_filename(mv.name, mv.view_type) == "diagram-matrix-fixtureMatrixView.svg"
    assert artifact_filename(sv.name, sv.view_type) == "diagram-fixtureStructureView.svg"


def test_view_parity_with_generate_view_index(fixture_sysml):
    """The viewer's view inventory must agree with scripts/generate_view_index."""
    mf = parse_file(fixture_sysml, FIXTURE)
    folder = fixture_sysml.parent
    collected = generate_view_index.collect_views(folder)
    assert len(collected) == 1
    _, index_views = collected[0]
    index_by_name = {v.name: v for v in index_views}
    assert set(index_by_name) == {v.name for v in mf.views}
    for v in mf.views:
        iv = index_by_name[v.name]
        assert iv.viewpoint == v.viewpoint
        assert iv.viewpoint_type == v.viewpoint_type
        assert iv.concern == v.concern
        assert iv.exposes == v.exposes
        assert iv.render == v.render
        assert iv.view_type == v.view_type


def test_build_tree(model_files):
    tree = build_tree(model_files)
    dirs = [c.label for c in tree.children]
    assert dirs == ["textual-notation-of-model"]
    packages = tree.children[0].children[0]
    assert packages.label == "packages"
    features = packages.children[0]
    assert features.label == "features"
    fixture = features.children[0]
    assert fixture.label == "fixture"
    file_node = fixture.children[0]
    assert file_node.label == "fixture_feature.sysml"
    child_kinds = {c.kind for c in file_node.children}
    assert "view" in child_kinds
    view_labels = {c.label for c in file_node.children if c.kind == "view"}
    assert view_labels == {"fixtureStructureView", "fixtureMatrixView"}


# --- hover enrichment -------------------------------------------------------


def test_extract_text_labels():
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg">'
        "<text x='1'>FixtureSystem</text>"
        "<text><tspan>fixtureSystem</tspan> : <tspan>FixtureSystem</tspan></text>"
        "<text>parts</text>"
        "<text>«part def»</text>"
        "</svg>"
    )
    labels = svg_info.extract_text_labels(svg)
    assert labels == [
        "FixtureSystem",
        "fixtureSystem : FixtureSystem",
        "parts",
        "«part def»",
    ]


def test_resolve_labels(model_files, fixture_sysml):
    index = build_member_index(model_files)
    labels = ["FixtureSystem", "fixtureSystem : FixtureSystem", "parts", "«part def»"]
    resolved = svg_info.resolve_labels(
        labels,
        index,
        view_file=fixture_sysml.relative_to(FIXTURE).as_posix(),
        view_folder="textual-notation-of-model/packages/features/fixture",
    )
    by_label = {r.label: r for r in resolved}
    assert by_label["FixtureSystem"].kind == "part def"
    assert by_label["FixtureSystem"].doc.startswith("A synthetic system part")
    assert by_label["fixtureSystem : FixtureSystem"].kind == "part"
    assert by_label["fixtureSystem : FixtureSystem"].name == "fixtureSystem"
    # layout text without a model match resolves to nothing
    assert "parts" not in by_label
    assert "«part def»" not in by_label


def test_inline_svg_and_hover_json_in_page(tmp_path):
    out = tmp_path / "site"
    generate(FIXTURE, out, ["textual-notation-of-model/packages"])
    file_page = (
        out
        / "pages"
        / "textual-notation-of-model/packages/features/fixture/fixture_feature.sysml.html"
    )
    html = file_page.read_text(encoding="utf-8")
    # the committed diagram is inlined, not referenced via <img>
    assert '<div class="diagram-frame interactive"' in html
    assert "<svg xmlns=" in html
    assert "<img" not in html
    # hover JSON is embedded for the view with a diagram
    m = re.search(
        r'<script type="application/json" class="diagram-info" '
        r'data-for="fixtureStructureView">(.*?)</script>',
        html,
        re.S,
    )
    assert m is not None
    payload = json.loads(m.group(1))
    info = payload["FixtureSystem"]
    assert info["kind"] == "part def"
    assert info["href"].endswith("fixture_feature.sysml.html#member-FixtureSystem")
    # the matrix view has no committed diagram -> no hover JSON for it
    assert 'data-for="fixtureMatrixView"' not in html
    # viewer.js is shipped with the site
    assert (out / "assets" / "viewer.js").exists()
    assert 'src="../../../../../assets/viewer.js"' in html


def test_active_path_chain_stays_open(tmp_path):
    """Regression: the tree on a file page must keep the whole ancestor
    chain of the active file open (root > dirs > file), not just the root."""
    out = tmp_path / "site"
    generate(FIXTURE, out, ["textual-notation-of-model/packages"])
    file_page = (
        out
        / "pages"
        / "textual-notation-of-model/packages/features/fixture/fixture_feature.sysml.html"
    )
    html = file_page.read_text(encoding="utf-8")
    # every dir on the path to the active file is open
    for label in ("textual-notation-of-model", "packages", "features", "fixture"):
        m = re.search(
            r'<details class="tree-node tree-dir" open>.*?'
            rf'<a href="[^"]*">{re.escape(label)}</a>',
            html,
            re.S,
        )
        assert m is not None, f"dir {label} not open on the file page"
    # the active file node itself is open and marked active
    m = re.search(
        r'<details class="tree-node tree-file active" open>.*?'
        r"fixture_feature\.sysml</a>",
        html,
        re.S,
    )
    assert m is not None


def _collect_links(html: str) -> list[str]:
    hrefs = re.findall(r'href="([^"]+)"', html)
    srcs = re.findall(r'src="([^"]+)"', html)
    return hrefs + srcs


def test_generate_site_and_links(tmp_path):
    """Generate the site from the fixture; every relative link must resolve."""
    out = tmp_path / "site"
    rc = generate(FIXTURE, out, ["textual-notation-of-model/packages"])
    assert rc == 0
    pages = sorted(out.rglob("*.html"))
    assert len(pages) >= 3  # index + dir page(s) + file page
    # index exists and contains the tree
    index = (out / "index.html").read_text(encoding="utf-8")
    assert "DE4SDV systems model" in index
    assert "fixture_feature.sysml" in index
    # file page: view section with embedded SVG and placeholder matrix view
    file_page = (
        out
        / "pages"
        / "textual-notation-of-model/packages/features/fixture/fixture_feature.sysml.html"
    )
    html = file_page.read_text(encoding="utf-8")
    assert 'id="view-fixtureStructureView"' in html
    assert "diagram-fixtureStructureView.svg" in html
    assert 'id="view-fixtureMatrixView"' in html
    assert "No committed diagram" in html
    assert "quoted part" in html
    # all relative links resolve (strip #fragments, skip external/mailto)
    for page in pages:
        text = page.read_text(encoding="utf-8")
        for link in _collect_links(text):
            if link.startswith(("http://", "https://", "mailto:")):
                continue
            path_part = link.split("#", 1)[0]
            if not path_part:
                continue
            target = (page.parent / path_part).resolve()
            assert target.exists(), f"broken link {link!r} from {page.name}"


def test_generate_deterministic(tmp_path):
    out1 = tmp_path / "site1"
    out2 = tmp_path / "site2"
    assert generate(FIXTURE, out1, ["textual-notation-of-model/packages"]) == 0
    assert generate(FIXTURE, out2, ["textual-notation-of-model/packages"]) == 0
    files1 = {p.relative_to(out1).as_posix() for p in out1.rglob("*.html")}
    files2 = {p.relative_to(out2).as_posix() for p in out2.rglob("*.html")}
    assert files1 == files2
    for rel in files1:
        a = (out1 / rel).read_bytes()
        b = (out2 / rel).read_bytes()
        assert a == b, f"non-deterministic output for {rel}"
