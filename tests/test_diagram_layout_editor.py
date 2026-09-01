"""Tests for the diagram layout editor (layout sidecar + apply + server API).

Uses the synthetic hand-authored fixture under ``tests/fixtures/
sysml_viewer_model`` — original test data, not a copy of any real model
file. The fixture diagram intentionally exercises every editable geometry
kind (text, box path, port-glyph square, polyline, open path).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "sysml_viewer_model"
SVG_REL = (
    "textual-notation-of-model/packages/features/fixture/"
    "diagrams/diagram-fixtureStructureView.svg"
)
sys.path.insert(0, str(REPO_ROOT))

from tools.sysml_html_viewer import layout_apply, layout_sidecar  # noqa: E402


@pytest.fixture()
def fixture_svg() -> Path:
    return FIXTURE / SVG_REL


@pytest.fixture()
def committed(fixture_svg) -> str:
    """Inlined markup (prologue stripped), the form the sidecar hashes."""
    import re

    text = fixture_svg.read_text(encoding="utf-8")
    return re.sub(r"^<\?xml[^>]*\?>", "", text).lstrip()


# ---------------------------------------------------------------------------
# sidecar storage


def test_sidecar_path_is_beside_diagrams_dir(fixture_svg):
    p = layout_sidecar.sidecar_for(fixture_svg)
    assert p.parent.name == layout_sidecar.LAYOUT_DIRNAME
    assert p.parent.parent == fixture_svg.parent
    assert p.name == fixture_svg.name + ".layout.json"


def test_save_load_roundtrip(fixture_svg, committed, tmp_path):
    layout = {"ops": [
        {"kind": "text", "find": "40,55", "op": {"x": 80.0, "y": 90.0}},
    ]}
    rec = layout_sidecar.save_layout(
        fixture_svg, layout_sidecar.sha256_text(committed), layout
    )
    assert rec["base_sha256"] == layout_sidecar.sha256_text(committed)
    loaded = layout_sidecar.load_layout(fixture_svg)
    assert loaded is not None
    assert loaded["layout"]["ops"][0]["find"] == "40,55"
    assert not layout_sidecar.is_stale(loaded, committed)
    assert layout_sidecar.delete_layout(fixture_svg)


def test_invalid_layout_rejected(fixture_svg):
    with pytest.raises(ValueError):
        layout_sidecar.save_layout(
            fixture_svg, "x" * 64,
            {"ops": [{"kind": "nope", "find": "1,2", "op": {}}]},
        )
    with pytest.raises(ValueError):
        layout_sidecar.save_layout(
            fixture_svg, "x" * 64,
            {"ops": [{"kind": "text", "find": "1,2", "op": {"x": "left"}}]},
        )
    with pytest.raises(ValueError):
        layout_sidecar.save_layout(
            fixture_svg, "x" * 64,
            {"ops": [{"kind": "boxes", "find": "1,2,3,4", "op": {"x1": 1}}]},
        )
    assert layout_sidecar.load_layout(fixture_svg) is None


def test_stale_detection_fail_closed(fixture_svg, committed):
    layout = {"ops": [
        {"kind": "text", "find": "40,55", "op": {"x": 80.0, "y": 90.0}},
    ]}
    layout_sidecar.save_layout(fixture_svg, "0" * 64, layout)
    loaded = layout_sidecar.load_layout(fixture_svg)
    assert layout_sidecar.is_stale(loaded, committed)
    layout_sidecar.delete_layout(fixture_svg)


# ---------------------------------------------------------------------------
# geometry engine


def test_text_move_rewrite(committed):
    layout = {"ops": [{"kind": "text", "find": "40,55", "op": {"x": 64, "y": 77}}]}
    new, notes = layout_apply.apply_layout(committed, layout)
    assert notes == []
    assert 'x="64"' in new and 'y="77"' in new
    assert 'x="40"' not in new.split("FixtureSystem")[0].split("<text")[-1]


def test_text_font_size_rewrite(committed):
    layout = {"ops": [
        {"kind": "text", "find": "40,55", "op": {"x": 40, "y": 55, "font-size": 14}},
    ]}
    new, notes = layout_apply.apply_layout(committed, layout)
    assert notes == []
    assert 'font-size="14"' in new


def test_box_resize_moves_companions(committed):
    # boxPart box: M 30,160 H 130 ... -> 24..136 x 160..196 (rounded box)
    key = "24,160,136,196"
    layout = {"ops": [
        {"kind": "boxes", "find": key, "op": {"x1": 60, "y1": 160, "x2": 200, "y2": 240}},
    ]}
    new, notes = layout_apply.apply_layout(committed, layout)
    assert notes == []
    # regenerated rounded header (radius 6): starts at x1+6
    assert "M 66,160" in new
    # the box owner label (45,178 -> inside old box) moves proportionally:
    # x: 60 + (45-24)*(140/112) = 86.25, y: 160 + (178-160)*(80/36) = 200
    assert 'x="86.25"' in new and 'y="200"' in new


def test_connector_reroute(committed):
    # signalBridge separator polyline: points="30,120 170,120"
    layout = {"ops": [
        {"kind": "connectors", "find": "30,120 170,120",
         "op": {"points": [[10, 10], [200, 140]]}},
    ]}
    new, notes = layout_apply.apply_layout(committed, layout)
    assert notes == []
    assert 'points="10,10 200,140"' in new


def test_open_path_reroute(committed):
    d = "M 150 50 C 200 50 190 140 170 140"
    # curved path is NOT editable: apply refuses and reports the op
    layout = {"ops": [
        {"kind": "paths", "find": d, "op": {"d": "M 10 10 L 20 20"}},
    ]}
    new, notes = layout_apply.apply_layout(committed, layout)
    assert notes and "unsupported" in notes[0]
    assert d in new  # unchanged


def test_svg_canvas_resize(committed):
    layout = {"ops": [
        {"kind": "svg", "op": {"width": 400, "height": 300, "viewBox": "0 0 400 300"}},
    ]}
    new, notes = layout_apply.apply_layout(committed, layout)
    assert notes == []
    assert 'width="400"' in new and 'height="300"' in new
    assert 'viewBox="0 0 400 300"' in new


def test_sequential_ops_second_uses_new_geometry(committed):
    layout = {"ops": [
        {"kind": "text", "find": "40,55", "op": {"x": 80, "y": 90}},
        {"kind": "text", "find": "80,90", "op": {"x": 120, "y": 60}},
    ]}
    new, notes = layout_apply.apply_layout(committed, layout)
    assert notes == []
    assert 'x="120"' in new and 'y="60"' in new


def test_stale_key_reports_note_and_skips(committed):
    layout = {"ops": [
        {"kind": "text", "find": "999,999", "op": {"x": 1, "y": 2}},
        {"kind": "text", "find": "40,55", "op": {"x": 60, "y": 66}},
    ]}
    new, notes = layout_apply.apply_layout(committed, layout)
    assert len(notes) == 1
    assert "999,999" in notes[0]
    assert 'x="60"' in new


def test_apply_is_pure(committed):
    layout = {"ops": [
        {"kind": "text", "find": "40,55", "op": {"x": 64, "y": 77}},
    ]}
    layout_apply.apply_layout(committed, layout)
    assert 'x="40"' in committed  # input untouched


def test_real_model_box_resize_end_to_end():
    """The committed AEBS structure view: resize the big part box and verify
    the regenerated rounded-box geometry + moved separators."""
    real = REPO_ROOT / (
        "textual-notation-of-model/packages/features/aebs/diagrams/"
        "diagram-aebsSystemStructureView.svg"
    )
    if not real.is_file():
        pytest.skip("real model checkout not present")
    import re

    text = re.sub(r"^<\?xml[^>]*\?>", "", real.read_text(encoding="utf-8")).lstrip()
    layout = {"ops": [
        {"kind": "boxes", "find": "28,368,343,709",
         "op": {"x1": 100, "y1": 380, "x2": 500, "y2": 760}},
    ]}
    new, notes = layout_apply.apply_layout(text, layout)
    assert notes == []
    assert "M 106,380" in new
    # separator 28,404 343,404 was inside; proportional map: y 368->380,
    # scale 380/341 -> 420.12
    assert 'points="100,420.12 500,420.12"' in new


# ---------------------------------------------------------------------------
# rendered page integration


def _render_fixture_site(tmp_path, editable: bool = False) -> Path:
    out = tmp_path / "site"
    from tools.sysml_html_viewer.generate import generate

    rc = generate(
        FIXTURE, out,
        ["textual-notation-of-model/packages"],
        refs=None, prs=False, editable=editable,
    )
    assert rc == 0
    return out


FIXTURE_PAGE = (
    "pages/textual-notation-of-model/packages/features/fixture/"
    "fixture_feature.sysml.html"
)


def test_page_without_sidecar_has_no_edit_assets(tmp_path):
    out = _render_fixture_site(tmp_path)
    html = (out / FIXTURE_PAGE).read_text(encoding="utf-8")
    assert "diagram-edit-btn" not in html          # not editable without ctx
    assert "editor_layout" not in html


def test_editable_page_embeds_payload_and_button(tmp_path):
    out = _render_fixture_site(tmp_path, editable=True)
    html = (out / FIXTURE_PAGE).read_text(encoding="utf-8")
    assert 'class="diagram-edit-btn" hidden' in html
    assert 'class="diagram-layout" data-for=' in html
    assert "assets/editor_layout.js" in html
    assert "assets/editor_layout.css" in html
    # payload carries the committed geometry maps
    m = re.search(
        r'<script type="application/json" class="diagram-layout" data-for="[^"]+">(.*?)</script>',
        html, re.S,
    )
    assert m is not None, "diagram-layout payload missing"
    payload = json.loads(m.group(1).replace("<\\/", "</"))
    assert payload["orig"]["text"], "orig text map must not be empty"
    assert any("24,160" in k for k in payload["orig"]["boxes"])


def test_editable_page_applies_saved_sidecar(tmp_path):
    fixture_svg = FIXTURE / SVG_REL
    committed = re.sub(
        r"^<\?xml[^>]*\?>", "",
        fixture_svg.read_text(encoding="utf-8"),
    ).lstrip()
    layout_sidecar.save_layout(
        fixture_svg, layout_sidecar.sha256_text(committed),
        {"ops": [{"kind": "text", "find": "40,55", "op": {"x": 90, "y": 95}}]},
    )
    try:
        out = _render_fixture_site(tmp_path, editable=True)
        html = (out / FIXTURE_PAGE).read_text(encoding="utf-8")
        assert 'x="90"' in html and 'y="95"' in html
        # hover JSON is built from the APPLIED markup (tooltip positions match)
        assert '"90,95"' in html
    finally:
        layout_sidecar.delete_layout(fixture_svg)


# ---------------------------------------------------------------------------
# server API


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True, capture_output=True,
    )


@pytest.fixture()
def fixture_repo(tmp_path):
    """Synthetic fixture as a real git repo (serve.py requires one)."""
    repo = tmp_path / "repo"
    shutil_ignore = None  # noqa: F841
    import shutil

    shutil.copytree(FIXTURE, repo)
    _git(repo, "init", "-q")
    _git(repo, "-c", "user.name=Test", "-c", "user.email=test@example.com",
         "add", "-A")
    _git(repo, "-c", "user.name=Test", "-c", "user.email=test@example.com",
         "commit", "-q", "-m", "fixture")
    return repo


def test_layout_api_roundtrip_and_guards(fixture_repo, tmp_path):
    from tools.sysml_html_viewer import serve

    out = tmp_path / "site"
    server = serve.make_server(fixture_repo, out, port=0, editable=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    base = f"http://127.0.0.1:{port}"
    url = f"{base}/diagram-layout/{SVG_REL}"
    try:
        # GET with no sidecar
        with urllib.request.urlopen(url) as r:
            data = json.loads(r.read())
        assert data["layout"] is None
        base_hash = data["base"]

        # PUT stores it
        layout = {"ops": [
            {"kind": "text", "find": "40,55", "op": {"x": 100, "y": 100}},
        ]}
        req = urllib.request.Request(
            url,
            data=json.dumps({
                "base": base_hash, "layout": layout,
                "original": {"svg": SVG_REL},
            }).encode(),
            method="PUT",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req) as r:
            body = json.loads(r.read())
        assert body["ok"] is True

        # GET shows it, not stale
        with urllib.request.urlopen(url) as r:
            data = json.loads(r.read())
        assert data["layout"]["ops"][0]["find"] == "40,55"
        assert data["stale"] is False

        # PUT with a stale base -> 409, nothing overwritten
        req = urllib.request.Request(
            url,
            data=json.dumps({"base": "0" * 64, "layout": layout}).encode(),
            method="PUT",
            headers={"Content-Type": "application/json"},
        )
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(req)
        assert exc.value.code == 409

        # invalid layout -> 400
        req = urllib.request.Request(
            url,
            data=json.dumps({
                "base": base_hash,
                "layout": {"ops": [{"kind": "bogus"}]},
            }).encode(),
            method="PUT",
            headers={"Content-Type": "application/json"},
        )
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(req)
        assert exc.value.code == 400

        # served page re-renders with the layout applied
        page_path = "pages/" + SVG_REL.replace("diagrams/diagram-fixtureStructureView.svg", "fixture_feature.sysml.html")
        with urllib.request.urlopen(f"{base}/{page_path}") as r:
            html = r.read().decode()
        assert 'x="100"' in html and 'y="100"' in html

        # DELETE resets
        req = urllib.request.Request(url, method="DELETE")
        with urllib.request.urlopen(req) as r:
            body = json.loads(r.read())
        assert body["ok"] is True
        with urllib.request.urlopen(url) as r:
            assert json.loads(r.read())["layout"] is None

        # non-editable server rejects writes
        server2 = serve.make_server(fixture_repo, tmp_path / "site2", port=0)
        thread2 = threading.Thread(target=server2.serve_forever, daemon=True)
        thread2.start()
        try:
            url2 = f"http://127.0.0.1:{server2.server_address[1]}/diagram-layout/{SVG_REL}"
            req = urllib.request.Request(
                url2,
                data=json.dumps({"base": base_hash, "layout": layout}).encode(),
                method="PUT",
                headers={"Content-Type": "application/json"},
            )
            with pytest.raises(urllib.error.HTTPError) as exc:
                urllib.request.urlopen(req)
            assert exc.value.code == 403
        finally:
            server2.shutdown()
    finally:
        server.shutdown()


def test_layout_api_rejects_path_escape(fixture_repo, tmp_path):
    from tools.sysml_html_viewer import serve

    server = serve.make_server(fixture_repo, tmp_path / "site", port=0,
                               editable=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        url = f"http://127.0.0.1:{port}/diagram-layout/../../etc/passwd"
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(url)
        assert exc.value.code == 404
    finally:
        server.shutdown()
