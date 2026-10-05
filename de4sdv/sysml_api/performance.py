"""Opt-in, out-of-band ingestion measurements; never evidence payload fields."""
from __future__ import annotations

from contextlib import contextmanager
import json
import os
import sys
from time import perf_counter
from typing import Any, Iterator


@contextmanager
def timing(stage: str, **metadata: Any) -> Iterator[dict[str, Any]]:
    """Append one monotonic stage measurement, including failed stages.

    No URLs, request bodies, credentials or exception text are recorded. Peak
    RSS is process-lifetime high-water memory, not a per-stage allocation.
    Nested durations overlap and must not be summed. Callers supply only
    non-sensitive counts. A telemetry I/O failure never masks a real failure.
    """
    destination = os.environ.get("DE4SDV_INGESTION_TIMINGS")
    if not destination:
        yield metadata
        return
    started = perf_counter()
    status = "failed"
    try:
        yield metadata
        status = "passed"
    finally:
        record = {
            **metadata,
            "schema": "de4sdv-ingestion-timing/v1",
            "stage": stage,
            "pid": os.getpid(),
            "elapsed_seconds": perf_counter() - started,
            "status": status,
        }
        try:
            import resource
            rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            record["process_peak_rss_bytes"] = rss if sys.platform == "darwin" else rss * 1024
        except ImportError:
            pass
        try:
            with open(destination, "a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, sort_keys=True) + "\n")
        except (OSError, TypeError, ValueError):
            # Telemetry must never replace an in-flight exception: unserializable
            # caller metadata or an unwritable destination only warns.
            print("warning: ingestion timing output unavailable", file=sys.stderr)
