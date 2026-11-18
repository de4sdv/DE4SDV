# Incremental guest build (INC-DRIVING-002, B12)

Status: draft, not yet validated. The script has run only against a synthetic tree on the
development host.

## The problem

The AAOS SDV guests were rebuilt and archived on 2026-11-17 (5-7 h of builds). The phase 10 probes
need two additions on top of them: the SDV Core side of the warning request
([`../ivi-warning/`](../ivi-warning/), B11) and the warning presentation on the IVI VM
([`../ivi-warning-app/`](../ivi-warning-app/), B10). A rebuild from scratch would cost hours, and a
build under another variant than a product's last one deletes that product's images. This
script adds both incrementally, checks the result on booted guests and stops them again.

## What it does

[`build_guests_incremental.sh`](build_guests_incremental.sh) `preflight | detect | core | ivi |
boot | install | verify | stop | all`. Each step logs to `~/aaos-build/logs/b12-<step>.log`, adds
its result to `~/aaos-build/identity/b12-summary.txt` and stops at the first failure.

| Step | What | Builds |
|---|---|---|
| `preflight` | the tree, both products' last variants (core `eng`, IVI `userdebug`), the kept images and the recipe's recorded IVI image digests, disk, no build running, the staging checks | nothing |
| `core` | detects B11 on the SDV Core side (below); only when missing: `stage_sdv_core_interop.sh validate` (stage and the catalog build G1b), then a plain incremental `m` for `sdv_core_cf-cp2a-eng` | only when needed |
| `ivi` | stages and builds the app as a module under `sdv_ivi_cf-cp2a-userdebug`, runs its JVM tests with the tree's JDK, and fails if the IVI images changed | the app module |
| `boot` | `launch_two_vms.sh up` in the SSH foreground. Existing groups need `GUESTS=fresh` (remove the groups and create them on the current images) or `GUESTS=reuse` (both already booted) | nothing |
| `install` | the app's ACLs and APK on the IVI VM, reboot, PackageManager check, identity | nothing |
| `verify` | the SDV Core VM's stack config carries 0x4dee, 0x4df0 and 0x4df1; the app starts, its `initComms` succeeds through the gateway; the SELinux mode of both guests is recorded | nothing |
| `stop` | `cvd --group_name=<g> stop` for both groups, then no `crosvm` may be left | nothing |

`all` runs them in this order; on a failure after `boot` it stops the guests
(`KEEP_GUESTS_ON_FAILURE=1` keeps them up for a diagnosis).

### Detecting B11 on the SDV Core side

Another operator may already have staged B11 and rebuilt the core image. The script then builds
nothing. It detects:

- **the tree**, when all hold: the stack config that `stage_sdv_core_interop.sh render` makes from
  `../ivi-warning/interop/vsomeip_config.json` with `SCORE_SOMEIP_PEER` (192.168.98.1) is
  byte-equal (`cmp`) to the tree's `some_ip/vsomeip_stack/vsomeip_config.json`; the catalog's
  `de4sdv_driver_assistance/` proto and mapping are byte-equal to B11's; the broker ACL names the
  unit `de4sdv-driving-warning-request` and `broker.vsidl` names the message;
- **the image**, when the tree check holds, the stack config installed in
  `out/target/product/sdv_core_cf/vendor/etc/someip/vsomeip_config.json` is byte-equal to the same
  render, and `super.img` and `vbmeta.img` are newer than that installed file.

`detect` prints which of the three states the host is in and builds nothing.

## Rules it keeps

- Builds only with the recorded variants; the refusal comes before `lunch`. No `installclean`, no
  clean, no deletion in the AOSP tree, its `out/` or the archive. The only directory it replaces is
  the app's staging directory `samples/de4sdv_collision_warning/`.
- The core image is built with a plain `m`, never with the INC-DRIVING-001 script's `build`, which
  re-stages its own stack config without 0x4df1.
- It changes the SELinux mode only with `IVI_PERMISSIVE=1` and records the mode in every case. It
  starts or stops no VM and calls no `gcloud`.

## On the guest host

The script needs this branch's `implementation/driver-assistance-bench/` and the bench scripts of
the 2026-11-17 rebuild (`DE4SDV_ROOT`, default `~/de4sdv-e8fa324a`, for `launch_two_vms.sh`):

```bash
# on the lead host: the exact branch head, as an archive with its digest
git archive --format=tar.gz -o da-bench.tar.gz <head> implementation/driver-assistance-bench
sha256sum da-bench.tar.gz
# on de4sdv-aaos-build, after the upload: check the digest, then
mkdir -p ~/da-b12 && tar -xzf da-bench.tar.gz -C ~/da-b12
cd ~/da-b12/implementation/driver-assistance-bench/guest-build
./build_guests_incremental.sh preflight
./build_guests_incremental.sh detect
GUESTS=fresh ./build_guests_incremental.sh all   # in the SSH foreground, never under systemd-run
```

Expected duration with B11 already in the core image: about 25-40 min (the first build of a new
module regenerates the IVI product's build graph, about 10-20 min; the module itself a few
minutes; boot 5-10 min; install with up to two IVI reboots about 5 min). With the core still to
build, add about 10 min for the catalog build and 20-45 min for the incremental core image.

## Tests

`tests/test_guest_build_script.py` runs in the `driver-assistance-bench (INC-DRIVING-002)` suite:
`bash -n`, no deletion of the kept tree, recorded variants only, groups removed only under
`GUESTS=fresh`, and `detect`, `core` and `ivi` against a synthetic tree whose `lunch` and `m` only
record their arguments.

## What the local tests cannot show

That the real tree's paths are the ones the detection reads (above all the installed
stack config), that the module build leaves the real IVI images untouched, and every step from `boot`
on. The phase 10 probe of the guests starts from this script's summary.
