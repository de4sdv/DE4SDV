# Windows x86_64 / WSL2 host runbook for the AAOS SDV reference proof

## Target arrangement

Use the Windows machine as the x86_64 Android build and runtime host:

```text
Windows x86_64
  └─ WSL2 Ubuntu 22.04
       ├─ AOSP source and build output on the Linux ext4 filesystem
       ├─ pinned AAOS SDV manifest
       ├─ VSIDL compiler and generated reference binding
       └─ AAOS SDV emulator/CF runtime or connected target
```

Do not build AOSP from `/mnt/c`. WSL's Linux filesystem is materially faster and avoids Windows path/permission problems.

## Preflight

The preflight script is stored in the DE4SDV repository. It must first be cloned or checked out on the Windows machine; it is not installed there automatically.

For a fresh Windows checkout, run from PowerShell:

```powershell
git clone -b feat/mw-008-physical-software-realization https://github.com/de4sdv/DE4SDV.git
cd DE4SDV
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\windows\check_aaos_sdv_host.ps1
```

Because the AOSP build will run inside WSL2, also run the Linux-side check from the WSL terminal:

```bash
cd /path/to/DE4SDV
bash scripts/windows/check_aaos_sdv_wsl.sh
```

The WSL-side output is the more important result for the AOSP build.

For an existing checkout:

```powershell
git fetch origin
git checkout feat/mw-008-physical-software-realization
git pull
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\windows\check_aaos_sdv_host.ps1
```

The script performs read-only checks. Record the output in the integration evidence directory. Do not include usernames, tokens, private hostnames, or connection strings.

Minimum capacity for the pinned AAOS/Cuttlefish proof profile
(corresponding to `AOSPAAOSBuildResourceEnvelope` in the execution-environment
model):

```text
x86_64 CPU
64 GiB RAM
400 GiB free Linux-backed storage
WSL2 Ubuntu 22.04
virtualization enabled in firmware
```

## WSL2 setup

Install/update WSL from an elevated PowerShell if it is not already available:

```powershell
wsl --install -d Ubuntu-22.04
wsl --update
```

Inside Ubuntu, keep all AOSP files under the Linux home directory:

```bash
mkdir -p ~/aosp ~/de4sdv-evidence
cd ~/aosp
```

Install the Android build prerequisites using the current AOSP build documentation. Do not copy credentials into this repository or into evidence.

## AOSP source target

The DE4SDV reference uses the public SDV target previously identified:

```text
manifest repository: https://android.googlesource.com/platform/manifest
manifest branch: android-latest-release
manifest revision: ad156f32caaa06dae91c02d443f6a8fe210eaa54
build target: sdv_core_cf-trunk_staging-userdebug
```

Use the exact manifest revision recorded in the DE4SDV model and retain the resulting manifest snapshot as evidence. Do not silently substitute a moving branch tip.

The source checkout and build are intentionally not automated by this document because the required disk/time cost must be confirmed by the preflight first.

## Reference contract integration

Copy or checkout the DE4SDV reference contract into the AOSP catalog integration area only as a build input:

```text
implementation/aaos-sdv-reference-interop-bench/contract/vehicle_speed.proto
implementation/aaos-sdv-reference-interop-bench/contract/vehicle_speed.vsidl
```

The contract is DE4SDV-owned and must remain labeled as a reference contract:

```text
not an OEM vehicle-service contract
not production vehicle compatibility
```

Build `vsidlc` through the AOSP build system, then generate the service-bundle-specific API from the exact `.proto` and `.vsidl` files. Retain:

- generated source paths;
- generator revision;
- catalog inputs;
- generated API identity;
- build output hashes.

## Runtime proof gates

Do not call the result AAOS ↔ Autoware runtime interoperability until all gates pass:

1. Reference provider service is built and installed.
2. Service bundle is registered with the AAOS SDV middleware.
3. Service discovery resolves the reference service identity.
4. The adapter receives a real AAOS publication.
5. The adapter publishes the exact ROS 2 topic/type/field.
6. An independent observer verifies both sides for known speed values.
7. Fault tests cover stale, invalid, provider loss, and discovery failure.
8. A reverse lifecycle/status path passes if bidirectional communication is claimed.

The local rehearsal is useful preparation, but it is not runtime evidence. The current bench reports AAOS and ROS 2 runtime interoperability as `not_proven` until these gates execute on the Windows-hosted Linux target.
