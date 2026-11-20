#!/usr/bin/env python3
"""Records the S-CORE platform the start runs and the GPU it runs on (start_score_side.sh, after the start is up).

  score_platform_record.py <bundle> <out.json>

The platform pins come from the bundle's own facts, never from the kit's expectations (score-build/pins.sh):
score_lifecycle@<v> and score_communication@<v> from facts/score-mod-explain.txt (Bazel's resolution, written by
build_score_bench.sh), and the SOME/IP gateway's commit from facts/sources.txt (its "gateway <commit>"). The GPU is
nvidia-smi's answer on this host (`DA_NVIDIA_SMI`, default nvidia-smi on PATH). A value it cannot read is written
as {"absent": "<reason>"}, never empty and never guessed. It writes both to <out.json> and prints two lines, each
one JSON object after its keyword, which the session reads from the step's tail into session.json (score_runs.<run>
.score_platform and .score_gpu, and the session's score_platform and execution_environment.score_gpu):

  SCORE_PLATFORM {"lifecycle_version": ..., "communication_version": ..., "someip_gateway_commit": ..., "facts": ...}
  SCORE_GPU {"gpus": [{"name": ..., "driver_version": ...}], "query": ...}

Exit status: 0 recorded (absent values included); 2 usage.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

QUERY = ["--query-gpu=name,driver_version", "--format=csv,noheader"]
SMI_TIMEOUT_S = 20


def _one_version(text: str, module: str, where: str):
    found = sorted(set(re.findall(re.escape(module) + r"@([0-9A-Za-z.+_-]+)", text)))
    if not found:
        return {"absent": f"{where} names no {module}@<version>"}
    if len(found) > 1:
        return {"absent": f"{where} names more than one version: " + " and ".join(f"{module}@{v}" for v in found)}
    return f"{module}@{found[0]}"


def platform_facts(facts: Path) -> dict:
    """The platform pins as the bundle's facts state them."""
    out: dict = {}
    explain = facts / "score-mod-explain.txt"
    text = None
    reason = ""
    try:
        text = explain.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        reason = f"{explain} not readable ({exc.strerror or exc}): the bundle's facts give no Bazel resolution"
    for key, module in (("lifecycle_version", "score_lifecycle"), ("communication_version", "score_communication")):
        out[key] = _one_version(text, module, str(explain)) if text is not None else {"absent": reason}
    sources = facts / "sources.txt"
    try:
        commits = sorted(set(re.findall(r"(?:^|[;\s])gateway ([0-9a-f]{40})\b",
                                        sources.read_text(encoding="utf-8", errors="replace"))))
        if len(commits) == 1:
            out["someip_gateway_commit"] = commits[0]
        elif not commits:
            out["someip_gateway_commit"] = {"absent": f"{sources} names no gateway commit"}
        else:
            out["someip_gateway_commit"] = {"absent": f"{sources} names more than one gateway commit: "
                                                      + " and ".join(commits)}
    except OSError as exc:
        out["someip_gateway_commit"] = {"absent": f"{sources} not readable ({exc.strerror or exc})"}
    out["facts"] = str(facts)
    return out


def gpu_facts(smi: str | None = None) -> dict:
    """nvidia-smi's name and driver of every GPU of this host."""
    smi = smi or os.environ.get("DA_NVIDIA_SMI") or "nvidia-smi"
    query = " ".join(["nvidia-smi", *QUERY])
    try:
        p = subprocess.run([smi, *QUERY], capture_output=True, text=True, timeout=SMI_TIMEOUT_S)
    except FileNotFoundError:
        return {"absent": f"nvidia-smi not found on the S-CORE host ({smi})"}
    except subprocess.TimeoutExpired:
        return {"absent": f"nvidia-smi gave no answer within {SMI_TIMEOUT_S} s"}
    except OSError as exc:
        return {"absent": f"nvidia-smi could not run: {exc}"}
    text = (p.stdout or "").strip()
    if p.returncode != 0:
        first = (text or (p.stderr or "").strip()).splitlines()[:1]
        return {"absent": f"nvidia-smi exit {p.returncode}: {first[0] if first else 'no output'}"}
    gpus = []
    for line in text.splitlines():
        name, sep, driver = line.partition(",")
        if sep and name.strip() and driver.strip():
            gpus.append({"name": name.strip(), "driver_version": driver.strip()})
    if not gpus:
        return {"absent": "nvidia-smi listed no GPU" + (f" (answer: {text[:120]})" if text else "")}
    return {"gpus": gpus, "query": query}


def lines(platform: dict, gpu: dict) -> list[str]:
    """The two lines the session reads (one JSON object each, after its keyword)."""
    return ["SCORE_PLATFORM " + json.dumps(platform, ensure_ascii=False),
            "SCORE_GPU " + json.dumps(gpu, ensure_ascii=False)]


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    bundle, out = Path(argv[0]), Path(argv[1])
    platform, gpu = platform_facts(bundle / "facts"), gpu_facts()
    try:
        out.write_text(json.dumps({"score_platform": platform, "score_gpu": gpu}, indent=1) + "\n")
    except OSError as exc:
        print(f"score_platform_record: {out} not written: {exc}", file=sys.stderr)
    for line in lines(platform, gpu):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
