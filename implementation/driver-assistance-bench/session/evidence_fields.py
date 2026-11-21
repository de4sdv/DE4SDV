#!/usr/bin/env python3
"""The session's producers of the evidence record's fields that no other step writes (case-evaluators/
evidence_record.py reads them for RetainedAssistanceRunEvidence, driver_assistance_verification_evidence.sysml:150-242):

  session.json configuration_identity, configuration_receipt_sha256 (with configuration_receipt: its path, commit,
  the digest the model binds, and the file and line of each source), visualization_recorder_delay,
  score_platform.{lifecycle_version, communication_version, someip_gateway_commit}, and
  execution_environment.{score_gpu, sdv_core_image, ivi_image}; per run score_runs.<run>.score_platform and
  .score_gpu.

A field the session cannot read is {"absent": "<reason>"}, never empty and never guessed.

- The configured product and its receipt: from the committed model at the session's own commit (`git show
  <commit>:<path>`, never the working tree and never a string in this file): the part <'DRIVING-CONFIG-...'> of
  driver_assistance_variability_configuration.sysml, the receipt file its doc names ("receiptSha256 is the SHA-256 of
  <path>,") and the digest it binds; the evidence item's doc must bind the same identity ("It binds <id> as its
  configurationIdentity"). configuration_receipt_sha256 is the SHA-256 of the receipt at the commit, the receipt
  the run ran against; whether it equals the model's bound digest is recorded beside it.
- The recorder's delay: the model's sentence verbatim (RetainedAssistanceRunEvidence's doc: "the readiness probe of
  the recorder on <date> measured ... on an S-CORE host with an <GPU>"), with its file, lines and commit. It holds
  only for an S-CORE host with that GPU: "a run on another host states the delay it measures".
- The platform and the GPU: each S-CORE start's SCORE_PLATFORM and SCORE_GPU lines (score-path/scripts/
  score_platform_record.py), per run and, where every start agrees, for the session.
- The guest images: guest_up.sh's GUEST_IMAGE lines (the booted guests' product, build id, fingerprint, vbmeta
  digest), once per session.

  evidence_fields.py config <bench tree> <commit> <out.json>   the preflight's read (prints one line for the log)
  evidence_fields.py line <SCORE_PLATFORM json> <SCORE_GPU json>  one log line for a start's two lines

write_record (da_session.sh) calls session_fields() with the session's folder and its score_runs.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys

CONFIG_SYSML = "textual-notation-of-model/packages/features/driving/driver_assistance_variability_configuration.sysml"
EVIDENCE_SYSML = "textual-notation-of-model/packages/features/driving/driver_assistance_verification_evidence.sysml"
PLATFORM_KEYS = ("lifecycle_version", "communication_version", "someip_gateway_commit")
GUEST_ROLES = (("sdv_core", "sdv_core_image"), ("ivi", "ivi_image"))


class NotCommitted(Exception):
    """A file the session reads from its commit is not there (or there is no commit, or no git)."""


def git_reader(tree: str, commit: str):
    """read(path) -> the bytes of <path> at <commit> of the git tree <tree>."""
    def read(path: str) -> bytes:
        if not re.fullmatch(r"[0-9a-f]{40}", commit or ""):
            raise NotCommitted(f"no commit of the bench tree ({commit or 'none'}): the session reads {path} only "
                               "from its commit")
        try:
            p = subprocess.run(["git", "-C", str(tree), "show", f"{commit}:{path}"], capture_output=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise NotCommitted(f"git could not read {path} at {commit}: {exc}") from None
        if p.returncode != 0:
            raise NotCommitted(f"{path} is not in commit {commit}: "
                               f"{p.stderr.decode(errors='replace').strip().splitlines()[:1]}")
        return p.stdout
    return read


def _absent(reason: str) -> dict:
    return {"absent": reason}


def _doc_text(lines: list[str], first: int, last: int) -> str:
    """The doc comment's words between two lines (1-based, inclusive), without the ` * ` prefixes."""
    return " ".join(re.sub(r"^\s*(/\*+|\*/|\*)\s?", "", ln).strip() for ln in lines[first - 1:last]).strip()


def _line_of(lines: list[str], pattern: str, start: int = 1) -> int | None:
    for i in range(start - 1, len(lines)):
        if re.search(pattern, lines[i]):
            return i + 1
    return None


def _item_doc(lines: list[str], header: str) -> tuple[int, int, str] | None:
    """The doc of the declaration whose line matches header: (first line, last line, text)."""
    h = _line_of(lines, header)
    if h is None:
        return None
    a = _line_of(lines, r"doc\s*/\*", h)
    b = _line_of(lines, r"\*/", a or h)
    if a is None or b is None:
        return None
    return a, b, _doc_text(lines, a, b)


def configuration(read, commit: str) -> dict:
    """configuration_identity, configuration_receipt_sha256 and configuration_receipt, from the commit's files."""
    out: dict = {"configuration_receipt": {"commit": commit, "sources": {}}}
    rec = out["configuration_receipt"]
    try:
        cfg = read(CONFIG_SYSML).decode("utf-8", errors="replace").splitlines()
    except NotCommitted as exc:
        out["configuration_identity"] = out["configuration_receipt_sha256"] = _absent(str(exc))
        return out
    parts = [(i + 1, m.group(1)) for i, ln in enumerate(cfg)
             for m in [re.search(r"\bpart\s*<'(DRIVING-CONFIG-[0-9]+)'>\s*configuredProduct\s*:", ln)] if m]
    if len(parts) != 1:
        out["configuration_identity"] = _absent(
            f"{CONFIG_SYSML} at {commit} holds no part <'DRIVING-CONFIG-...'> configuredProduct" if not parts else
            f"{CONFIG_SYSML} at {commit} holds {len(parts)} configured products: {[p for _, p in parts]}")
        identity, part_line = None, None
    else:
        part_line, identity = parts[0]
        rec["sources"]["configuration_identity"] = f"{CONFIG_SYSML}:{part_line} at {commit}"
        # the evidence item binds the same identity (RetainedAssistanceRunEvidence's doc)
        try:
            ev = read(EVIDENCE_SYSML).decode("utf-8", errors="replace").splitlines()
            doc = _item_doc(ev, r"\bitem def RetainedAssistanceRunEvidence\b")
            m = re.search(r"It binds (DRIVING-CONFIG-[0-9]+) as its configurationIdentity", doc[2]) if doc else None
            if m is None:
                out["configuration_identity"] = _absent(f"{EVIDENCE_SYSML} at {commit}: RetainedAssistanceRunEvidence "
                                                        "names no configuration it binds")
            elif m.group(1) != identity:
                out["configuration_identity"] = _absent(
                    f"{CONFIG_SYSML}:{part_line} names {identity}, but RetainedAssistanceRunEvidence binds "
                    f"{m.group(1)} ({EVIDENCE_SYSML} at {commit})")
            else:
                out["configuration_identity"] = identity
                rec["sources"]["evidence_binding"] = \
                    f"{EVIDENCE_SYSML}:{_line_of(ev, r'It binds', doc[0])} at {commit}"
        except NotCommitted as exc:
            out["configuration_identity"] = _absent(str(exc))
    # the receipt the configured product names, and the digest it binds
    if part_line is None:
        out["configuration_receipt_sha256"] = _absent("no configured product to name its receipt (see "
                                                      "configuration_identity)")
        return out
    end = _line_of(cfg, r"^\s{2}\}", part_line) or len(cfg)
    body = _doc_text(cfg, part_line, end)
    m = re.search(r"receiptSha256 is the SHA-256 of (\S+?\.json),", body)
    bound_line = _line_of(cfg, r'attribute receiptSha256 : ScalarValues::String = "[0-9a-f]{64}";', part_line)
    if bound_line is not None and bound_line <= end:
        rec["model_bound_sha256"] = re.search(r'"([0-9a-f]{64})"', cfg[bound_line - 1]).group(1)
        rec["sources"]["model_bound_sha256"] = f"{CONFIG_SYSML}:{bound_line} at {commit}"
    else:
        rec["model_bound_sha256"] = None
    if m is None:
        out["configuration_receipt_sha256"] = _absent(f"the doc of {identity} ({CONFIG_SYSML}:{part_line} at "
                                                      f"{commit}) names no receipt file")
        return out
    rec["path"] = m.group(1)
    rec["sources"]["path"] = f"{CONFIG_SYSML}:{_line_of(cfg, re.escape(m.group(1)), part_line)} at {commit}"
    try:
        sha = hashlib.sha256(read(m.group(1))).hexdigest()
    except NotCommitted as exc:
        out["configuration_receipt_sha256"] = _absent(str(exc))
        return out
    out["configuration_receipt_sha256"] = sha
    rec["equal_to_model"] = sha == rec["model_bound_sha256"]
    return out


def model_delay(read, commit: str) -> dict:
    """The model's sentence of the recorder's delay, verbatim, with the GPU of the host it was measured on."""
    try:
        ev = read(EVIDENCE_SYSML).decode("utf-8", errors="replace").splitlines()
    except NotCommitted as exc:
        return _absent(str(exc))
    doc = _item_doc(ev, r"\bitem def RetainedAssistanceRunEvidence\b")
    m = re.search(r"visualizationRecorderDelay is the delay of the recorder that every verdict of the run states: "
                  r"(the readiness probe of the recorder on \d{4}-\d{2}-\d{2} measured .+? from an image to its "
                  r"command, on an S-CORE host with an? (NVIDIA [A-Za-z0-9 ]+?));", doc[2]) if doc else None
    if m is None:
        return _absent(f"{EVIDENCE_SYSML} at {commit}: RetainedAssistanceRunEvidence states no "
                       "visualizationRecorderDelay of the form the session reads")
    first = _line_of(ev, r"visualizationRecorderDelay is", doc[0])
    last = _line_of(ev, r"\bdelay\.\s*$", first) or first
    return {"text": m.group(1), "host_gpu": m.group(2),
            "source": f"{EVIDENCE_SYSML}:{first}-{last} at {commit} (RetainedAssistanceRunEvidence)"}


def recorder_delay(model: dict, score_gpu, gpu_names: list[str]):
    """visualization_recorder_delay: the model's sentence with its source, for a host with the model's GPU only."""
    if not isinstance(model, dict) or "text" not in model:
        return _absent((model or {}).get("absent") if isinstance(model, dict) and model.get("absent") else
                       "the model's sentence of the recorder's delay was not read")
    if not isinstance(score_gpu, str):
        return _absent(f"the S-CORE host's GPU is unread ({(score_gpu or {}).get('absent')}): the model's delay holds "
                       f"for an S-CORE host with an {model['host_gpu']} only")
    if not gpu_names or any(n != model["host_gpu"] for n in gpu_names):
        return _absent(f"the model's delay was measured on an S-CORE host with an {model['host_gpu']}; this "
                       f"session's S-CORE host has {score_gpu}: a run on another host states the delay it measures")
    return f"{model['text']} ({model['source']})"


def _json_line(value):
    if isinstance(value, dict):
        return value
    try:
        d = json.loads(value)
        return d if isinstance(d, dict) else None
    except (TypeError, ValueError):
        return None


def _gpu_text(g: dict):
    if not isinstance(g, dict) or not isinstance(g.get("gpus"), list) or not g["gpus"]:
        return None
    return "; ".join(f"{x.get('name')}, driver {x.get('driver_version')}" for x in g["gpus"])


def _agree(per_run: dict, what: str):
    """The one value every run gave, else absent naming each run's."""
    if not per_run:
        return _absent(f"no S-CORE start of this session printed its {what} line")
    bad = {r: v for r, v in per_run.items() if not isinstance(v, str)}
    if bad:
        return _absent("; ".join(f"run {r}: {v.get('absent') if isinstance(v, dict) else v}" for r, v in bad.items()))
    if len(set(per_run.values())) > 1:
        return _absent(f"the S-CORE starts of this session differ: " + "; ".join(f"{r}: {v}" for r, v in
                                                                                per_run.items()))
    return next(iter(per_run.values()))


def _guest_images(in_dir: str, guest_host: bool) -> dict:
    out = {}
    if not guest_host:
        return {k: _absent("this session ran without the guest host: no guest image was booted")
                for _, k in GUEST_ROLES}
    try:
        text = open(os.path.join(in_dir, "guest_images.txt"), encoding="utf-8").read()
    except OSError:
        text = None
    seen = {}
    for line in (text or "").splitlines():
        words = line.split()
        if len(words) >= 2 and words[0] == "GUEST_IMAGE":
            seen[words[1]] = dict(w.split("=", 1) for w in words[2:] if "=" in w)
    for role, key in GUEST_ROLES:
        v = seen.get(role)
        if text is None:
            out[key] = _absent("no guest_up step of this session ran to its end (no guest_images.txt)")
        elif v is None:
            out[key] = _absent(f"guest_up printed no GUEST_IMAGE line for {role}")
        elif v.get("fingerprint", "unread") == "unread":
            out[key] = _absent(f"the {role} guest ({v.get('serial')}) answered no ro.build.fingerprint")
        else:
            out[key] = (f"{v.get('product', 'unread')}, build {v.get('build_id', 'unread')}, fingerprint "
                        f"{v['fingerprint']}, vbmeta digest {v.get('vbmeta_digest', 'unread')}")
    return out


def session_fields(in_dir: str, score_runs: dict, kind: str = "", guest_host: bool = True) -> dict:
    """The top-level fields for session.json; parses each run's score_platform and score_gpu in place."""
    try:
        cfg = json.load(open(os.path.join(in_dir, "evidence_config.json"), encoding="utf-8"))
    except (OSError, ValueError):
        cfg = None
    why = "the session ended before its preflight wrote evidence_config.json (the configuration's read)"
    plat_runs = {k: {} for k in PLATFORM_KEYS}
    gpu_runs, gpu_names, facts = {}, [], []
    for run, d in (score_runs or {}).items():
        if not isinstance(d, dict):
            continue
        p, g = _json_line(d.get("score_platform")), _json_line(d.get("score_gpu"))
        started = "staged" in d   # score_config_check records "staged" for every S-CORE start that ran
        if p is None and g is None and not started:
            if "setting" in d:    # planned, its S-CORE start never ran (an owed run): no value, and no vote
                d["score_platform"] = _absent(f"the S-CORE start of {run} did not run")
                d["score_gpu"] = _absent(f"the S-CORE start of {run} did not run")
            continue
        d["score_platform"] = p if p is not None else _absent(f"the S-CORE start of {run} printed no SCORE_PLATFORM "
                                                               "line")
        d["score_gpu"] = g if g is not None else _absent(f"the S-CORE start of {run} printed no SCORE_GPU line")
        for k in PLATFORM_KEYS:
            plat_runs[k][run] = d["score_platform"] if "absent" in d["score_platform"] else \
                d["score_platform"].get(k, _absent(f"the SCORE_PLATFORM line of {run} has no {k}"))
        if isinstance(d["score_platform"].get("facts"), str):
            facts.append(d["score_platform"]["facts"])
        gt = _gpu_text(d["score_gpu"])
        gpu_runs[run] = gt if gt is not None else d["score_gpu"]
        if gt is not None:
            gpu_names += [x.get("name") for x in d["score_gpu"]["gpus"]]
    platform = {k: _agree(plat_runs[k], "SCORE_PLATFORM") for k in PLATFORM_KEYS}
    if facts:
        platform["facts"] = facts[0] if len(set(facts)) == 1 else sorted(set(facts))
    platform["source"] = "the SCORE_PLATFORM line of every S-CORE start: " + ", ".join(plat_runs[PLATFORM_KEYS[0]]) \
        if plat_runs[PLATFORM_KEYS[0]] else "no S-CORE start printed one"
    score_gpu = _agree(gpu_runs, "SCORE_GPU")
    out = {"score_platform": platform,
           "execution_environment": {"score_gpu": score_gpu, **_guest_images(in_dir, guest_host)}}
    if cfg is None:
        out.update(configuration_identity=_absent(why), configuration_receipt_sha256=_absent(why),
                   configuration_receipt=None, visualization_recorder_delay=_absent(why))
        return out
    out.update(configuration_identity=cfg.get("configuration_identity"),
               configuration_receipt_sha256=cfg.get("configuration_receipt_sha256"),
               configuration_receipt=cfg.get("configuration_receipt"),
               visualization_recorder_delay=recorder_delay(cfg.get("model_delay"), score_gpu, gpu_names))
    return out


def _summary(v) -> str:
    return v if isinstance(v, str) else f"absent ({(v or {}).get('absent')})"


def platform_line(p, g) -> str:
    """One line for session.log from a start's two lines (their JSON after the keyword; empty: none printed)."""
    p, g = _json_line(p), _json_line(g)
    if p is None:
        plat = "no SCORE_PLATFORM line"
    elif "absent" in p:
        plat = f"absent ({p['absent']})"
    else:
        plat = ", ".join(_summary(p.get(k)) for k in PLATFORM_KEYS[:2]) + \
            f", gateway {_summary(p.get('someip_gateway_commit'))}"
    gpu = "no SCORE_GPU line" if g is None else (_gpu_text(g) or f"absent ({g.get('absent')})")
    return f"{plat}; GPU {gpu}"


def main(argv: list[str]) -> int:
    if len(argv) == 3 and argv[0] == "line":
        print(platform_line(argv[1], argv[2]))
        return 0
    if len(argv) != 4 or argv[0] != "config":
        print(__doc__, file=sys.stderr)
        return 2
    tree, commit, out = argv[1:]
    read = git_reader(tree, commit)
    doc = {**configuration(read, commit), "model_delay": model_delay(read, commit)}
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1)
    rec = doc.get("configuration_receipt") or {}
    delay = doc["model_delay"]
    print(f"configuration {_summary(doc['configuration_identity'])}, receipt sha256 "
          f"{_summary(doc['configuration_receipt_sha256'])} ({rec.get('path')}, the model binds "
          f"{rec.get('model_bound_sha256')}: {'equal' if rec.get('equal_to_model') else 'NOT equal'}); recorder delay "
          f"of the model: {delay.get('source') if 'text' in delay else _summary(delay)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
