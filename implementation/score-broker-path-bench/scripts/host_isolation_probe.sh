#!/usr/bin/env bash
# Reachability check of REQ-MW-016's second finding: confirm the host DDS ports
# and port 4721 stay unreachable from every guest domain. Defensive
# verification of isolation with standard tools. It records artifacts for the
# evaluator (de4sdv_broker_path_bench.probe); the evaluator, not this script,
# returns the verdict. A pass means the probes did NOT reach the host.
#
#   host_isolation_probe.sh run <out-dir>   list, probe from both VMs over every interface, record
#
# Reachability is judged as #448 asks: a capture on the guest-facing interface
# and the counters of the isolation rule (both). A probe reached when its
# marker was captured on the host AND the drop counter did not take it;
# dropped when the counter moved; unknown when the send failed or nothing
# arrived. The pre-netfilter capture over-counts (it sees dropped datagrams
# too), so the counter decides reached vs dropped. Without a readable table
# the probe cannot judge, so it records that and the run is inconclusive. The
# positive control uses the same capture observation and must also arrive at
# the bench's own socket. It assumes launch_two_vms.sh is up and
# host_isolation_firewall.sh add is in place.
set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/bench_env.sh"
OUT="${2:?usage: $0 run <out-dir>}"; mkdir -p "$OUT"
: "${CONTROL_PORT:=39999}"       # a host port with no drop rule, for the positive control
: "${PROBE_SEND_TIMEOUT:=2}"     # seconds; every guest send is wrapped in it (review R27)
TABLE_INET="de4sdv_bench"
SCAN=(python3 -m de4sdv_broker_path_bench.hostscan)
export PYTHONPATH="$HERE/../src${PYTHONPATH:+:$PYTHONPATH}"

guest_cmd() { local serial="$1"; shift; "$ADB" -s "$serial" shell "$@"; }

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
    echo "$!" >> "$OUT/.capture.pids"; echo "$pcap" >> "$OUT/.capture.files"
  done
  sleep 1
}

stop_captures() {
  sleep 1
  if [ -f "$OUT/.capture.pids" ]; then while read -r pid; do sudo kill -INT "$pid" 2>/dev/null || true; done < "$OUT/.capture.pids"; fi
  sleep 1
  local files=(); [ -f "$OUT/.capture.files" ] && mapfile -t files < "$OUT/.capture.files"
  for f in "${files[@]}"; do [ -f "$f" ] && sudo chown "$USER" "$f" 2>/dev/null || true; done
  "${SCAN[@]}" captured "${files[@]}" > "$OUT/captured_markers.json" 2>/dev/null \
    || echo '{"udp_markers": [], "tcp_syns": []}' > "$OUT/captured_markers.json"
}

# --- the positive control, by the same capture observation --------------
# It sends while the captures run; its capture witness is read in
# finalize_control after the captures have been read (ordering matters).
CONTROL_MARKER="MARK:control-ivi"
control_probe() {
  CONTROL_MARKER="MARK:control-ivi-${HOST_ADDR}-${CONTROL_PORT}"
  : > "$OUT/control-received.txt"
  ( timeout 120 "${SCAN[@]}" control-listen --port "$CONTROL_PORT" --out "$OUT/control-received.txt" --seconds 60 \
      >/dev/null 2>&1 & echo $! > "$OUT/.control.pid" ) || true
  sleep 1
  local before after
  before="$(dds_counter)"
  guest_cmd "$IVI_ADB" "echo -n '$CONTROL_MARKER' | toybox nc -u -w 1 $HOST_ADDR $CONTROL_PORT >/dev/null 2>&1" || true
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
  local probed_if="" probed_addr="" expected_if
  # Expected interfaces: the guest's non-lo interfaces that have an IPv4 address
  # (the IPv4 probe can cover them; IPv6 stays a known limit). Derived from the
  # inventory, independently of which pairs the probe skips (review R29).
  expected_if="$("${SCAN[@]}" guest-ifaces "$OUT/guest_inventory_${guest}.txt" | awk '$2!="lo" && $3!="-"{print $2}' | sort -u | tr '\n' ' ')"
  : "${PROBE_HOST_ADDRS:=$HOST_EXPECTED_ADDRS}"
  local ns iface src addr port before after moved status connected marker
  # Probe from the root namespace interfaces and from each VLAN namespace.
  while read -r ns iface src; do
    [ -n "$iface" ] || continue
    [ "$iface" = lo ] && continue                  # loopback cannot reach the host segment (review R15/R27)
    [ "$src" = "-" ] && continue                   # an interface with no IPv4 address
    probed_if="$probed_if $iface"
    local runner=("$ADB" -s "$serial" shell)
    [ "$ns" != "-" ] && runner=("$ADB" -s "$serial" shell "ip netns exec $ns")
    for addr in $PROBE_HOST_ADDRS; do
      case " $probed_addr " in *" $addr "*) : ;; *) probed_addr="$probed_addr $addr" ;; esac
      # A route check: skip the (interface, address) pair with no route (review R27).
      if ! "${runner[@]}" "ip route get $addr >/dev/null 2>&1"; then
        continue
      fi
      for port in $(dds_ports_expanded); do
        marker="MARK:${guest}-${iface}-${addr}-${port}"
        before="$(dds_counter)"
        if "${runner[@]}" "echo -n '$marker' | timeout $PROBE_SEND_TIMEOUT toybox nc -s $src -u -w 1 $addr $port >/dev/null 2>&1"; then
          status=sent
        else
          status=send_failed
        fi
        after="$(dds_counter)"
        moved="$(counter_moved_json "$before" "$after")"
        printf '{"guest":"%s","interface":"%s","src_addr":"%s","host":"%s","port":%s,"protocol":"udp","marker":"%s","send_status":"%s","counter_moved":%s,"guest_connected":null}\n' \
          "$guest" "$iface" "$src" "$addr" "$port" "$marker" "$status" "$moved" >> "$OUT/attempts.ndjson"
      done
      # Port 4721 (TCP): nc -z, the guest's own connect result, with the counter.
      marker="MARK:${guest}-${iface}-${addr}-${FRAME_ASSEMBLER_PORT}"
      before="$(tcp_counter)"
      if "${runner[@]}" "timeout $PROBE_SEND_TIMEOUT toybox nc -z -s $src -w 1 $addr $FRAME_ASSEMBLER_PORT >/dev/null 2>&1"; then
        connected=true; status=sent
      else
        connected=false; status=sent    # a refused/timed-out connect still left the guest; the counter and capture judge it
      fi
      after="$(tcp_counter)"
      moved="$(counter_moved_json "$before" "$after")"
      printf '{"guest":"%s","interface":"%s","src_addr":"%s","host":"%s","port":%s,"protocol":"tcp","marker":"%s","send_status":"%s","counter_moved":%s,"guest_connected":%s}\n' \
        "$guest" "$iface" "$src" "$addr" "$FRAME_ASSEMBLER_PORT" "$marker" "$status" "$moved" "$connected" >> "$OUT/attempts.ndjson"
    done
  done < <("${SCAN[@]}" guest-ifaces "$OUT/guest_inventory_${guest}.txt")
  # shellcheck disable=SC2153
  COV_GUEST="$guest" COV_PIF="$probed_if" COV_PADDR="$probed_addr" COV_EIF="$expected_if" COV_EADDR="$HOST_EXPECTED_ADDRS" \
    py_json "$OUT/coverage_${guest}.json" <<'PY'
import json, os, sys
json.dump({"guest": os.environ["COV_GUEST"],
           "probed_interfaces": os.environ["COV_PIF"].split(),
           "probed_host_addresses": os.environ["COV_PADDR"].split(),
           "expected_interfaces": os.environ["COV_EIF"].split(),
           "expected_host_addresses": os.environ["COV_EADDR"].split()}, open(sys.argv[1], "w"), indent=1)
PY
}

counter_moved_json() {
  local before="$1" after="$2"
  if [ -n "$before" ] && [ -n "$after" ]; then [ "$after" -gt "$before" ] 2>/dev/null && echo true || echo false; else echo null; fi
}

asm_mw_031() { sudo "${SCAN[@]}" asm031 --proc /proc > "$OUT/asm_mw_031.json" 2>/dev/null || "${SCAN[@]}" asm031 --proc /proc > "$OUT/asm_mw_031.json"; }

run() {
  require_cmd ss "$ADB" nft tcpdump python3 toybox || true
  : > "$OUT/attempts.ndjson"
  # The host addresses the probe expects to cover: every cvd-* host address,
  # derived independently of what the probe iterates (review R29).
  ip -o -4 addr show > "$OUT/host_ip_addr.txt" 2>/dev/null || true
  HOST_EXPECTED_ADDRS="$("${SCAN[@]}" host-addresses "$OUT/host_ip_addr.txt" | tr '\n' ' ')"
  [ -n "${HOST_EXPECTED_ADDRS// }" ] || HOST_EXPECTED_ADDRS="$HOST_ADDR"
  export HOST_EXPECTED_ADDRS
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
}

case "${1:-}" in
  run) run ;;
  *) echo "usage: $0 run <out-dir>" >&2; exit 2 ;;
esac
