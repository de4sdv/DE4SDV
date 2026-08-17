"""Tests for the DE4SDV static HTML model viewer (tools/sysml_html_viewer).

Uses a synthetic hand-authored fixture under
``tests/fixtures/sysml_viewer_model`` — original test data, not a copy of any
real model file.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
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
    # `exhibit state X {` indexes the exhibited usage under its real name
    assert "fixtureLifecycle" in names
    assert {m.kind for m in mf.members if m.name == "fixtureLifecycle"} == {"state"}
    assert "fixtureIdle" in names


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
    # every declared member is listed (any nesting depth), packages are not
    member_labels = {c.label for c in file_node.children if c.kind != "view"}
    assert "fixtureSystem" in member_labels
    assert "signalIn" in member_labels  # port nested inside a part def
    assert "signalOut" in member_labels
    assert "RootLevelPart" in member_labels
    assert "FixtureRoot" not in member_labels  # packages are containers
    assert "Features" not in member_labels
    # the kind of every element is written out next to its name
    member_meta = {c.label: c.meta for c in file_node.children if c.kind != "view"}
    assert member_meta["fixtureSystem"] == "part"
    assert member_meta["signalIn"] == "port"
    assert member_meta["RootLevelPart"] == "part def"
    assert member_meta["fixtureRequirement"] == "requirement"
    view_meta = {c.label: c.meta for c in file_node.children if c.kind == "view"}
    assert view_meta["fixtureStructureView"].startswith("view · asTreeDiagram")


# --- hover enrichment -------------------------------------------------------


def test_extract_text_labels():
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg">'
        "<text x='1'>FixtureSystem</text>"
        "<text><tspan>fixtureSystem</tspan> : <tspan>FixtureSystem</tspan></text>"
        "<text>parts</text>"
        "<text>«part def»</text>"
        "<text>FixtureSystem :&gt; FixtureSuperType</text>"
        "<text>expose FixtureSystem::signalIn</text>"
        "</svg>"
    )
    labels = svg_info.extract_text_labels(svg)
    assert labels == [
        "FixtureSystem",
        "fixtureSystem : FixtureSystem",
        "parts",
        "«part def»",
        "FixtureSystem :> FixtureSuperType",
        "expose FixtureSystem::signalIn",
    ]


def test_resolve_labels(model_files, fixture_sysml):
    index = build_member_index(model_files)
    labels = [
        "FixtureSystem",
        "fixtureSystem : FixtureSystem",
        "parts",
        "«part def»",
        # specializer suffix (extract_text_labels unescapes the &gt; form)
        "FixtureSystem :> FixtureSuperType",
        # qualified path resolves by root name
        "expose FixtureSystem::signalIn",
        "expose FixtureSystem::'quoted part'",
        # redefines marker, dotted deployment path
        "^fixtureSystem.signalIn",
        # relationship / stakeholder usages
        "fixtureDependency",
        "fixtureStakeholder",
        # package name in an expose
        "expose FixtureRoot::*",
        # exhibited usage: plain label and plural-usage label
        "fixtureLifecycle",
        "states fixtureLifecycle",
        # stereotype/layout headers stay inert
        "exhibit states",
    ]
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
    # specializer resolves to the part def
    assert by_label["FixtureSystem :> FixtureSuperType"].name == "FixtureSystem"
    # qualified expose resolves by root name
    assert by_label["expose FixtureSystem::signalIn"].name == "FixtureSystem"
    assert by_label["expose FixtureSystem::'quoted part'"].name == "FixtureSystem"
    # redefines marker stripped; dotted path resolves by first segment
    assert by_label["^fixtureSystem.signalIn"].name == "fixtureSystem"
    assert by_label["^fixtureSystem.signalIn"].kind == "part"
    # relationship and stakeholder usages resolve
    assert by_label["fixtureDependency"].kind == "dependency"
    assert by_label["fixtureStakeholder"].kind == "stakeholder"
    # package exposes resolve to the package
    assert by_label["expose FixtureRoot::*"].kind == "package"
    assert by_label["expose FixtureRoot::*"].name == "FixtureRoot"
    # exhibited usage resolves under its real name (kind state)
    assert by_label["fixtureLifecycle"].kind == "state"
    assert by_label["states fixtureLifecycle"].name == "fixtureLifecycle"
    # the 'exhibit states' header label stays inert
    assert "exhibit states" not in by_label
    # layout text without a model match resolves to nothing
    assert "parts" not in by_label
    assert "«part def»" not in by_label


def test_revision_picker_in_pages(tmp_path):
    """Every page carries the revision picker; the option hrefs are relative
    to that page and always resolve (they are crawled by the link test)."""
    out = tmp_path / "site"
    generate(FIXTURE, out, ["textual-notation-of-model/packages"])
    index = (out / "index.html").read_text(encoding="utf-8")
    assert 'id="refPicker"' in index
    # single build -> one selected option labeled working tree
    assert re.search(r'<option value="index\.html" selected>working tree</option>', index)
    file_page = (
        out
        / "pages"
        / "textual-notation-of-model/packages/features/fixture/fixture_feature.sysml.html"
    )
    html = file_page.read_text(encoding="utf-8")
    # the same picker, with a value that walks back up to the site root
    assert re.search(r'<option value="(\.\./)+index\.html" selected>working tree</option>', html)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True
    )


def _make_fixture_repo(tmp_path: Path) -> Path:
    """A real (tiny) git repository containing the viewer fixture tree."""
    repo = tmp_path / "repo"
    repo.mkdir()
    shutil.copytree(FIXTURE, repo, dirs_exist_ok=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=Test", "-c", "user.email=test@example.com",
         "commit", "-q", "-m", "init")
    return repo


def test_generate_with_git_refs(tmp_path):
    """--refs builds a complete sub-site per revision from git itself; the
    picker switches between the working tree and each ref."""
    repo = _make_fixture_repo(tmp_path)
    # a feature branch with an extra model file
    extra = (
        repo
        / "textual-notation-of-model/packages/features/fixture/extra_feature.sysml"
    )
    _git(repo, "checkout", "-q", "-b", "feature")
    extra.write_text(
        "package FixtureExtraPackage {\n  part def ExtraPart;\n}\n",
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=Test", "-c", "user.email=test@example.com",
         "commit", "-q", "-m", "add extra feature")
    _git(repo, "checkout", "-q", "main")

    out = tmp_path / "site"
    rc = generate(repo, out, ["textual-notation-of-model/packages"], refs="feature")
    assert rc == 0

    # working-tree site (branch main) has no extra file
    index = (out / "index.html").read_text(encoding="utf-8")
    assert "extra_feature.sysml" not in index
    assert re.search(r'<option value="index\.html" selected>working tree · main</option>', index)
    assert re.search(r'<option value="refs/feature/index\.html">feature</option>', index)
    # main is current, so the picker lists no disabled entries and no
    # static-serving note (no buildable revision is missing)
    assert "not built" not in index
    assert "served statically" not in index

    # the feature sub-site contains the extra file
    ref_index = (out / "refs" / "feature" / "index.html").read_text(encoding="utf-8")
    assert "extra_feature.sysml" in ref_index
    assert re.search(r'<option value="index\.html" selected>feature</option>', ref_index)
    # from the ref sub-site the working tree is reachable
    assert re.search(r'<option value="\.\./\.\./index\.html">working tree · main</option>', ref_index)

    # every relative link in the ref sub-site resolves
    pages = sorted((out / "refs" / "feature").rglob("*.html"))
    assert len(pages) >= 4
    for page in pages:
        text = page.read_text(encoding="utf-8")
        for link in _collect_links(text):
            if link.startswith(("http://", "https://", "mailto:")):
                continue
            path_part = link.split("#", 1)[0].split("?", 1)[0]
            if not path_part:
                continue
            target = (page.parent / path_part).resolve()
            assert target.exists(), f"broken link {link!r} from {page}"
    # no git remote -> no PR labels; branch names are the labels
    assert "PR #" not in ref_index


def test_generate_with_remote_only_ref(tmp_path):
    """auto (default refs) includes branches that exist only on the remote
    (origin/<name>) — PR branches are typically not checked out locally."""
    repo = _make_fixture_repo(tmp_path)
    # a bare remote, and a branch that only lives there
    remote = tmp_path / "remote.git"
    _git(repo, "init", "-q", "--bare", str(remote))
    _git(repo, "checkout", "-q", "-b", "feature")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=Test", "-c", "user.email=test@example.com",
         "commit", "-q", "-m", "feature work")
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-q", "-u", "origin", "feature")
    _git(repo, "checkout", "-q", "main")
    _git(repo, "branch", "-q", "-D", "feature")

    out = tmp_path / "site"
    rc = generate(repo, out, ["textual-notation-of-model/packages"], refs="auto")
    assert rc == 0
    ref_index = (out / "refs" / "feature" / "index.html").read_text(encoding="utf-8")
    assert re.search(r'<option value="index\.html" selected>feature</option>', ref_index)


def test_generate_public_mode(tmp_path):
    """--public labels the root build with the plain branch name — a
    published snapshot must not expose the local 'working tree' concept."""
    repo = _make_fixture_repo(tmp_path)
    _git(repo, "checkout", "-q", "-b", "feature")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=Test", "-c", "user.email=test@example.com",
         "commit", "-q", "-m", "feature work")
    _git(repo, "checkout", "-q", "main")
    out = tmp_path / "site"
    rc = generate(
        repo, out, ["textual-notation-of-model/packages"],
        refs="feature", public=True,
    )
    assert rc == 0
    index = (out / "index.html").read_text(encoding="utf-8")
    assert re.search(r'<option value="index\.html" selected>main</option>', index)
    assert "working tree" not in index
    assert re.search(r'<option value="refs/feature/index\.html">feature</option>', index)


def test_unbuilt_buildable_ref_shows_hint(tmp_path):
    """A buildable branch that was not built appears disabled with the
    regenerate command, and the page shows the static-serving note."""
    repo = _make_fixture_repo(tmp_path)
    _git(repo, "checkout", "-q", "-b", "other")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=Test", "-c", "user.email=test@example.com",
         "commit", "-q", "-m", "other branch")
    _git(repo, "checkout", "-q", "main")

    out = tmp_path / "site"
    rc = generate(repo, out, ["textual-notation-of-model/packages"], refs=None)
    assert rc == 0
    index = (out / "index.html").read_text(encoding="utf-8")
    assert re.search(
        r'<option value="" disabled title="[^"]*--refs other[^"]*">'
        r"other \(not built\)</option>",
        index,
    )
    assert "served statically" in index



def test_generate_skips_ref_without_model(tmp_path):
    """Refs that contain no .sysml under the model roots are skipped: the
    build stays green and the picker never lists a broken site."""
    repo = _make_fixture_repo(tmp_path)
    _git(repo, "checkout", "-q", "-b", "docs-only")
    (repo / "README.md").write_text("# docs only\n", encoding="utf-8")
    _git(repo, "rm", "-q", "-r", "textual-notation-of-model")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=Test", "-c", "user.email=test@example.com",
         "commit", "-q", "-m", "docs only")
    _git(repo, "checkout", "-q", "main")

    out = tmp_path / "site"
    rc = generate(repo, out, ["textual-notation-of-model/packages"], refs="docs-only")
    assert rc == 0
    index = (out / "index.html").read_text(encoding="utf-8")
    assert "refs/docs-only" not in index
    assert not (out / "refs" / "docs_only").exists()
    # the branch is still known: a disabled picker entry explains why it
    # cannot be shown (no model content), and no static-serving note appears
    # because nothing buildable is missing
    assert re.search(
        r'<option value="" disabled title="[^"]*no \.sysml under the validated[^"]*">'
        r"docs-only \(no model content\)</option>",
        index,
    )
    assert "served statically" not in index


def test_serve_on_demand(tmp_path):
    """Server mode: /_refs lists every revision; unbuilt refs generate on
    the first request and are cached afterwards."""
    repo = _make_fixture_repo(tmp_path)
    extra = (
        repo
        / "textual-notation-of-model/packages/features/fixture/extra_feature.sysml"
    )
    _git(repo, "checkout", "-q", "-b", "feature")
    extra.write_text(
        "package FixtureExtraPackage {\n  part def ExtraPart;\n}\n",
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=Test", "-c", "user.email=test@example.com",
         "commit", "-q", "-m", "extra")
    _git(repo, "checkout", "-q", "main")

    from tools.sysml_html_viewer import serve

    out = tmp_path / "site"
    server = serve.make_server(repo, out, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    base = f"http://127.0.0.1:{port}"
    try:
        # manifest: working tree + every branch
        with urllib.request.urlopen(base + "/_refs") as r:
            data = json.loads(r.read())
        assert any(x["id"] == "" for x in data["refs"])  # working tree
        labels = {x["label"] for x in data["refs"]}
        assert "feature" in labels
        # built flags: working tree built, feature not yet
        feature_entry = next(x for x in data["refs"] if x["id"] == "feature")
        assert feature_entry["built"] is False
        work_entry = next(x for x in data["refs"] if x["id"] == "")
        assert work_entry["built"] is True
        # working tree site is served (generated on first start), stamped
        # with the server marker so the picker JS enables dynamic mode
        with urllib.request.urlopen(base + "/index.html") as r:
            body = r.read().decode()
        assert "DE4SDV" in body
        assert "__DE4SDV_VIEWER_SERVER__" in body
        # unbuilt ref generates on demand
        with urllib.request.urlopen(base + "/refs/feature/index.html", timeout=120) as r:
            body = r.read().decode()
        assert "extra_feature.sysml" in body
        assert "__DE4SDV_VIEWER_SERVER__" in body  # marker on ref pages too
        # ... and the manifest now reports it as built
        with urllib.request.urlopen(base + "/_refs") as r:
            data = json.loads(r.read())
        feature_entry = next(x for x in data["refs"] if x["id"] == "feature")
        assert feature_entry["built"] is True
        # ... and is cached: the second request is fast
        t0 = time.monotonic()
        with urllib.request.urlopen(base + "/refs/feature/index.html") as r:
            r.read()
        assert time.monotonic() - t0 < 2
        # unknown ref -> 404
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(base + "/refs/nope/index.html")
        assert exc_info.value.code == 404
        # working-tree model changes are picked up automatically: editing a
        # .sysml file makes the next request regenerate the served site
        feature_file = (
            repo
            / "textual-notation-of-model/packages/features/fixture/fixture_feature.sysml"
        )
        feature_file.write_text(
            feature_file.read_text(encoding="utf-8")
            + "\npart def WorktreeAddedPart;\n",
            encoding="utf-8",
        )
        page_url = (
            base
            + "/pages/textual-notation-of-model/packages/features/fixture/"
            + "fixture_feature.sysml.html"
        )
        with urllib.request.urlopen(page_url, timeout=120) as r:
            body = r.read().decode()
        assert "WorktreeAddedPart" in body
        # viewer code updates make stale sites rebuild: touching the tool's
        # viewer.js marks every built site stale until regenerated
        tool_js = REPO_ROOT / "tools/sysml_html_viewer/viewer.js"
        old_mtime = tool_js.stat().st_mtime
        os.utime(tool_js, (time.time() + 10, time.time() + 10))
        try:
            with urllib.request.urlopen(base + "/_refs") as r:
                data = json.loads(r.read())
            feature_entry = next(x for x in data["refs"] if x["id"] == "feature")
            assert feature_entry["built"] is False  # stale -> unbuilt
            # requesting the ref page still serves it (rebuilding first)
            with urllib.request.urlopen(base + "/refs/feature/index.html", timeout=120) as r:
                assert "extra_feature.sysml" in r.read().decode()
        finally:
            os.utime(tool_js, (old_mtime, old_mtime))
        # once the tool code is back to normal, the ref is current again
        with urllib.request.urlopen(base + "/_refs") as r:
            data = json.loads(r.read())
        feature_entry = next(x for x in data["refs"] if x["id"] == "feature")
        assert feature_entry["built"] is True
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_inline_svg_and_hover_json_in_page(tmp_path):
    out = tmp_path / "site"
    generate(FIXTURE, out, ["textual-notation-of-model/packages"])
    file_page = (
        out
        / "pages"
        / "textual-notation-of-model/packages/features/fixture/fixture_feature.sysml.html"
    )
    html = file_page.read_text(encoding="utf-8")
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
    assert re.search(r"fixture_feature\.sysml\.html#src-\d+$", info["href"])
    # the matrix view has no committed diagram -> no hover JSON for it
    assert 'data-for="fixtureMatrixView"' not in html
    # viewer.js is shipped with the site, stamped against stale caches
    assert (out / "assets" / "viewer.js").exists()
    assert re.search(r'src="\.\./\.\./\.\./\.\./\.\./assets/viewer\.js\?v=[0-9a-f]{10}"', html)


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
            r'<details class="tree-node tree-dir" open[^>]*>.*?'
            rf'<a href="[^"]*">{re.escape(label)}</a>',
            html,
            re.S,
        )
        assert m is not None, f"dir {label} not open on the file page"
    # the active file node itself is open and marked active
    m = re.search(
        r'<details class="tree-node tree-file active" open[^>]*>.*?'
        r"fixture_feature\.sysml</a>",
        html,
        re.S,
    )
    assert m is not None


def test_source_view_only(tmp_path):
    """File pages show only the highlighted source below the diagrams —
    no members list, no Source/Members tab switch."""
    out = tmp_path / "site"
    generate(FIXTURE, out, ["textual-notation-of-model/packages"])
    file_page = (
        out
        / "pages"
        / "textual-notation-of-model/packages/features/fixture/fixture_feature.sysml.html"
    )
    html = file_page.read_text(encoding="utf-8")
    # no tabs, no members pane
    assert "tab-source" not in html
    assert "tab-members" not in html
    assert "pane-members" not in html
    assert "member-list" not in html
    assert "member-node" not in html
    # source pane: actual file content, numbered lines, highlighted tokens
    assert 'class="source-view"' in html
    assert "FixtureRoot" in html  # keyword is span-wrapped, name is plain
    assert re.search(r'class="src-kw">package</span>', html)
    assert re.search(r'class="src-cmt">', html)
    assert re.search(r'id="src-1"', html)
    line_count = len(re.findall(r'class="src-line"', html))
    assert line_count >= 40  # fixture file length
    # regression: multi-line comments must not nest later lines inside the
    # first line's block (every src-line is a direct child of the pre)
    pre_m = re.search(r'<pre class="source-view">(.*?)</pre>', html, re.S)
    assert pre_m is not None
    pre_body = pre_m.group(1)
    assert pre_body.count("<span") == pre_body.count("</span>")
    assert "src-cmt" in pre_body
    # regression: no newline between line blocks — inside a white-space:pre
    # <pre> a newline between blocks renders as an extra line box (doubled
    # perceived line spacing)
    assert "\n" not in pre_body
    # no comment span may contain a newline (would break line wrapping)
    for cmt in re.findall(r'<span class="src-cmt">(.*?)</span>', pre_body, re.S):
        assert "\n" not in cmt


def test_member_links_target_source_lines(tmp_path):
    """Tree member nodes and hover JSON jump to declaration lines (#src-N)."""
    out = tmp_path / "site"
    generate(FIXTURE, out, ["textual-notation-of-model/packages"])
    file_page = (
        out
        / "pages"
        / "textual-notation-of-model/packages/features/fixture/fixture_feature.sysml.html"
    )
    html = file_page.read_text(encoding="utf-8")
    # tree member links point at source lines
    assert re.search(r'href="[^"]*fixture_feature\.sysml\.html#src-\d+"', html)
    # hover JSON hrefs for members also point at source lines
    m = re.search(
        r'<script type="application/json" class="diagram-info" '
        r'data-for="fixtureStructureView">(.*?)</script>',
        html,
        re.S,
    )
    assert m is not None
    payload = json.loads(m.group(1))
    info = payload["FixtureSystem"]
    assert re.search(r"fixture_feature\.sysml\.html#src-\d+$", info["href"])
    # the view itself still links to its section anchor (tree)
    assert "#view-fixtureStructureView" in html


def test_source_refs_link_to_definitions(tmp_path):
    """Identifiers in the source that resolve to model elements become
    references: cross-file ones jump to the defining file, same-file usages
    jump within the page; declarations themselves are not annotated."""
    out = tmp_path / "site"
    generate(FIXTURE, out, ["textual-notation-of-model/packages"])
    file_page = (
        out
        / "pages"
        / "textual-notation-of-model/packages/features/fixture/fixture_feature.sysml.html"
    )
    html = file_page.read_text(encoding="utf-8")
    # cross-file reference: SignalInputPort is declared in fixture_shared.sysml
    m = re.search(
        r'<a class="src-ref" href="([^"]*fixture_shared\.sysml\.html#src-\d+)" '
        r'data-tip-kind="part def" data-tip-name="SignalInputPort"[^>]*>'
        r"SignalInputPort</a>",
        html,
    )
    assert m is not None
    target = (file_page.parent / m.group(1).split("#", 1)[0]).resolve()
    assert target.exists()
    # ... as is the explicitly imported type
    assert re.search(
        r'<a class="src-ref" href="[^"]*fixture_shared\.sysml\.html#src-\d+" '
        r'[^>]*data-tip-name="FixtureSharedType"',
        html,
    )
    # same-file usage (expose FixtureSystem) jumps within the page
    assert re.search(
        r'<a class="src-ref" href="#src-13" data-tip-kind="part def" '
        r'data-tip-name="FixtureSystem"',
        html,
    )
    # the declaration line itself is not annotated
    seg = html[html.find('id="src-13"'): html.find('id="src-14"')]
    assert "src-ref" not in seg
    # exactly the four usages of FixtureSystem are annotated (typed parts,
    # expose statements), not the declaration
    assert html.count('data-tip-name="FixtureSystem"') == 4


def test_tree_search(tmp_path):
    """The search box lives in the tree pane on every page and filters the
    tree in place (same layout); the whole-model index is not shipped as a
    separate asset anymore — the tree itself is the search space."""
    out = tmp_path / "site"
    generate(FIXTURE, out, ["textual-notation-of-model/packages"])
    assert not (out / "search.html").exists()
    assert not (out / "assets" / "search-index.js").exists()

    # root page: search box + status line in the tree pane, tree container
    index = (out / "index.html").read_text(encoding="utf-8")
    assert 'id="treeSearch"' in index
    assert 'id="treeSearchStatus"' in index
    assert 'id="treeNav"' in index
    assert 'id="treeSearchResults"' not in index
    # no separate index script tag on the page
    assert "search-index.js" not in index

    # nested file page: same input/status/tree, prefix-aware title link
    file_page = (
        out
        / "pages"
        / "textual-notation-of-model/packages/features/fixture/fixture_feature.sysml.html"
    ).read_text(encoding="utf-8")
    assert 'id="treeSearch"' in file_page
    assert 'id="treeSearchStatus"' in file_page
    assert 'id="treeNav"' in file_page
    assert "search-index.js" not in file_page
    # no header search link / no-tree remnants
    assert "site-search-link" not in file_page
    assert "no-tree" not in file_page
    # the header title links back to the site index (prefix-aware)
    assert '<a class="site-title" href="../../../../../index.html">' in file_page


def test_tree_filters(tmp_path):
    """The tree pane carries kind/SAF-domain/SAF-aspect/viewpoint filters
    derived from the model, and every tree node carries the data-*
    attributes the filters operate on."""
    out = tmp_path / "site"
    generate(FIXTURE, out, ["textual-notation-of-model/packages"])
    index = (out / "index.html").read_text(encoding="utf-8")

    # four filter selects in the tree pane
    for sid in ("kindFilter", "domainFilter", "aspectFilter", "viewpointFilter"):
        assert f'id="{sid}"' in index, f"missing {sid}"
    # kind options come from the tree (members, views, files, dirs)
    for opt in ("part def", "view", "viewpoint def", "file", "dir"):
        assert f'<option value="{opt}">{opt}</option>' in index, f"missing kind {opt}"
    # SAF options come from the viewpoint def's doc comment
    assert '<option value="Fixture">Fixture</option>' in index
    assert '<option value="Test &amp; Sample">Test &amp; Sample</option>' in index
    assert '<option value="FixtureViewpoint">FixtureViewpoint</option>' in index
    assert 'id="clearFilters"' in index

    # view node carries kind + viewpoint + SAF domain/aspect attrs
    assert re.search(
        r'<details class="tree-node tree-file"[^>]*>.*?'
        r'data-kind="view" data-vp="FixtureViewpoint" '
        r'data-domain="Fixture" data-aspect="Test &amp; Sample"',
        index,
        re.S,
    ), "view node lacks SAF data attributes"
    # member and dir/file nodes carry their kind
    assert re.search(r'data-kind="part def"', index)
    assert re.search(r'data-kind="file"', index)
    assert re.search(r'data-kind="dir"', index)


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
            path_part = link.split("#", 1)[0].split("?", 1)[0]
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


