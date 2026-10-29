#!/usr/bin/env bash
# Reachability check of REQ-MW-016's second finding: confirm the host DDS ports
# stay unreachable from every guest domain. Defensive verification of isolation
# with standard tools. It records artifacts for the evaluator
# (de4sdv_broker_path_bench.probe); the evaluator, not this script, returns the
# verdict. A pass means the probes did NOT reach a host socket.
#
#   host_isolation_probe.sh run <out-dir>   list, probe from both VMs over every interface, record
#
# Reachability is judged by the authoritative host signal, not a pre-netfilter
# capture: a UDP probe reached the host when the DDS drop-rule counter did NOT
# move for it (read once per probe, serialized); the positive control is a host
# listener on a port with no drop rule. A TCP probe reached when the guest
# connected and the host shows the connection. It probes the full DDS port set
# and 4721, from each VM over each interface, with an explicit source address,
# to each host address. It assumes launch_two_vms.sh is up and
# host_isolation_firewall.sh add is in place.
set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/bench_env.sh"
OUT="${2:?usage: $0 run <out-dir>}"; mkdir -p "$OUT"
: "${CONTROL_PORT:=39999}"       # a host UDP port with no drop rule, for the positive control
TABLE_INET="de4sdv_bench"

py() { PYTHONPATH="$HERE/../src" python3 "$@"; }

host_listeners() {
  { ss -H -u -l -n -p 2>/dev/null; ss -H -t -l -n -p 2>/dev/null; } > "$OUT/ss_listeners.txt" 2>&1
  py - "$OUT/ss_listeners.txt" > "$OUT/host_listeners.json" <<'PY'
import json, re, sys
rows = []
for line in open(sys.argv[1]):
    parts = line.split()
    if len(parts) < 5:
        continue
    proto = "udp" if parts[0].lower() in ("udp", "unconn") else "tcp"
    m = re.search(r"(\d+\.\d+\.\d+\.\d+|\[[0-9a-f:]+\]|\*):(\d+)\b", parts[4])
    if not m:
        continue
    users = re.search(r'users:\(\("([^"]+)"', line)
    proc = users.group(1) if users else ""
    rows.append({"address": m.group(1), "port": int(m.group(2)), "protocol": proto, "element": proc,
                 "element_in_layer": any(k in proc for k in ("adapter", "health_proxy", "de4sdv_score"))})
json.dump(rows, open("/dev/stdout", "w"), indent=1)
PY
  log "recorded host listeners in $OUT/host_listeners.json"
}

dds_ports_expanded() {
  local token first last
  for token in $(dds_udp_port_set); do
    if printf '%s' "$token" | grep -q '-'; then
      first="${token%-*}"; last="${token#*-}"; seq "$first" "$last"
    else echo "$token"; fi
  done
}

drop_counter_packets() {
  # The packet count of the inet DDS drop rule (one counter for the whole set).
  sudo nft -a list table inet "$TABLE_INET" 2>/dev/null \
    | awk '/DDS d|DDS ports off the guest/ && /counter/ {for(i=1;i<=NF;i++) if($i=="packets") print $(i+1)}' | head -1
}

guest_cmd() { local serial="$1"; shift; "$ADB" -s "$serial" shell "$@"; }

probe_guest() {
  local serial="$1" guest="$2"
  "$ADB" connect "$serial" >/dev/null 2>&1 || true
  "$ADB" -s "$serial" root >/dev/null 2>&1 || true
  local ifaces addrs probed_if="" probed_addr=""
  ifaces="$(guest_cmd "$serial" "ip -o addr show | awk '{print \$2}'" | tr -d '\r' | sort -u)"
  addrs="$HOST_ADDR"   # extend with the buried host ends and other cvd-* bridge addresses per the run
  : "${PROBE_HOST_ADDRS:=$addrs}"
  local iface addr port src before after reached marker
  for iface in $ifaces; do
    probed_if="$probed_if $iface"
    src="$(guest_cmd "$serial" "ip -o -4 addr show dev $iface | awk '{print \$4}' | cut -d/ -f1 | head -1" | tr -d '\r')"
    [ -n "$src" ] || continue
    for addr in $PROBE_HOST_ADDRS; do
      case " $probed_addr " in *" $addr "*) : ;; *) probed_addr="$probed_addr $addr" ;; esac
      # DDS UDP ports: serialize, read the drop counter around each probe.
      for port in $(dds_ports_expanded); do
        marker="${guest}-${iface}-${addr}-${port}"
        before="$(drop_counter_packets)"
        guest_cmd "$serial" "echo -n MARK:$marker | toybox nc -s $src -u -w 1 $addr $port >/dev/null 2>&1" || true
        after="$(drop_counter_packets)"
        reached=false
        if [ -n "$before" ] && [ -n "$after" ] && [ "$before" = "$after" ]; then reached=true; fi
        printf '{"guest":"%s","interface":"%s","src_addr":"%s","host":"%s","port":%s,"protocol":"udp","marker":"MARK:%s","result":"sent"}\n' \
          "$guest" "$iface" "$src" "$addr" "$port" "$marker" >> "$OUT/attempts.ndjson"
        [ "$reached" = true ] && printf 'MARK:%s\n' "$marker" >> "$OUT/udp_reached.txt"
      done
      # Port 4721 (TCP): the guest connect result; the host established side is the authority.
      marker="${guest}-${iface}-${addr}-${FRAME_ASSEMBLER_PORT}"
      if guest_cmd "$serial" "toybox nc -s $src -w 2 $addr $FRAME_ASSEMBLER_PORT </dev/null >/dev/null 2>&1"; then
        if ss -H -t -n state established "( sport = :$FRAME_ASSEMBLER_PORT )" 2>/dev/null | grep -q "$src"; then
          printf '{"port":%s,"guest":"%s","src_addr":"%s"}\n' "$FRAME_ASSEMBLER_PORT" "$guest" "$src" >> "$OUT/tcp_reached.ndjson"
        fi
      fi
      printf '{"guest":"%s","interface":"%s","src_addr":"%s","host":"%s","port":%s,"protocol":"tcp","marker":"%s","result":"attempted"}\n' \
        "$guest" "$iface" "$src" "$addr" "$FRAME_ASSEMBLER_PORT" "$marker" >> "$OUT/attempts.ndjson"
    done
  done
  # Coverage record for this guest.
  py - "$OUT/coverage_${guest}.json" "$guest" "$probed_if" "$probed_addr" "$PROBE_HOST_ADDRS" "$ifaces" <<'PY'
import json, sys
out, guest, probed_if, probed_addr, expected_addr, expected_if = sys.argv[1:7]
json.dump({"guest": guest, "probed_interfaces": probed_if.split(), "probed_host_addresses": probed_addr.split(),
           "expected_interfaces": expected_if.split(), "expected_host_addresses": expected_addr.split()},
          open(out, "w"), indent=1)
PY
}

control_probe() {
  # A host listener on a port with no drop rule; the IVI sends a marker to it.
  ( timeout 60 toybox nc -u -l -p "$CONTROL_PORT" > "$OUT/control-received.txt" 2>/dev/null & echo $! > "$OUT/.control.pid" ) || true
  sleep 1
  "$ADB" connect "$IVI_ADB" >/dev/null 2>&1 || true
  "$ADB" -s "$IVI_ADB" shell "echo -n CONTROL | toybox nc -u -w 1 $HOST_ADDR $CONTROL_PORT >/dev/null 2>&1" || true
  sleep 1
  [ -f "$OUT/.control.pid" ] && kill "$(cat "$OUT/.control.pid")" 2>/dev/null || true
}

asm_mw_031() {
  # Each host ROS 2 process: its RMW, domain and CYCLONEDDS_URI, from /proc.
  py - "$OUT/asm_mw_031.json" "$OUT/ss_listeners.txt" <<'PY'
import glob, json, os, sys
envs = []
for environ in glob.glob("/proc/[0-9]*/environ"):
    try:
        data = dict(kv.split("=", 1) for kv in open(environ).read().split("\0") if "=" in kv)
    except OSError:
        continue
    if "RMW_IMPLEMENTATION" in data or "ROS_DOMAIN_ID" in data:
        envs.append({"rmw": data.get("RMW_IMPLEMENTATION"), "domain": data.get("ROS_DOMAIN_ID"),
                     "uri": data.get("CYCLONEDDS_URI"), "localhost_only": data.get("ROS_LOCALHOST_ONLY")})
rmws = {e["rmw"] for e in envs if e["rmw"]}
domains = {e["domain"] for e in envs if e["domain"]}
holds = len(envs) > 0 and rmws == {"rmw_cyclonedds_cpp"} and domains == {"91"}
json.dump({"holds": holds, "processes": envs, "detail": f"rmws={sorted(rmws)} domains={sorted(domains)}"},
          open(sys.argv[1], "w"), indent=1)
PY
}

run() {
  require_cmd ss "$ADB" py toybox || true
  : > "$OUT/attempts.ndjson"; : > "$OUT/udp_reached.txt"; : > "$OUT/tcp_reached.ndjson"
  host_listeners
  sudo nft list table inet "$TABLE_INET" > "$OUT/nft_before.txt" 2>&1 || true
  control_probe
  probe_guest "$CORE_ADB" core
  probe_guest "$IVI_ADB" ivi
  sudo nft list table inet "$TABLE_INET" > "$OUT/nft_after.txt" 2>&1 || true
  asm_mw_031
  # Assemble the evaluator's artifacts.
  py - "$OUT" <<'PY'
import json, os, sys
out = sys.argv[1]
attempts = [json.loads(l) for l in open(os.path.join(out, "attempts.ndjson")) if l.strip()]
json.dump(attempts, open(os.path.join(out, "probe_attempts.json"), "w"), indent=1)
udp = sorted({l.strip() for l in open(os.path.join(out, "udp_reached.txt")) if l.strip()})
tcp = [json.loads(l) for l in open(os.path.join(out, "tcp_reached.ndjson")) if l.strip()]
json.dump({"udp_markers": udp, "tcp_connects": tcp}, open(os.path.join(out, "host_socket_receipts.json"), "w"), indent=1)
control = os.path.join(out, "control-received.txt")
reached = os.path.exists(control) and "CONTROL" in open(control, errors="replace").read()
json.dump({"reached": reached, "detail": f"control datagram received: {reached}"},
          open(os.path.join(out, "control.json"), "w"), indent=1)
per_guest = {}
for guest in ("core", "ivi"):
    path = os.path.join(out, f"coverage_{guest}.json")
    if os.path.exists(path):
        per_guest[guest] = json.load(open(path))
json.dump({"per_guest": per_guest}, open(os.path.join(out, "coverage.json"), "w"), indent=1)
PY
  log "probe artifacts in $OUT; evaluate with: python -m de4sdv_broker_path_bench.run $OUT --case VC-MW-017"
  log "NOTE: also stop the frame assembler or re-run the ss client check (ASM-MW-029): a connect to :4721 takes the stream from the adapter."
}

case "${1:-}" in
  run) run ;;
  *) echo "usage: $0 run <out-dir>" >&2; exit 2 ;;
esac
