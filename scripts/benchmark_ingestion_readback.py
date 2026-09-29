#!/usr/bin/env python3
"""Retained-corpus HTTP read-back reuse benchmark (synthetic transport replay).

What this measures
------------------
The production import path (``de4sdv.sysml_api.ingestion.import_baseline``)
creates one immutable project/commit and then reads the element corpus back
over HTTP (``GET /projects/{p}/commits/{c}/elements``, default page size 100).

* ``before`` mode: ``import_baseline`` followed by a second full
  ``SysMLRepository.list_elements`` traversal (``page[size]=1000``) — the
  pre-optimization double traversal whose result fed
  ``validate_ontology_bindings``.
* ``after`` mode: ``import_baseline`` only, reusing
  ``BaselineImportResult.readback_elements`` for the same validation.

SYNTHETIC TRANSPORT REPLAY — NOT the production API and NOT a database.
The retained full-model export corpus is served over a loopback-only
standard-library ``http.server`` fixture that emulates the paginated elements
read contract (bare JSON array pages, ``Link: <...>; rel="next"``, default
page size 100, ``page[size]=1000`` honored). POST ``/projects`` and
``/projects/{p}/commits`` are answered with deterministic synthetic
identities; the fixture reads and accounts for the request bodies but stores
nothing. No network delay is injected anywhere: the only cost measured is real
HTTP pagination + JSON decode + validation over loopback. This benchmark is a
local replay of retained bytes, not a full-model end-to-end speedup claim.

Parity proof (computed independently in each child and compared by the parent):
element identity set, internal-reference path set, per-element canonical JSON
content digest, and the exact ``validate_ontology_bindings(...)`` result digest
must be identical between ``before`` and ``after`` and match the export.

Usage (parent orchestrator):
  python scripts/benchmark_ingestion_readback.py \
      --export /path/to/de4sdv-full-model-export.json \
      [--repeat 3] [--out-dir /tmp/de4sdv-readback-bench]

Each mode/repeat runs in its own subprocess (fresh interpreter) so wall time
and peak RSS are per-run measurements; children print a ``RESULT:`` JSON line
and write a full artifact under the output directory.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import re
import resource
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REPLAY_LABEL = "synthetic-transport-replay"
DEFAULT_PAGE_SIZE = 100  # baseline import read-back default
SECOND_PAGE_SIZE = 1000  # SysMLRepository.list_elements page size
FIXTURE_VERSION = "de4sdv-synthetic-transport-replay/1"

_ELEMENTS_ROUTE = re.compile(r"^/projects/([^/]+)/commits/([^/]+)/elements$")
_COMMITS_ROUTE = re.compile(r"^/projects/([^/]+)/commits$")


# ---------------------------------------------------------------------------
# loopback fixture
# ---------------------------------------------------------------------------


class _ReplayState:
    """Shared fixture state: served corpus + request accounting."""

    def __init__(self, corpus: list[dict]) -> None:
        self.corpus = corpus
        self.log: list[dict] = []
        self.lock = threading.Lock()

    def record(self, entry: dict) -> None:
        with self.lock:
            self.log.append(entry)


class _ReplayHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = FIXTURE_VERSION

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return  # fixture traffic is accounted for explicitly below

    # -- helpers ------------------------------------------------------------

    def _send_json(self, status: int, body: bytes, extra: dict[str, str] | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-DE4SDV-Replay", REPLAY_LABEL)
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(length) if length else b""

    # -- routes -------------------------------------------------------------

    def do_GET(self) -> None:  # noqa: N802
        state: _ReplayState = self.server.state  # type: ignore[attr-defined]
        url = urlsplit(self.path)
        match = _ELEMENTS_ROUTE.match(url.path)
        if match is None:
            body = json.dumps({"error": "fixture serves only the elements route"}).encode()
            self._send_json(404, body)
            state.record({"method": "GET", "path": url.path, "status": 404, "body_bytes": len(body)})
            return
        query = parse_qs(url.query)
        try:
            page_size = int(query.get("page[size]", [str(DEFAULT_PAGE_SIZE)])[0])
            page_number = int(query.get("page[number]", ["1"])[0])
        except ValueError:
            body = json.dumps({"error": "invalid page parameters"}).encode()
            self._send_json(400, body)
            state.record({"method": "GET", "path": url.path, "status": 400, "body_bytes": len(body)})
            return
        if page_size <= 0 or page_number <= 0:
            body = json.dumps({"error": "page parameters must be positive"}).encode()
            self._send_json(400, body)
            state.record({"method": "GET", "path": url.path, "status": 400, "body_bytes": len(body)})
            return
        start = (page_number - 1) * page_size
        page = state.corpus[start : start + page_size]
        body = json.dumps(page).encode()
        extra: dict[str, str] = {}
        if start + page_size < len(state.corpus):
            next_url = (
                f"{url.path}?page%5Bsize%5D={page_size}"
                f"&page%5Bnumber%5D={page_number + 1}"
            )
            extra["Link"] = f'<{next_url}>; rel="next"'
        self._send_json(200, body, extra)
        state.record(
            {
                "method": "GET",
                "path": url.path,
                "query": url.query,
                "status": 200,
                "page_number": page_number,
                "page_size": page_size,
                "items": len(page),
                "body_bytes": len(body),
            }
        )

    def do_POST(self) -> None:  # noqa: N802
        state: _ReplayState = self.server.state  # type: ignore[attr-defined]
        url = urlsplit(self.path)
        payload = self._read_body()
        if url.path == "/projects":
            try:
                name = json.loads(payload.decode("utf-8")).get("name", "")
            except (json.JSONDecodeError, UnicodeDecodeError):
                name = ""
            project_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"de4sdv-replay:project:{name}"))
            body = json.dumps({"@type": "Project", "@id": project_id, "name": name}).encode()
            self._send_json(201, body)
            state.record(
                {
                    "method": "POST",
                    "path": url.path,
                    "status": 201,
                    "request_bytes": len(payload),
                    "body_bytes": len(body),
                }
            )
            return
        commit_match = _COMMITS_ROUTE.match(url.path)
        if commit_match is not None:
            project_id = commit_match.group(1)
            digest = hashlib.sha256(payload).hexdigest()
            commit_id = str(
                uuid.uuid5(uuid.NAMESPACE_URL, f"de4sdv-replay:commit:{project_id}:{digest}")
            )
            body = json.dumps({"@type": "Commit", "@id": commit_id}).encode()
            self._send_json(201, body)
            state.record(
                {
                    "method": "POST",
                    "path": url.path,
                    "status": 201,
                    "request_bytes": len(payload),
                    "body_bytes": len(body),
                }
            )
            return
        body = json.dumps({"error": "fixture serves only /projects and commit POSTs"}).encode()
        self._send_json(404, body)
        state.record(
            {
                "method": "POST",
                "path": url.path,
                "status": 404,
                "request_bytes": len(payload),
                "body_bytes": len(body),
            }
        )


def start_fixture(corpus: list[dict]) -> tuple[ThreadingHTTPServer, threading.Thread, _ReplayState]:
    state = _ReplayState(corpus)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _ReplayHandler)
    httpd.daemon_threads = True
    httpd.state = state  # type: ignore[attr-defined]
    thread = threading.Thread(target=httpd.serve_forever, name="replay-fixture", daemon=True)
    thread.start()
    return httpd, thread, state


# ---------------------------------------------------------------------------
# digests / parity primitives
# ---------------------------------------------------------------------------


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def content_digest(elements: list[dict]) -> str:
    ordered = sorted(elements, key=lambda item: str(item.get("@id")))
    return hashlib.sha256(_canonical_json(ordered)).hexdigest()


def identity_digest(elements: list[dict]) -> str:
    ids = sorted(str(item.get("@id")) for item in elements)
    return hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()


def reference_digest(elements: list[dict]) -> str:
    from de4sdv.sysml_api.ingestion import _reference_paths

    keyed = {str(item.get("@id")): item for item in elements}
    references = sorted(_reference_paths(keyed))
    return hashlib.sha256("\n".join(f"{s}\x00{p}\x00{t}" for s, p, t in references).encode()).hexdigest()


def digest_of(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _rss_peak_kb() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


# ---------------------------------------------------------------------------
# child: one mode, one run
# ---------------------------------------------------------------------------


def run_child(mode: str, export_path: Path, out_path: Path) -> dict:
    from de4sdv.semantic.kernel_contract import KernelContract
    from de4sdv.semantic.validation import validate_ontology_bindings
    from de4sdv.sysml_api.baseline import BaselineExportBundle
    from de4sdv.sysml_api.client import ApiClient
    from de4sdv.sysml_api.ingestion import import_baseline
    from de4sdv.sysml_api.repository import SysMLRepository

    t_total0 = time.perf_counter()

    export_bytes = export_path.read_bytes()
    export_sha256 = hashlib.sha256(export_bytes).hexdigest()
    export_size = len(export_bytes)
    bundle = BaselineExportBundle.load(export_path)
    corpus = [bundle.elements[element_id] for element_id in sorted(bundle.elements)]
    export_content_digest = content_digest(corpus)
    del export_bytes

    httpd, thread, state = start_fixture(corpus)
    port = httpd.server_address[1]
    client = ApiClient(f"http://127.0.0.1:{port}", timeout=600.0)

    try:
        t_import0 = time.perf_counter()
        imported = import_baseline(
            client,
            bundle,
            project_name=f"DE4SDV {REPLAY_LABEL}",
        )
        t_import1 = time.perf_counter()

        first_fetch_count = len(imported.readback_elements)
        first_fetch_content_digest = content_digest(list(imported.readback_elements))
        first_fetch_identity_digest = identity_digest(list(imported.readback_elements))
        first_fetch_reference_digest = reference_digest(list(imported.readback_elements))

        project_id = imported.project_id
        commit_id = imported.commit_id

        if mode == "before":
            # The original importer discarded its read-back before the second
            # fetch. Match that lifetime; retaining both would inflate baseline RSS.
            del imported
            gc.collect()
            repository = SysMLRepository(client)
            t_fetch0 = time.perf_counter()
            elements = list(repository.list_elements(project_id, commit_id))
            t_fetch1 = time.perf_counter()
        else:
            elements = list(imported.readback_elements)
            t_fetch0 = t_fetch1 = t_import1
        if mode == "after":
            del imported
        gc.collect()

        t_validate0 = time.perf_counter()
        contract = KernelContract.load(
            ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"
        )
        ontology = validate_ontology_bindings(contract, elements, bundle.element_sources)
        t_validate1 = time.perf_counter()
        ontology_dict = ontology.to_dict()
    finally:
        httpd.shutdown()
        thread.join(timeout=10)
        httpd.server_close()

    second_fetch_count = len(elements)
    content_digest_used = content_digest(elements)
    identity_digest_used = identity_digest(elements)
    reference_digest_used = reference_digest(elements)

    get_entries = [entry for entry in state.log if entry.get("method") == "GET" and entry.get("status") == 200]
    post_entries = [entry for entry in state.log if entry.get("method") == "POST" and entry.get("status") in (200, 201)]

    # Internal reference count exactly as the production import computes it.
    from de4sdv.sysml_api.ingestion import _reference_paths

    internal_reference_count = len(_reference_paths(bundle.elements))

    def _page_size(entry: dict) -> int:
        return int(entry.get("page_size", DEFAULT_PAGE_SIZE))

    first_pages = [e for e in get_entries if _page_size(e) != SECOND_PAGE_SIZE]
    second_pages = [e for e in get_entries if _page_size(e) == SECOND_PAGE_SIZE]

    result = {
        "label": REPLAY_LABEL,
        "mode": mode,
        "export_path": str(export_path),
        "export_sha256": export_sha256,
        "export_bytes": export_size,
        "export_git_commit": bundle.git_commit,
        "element_count": second_fetch_count,
        "internal_reference_count": internal_reference_count,
        "digests": {
            "export_content": export_content_digest,
            "first_fetch_content": first_fetch_content_digest,
            "first_fetch_identity": first_fetch_identity_digest,
            "first_fetch_references": first_fetch_reference_digest,
            "used_content": content_digest_used,
            "used_identity": identity_digest_used,
            "used_references": reference_digest_used,
            "ontology_result": digest_of(ontology_dict),
        },
        "within_mode_parity": {
            "first_fetch_count": first_fetch_count,
            "second_fetch_count": second_fetch_count,
            "content_equal": first_fetch_content_digest == content_digest_used,
            "identity_equal": first_fetch_identity_digest == identity_digest_used,
            "references_equal": first_fetch_reference_digest == reference_digest_used,
            "matches_export": content_digest_used == export_content_digest,
        },
        "ontology": {
            "passed": ontology.passed,
            "summary": ontology.summary,
            "result": ontology_dict,
        },
        "timing_s": {
            "total": time.perf_counter() - t_total0,
            "import_baseline": t_import1 - t_import0,
            "second_fetch": (t_fetch1 - t_fetch0) if mode == "before" else 0.0,
            "ontology_validation": t_validate1 - t_validate0,
        },
        "rss_peak_kb": _rss_peak_kb(),
        "server_accounting": {
            "fixture": FIXTURE_VERSION,
            "injected_delay_s": 0.0,
            "default_page_size": DEFAULT_PAGE_SIZE,
            "requests_total": len(state.log),
            "pages_total": len(get_entries),
            "pages_first_fetch": len(first_pages),
            "pages_second_fetch": len(second_pages),
            "get_body_bytes": sum(int(e["body_bytes"]) for e in get_entries),
            "get_body_bytes_first_fetch": sum(int(e["body_bytes"]) for e in first_pages),
            "get_body_bytes_second_fetch": sum(int(e["body_bytes"]) for e in second_pages),
            "post_request_bytes": sum(int(e.get("request_bytes", 0)) for e in post_entries),
            "post_body_bytes": sum(int(e["body_bytes"]) for e in post_entries),
        },
        "client_reported": {
            "project_id": project_id,
            "commit_id": commit_id,
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


# ---------------------------------------------------------------------------
# parent orchestration + parity verdict
# ---------------------------------------------------------------------------


def _child_result_line(stdout: str) -> dict | None:
    for line in reversed(stdout.splitlines()):
        if line.startswith("RESULT: "):
            return json.loads(line[len("RESULT: ") :])
    return None


def run_parent(args: argparse.Namespace) -> int:
    export_path = Path(args.export)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    export_bytes = export_path.read_bytes()
    export_sha256 = hashlib.sha256(export_bytes).hexdigest()
    export_size = len(export_bytes)
    del export_bytes

    script = str(Path(__file__).resolve())
    runs: dict[str, list[dict]] = {"after": [], "before": []}
    for mode in ("after", "before"):
        for index in range(args.repeat):
            out_path = out_dir / f"{mode}-run{index}.json"
            cmd = [
                sys.executable,
                script,
                "--child",
                mode,
                "--export",
                str(export_path),
                "--out",
                str(out_path),
            ]
            started = time.perf_counter()
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
            parent_wall = time.perf_counter() - started
            if proc.returncode != 0:
                print(f"child failed: mode={mode} run={index} rc={proc.returncode}", file=sys.stderr)
                print(proc.stdout[-4000:], file=sys.stderr)
                print(proc.stderr[-4000:], file=sys.stderr)
                return 2
            result = _child_result_line(proc.stdout)
            if result is None:
                print(f"child produced no RESULT line: mode={mode} run={index}", file=sys.stderr)
                return 2
            result["parent_wall_s"] = parent_wall
            runs[mode].append(result)
            print(
                f"[{mode} #{index}] wall={result['timing_s']['total']:.2f}s "
                f"import={result['timing_s']['import_baseline']:.2f}s "
                f"second_fetch={result['timing_s']['second_fetch']:.2f}s "
                f"validate={result['timing_s']['ontology_validation']:.2f}s "
                f"pages={result['server_accounting']['pages_total']} "
                f"get_MB={result['server_accounting']['get_body_bytes'] / 1e6:.1f} "
                f"rss_MB={result['rss_peak_kb'] / 1024:.0f}"
            )

    # ---- parity verdict ----------------------------------------------------
    all_runs = runs["after"] + runs["before"]
    digest_keys = [
        "export_content",
        "first_fetch_content",
        "first_fetch_identity",
        "first_fetch_references",
        "used_content",
        "used_identity",
        "used_references",
        "ontology_result",
    ]
    digest_uniform: dict[str, bool] = {}
    for key in digest_keys:
        values = {run["digests"][key] for run in all_runs}
        digest_uniform[key] = len(values) == 1

    checks = {
        "export_sha256_matches_input": all(run["export_sha256"] == export_sha256 for run in all_runs),
        "element_count_equal_all_runs": len({run["element_count"] for run in all_runs}) == 1,
        "internal_reference_count_equal_all_runs": len({run["internal_reference_count"] for run in all_runs}) == 1,
        "ontology_passed_all_runs": all(run["ontology"]["passed"] for run in all_runs),
        "ontology_summary_equal_all_runs": len(
            {json.dumps(run["ontology"]["summary"], sort_keys=True) for run in all_runs}
        )
        == 1,
        "ontology_result_digest_equal_all_runs": digest_uniform["ontology_result"],
        "used_content_digest_equal_before_after": digest_uniform["used_content"],
        "used_identity_digest_equal_before_after": digest_uniform["used_identity"],
        "used_references_digest_equal_before_after": digest_uniform["used_references"],
        "used_content_matches_export": digest_uniform["export_content"]
        and all(run["within_mode_parity"]["matches_export"] for run in all_runs),
        "within_mode_first_vs_second_fetch_equal": all(
            run["within_mode_parity"]["content_equal"]
            and run["within_mode_parity"]["identity_equal"]
            and run["within_mode_parity"]["references_equal"]
            for run in all_runs
        ),
    }
    parity_pass = all(checks.values())

    def _agg(mode: str, path: tuple[str, ...]) -> dict[str, float]:
        values = []
        for run in runs[mode]:
            node: object = run
            for key in path:
                node = node[key]  # type: ignore[index]
            values.append(float(node))
        return {
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / len(values),
        }

    summary = {
        "label": REPLAY_LABEL,
        "input": {
            "export_path": str(export_path),
            "export_sha256": export_sha256,
            "export_bytes": export_size,
            "export_git_commit": all_runs[0]["export_git_commit"],
            "element_count": all_runs[0]["element_count"],
            "internal_reference_count": all_runs[0]["internal_reference_count"],
        },
        "fixture": {
            "version": FIXTURE_VERSION,
            "default_page_size": DEFAULT_PAGE_SIZE,
            "second_fetch_page_size": SECOND_PAGE_SIZE,
            "injected_delay_s": 0.0,
        },
        "repeat": args.repeat,
        "modes": {
            mode: {
                "runs": len(runs[mode]),
                "wall_s": _agg(mode, ("timing_s", "total")),
                "import_baseline_s": _agg(mode, ("timing_s", "import_baseline")),
                "second_fetch_s": _agg(mode, ("timing_s", "second_fetch")),
                "ontology_validation_s": _agg(mode, ("timing_s", "ontology_validation")),
                "rss_peak_kb": _agg(mode, ("rss_peak_kb",)),
                "pages_total": _agg(mode, ("server_accounting", "pages_total")),
                "pages_first_fetch": _agg(mode, ("server_accounting", "pages_first_fetch")),
                "pages_second_fetch": _agg(mode, ("server_accounting", "pages_second_fetch")),
                "get_body_bytes": _agg(mode, ("server_accounting", "get_body_bytes")),
                "post_request_bytes": _agg(mode, ("server_accounting", "post_request_bytes")),
            }
            for mode in ("after", "before")
        },
        "parity_checks": checks,
        "parity_pass": parity_pass,
        "digests": {
            key: sorted({run["digests"][key] for run in all_runs}) for key in digest_keys
        },
    }
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print()
    print("=== parity ===")
    for name, ok in checks.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    print()
    print("=== headline ===")
    for mode in ("after", "before"):
        agg = summary["modes"][mode]
        print(
            f"  {mode:6s}: wall {agg['wall_s']['mean']:.2f}s  "
            f"pages {agg['pages_total']['mean']:.0f}  "
            f"GET {agg['get_body_bytes']['mean'] / 1e6:.1f} MB  "
            f"POST {agg['post_request_bytes']['mean'] / 1e6:.1f} MB  "
            f"RSS {agg['rss_peak_kb']['mean'] / 1024:.0f} MB"
        )
    print()
    print(f"summary: {summary_path}")
    print(f"parity_pass={parity_pass}")
    return 0 if parity_pass else 1


# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", required=True, help="retained full-model export JSON path")
    parser.add_argument("--repeat", type=int, default=3, help="runs per mode (default 3)")
    parser.add_argument("--out-dir", default="/tmp/de4sdv-readback-bench")
    parser.add_argument("--child", choices=("before", "after"), help=argparse.SUPPRESS)
    parser.add_argument("--out", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error("--repeat must be positive")
    if args.child:
        if not args.out:
            parser.error("--child requires --out")
        result = run_child(args.child, Path(args.export), Path(args.out))
        print("RESULT: " + json.dumps(result))
        return 0
    return run_parent(args)


if __name__ == "__main__":
    raise SystemExit(main())
