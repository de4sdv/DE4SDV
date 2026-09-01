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
from .layout_sidecar import (
    LAYOUT_DIRNAME,
    delete_layout,
    is_stale,
    load_layout,
    save_layout,
    sha256_text,
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
        editable: bool = False,
    ):
        super().__init__(addr, functools.partial(_Handler, directory=str(out_dir)))
        self.repo_root = repo_root
        self.out_dir = out_dir
        self.roots = roots
        self.prs = prs
        self.editable = editable
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
                # saved diagram-layout sidecars participate in staleness so a
                # layout save re-renders the affected pages on the next request
                for p in base.rglob(f"{LAYOUT_DIRNAME}/*.layout.json"):
                    newest = max(newest, p.stat().st_mtime)
            except OSError:
                continue
        return newest

    def _worktree_stale(self) -> bool:
        if self.editable:
            newest = max(self._newest_model_time(), self._tool_code_time())
            return self._site_stale(self.out_dir / "index.html", newest)
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
            branch = _current_branch(self.repo_root)
            work_label = f"working tree · {branch}" if branch else "working tree"
            try:
                if _build_site(
                    self.repo_root, self.out_dir, self.roots,
                    options=[("index.html", work_label, True, "", True)],
                    current="index.html",
                    editable=self.editable,
                ) != 0:
                    return False
            except Exception:
                return False
            return True

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
_EDITOR_MARKER = b"<script>window.__DE4SDV_EDITOR__=true;</script>"


class _Handler(SimpleHTTPRequestHandler):
    """Static file serving + the /_refs manifest + on-demand ref builds +
    the diagram-layout save API (``/diagram-layout/<svg-rel-path>``)."""

    def do_GET(self) -> None:
        server = cast(ViewerServer, self.server)
        path = urlsplit(self.path).path
        if path == "/_refs":
            self._send_json(server.manifest())
            return
        if path.startswith("/diagram-layout/"):
            self._serve_layout_get(server, path)
            return
        if path.endswith(".html"):
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
        if path.endswith(".html"):
            fs_path = self.translate_path(path)
            if fs_path and Path(fs_path).is_file():
                self._serve_marked_html(Path(fs_path))
                return
        super().do_GET()

    # -- layout sidecar API -------------------------------------------------

    def _layout_svg_path(self, server: ViewerServer, path: str) -> Path | None:
        """/diagram-layout/<repo-relative svg path> -> Path, or None when the
        path escapes the repository or the file is not a committed diagram."""
        rel = urlsplit(path).path[len("/diagram-layout/"):]
        svg = (server.repo_root / rel).resolve()
        try:
            svg.relative_to(server.repo_root.resolve())
        except ValueError:
            return None
        if (
            not svg.is_file()
            or svg.suffix != ".svg"
            or LAYOUT_DIRNAME in svg.parts
            or "diagrams" not in svg.parts
        ):
            return None
        return svg

    def _serve_layout_get(self, server: ViewerServer, path: str) -> None:
        svg = self._layout_svg_path(server, path)
        if svg is None:
            self.send_error(404, "no such committed diagram")
            return
        svg_text = svg.read_text(encoding="utf-8")
        record = load_layout(svg)
        base = sha256_text(
            re.sub(r"^<\?xml[^>]*\?>", "", svg_text).lstrip()
        )
        if record is None:
            self._send_json({"svg": str(svg.relative_to(server.repo_root)), "base": base, "layout": None})
            return
        stale = is_stale(record, re.sub(r"^<\?xml[^>]*\?>", "", svg_text).lstrip())
        self._send_json({
            "svg": str(svg.relative_to(server.repo_root)),
            "base": base,
            "stale": stale,
            "layout": record["layout"],
            "saved_at": record.get("saved_at", ""),
        })

    def do_PUT(self) -> None:
        server = cast(ViewerServer, self.server)
        path = urlsplit(self.path).path
        if not path.startswith("/diagram-layout/"):
            self.send_error(404)
            return
        if not server.editable:
            self.send_error(403, "layout editing is off (start the editor server)")
            return
        svg = self._layout_svg_path(server, path)
        if svg is None:
            self.send_error(404, "no such committed diagram")
            return
        length = int(self.headers.get("Content-Length") or 0)
        if length > 2_000_000:
            self.send_error(413, "layout payload too large")
            return
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_error(400, "invalid JSON body")
            return
        base = body.get("base")
        layout = body.get("layout")
        original = body.get("original") or {}
        if not isinstance(base, str) or not base:
            self.send_error(400, "missing 'base' (the diagram hash you edited)")
            return
        committed = re.sub(r"^<\?xml[^>]*\?>", "", svg.read_text(encoding="utf-8")).lstrip()
        current = sha256_text(committed)
        if base != current:
            self._send_json({
                "error": "stale-base",
                "message": "The committed diagram changed since you loaded it.",
                "current_base": current,
            }, status=409)
            return
        try:
            record = save_layout(svg, base, layout, original)
        except ValueError as exc:
            self._send_json({"error": "invalid-layout", "message": str(exc)}, status=400)
            return
        except FileNotFoundError:
            self.send_error(404, "diagram gone")
            return
        self._send_json({"ok": True, "saved_at": record.get("saved_at", "")})

    def do_DELETE(self) -> None:
        server = cast(ViewerServer, self.server)
        path = urlsplit(self.path).path
        if not path.startswith("/diagram-layout/"):
            self.send_error(404)
            return
        if not server.editable:
            self.send_error(403, "layout editing is off (start the editor server)")
            return
        svg = self._layout_svg_path(server, path)
        if svg is None:
            self.send_error(404, "no such committed diagram")
            return
        removed = delete_layout(svg)
        self._send_json({"ok": True, "removed": removed})

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
        """Serve an HTML page stamped with the server marker (and the editor
        marker when editing is on) so the page JS knows which mode is
        active."""
        try:
            body = fs_path.read_bytes()
        except OSError:
            self.send_error(404, "File not found")
            return
        head = body.find(b"</head>")
        markers = _MARKER + (_EDITOR_MARKER if self.server.editable else b"")  # type: ignore[attr-defined]
        if head != -1:
            body = body[:head] + markers + body[head:]
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

    def log_message(self, format: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), format % args))


def make_server(
    repo_root: Path,
    out_dir: Path,
    roots: list[str] | None = None,
    host: str = "127.0.0.1",
    port: int = 8787,
    prs: bool = True,
    editable: bool = False,
) -> ViewerServer:
    """Create (not yet started) the viewer server; ensures the working-tree
    site exists first. With ``editable=True`` the working-tree site is built
    with diagram-layout payloads and the layout save API is enabled."""
    repo_root = Path(repo_root).resolve()
    out_dir = Path(out_dir).resolve()
    roots = roots or DEFAULT_ROOTS
    if not (out_dir / "index.html").exists():
        branch = _current_branch(repo_root)
        work_label = f"working tree · {branch}" if branch else "working tree"
        _build_site(
            repo_root, out_dir, roots,
            options=[("index.html", work_label, True, "", True)],
            current="index.html",
            editable=editable,
        )
    return ViewerServer((host, port), repo_root, out_dir, roots, prs, editable)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="repository root (default: cwd)")
    parser.add_argument("--out", default="build/model-viewer", help="site directory")
    parser.add_argument("--host", default="127.0.0.1", help="bind address")
    parser.add_argument("--port", type=int, default=8787, help="bind port")
    parser.add_argument("--no-prs", action="store_true", help="skip GitHub PR refs")
    parser.add_argument(
        "--edit-layout", action="store_true",
        help="enable the diagram layout editor (Edit layout buttons + save API)",
    )
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    if not _is_git_root(repo):
        print("--repo must be the repository root (has .git).", file=sys.stderr)
        return 2
    server = make_server(
        repo, Path(args.out).resolve(),
        host=args.host, port=args.port, prs=not args.no_prs,
        editable=args.edit_layout,
    )
    url = f"http://{args.host}:{server.server_address[1]}/"
    print(f"Serving the DE4SDV model viewer at {url}")
    if args.edit_layout:
        print("Diagram layout editing is ON: diagrams carry an Edit layout")
        print("button; saved layouts go to <diagrams>/.de4sdv-diagrams/.")
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
