"""Generate the DE4SDV static HTML model viewer.

Usage:
    python -m tools.sysml_html_viewer.generate [--repo REPO] [--out OUT]

The viewer is a read-only browser over the SysML v2 textual model: a
navigation tree on the left, and package/file/element/view pages on the
right. Views embed the committed SysIDE diagram artifacts; nothing is
re-rendered or invented.

Output defaults to ``build/model-viewer`` (gitignored). Serve from the
repository root, e.g. ``python -m http.server`` — all links are relative
and the site also works from ``file://``.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
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
    render_tree,
)

DEFAULT_ROOTS = ["textual-notation-of-model/packages"]


def _rel_prefix(site_path: str) -> str:
    """Relative path prefix from the page at site_path up to the site root."""
    parts = Path(site_path).parts
    return "../" * max(0, len(parts) - 1)


def _source_url(repo_root: Path, rel_path: str) -> str:
    """Best-effort GitHub blob URL for a repo-relative file."""
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
        return f"{url}/blob/main/{rel_path}"
    except Exception:
        return ""


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
    def walk(node: TreeNode) -> str:
        href = prefix + node.site_href if node.site_href else ""
        cls = f"tree-node tree-{node.kind}"
        if node.site_href and node.site_href == active_site:
            cls += " active"
        kids = "".join(walk(c) for c in node.children)
        inner = f'<span class="tree-icon">{_icon(node.kind)}</span>'
        if href:
            label = f'<a href="{href}">{_esc(node.label)}</a>'
        else:
            label = f"<span class='tree-label'>{_esc(node.label)}</span>"
        meta = f"<span class='tree-meta'>{_esc(node.meta)}</span>" if node.meta else ""
        if kids:
            open_attr = " open" if node.depth <= 1 or node.site_href == active_site else ""
            return (
                f'<details class="{cls}"{open_attr}><summary>{inner} {label} {meta}</summary>'
                f"<ul>{kids}</ul></details>"
            )
        return f'<li class="{cls}">{inner} {label} {meta}</li>'

    return f"<ul>{walk(tree)}</ul>"


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


def generate(repo_root: Path, out_dir: Path, roots: list[str]) -> int:
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

    pages_root = out_dir / "pages"

    # index page
    index_tree = _tree_with_prefix(tree, "", "")
    (out_dir / "index.html").write_text(
        render_index(tree, stats, diagrams), encoding="utf-8"
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
        page.write_text(
            render_file_page(
                mf,
                _tree_with_prefix(tree, prefix, site),
                prefix,
                repo_prefix,
                _breadcrumbs(site),
                _source_url(repo_root, mf.rel_path),
                member_index,
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
        help="repo-relative model roots (default: textual-notation-of-model/packages)",
    )
    args = parser.parse_args(argv)
    return generate(Path(args.repo).resolve(), Path(args.out).resolve(), args.roots)


if __name__ == "__main__":
    raise SystemExit(main())
