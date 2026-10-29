#!/usr/bin/env bash
# Shared settings of the AAOS SDV broker-path bench (INC-MW-011 phase 10).
#
# Source it from the other scripts: `. "$(dirname "$0")/bench_env.sh"`. It sets
# names and addresses only; it starts nothing. Override any value from the
# environment before sourcing. The scripts run on the System 2 bench VM
# (GAP-MW-044); nothing here runs a workflow or touches a VM from CI.
set -u

# --- AOSP tree and products (the bench VM holds the checkout) ---
: "${AOSP_TOP:=$HOME/aosp}"
: "${AOSP_HOST_OUT:=$AOSP_TOP/out/host/linux-x86}"
: "${CORE_PRODUCT:=sdv_core_cf}"
: "${IVI_PRODUCT:=sdv_ivi_cf}"
: "${RELEASE:=cp2a}"
: "${VARIANT:=eng}"            # the bench boot mode is UNLOCKED (ADR 0025, decision 8)
: "${ADB:=$AOSP_HOST_OUT/bin/adb}"
: "${CVD:=$AOSP_HOST_OUT/bin/cvd}"

# --- cvd groups and adb ports (the documented multi-VM recipe: the SDV Core
#     VM as instance 1 and the IVI VM as instance 2 of the dev mesh, on cvd
#     base instance numbers 2 and 3, as the feasibility runs used) ---
: "${CORE_GROUP:=de4sdv_core}"
: "${IVI_GROUP:=de4sdv_ivi}"
: "${CORE_INSTANCE:=2}"       # cvd base_instance_num -> adb 6521
: "${IVI_INSTANCE:=3}"        # cvd base_instance_num -> adb 6522
: "${CORE_CONFIG:=sdv_core_instance1}"
: "${IVI_CONFIG:=sdv_ivi_instance2}"
: "${CORE_ADB:=0.0.0.0:6521}"
: "${IVI_ADB:=0.0.0.0:6522}"

# The dev-mesh boot identity (AOSP sample values of device/google/sdv; public
# sample keys, not secrets). The launch sets the full argument set with the
# boot mode forced to UNLOCKED and SOME/IP enabled on the core, as the
# feasibility runs did.
: "${VVM_FACTORY_TRUST:=c779a73d0595a6814ba0414a419e99ad4026ad0feb603f2ad80ee6a9e4d1adb7}"
: "${CORE_KEYMINT_HBK:=799da7577efd41d5b27810c5952fcec0291cbcfd687e77ac9a6cec8370651b1d}"
: "${IVI_KEYMINT_HBK:=a3b876291ff7341d861e325406b96a0b58d0a3daf6b030681b8afc24b84d1160}"

# --- host network of the KVM guest segment (cvd-ebr) ---
: "${HOST_BRIDGE:=cvd-ebr}"
: "${HOST_ADDR:=192.168.98.1}"
: "${CORE_ADDR:=192.168.98.3}"
: "${IVI_ADDR:=192.168.98.118}"
: "${SD_GROUP:=224.0.0.0}"       # in 224.0.0.0/24, which a Linux bridge floods (GAP-MW-047)
: "${SD_PORT:=30490}"            # SOME/IP service discovery
: "${SOMEIP_RELIABLE_PORT:=30509}"  # the frame event over TCP

# --- the frame path ports ---
: "${FRAME_ASSEMBLER_PORT:=4721}"   # INC-AEBS-010 frame server on the host (ASM-MW-029)
: "${RELAY_LOOPBACK_PORT:=4731}"    # the IVI frame relay on the IVI VM loopback

# --- the one ROS 2 environment of the host (adapterAbortConditions) ---
: "${ROS_DOMAIN_ID:=91}"
: "${DDS_MAX_PARTICIPANT_INDEX:=120}"

# --- the IVI SDV Gateway identity of the frame topic (for the broker's object
#     policy) ---
: "${BROKER_PACKAGE:=com.android.sdv.someip}"
: "${BROKER_BUNDLE:=SomeIpBroker}"
: "${FRAME_SERVICE_UNIT:=de4sdv-score-aebs-signal-frame}"

# --- the SNTP server for the IVI VM clock (ASM-MW-030): the host chrony ---
: "${SNTP_SERVER:=$HOST_ADDR}"

# --- the IVI frame relay (the relay lane owns these; no defaults). A script
#     that needs them calls require_relay_inputs and fails fast when they are
#     unset, so the bench never provisions the wrong subject or reads the wrong
#     logcat tag (review R10/R23). The real values of #439 are in the README.
#     RELAY_LOGCAT_TAG and RELAY_BIN are the relay's init-service name, which is
#     the model-guard marker, so they are not written into this file. ---
require_relay_inputs() {
  local missing=0 name
  for name in RELAY_BIN RELAY_RC RELAY_LOGCAT_TAG RELAY_SUBJECT_PACKAGE RELAY_SUBJECT_BUNDLE RELAY_SUBJECT_INSTANCE; do
    if [ -z "${!name:-}" ]; then echo "MISSING required relay input: $name (see the README for #439's values)"; missing=1; fi
  done
  return $missing
}

# The DDS UDP ports of the domain and the participant index (DDSI-RTPS 9.6.1.1):
# PB=7400 DG=250 PG=2, d0=0 d1=10 d2=1 d3=11. SPDP/user multicast and the
# unicast range of indices 0..MaxAutoParticipantIndex. The firewall and the
# evaluator derive the same set from these two parameters (GAP-MW-046).
dds_udp_port_set() {
  local domain="$ROS_DOMAIN_ID" mi="$DDS_MAX_PARTICIPANT_INDEX"
  local spdp_mc=$((7400 + 250 * domain + 0))
  local user_mc=$((7400 + 250 * domain + 1))
  local first_uni=$((7400 + 250 * domain + 10))
  local last_uni=$((7400 + 250 * domain + 11 + 2 * mi))
  echo "${spdp_mc} ${user_mc} ${first_uni}-${last_uni}"
}

# The core and IVI boot argument sets, UNLOCKED with SOME/IP enabled on the core.
core_bootconfig() {
  echo "androidboot.sdv.instance_name=instance1 androidboot.sdv.boot_mode=unlocked" \
       "androidboot.virt.address=3 androidboot.sdv.init_open_dice.sample_file=dice_handover_instance1" \
       "androidboot.sdv.vvmfactorytrust=${VVM_FACTORY_TRUST}" \
       "androidboot.sdv.keymint.rpc.hbk=${CORE_KEYMINT_HBK}" \
       "androidboot.sdv.preprovisioned_vvmtruststore=img androidboot.sdv.ignore_avb_state=true" \
       "androidboot.sdv.someip.enable=true"
}
ivi_bootconfig() {
  echo "androidboot.sdv.instance_name=instance2 androidboot.sdv.boot_mode=unlocked" \
       "androidboot.virt.address=4 androidboot.sdv.init_open_dice.sample_file=dice_handover_instance2" \
       "androidboot.sdv.vvmfactorytrust=${VVM_FACTORY_TRUST}" \
       "androidboot.sdv.keymint.rpc.hbk=${IVI_KEYMINT_HBK}" \
       "androidboot.sdv.preprovisioned_vvmtruststore=img androidboot.sdv.ignore_avb_state=true" \
       "androidboot.sdv.someip.enable=false"
}

log() { printf '%s %s\n' "$(date -u +%FT%T.%NZ)" "$*"; }

require_cmd() {
  local missing=0
  for cmd in "$@"; do command -v "$cmd" >/dev/null 2>&1 || { log "MISSING command: $cmd"; missing=1; }; done
  return $missing
}
