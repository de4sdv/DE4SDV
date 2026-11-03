"""Report the runner's disk use as one workflow annotation (privileged ingestion).

Release run 41718067304 died with "No space left on device" while importing
candidate transaction 1, and the runner lost its job log with it. The
annotations of the steps that had finished survived, so each report is one
``::notice`` annotation: free space on the filesystem of /tmp, the API service
log, the run's exports and the database the imports fill.

Diagnostic only: it exits 0 whatever it cannot measure, imports only the
standard library and writes nothing, so the dirty-checkout guards stay green.
"""
from __future__ import annotations

import argparse
import glob
import os
import shutil
import subprocess

GIB = 1024 ** 3
MIB = 1024 ** 2


def _size(path: str) -> int | None:
    try:
        return os.path.getsize(path)
    except OSError:
        return None


def _database_bytes(container: str) -> int | None:
    """The size of the sysml2 database in the PostgreSQL service container."""
    if not container:
        return None
    try:
        result = subprocess.run(
            ["docker", "exec", container, "psql", "-U", "postgres", "-d", "sysml2", "-tAc",
             "select pg_database_size('sysml2')"],
            capture_output=True, text=True, timeout=60, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    answer = result.stdout.strip()
    return int(answer) if result.returncode == 0 and answer.isdigit() else None


def _mib(value: int | None) -> str:
    return "unknown" if value is None else f"{round(value / MIB)} MiB"


def report(label: str, path: str, api_log: str, exports: str, container: str) -> str:
    try:
        usage = shutil.disk_usage(path)
        disk = (f"{usage.free / GIB:.1f} GiB free of {usage.total / GIB:.1f} GiB "
                f"on the filesystem of {path}")
    except OSError:
        disk = f"free space on the filesystem of {path} unknown"
    log = _size(api_log)
    files = [size for size in map(_size, glob.glob(exports)) if size is not None]
    parts = (disk,
             "API service log absent" if log is None else f"API service log {_mib(log)}",
             f"{len(files)} files matching {exports}: {_mib(sum(files))}",
             f"database {_mib(_database_bytes(container))}")
    return f"{label}: " + "; ".join(parts)


def _escape(data: str) -> str:
    """Workflow-command data escaping (%, CR, LF)."""
    return data.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report the runner's disk use as one workflow annotation.")
    parser.add_argument("--label", required=True, help="when in the run the report is taken")
    parser.add_argument("--path", default="/tmp", help="a path on the filesystem to report")
    parser.add_argument("--api-log", default="/tmp/sysml-api.log")
    parser.add_argument("--exports", default="/tmp/de4sdv-*.json", help="glob of the run's files")
    parser.add_argument("--postgres-container", default="",
                        help="the PostgreSQL service container id (job.services.postgres.id)")
    args = parser.parse_args(argv)
    try:
        message = report(args.label, args.path, args.api_log, args.exports,
                         args.postgres_container)
    except Exception as error:  # noqa: BLE001 - a diagnostic never fails the run
        message = f"{args.label}: disk report failed ({type(error).__name__}: {error})"
    print(f"::notice title=Runner disk::{_escape(message)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
