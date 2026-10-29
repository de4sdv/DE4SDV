#!/usr/bin/env bash
# Reachability check of REQ-MW-016's second finding: confirm the host DDS ports
# and port 4721 stay unreachable from every guest domain. Defensive
# verification of isolation. It records artifacts for the evaluator
# (de4sdv_broker_path_bench.probe); the evaluator, not this script, returns the
# verdict. A pass means the probes did NOT reach the host.
#
#   host_isolation_probe.sh run <out-dir>   list, probe from both VMs over every interface, record
#   host_isolation_probe.sh render-probe <ns> <iface> <src> <addr> <port> <marker>   print the guest UDP command
#   host_isolation_probe.sh render-tcp   <ns> <iface> <src> <addr> <port> <marker> [sport]   print the guest TCP command
#   host_isolation_probe.sh dds-range <out.json>   write the DDS range the probe iterates (dds_range.json)
#
# The probes use the bench sender (de4sdv_probe_send), not nc: it pins the
# egress device (SO_BINDTODEVICE), the source address and the source port, sends
# one datagram or does one timed TCP connect, and exits with the errno. So each
# probe really leaves on its named interface whatever the route says (review
# R41) and never loops (reviews R39, R40). A namespaced probe runs the sender
# inside the namespace (review R42). Coverage is derived by the evaluator from
# the captured attempts, so a pair the sender could not leave on is a gap, not a
# self-reported probe (reviews R41, B3). Each attempt records the guest
# interface's MAC (from the guest inventory), and each capture records the host
# interface, source address and MAC it saw, so the evaluator counts a probe for
# its pair only when it arrived from the named interface and source (R41). The
# :4721 probe pins a source port per attempt, which identifies its SYN.
#
# Reachability is judged as VC-MW-017 asks: a capture on the guest-facing interface
# AND the counters of the isolation rule. reached = captured and the counter
# did not take it; dropped = captured and the counter moved; unknown = the send
# failed or nothing arrived. The pre-netfilter capture over-counts, so the
# counter decides reached vs dropped. Without a readable table the probe cannot
# judge, so the run is inconclusive. The positive control uses the same capture
# observation and must also arrive at the bench's own socket. It assumes
# launch_two_vms.sh is up and host_isolation_firewall.sh add is in place.
set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/bench_env.sh"
: "${PROBE_SENDER:=$PROBE_SENDER_GUEST}"  # the guest sender (provision_probe_sender.sh install)
: "${RUN_DIR:=$HERE/../run}"             # the session run directory with run-manifest.yaml
: "${PROBE_TCP_SPORT_BASE:=28000}"       # the :4721 probes pin source ports from here, one per attempt
: "${CONTROL_PORT:=39999}"               # a host port with no drop rule, for the positive control
: "${PROBE_SEND_TIMEOUT:=2}"             # seconds; a guest send that hangs is killed by this outer timeout
: "${PROBE_TCP_TIMEOUT_MS:=1000}"        # the sender's own TCP connect timeout
TABLE_INET="de4sdv_bench"
SCAN=(python3 -m de4sdv_broker_path_bench.hostscan)
export PYTHONPATH="$HERE/../src${PYTHONPATH:+:$PYTHONPATH}"

guest_cmd() { local serial="$1"; shift; "$ADB" -s "$serial" shell "$@"; }

# --- the guest commands (rendered so a test can check the namespace prefix) ---
# A namespaced probe runs the sender inside the namespace (review R42); the
# marker is fed on stdin from the guest shell. `ns` is "-" for the root netns.
remote_probe_cmd() {  # ns iface src addr port marker
  local ns="$1" iface="$2" src="$3" addr="$4" port="$5" marker="$6" prefix=""
  [ "$ns" != "-" ] && prefix="ip netns exec $ns "
  printf "echo -n '%s' | timeout %s %s%s --device %s --source %s --sport 0 --host %s --port %s" \
    "$marker" "$PROBE_SEND_TIMEOUT" "$prefix" "$PROBE_SENDER" "$iface" "$src" "$addr" "$port"
}
remote_tcp_cmd() {  # ns iface src addr port marker [sport]
  local ns="$1" iface="$2" src="$3" addr="$4" port="$5" _marker="$6" sport="${7:-0}" prefix=""
  [ "$ns" != "-" ] && prefix="ip netns exec $ns "
  printf "timeout %s %s%s --tcp --device %s --source %s --sport %s --host %s --port %s --timeout-ms %s" \
    "$PROBE_SEND_TIMEOUT" "$prefix" "$PROBE_SENDER" "$iface" "$src" "$sport" "$addr" "$port" "$PROBE_TCP_TIMEOUT_MS"
}

# --- the sender on both guests, checked against the run manifest ----------
# provision_probe_sender.sh install pushes the sender and records its sha256 in
# the run manifest. The probe stops before any probe if a guest lacks it or
# carries other bytes, and records what it found (probe_sender.json).
sender_preflight() {
  local expected core_sha ivi_sha
  expected="$(run_manifest_sender_sha256 "$RUN_DIR/run-manifest.yaml" 2>/dev/null)"
  core_sha="$(guest_cmd "$CORE_ADB" "sha256sum $PROBE_SENDER 2>/dev/null" 2>/dev/null | tr -d '\r' | awk '{print $1}')"
  ivi_sha="$(guest_cmd "$IVI_ADB" "sha256sum $PROBE_SENDER 2>/dev/null" 2>/dev/null | tr -d '\r' | awk '{print $1}')"
  SENDER_PATH="$PROBE_SENDER" SENDER_EXPECTED="$expected" SENDER_CORE="$core_sha" SENDER_IVI="$ivi_sha" \
    py_json "$OUT/probe_sender.json" <<'PY'
import json, os, sys
expected = os.environ["SENDER_EXPECTED"] or None
guests = {name: {"path": os.environ["SENDER_PATH"], "sha256": os.environ[key] or None}
          for name, key in (("core", "SENDER_CORE"), ("ivi", "SENDER_IVI"))}
ok = bool(expected) and all(g["sha256"] == expected for g in guests.values())
json.dump({"expected_sha256": expected, "guests": guests, "ok": ok}, open(sys.argv[1], "w"), indent=1)
sys.exit(0 if ok else 1)
PY
}

# --- the DDS range the probe iterates (review R45) ----------------------
dds_range_record() {
  local out="$1"
  DDS_RANGE_PORTS="$(dds_ports_expanded | tr '\n' ' ')" ROS_DOMAIN_ID="$ROS_DOMAIN_ID" \
    DDS_MAX_PARTICIPANT_INDEX="$DDS_MAX_PARTICIPANT_INDEX" py_json "$out" <<'PY'
import json, os, sys
json.dump({"domain": int(os.environ["ROS_DOMAIN_ID"]),
           "max_participant_index": int(os.environ["DDS_MAX_PARTICIPANT_INDEX"]),
           "ports": sorted({int(p) for p in os.environ["DDS_RANGE_PORTS"].split()})}, open(sys.argv[1], "w"), indent=1)
PY
}

# --- the isolation table and its counters (the validity gate) -----------
nft_dump() { sudo nft -a list table inet "$TABLE_INET" 2>&1; }
dds_counter() { nft_dump | awk '/udp dport @dds/ && / drop/ {for(i=1;i<=NF;i++) if($i=="packets"){s+=$(i+1);n++}} END{if(n>0) print s}'; }
tcp_counter() { nft_dump | awk '/tcp dport '"$FRAME_ASSEMBLER_PORT"'/ && / drop/ {for(i=1;i<=NF;i++) if($i=="packets"){s+=$(i+1);n++}} END{if(n>0) print s}'; }

firewall_record() {
  nft_dump > "$OUT/nft.txt" 2>&1 || true
  "${SCAN[@]}" counters "$OUT/nft.txt" > "$OUT/.counters.json"
  py_json "$OUT/firewall.json" "$OUT/.counters.json" <<'PY'
import json, sys
counters = json.load(open(sys.argv[2]))
json.dump({"inet_table_present": bool(counters.get("table")),
           "dds_counters_readable": counters.get("dds_packets") is not None,
           "tcp_counters_readable": counters.get("tcp_packets") is not None}, open(sys.argv[1], "w"), indent=1)
PY
}

py_json() { local out="$1"; shift; python3 - "$out" "$@"; }

# --- host listeners (both ss steps, parsed by hostscan) -----------------
host_listeners() {
  ss -H -u -l -n -p > "$OUT/ss_udp.txt" 2>/dev/null || true
  ss -H -t -l -n -p > "$OUT/ss_tcp.txt" 2>/dev/null || true
  "${SCAN[@]}" listeners --udp "$OUT/ss_udp.txt" --tcp "$OUT/ss_tcp.txt" > "$OUT/host_listeners.json"
}

# --- guest-facing host interfaces to capture on -------------------------
host_capture_ifaces() {
  { echo "$HOST_BRIDGE"; ip -o link show 2>/dev/null | awk -F': ' '{print $2}' | sed 's/@.*//' | grep -E '^cvd-'; } | sort -u
}

start_captures() {
  : > "$OUT/.capture.pids"; : > "$OUT/.capture.files"
  local iface
  for iface in $(host_capture_ifaces); do
    ip link show "$iface" >/dev/null 2>&1 || continue
    local pcap="$OUT/capture-$iface.pcap"
    sudo tcpdump -i "$iface" -s0 -U -w "$pcap" "udp or (tcp port $FRAME_ASSEMBLER_PORT)" >/dev/null 2>&1 &
    # Each capture is named by its host interface (IFACE=PATH), so the reader
    # records where each marker arrived (review R41).
    echo "$!" >> "$OUT/.capture.pids"; echo "$iface=$pcap" >> "$OUT/.capture.files"
  done
  sleep 1
}

stop_captures() {
  sleep 1
  if [ -f "$OUT/.capture.pids" ]; then while read -r pid; do sudo kill -INT "$pid" 2>/dev/null || true; done < "$OUT/.capture.pids"; fi
  sleep 1
  local files=(); [ -f "$OUT/.capture.files" ] && mapfile -t files < "$OUT/.capture.files"
  for f in "${files[@]}"; do [ -f "${f#*=}" ] && sudo chown "$USER" "${f#*=}" 2>/dev/null || true; done
  "${SCAN[@]}" captured "${files[@]}" > "$OUT/captured_markers.json" 2>"$OUT/captured_markers.err" \
    || echo '{"udp_markers": [], "udp_captures": [], "tcp_syns": []}' > "$OUT/captured_markers.json"
}

# --- the positive control, by the same capture observation --------------
CONTROL_MARKER="MARK:control-ivi"
control_probe() {
  CONTROL_MARKER="MARK:control-ivi-${HOST_ADDR}-${CONTROL_PORT}"
  : > "$OUT/control-received.txt"
  ( timeout 120 "${SCAN[@]}" control-listen --port "$CONTROL_PORT" --out "$OUT/control-received.txt" --seconds 60 \
      >/dev/null 2>&1 & echo $! > "$OUT/.control.pid" ) || true
  sleep 1
  # The IVI's egress device and source toward the host, from its own routing,
  # so the control sender binds the real interface (not a foreign source).
  local route dev src before after
  route="$(guest_cmd "$IVI_ADB" "ip route get $HOST_ADDR 2>/dev/null" | tr -d '\r')"
  read -r dev src < <("${SCAN[@]}" route <(printf '%s\n' "$route"))
  before="$(dds_counter)"
  if [ -n "$dev" ] && [ "$dev" != none ] && [ -n "$src" ] && [ "$src" != "-" ]; then
    guest_cmd "$IVI_ADB" "$(remote_probe_cmd - "$dev" "$src" "$HOST_ADDR" "$CONTROL_PORT" "$CONTROL_MARKER")" \
      >/dev/null 2>&1 || true
  fi
  sleep 1
  after="$(dds_counter)"
  [ -f "$OUT/.control.pid" ] && kill "$(cat "$OUT/.control.pid")" 2>/dev/null || true
  echo "$before" > "$OUT/.control-before"; echo "$after" > "$OUT/.control-after"
}

finalize_control() {
  local before after
  before="$(cat "$OUT/.control-before" 2>/dev/null)"; after="$(cat "$OUT/.control-after" 2>/dev/null)"
  CONTROL_MARKER="$CONTROL_MARKER" CONTROL_BEFORE="$before" CONTROL_AFTER="$after" \
    py_json "$OUT/control.json" "$OUT/captured_markers.json" "$OUT/control-received.txt" <<'PY'
import json, os, sys
captured = set(json.load(open(sys.argv[2])).get("udp_markers", [])) if os.path.exists(sys.argv[2]) else set()
received = open(sys.argv[3]).read() if os.path.exists(sys.argv[3]) else ""
marker = os.environ["CONTROL_MARKER"]
before, after = os.environ.get("CONTROL_BEFORE", ""), os.environ.get("CONTROL_AFTER", "")
counter_moved = (int(after) > int(before)) if (before.isdigit() and after.isdigit()) else \
    (False if before == after else None)
delivered = marker in received
json.dump({"captured": marker in captured, "counter_moved": counter_moved, "delivered": delivered,
           "detail": f"captured={marker in captured} delivered={delivered}"}, open(sys.argv[1], "w"), indent=1)
PY
}

# --- the probes ---------------------------------------------------------
dds_ports_expanded() {
  local token first last
  for token in $(dds_udp_port_set); do
    if printf '%s' "$token" | grep -q '-'; then first="${token%-*}"; last="${token#*-}"; seq "$first" "$last"; else echo "$token"; fi
  done
}

counter_moved_json() {
  local before="$1" after="$2"
  if [ -n "$before" ] && [ -n "$after" ]; then [ "$after" -gt "$before" ] 2>/dev/null && echo true || echo false; else echo null; fi
}

probe_guest() {
  local serial="$1" guest="$2"
  "$ADB" connect "$serial" >/dev/null 2>&1 || true
  "$ADB" -s "$serial" root >/dev/null 2>&1 || true
  # The guest's interfaces and their IPv4 source address, per namespace.
  {
    echo "# netns:"; guest_cmd "$serial" "ip -o link show; ip -o -4 addr show"
    for ns in sd_mesh_ns sdv_dt_ns; do
      echo "# netns: $ns"
      guest_cmd "$serial" "ip netns exec $ns ip -o link show 2>/dev/null; ip netns exec $ns ip -o -4 addr show 2>/dev/null" 2>/dev/null
    done
  } | tr -d '\r' > "$OUT/guest_inventory_${guest}.txt"
  # Expected interfaces: the guest's non-lo interfaces with an IPv4 address (the
  # IPv4 probe covers them; IPv6 is a known limit). Derived from the inventory,
  # independently of which pairs the probe can leave on (reviews R29, R41).
  local expected_if
  expected_if="$("${SCAN[@]}" guest-ifaces "$OUT/guest_inventory_${guest}.txt" | awk '$2!="lo" && $3!="-"{print $2}' | sort -u | tr '\n' ' ')"
  : "${PROBE_HOST_ADDRS:=$HOST_EXPECTED_ADDRS}"
  local ns iface src mac addr port before after moved status connected marker sport
  # Probe from the root-namespace interfaces and from each VLAN namespace. The
  # sender binds the device, so no route pre-check is needed: a pair it cannot
  # leave on returns an errno (send_failed), which the evaluator reads as a
  # coverage gap, not a silent skip (reviews R41, B3). Each attempt records the
  # interface's MAC from the inventory; the evaluator matches it with the
  # source MAC the host capture saw (R41).
  while read -r ns iface src mac; do
    [ -n "$iface" ] || continue
    [ "$iface" = lo ] && continue                  # loopback cannot reach the host segment (review R15/R27)
    [ "$src" = "-" ] && continue                   # an interface with no IPv4 address
    for addr in $PROBE_HOST_ADDRS; do
      for port in $(dds_ports_expanded); do
        marker="MARK:${guest}-${iface}-${addr}-${port}"
        before="$(dds_counter)"
        if guest_cmd "$serial" "$(remote_probe_cmd "$ns" "$iface" "$src" "$addr" "$port" "$marker")" >/dev/null 2>&1; then
          status=sent
        else
          status=send_failed
        fi
        after="$(dds_counter)"
        moved="$(counter_moved_json "$before" "$after")"
        printf '{"guest":"%s","netns":"%s","interface":"%s","src_addr":"%s","src_mac":"%s","host":"%s","port":%s,"protocol":"udp","marker":"%s","send_status":"%s","counter_moved":%s,"guest_connected":null}\n' \
          "$guest" "$ns" "$iface" "$src" "${mac:--}" "$addr" "$port" "$marker" "$status" "$moved" >> "$OUT/attempts.ndjson"
      done
      # Port 4721 (TCP): the sender's own timed connect result, with the counter.
      # The source port is pinned per attempt, so the capture can find its SYN.
      marker="MARK:${guest}-${iface}-${addr}-${FRAME_ASSEMBLER_PORT}"
      TCP_SEQ=$(( ${TCP_SEQ:-0} + 1 )); sport=$(( PROBE_TCP_SPORT_BASE + TCP_SEQ ))
      before="$(tcp_counter)"
      if guest_cmd "$serial" "$(remote_tcp_cmd "$ns" "$iface" "$src" "$addr" "$FRAME_ASSEMBLER_PORT" "$marker" "$sport")" >/dev/null 2>&1; then
        connected=true
      else
        connected=false   # a refused/timed-out connect still left the guest; the counter and capture judge it
      fi
      after="$(tcp_counter)"
      moved="$(counter_moved_json "$before" "$after")"
      printf '{"guest":"%s","netns":"%s","interface":"%s","src_addr":"%s","src_mac":"%s","host":"%s","port":%s,"sport":%s,"protocol":"tcp","marker":"%s","send_status":"sent","counter_moved":%s,"guest_connected":%s}\n' \
        "$guest" "$ns" "$iface" "$src" "${mac:--}" "$addr" "$FRAME_ASSEMBLER_PORT" "$sport" "$marker" "$moved" "$connected" >> "$OUT/attempts.ndjson"
    done
  done < <("${SCAN[@]}" guest-ifaces "$OUT/guest_inventory_${guest}.txt")
  # The run records only the EXPECTED sets; the evaluator derives the PROBED
  # sets from the captured attempts (reviews R41, B3).
  COV_GUEST="$guest" COV_EIF="$expected_if" COV_EADDR="$HOST_EXPECTED_ADDRS" \
    py_json "$OUT/coverage_${guest}.json" <<'PY'
import json, os, sys
json.dump({"guest": os.environ["COV_GUEST"],
           "expected_interfaces": os.environ["COV_EIF"].split(),
           "expected_host_addresses": os.environ["COV_EADDR"].split()}, open(sys.argv[1], "w"), indent=1)
PY
}

asm_mw_031() {
  # The ROS 2 environment scan reads /proc/<pid>/environ for every ROS 2
  # process, so it needs root. sudo strips PYTHONPATH, so it runs from src/ with
  # the module on the default path (review R44). Keep stderr, and record the uid
  # that ran the scan; the unprivileged fallback gives holds=null for any
  # process it cannot read.
  if ( cd "$HERE/../src" && sudo python3 -m de4sdv_broker_path_bench.hostscan asm031 --proc /proc ) \
       > "$OUT/asm_mw_031.json" 2> "$OUT/asm_mw_031.err"; then
    echo "scan_uid: 0 (root via sudo)" > "$OUT/asm_mw_031.uid"
  else
    ( cd "$HERE/../src" && python3 -m de4sdv_broker_path_bench.hostscan asm031 --proc /proc ) \
       > "$OUT/asm_mw_031.json" 2>> "$OUT/asm_mw_031.err" || true
    echo "scan_uid: $(id -u) (unprivileged fallback; an unreadable process gives holds=null)" > "$OUT/asm_mw_031.uid"
  fi
}

run() {
  require_cmd ss "$ADB" nft tcpdump python3 || true
  : > "$OUT/attempts.ndjson"
  # The host addresses the probe expects to cover: every cvd-* host address,
  # derived independently of what the probe iterates (review R29).
  ip -o -4 addr show > "$OUT/host_ip_addr.txt" 2>/dev/null || true
  HOST_EXPECTED_ADDRS="$("${SCAN[@]}" host-addresses "$OUT/host_ip_addr.txt" | tr '\n' ' ')"
  [ -n "${HOST_EXPECTED_ADDRS// }" ] || HOST_EXPECTED_ADDRS="$HOST_ADDR"
  export HOST_EXPECTED_ADDRS
  # The sender must be on both guests with the bytes the run manifest records;
  # without it every probe would be a send failure, so stop here.
  if ! sender_preflight; then
    log "ERROR: the probe sender is missing on a guest or differs from the run manifest ($OUT/probe_sender.json); run provision_probe_sender.sh install first"
    return 1
  fi
  dds_range_record "$OUT/dds_range.json"
  firewall_record
  host_listeners
  start_captures
  control_probe
  probe_guest "$CORE_ADB" core
  probe_guest "$IVI_ADB" ivi
  stop_captures
  finalize_control
  asm_mw_031
  python3 - "$OUT" <<'PY'
import json, os, sys
out = sys.argv[1]
attempts = [json.loads(line) for line in open(os.path.join(out, "attempts.ndjson")) if line.strip()]
json.dump(attempts, open(os.path.join(out, "probe_attempts.json"), "w"), indent=1)
per_guest = {}
for guest in ("core", "ivi"):
    path = os.path.join(out, f"coverage_{guest}.json")
    if os.path.exists(path):
        per_guest[guest] = json.load(open(path))
json.dump({"per_guest": per_guest}, open(os.path.join(out, "coverage.json"), "w"), indent=1)
PY
  log "probe artifacts in $OUT; evaluate with: python -m de4sdv_broker_path_bench.run $OUT --case VC-MW-017"
  log "NOTE: the first finding needs an inspection record (inspection.json); the ASM-MW-029 client check is recorded by capture_case.sh."
  log "NOTE: a full probe covers every DDS port of the set plus 4721 for each (guest, interface, host) pair; a reduced range is a coverage gap (dds_range.json)."
}

case "${1:-}" in
  run) OUT="${2:?usage: $0 run <out-dir>}"; mkdir -p "$OUT"; run ;;
  render-probe) remote_probe_cmd "${2:--}" "${3:?iface}" "${4:?src}" "${5:?addr}" "${6:?port}" "${7:?marker}"; echo ;;
  render-tcp) remote_tcp_cmd "${2:--}" "${3:?iface}" "${4:?src}" "${5:?addr}" "${6:?port}" "${7:?marker}" "${8:-0}"; echo ;;
  dds-range) dds_range_record "${2:?usage: $0 dds-range <out.json>}" ;;
  *) echo "usage: $0 {run <out-dir>|render-probe ...|render-tcp ...|dds-range <out.json>}" >&2; exit 2 ;;
esac
