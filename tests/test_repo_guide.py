"""Tests for DE4SDV Guide: repository retrieval, /api/repo-chat, and UI.

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

def test_guide_panel_is_generated_minimized_and_expandable():
    script = r"""
const fs = require('fs');
const vm = require('vm');

const registry = {};
const store = {};
const fetches = [];

function textNode(text) {
  return {nodeType: 3, textContent: String(text), children: []};
}
function element(tag) {
  const node = {
    nodeType: 1, tagName: String(tag).toUpperCase(), children: [],
    attributes: {}, style: {}, _handlers: {}, value: '', focused: false,
    appendChild(c) { c.parentNode = node; this.children.push(c); return c; },
    remove() {
      if (this.parentNode) {
        const i = this.parentNode.children.indexOf(this);
        if (i >= 0) this.parentNode.children.splice(i, 1);
      }
    },
    setAttribute(k, v) { this.attributes[k] = String(v); },
    getAttribute(k) { return k in this.attributes ? this.attributes[k] : null; },
    addEventListener(t, f) { (this._handlers[t] = this._handlers[t] || []).push(f); },
    dispatch(t) { (this._handlers[t] || []).forEach((f) => f({
      preventDefault() {}, stopPropagation() {}, key: ''
    })); },
    querySelectorAll() { return []; },
    querySelector() { return null; },
    closest() { return null; },
    focus() { this.focused = true; },
    get scrollTop() { return this._scrollTop || 0; },
    set scrollTop(v) { this._scrollTop = v; },
    get scrollHeight() { return 0; }
  };
  const classes = new Set();
  let classNameStr = '';
  Object.defineProperty(node, 'className', {
    get() { return classNameStr; },
    set(v) {
      classNameStr = String(v);
      classes.clear();
      classNameStr.split(/\\s+/).filter(Boolean).forEach((c) => classes.add(c));
    }
  });
  node.classList = {
    add: (c) => classes.add(c),
    remove: (c) => classes.delete(c),
    toggle: (c, on) => {
      if (on === undefined) { classes.has(c) ? classes.delete(c) : classes.add(c); }
      else if (on) classes.add(c); else classes.delete(c);
    },
    contains: (c) => classes.has(c)
  };
  Object.defineProperty(node, 'id', {
    get() { return this.attributes.id || ''; },
    set(v) { this.attributes.id = v; registry[v] = node; }
  });
  Object.defineProperty(node, 'textContent', {
    get() { return this.children.map((c) => c.textContent).join(''); },
    set(v) { this.children = v ? [textNode(v)] : []; }
  });
  return node;
}

const body = element('body');
global.document = {
  readyState: 'loading',   // keeps the IIFE from auto-running real init()
  addEventListener() {},
  createElement: element,
  createTextNode: textNode,
  getElementById(id) { return registry[id] || null; },
  body
};
global.window = {
  localStorage: {
    getItem: (k) => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); }
  }
};
global.location = {hash: '', pathname: ''};
global.fetch = function (url, opts) {
  fetches.push({url, opts});
  return Promise.resolve({ok: true, json: () => Promise.resolve({
    answer: 'stub answer',
    sources: [{path: 'docs/guides/adrs.md', start: 1, end: 5,
               github_url: 'https://github.com/de4sdv/DE4SDV/blob/'
                 + 'a'.repeat(40) + '/docs/guides/adrs.md#L1-L5'}],
    git_sha: 'a'.repeat(40)
  })});
};

let source = fs.readFileSync(process.argv[1], 'utf8');
source = source.replace(
  '  function init() {',
  '  global.renderAskAnswer = renderAskAnswer;\n'
  + '  global.initRepoGuide = initRepoGuide;\n\n  function init() {'
);
vm.runInThisContext(source);
if (typeof global.initRepoGuide !== 'function') {
  throw new Error('initRepoGuide was not loaded from the shipped viewer.js');
}

global.initRepoGuide();

const fab = registry.guideFab;
const panel = registry.guidePanel;
if (!fab || !panel) throw new Error('FAB or panel not generated');
if (panel.classList.contains('open')) {
  throw new Error('panel must be minimized by default');
}
if (fab.style.display === 'none') {
  throw new Error('collapsed FAB must be visible by default');
}
const bodyEl = registry.guideBody;
const starters = bodyEl.children.filter(
  (c) => c.classList && c.classList.contains('guide-starter'));
if (starters.length !== 5) {
  throw new Error('expected 5 starter questions, got ' + starters.length);
}

// expand
fab.dispatch('click');
if (!panel.classList.contains('open')) throw new Error('panel did not expand');
if (fab.style.display !== 'none') throw new Error('FAB not hidden when open');

// send a question -> POST /api/repo-chat
const input = registry.guideInput;
input.value = 'where do architecture decision records live?';
registry.guideInput._handlers = registry.guideInput._handlers || {};
const sendBtn = bodyEl.parentNode.children
  .find((c) => c.classList && c.classList.contains('guide-foot'));
if (!sendBtn) throw new Error('footer not found');

function send() {
  const foot = bodyEl.parentNode.children
    .find((c) => c.classList && c.classList.contains('guide-foot'));
  foot.children.find((c) => c.classList.contains('guide-send'))
    .dispatch('click');
}
send();
if (fetches.length !== 1) throw new Error('expected one fetch');
if (fetches[0].url !== '/api/repo-chat') {
  throw new Error('guide must POST /api/repo-chat, got ' + fetches[0].url);
}
const sent = JSON.parse(fetches[0].opts.body);
if (sent.question !== 'where do architecture decision records live?') {
  throw new Error('question not sent verbatim');
}

setTimeout(() => {
  // minimized state + persisted conversation (client-side only)
  const saved = JSON.parse(store['de4sdv-guide-state']);
  if (!Array.isArray(saved.messages) || saved.messages.length !== 2) {
    throw new Error('conversation not persisted: ' + JSON.stringify(saved));
  }
  if (saved.messages[0].role !== 'user'
      || saved.messages[1].role !== 'guide') {
    throw new Error('unexpected message roles');
  }

  // clear (new chat) resets to intro + starters
  const head = bodyEl.parentNode.children
    .find((c) => c.classList && c.classList.contains('guide-head'));
  head.children.find((c) => c.classList.contains('guide-clear'))
    .dispatch('click');
  const savedAfterClear = JSON.parse(store['de4sdv-guide-state']);
  if (savedAfterClear.messages.length !== 0) {
    throw new Error('clear did not reset the conversation');
  }

  // minimize again: state persisted as closed
  head.children.find((c) => c.classList.contains('guide-min'))
    .dispatch('click');
  if (panel.classList.contains('open')) {
    throw new Error('panel did not minimize');
  }
  const savedClosed = JSON.parse(store['de4sdv-guide-state']);
  if (savedClosed.open !== false) throw new Error('open state not persisted');

  // source reference rendering: SHA-pinned GitHub link with provenance
  // (checked on the pre-clear answer flow via a second round)
  input.value = 'adr locations';
  send();
  setTimeout(() => {
    const sourceLinks = [];
    (function collect(n) {
      (n.children || []).forEach((c) => {
        if (c.classList && c.classList.contains('guide-source')) {
          sourceLinks.push(c);
        }
        collect(c);
      });
    })(bodyEl);
    if (!sourceLinks.length) throw new Error('no source links rendered');
    const link = sourceLinks[sourceLinks.length - 1];
    if (!/github\.com\/de4sdv\/DE4SDV\/blob\/a{40}\//.test(link.href)
        || !/#L1-L5$/.test(link.href)) {
      throw new Error('source link not pinned to the deployed SHA: '
        + link.href);
    }
    if (link.target !== '_blank' || link.rel !== 'noopener') {
      throw new Error('external source link must be rel=noopener new tab');
    }
    console.log('guide UI OK');
  }, 20);
}, 20);
"""
    result = subprocess.run(
        ["node", "-e", script,
         str(REPO_ROOT / "tools/sysml_html_viewer/viewer.js")],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "guide UI OK" in result.stdout


def test_tree_context_menu_offers_both_assistants():
    """Right-clicking an element tree node must offer 'Ask repo assistant'
    (opens the Guide prefilled) and 'Ask the model… (authoritative query)'.
    The identity attrs live on the .tree-node container, so askInfoFor must
    walk up from the matched anchor."""
    import re
    script = r"""
const fs = require('fs');
const vm = require('vm');
const registry = {};
const docListeners = [];
function textNode(t){return {nodeType:3, textContent:String(t), children:[]};}
function element(tag){
  const node = {nodeType:1, tagName:String(tag).toUpperCase(), children:[],
    attributes:{}, style:{}, _handlers:{}, value:'',
    appendChild(c){c._parent=node; this.children.push(c); return c;},
    remove(){}, setAttribute(k,v){this.attributes[k]=String(v);},
    getAttribute(k){return k in this.attributes?this.attributes[k]:null;},
    addEventListener(t,f){(this._handlers[t]=this._handlers[t]||[]).push(f);},
    dispatch(t,ev){(this._handlers[t]||[]).forEach(f=>f(ev||{preventDefault(){},stopPropagation(){},key:'',clientX:5,clientY:5,target:node}));},
    querySelectorAll(){return [];}, querySelector(){return null;},
    removeAttribute(k){delete this.attributes[k];},
    focus(){}, contains(){return false;}
  };
  Object.defineProperty(node,'parentNode',{get(){return node._parent||null;},set(v){node._parent=v;}});
  Object.defineProperty(node,'parentElement',{get(){return node._parent||null;},set(v){node._parent=v;}});
  const classes = new Set();
  let classNameStr = '';
  Object.defineProperty(node,'className',{
    get(){return classNameStr;},
    set(v){classNameStr=String(v); classes.clear();
      classNameStr.split(/\s+/).filter(Boolean).forEach(c=>classes.add(c));}
  });
  node.classList = {add:c=>classes.add(c), remove:c=>classes.delete(c),
    toggle(c,on){if(on===undefined){classes.has(c)?classes.delete(c):classes.add(c);}else if(on)classes.add(c);else classes.delete(c);},
    contains:c=>classes.has(c)};
  Object.defineProperty(node,'id',{get(){return node.attributes.id||'';},set(v){node.attributes.id=v;registry[v]=node;}});
  Object.defineProperty(node,'textContent',{get(){return node.children.map(c=>c.textContent).join('');},set(v){node.children=v?[textNode(v)]:[];}});
  Object.defineProperty(node,'offsetWidth',{get(){return 10;}});
  return node;
}
function attachClosest(node) {
  node.closest = function (sel) {
    for (const s of sel.split(',').map(x=>x.trim())) {
      if (s.indexOf('.tree-node[data-tip-name]') === 0) {
        const p = node._parent;
        if (p && p.classList && p.classList.contains('tree-node')
            && p.attributes['data-tip-name']) return node;
      }
    }
    return null;
  };
}
const body = element('body');
global.document = {
  readyState:'complete', body,
  createElement:element, createTextNode:textNode,
  getElementById(id){return registry[id]||null;},
  documentElement:{style:{setProperty(){}}, getAttribute:()=>null,
    setAttribute(){}, classList:{toggle(){}}},
  querySelector(){return null;}, querySelectorAll(){return [];},
  addEventListener(t,f){docListeners.push([t,f]);}
};
global.window = {localStorage:{getItem:()=>null,setItem(){}},
  GUIDE_REPO_BLOB_BASE:'', addEventListener(){}, removeEventListener(){}};
global.location = {hash:'', pathname:''};
global.sessionStorage = {getItem:()=>null, setItem(){}};
global.fetch = () => Promise.resolve({ok:true, json:()=>Promise.resolve({})});
let source = fs.readFileSync(process.argv[1], 'utf8');
vm.runInThisContext(source);

const anchor = element('a'); anchor.attributes['href']='pages/x.html#src-3';
const li = element('li');
li.setAttribute('class','tree-node tree-part def');
li.setAttribute('data-kind','part def');
li.setAttribute('data-tip-name','FixtureSystem');
li.setAttribute('data-tip-kind','part def');
li.setAttribute('data-tip-file','textual-notation-of-model/packages/features/fixture/fixture_feature.sysml');
li.setAttribute('data-tip-line','3');
li.appendChild(anchor);
anchor._parent = li;
attachClosest(anchor);
global.window.__DE4SDV_VIEWER_SERVER__ = true;

const cm = docListeners.filter(x=>x[0]==='contextmenu').map(x=>x[1]);
if (!cm.length) throw new Error('no contextmenu listener');
cm[0]({preventDefault(){}, stopPropagation(){}, clientX:5, clientY:5, target:anchor, closest:anchor.closest});

function findByClass(n, cls){
  if (n.classList && n.classList.contains(cls)) return n;
  for (const c of (n.children||[])) { const hit = findByClass(c, cls); if (hit) return hit; }
  return null;
}
const menuEl = findByClass(body, 'uses-menu');
if (!menuEl) throw new Error('menu not opened');
const items = menuEl.children.filter(c=>c.classList.contains('uses-menu-item'));
const labels = items.map(i=>i.textContent);
if (labels.length !== 2) throw new Error('expected 2 items, got ' + JSON.stringify(labels));
const repoItem = labels.find(l => l.indexOf('Ask repo assistant') !== -1);
const askItem = labels.find(l => l.indexOf('Ask the model') !== -1
  && l.indexOf('(authoritative query)') !== -1);
if (!repoItem) throw new Error('repo item missing, labels: ' + JSON.stringify(labels));
if (!askItem) throw new Error('authoritative marker missing: ' + JSON.stringify(labels));
items[0].dispatch('click');
const panel = registry.guidePanel;
const input = registry.guideInput;
if (!panel || !panel.classList.contains('open')) throw new Error('guide panel not opened');
if (!input.value || input.value.indexOf('FixtureSystem') === -1) {
  throw new Error('guide input not prefilled: ' + input.value);
}
console.log('TREE MENU OK');
"""
    result = subprocess.run(
        ["node", "-e", script,
         str(REPO_ROOT / "tools/sysml_html_viewer/viewer.js")],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "TREE MENU OK" in result.stdout



def test_chat_panels_layout_states():
    """Single Guide entry point (FAB) + fixed panel order:
    [Ask panel/chip] left, [Guide panel] right (corner). States:
    Guide open -> FAB hidden, corner; both open -> Ask shifted left;
    Ask minimized -> chip left of Guide; Guide minimized -> FAB returns
    and Ask owns the corner."""
    script = r"""
const fs = require('fs');
const vm = require('vm');
const registry = {};
const docListeners = [];
const store = {};
function textNode(t){return {nodeType:3, textContent:String(t), children:[]};}
function element(tag){
  const node = {nodeType:1, tagName:String(tag).toUpperCase(), children:[],
    attributes:{}, style:{}, _handlers:{}, value:'',
    appendChild(c){c._parent=node; this.children.push(c); return c;},
    remove(){}, setAttribute(k,v){this.attributes[k]=String(v);},
    getAttribute(k){return k in this.attributes?this.attributes[k]:null;},
    addEventListener(t,f){(this._handlers[t]=this._handlers[t]||[]).push(f);},
    dispatch(t,ev){(this._handlers[t]||[]).forEach(f=>f(ev||{preventDefault(){},stopPropagation(){},key:'',clientX:5,clientY:5,target:node}));},
    querySelectorAll(){return [];}, querySelector(){return null;},
    removeAttribute(k){delete this.attributes[k];},
    focus(){}, contains(){return false;}
  };
  Object.defineProperty(node,'parentNode',{get(){return node._parent||null;},set(v){node._parent=v;}});
  Object.defineProperty(node,'parentElement',{get(){return node._parent||null;},set(v){node._parent=v;}});
  const classes = new Set();
  let cn = '';
  Object.defineProperty(node,'className',{
    get(){return cn;},
    set(v){cn=String(v); classes.clear();
      cn.split(/\\s+/).filter(Boolean).forEach(c=>classes.add(c));}
  });
  node.classList = {add:c=>classes.add(c), remove:c=>classes.delete(c),
    toggle(c,on){if(on===undefined){classes.has(c)?classes.delete(c):classes.add(c);}else if(on)classes.add(c);else classes.delete(c);},
    contains:c=>classes.has(c)};
  Object.defineProperty(node,'id',{get(){return node.attributes.id||'';},set(v){node.attributes.id=v;registry[v]=node;}});
  Object.defineProperty(node,'textContent',{get(){return node.children.map(c=>c.textContent).join('');},set(v){node.children=v?[textNode(v)]:[];}});
  Object.defineProperty(node,'offsetWidth',{get(){return 10;}});
  return node;
}
function attachClosest(node) {
  node.closest = function (sel) {
    for (const s of sel.split(',').map(x=>x.trim())) {
      if (s === 'a.src-ref' && (node.attributes['class']||'').includes('src-ref')) return node;
    }
    return null;
  };
}
const body = element('body');
const bodyClasses = new Set();
body.classList = {add:c=>bodyClasses.add(c), remove:c=>bodyClasses.delete(c),
  toggle(c,on){if(on===undefined){bodyClasses.has(c)?bodyClasses.delete(c):bodyClasses.add(c);}else if(on)bodyClasses.add(c);else bodyClasses.delete(c);},
  contains:c=>bodyClasses.has(c)};
global.document = {
  readyState:'complete', body,
  createElement:element, createTextNode:textNode,
  getElementById(id){return registry[id]||null;},
  documentElement:{style:{setProperty(){}}, getAttribute:()=>null,
    setAttribute(){}, classList:{toggle(){}}},
  querySelector(){return null;}, querySelectorAll(){return [];},
  addEventListener(t,f){docListeners.push([t,f]);}
};
global.window = {localStorage:{
  getItem:(k)=> (k in store ? store[k] : null),
  setItem:(k,v)=> { store[k] = String(v); }
}, GUIDE_REPO_BLOB_BASE:'', addEventListener(){}, removeEventListener(){}};
global.location = {hash:'', pathname:''};
global.sessionStorage = {getItem:()=>null, setItem(){}};
global.fetch = () => Promise.resolve({ok:true, json:()=>Promise.resolve({})});
let source = fs.readFileSync(process.argv[process.argv.length - 1], 'utf8');
vm.runInThisContext(source);
global.window.__DE4SDV_VIEWER_SERVER__ = true;
function assert(cond, msg) { if (!cond) throw new Error(msg); }
function findByClass(n, cls){
  if (n.classList && n.classList.contains(cls)) return n;
  for (const c of (n.children||[])) { const hit = findByClass(c, cls); if (hit) return hit; }
  return null;
}

// A: both closed -> FAB visible, no ask chip
assert(registry.guideFab.style.display !== 'none', 'A fab hidden');
assert(!registry.askMinChip || registry.askMinChip.style.display !== 'inline-flex', 'A ask chip visible');

// B: Guide open via FAB -> FAB hidden, Guide at corner
const fab = registry.guideFab;
fab.dispatch('click');
assert(registry.guidePanel.classList.contains('open'), 'B guide not open');
assert(fab.style.display === 'none', 'B fab visible while guide open');

// C: open Ask via context menu -> both open, Ask shifted left
const anchor = element('a');
anchor.setAttribute('class','src-ref');
anchor.setAttribute('data-tip-name','FixtureSystem');
anchor.setAttribute('data-tip-kind','part def');
anchor.setAttribute('data-tip-file','fix/fixture.sysml');
anchor.setAttribute('data-tip-line','3');
anchor._parent = body;
attachClosest(anchor);
const cm = docListeners.filter(x=>x[0]==='contextmenu').map(x=>x[1]);
cm[0]({preventDefault(){}, stopPropagation(){}, clientX:5, clientY:5, target:anchor, closest:anchor.closest});
const menuEl = findByClass(body, 'uses-menu');
const items = menuEl.children.filter(c => c.classList.contains('uses-menu-item'));
const askItem = items.find(c => c.textContent.indexOf('Ask the model') !== -1);
assert(askItem, 'C ask menu item missing');
askItem.dispatch('click');
const askPanel = registry.askPanel;
assert(askPanel && askPanel.classList.contains('open'), 'C ask not open');
assert(bodyClasses.has('chat-both-open'), 'C both-open class missing');
assert(askPanel.classList.contains('shifted'), 'C ask must shift left of guide');
assert(!registry.guidePanel.classList.contains('shifted'), 'C guide must own the corner');

// D: minimize Ask -> chip appears; Guide keeps corner; chip shifted
const askMin = findByClass(askPanel, 'ask-min');
askMin.dispatch('click');
assert(!askPanel.classList.contains('open'), 'D ask not hidden');
const askChip = registry.askMinChip;
assert(askChip && askChip.style.display === 'inline-flex', 'D ask chip missing');
assert(askChip.classList.contains('shifted'), 'D chip not shifted left of guide');

// E: chip restores Ask with element context
askChip.dispatch('click');
assert(askPanel.classList.contains('open'), 'E ask not restored');
assert(askPanel.__els.title.textContent === 'FixtureSystem',
  'E element context lost');

// F: minimize Guide -> FAB returns; Ask (open) owns the corner unshifted
const guideMin = findByClass(registry.guidePanel, 'guide-min');
guideMin.dispatch('click');
assert(!registry.guidePanel.classList.contains('open'), 'F guide not hidden');
assert(fab.style.display !== 'none', 'F fab missing');
assert(!askPanel.classList.contains('shifted'), 'F ask must own the corner');

// G: reopen Guide -> both open again, ask re-shifts
fab.dispatch('click');
assert(askPanel.classList.contains('shifted'), 'G ask must re-shift');

console.log('LAYOUT STATES OK');
"""
    result = subprocess.run(
        ["node", "-e", script,
         str(REPO_ROOT / "tools/sysml_html_viewer/viewer.js")],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "LAYOUT STATES OK" in result.stdout
