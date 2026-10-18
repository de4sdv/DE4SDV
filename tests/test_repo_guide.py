"""Tests for DE4SDV Guide: repository retrieval, /api/repo-chat, and the
viewer's Ask window (one chat window, Model and Repository modes).

DE4SDV Guide is the repository/documentation assistant — a capability
separate from Ask the model. These tests follow the no-mirror rule: all
fixtures are synthetic files in a temporary Git repository (never copies
of real repository content), and the LLM is never called (guide_llm_answer
is monkeypatched; fail-closed paths are tested directly).
"""
from __future__ import annotations

import json
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.sysml_html_viewer import repo_guide  # noqa: E402
from tools.sysml_html_viewer import serve as serve_mod  # noqa: E402


FIXTURE_SYSML = """\
package RepoGuideFixture {
  part def GuideProbePart {
    doc /* Synthetic fixture element. */
  }
}
"""

README_TEXT = """\
# Fixture repository

The zephyr calibration workflow lives in docs/zephyr-workflow.md and is
the canonical entry point for new contributors.

## Layout

- docs/ — human-facing documentation
- approach/ — methodology and the basic ontology
"""

ZEPHYR_DOC = """\
# Zephyr calibration workflow

The zephyr calibration workflow has three stages: inventory, alignment,
and signoff. New contributors start with the inventory stage.
"""

ADR_DOC = """\
# Architecture decision records

Architecture decision records live in docs/architecture-decisions and
are numbered NNNN-short-title.md. Proposed changes start as drafts.
"""


@pytest.fixture()
def guide_repo(tmp_path):
    """Synthetic repository, committed to Git so HEAD/SHA flows work."""
    root = tmp_path / "repo"
    (root / "docs" / "guides").mkdir(parents=True)
    (root / "tools").mkdir()
    (root / "deploy").mkdir()
    (root / "approach" / "framework" / "ontology").mkdir(parents=True)
    (root / "textual-notation-of-model" / "packages" / "fix").mkdir(
        parents=True
    )
    (root / "build").mkdir()
    (root / ".sysand").mkdir()

    (root / "README.md").write_text(README_TEXT, encoding="utf-8")
    (root / "docs" / "guides" / "zephyr-workflow.md").write_text(
        ZEPHYR_DOC, encoding="utf-8"
    )
    (root / "docs" / "guides" / "adrs.md").write_text(
        ADR_DOC, encoding="utf-8"
    )
    (root / "tools" / "helper.py").write_text(
        "def quuxbridge(x):\n"
        "    '''Quuxbridge normalizes the inventory ledger.'''\n"
        "    return x\n",
        encoding="utf-8",
    )
    (
        root / "approach" / "framework" / "ontology" / "basic-ontology.yaml"
    ).write_text("ontology:\n  kernel: fixture-kernel-v1\n", encoding="utf-8")
    (root / "textual-notation-of-model" / "packages" / "fix"
     / "fixture_model.sysml").write_text(FIXTURE_SYSML, encoding="utf-8")

    # excluded material (each with a unique token that must stay unindexed)
    (root / ".env").write_text("topsecretvalue=1\n", encoding="utf-8")
    (root / "deploy" / "service.key").write_text(
        "privkeymaterial\n", encoding="utf-8"
    )
    (root / "SECURITY-secret-notes.md").write_text(
        "classified walrus material\n", encoding="utf-8"
    )
    (root / "sysand-lock.toml").write_text(
        "locked = 'sysandlocktoken'\n", encoding="utf-8"
    )
    (root / "docs" / "img").mkdir()
    (root / "docs" / "img" / "diagram.svg").write_text(
        "<svg>svgonlytoken</svg>", encoding="utf-8"
    )
    (root / "build" / "generated.py").write_text(
        "BUILDPYTOKEN = 1\n", encoding="utf-8"
    )
    (root / ".sysand" / "vendored.py").write_text(
        "VENDOREDTOKEN = 1\n", encoding="utf-8"
    )

    def git(*args: str) -> None:
        subprocess.run(
            ["git", "-C", str(root), *args],
            check=True, capture_output=True,
        )

    git("init")
    git("config", "user.name", "Fixture")
    git("config", "user.email", "fixture@example.com")
    git("add", "-A")
    git("commit", "-m", "fixture corpus")
    return root


# ---- corpus selection / exclusions ------------------------------------------

def test_excluded_basenames_cover_secrets_and_generated():
    for name in (".env", "deploy.env", "SERVICE.key", "id_rsa_home",
                 "secret-notes.md", "credential-store.yaml",
                 "sysand-lock.toml", "logo.min.js", "x.svg", "y.png"):
        assert repo_guide.is_excluded_basename(name), name
    for name in ("README.md", "contribute.py", "model.sysml",
                 "ontology.yaml", "compose.yml"):
        assert not repo_guide.is_excluded_basename(name), name


def test_index_excludes_secret_generated_and_vcs_paths(guide_repo):
    stats = repo_guide.build_repo_index(
        guide_repo, guide_repo.parent / "idx.sqlite3"
    )
    assert stats["files"] > 0
    con_path = guide_repo.parent / "idx.sqlite3"
    con = repo_guide.sqlite3.connect(con_path)
    try:
        paths = {
            row[0] for row in con.execute("SELECT DISTINCT path FROM chunks")
        }
    finally:
        con.close()
    assert "README.md" in paths
    assert "docs/guides/zephyr-workflow.md" in paths
    assert "textual-notation-of-model/packages/fix/fixture_model.sysml" \
        in paths
    # every exclusion class from the brief
    assert not any(p.startswith(".git/") for p in paths)
    assert not any(p.startswith(".sysand/") for p in paths)
    assert not any(p.startswith("build/") for p in paths)
    assert not any(".env" in p for p in paths)
    assert not any("secret" in p.lower() for p in paths)
    assert not any(p.endswith((".svg", ".key")) for p in paths)
    assert "sysand-lock.toml" not in paths


def test_search_finds_nothing_from_excluded_content(guide_repo):
    idx = guide_repo.parent / "idx.sqlite3"
    repo_guide.build_repo_index(guide_repo, idx)
    for token in ("topsecretvalue", "privkeymaterial", "classified",
                  "sysandlocktoken", "svgonlytoken", "BUILDPYTOKEN",
                  "VENDOREDTOKEN"):
        # secret/binary/generated content is never a trustworthy source
        assert repo_guide.search_repo(idx, token) == [], token


def test_search_finds_relevant_repository_content(guide_repo):
    idx = guide_repo.parent / "idx2.sqlite3"
    repo_guide.build_repo_index(guide_repo, idx)
    hits = repo_guide.search_repo(
        idx, "how does the zephyr calibration workflow start?"
    )
    assert hits, "expected the zephyr doc to match"
    assert hits[0]["path"] == "docs/guides/zephyr-workflow.md"
    hits_adr = repo_guide.search_repo(
        idx, "where do architecture decision records live?"
    )
    assert any(h["path"] == "docs/guides/adrs.md" for h in hits_adr)


def test_question_without_indexed_terms_returns_no_sources(guide_repo):
    idx = guide_repo.parent / "idx3.sqlite3"
    repo_guide.build_repo_index(guide_repo, idx)
    assert repo_guide.search_repo(
        idx, "what is the quantum flux capacitance schedule?"
    ) == []


def test_current_head_sha_and_origin_read_the_real_worktree(guide_repo):
    """Regression for an inverted return-code check that made
    github_origin() return '' on success; SHA/origin must come from the
    checkout itself, not from monkeypatched helpers."""
    sha = repo_guide.current_head_sha(guide_repo)
    assert len(sha) == 40
    subprocess.run(
        ["git", "-C", str(guide_repo), "remote", "add", "origin",
         "https://github.com/de4sdv/DE4SDV.git"],
        check=True, capture_output=True,
    )
    origin = repo_guide.github_origin(guide_repo)
    assert origin == "https://github.com/de4sdv/DE4SDV"
    url = repo_guide.github_blob_url(origin, sha, "README.md", 1, 2)
    assert url.startswith(f"https://github.com/de4sdv/DE4SDV/blob/{sha}/")


# ---- provenance ---------------------------------------------------------------

def test_chunks_carry_exact_line_provenance(guide_repo):
    idx = guide_repo.parent / "idx4.sqlite3"
    repo_guide.build_repo_index(guide_repo, idx)
    hits = repo_guide.search_repo(
        idx, "where do architecture decision records live?"
    )
    assert hits
    for hit in hits:
        text = (guide_repo / hit["path"]).read_text(
            encoding="utf-8"
        ).splitlines()
        # 1-based inclusive range exactly matching the checked-out file
        chunk_lines = text[hit["start"] - 1:hit["end"]]
        assert "\n".join(chunk_lines).strip() == hit["text"]
        assert hit["start"] >= 1
        assert hit["end"] >= hit["start"]


def test_github_blob_url_is_pinned_to_the_deployed_sha():
    url = repo_guide.github_blob_url(
        "https://github.com/de4sdv/DE4SDV",
        "a" * 40, "docs/guides/adrs.md", 3, 9,
    )
    assert url == (
        "https://github.com/de4sdv/DE4SDV/blob/"
        + "a" * 40 + "/docs/guides/adrs.md#L3-L9"
    )


def test_github_blob_url_is_empty_without_full_sha_or_origin():
    assert repo_guide.github_blob_url("", "a" * 40, "x.md", 1, 2) == ""
    assert repo_guide.github_blob_url(
        "https://github.com/de4sdv/DE4SDV", "shortsha", "x.md", 1, 2
    ) == ""


def test_index_currency_tracks_head(guide_repo):
    idx = guide_repo.parent / "idx5.sqlite3"
    repo_guide.build_repo_index(guide_repo, idx)
    assert repo_guide.index_is_current(idx, guide_repo)
    # a new commit moves HEAD: the index must be considered stale
    (guide_repo / "docs" / "guides" / "new.md").write_text(
        "fresh content\n", encoding="utf-8"
    )
    subprocess.run(
        ["git", "-C", str(guide_repo), "add", "-A"], check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(guide_repo), "commit", "-m", "second"],
        check=True, capture_output=True,
    )
    assert not repo_guide.index_is_current(idx, guide_repo)


# ---- authority boundary ------------------------------------------------------

def test_repo_guide_has_no_systems_modeling_api_dependency():
    """The Guide layer must not import the semantic API or ask machinery.

    Checked at the AST level (imports only) so prose in docstrings cannot
    false-positive, and at runtime so no semantic attribute leaks in.
    """
    import ast

    source_path = REPO_ROOT / "tools/sysml_html_viewer/repo_guide.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    for forbidden in (
        "urllib", "urllib.request", "http.client", "requests",
        "ask_model_semantic",
    ):
        assert forbidden not in imported, forbidden
    # the only project import is the shared credential/transport helper
    assert "ask_model" in imported
    # no semantic-API machinery reachable through the module
    for attr in (
        "build_method_context_api", "warm_status", "start_warmup",
        "DE4SDV_SYSML_API_URL",
    ):
        assert not hasattr(repo_guide, attr), attr


def test_guide_transport_reuses_the_shared_ask_credential_path():
    """guide_llm_answer delegates to ask_model.chat_completion: one
    credential mechanism, one transport, key never browser-exposed."""
    source = (
        REPO_ROOT / "tools/sysml_html_viewer/repo_guide.py"
    ).read_text(encoding="utf-8")
    assert "from .ask_model import chat_completion" in source


def test_llm_receives_question_and_repository_context_only(guide_repo):
    idx = guide_repo.parent / "idx6.sqlite3"
    repo_guide.build_repo_index(guide_repo, idx)
    hits = repo_guide.search_repo(idx, "zephyr calibration workflow")
    content = repo_guide.guide_user_content("zephyr calibration workflow",
                                            hits)
    assert content.startswith("Repository context")
    assert "docs/guides/zephyr-workflow.md" in content
    assert "Question: zephyr calibration workflow" in content
    # the system prompt draws the authority boundary explicitly
    assert "NOT the engineering or model authority" in \
        repo_guide.GUIDE_SYSTEM_PROMPT
    assert "Ask the model" in repo_guide.GUIDE_SYSTEM_PROMPT


# ---- endpoint (real server, LLM monkeypatched) -------------------------------

def _make_server(guide_repo, tmp_path, **kwargs):
    out = tmp_path / "site"
    out.mkdir(exist_ok=True)
    return serve_mod.make_server(
        guide_repo, out, roots=["textual-notation-of-model"],
        host="127.0.0.1", port=0, prs=False, **kwargs
    )


def _post(port: int, payload, path: str = "/api/repo-chat"):
    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}", data=body,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode(errors="replace")
        try:
            return exc.code, json.loads(raw)
        except ValueError:
            return exc.code, {"raw": raw}


@pytest.fixture()
def guide_origin(monkeypatch):
    monkeypatch.setattr(
        repo_guide, "github_origin",
        lambda repo: "https://github.com/de4sdv/DE4SDV",
    )


def test_repo_chat_roundtrip_with_sha_pinned_sources(
    guide_repo, tmp_path, monkeypatch, guide_origin
):
    monkeypatch.setenv("NOUS_API_KEY", "test-key")
    monkeypatch.setattr(
        repo_guide, "guide_llm_answer",
        lambda q, sources, key, model="": (
            "grounded repo answer citing "
            + ", ".join(s["path"] for s in sources)
        ),
    )
    server = _make_server(guide_repo, tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        status, data = _post(
            port, {"question": "where do architecture decision records live?"}
        )
        assert status == 200
        assert data["answer"].startswith("grounded repo answer citing docs/")
        assert data["capability"] == "de4sdv-guide"
        assert data["sources"], "expected repository source references"
        expected_sha = repo_guide.current_head_sha(guide_repo)
        assert data["git_sha"] == expected_sha
        for source in data["sources"]:
            assert source["github_url"].startswith(
                f"https://github.com/de4sdv/DE4SDV/blob/{expected_sha}/"
            )
            assert "#L" in source["github_url"]
    finally:
        server.shutdown()
        server.server_close()


def test_repo_chat_refuses_without_trustworthy_context(
    guide_repo, tmp_path, monkeypatch
):
    monkeypatch.setenv("NOUS_API_KEY", "test-key")

    def fail_llm(*args, **kwargs):
        raise AssertionError("LLM must not be called without context")

    monkeypatch.setattr(repo_guide, "guide_llm_answer", fail_llm)
    server = _make_server(guide_repo, tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, data = _post(
            server.server_address[1],
            {"question": "what is the quantum flux capacitance schedule?"},
        )
        assert status == 404
        assert "no trustworthy repository context" in data["error"]
        assert data["sources"] == []
    finally:
        server.shutdown()
        server.server_close()


def test_repo_chat_fails_closed_without_api_key(guide_repo, tmp_path,
                                                monkeypatch):
    monkeypatch.delenv("NOUS_API_KEY", raising=False)
    monkeypatch.setattr(
        serve_mod, "load_api_key", lambda: ""
    )
    server = _make_server(guide_repo, tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, data = _post(
            server.server_address[1], {"question": "how do I contribute?"}
        )
        assert status == 503
        assert "not configured" in data["error"]
    finally:
        server.shutdown()
        server.server_close()


def test_repo_chat_validates_input(guide_repo, tmp_path, monkeypatch):
    monkeypatch.setenv("NOUS_API_KEY", "test-key")
    server = _make_server(guide_repo, tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        assert _post(port, {"question": ""})[0] == 400
        assert _post(port, {"noquestion": "x"})[0] == 400
        assert _post(port, {"question": "x" * 600})[0] == 400
        assert _post(port, b"not json")[0] == 400
        assert _post(port, [1, 2, 3])[0] == 400
        status, _ = _post(port, {"question": "ok"}, path="/nope")
        assert status == 404
    finally:
        server.shutdown()
        server.server_close()


def test_repo_chat_enforces_the_public_origin(guide_repo, tmp_path,
                                              monkeypatch):
    monkeypatch.setenv("NOUS_API_KEY", "test-key")
    monkeypatch.setattr(
        repo_guide, "guide_llm_answer",
        lambda q, sources, key, model="": "ok",
    )
    server = _make_server(
        guide_repo, tmp_path,
        allowed_origin="https://viewer.de4sdv.org",
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        body = json.dumps({
            "question": "where do architecture decision records live?"
        }).encode()

        def status_with(origin):
            headers = {"Content-Type": "application/json"}
            if origin:
                headers["Origin"] = origin
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/repo-chat", data=body,
                headers=headers, method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    return r.status
            except urllib.error.HTTPError as exc:
                return exc.code

        assert status_with(None) == 403
        assert status_with("https://other.example") == 403
        assert status_with("https://viewer.de4sdv.org") == 200
    finally:
        server.shutdown()
        server.server_close()


def test_repo_chat_shares_the_llm_concurrency_budget_with_ask(
    guide_repo, tmp_path, monkeypatch
):
    monkeypatch.setenv("NOUS_API_KEY", "test-key")
    server = _make_server(guide_repo, tmp_path, max_concurrent_asks=1)
    # occupy the single slot: the guide must refuse rather than queue
    assert server.ask_slots.acquire(blocking=False)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, data = _post(
            server.server_address[1],
            {"question": "where do architecture decision records live?"},
        )
        assert status == 429
        assert "busy" in data["error"]
    finally:
        server.ask_slots.release()
        server.shutdown()
        server.server_close()


def test_repo_chat_works_when_the_semantic_layer_is_broken(
    guide_repo, tmp_path, monkeypatch, guide_origin
):
    """No fallback in either direction: with the Systems Modeling API
    layer poisoned, the repository capability still works — and Ask the
    model stays untouched."""
    monkeypatch.setenv("NOUS_API_KEY", "test-key")

    def poisoned(*args, **kwargs):
        raise AssertionError("semantic API must not be reached")

    monkeypatch.setattr(serve_mod, "build_method_context_api", poisoned)
    monkeypatch.setattr(
        repo_guide, "guide_llm_answer",
        lambda q, sources, key, model="": "repo-only answer",
    )
    server = _make_server(guide_repo, tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, data = _post(
            server.server_address[1],
            {"question": "how does the zephyr calibration workflow start?"},
        )
        assert status == 200
        assert data["answer"] == "repo-only answer"
        assert data["capability"] == "de4sdv-guide"
    finally:
        server.shutdown()
        server.server_close()


def test_ask_endpoint_still_works_after_the_post_dispatcher_refactor(
    guide_repo, tmp_path, monkeypatch
):
    """The /ask capability is unchanged by the repo-chat addition."""
    monkeypatch.setenv("NOUS_API_KEY", "test-key")
    monkeypatch.setattr(
        serve_mod, "ask_llm",
        lambda ev, q, key, model="": "grounded answer about "
                                     + ev["element"]["name"],
    )
    server = _make_server(guide_repo, tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, data = _post(
            server.server_address[1],
            {"element": "GuideProbePart", "question": "what is this?"},
            path="/ask",
        )
        assert status == 200
        assert data["answer"] == "grounded answer about GuideProbePart"
    finally:
        server.shutdown()
        server.server_close()


def test_guide_inline_renderer_converts_citations_to_sha_pinned_links():
    """In-text citations like [AGENTS.md](AGENTS.md) render once, as a
    real link pinned to the deployed SHA; unsafe URLs never become
    links; without a SHA nothing relative is linked."""
    script = r"""
const fs = require('fs');
const vm = require('vm');

function textNode(text) {
  return {nodeType: 3, textContent: String(text), children: []};
}
function element(tag) {
  const node = {
    nodeType: 1, tagName: String(tag).toUpperCase(), children: [],
    appendChild(c) { this.children.push(c); return c; },
  };
  Object.defineProperty(node, 'textContent', {
    get() { return this.children.map((c) => c.textContent).join(''); },
    set(v) { this.children = v ? [textNode(v)] : []; }
  });
  return node;
}
global.document = {
  readyState: 'loading',
  addEventListener() {},
  createElement: element,
  createTextNode: textNode
};
global.window = { GUIDE_REPO_BLOB_BASE: 'https://github.com/de4sdv/DE4SDV' };
const SHA = 'a'.repeat(40);

let source = fs.readFileSync(process.argv[1], 'utf8');
source = source.replace(
  '  function init() {',
  '  global.appendGuideInline = appendGuideInline;\n'
  + '  global.appendAskInline = appendAskInline;\n\n  function init() {'
);
vm.runInThisContext(source);
if (typeof global.appendGuideInline !== 'function') {
  throw new Error('appendGuideInline was not loaded from the shipped viewer.js');
}

function linksOf(box) {
  const out = [];
  (function walk(n) {
    (n.children || []).forEach((c) => {
      if (c.tagName === 'A') out.push(c);
      walk(c);
    });
  })(box);
  return out;
}

// 1) markdown citation -> exactly one link, correct label, SHA-pinned
const box1 = element('div');
global.appendGuideInline(
  box1, 'Per [AGENTS.md](AGENTS.md), classify every declaration.', SHA);
const links1 = linksOf(box1);
if (links1.length !== 1) {
  throw new Error('expected 1 link, got ' + links1.length);
}
if (links1[0].textContent !== 'AGENTS.md') {
  throw new Error('label doubled: ' + links1[0].textContent);
}
if (links1[0].href !==
    'https://github.com/de4sdv/DE4SDV/blob/' + SHA + '/AGENTS.md') {
  throw new Error('href not SHA-pinned: ' + links1[0].href);
}
if (box1.textContent.indexOf('[AGENTS.md](AGENTS.md)') !== -1) {
  throw new Error('literal markdown leaked: ' + box1.textContent);
}

// 2) bare repository path auto-links with the same pinning
const box2 = element('div');
global.appendGuideInline(
  box2, 'See docs/guides/model-viewer.md for details.', SHA);
const links2 = linksOf(box2);
if (links2.length !== 1
    || !links2[0].href.endsWith('/blob/' + SHA
        + '/docs/guides/model-viewer.md')) {
  throw new Error('bare path not auto-linked: '
    + (links2[0] && links2[0].href));
}

// 3) unsafe URL never becomes a link
const box3 = element('div');
global.appendGuideInline(box3, '[click](javascript:alert(1))', SHA);
if (linksOf(box3).length !== 0) {
  throw new Error('unsafe URL became a link');
}

// 4) without a SHA, relative citations stay inert text
const box4 = element('div');
global.appendGuideInline(box4, 'Per [AGENTS.md](AGENTS.md).', '');
if (linksOf(box4).length !== 0) {
  throw new Error('relative link emitted without a SHA');
}

// 5) https links pass through as external rel=noopener links
const box5 = element('div');
global.appendGuideInline(box5, '[spec](https://example.com/x)', SHA);
const links5 = linksOf(box5);
if (links5.length !== 1 || links5[0].href !== 'https://example.com/x'
    || links5[0].rel !== 'noopener' || links5[0].target !== '_blank') {
  throw new Error('external link not passed through safely');
}

// 6) the default renderer (Ask the model) is unchanged: literal text
const box6 = element('div');
global.appendAskInline(box6, 'Per [AGENTS.md](AGENTS.md).');
if (linksOf(box6).length !== 0) {
  throw new Error('ask renderer unexpectedly grew links');
}
console.log('guide inline renderer OK');
"""
    result = subprocess.run(
        ["node", "-e", script,
         str(REPO_ROOT / "tools/sysml_html_viewer/viewer.js")],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "guide inline renderer OK" in result.stdout


def test_repo_chat_response_carries_repo_blob_base(
    guide_repo, tmp_path, monkeypatch, guide_origin
):
    monkeypatch.setenv("NOUS_API_KEY", "test-key")
    monkeypatch.setattr(
        repo_guide, "guide_llm_answer",
        lambda q, sources, key, model="": "see [AGENTS.md](AGENTS.md)",
    )
    server = _make_server(guide_repo, tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, data = _post(
            server.server_address[1],
            {"question": "where do architecture decision records live?"},
        )
        assert status == 200
        assert data["repo_blob_base"] == "https://github.com/de4sdv/DE4SDV"
    finally:
        server.shutdown()
        server.server_close()


# ---- UI generation (node-level, same approach as test_ask_model.py) ----------

# One mock DOM for the Ask window tests. The shipped viewer.js runs its
# real init() (readyState 'complete'); fetch records each request and
# answers with `reply(url)`.
_CHAT_DOM = r"""
const fs = require('fs');
const vm = require('vm');
const registry = {};
const docListeners = [];
const store = {};
const fetches = [];
let reply = () => ({ok: true, status: 200, data: {}});

function textNode(t) {
  return {nodeType: 3, textContent: String(t), children: []};
}
function element(tag) {
  const node = {nodeType: 1, tagName: String(tag).toUpperCase(), children: [],
    attributes: {}, style: {}, _handlers: {}, value: '', disabled: false,
    appendChild(c) { c._parent = node; this.children.push(c); return c; },
    remove() {},
    setAttribute(k, v) { this.attributes[k] = String(v); },
    getAttribute(k) { return k in this.attributes ? this.attributes[k] : null; },
    removeAttribute(k) { delete this.attributes[k]; },
    addEventListener(t, f) {
      (this._handlers[t] = this._handlers[t] || []).push(f);
    },
    dispatch(t, ev) {
      (this._handlers[t] || []).forEach((f) => f(Object.assign({
        preventDefault() {}, stopPropagation() {}, key: '', shiftKey: false,
        clientX: 5, clientY: 5, target: node
      }, ev || {})));
    },
    querySelectorAll() { return []; }, querySelector() { return null; },
    closest() { return null; }, focus() {}, contains() { return false; }
  };
  Object.defineProperty(node, 'parentNode', {
    get() { return node._parent || null; }, set(v) { node._parent = v; }});
  Object.defineProperty(node, 'parentElement', {
    get() { return node._parent || null; }, set(v) { node._parent = v; }});
  const classes = new Set();
  let cn = '';
  Object.defineProperty(node, 'className', {
    get() { return cn; },
    set(v) {
      cn = String(v); classes.clear();
      cn.split(/\s+/).filter(Boolean).forEach((c) => classes.add(c));
    }
  });
  node.classList = {
    add: (c) => classes.add(c), remove: (c) => classes.delete(c),
    toggle(c, on) {
      if (on === undefined) { classes.has(c) ? classes.delete(c) : classes.add(c); }
      else if (on) classes.add(c); else classes.delete(c);
    },
    contains: (c) => classes.has(c)
  };
  Object.defineProperty(node, 'id', {
    get() { return node.attributes.id || ''; },
    set(v) { node.attributes.id = v; registry[v] = node; }});
  Object.defineProperty(node, 'textContent', {
    get() { return node.children.map((c) => c.textContent).join(''); },
    set(v) { node.children = v ? [textNode(v)] : []; }});
  Object.defineProperty(node, 'offsetWidth', {get() { return 10; }});
  return node;
}

const body = element('body');
global.document = {
  readyState: 'complete', body,
  createElement: element, createTextNode: textNode,
  getElementById(id) { return registry[id] || null; },
  documentElement: {style: {setProperty() {}}, getAttribute: () => null,
    setAttribute() {}, classList: {toggle() {}}},
  querySelector() { return null; }, querySelectorAll() { return []; },
  addEventListener(t, f) { docListeners.push([t, f]); }
};
global.window = {
  localStorage: {
    getItem: (k) => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); },
    removeItem: (k) => { delete store[k]; }
  },
  GUIDE_REPO_BLOB_BASE: '', addEventListener() {}, removeEventListener() {}
};
global.location = {hash: '', pathname: ''};
global.sessionStorage = {getItem: () => null, setItem() {}};
global.fetch = function (url, opts) {
  fetches.push({url, body: JSON.parse(opts.body)});
  const r = reply(url);
  return Promise.resolve({ok: r.ok, status: r.status,
                          json: () => Promise.resolve(r.data)});
};

function assert(cond, msg) { if (!cond) throw new Error(msg); }
function all(n, pred, out) {
  out = out || [];
  (n.children || []).forEach((c) => {
    if (pred(c)) out.push(c);
    all(c, pred, out);
  });
  return out;
}
function byClass(n, cls) {
  return all(n, (c) => c.classList && c.classList.contains(cls));
}
function modeButton(mode) {
  return byClass(registry.chatPanel, 'chat-mode')
    .find((b) => b.getAttribute('data-mode') === mode);
}
function saved() { return JSON.parse(store['de4sdv-chat-state']); }
function later(f) {
  return new Promise((done) => setTimeout(() => { f(); done(); }, 20));
}
function load() {
  vm.runInThisContext(
    fs.readFileSync(process.argv[process.argv.length - 1], 'utf8'));
}
// right-click `anchor` and return the context menu items
function contextMenu(anchor) {
  docListeners.filter((x) => x[0] === 'contextmenu').forEach((x) => x[1]({
    preventDefault() {}, stopPropagation() {}, clientX: 5, clientY: 5,
    target: anchor
  }));
  const menu = byClass(body, 'uses-menu')[0];
  assert(menu, 'context menu not opened');
  return menu.children.filter((c) => c.classList.contains('uses-menu-item'));
}
// a source reference to a model element, as rendered on file pages
function sourceRef(name) {
  const a = element('a');
  a.setAttribute('class', 'src-ref');
  a.setAttribute('data-tip-name', name);
  a.setAttribute('data-tip-kind', 'part def');
  a.setAttribute('data-tip-file', 'fix/fixture.sysml');
  a.setAttribute('data-tip-line', '3');
  a._parent = body;
  a.closest = (sel) => sel.split(',').map((s) => s.trim())
    .indexOf('a.src-ref') !== -1 ? a : null;
  return a;
}
"""


def _run_chat_ui(script: str, marker: str) -> None:
    result = subprocess.run(
        ["node", "-e", _CHAT_DOM + script,
         str(REPO_ROOT / "tools/sysml_html_viewer/viewer.js")],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert marker in result.stdout


def test_ask_window_is_one_minimized_window_asking_the_repository():
    """One Ask window replaces the two floating panels. It starts
    minimized in Repository mode, sends Repository questions only to
    /api/repo-chat, renders SHA-pinned sources and persists its state
    client-side."""
    _run_chat_ui(r"""
load();
const fab = registry.chatFab;
const panel = registry.chatPanel;
assert(fab && panel, 'Ask window not generated');
assert(!registry.guideFab && !registry.guidePanel && !registry.askPanel
       && !registry.askMinChip, 'a second chat window still exists');
assert(!panel.classList.contains('open'), 'window must be minimized by default');
assert(fab.style.display !== 'none', 'collapsed FAB must be visible by default');
const modes = byClass(panel, 'chat-mode');
assert(modes.map((b) => b.getAttribute('data-mode')).join() === 'model,repo',
  'the window must offer Model and Repository');
assert(modeButton('repo').getAttribute('aria-pressed') === 'true'
       && modeButton('model').getAttribute('aria-pressed') === 'false',
  'Repository must be the default mode');
assert(byClass(registry.chatBody, 'chat-starter').length === 4,
  'expected 4 repository starter questions');

fab.dispatch('click');
assert(panel.classList.contains('open'), 'window did not expand');
assert(fab.style.display === 'none', 'FAB not hidden while the window is open');

reply = () => ({ok: true, status: 200, data: {
  answer: 'stub answer',
  sources: [{path: 'docs/guides/adrs.md', start: 1, end: 5,
             github_url: 'https://github.com/de4sdv/DE4SDV/blob/'
               + 'a'.repeat(40) + '/docs/guides/adrs.md#L1-L5'}],
  git_sha: 'a'.repeat(40)
}});
registry.chatInput.value = 'where do architecture decision records live?';
byClass(panel, 'chat-send')[0].dispatch('click');
assert(fetches.length === 1 && fetches[0].url === '/api/repo-chat',
  'Repository mode must POST /api/repo-chat only');
assert(fetches[0].body.question
       === 'where do architecture decision records live?',
  'question not sent verbatim');

later(() => {
  const st = saved();
  assert(st.threads.repo.length === 2 && st.threads.repo[0].role === 'user'
         && st.threads.repo[1].role === 'guide',
    'repository conversation not persisted: ' + JSON.stringify(st));
  assert(st.threads.model.length === 0,
    'repository answer leaked into the model conversation');
  const link = byClass(registry.chatBody, 'guide-source').pop();
  assert(link && /github\.com\/de4sdv\/DE4SDV\/blob\/a{40}\//.test(link.href)
         && /#L1-L5$/.test(link.href),
    'source link not pinned to the deployed SHA');
  assert(link.target === '_blank' && link.rel === 'noopener',
    'external source link must be rel=noopener new tab');

  byClass(panel, 'chat-clear')[0].dispatch('click');
  assert(saved().threads.repo.length === 0, 'New chat did not clear the conversation');
  byClass(panel, 'chat-min')[0].dispatch('click');
  assert(!panel.classList.contains('open'), 'window did not minimize');
  assert(saved().open === false, 'open state not persisted');
  assert(fab.style.display !== 'none', 'FAB not restored after minimizing');
  console.log('ASK WINDOW OK');
});
""", "ASK WINDOW OK")


def test_tree_context_menu_opens_the_one_window_in_either_mode():
    """Right-clicking an element tree node offers 'Ask the model…
    (element-grounded query)' and 'Ask the repository…'. Both open the same
    window: the model item selects the element in Model mode, the
    repository item prefills a question in Repository mode. The identity
    attrs live on the .tree-node container, so askInfoFor must walk up from
    the matched anchor."""
    _run_chat_ui(r"""
load();
window.__DE4SDV_VIEWER_SERVER__ = true;
const anchor = element('a');
anchor.attributes.href = 'pages/x.html#src-3';
const li = element('li');
li.setAttribute('class', 'tree-node tree-part def');
li.setAttribute('data-kind', 'part def');
li.setAttribute('data-tip-name', 'FixtureSystem');
li.setAttribute('data-tip-kind', 'part def');
li.setAttribute('data-tip-file',
  'textual-notation-of-model/packages/features/fixture/fixture_feature.sysml');
li.setAttribute('data-tip-line', '3');
li.appendChild(anchor);
anchor.closest = (sel) => sel.split(',').map((s) => s.trim())
  .some((s) => s.indexOf('.tree-node[data-tip-name]') === 0) ? anchor : null;

let items = contextMenu(anchor);
const labels = items.map((i) => i.textContent);
assert(labels.length === 2, 'expected 2 items, got ' + JSON.stringify(labels));
assert(labels[0].indexOf('Ask the model') !== -1
       && labels[0].indexOf('(element-grounded query)') !== -1,
  'element-grounded model item missing: ' + JSON.stringify(labels));
assert(labels[1].indexOf('Ask the repository') !== -1,
  'repository item missing: ' + JSON.stringify(labels));
assert(!labels.some((l) => l.includes('(authoritative query)')),
  'generated answer is mislabeled as authoritative');

items[1].dispatch('click');
const panel = registry.chatPanel;
assert(panel.classList.contains('open'), 'window not opened');
assert(panel.getAttribute('data-mode') === 'repo', 'not in Repository mode');
assert(registry.chatInput.value.indexOf('FixtureSystem') !== -1,
  'repository question not prefilled: ' + registry.chatInput.value);

items = contextMenu(anchor);
items[0].dispatch('click');
assert(panel.getAttribute('data-mode') === 'model', 'not in Model mode');
const context = byClass(panel, 'chat-context')[0];
assert(context.textContent.indexOf('FixtureSystem') !== -1
       && context.textContent.indexOf('fixture_feature.sysml:3') !== -1,
  'selected element not shown: ' + context.textContent);
assert(byClass(body, 'chat-panel').length === 1, 'more than one chat window');
console.log('TREE MENU OK');
""", "TREE MENU OK")


def test_ask_window_modes_keep_separate_conversations_without_fallback():
    """Each mode keeps its own conversation and calls only its own
    endpoint: a failed model query is reported in the model conversation
    and never retried against the repository. Model mode needs a selected
    element and the viewer server; one request is in flight at a time; the
    Guide conversation of the two-panel layout is migrated once."""
    _run_chat_ui(r"""
store['de4sdv-guide-state'] = JSON.stringify({open: false, messages: [
  {role: 'user', text: 'old repo question'},
  {role: 'guide', text: 'old repo answer', sources: [], sha: '',
   repoBlobBase: ''}
]});
store['de4sdv-ask-open'] = '0';
store['de4sdv-guide-minimized'] = '1';
load();
assert(saved().threads.repo.length === 2, 'Guide conversation not migrated');
['de4sdv-guide-state', 'de4sdv-ask-open', 'de4sdv-guide-minimized']
  .forEach((k) => assert(!(k in store), 'legacy key not removed: ' + k));

const panel = registry.chatPanel;
const input = registry.chatInput;
const send = byClass(panel, 'chat-send')[0];
const context = byClass(panel, 'chat-context')[0];

// Model mode on a static page: Ask the model needs the viewer server
modeButton('model').dispatch('click');
assert(panel.getAttribute('data-mode') === 'model', 'Model mode not selected');
assert(context.textContent.indexOf('served statically') !== -1,
  'static page must say Ask the model needs the viewer server');
window.__DE4SDV_VIEWER_SERVER__ = true;

// no element selected: nothing to ask, nothing sent
assert(send.disabled, 'Send must be disabled without a model element');
input.value = 'what is this?';
input.dispatch('keydown', {key: 'Enter'});
assert(fetches.length === 0, 'Model mode sent a question without an element');

const items = contextMenu(sourceRef('FixtureSystem'));
items.find((i) => i.textContent.indexOf('Ask the model') !== -1)
  .dispatch('click');
assert(!send.disabled, 'Send must be enabled once an element is selected');

reply = (url) => (url === '/ask'
  ? {ok: false, status: 404, data: {error: "element 'FixtureSystem' is not "
       + 'in the model index of this revision'}}
  : {ok: true, status: 200, data: {answer: 'repo answer', sources: [],
       git_sha: 'b'.repeat(40)}});
input.value = 'what is this?';
send.dispatch('click');
assert(fetches.length === 1 && fetches[0].url === '/ask',
  'Model mode must POST /ask');
const sent = fetches[0].body;
assert(sent.element === 'FixtureSystem' && sent.file === 'fix/fixture.sysml'
       && sent.line === '3' && sent.question === 'what is this?',
  'element identity not sent: ' + JSON.stringify(sent));
input.value = 'again?';
send.dispatch('click');
assert(fetches.length === 1, 'a second request was sent while one is in flight');

later(() => {
  assert(fetches.length === 1,
    'a failed model query fell back to another endpoint');
  const st = saved();
  assert(st.threads.model.length === 2 && st.threads.model[1].error === true,
    'model failure not reported in the model conversation');
  assert(st.threads.model[0].element.name === 'FixtureSystem',
    'question not tagged with its element');
  assert(st.threads.repo.length === 2,
    'model exchange leaked into the repository conversation');

  // switching modes swaps conversations and keeps the text being typed
  input.value = 'how do I contribute?';
  modeButton('repo').dispatch('click');
  const shown = registry.chatBody.textContent;
  assert(shown.indexOf('old repo answer') !== -1,
    'repository conversation not shown');
  assert(shown.indexOf('not in the model index') === -1,
    'model conversation shown in Repository mode');
  assert(input.value === 'how do I contribute?', 'draft lost when switching modes');
  send.dispatch('click');
  assert(fetches.length === 2 && fetches[1].url === '/api/repo-chat',
    'Repository mode must POST /api/repo-chat');
}).then(() => later(() => {
  const st = saved();
  assert(st.threads.repo.length === 4 && st.threads.model.length === 2,
    'an answer landed in the wrong conversation');
  modeButton('model').dispatch('click');
  assert(registry.chatBody.textContent.indexOf('not in the model index') !== -1,
    'model conversation lost after switching back');
  console.log('MODES OK');
}));
""", "MODES OK")
