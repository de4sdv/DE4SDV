#!/usr/bin/env python3
"""Checks that each component of the Launch Manager configuration can load.

The Launch Manager passes a component only the environment of its
configuration. This check renders the configuration for this host
(render_launch_manager_config.py, with the given ROS 2 setup script) and runs
``ldd`` on each component's executable in exactly that environment
(``env -i``), from the bin_dir of the configuration. It fails when ldd fails
or names a library as "not found". A component whose executable is not in
bin_dir yet (the health proxy node) is listed, not failed.

Unpack the runtime bundle into the working directory of the configuration
first (/tmp/de4sdv-score-bench), so the library and configuration paths of
the configuration are real.

Usage: check_launch_manager_environment.py <config.json> [--ros-setup /opt/ros/humble/setup.bash]
           [--require adapter,someipd,gatewayd] --out <report>
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import render_launch_manager_config as renderer  # noqa: E402


def ldd_problems(output: str) -> list[str]:
    """The lines of ldd output that name a library ldd could not find."""
    return [line.strip() for line in output.splitlines() if "not found" in line]


def component_environment(config: dict, name: str) -> dict[str, str]:
    return dict((config["components"][name].get("deployment_config") or {}).get("environmental_variables", {}))


def check(config: dict, required: tuple[str, ...] = ()) -> tuple[list[dict], bool]:
    """ldd of each executable in its rendered environment; a required component must have one in bin_dir."""
    bin_dir = Path(config["defaults"]["deployment_config"]["bin_dir"])
    results = []
    passed = True
    for name, component in config["components"].items():
        binary = bin_dir / component["component_properties"]["binary_name"]
        environment = component_environment(config, name)
        if not binary.is_file():
            missing = name in required
            passed = passed and not missing
            results.append({"component": name, "binary": str(binary),
                            "result": "missing from bin_dir" if missing else "not in bin_dir yet"})
            continue
        argv = ["/usr/bin/env", "-i", *[f"{key}={value}" for key, value in environment.items()], "/usr/bin/ldd",
                str(binary)]
        completed = subprocess.run(argv, capture_output=True, text=True, check=False)
        problems = ldd_problems(completed.stdout + completed.stderr)
        ok = completed.returncode == 0 and not problems
        passed = passed and ok
        results.append({"component": name, "binary": str(binary), "variables": len(environment),
                        "returncode": completed.returncode, "not_found": problems,
                        "result": "loads" if ok else "does not load", "ldd": completed.stdout + completed.stderr})
    return results, passed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("config")
    parser.add_argument("--ros-setup", default="/opt/ros/humble/setup.bash")
    parser.add_argument("--ros-components", default="adapter,health_proxy")
    parser.add_argument("--require", default="", help="components whose executable must be in bin_dir")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    home = config["defaults"]["deployment_config"]["working_dir"]
    setup_variables = renderer.ros_setup_variables(Path(args.ros_setup), home)
    rendered = renderer.render(config, setup_variables, [name for name in args.ros_components.split(",") if name],
                               os.getuid(), os.getgid())
    results, passed = check(rendered, tuple(name for name in args.require.split(",") if name))
    lines = [f"Launch Manager environment, rendered with {args.ros_setup}: "
             f"{'every built component loads' if passed else 'a component does not load'}"]
    for result in results:
        lines.append(f"- {result['component']}: {result['result']} ({result['binary']}"
                     + (f", {result['variables']} variables" if "variables" in result else "") + ")")
        for problem in result.get("not_found", []):
            lines.append(f"  - {problem}")
    report = "\n".join(lines) + "\n"
    Path(args.out).write_text(report + "\n" + json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(report, end="")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
