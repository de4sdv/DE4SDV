"""On-demand server for the DE4SDV static HTML model viewer.

Usage:
    python -m tools.sysml_html_viewer.serve [--repo REPO] [--out OUT]
        [--port PORT] [--host HOST] [--no-prs] [--production]

Serves the generated viewer (build/model-viewer by default) over HTTP and
makes every branch and pull request of the repository selectable in the
Revision picker:

- ``/_refs`` returns the manifest of all known revisions (working tree,
  local branches, open PRs) with their labels and buildability.
- The first request for a not-yet-built revision (``/refs/<name>/...``)
  materializes it from git and generates its site on the fly (a few
  seconds), then serves it; subsequent requests are served from the cache.

Static builds (``file://`` or any plain static host) keep the static
picker; the dynamic upgrade happens only when the page is served by this
server (the picker JS fetches ``/_refs`` and falls back silently).
"""
from __future__ import annotations

import argparse
import functools
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import cast
from urllib.parse import urlsplit

from .generate import (
    DEFAULT_ROOTS,
    _blob_ref,
    _build_site,
    _gh_pr_list,
    _github_blob_base,
    _is_git_root,
    _local_branches,
    _materialize,
)
from .ask_model import (
    MODEL as ASK_MODEL,
    ask_llm,
    build_evidence,
    load_api_key,
    resolve_element,
)
from .ask_model_semantic import build_method_context_api, start_warmup, warm_status
from .model_parse import ModelFile, build_member_index, load_model
from .model_parse import ElementRef  # noqa: F401  (type only)


@dataclass
class Target:
    """One selectable revision."""

    ref: str        # git ref to materialize ('' for the working tree)
    san: str        # directory name under refs/ ('' for the working tree)
    label: str      # picker label
    work: bool = False      # the working tree entry
    fetch: bool = False     # must git-fetch before materializing (PR head)
    buildable: bool = True  # has .sysml under the model roots


def _sanitize(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)


def _current_branch(repo_root: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0 and out.stdout.strip() != "HEAD":
            return out.stdout.strip()
    except Exception:
        pass
    return ""


def _ref_buildable(repo_root: Path, ref: str, roots: list[str]) -> bool:
    """True when the ref has at least one .sysml file under the roots."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "ls-tree", "-r", "--name-only",
             ref, "--"] + roots,
            capture_output=True, text=True, timeout=60,
        )
        return out.returncode == 0 and any(
            n.endswith(".sysml") for n in out.stdout.splitlines()
        )
    except Exception:
        return False


def build_registry(
    repo_root: Path, roots: list[str], prs: bool = True
) -> dict[str, Target]:
    """san ('' = working tree) -> Target for every known revision."""
    branch = _current_branch(repo_root)
    targets: dict[str, Target] = {}
    seen: set[str] = set()

    def add(target: Target) -> None:
        san = target.san
        base, n = san, 2
        while san in seen:
            san = f"{base}_{n}"
            n += 1
        seen.add(san)
        target.san = san
        targets[san] = target

    work_label = f"working tree · {branch}" if branch else "working tree"
    add(Target(ref="", san="", label=work_label, work=True))

    for name in _local_branches(repo_root):
        if name == branch:
            continue
        add(Target(ref=name, san=_sanitize(name), label=name))

    for pr in _gh_pr_list(repo_root) if prs else []:
        head = pr["headRefName"]
        label = f"PR #{pr['number']}: {pr['title']}"
        short = _blob_ref(head)
        if short == branch:
            continue
        existing = next(
            (t for t in targets.values() if t.ref == head), None
        )
        if existing is not None:
            existing.label = label
            continue
        add(Target(
            ref=f"refs/pull/{pr['number']}/head",
            san=_sanitize(short),
            label=label,
            fetch=True,
        ))

    # buildability is a registry property (cheap ls-tree per ref)
    for target in targets.values():
        if target.work:
            continue
        target.buildable = _ref_buildable(repo_root, target.ref, roots)
    return targets


class ViewerServer(ThreadingHTTPServer):
    """Threading HTTP server with a shared generation cache."""

    def __init__(
        self,
        addr: tuple[str, int],
        repo_root: Path,
        out_dir: Path,
        roots: list[str],
        prs: bool,
        *,
        allowed_origin: str,
        max_concurrent_asks: int,
        application_revision: str,
        model_revision: str,
        production: bool,
    ):
        super().__init__(addr, functools.partial(_Handler, directory=str(out_dir)))
        self.repo_root = repo_root
        self.out_dir = out_dir
        self.roots = roots
        self.prs = prs
        self.allowed_origin = allowed_origin
        self.ask_slots = threading.BoundedSemaphore(max_concurrent_asks)
        self.application_revision = application_revision
        self.model_revision = model_revision
        self.production = production
        self.registry: dict[str, Target] = {}
        self.registry_at = 0.0
        self.build_locks: dict[str, threading.Lock] = {}
        self.build_lock_guard = threading.Lock()
        # ask-model: cached grounding index per served revision
        self.ask_lock = threading.Lock()
        self.ask_index: dict[
            str,
            tuple[float, dict[str, list[ElementRef]], list[ModelFile]],
        ] = {}

    # -- registry ---------------------------------------------------------
    def registry_refresh(self, ttl: float = 60.0) -> dict[str, Target]:
        if self.production:
            label = f"deployed · {self.application_revision[:7]}"
            return {"": Target("", "", label, work=True)}
        if time.time() - self.registry_at > ttl or not self.registry:
            self.registry = build_registry(self.repo_root, self.roots, self.prs)
            self.registry_at = time.time()
        return self.registry

    def manifest(self) -> dict:
        reg = self.registry_refresh()
        refs = []
        for san, t in reg.items():
            url = "/index.html" if t.work else f"/refs/{san}/index.html"
            built = True if t.work else (
                (self.out_dir / "refs" / san / "index.html").exists()
                and not self._ref_stale(self.out_dir / "refs" / san)
            )
            entry: dict = {
                "id": san,
                "label": t.label,
                "url": url,
                "buildable": t.buildable,
                "built": built,
            }
            if not t.buildable:
                entry["hint"] = (
                    "no .sysml under the validated model roots"
                )
            refs.append(entry)
        refs.sort(key=lambda r: (r["id"] != "", r["label"]))
        return {"refs": refs}

    # -- working tree staleness ---------------------------------------------
    @staticmethod
    def _tool_code_time() -> float:
        """Newest mtime of the viewer's own code (tools/sysml_html_viewer).

        When the tool code is newer than a generated site, the site was
        built by an older version and must be regenerated — this is what
        makes a fresh `git pull` visible after one page refresh.
        """
        tools_dir = Path(__file__).resolve().parent
        newest = 0.0
        for pattern in ("*.py", "viewer.js", "viewer.css"):
            for p in tools_dir.glob(pattern):
                try:
                    newest = max(newest, p.stat().st_mtime)
                except OSError:
                    continue
        return newest

    def _site_stale(self, site_marker: Path, newest_model: float) -> bool:
        """True when the model or the viewer's own code is newer than the
        generated site at site_marker."""
        try:
            site_time = site_marker.stat().st_mtime
        except OSError:
            return True
        return max(newest_model, self._tool_code_time()) > site_time

    def _newest_model_time(self) -> float:
        newest = 0.0
        for root in self.roots:
            base = self.repo_root / root
            if not base.is_dir():
                continue
            try:
                for p in base.rglob("*.sysml"):
                    newest = max(newest, p.stat().st_mtime)
            except OSError:
                continue
        return newest

    def _worktree_stale(self) -> bool:
        return self._site_stale(self.out_dir / "index.html", self._newest_model_time())

    def _ref_stale(self, ref_dir: Path) -> bool:
        return self._site_stale(ref_dir / "index.html", 0.0)

    def ensure_worktree_current(self) -> bool:
        """Regenerate the working-tree site when the model changed on disk.

        Returns True when the served site is current (after any rebuild).
        This is what makes `python -m tools.sysml_html_viewer.serve` the
        only command needed: editing a .sysml file is picked up on the
        next page request.
        """
        if not self._worktree_stale():
            return True
        with self.build_lock_guard:
            lock = self.build_locks.setdefault("", threading.Lock())
        with lock:
            if not self._worktree_stale():
                return True
            if self.production:
                work_label = f"deployed · {self.application_revision[:7]}"
            else:
                branch = _current_branch(self.repo_root)
                work_label = f"working tree · {branch}" if branch else "working tree"
            try:
                if _build_site(
                    self.repo_root, self.out_dir, self.roots,
                    options=[("index.html", work_label, True, "", True)],
                    current="index.html",
                ) != 0:
                    return False
            except Exception:
                return False
            return True

    # -- ask-model grounding index ----------------------------------------
    def ask_grounding(
        self, san: str, ref: str = ""
    ) -> tuple[dict[str, list[ElementRef]], list[ModelFile]]:
        """(index, files) for one served revision, parsed once and cached.

        san '' is the working tree (rebuilt when .sysml files change);
        a ref sub-site parses a persistent materialization of `ref` under
        refs/<san>/ (created on first ask; the generated site inlines its
        diagrams, so only the ask path needs the tree).
        """
        with self.ask_lock:
            if san == "":
                newest = self._newest_model_time()
                cached = self.ask_index.get("")
                if cached and cached[0] == newest:
                    return cached[1], cached[2]
                files = load_model(self.repo_root, self.roots)
                index = build_member_index(files)
                self.ask_index[""] = (self._newest_model_time(), index, files)
                return index, files

            ref_dir = self.out_dir / "refs" / san
            cached = self.ask_index.get(san)
            if cached and (ref_dir / "index.html").exists():
                return cached[1], cached[2]
            if ref:
                # persistent materialization for grounding (build/ is
                # gitignored); a sibling of the site, never inside it
                tree_dir = self.out_dir / "ask-refs" / san
                has_model = tree_dir.exists() and any(tree_dir.rglob("*.sysml"))
                if not has_model:
                    tree_dir.mkdir(parents=True, exist_ok=True)
                    _materialize(self.repo_root, ref, self.roots, tree_dir)
                files = load_model(tree_dir, self.roots)
            else:
                files = load_model(ref_dir, self.roots)
            index = build_member_index(files)
            self.ask_index[san] = (0.0, index, files)
            return index, files

    # -- on-demand builds --------------------------------------------------
    def ensure_built(self, san: str) -> bool:
        """Generate (or refresh) refs/<san>/ on first request; True when
        served. A ref site built by older viewer code is rebuilt."""
        reg = self.registry_refresh()
        target = reg.get(san)
        if target is None or target.work:
            return False
        ref_dir = self.out_dir / "refs" / san
        if (ref_dir / "index.html").exists() and not self._ref_stale(ref_dir):
            return True
        with self.build_lock_guard:
            lock = self.build_locks.setdefault(san, threading.Lock())
        with lock:
            if (ref_dir / "index.html").exists() and not self._ref_stale(ref_dir):
                return True
            ref = target.ref
            if target.fetch:
                try:
                    subprocess.run(
                        ["git", "-C", str(self.repo_root), "fetch", "origin",
                         f"{target.ref}:{target.ref}"],
                        capture_output=True, text=True, timeout=120,
                    )
                except Exception:
                    return False
            try:
                with tempfile.TemporaryDirectory(prefix="model-viewer-ref-") as td:
                    tmp = Path(td)
                    if not _materialize(self.repo_root, ref, self.roots, tmp):
                        return False
                    blob_base = _github_blob_base(self.repo_root, ref)
                    work = reg[""].label
                    options = [
                        ("index.html", work, True, "", True),
                        (f"refs/{san}/index.html", target.label, True, "", True),
                    ]
                    if _build_site(
                        tmp, ref_dir, self.roots,
                        blob_base=blob_base,
                        options=options,
                        current=f"refs/{san}/index.html",
                        external_ref=True,
                    ) != 0:
                        return False
            except Exception:
                return False
            return True


_MARKER = b"<script>window.__DE4SDV_VIEWER_SERVER__=true;</script>"


class _Handler(SimpleHTTPRequestHandler):
    """Static file serving + the /_refs manifest + on-demand ref builds."""

    def do_GET(self) -> None:
        server = cast(ViewerServer, self.server)
        path = urlsplit(self.path).path
        if path == "/_refs":
            self._send_json(server.manifest())
            return
        if path == "/_ask_warmup":
            self._send_json(warm_status())
            return
        if path == "/ask-status.json":
            warmup_state = warm_status()
            self._send_json({
                "service": "DE4SDV public Ask-model viewer",
                "application_git_commit": server.application_revision,
                "model_git_commit": server.model_revision,
                "semantic_warmup": {
                    "status": warmup_state.get("status", "unknown")
                },
            })
            return
        if path == "/" or path.endswith(".html"):
            # pick up working-tree model changes before serving pages
            server.ensure_worktree_current()
        if path.startswith("/refs/"):
            san = path.split("/")[2]
            if san and not server.ensure_built(san):
                self.send_error(404, f"ref {san!r} cannot be built")
                return
        if path.endswith((".js", ".css")):
            # never let browsers cache viewer assets across updates
            fs_path = self.translate_path(path)
            if fs_path and Path(fs_path).is_file():
                self._serve_file_no_cache(Path(fs_path))
                return
        if path == "/" or path.endswith(".html"):
            fs_path = self.translate_path(path if path != "/" else "/index.html")
            if fs_path and Path(fs_path).is_file():
                self._serve_marked_html(Path(fs_path))
                return
        super().do_GET()

    def _serve_file_no_cache(self, fs_path: Path) -> None:
        try:
            body = fs_path.read_bytes()
        except OSError:
            self.send_error(404, "File not found")
            return
        ctype = "text/javascript; charset=utf-8" if fs_path.suffix == ".js" \
            else "text/css; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def _serve_marked_html(self, fs_path: Path) -> None:
        """Serve an HTML page stamped with the server marker so the picker
        JS knows the dynamic revision list is available."""
        try:
            body = fs_path.read_bytes()
        except OSError:
            self.send_error(404, "File not found")
            return
        head = body.find(b"</head>")
        if head != -1:
            body = body[:head] + _MARKER + body[head:]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    # -- ask-model endpoint --------------------------------------------------
    def do_POST(self) -> None:
        server = cast(ViewerServer, self.server)
        path = urlsplit(self.path).path
        if path != "/ask":
            self.send_error(404)
            return
        if (server.allowed_origin
                and self.headers.get("Origin") != server.allowed_origin):
            self._send_json({"error": "origin is not allowed"}, status=403)
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0 or length > 16384:
            self._send_json({"error": "invalid request body"}, status=400)
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            self._send_json({"error": "invalid JSON"}, status=400)
            return
        element = str(payload.get("element") or "").strip()
        question = str(payload.get("question") or "").strip()
        ref = str(payload.get("ref") or "").strip()
        # the element the user right-clicked (identity, not just name)
        el_file = str(payload.get("file") or "").strip()
        el_line = str(payload.get("line") or "").strip()
        if not element or not question:
            self._send_json({"error": "element and question are required"},
                            status=400)
            return
        if len(question) > 500:
            self._send_json({"error": "question too long (max 500 chars)"},
                            status=400)
            return

        # ground against the revision being browsed: '' = working tree,
        # otherwise the ref sub-site's materialized tree
        if ref:
            reg = server.registry_refresh()
            target = reg.get(ref)
            if target is None:
                self._send_json({"error": f"unknown revision {ref!r}"},
                                status=404)
                return
            index, files = server.ask_grounding(ref, target.ref)
        else:
            index, files = server.ask_grounding("")

        resolved, candidates = resolve_element(index, element)
        if resolved is not None and el_file:
            # disambiguate to the element the user actually pointed at
            if el_line:
                exact = [
                    c for c in candidates
                    if c.rel_path == el_file and str(c.line) == el_line
                ]
            else:
                exact = [c for c in candidates if c.rel_path == el_file]
            if exact:
                resolved = exact[0]
        if resolved is None:
            self._send_json({"error": f"element {element!r} is not in the "
                                      f"model index of this revision"},
                            status=404)
            return

        evidence = build_evidence(resolved, files)
        try:
            method_ctx, derivation = build_method_context_api(
                resolved, files
            )
        except Exception:
            method_ctx, derivation = {}, "regex:fallback:exception"
        if method_ctx:
            evidence["method_context"] = method_ctx
        api_key = load_api_key()
        if not api_key:
            self._send_json(
                {"error": "ask-model is not configured on this server: "
                          "set NOUS_API_KEY or the key file",
                 "evidence": evidence},
                status=503,
            )
            return
        if not server.ask_slots.acquire(blocking=False):
            self._send_json(
                {"error": "ask-model is busy; retry later"}, status=429
            )
            return
        try:
            try:
                answer = ask_llm(evidence, question, api_key)
            except Exception as exc:  # noqa: BLE001 — surfaced honestly to the panel
                self._send_json({"error": f"LLM call failed: {exc}",
                                 "evidence": evidence},
                                status=502)
                return
        finally:
            server.ask_slots.release()
        self._send_json({
            "answer": answer,
            "element": {
                "name": resolved.name, "kind": resolved.kind,
                "file": resolved.rel_path, "line": resolved.line,
                "href": f"pages/{resolved.rel_path}.html#src-{resolved.line}",
            },
            "model": ASK_MODEL,
            "method_context_source": derivation,
            "ambiguous_alternatives": [
                {"name": c.name, "file": c.rel_path, "line": c.line}
                for c in candidates[1:6]
            ] if (len(candidates) > 1 and derivation.startswith("regex")) else [],
        })

    def log_message(self, format: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), format % args))


def make_server(
    repo_root: Path,
    out_dir: Path,
    roots: list[str] | None = None,
    host: str = "127.0.0.1",
    port: int = 8787,
    prs: bool = True,
    allowed_origin: str | None = None,
    max_concurrent_asks: int | None = None,
    application_revision: str | None = None,
    model_revision: str | None = None,
    production: bool = False,
) -> ViewerServer:
    """Create (not yet started) the viewer server; ensures the working-tree
    site exists first."""
    repo_root = Path(repo_root).resolve()
    out_dir = Path(out_dir).resolve()
    roots = roots or DEFAULT_ROOTS
    if allowed_origin is None:
        allowed_origin = os.environ.get("DE4SDV_ASK_ALLOWED_ORIGIN", "")
    if max_concurrent_asks is None:
        raw_limit = os.environ.get("NOUS_MAX_CONCURRENT_REQUESTS", "2")
        try:
            max_concurrent_asks = int(raw_limit)
        except ValueError as exc:
            raise ValueError(
                "NOUS_MAX_CONCURRENT_REQUESTS must be a positive integer"
            ) from exc
    if max_concurrent_asks < 1:
        raise ValueError(
            "NOUS_MAX_CONCURRENT_REQUESTS must be a positive integer"
        )
    application_revision = application_revision or os.environ.get(
        "DE4SDV_APP_GIT_SHA", ""
    )
    model_revision = model_revision or os.environ.get(
        "DE4SDV_EXPECTED_GIT_SHA", ""
    )
    if production and not re.fullmatch(r"[0-9a-f]{40}", application_revision):
        raise ValueError("production mode requires DE4SDV_APP_GIT_SHA")
    if not (out_dir / "index.html").exists():
        if production:
            work_label = f"deployed · {application_revision[:7]}"
        else:
            branch = _current_branch(repo_root)
            work_label = f"working tree · {branch}" if branch else "working tree"
        _build_site(
            repo_root, out_dir, roots,
            options=[("index.html", work_label, True, "", True)],
            current="index.html",
        )
    return ViewerServer(
        (host, port), repo_root, out_dir, roots, prs,
        allowed_origin=allowed_origin,
        max_concurrent_asks=max_concurrent_asks,
        application_revision=application_revision,
        model_revision=model_revision,
        production=production,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="repository root (default: cwd)")
    parser.add_argument("--out", default="build/model-viewer", help="site directory")
    parser.add_argument("--host", default="127.0.0.1", help="bind address")
    parser.add_argument("--port", type=int, default=8787, help="bind port")
    parser.add_argument("--no-prs", action="store_true", help="skip GitHub PR refs")
    parser.add_argument(
        "--production", action="store_true",
        help="serve only the exact deployed revision",
    )
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    if not _is_git_root(repo):
        print("--repo must be the repository root (has .git).", file=sys.stderr)
        return 2
    server = make_server(
        repo, Path(args.out).resolve(),
        host=args.host, port=args.port, prs=not args.no_prs,
        production=args.production,
    )
    # semantic ask-mode: warm the API corpus in the background so no
    # visitor ever waits for the cold load (no-op when NOUS_ASK_SEMANTIC
    # is unset; snapshot-backed, see ask_model_semantic)
    start_warmup()
    url = f"http://{args.host}:{server.server_address[1]}/"
    print(f"Serving the DE4SDV model viewer at {url}")
    print("Pick any branch or PR in the Revision picker — the first view of")
    print("a ref generates it on demand (a few seconds), then it is cached.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
