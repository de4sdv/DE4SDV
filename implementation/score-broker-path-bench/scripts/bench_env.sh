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

# --- cvd groups and adb ports (the documented multi-VM recipe:
#     SDV Core VM as instance 1, IVI VM as instance 2) ---
: "${CORE_GROUP:=de4sdv_core}"
: "${IVI_GROUP:=de4sdv_ivi}"
: "${CORE_INSTANCE:=1}"
: "${IVI_INSTANCE:=2}"
: "${CORE_ADB:=0.0.0.0:6520}"
: "${IVI_ADB:=0.0.0.0:6521}"

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

# --- the IVI SDV Gateway identity of the frame topic (for the relay's ACL) ---
# The relay's subject and the broker's publication; a run records the exact
# strings the relay and the mapping use.
: "${BROKER_PACKAGE:=com.android.sdv.someip}"
: "${BROKER_BUNDLE:=SomeIpBroker}"
: "${FRAME_SERVICE_UNIT:=de4sdv-score-aebs-signal-frame}"

# --- the SNTP server for the IVI VM clock (ASM-MW-030): the host chrony ---
: "${SNTP_SERVER:=$HOST_ADDR}"

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

log() { printf '%s %s\n' "$(date -u +%FT%T.%NZ)" "$*"; }

require_cmd() {
  local missing=0
  for cmd in "$@"; do command -v "$cmd" >/dev/null 2>&1 || { log "MISSING command: $cmd"; missing=1; }; done
  return $missing
}
