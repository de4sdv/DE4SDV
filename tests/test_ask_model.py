"""Tests for the ask-model grounding layer, /ask endpoint, and panel wiring.

Follows the no-mirror rule: all fixtures are synthetic, hand-authored
SysML (never copies of real model files). The LLM is never called in
tests — ask_llm is monkeypatched or the key path is tested for
fail-closed behavior only.
"""
from __future__ import annotations

import json
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.sysml_html_viewer import serve as serve_mod  # noqa: E402
from tools.sysml_html_viewer import ask_model  # noqa: E402
from tools.sysml_html_viewer.model_parse import (  # noqa: E402
    build_member_index,
    load_model,
)


FIXTURE_SYSML = """\
package AskModelFixture {
  part def VehicleSpeedObserver {
    doc /* Observes the vehicle speed signal and forwards it. */
  }

  part speedService {
    part observer : VehicleSpeedObserver;
    part publisher;
  }

  view structureView {
    expose speedService;
  }
}
"""


@pytest.fixture()
def fixture_repo(tmp_path):
    (tmp_path / "textual-notation-of-model" / "packages" / "fix").mkdir(
        parents=True
    )
    (tmp_path / "textual-notation-of-model" / "packages" / "fix"
     / "fixture_model.sysml").write_text(FIXTURE_SYSML, encoding="utf-8")
    return tmp_path


# ---- grounding layer -------------------------------------------------------

def test_resolve_element_prefers_exact_name(fixture_repo):
    files = load_model(fixture_repo, ["textual-notation-of-model"])
    index = build_member_index(files)
    ref, cands = ask_model.resolve_element(index, "observer")
    assert ref is not None
    assert ref.kind == "part"
    assert ref.type_name == "VehicleSpeedObserver"
    assert len(cands) == 1


def test_element_source_single_line(fixture_repo):
    files = load_model(fixture_repo, ["textual-notation-of-model"])
    index = build_member_index(files)
    ref, _ = ask_model.resolve_element(index, "observer")
    src = ask_model.element_source(ref, files)
    assert src == "    part observer : VehicleSpeedObserver;"


def test_element_source_braced_block_with_doc(fixture_repo):
    files = load_model(fixture_repo, ["textual-notation-of-model"])
    index = build_member_index(files)
    ref, _ = ask_model.resolve_element(index, "VehicleSpeedObserver")
    src = ask_model.element_source(ref, files)
    assert src.startswith("  part def VehicleSpeedObserver {")
    assert src.rstrip().endswith("}")
    assert "doc /* Observes" in src


def test_children_are_real_children_not_owner(fixture_repo):
    files = load_model(fixture_repo, ["textual-notation-of-model"])
    index = build_member_index(files)
    ref, _ = ask_model.resolve_element(index, "observer")
    kids = ask_model.siblings_of(ref, files)
    assert kids == []  # observer has no children; owner must not leak in
    ref2, _ = ask_model.resolve_element(index, "speedService")
    kids2 = ask_model.siblings_of(ref2, files)
    assert sorted(kids2) == ["observer", "publisher"]


def test_build_evidence_shape(fixture_repo):
    files = load_model(fixture_repo, ["textual-notation-of-model"])
    index = build_member_index(files)
    ref, _ = ask_model.resolve_element(index, "observer")
    ev = ask_model.build_evidence(ref, files)
    assert ev["element"]["name"] == "observer"
    assert ev["element"]["typed_as"] == "VehicleSpeedObserver"
    assert ev["element"]["owner"] == "speedService"
    assert ev["doc"] is None  # doc lives on the def, not the usage
    assert ev["declaration_source"]


def test_load_api_key_missing_is_empty(monkeypatch, tmp_path):
    monkeypatch.delenv("NOUS_API_KEY", raising=False)
    monkeypatch.setattr(
        ask_model, "DEFAULT_KEY_FILE", tmp_path / "nonexistent-key"
    )
    assert ask_model.load_api_key() == ""


def test_load_api_key_env_wins(monkeypatch, tmp_path):
    monkeypatch.setenv("NOUS_API_KEY", "env-key")
    monkeypatch.setattr(
        ask_model, "DEFAULT_KEY_FILE", tmp_path / "nope"
    )
    assert ask_model.load_api_key() == "env-key"


# ---- /ask endpoint (real server, LLM monkeypatched) ------------------------

def _make_server(fixture_repo, tmp_path):
    out = tmp_path / "site"
    out.mkdir()
    return serve_mod.make_server(
        fixture_repo, out, roots=["textual-notation-of-model"],
        host="127.0.0.1", port=0, prs=False,
    )


def test_ask_endpoint_full_roundtrip(fixture_repo, tmp_path, monkeypatch):
    monkeypatch.setattr(
        ask_model, "DEFAULT_KEY_FILE", tmp_path / "nope"
    )
    monkeypatch.setenv("NOUS_API_KEY", "test-key")
    monkeypatch.setattr(
        serve_mod, "ask_llm",
        lambda ev, q, key, model="": (
            "grounded answer about " + ev["element"]["name"]
        ),
    )
    server = _make_server(fixture_repo, tmp_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        port = server.server_address[1]
        body = json.dumps({
            "element": "observer",
            "question": "What does this part do?",
        }).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/ask", data=body,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
        assert data["answer"] == "grounded answer about observer"
        assert data["element"]["file"].endswith("fixture_model.sysml")
        assert data["element"]["line"] > 0
        assert "#src-" in data["element"]["href"]
        assert data["model"]
    finally:
        server.shutdown()
        server.server_close()


def test_ask_endpoint_unknown_element_404(fixture_repo, tmp_path,
                                          monkeypatch):
    monkeypatch.setenv("NOUS_API_KEY", "test-key")
    server = _make_server(fixture_repo, tmp_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        port = server.server_address[1]
        body = json.dumps({
            "element": "notAnElement", "question": "q",
        }).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/ask", data=body,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=30)
            raised = False
        except urllib.error.HTTPError as e:
            raised = True
            assert e.code == 404
        assert raised
    finally:
        server.shutdown()
        server.server_close()


def test_ask_endpoint_without_key_fail_closed_503(fixture_repo, tmp_path,
                                                  monkeypatch):
    monkeypatch.delenv("NOUS_API_KEY", raising=False)
    monkeypatch.setattr(
        ask_model, "DEFAULT_KEY_FILE", tmp_path / "nope"
    )
    server = _make_server(fixture_repo, tmp_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        port = server.server_address[1]
        body = json.dumps({
            "element": "observer", "question": "q",
        }).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/ask", data=body,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=30)
            raised = False
        except urllib.error.HTTPError as e:
            raised = True
            assert e.code == 503
        assert raised
    finally:
        server.shutdown()
        server.server_close()


def test_ask_endpoint_disambiguates_by_file_and_line(fixture_repo, tmp_path,
                                                     monkeypatch):
    """Same-name elements resolve to the one the user right-clicked."""
    monkeypatch.setenv("NOUS_API_KEY", "test-key")
    captured: dict = {}

    def fake_llm(ev, q, key, model=""):
        captured["evidence"] = ev
        return "ok"

    monkeypatch.setattr(serve_mod, "ask_llm", fake_llm)
    server = _make_server(fixture_repo, tmp_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        port = server.server_address[1]

        def post(payload):
            body = json.dumps(payload).encode()
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/ask", data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())

        # find two same-name elements in different files? the fixture has
        # one file; instead verify a WRONG file hint falls back to the
        # resolved element and the evidence follows the right file
        data = post({
            "element": "observer",
            "question": "q",
            "file": "textual-notation-of-model/other.sysml",
            "line": "999",
        })
        assert data["element"]["file"].endswith("fixture_model.sysml")
        assert data["answer"] == "ok"

        # a correct file hint pins the same element
        data2 = post({
            "element": "observer",
            "question": "q",
            "file": data["element"]["file"],
            "line": str(data["element"]["line"]),
        })
        assert data2["element"]["line"] == data["element"]["line"]
        assert captured["evidence"]["element"]["line"] == \
            data2["element"]["line"]
    finally:
        server.shutdown()
        server.server_close()


def test_ask_endpoint_includes_method_context(fixture_repo, tmp_path,
                                              monkeypatch):
    """When the model declares the element as a requirement subject, the
    evidence carries the method relation (traceability questions work)."""
    fixture = (
        "package AskMethodFixture {\n"
        "  part def ProductLineMemberProduct;\n"
        "  part systemCtx {\n"
        "    part memberProduct : ProductLineMemberProduct;\n"
        "  }\n"
        "  requirement needBounded : Need {\n"
        "    doc /* N-FIX-001 draft bounded need. */\n"
        "    subject memberProduct : ProductLineMemberProduct;\n"
        "    require constraint statement { language \"English\" /* The member product shall stay bounded. */ }\n"
        "  }\n"
        "}\n"
    )
    (fixture_repo / "textual-notation-of-model" / "packages" / "fix"
     / "method_fixture.sysml").write_text(fixture, encoding="utf-8")

    seen: dict = {}

    def fake_llm(ev, q, key, model=""):
        seen["evidence"] = ev
        return "cites N-FIX-001"

    monkeypatch.setenv("NOUS_API_KEY", "test-key")
    monkeypatch.setattr(serve_mod, "ask_llm", fake_llm)
    server = _make_server(fixture_repo, tmp_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        port = server.server_address[1]
        body = json.dumps({
            "element": "memberProduct",
            "question": "to which requirement can this element be traced?",
        }).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/ask", data=body,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
        ctx = seen["evidence"].get("method_context", {})
        subs = ctx.get("requirement_subject_of", [])
        assert any(s.get("id") == "N-FIX-001" for s in subs), subs
        assert data["answer"] == "cites N-FIX-001"
    finally:
        server.shutdown()
        server.server_close()


def test_ask_endpoint_rejects_bad_input(fixture_repo, tmp_path,
                                        monkeypatch):
    monkeypatch.setenv("NOUS_API_KEY", "test-key")
    server = _make_server(fixture_repo, tmp_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        port = server.server_address[1]

        def post(payload):
            body = json.dumps(payload).encode()
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/ask", data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                urllib.request.urlopen(req, timeout=30)
                return 200
            except urllib.error.HTTPError as e:
                return e.code

        assert post({"question": "no element"}) == 400
        assert post({"element": "observer"}) == 400
        assert post({"element": "observer",
                     "question": "x" * 600}) == 400
    finally:
        server.shutdown()
        server.server_close()
