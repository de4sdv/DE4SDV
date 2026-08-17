"""On-demand server for the DE4SDV static HTML model viewer.

Usage:
    python -m tools.sysml_html_viewer.serve [--repo REPO] [--out OUT]
        [--port PORT] [--host HOST] [--no-prs]

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
    ):
        super().__init__(addr, functools.partial(_Handler, directory=str(out_dir)))
        self.repo_root = repo_root
        self.out_dir = out_dir
        self.roots = roots
        self.prs = prs
        self.registry: dict[str, Target] = {}
        self.registry_at = 0.0
        self.build_locks: dict[str, threading.Lock] = {}
        self.build_lock_guard = threading.Lock()

    # -- registry ---------------------------------------------------------
    def registry_refresh(self, ttl: float = 60.0) -> dict[str, Target]:
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
                self.out_dir / "refs" / san / "index.html"
            ).exists()
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
    def _worktree_stale(self) -> bool:
        """True when any .sysml under the model roots is newer than the
        generated working-tree site (or the site is missing)."""
        marker = self.out_dir / "index.html"
        try:
            site_time = marker.stat().st_mtime
        except OSError:
            return True
        newest = site_time
        for root in self.roots:
            base = self.repo_root / root
            if not base.is_dir():
                continue
            try:
                for p in base.rglob("*.sysml"):
                    newest = max(newest, p.stat().st_mtime)
            except OSError:
                continue
        return newest > site_time

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
            branch = _current_branch(self.repo_root)
            work_label = f"working tree · {branch}" if branch else "working tree"
            try:
                if _build_site(
                    self.repo_root, self.out_dir, self.roots,
                    options=[("index.html", work_label, True, "")],
                    current="index.html",
                ) != 0:
                    return False
            except Exception:
                return False
            return True

    # -- on-demand builds --------------------------------------------------
    def ensure_built(self, san: str) -> bool:
        """Generate refs/<san>/ on first request; True when served."""
        reg = self.registry_refresh()
        target = reg.get(san)
        if target is None or target.work:
            return False
        ref_dir = self.out_dir / "refs" / san
        if (ref_dir / "index.html").exists():
            return True
        with self.build_lock_guard:
            lock = self.build_locks.setdefault(san, threading.Lock())
        with lock:
            if (ref_dir / "index.html").exists():
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
                        ("index.html", work, True, ""),
                        (f"refs/{san}/index.html", target.label, True, ""),
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
        if path.endswith(".html"):
            # pick up working-tree model changes before serving pages
            server.ensure_worktree_current()
        if path.startswith("/refs/"):
            san = path.split("/")[2]
            if san and not server.ensure_built(san):
                self.send_error(404, f"ref {san!r} cannot be built")
                return
        if path.endswith(".html"):
            fs_path = self.translate_path(path)
            if fs_path and Path(fs_path).is_file():
                self._serve_marked_html(Path(fs_path))
                return
        super().do_GET()

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

    def _send_json(self, data: dict) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), format % args))


def make_server(
    repo_root: Path,
    out_dir: Path,
    roots: list[str] | None = None,
    host: str = "127.0.0.1",
    port: int = 8787,
    prs: bool = True,
) -> ViewerServer:
    """Create (not yet started) the viewer server; ensures the working-tree
    site exists first."""
    repo_root = Path(repo_root).resolve()
    out_dir = Path(out_dir).resolve()
    roots = roots or DEFAULT_ROOTS
    if not (out_dir / "index.html").exists():
        branch = _current_branch(repo_root)
        work_label = f"working tree · {branch}" if branch else "working tree"
        _build_site(
            repo_root, out_dir, roots,
            options=[("index.html", work_label, True, "")],
            current="index.html",
        )
    return ViewerServer((host, port), repo_root, out_dir, roots, prs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="repository root (default: cwd)")
    parser.add_argument("--out", default="build/model-viewer", help="site directory")
    parser.add_argument("--host", default="127.0.0.1", help="bind address")
    parser.add_argument("--port", type=int, default=8787, help="bind port")
    parser.add_argument("--no-prs", action="store_true", help="skip GitHub PR refs")
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    if not _is_git_root(repo):
        print("--repo must be the repository root (has .git).", file=sys.stderr)
        return 2
    server = make_server(
        repo, Path(args.out).resolve(),
        host=args.host, port=args.port, prs=not args.no_prs,
    )
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
