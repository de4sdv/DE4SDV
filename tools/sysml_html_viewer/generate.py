"""Generate the DE4SDV static HTML model viewer.

Usage:
    python -m tools.sysml_html_viewer.generate [--repo REPO] [--out OUT]
        [--refs REFS] [--no-prs]

The viewer is a read-only browser over the SysML v2 textual model: a
navigation tree on the left, and package/file/element/view pages on the
right. Views embed the committed SysIDE diagram artifacts; nothing is
re-rendered or invented.

By default the working tree is built, plus the ``main`` (or ``origin/main``)
revision when the repository has it. Extra revisions are built with
``--refs`` (comma-separated refs, or ``auto`` for every local branch); each
becomes a complete site under ``refs/<name>/`` and every page header offers
a "Revision" picker to switch between them. Pull-request labels are attached
when the ``gh`` CLI can map a branch to an open PR (disable with ``--no-prs``).

Output defaults to ``build/model-viewer`` (gitignored). Serve from the
repository root, e.g. ``python -m http.server`` — all links are relative
and the site also works from ``file://``.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .model_parse import (
    TreeNode,
    build_member_index,
    build_tree,
    count_stats,
    load_model,
)
from .render import (
    render_dir_page,
    render_file_page,
    render_index,
    render_ref_picker,
)

# Same scope as scripts/validate_sysml.py MODEL_PATHS: the whole textual
# notation root (packages, imported libraries like COVESA VSS, snapshots)
# plus the PLE product models.
DEFAULT_ROOTS = [
    "textual-notation-of-model",
    "model-based-product-line-engineering/product-models",
]


@dataclass
class RefSpec:
    """One extra repository revision to build alongside the working tree."""

    ref: str    # git ref name (branch, tag, refs/pull/N/head, ...)
    short: str  # short name GitHub accepts (blob URLs, PR lookups)
    san: str    # sanitized subdirectory name under refs/
    label: str  # picker label (branch name, or PR label when mapped)


def _rel_prefix(site_path: str) -> str:
    """Relative path prefix from the page at site_path up to the site root."""
    parts = Path(site_path).parts
    return "../" * max(0, len(parts) - 1)


def _blob_ref(ref: str) -> str:
    """Ref name GitHub accepts in blob URLs (best effort)."""
    for prefix in ("refs/heads/", "refs/remotes/", "refs/tags/"):
        if ref.startswith(prefix):
            ref = ref[len(prefix):]
    if ref.startswith("origin/"):
        ref = ref[len("origin/"):]
    return ref


def _github_blob_base(repo_root: Path, blob_ref: str = "") -> str:
    """https://github.com/<owner>/<repo>/blob/<ref> for the origin remote,
    or '' when there is no GitHub remote."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=10,
        )
        url = out.stdout.strip()
        if not url:
            return ""
        if url.startswith("git@github.com:"):
            url = "https://github.com/" + url.split(":", 1)[1]
        url = url.removesuffix(".git")
        if "github.com" not in url:
            return ""
        ref = _blob_ref(blob_ref) or "main"
        return f"{url}/blob/{ref}"
    except Exception:
        return ""


def _git_verify(repo_root: Path, ref: str) -> bool:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--verify", "--quiet",
             f"{ref}^{{commit}}"],
            capture_output=True, timeout=10,
        )
        return out.returncode == 0
    except Exception:
        return False


def _is_git_root(repo_root: Path) -> bool:
    """True when repo_root is itself the repository root (not a subdir of
    one, e.g. a test fixture tree)."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode != 0:
            return False
        return Path(out.stdout.strip()).resolve() == repo_root.resolve()
    except Exception:
        return False


def _local_branches(repo_root: Path) -> list[str]:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "for-each-ref",
             "--sort=refname", "--format=%(refname:short)", "refs/heads"],
            capture_output=True, text=True, timeout=10,
        )
        return out.stdout.splitlines() if out.returncode == 0 else []
    except Exception:
        return []


def _remote_branches(repo_root: Path) -> list[str]:
    """origin/* branch short names (without the origin/ prefix)."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "for-each-ref",
             "--sort=refname", "--format=%(refname:short)", "refs/remotes/origin"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode != 0:
            return []
        return [n for n in out.stdout.splitlines() if n != "origin/HEAD"]
    except Exception:
        return []


def _gh_pr_list(repo_root: Path) -> list[dict]:
    """Open pull requests of this repository (gh CLI, best effort).

    Returns [] on any failure (no GitHub origin, gh missing, not authed,
    offline)."""
    try:
        url = subprocess.run(
            ["git", "-C", str(repo_root), "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=10,
        ).stdout
        if "github.com" not in url:
            return []
        out = subprocess.run(
            ["gh", "pr", "list", "--state", "open",
             "--json", "number,headRefName,title", "--limit", "100"],
            capture_output=True, text=True, timeout=20, cwd=str(repo_root),
        )
        if out.returncode != 0:
            return []
        return json.loads(out.stdout)
    except Exception:
        return []


def _pr_labels(repo_root: Path) -> dict[str, str]:
    """Ref name -> 'PR #N: title' for open PRs of this repository.

    Keyed by both the head branch name and the refs/pull/N/head form, so
    labels survive either resolution path. Best effort: requires a GitHub
    origin and a working `gh` CLI; any failure returns an empty map.
    """
    out: dict[str, str] = {}
    for pr in _gh_pr_list(repo_root):
        label = f"PR #{pr['number']}: {pr['title']}"
        out[pr["headRefName"]] = label
        out[f"refs/pull/{pr['number']}/head"] = label
    return out


def _expand_refs(
    repo_root: Path, refs_arg: str | None, prs: bool
) -> tuple[list[RefSpec], str, dict[str, str]]:
    """Resolve the --refs argument into buildable RefSpecs.

    Returns (specs, current branch short name, pr labels map). The current
    branch is never rebuilt as a ref: the working tree build already is it.
    """
    branch = ""
    if not _is_git_root(repo_root):
        # not a repository root (e.g. a fixture tree): no branch context,
        # no refs
        return [], branch, {}
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0:
            branch = out.stdout.strip()
            if branch == "HEAD":  # detached
                branch = ""
    except Exception:
        pass

    if refs_arg in (None, ""):
        names = []
        for cand in ("main", "origin/main"):
            if _git_verify(repo_root, cand):
                names.append(cand)
                break
    elif refs_arg == "auto":
        # local + origin branches, plus open PR heads (refs/pull/N/head)
        names = _local_branches(repo_root)
        names += [n.removeprefix("origin/") for n in _remote_branches(repo_root)]
        seen: set[str] = set()
        names = [n for n in names if not (n in seen or seen.add(n))]
        for pr in _gh_pr_list(repo_root) if prs else []:
            head = _blob_ref(pr["headRefName"])
            if head == branch or head in seen:
                continue
            names.append(f"refs/pull/{pr['number']}/head")
    else:
        names = [r.strip() for r in refs_arg.split(",") if r.strip()]

    pr_map = _pr_labels(repo_root) if (prs and names) else {}
    specs: list[RefSpec] = []
    seen_dirs: set[str] = set()
    for ref in names:
        resolved = ref
        if not _git_verify(repo_root, resolved):
            # PR branches often exist only on the remote
            remote_cand = "origin/" + ref.lstrip("/")
            if _git_verify(repo_root, remote_cand):
                resolved = remote_cand
            else:
                print(f"  ref {ref!r} not found; skipped", file=sys.stderr)
                continue
        short = _blob_ref(resolved)
        if branch and short == branch:
            continue  # the working tree build already covers this branch
        label = pr_map.get(short) or short
        san = re.sub(r"[^A-Za-z0-9._-]", "_", short)
        base, n = san, 2
        while san in seen_dirs:
            san = f"{base}_{n}"
            n += 1
        seen_dirs.add(san)
        specs.append(RefSpec(ref=resolved, short=short, san=san, label=label))
    return specs, branch, pr_map


def _known_unbuilt_refs(
    repo_root: Path,
    branch: str,
    built_shorts: set[str],
    pr_map: dict[str, str],
) -> list[tuple[str, str]]:
    """(short name, label) for revisions that exist in the repository (local
    branches + open PR heads) but were not built — the picker shows them as
    disabled options with a hint instead of hiding them."""
    known = set(_local_branches(repo_root))
    known |= set(pr_map.keys())
    out = []
    for name in sorted(known):
        if name == branch or name in built_shorts:
            continue
        out.append((name, pr_map.get(name) or name))
    return out


def _ref_has_model(repo_root: Path, ref: str, roots: list[str]) -> bool:
    """True when the ref has at least one .sysml file under the roots.

    Refs without model content (e.g. PRs that only touch docs or tooling)
    are skipped before building so the picker never lists a broken site.
    """
    try:
        for root in roots:
            out = subprocess.run(
                ["git", "-C", str(repo_root), "ls-tree", "-r", "--name-only",
                 ref, "--", root],
                capture_output=True, text=True, timeout=60,
            )
            if out.returncode != 0:
                continue  # root does not exist at this ref
            if any(n.endswith(".sysml") for n in out.stdout.splitlines()):
                return True
    except Exception:
        pass
    return False


def _materialize(
    repo_root: Path, ref: str, roots: list[str], tmp: Path
) -> list[str]:
    """Extract the model roots at `ref` into tmp via git archive.

    Returns the roots that exist at that ref; empty when the ref has no
    model content under the given roots.
    """
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "ls-tree", "-r", "--name-only",
             ref, "--"] + roots,
            capture_output=True, text=True, timeout=60,
        )
        names = set(out.stdout.splitlines())
    except Exception:
        return []
    existing = [r for r in roots if any(n.startswith(r + "/") for n in names)]
    if not existing:
        return []
    try:
        arc = subprocess.run(
            ["git", "-C", str(repo_root), "archive", "--format=tar", ref, "--"]
            + existing,
            capture_output=True, timeout=120,
        )
    except Exception:
        return []
    if arc.returncode != 0:
        return []
    with tarfile.open(fileobj=io.BytesIO(arc.stdout), mode="r|") as tf:
        for member in tf:
            if member.name.startswith("/") or ".." in member.name.split("/"):
                continue  # never extract outside tmp
            tf.extract(member, tmp)
    return existing


def _breadcrumbs(site_path: str) -> list[tuple[str, str]]:
    """Breadcrumb trail: Model / ... / page label."""
    parts = Path(site_path).parts  # e.g. pages / textual-notation-of-model / ... / file.html
    crumbs = [("Model", "index.html")]
    if len(parts) == 1:  # index.html
        return crumbs
    # dirs between site root and the page
    for i in range(1, len(parts) - 1):
        dir_path = "/".join(parts[1 : i + 1])
        crumbs.append((parts[i], _rel_prefix(site_path) + f"pages/{dir_path}/index.html"))
    label = parts[-1]
    if label.endswith(".html"):
        label = label[: -len(".html")]
    crumbs.append((label, ""))
    return crumbs


def _tree_with_prefix(tree: TreeNode, prefix: str, active_site: str) -> str:
    def walk(node: TreeNode) -> tuple[str, bool]:
        """Returns (html, contains_active) — the second value lets parents
        keep the whole ancestor chain of the active page open."""
        contains = node.site_href == active_site
        kids = []
        for c in node.children:
            child_html, child_contains = walk(c)
            contains = contains or child_contains
            kids.append(child_html)
        kids_html = "".join(kids)
        href = prefix + node.site_href if node.site_href else ""
        cls = f"tree-node tree-{node.kind}"
        if node.site_href and node.site_href == active_site:
            cls += " active"
        inner = f'<span class="tree-icon">{_icon(node.kind)}</span>'
        if href:
            label = f'<a href="{href}">{_esc(node.label)}</a>'
        else:
            label = f"<span class='tree-label'>{_esc(node.label)}</span>"
        meta = f"<span class='tree-meta'>{_esc(node.meta)}</span>" if node.meta else ""
        if kids_html:
            open_attr = " open" if node.depth <= 1 or contains else ""
            html = (
                f'<details class="{cls}"{open_attr}><summary>{inner} {label} {meta}</summary>'
                f"<ul>{kids_html}</ul></details>"
            )
        else:
            html = f'<li class="{cls}">{inner} {label} {meta}</li>'
        return html, contains

    html, _ = walk(tree)
    return f"<ul>{html}</ul>"


def _icon(kind: str) -> str:
    from .render import _ICONS  # reuse the icon set

    base = kind.split()[0]
    for key in (kind, base):
        if key in _ICONS:
            return _ICONS[key]
    if base.endswith("def"):
        return _ICONS.get(base[:-4], _ICONS["other"])
    return _ICONS["other"]


def _esc(text: str) -> str:
    import html

    return html.escape(text, quote=True)


def _annotate_tree(root: TreeNode) -> None:
    """Add site_href/depth attributes for page-aware tree rendering."""
    def walk(node: TreeNode, site_href: str, depth: int) -> None:
        node.site_href = site_href
        node.depth = depth
        for c in node.children:
            walk(c, c.href, depth + 1)

    walk(root, "", 0)


def _build_site(
    repo_root: Path,
    out_dir: Path,
    roots: list[str],
    blob_base: str = "",
    options: list[tuple[str, str, bool, str, bool]] | None = None,
    current: str = "index.html",
    external_ref: bool = False,
) -> int:
    """Build one complete viewer site from the files under repo_root."""
    files = load_model(repo_root, roots)
    if not files:
        print("No .sysml files found under the given roots.", file=sys.stderr)
        return 2

    tree = build_tree(files)
    _annotate_tree(tree)
    stats = count_stats(files)

    diagrams = sum(
        1
        for mf in files
        for v in mf.views
        if (mf.path.parent / "diagrams" / _artifact(v)).exists()
    )
    missing = [
        (mf.rel_path, v.name)
        for mf in files
        for v in mf.views
        if not (mf.path.parent / "diagrams" / _artifact(v)).exists()
    ]

    # ---- write site ----
    out_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = out_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    css_src = Path(__file__).parent / "viewer.css"
    shutil.copyfile(css_src, assets_dir / "viewer.css")
    js_src = Path(__file__).parent / "viewer.js"
    shutil.copyfile(js_src, assets_dir / "viewer.js")

    # content stamp so browsers never serve stale assets (file:// caching)
    import hashlib

    stamp = hashlib.sha1(
        css_src.read_bytes() + js_src.read_bytes()
    ).hexdigest()[:10]

    if options is None:
        options = [("index.html", "working tree", True, "", True)]
    pages_root = out_dir / "pages"

    def picker(site: str) -> str:
        return render_ref_picker(options, current, site)

    # index page — its site path is the site root itself (current)
    index_tree = _tree_with_prefix(tree, "", "")
    (out_dir / "index.html").write_text(
        render_index(tree, stats, diagrams, picker(current), "", stamp),
        encoding="utf-8",
    )

    # directory TOC pages
    dirs: dict[str, list[TreeNode]] = {}
    for mf in files:
        parts = Path(mf.rel_path).parts[:-1]
        for i in range(1, len(parts) + 1):
            key = "/".join(parts[:i])
            dirs.setdefault(key, [])
    for d in sorted(dirs):
        site = f"pages/{d}/index.html"
        prefix = _rel_prefix(site)
        page = pages_root / d / "index.html"
        page.parent.mkdir(parents=True, exist_ok=True)
        # children of this dir in the tree
        node = _find_tree_node(tree, d)
        children = node.children if node else []
        page.write_text(
            render_dir_page(
                d.split("/")[-1],
                _breadcrumbs(site),
                _tree_with_prefix(tree, prefix, ""),
                children,
                prefix,
                picker(site),
                prefix,
                stamp,
            ),
            encoding="utf-8",
        )

    # file pages
    member_index = build_member_index(files)
    for mf in files:
        site = f"pages/{mf.rel_path}.html"
        prefix = _rel_prefix(site)
        page = pages_root / f"{mf.rel_path}.html"
        page.parent.mkdir(parents=True, exist_ok=True)
        repo_prefix = os.path.relpath(repo_root, page.parent).replace(os.sep, "/") + "/"
        source_url = blob_base + "/" + mf.rel_path if blob_base else ""
        page.write_text(
            render_file_page(
                mf,
                _tree_with_prefix(tree, prefix, site),
                prefix,
                repo_prefix,
                _breadcrumbs(site),
                source_url,
                member_index,
                picker(site),
                blob_base,
                external_ref,
                prefix,
                stamp,
            ),
            encoding="utf-8",
        )

    print(f"wrote {out_dir}")
    print(f"  files: {stats['files']}, views: {stats['views']}, "
          f"diagrams linked: {diagrams}, members: {stats['members']}")
    if missing:
        print(f"  views without committed diagrams: {len(missing)}")
        for rel, v in missing[:10]:
            print(f"    - {rel}: {v}")
    return 0


def generate(
    repo_root: Path,
    out_dir: Path,
    roots: list[str],
    refs: str | None = None,
    prs: bool = True,
    public: bool = False,
) -> int:
    """Build the working tree at the site root plus one sub-site per ref.

    With public=True the root build is labeled with the plain branch name
    (no "working tree" concept) — for published snapshots that must only
    show committed content.
    """
    repo_root = Path(repo_root).resolve()
    out_dir = Path(out_dir).resolve()

    specs, branch, pr_map = _expand_refs(repo_root, refs, prs)
    eligible: list[RefSpec] = []
    no_model: set[str] = set()
    for spec in specs:
        if _ref_has_model(repo_root, spec.ref, roots):
            eligible.append(spec)
        else:
            no_model.add(spec.short)
            print(
                f"  ref {spec.ref!r} has no .sysml under the model roots; skipped",
                file=sys.stderr,
            )
    if public:
        work_label = branch or "main"
    else:
        work_label = f"working tree · {branch}" if branch else "working tree"
    options: list[tuple[str, str, bool, str, bool]] = [
        ("index.html", work_label, True, "", True)
    ]
    for s in eligible:
        options.append((f"refs/{s.san}/index.html", s.label, True, "", True))
    if _is_git_root(repo_root):
        built_shorts = {s.short for s in eligible}
        for name, label in _known_unbuilt_refs(repo_root, branch, built_shorts, pr_map):
            if name in no_model:
                options.append(
                    (
                        "",
                        f"{label} (no model content)",
                        False,
                        "no .sysml under the validated model roots",
                        False,
                    )
                )
            else:
                options.append(
                    (
                        "",
                        f"{label} (not built)",
                        False,
                        f"regenerate with: --refs {name} (or --refs auto)",
                        True,
                    )
                )

    ok = True
    blob_base = _github_blob_base(repo_root, branch)
    rc = _build_site(
        repo_root, out_dir, roots,
        blob_base=blob_base, options=options, current="index.html",
    )
    if rc != 0:
        return rc

    for spec in eligible:
        with tempfile.TemporaryDirectory(prefix="model-viewer-ref-") as td:
            tmp = Path(td)
            if not _materialize(repo_root, spec.ref, roots, tmp):
                print(
                    f"  could not materialize ref {spec.ref!r}; skipped",
                    file=sys.stderr,
                )
                ok = False
                continue
            ref_out = out_dir / "refs" / spec.san
            blob_base = _github_blob_base(repo_root, spec.ref)
            if _build_site(
                tmp, ref_out, roots,
                blob_base=blob_base, options=options,
                current=f"refs/{spec.san}/index.html",
                external_ref=True,
            ) != 0:
                ok = False
    return 0 if ok else 2


def _artifact(v) -> str:
    from .model_parse import artifact_filename

    return artifact_filename(v.name, v.view_type)


def _find_tree_node(node: TreeNode, dir_rel: str) -> TreeNode | None:
    parts = Path(dir_rel).parts
    cur = node
    for p in parts:
        nxt = next((c for c in cur.children if c.label == p), None)
        if nxt is None:
            return None
        cur = nxt
    return cur


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="repository root (default: cwd)")
    parser.add_argument("--out", default="build/model-viewer", help="output directory")
    parser.add_argument(
        "--roots",
        nargs="*",
        default=DEFAULT_ROOTS,
        help="repo-relative model roots (default: both validated model roots)",
    )
    parser.add_argument(
        "--refs",
        default="",
        help='extra revisions to build: comma-separated refs (e.g. "main,feat/x") '
        'or "auto" for every local branch (default: main/origin/main if present)',
    )
    parser.add_argument(
        "--no-prs",
        action="store_true",
        help="skip GitHub PR labels for refs (default: label refs via gh when possible)",
    )
    parser.add_argument(
        "--public",
        action="store_true",
        help="published-snapshot mode: label the root build with the plain "
        "branch name (no 'working tree' concept); only committed content",
    )
    args = parser.parse_args(argv)
    return generate(
        Path(args.repo).resolve(),
        Path(args.out).resolve(),
        args.roots,
        refs=args.refs or None,
        prs=not args.no_prs,
        public=args.public,
    )


if __name__ == "__main__":
    raise SystemExit(main())
