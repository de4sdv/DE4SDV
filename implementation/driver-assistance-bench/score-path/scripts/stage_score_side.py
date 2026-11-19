#!/usr/bin/env python3
"""Stages the S-CORE host's files under /tmp/de4sdv-da-bench for the Launch Manager (build item B13, S-CORE side).

The layout is the Launch Manager lane's contract (launch-manager/README.md "What the session must do") and the
paths of launch-manager/config/launch_manager_config.json:

  bin/          vision_pilot (the bundle's VisionPilot), actuation_adapter, gatewayd, someipd, identity_recorder,
                and, when the bundle has them, candidate_record_probe, warning_injector, ort_cuda_check
  lib/          the bundle's lib/ (ONNX Runtime, the gateway's serializer, vsomeip)
  config/       launch_manager_config.json (the full file, or the path-only one in mode path), the mw::com
                manifests of every process, the gateway's config binary and vsomeip config, adapter.json with the
                CARLA host, and de4sdv_score_interface.conf with mw_com.config naming mw_com_config_vision_pilot.json
  etc/          the serialized Launch Manager configuration of the mode, from the bundle's etc/
  vision_pilot/ the candidate's working directory: config/vision_pilot.conf, config/H.yaml,
                config/homography_C_matrix.yaml, modules/models/weights/*.onnx, assets/
  facts/        the source difference (the bundle's patches and SHA256SUMS) and upstream_revision.txt, which the
                identity recorder reads
  run/          the run directory (--run-dir of the recorder and the adapter)

vision_pilot.conf is upstream's file from the bundle with the model's settings for the S-CORE path (PSR
VisionPilotSCOREApplication): source.mode = score, engine.provider = cuda, model.precision = fp32,
visualization_on = false, rrd_on = true; speed_limit is upstream's unless --speed-limit is given (set per setting
by the world side). Every other line stays as upstream has it (L = 2.860 included, the lead's answer B7 item 4).

The camera calibration (H.yaml and homography_C_matrix.yaml) comes from --calibration-dir, which
start_score_side.sh fills from DA_CAMERA_CALIBRATION_DIR, the session's calibration of the CARLA camera. Mode full
refuses without it and never takes the bundle's files: those are upstream's calibration of another camera, and a
judged run on them would use the wrong geometry. Only mode path, which runs no candidate, falls back to the bundle's
files when no directory is given. Which calibration was staged (its source, and the sha256 of both files at the
source and in the stage) goes to <stage>/state/camera_calibration.json; the identity record hashes the staged files.

It prints a JSON summary (the files staged and their sha256) and writes it to <stage>/state/staging.json.
Exit status: 0 staged; 2 usage; 3 a required input is missing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[2]
DEFAULT_STAGE = "/tmp/de4sdv-da-bench"
MODES = ("full", "path")

# The candidate's settings on the S-CORE path (PSR VisionPilotSCOREApplication).
CONF_OVERRIDES = {
    "source.mode": "score",
    "engine.provider": "cuda",
    "model.precision": "fp32",
    "visualization_on": "false",
    "rrd_on": "true",
}

# bundle name -> staged name; the Launch Manager configuration names the staged ones.
REQUIRED_BINARIES = {"VisionPilot": "vision_pilot", "actuation_adapter": "actuation_adapter",
                     "gatewayd": "gatewayd", "someipd": "someipd", "identity_recorder": "identity_recorder"}
OPTIONAL_BINARIES = {"candidate_record_probe": "candidate_record_probe", "warning_injector": "warning_injector",
                     "ort_cuda_check": "ort_cuda_check", "launch_manager": "launch_manager"}

MANIFESTS = [
    "score-path/config/mw_com_config_vision_pilot.json",
    "score-path/config/mw_com_config_gatewayd_warning.json",
    "score-path/config/mw_com_config_someipd_warning.json",
    "score-path/config/vsomeip_someipd_warning.json",
    "actuation-adapter/mw_com_config_actuation_adapter.json",
    "identity-recorder/mw_com_config_identity_recorder.json",
    "identity-recorder/mw_com_config_candidate_record_probe.json",
    "ivi-warning/injector/mw_com_config_warning_injector.json",
]
LAUNCH_CONFIGS = {"full": "launch-manager/config/launch_manager_config.json",
                  "path": "score-path/config/launch_manager_config_path_only.json"}
SERIALIZED = {"full": "launch_manager_config.bin", "path": "launch_manager_config_path_only.bin"}


class Missing(Exception):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def need(path: Path, what: str) -> Path:
    if not path.is_file():
        raise Missing(f"{what}: {path} is missing")
    return path


def override_conf(text: str, overrides: dict[str, str]) -> str:
    """Sets each key of overrides in an upstream-style .conf, keeping the comments and the order; appends a key
    that is not there."""
    lines = text.splitlines()
    done = set()
    pattern = re.compile(r"^(\s*)([A-Za-z0-9_.]+)(\s*=\s*)([^#;]*?)(\s*;?)(\s*#.*)?$")
    for i, line in enumerate(lines):
        match = pattern.match(line)
        if match and match.group(2) in overrides:
            key = match.group(2)
            lines[i] = (match.group(1) + key + match.group(3) + overrides[key] + (match.group(5) or "") +
                        (match.group(6) or ""))
            done.add(key)
    missing = [k for k in overrides if k not in done]
    if missing:
        lines.append("")
        lines.append("# DE4SDV S-CORE path (score-path/scripts/stage_score_side.py)")
        lines += [f"{k} = {overrides[k]}" for k in missing]
    return "\n".join(lines) + "\n"


CALIBRATION_FILES = ("H.yaml", "homography_C_matrix.yaml")


def stage_calibration(args: argparse.Namespace, root: Path, put) -> dict:
    """Stages the camera calibration into the candidate's config/ and records which one it was."""
    given = args.calibration_dir
    if given is not None:
        missing = [n for n in CALIBRATION_FILES if not (given / n).is_file()]
        if missing:
            raise Missing(f"camera calibration: DA_CAMERA_CALIBRATION_DIR {given} lacks {' and '.join(missing)}")
        source, kind = given, "DA_CAMERA_CALIBRATION_DIR"
    elif args.mode == "full":
        raise Missing("camera calibration: mode full needs DA_CAMERA_CALIBRATION_DIR (--calibration-dir) with "
                      "H.yaml and homography_C_matrix.yaml; it never falls back to the bundle's upstream files")
    else:
        source, kind = args.bundle / "config" / "visionpilot", "bundle fallback (mode path, no candidate runs)"
        missing = [n for n in CALIBRATION_FILES if not (source / n).is_file()]
        if missing:
            raise Missing(f"camera calibration: no DA_CAMERA_CALIBRATION_DIR, and the bundle lacks "
                          f"{' and '.join(missing)}")
    files = {}
    for name in CALIBRATION_FILES:
        staged = root / "vision_pilot" / "config" / name
        put(source / name, staged)
        files[name] = {"source_path": str((source / name).resolve()), "source_sha256": sha256(source / name),
                       "staged_path": str(staged), "staged_sha256": sha256(staged)}
    record = {"mode": args.mode, "source": kind, "dir": str(source.resolve()), "files": files}
    (root / "state" / "camera_calibration.json").write_text(json.dumps(record, indent=1) + "\n")
    return record


def stage(args: argparse.Namespace) -> dict:
    bundle, root, bench = args.bundle, args.stage, args.bench
    if root.name != "de4sdv-da-bench" and not args.allow_any_stage:
        raise SystemExit(f"refusing to stage into {root}: the Launch Manager configuration names /tmp/de4sdv-da-bench")
    if root.exists():
        shutil.rmtree(root)
    for sub in ("bin", "lib", "config", "etc", "facts", "run", "state", "vision_pilot/config",
                "vision_pilot/modules/models/weights"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    staged: dict[str, str] = {}

    def put(src: Path, dst: Path, mode: int | None = None) -> None:
        shutil.copy2(src, dst)
        if mode is not None:
            dst.chmod(mode)
        staged[str(dst)] = sha256(dst)

    for name, target in REQUIRED_BINARIES.items():
        put(need(bundle / "bin" / name, f"binary {name}"), root / "bin" / target, 0o755)
    for name, target in OPTIONAL_BINARIES.items():
        if (bundle / "bin" / name).is_file():
            put(bundle / "bin" / name, root / "bin" / target, 0o755)
    libs = sorted(p for p in (bundle / "lib").glob("*") if p.is_file())
    if not libs:
        raise Missing(f"no library in {bundle / 'lib'}")
    for lib in libs:
        put(lib, root / "lib" / lib.name)

    # configuration
    launch_text = need(bench / LAUNCH_CONFIGS[args.mode], "Launch Manager configuration").read_text(encoding="utf-8")
    if str(root) != DEFAULT_STAGE:  # tests only (--allow-any-stage): the file's paths follow the stage
        launch_text = launch_text.replace(DEFAULT_STAGE, str(root))
    (root / "config" / "launch_manager_config.json").write_text(launch_text, encoding="utf-8")
    staged[str(root / "config" / "launch_manager_config.json")] = sha256(root / "config" / "launch_manager_config.json")
    for rel in MANIFESTS:
        put(need(bench / rel, "manifest"), root / "config" / Path(rel).name)
    put(need(bundle / "config" / "gateway" / "someip_gateway_config_warning.bin", "gateway config binary"),
        root / "config" / "someip_gateway_config_warning.bin")
    adapter = json.loads(need(bench / "actuation-adapter" / "config" / "adapter.json", "adapter.json").read_text())
    if args.carla_host != "none":
        adapter["carla_host"] = args.carla_host
    (root / "config" / "adapter.json").write_text(json.dumps(adapter, indent=2) + "\n")
    staged[str(root / "config" / "adapter.json")] = sha256(root / "config" / "adapter.json")
    interface = "\n".join([
        "# DE4SDV S-CORE interface settings (score-path/scripts/stage_score_side.py)",
        f"mw_com.config = {root / 'config' / 'mw_com_config_vision_pilot.json'}",
        f"carla.host = {args.carla_host}",
        "carla.port = 2000",
        "carla.hero_role = hero",
        "carla.camera_role = front",
        f"log.path = {root / 'run' / 'score' / 'score_interface.jsonl'}",
    ]) + "\n"
    (root / "config" / "de4sdv_score_interface.conf").write_text(interface)
    staged[str(root / "config" / "de4sdv_score_interface.conf")] = sha256(root / "config" / "de4sdv_score_interface.conf")
    serialized = bundle / "etc" / SERIALIZED[args.mode]
    if serialized.is_file():
        put(serialized, root / "etc" / "launch_manager_config.bin")
    elif args.require_serialized:
        raise Missing(f"serialized Launch Manager configuration: {serialized} is missing")

    # the candidate's working directory
    upstream_conf = need(bundle / "config" / "visionpilot" / "vision_pilot.conf", "upstream vision_pilot.conf")
    overrides = dict(CONF_OVERRIDES)
    if args.speed_limit is not None:
        overrides["speed_limit"] = args.speed_limit
    conf = root / "vision_pilot" / "config" / "vision_pilot.conf"
    conf.write_text(override_conf(upstream_conf.read_text(encoding="utf-8"), overrides))
    staged[str(conf)] = sha256(conf)
    calibration_record = stage_calibration(args, root, put)
    weights = sorted((bundle / "share" / "visionpilot" / "modules" / "models" / "weights").glob("*.onnx"))
    if not weights:
        raise Missing("no network (*.onnx) in the bundle")
    for w in weights:
        put(w, root / "vision_pilot" / "modules" / "models" / "weights" / w.name)
    assets = bundle / "share" / "visionpilot" / "assets"
    if assets.is_dir():
        shutil.copytree(assets, root / "vision_pilot" / "assets")

    # the facts the identity recorder reads
    diffs = sorted((bundle / "facts").glob("*.diff"))
    if not diffs:
        raise Missing("no source difference (*.diff) in the bundle's facts/")
    for d in diffs:
        put(d, root / "facts" / d.name)
    if (bundle / "facts" / "SHA256SUMS").is_file():
        put(bundle / "facts" / "SHA256SUMS", root / "facts" / "SHA256SUMS")
    revision = args.upstream_revision
    if not re.fullmatch(r"[0-9a-f]{40}", revision or ""):
        raise Missing(f"upstream revision: '{revision}' is not 40 lowercase hex digits")
    (root / "facts" / "upstream_revision.txt").write_text(revision + "\n")
    summary = {"stage": str(root), "mode": args.mode, "carla_host": args.carla_host, "bundle": str(bundle),
               "camera_calibration": calibration_record, "upstream_revision": revision,
               "serialized_launch_config": (root / "etc" / "launch_manager_config.bin").is_file(),
               "files": dict(sorted(staged.items()))}
    (root / "state" / "staging.json").write_text(json.dumps(summary, indent=1) + "\n")
    return summary


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--stage", type=Path, default=Path("/tmp/de4sdv-da-bench"))
    parser.add_argument("--bench", type=Path, default=BENCH)
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--carla-host", required=True, help="the simulator host, or none (mode path)")
    parser.add_argument("--calibration-dir", type=Path,
                        help="the camera calibration (DA_CAMERA_CALIBRATION_DIR); required in mode full")
    parser.add_argument("--speed-limit")
    parser.add_argument("--upstream-revision", required=True)
    parser.add_argument("--require-serialized", action="store_true",
                        help="fail when the bundle has no serialized Launch Manager configuration of the mode")
    parser.add_argument("--allow-any-stage", action="store_true", help="tests only: stage outside /tmp")
    args = parser.parse_args(argv)
    if args.mode == "full" and args.carla_host == "none":
        parser.error("mode full needs a CARLA host")
    try:
        summary = stage(args)
    except Missing as error:
        print(f"stage_score_side: {error}", file=sys.stderr)
        return 3
    print(json.dumps({k: v for k, v in summary.items() if k != "files"}, indent=1))
    print(f"staged {len(summary['files'])} files")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
