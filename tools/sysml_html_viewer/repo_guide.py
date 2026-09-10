"""Repository-grounded Q&A for the DE4SDV viewer ("DE4SDV Guide").

DE4SDV Guide is the repository/documentation assistant of the public
viewer. It helps newcomers understand the DE4SDV Git repository: its
documentation, architecture material, ADRs, tooling, contribution
workflow, and product-line assets. Retrieval is a deterministic SQLite
FTS5 index built over the exact deployed Git checkout — no vector
database, no Systems Modeling API call, and no fallback to the
element-grounded "Ask the model" capability.

Authority boundary (mirrored in the UI and docs):

- **DE4SDV Guide** (this module): generated answers grounded in the
  checked-out Git repository. Not an engineering or model authority.
  Never queries the Systems Modeling API.
- **Ask the model** (``ask_model.py``): the element-grounded model
  capability. Unchanged and separate.

The LLM receives only the question plus the retrieved repository
context. Secrets never live in this repository: the API key comes
through the same server-side mechanism as ask_model (``NOUS_API_KEY``
env or the 0600 key file), never exposed to the browser.
"""
from __future__ import annotations

import fnmatch
import os
import re
import sqlite3
import subprocess
from pathlib import Path

from .ask_model import chat_completion

MAX_QUESTION_CHARS = 500
MAX_CONTEXT_SOURCES = 8
MAX_CHUNKS_PER_PATH = 3
MAX_FILE_BYTES = 256 * 1024

GUIDE_SYSTEM_PROMPT = """You are the DE4SDV Guide, the repository assistant
of the DE4SDV Model Viewer (viewer.de4sdv.org). You help newcomers
understand the DE4SDV Git repository: its documentation, architecture
material, architecture decision records, tooling, contribution workflow,
and product-line assets.

Rules:
- Answer ONLY from the provided repository context. When the context does
  not contain the answer, say exactly what the provided repository
  material does not cover and point to the most relevant repository paths.
- Cite the repository paths you used (for example
  docs/guides/model-viewer.md) so the UI can link them. Write citations
  as plain repository paths or [label](repo/path) links with the path
  EXACTLY as in the repository — never wrap them in extra brackets,
  backticks, or parentheses; the UI turns them into GitHub links.
- You are NOT the engineering or model authority: do not confirm, invent,
  or reinterpret requirements, compliance claims, or SysML model
  semantics. If the question asks what a specific model element means,
  say the viewer's "Ask the model" capability (right-click an element) is
  the authority for that.
- Never claim certification, homologation, or approval.
- Keep answers under 180 words unless the user asks for detail.
"""

GUIDE_STARTER_QUESTIONS = (
    "How do I contribute to the repository?",
    "Where are the architecture decision records (ADRs)?",
    "How is the SysML v2 model organized?",
    "What does the public deployment stack look like?",
)

GUIDE_INTRO = (
    "I can help you understand the DE4SDV repository, architecture, "
    "documentation and contribution workflow. Answers are generated from "
    "the checked-out Git repository \u2014 not from the Systems Modeling "
    "API. For a specific model element, right-click it and use "
    "Ask the model."
)

# ---- corpus selection -------------------------------------------------------

INCLUDED_SUFFIXES = {".md", ".py", ".sysml", ".yaml", ".yml"}

# directories never indexed (VCS internals, dependency checkouts, build
# output, caches, generated assets)
EXCLUDED_DIR_NAMES = {
    ".git", ".github", ".sysand", ".venv", "venv", "__pycache__",
    "node_modules", "build", "dist", "out", "coverage",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", ".cache",
    "libraries", "snapshots", "diagrams",
}

# basenames/patterns never indexed regardless of location (secrets,
# environment files, generated lock/summary artifacts)
EXCLUDED_BASENAME_EXACT = {
    ".env", ".gitignore", ".gitattributes", ".dockerignore",
    "sysand-lock.toml", "package-lock.json", "poetry.lock",
}
EXCLUDED_BASENAME_PATTERNS = (
    ".env.*", "*.env", "*.pem", "*.key", "id_rsa*", "*.p12", "*.pfx",
    "*secret*", "*credential*", "*.min.*", "*.svg", "*.png", "*.jpg",
    "*.jpeg", "*.gif", "*.ico", "*.pdf", "*.zip", "*.tar", "*.gz",
    "*.whl", "*.pyc", "*.so", "*.bin", "*.sqlite3", "*.db",
)

# Filler words dropped before an FTS query; everything left must be a
# real content term so the "trustworthy context" gate stays honest.
STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "am", "do", "does", "did", "done", "has", "have", "had", "having",
    "i", "me", "my", "we", "our", "us", "you", "your", "it", "its",
    "this", "that", "these", "those", "there", "here", "he", "she",
    "they", "them", "their", "what", "which", "who", "whom", "whose",
    "how", "why", "when", "where", "can", "could", "should", "would",
    "shall", "will", "may", "might", "must", "of", "in", "on", "at",
    "by", "for", "with", "about", "as", "into", "to", "from", "and",
    "or", "not", "no", "if", "then", "than", "so", "s", "t", "d", "ll",
    "re", "ve", "m", "get", "got", "please", "tell", "give", "find",
    "up", "out", "over", "under", "again", "more", "most", "some",
    "any", "each", "per", "via", "use", "used", "using",
}

_CHUNK_TARGET_LINES = 60
_CHUNK_MAX_CHARS = 1600


def is_excluded_basename(name: str) -> bool:
    """True when a file basename must never be indexed (secrets, env
    files, binary/generated artifacts)."""
    lowered = name.lower()
    if lowered in EXCLUDED_BASENAME_EXACT:
        return True
    return any(
        fnmatch.fnmatch(lowered, pattern)
        for pattern in EXCLUDED_BASENAME_PATTERNS
    )


def _iter_indexable_files(repo_root: Path) -> list[tuple[str, Path]]:
    """Deterministic (rel_path, abs_path) list of the indexable corpus."""
    out: list[tuple[str, Path]] = []
    for dirpath, dirnames, filenames in os.walk(repo_root):
        rel_dir = Path(dirpath).relative_to(repo_root)
        dirnames[:] = sorted(
            d for d in dirnames if d not in EXCLUDED_DIR_NAMES
        )
        for name in sorted(filenames):
            if Path(name).suffix.lower() not in INCLUDED_SUFFIXES:
                continue
            if is_excluded_basename(name):
                continue
            abspath = Path(dirpath) / name
            rel = (
                str(rel_dir / name).replace(os.sep, "/")
                if str(rel_dir) != "."
                else name
            )
            try:
                if abspath.stat().st_size > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            out.append((rel, abspath))
    return out


def _iter_chunks(
    rel_path: str, text: str
) -> list[tuple[int, int, str]]:
    """Split one file into provenance-carrying chunks.

    Each chunk is (start_line, end_line, text) with 1-based inclusive
    line numbers exactly matching the checked-out file, so every chunk
    can be cited as a GitHub blob URL pinned to the deployed SHA.
    Boundaries snap to blank lines inside the tail of a block when that
    keeps chunks coherent.
    """
    lines = text.splitlines()
    chunks: list[tuple[int, int, str]] = []
    start = 0
    n = len(lines)
    index = 0
    while start < n:
        end = min(start + _CHUNK_TARGET_LINES, n)
        if end < n:
            # snap to the last blank line in the final third of the block
            zone_start = start + (2 * _CHUNK_TARGET_LINES) // 3
            snap = max(
                (i for i in range(zone_start, end) if not lines[i].strip()),
                default=-1,
            )
            if snap > start + 8:
                end = snap
        chunk_text = "\n".join(lines[start:end]).strip("\n")
        if chunk_text:
            index += 1
            chunks.append((start + 1, end, chunk_text))
        start = end
    if not chunks and n == 0 and text.strip():
        chunks.append((1, 1, text.strip()))
    return chunks


def current_head_sha(repo_root: Path) -> str:
    """Full 40-hex HEAD of the checkout, or '' when unavailable."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        sha = out.stdout.strip()
        if out.returncode == 0 and re.fullmatch(r"[0-9a-f]{40}", sha):
            return sha
    except Exception:
        pass
    return ""


def github_origin(repo_root: Path) -> str:
    """https://github.com/<owner>/<repo> for the origin remote, or ''."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=10,
        )
        url = out.stdout.strip()
        if out.returncode != 0 or not url:
            return ""
        if url.startswith("git@github.com:"):
            url = "https://github.com/" + url.split(":", 1)[1]
        url = url.removesuffix(".git")
        return url if "github.com" in url else ""
    except Exception:
        return ""


def github_blob_url(
    repo_origin: str, sha: str, rel_path: str, start_line: int, end_line: int
) -> str:
    """GitHub blob URL pinned to the deployed application SHA, or '' when
    the origin or SHA is unknown (the UI then shows a plain path)."""
    if not repo_origin or not re.fullmatch(r"[0-9a-f]{40}", sha or ""):
        return ""
    return (
        f"{repo_origin}/blob/{sha}/{rel_path}"
        f"#L{start_line}-L{end_line}"
    )


# ---- index build / query ----------------------------------------------------

_SCHEMA = (
    "CREATE VIRTUAL TABLE chunks USING fts5("
    "path UNINDEXED, start_line UNINDEXED, end_line UNINDEXED, "
    "chunk_index UNINDEXED, text)",
    "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)",
)


def build_repo_index(repo_root: Path, index_path: Path) -> dict:
    """Build the FTS5 retrieval index over the exact checkout.

    Writes to a temporary file and renames atomically, so a failed build
    never leaves a half-written index behind. Returns
    ``{"files": int, "chunks": int, "git_sha": str}``.
    """
    repo_root = Path(repo_root)
    index_path = Path(index_path)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = index_path.with_name(index_path.name + ".tmp")
    if tmp_path.exists():
        tmp_path.unlink()
    con = sqlite3.connect(tmp_path)
    files = 0
    chunks = 0
    try:
        for stmt in _SCHEMA:
            con.execute(stmt)
        for rel, abspath in _iter_indexable_files(repo_root):
            try:
                text = abspath.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            files += 1
            for i, (start, end, chunk_text) in enumerate(_iter_chunks(rel, text), 1):
                con.execute(
                    "INSERT INTO chunks VALUES (?, ?, ?, ?, ?)",
                    (rel, start, end, i, chunk_text),
                )
                chunks += 1
        con.execute(
            "INSERT INTO meta VALUES ('git_sha', ?)",
            (current_head_sha(repo_root),),
        )
        con.commit()
    finally:
        con.close()
    tmp_path.replace(index_path)
    return {"files": files, "chunks": chunks, "git_sha": current_head_sha(repo_root)}


def _meta_sha(index_path: Path) -> str:
    try:
        con = sqlite3.connect(f"file:{index_path}?mode=ro", uri=True)
    except sqlite3.Error:
        return ""
    try:
        row = con.execute(
            "SELECT value FROM meta WHERE key = 'git_sha'"
        ).fetchone()
        return str(row[0]) if row else ""
    except sqlite3.Error:
        return ""
    finally:
        con.close()


def index_is_current(index_path: Path, repo_root: Path) -> bool:
    """True when the index exists and was built from the checkout that is
    on disk now (keyed by HEAD SHA; the deployment entrypoint guarantees
    HEAD equals the deployed application SHA in production)."""
    if not Path(index_path).is_file():
        return False
    return _meta_sha(index_path) == current_head_sha(repo_root)


def _content_terms(question: str) -> list[str]:
    """Lowercase deduped content terms of the question (stopwords and
    very short tokens dropped), capped at 12."""
    terms: list[str] = []
    for raw in re.split(r"[^a-z0-9_.-]+", question.lower()):
        term = raw.strip("._-")
        if len(term) < 2 or term in STOPWORDS:
            continue
        if term not in terms:
            terms.append(term)
    return terms[:12]


def _fts_query(con: sqlite3.Connection, match: str, limit: int):
    return con.execute(
        "SELECT path, start_line, end_line, chunk_index, text "
        "FROM chunks WHERE chunks MATCH ? ORDER BY bm25(chunks) LIMIT ?",
        (match, limit),
    ).fetchall()


def search_repo(
    index_path: Path, question: str, limit: int = MAX_CONTEXT_SOURCES
) -> list[dict]:
    """Retrieve the most relevant indexed chunks for a question.

    Returns provenance-carrying chunk records
    ``{"path", "start", "end", "chunk_index", "text"}``. Empty when no
    indexed repository text matches the question's content terms — the
    caller must treat that as "no trustworthy context" and refuse to
    answer rather than letting the model guess.
    """
    terms = _content_terms(question)
    if not terms or not Path(index_path).is_file():
        return []
    con = sqlite3.connect(f"file:{index_path}?mode=ro", uri=True)
    try:
        match = " ".join(f'"{t}"' for t in terms[:10])
        rows = _fts_query(con, match, limit * 3)
        mode = "and"
        if not rows:
            match = " OR ".join(f'"{t}"' for t in terms[:10])
            rows = _fts_query(con, match, limit * 3)
            mode = "or"
        if not rows:
            return []
    finally:
        con.close()

    seen: set[tuple[str, int]] = set()
    per_path: dict[str, int] = {}
    sources: list[dict] = []
    for path, start, end, chunk_index, text in rows:
        key = (path, int(start))
        if key in seen:
            continue
        if per_path.get(path, 0) >= MAX_CHUNKS_PER_PATH:
            continue
        seen.add(key)
        per_path[path] = per_path.get(path, 0) + 1
        sources.append({
            "path": path,
            "start": int(start),
            "end": int(end),
            "chunk_index": int(chunk_index),
            "text": text,
            "match": mode,
        })
        if len(sources) >= limit:
            break
    return sources


def format_context(sources: list[dict]) -> str:
    """Render retrieved chunks as the numbered context block the LLM
    receives (path + line range provenance kept intact)."""
    blocks = []
    for i, s in enumerate(sources, 1):
        blocks.append(
            f"[{i}] {s['path']} (lines {s['start']}-{s['end']})\n"
            f"{s['text']}"
        )
    return "\n\n".join(blocks)


def guide_user_content(question: str, sources: list[dict]) -> str:
    """The exact user message: the question plus retrieved repository
    context — nothing else."""
    return (
        "Repository context (from the exact deployed Git checkout; "
        "each block is cited with its repository path and line range):\n\n"
        f"{format_context(sources)}\n\n"
        f"Question: {question}"
    )


def guide_llm_answer(
    question: str, sources: list[dict], api_key: str, model: str = ""
) -> str:
    """One grounded DE4SDV Guide answer. The model receives only the
    question and the retrieved repository context."""
    return chat_completion(
        GUIDE_SYSTEM_PROMPT,
        guide_user_content(question, sources),
        api_key,
        model=model,
    )
