# Eclipse SysON local pilot

This directory contains the local SysON stack used to evaluate SysON in the
DE4SDV SysML v2 engineering workflow.

SysON is the preferred GUI pilot for DE4SDV because it is open-source,
web-based, and aligned with collaborative graphical SysML v2 modeling. It is
still under active development, so DE4SDV treats it as a pilot tool, not as a
production dependency.

## Start

On x86_64 hosts:

```bash
docker compose -f tools/syson/compose.yaml up -d
```

On ARM/aarch64 hosts:

```bash
DOCKER_DEFAULT_PLATFORM=linux/amd64 \
  docker compose -f tools/syson/compose.yaml up -d
```

Open:

```text
http://localhost:8080
```

## Stop

```bash
docker compose -f tools/syson/compose.yaml down
```

To delete pilot state:

```bash
docker compose -f tools/syson/compose.yaml down -v
```

## Image/version

The compose file defaults to:

```text
eclipsesyson/syson:v2026.5.0
```

Override with:

```bash
SYSON_IMAGE_TAG=eclipsesyson/syson:<version> \
  docker compose -f tools/syson/compose.yaml up -d
```

## DE4SDV operating rule

Use SysON for GUI editing and view authoring experiments. Keep GitHub as the
reviewed baseline:

```text
SysON GUI edit/export
  -> generated snapshot/view artifacts
  -> GitHub draft PR
  -> review/validation
  -> merge
```

Do not let SysON or automation push generated artifacts directly to `main`.

## Known pilot limits

- SysON's standard SysML v2 REST API support is not fully available yet.
- SysON project/model JSON is SysON-specific, not OMG SysML v2 standard JSON.
- SysON supports textual `.sysml` import/export, but upstream docs explicitly
  warn that some concepts are still under development.
- Diagram export is available through the UI as SVG, and PNG support exists in
  current release notes, but scripted deterministic export still needs a spike.
