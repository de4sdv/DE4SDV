# VM change log — AAOS SDV broker-path bench (INC-MW-011 phase 10)

Every change the bench scripts make on the System 2 bench VM (GAP-MW-044), and
how to undo it. The table below is the reference of what each change is and its
undo; it is the tracked template. Per-session dated entries are written by the
scripts to `RUN_DIR/vm-change-log.session.txt` (in the run directory, not this
tracked file), as the spike's change log did, so a later session can see the
VM's state without editing a committed file.

The bench runs on the VM only. Nothing in this repository starts, stops or
reboots the VM, and nothing dispatches a workflow. The operator owns the VM
power state and the recovery steps.

| Change | Made by | Undo |
|---|---|---|
| SDV Core image overlay (mapping, stack config, broker ACL) | `build_sdv_core_image.sh stage` | `build_sdv_core_image.sh revert` |
| SDV Core image rebuilt (clean, recorded) | `build_sdv_core_image.sh build` | rebuild the base image after `revert` |
| Two guest VMs created (core instance 1, IVI instance 2, UNLOCKED) | `launch_two_vms.sh up` | `launch_two_vms.sh down` |
| Host route for the SD group on `cvd-ebr` | `host_sd_multicast_route.sh add` | `host_sd_multicast_route.sh remove` |
| Host isolation firewall (DDS ports + 4721 off the guest; SOME/IP bridge-port rule) | `host_isolation_firewall.sh add` | `host_isolation_firewall.sh remove` |
| IVI relay provisioning (one ACL per subject, broker object policy, relay binary and init, reboot) | `provision_ivi_relay.sh install` | `provision_ivi_relay.sh remove` |
| Host chrony serves the IVI (`chronyc allow`) | `set_ivi_clock.sh allow` | `set_ivi_clock.sh deny` |
| IVI VM clock set and slewed; auto_time off | `set_ivi_clock.sh setup` | re-enable `auto_time`, stop the slew (a reboot resets it) |
| Reachability probe (control listener, counter reads, nc probes) | `host_isolation_probe.sh run` | self-contained; stops its own observers |
| Recording (terminal panes, adb screenrecord) | `record_full_chain.sh` | `record_full_chain.sh stop` |
| SDV Core VM rebooted in place (recovery) | `recover_core_vm.sh recover` | none needed (in-place reboot) |
| Everything above | — | `teardown.sh` |

## Standing notes

- The bench starts from a clean, recorded SDV Core build. The spike's cp2a eng
  images with the spike's broker APEX are not acceptable (they were not
  reverted on the VM after the 2026-10-28 spike).
- The SD agent of the IVI VM reads the ACLs only at its start, and a second
  ACL file for one subject makes it exit. `provision_ivi_relay.sh` installs
  exactly one and reboots.
- A failure of the IVI SD agent or of the gateway client needs an IVI VM
  reboot (`launch_two_vms.sh reboot-ivi`), which also restarts the relay and
  the ingress and needs a new clock setting.
- Check `df -h /` before a build or a capture; the SDV Core build needs tens
  of GB and the disk guard floor is in the plan.
