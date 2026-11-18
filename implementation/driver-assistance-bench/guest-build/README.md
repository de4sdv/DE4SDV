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
boot | install | verify | stop | all`. Each step logs to `~/aaos-build/b12-<date>/logs/b12-<step>.log`,
adds its result to `~/aaos-build/b12-<date>/identity/b12-summary.txt` and stops at the first
failure. B12 writes nothing into the 2026-11-17 kit's `~/aaos-build/identity/` or `logs/`;
[`b12_launch.sh`](b12_launch.sh) gives every run its own `~/aaos-build/b12-<date>-<sha>[-r<n>]/`.

| Step | What | Builds |
|---|---|---|
| `preflight` | the tree, both products' last variants (core `eng`, IVI `userdebug`), the kept images against B12's own image records (below), disk, no build running, the staging checks | nothing |
| `core` | detects B11 on the SDV Core side (below); only when missing: `stage_sdv_core_interop.sh validate` (stage and the catalog build G1b), then a plain incremental `m` for `sdv_core_cf-cp2a-eng`. Either way it writes the core image hashes into the identity and says whether they equal the record | only when needed |
| `ivi` | stages and builds the app as a module under `sdv_ivi_cf-cp2a-userdebug`, runs its JVM tests with the tree's JDK, and fails if the IVI images changed (stat and the record) | the app module |
| `boot` | `launch_two_vms.sh up`. Existing groups need `GUESTS=fresh` (remove the groups and create them on the current images) or `GUESTS=reuse` (both already booted). It refuses to run inside a systemd unit, whose cgroup takes the guests down | nothing |
| `install` | the app's ACLs and APK on the IVI VM, reboot, PackageManager check; every push checked, the guest APK's sha256 must equal the host's; the broker object policy merged and logged (the lead's decision 3 for B10 and B12) | nothing |
| `verify` | the SDV Core VM's stack config carries 0x4dee, 0x4df0 and 0x4df1 and its broker APEX names the unit; the app starts and its `initComms` succeeds through the gateway; `getenforce` of both guests is recorded | nothing |
| `stop` | `cvd --group_name=<g> stop` for both groups, then no `crosvm` may be left | nothing |

`all` runs them in this order. Once `boot` has begun, every exit that is not a pass stops the
guests: a failed step, and also SIGHUP, SIGINT and SIGTERM (exit 129, 130, 143). A signal is
handled at once: the running step and its children are ended first. `KEEP_GUESTS_ON_FAILURE=1`
keeps the guests up for a diagnosis and says so. Every adb call is bounded (`ADB_TIMEOUT_S`, 120 s),
so a wedged adb fails the step instead of hanging with the guests up.

### B12's image records

[`image-records/`](image-records/) holds the images B12 expects, as `sha256sum` lists relative to the
product directory. `preflight` checks both and fails when a record is missing or an image differs.
B12 never reads the kit's `~/aaos-build/state/images-*.sha256`: those are stale since the first boot
of 2026-11-17, when `assemble_cvd` rewrote the IVI `super.img` in place through the `artifacts/0`
symlink, and since the core build of 2026-11-18.

- `sdv_ivi_cf.sha256`: the IVI `super.img` as it is since that first boot, `91a4d73f…` (equal to the
  2026-11-17 archive's copy and to both boots of 2026-11-18), and `vbmeta`, `boot`, `init_boot` and
  `vendor_boot` of the 2026-11-16 record, which still matched on 2026-11-18.
- `sdv_core_cf.sha256`: the 27 top-level core images after the operator's B11 build of 2026-11-18
  (`guest-prep-20261118/identity/core-images-after.sha256`; `super.img` `434b485f…`, `vbmeta.img`
  `535d7aba…`).

If `core` ever rebuilds the core image, the core record no longer applies; the step says so and names
the identity file to use as `CORE_IMAGE_RECORD` for the next run.

### Detecting B11 on the SDV Core side

Another operator may already have staged B11 and rebuilt the core image (on 2026-11-18 one did). The
script then builds nothing. It detects:

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
  the app's staging directory `samples/de4sdv_collision_warning/`. Incremental builds only.
- The core image is built with a plain `m`, never with the INC-DRIVING-001 script's `build`, which
  re-stages its own stack config without 0x4df1, and never while guests run.
- SELinux: the IVI stays Enforcing by default. When `verify` finds that the app's Gateway lookup
  (`initComms`) failed under Enforcing, the run stops (and stops the guests) and prints the exact
  rerun command with `IVI_PERMISSIVE=1`. The script never sets permissive on its own. The owner
  allowed this permissive fallback on 2026-11-18. Every result of a run with `IVI_PERMISSIVE=1` is
  conditional on a permissive IVI, and the summary says so; `getenforce` of both guests is recorded
  at run time on every run. With `IVI_PERMISSIVE=1` the script runs `setenforce 0` on the IVI only
  and fails unless `getenforce` then reads `Permissive`.
- It starts or stops no VM and calls no `gcloud`.

## On the guest host

Run it detached with [`b12_launch.sh`](b12_launch.sh), in the operator's pattern of 2026-11-18
(`setsid nohup`, no systemd unit). Never run `all` in an SSH foreground: a dropped connection would
end a build mid-way. Never run it under `systemd-run` on that host: the unit's cgroup takes the
guests down. The launcher checks the tar's sha256 and commit id, extracts it into a fresh
`~/da-b12-<sha>` (an existing directory is refused; a rerun gets `-r<n>`), starts `all` detached,
stops the guests on any failure once this run began to boot them, packs the logs and identity into
`b12-records.tgz` with its sha256, and ends with one `B12 RESULT:` line. The script also needs the
bench scripts of the 2026-11-17 rebuild (`DE4SDV_ROOT`, default `~/de4sdv-e8fa324a`, for
`launch_two_vms.sh`).

```bash
# 1. On the lead host, in the repository: the exact head, the launcher beside it, their digests.
H=$(git rev-parse --short=8 <head>)
mkdir -p ~/b12-upload-$H
git archive --format=tar.gz -o ~/b12-upload-$H/da-b12-$H.tar.gz "$H" implementation/driver-assistance-bench
git show "$H:implementation/driver-assistance-bench/guest-build/b12_launch.sh" > ~/b12-upload-$H/b12_launch.sh
cd ~/b12-upload-$H
sha256sum da-b12-$H.tar.gz > da-b12-$H.tar.gz.sha256
sha256sum da-b12-$H.tar.gz b12_launch.sh > b12-upload.sha256
# Upload the four files into ~/b12-upload/ on de4sdv-aaos-build.

# 2. On de4sdv-aaos-build: check the upload, then start the run detached (it returns at once).
cd ~/b12-upload && sha256sum -c b12-upload.sha256
bash ~/b12-upload/b12_launch.sh start ~/b12-upload/da-b12-<H>.tar.gz

# 3. Poll (every few minutes) until the B12 RESULT line appears.
bash ~/b12-upload/b12_launch.sh status

# 4a. If the result is FAILED on the Gateway lookup under Enforcing, the run printed this rerun
#     command (the owner's permissive fallback of 2026-11-18); run it as printed:
IVI_PERMISSIVE=1 B12_RERUN=2 bash /home/mrk/b12-upload/b12_launch.sh start /home/mrk/b12-upload/da-b12-<H>.tar.gz
# 4b. To end a run early (the run stops the guests on its way out, then writes its result line):
bash ~/b12-upload/b12_launch.sh abort

# 5. Copy back <run dir>/b12-records.tgz and b12-records.tgz.sha256 (the result line names them),
#    check them with sha256sum -c on the lead host, and stop the host only after a result line
#    with "crosvm left: 0".
```

Expected duration after the product switch of 2026-11-18 (the switch back to the core ran 44,590
actions in 49 min): about 60 min for the IVI module step (the first IVI build after the switch
re-runs Soong for `sdv_ivi_cf`, and may rebuild shared intermediates the app's dependencies use;
inference), nothing for the core (B11 is in the core image since 2026-11-18), about 20 min for
boot, install and verify. About 1.5 h in all; add 49 min if the core must be rebuilt after all. Set
the host deadline to at least 2.5 h. A permissive rerun adds about 30 min (the module build is then
incremental; boot, install and verify again). The script puts no timeout on `m`; `up` is bounded
(1800 s) and every adb call by `ADB_TIMEOUT_S`.

## Tests

`tests/` runs in the `driver-assistance-bench (INC-DRIVING-002)` suite, against a synthetic tree
whose `lunch` and `m` only record their arguments, a fake adb
(`../ivi-warning-app/tests/fakes/adb`), a fake `cvd` and a fake `launch_two_vms.sh`:

- `test_guest_build_script.py`: `bash -n`, no deletion of the kept tree, recorded variants only,
  groups removed only under `GUESTS=fresh`, the SELinux mode changed only under `IVI_PERMISSIVE=1`,
  and `detect`, `core` and `ivi` against the synthetic tree;
- `test_guest_build_run.py`: the image records (the committed ones and the refusal of a mismatch or a
  missing record beside the kit's stale one), the refusal of an IVI image change, of a core build
  under running guests and of a tree whose `broker.vsidl` lacks the message, `all` passing, the
  guest stop on a failure after boot and on HUP, INT and TERM, none before boot, the Enforcing stop
  with its rerun command, the permissive run, the broker APEX check, and B12's own directories;
- `test_b12_launch.py`: the launcher's sha256 and commit checks, the fresh extraction, the detached
  run's result line and records, the guest stop on failure and on `abort`, the rerun command.

## What the local tests cannot show

That the real tree's paths are the ones the detection reads (above all the installed
stack config), that the module build leaves the real IVI images untouched, and every step from `boot`
on against real guests. The phase 10 probe of the guests starts from this script's summary.
