#!/bin/bash
# Simulator host set-up of a P10-2 session (entry ENTRY_SIM_SETUP): the CARLA 1.0 server from the package that
# SIM20-G4 left on the G4's disk, started as in SIM20-G4's g4_vm.sh (off-screen, no sound, RPC port 2000, a systemd
# unit), plus the checks a recorded run needs first: free disk (brief R6) and NVENC at the recording size.
#
#   sim_setup.sh <out_dir>     exit 0 when the server answers; its versions and map in <out_dir>/server_probe.txt
#
# The world side (another lane's entry) sets synchronous mode and the fixed step of 0.05 s; this script does not.
set -uo pipefail
OUT=${1:?out dir}; mkdir -p "$OUT"
S=${SIM_ROOT:-/opt/sim20g4}; PY=${SIM_PY:-$S/venv/bin/python}; UNIT=${SIM_UNIT:-da-carla}
MIN_FREE_GB=${MIN_FREE_GB:-8}; SIM_WAIT_S=${SIM_WAIT_S:-120}
CR=$(cat "$S/carla_root" 2>/dev/null)
[ -x "$CR/CarlaUnreal.sh" ] || { echo "FAIL no CARLA package under $S (carla_root '$CR')"; exit 1; }
cp "$S/pkg.ok" "$OUT/package.ok" 2>/dev/null && echo "package: $(cat "$OUT/package.ok")"

FREE_G=$(df -BG --output=avail / | tail -1 | tr -dc 0-9)
echo "free on /: ${FREE_G} GiB (need $MIN_FREE_GB)"
[ "${FREE_G:-0}" -ge "$MIN_FREE_GB" ] || { echo "FAIL disk space"; exit 1; }
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader | tee "$OUT/gpu.txt"
if ffmpeg -hide_banner -loglevel error -f lavfi -i testsrc=size=1920x1080:rate=20 -t 1 -c:v h264_nvenc -preset p4 \
     -b:v 12M -pix_fmt yuv420p -f null - > "$OUT/nvenc_test.log" 2>&1; then
  echo "NVENC ok at 1920x1080, 20 fps"
else
  echo "NVENC FAILED: the chase recorder would fall back to libx264 on this host's CPU and says so in its summary"
fi

sudo systemctl stop "$UNIT" 2>/dev/null; sudo systemctl reset-failed "$UNIT" 2>/dev/null
pkill -9 -f "[C]arlaUnreal"; sleep 1
sudo systemd-run --uid="$(id -u)" --gid="$(id -g)" --unit="$UNIT" --setenv=HOME="$HOME" --working-directory="$CR" \
  bash -c "exec $CR/CarlaUnreal.sh -RenderOffScreen -nosound -carla-rpc-port=2000 > $OUT/server.log 2>&1" || exit 1
for _ in $(seq 1 120); do grep -q ":2000 " <(ss -ltn) && break; sleep 2; done
grep -q ":2000 " <(ss -ltn) || { echo "FAIL server port 2000"; exit 1; }
# the server listens before its world is loaded: ask for the world until SIM_WAIT_S (INC-DRIVING-001's hero check)
timeout $((SIM_WAIT_S + 60)) "$PY" -u - "$SIM_WAIT_S" > "$OUT/server_probe.txt" 2>&1 <<'PY'
import sys, time
import carla
wait_s = float(sys.argv[1]); t0 = time.monotonic()
while True:
    try:
        c = carla.Client("127.0.0.1", 2000); c.set_timeout(10.0); w = c.get_world()
        break
    except RuntimeError:
        if time.monotonic() - t0 > wait_s:
            raise
        time.sleep(2.0)
print("the simulator answered after %.1f s" % (time.monotonic() - t0))
print("server_version", c.get_server_version()); print("client_version", c.get_client_version())
s = w.get_settings()
print("map", w.get_map().name, "sync", s.synchronous_mode, "fixed_delta_seconds", s.fixed_delta_seconds)
PY
RC=$?
cat "$OUT/server_probe.txt"
systemctl is-active --quiet "$UNIT" || { echo "FAIL server unit not active"; exit 1; }
exit $RC
