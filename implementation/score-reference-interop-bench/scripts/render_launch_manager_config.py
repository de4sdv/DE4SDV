#!/usr/bin/env python3
"""Renders the Launch Manager configuration of the bench for one host.

The Launch Manager of lifecycle v0.6.1 passes a component only the
environment variables of its configuration, as literal values (no shell
expansion). The committed configuration holds the values of the bench: the
library directory of the S-CORE daemons, the vsomeip configuration of
someipd, and the ROS 2 environment of the adapter and the health proxy node.
This renderer adds what depends on the host:

- the ROS 2 setup: the variables that the host's ROS 2 setup script sets
  (library and package paths, PATH, ROS_DISTRO and the like), read from a
  clean shell that sources it, for each ROS 2 component;
- the sandbox user and group (the bench user).

It refuses a value that holds "$" (the Launch Manager expands nothing), a
component with more than 100 variables (the limit of the Launch Manager),
and ROS_LOCALHOST_ONLY, which the ROS 2 environment of the bench leaves
unset. The Launch Manager's own configuration rule then checks the rendered
file against its schema and serializes it.

Usage: render_launch_manager_config.py <config.json> <rendered.json> --uid U --gid G
           [--ros-setup /opt/ros/humble/setup.bash] [--ros-components adapter,health_proxy]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

MAX_VARIABLES = 100
SHELL_VARIABLES = {"_", "PWD", "OLDPWD", "SHLVL", "HOME"}
NEVER_SET = {"ROS_LOCALHOST_ONLY"}


def _clean_shell_environment(script: str, home: str) -> dict[str, str]:
    output = subprocess.run(["env", "-i", f"HOME={home}", "bash", "-c", script], capture_output=True, check=True)
    return dict(item.split("=", 1) for item in output.stdout.decode().split("\0") if "=" in item)


def ros_setup_variables(setup: Path, home: str) -> dict[str, str]:
    """The variables that sourcing setup changes in a clean shell."""
    before = _clean_shell_environment("env -0", home)
    after = _clean_shell_environment(f'set +u; source "{setup}" >/dev/null && env -0', home)
    return {
        name: value
        for name, value in after.items()
        if name not in SHELL_VARIABLES and name not in NEVER_SET and before.get(name) != value
    }


def render(config: dict, setup_variables: dict[str, str], ros_components: list[str], uid: int, gid: int) -> dict:
    rendered = json.loads(json.dumps(config))
    rendered["defaults"]["deployment_config"]["sandbox"] = {
        "uid": uid, "gid": gid, "supplementary_group_ids": [],
        "scheduling_policy": "SCHED_OTHER", "scheduling_priority": 0,
    }
    components = rendered["components"]
    for name in ros_components:
        if name not in components:
            raise SystemExit(f"no component {name} in the configuration")
        deployment = components[name].setdefault("deployment_config", {})
        variables = deployment.setdefault("environmental_variables", {})
        # The committed values of the bench win over the setup script.
        deployment["environmental_variables"] = {**setup_variables, **variables}
    for name, component in components.items():
        variables = (component.get("deployment_config") or {}).get("environmental_variables", {})
        if len(variables) > MAX_VARIABLES:
            raise SystemExit(f"{name}: {len(variables)} environment variables, more than {MAX_VARIABLES}")
        for key, value in variables.items():
            if "$" in value:
                raise SystemExit(f"{name}: {key} holds '$'; the Launch Manager passes literal values only")
            if key in NEVER_SET:
                raise SystemExit(f"{name}: {key} must stay unset")
    return rendered


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("config")
    parser.add_argument("rendered")
    parser.add_argument("--uid", type=int, required=True)
    parser.add_argument("--gid", type=int, required=True)
    parser.add_argument("--ros-setup", default="/opt/ros/humble/setup.bash")
    parser.add_argument("--ros-components", default="adapter,health_proxy")
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    home = config["defaults"]["deployment_config"]["working_dir"]
    setup_variables = ros_setup_variables(Path(args.ros_setup), home)
    if not setup_variables:
        raise SystemExit(f"{args.ros_setup} set no variable")
    rendered = render(config, setup_variables, [name for name in args.ros_components.split(",") if name],
                      args.uid, args.gid)
    Path(args.rendered).write_text(json.dumps(rendered, indent=4) + "\n", encoding="utf-8")
    print(json.dumps({"ros_setup": args.ros_setup, "ros_setup_variables": setup_variables}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
