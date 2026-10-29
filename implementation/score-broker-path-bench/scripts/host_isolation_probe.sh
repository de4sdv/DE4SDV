#!/usr/bin/env bash
# Reachability check of REQ-MW-016's second finding: confirm the host DDS ports
# and port 4721 stay unreachable from every guest domain. It is a defensive
# verification of isolation, with standard tools (ss to list, nc to test one
# port, tcpdump and the nft counters on the host to observe). It records
# artifacts for the evaluator (de4sdv_broker_path_bench.probe); the evaluator,
# not this script, returns the verdict. A pass means the probes did NOT get
# through, confirmed by a positive control.
#
#   host_isolation_probe.sh run <out-dir>   list, probe from both VMs over every interface, and record
#
# It assumes launch_two_vms.sh is up and host_isolation_firewall.sh add is in
# place. It never opens a host port except the one control listener it starts
# and stops itself.
set -u
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/bench_env.sh"
OUT="${2:?usage: $0 run <out-dir>}"; mkdir -p "$OUT"
CONTROL_PORT="${CONTROL_PORT:-39999}"   # a host UDP port left reachable, for the positive control

py() { PYTHONPATH="$HERE/../src" python3 "$@"; }

host_listeners() {
  # Every UDP and TCP listener, with the owning process; mark the layer's
  # ROS 2 processes (adapter, health proxy) so the evaluator can fail a
  # reachable layer port outright.
  { ss -ulnp 2>/dev/null; ss -tlnp 2>/dev/null; } | py - > "$OUT/host_listeners.json" <<'PY'
import json, re, sys
rows = []
for line in sys.stdin:
    m = re.search(r"\s(\S+):(\d+)\s", line)
    users = re.search(r'users:\(\("([^"]+)"', line)
    if not m:
        continue
    proc = users.group(1) if users else ""
    rows.append({"address": m.group(1), "port": int(m.group(2)),
                 "protocol": "udp" if line.split()[0] in ("udp", "UNCONN") else "tcp",
                 "element": proc,
                 "element_in_layer": any(k in proc for k in ("adapter", "health_proxy", "de4sdv_score"))})
json.dump(rows, sys.stdout, indent=1)
PY
  log "recorded $(py -c "import json;print(len(json.load(open('$OUT/host_listeners.json'))))") host listeners"
}

start_host_observers() {
  "$HERE/host_isolation_firewall.sh" show > "$OUT/nft_before.txt" 2>&1 || true
  # Capture arrivals on the guest-facing bridge; markers that appear here reached the host.
  sudo tcpdump -i "$HOST_BRIDGE" -n -l -U -w "$OUT/host-guest-facing.pcap" \
    "udp or (tcp port $FRAME_ASSEMBLER_PORT)" >/dev/null 2>&1 &
  echo $! > "$OUT/.tcpdump.pid"
  # A control listener on a reachable port, to prove the method observes a hit.
  ( timeout 120 nc -u -l -k -p "$CONTROL_PORT" > "$OUT/control-received.txt" 2>/dev/null & echo $! > "$OUT/.control.pid" ) || true
  sleep 1
}

stop_host_observers() {
  [ -f "$OUT/.tcpdump.pid" ] && sudo kill "$(cat "$OUT/.tcpdump.pid")" 2>/dev/null || true
  [ -f "$OUT/.control.pid" ] && kill "$(cat "$OUT/.control.pid")" 2>/dev/null || true
  "$HERE/host_isolation_firewall.sh" show > "$OUT/nft_after.txt" 2>&1 || true
}

probe_from_guest() {
  local serial="$1" guest="$2"; shift 2
  "$ADB" connect "$serial" >/dev/null 2>&1 || true
  local s=("$ADB" -s "$serial"); "${s[@]}" root >/dev/null 2>&1 || true
  # Every interface and every address the guest holds.
  local ifaces; ifaces="$("${s[@]}" shell "ip -o -4 addr show | awk '{print \$2}'" | tr -d '\r' | sort -u)"
  for iface in $ifaces; do
    for port in $(dds_udp_port_set | tr '-' ' ' | tr ' ' '\n' | sort -un | head -2) "$FRAME_ASSEMBLER_PORT"; do
      local marker; marker="$(printf '%s-%s-%s' "$guest" "$iface" "$port")"
      if [ "$port" = "$FRAME_ASSEMBLER_PORT" ]; then
        local res; res="$("${s[@]}" shell "toybox nc -w 2 $HOST_ADDR $port </dev/null >/dev/null 2>&1 && echo connected || echo refused_or_timeout" | tr -d '\r')"
        echo "{\"guest\":\"$guest\",\"interface\":\"$iface\",\"host\":\"$HOST_ADDR\",\"port\":$port,\"protocol\":\"tcp\",\"marker\":\"$marker\",\"result\":\"$res\"}"
      else
        "${s[@]}" shell "echo -n MARK:$marker | toybox nc -u -w 1 $HOST_ADDR $port >/dev/null 2>&1" || true
        echo "{\"guest\":\"$guest\",\"interface\":\"$iface\",\"host\":\"$HOST_ADDR\",\"port\":$port,\"protocol\":\"udp\",\"marker\":\"MARK:$marker\",\"result\":\"sent\"}"
      fi
    done
  done
}

control_probe() {
  # The same method against the reachable control port, from the IVI VM.
  "$ADB" connect "$IVI_ADB" >/dev/null 2>&1 || true
  "$ADB" -s "$IVI_ADB" shell "echo -n CONTROL | toybox nc -u -w 1 $HOST_ADDR $CONTROL_PORT >/dev/null 2>&1" || true
}

run() {
  require_cmd ss tcpdump nc "$ADB" py || true
  host_listeners
  start_host_observers
  { probe_from_guest "$CORE_ADB" core; probe_from_guest "$IVI_ADB" ivi; } | py -c \
    'import sys,json; print(json.dumps([json.loads(l) for l in sys.stdin if l.strip()], indent=1))' \
    > "$OUT/probe_attempts.json"
  control_probe
  sleep 2
  stop_host_observers
  # Which markers reached the host: read the capture and the control file.
  py - "$OUT/host-guest-facing.pcap" "$OUT/control-received.txt" > "$OUT/host_capture_markers.json" <<'PY'
import json, sys
from de4sdv_broker_path_bench.pcap import read_pcap, datagrams
udp_markers, tcp_accepted = [], []
try:
    for d in datagrams(read_pcap(sys.argv[1])):
        if d.protocol == "udp" and b"MARK:" in d.payload:
            udp_markers.append(d.payload.split(b"MARK:", 1)[1].decode("ascii", "replace").strip())
except Exception as error:
    print(json.dumps({"error": str(error)})); sys.exit(0)
json.dump({"udp_markers": sorted(set(udp_markers)), "tcp_accepted": tcp_accepted}, sys.stdout, indent=1)
PY
  control="$(grep -c CONTROL "$OUT/control-received.txt" 2>/dev/null || echo 0)"
  printf '{"reached": %s, "detail": "control datagrams received: %s"}\n' \
    "$([ "${control:-0}" -gt 0 ] && echo true || echo false)" "${control:-0}" > "$OUT/control.json"
  log "probe artifacts in $OUT; evaluate with: python -m de4sdv_broker_path_bench.run $OUT --case VC-MW-017"
}

case "${1:-}" in
  run) run ;;
  *) echo "usage: $0 run <out-dir>" >&2; exit 2 ;;
esac
