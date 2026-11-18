#!/usr/bin/env python3
"""Render the SDV Core stack config with the S-CORE peer, keeping the services already staged.

    render_stack_config.py --template interop/vsomeip_config.json --peer <address> --out <file>
                           [--current <the tree's vsomeip_config.json>]

- Replaces __SCORE_SOMEIP_PEER__ with the peer and merges the acceptances of one address into
  one entry (as the closed-loop driving bench's staging does).
- Refuses (exit 1, nothing written) when the result lacks the warning service or a kept service
  of ../interfaces/service_ids.json (0x4dee, 0x4df0), or when --current is given and one of its
  services, secure services or acceptance ranges would change or disappear.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import pathlib
import sys

PLACEHOLDER = "__SCORE_SOMEIP_PEER__"
IDS = pathlib.Path(__file__).resolve().parent.parent.parent / "interfaces" / "service_ids.json"


class RenderError(ValueError):
    pass


def render(template_text: str, peer: str, current: dict | None) -> dict:
    ipaddress.IPv4Address(peer)
    ids = json.loads(IDS.read_text(encoding="utf-8"))["icd"]
    required = [ids["someip_warning_request"]["service_id"]] + [k["service_id"] for k in ids["someip_kept"]]
    config = json.loads(template_text.replace(PLACEHOLDER, peer))
    merged: dict[str, dict] = {}
    for acceptance in config.get("acceptances", []):
        entry = merged.setdefault(acceptance["address"], {"address": acceptance["address"], "reliable": []})
        entry["reliable"] += [r for r in acceptance.get("reliable", []) if r not in entry["reliable"]]
    config["acceptances"] = list(merged.values())

    services = {s["service"]: s for s in config["services"]}
    missing = [s for s in required if s not in services]
    if missing:
        raise RenderError(f"the rendered stack config lacks {', '.join(missing)}; every one of {required} must stay")
    secure = {(s["service"], s["instance"]) for s in config.get("secure-services", [])}
    for service in required:
        if (service, services[service]["instance"]) not in secure:
            raise RenderError(f"{service} is not a secure service in the rendered stack config")
    if PLACEHOLDER in json.dumps(config):
        raise RenderError("the peer placeholder is left")

    if current is not None:
        for service in current.get("services", []):
            mine = services.get(service["service"])
            if mine != service:
                raise RenderError(f"{service['service']}: the tree's entry would change or disappear:"
                                  f" {json.dumps(service)} -> {json.dumps(mine)}")
        for entry in current.get("secure-services", []):
            if entry not in config.get("secure-services", []):
                raise RenderError(f"{entry['service']}: the tree's secure-service entry would disappear")
        accepted = {a["address"]: a["reliable"] for a in config["acceptances"]}
        for acceptance in current.get("acceptances", []):
            for reliable in acceptance.get("reliable", []):
                if reliable not in accepted.get(acceptance["address"], []):
                    raise RenderError(f"acceptance {acceptance['address']} {reliable} of the tree would disappear")
    return config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="render the SDV Core stack config")
    parser.add_argument("--template", type=pathlib.Path, required=True)
    parser.add_argument("--peer", required=True, help="the S-CORE host's address on the VXLAN segment")
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--current", type=pathlib.Path, help="the stack config the tree carries now")
    args = parser.parse_args(argv)
    current = json.loads(args.current.read_text(encoding="utf-8")) if args.current else None
    try:
        config = render(args.template.read_text(encoding="utf-8"), args.peer, current)
    except (RenderError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    args.out.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    services = sorted(s["service"] for s in config["services"])
    print(f"stack config rendered: services {services}, peer {args.peer}"
          f"{', the tree' + chr(39) + 's services kept' if current is not None else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
