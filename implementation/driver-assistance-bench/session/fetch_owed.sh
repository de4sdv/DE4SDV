#!/bin/bash
# fetch_owed.sh <incoming_<id> folder>: the hand fetch of the simulator host's pack that a session left on the host
# (session.json not_fetched "sim: ~/da-kit/<id>/out.tgz sha256 <sha> <bytes> B (fetch owed...)"; README "A fetch
# owed"). Modelled on the lead's fetch of 20261120T092051Z (sim-lead-fetch/fetch_g4_ranges.sh): refuse unless the
# simulator host reads TERMINATED and no da-session-* unit is loaded; start it alone (no capacity: again every
# 3 min, for 1 h at most); read the pack as ranges over parallel IAP tunnels (dd on the host, nothing written there),
# each range size-checked, 3 tries; join them in order; compare the sha256 with the session's; unpack and check the
# session id; stop the host in the EXIT trap and read TERMINATED back. The whole ranges the session kept in
# <role>/.ranges stay when their pack file names the same sha256; only the others are read.
# Writes sim/out.tgz, sim/out/, sim/fetch_owed_ranges.tsv and sim/fetch_owed.json in the incoming folder.
# The sha256 and size come from session.json fetch.sim (FETCH_OWED_SHA, FETCH_OWED_BYTES override them: a fetch a
# signal cut has none; read them on the host first, `sha256sum ~/da-kit/<id>/out.tgz; stat -c %s ...`).
# Exit: 0 fetched and checked; 2 refused; 3 no start or no SSH; 4 a range failed; 5 the sha256 or the files differ.
set -u
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=hosts.env
. "$HERE/hosts.env"
IN=$(cd -- "${1:?usage: fetch_owed.sh <incoming_<id> folder>}" && pwd) || exit 2
GC=${FETCH_OWED_GCLOUD:-$HOME/google-cloud-sdk/bin/gcloud}
PAUSE_S=${FETCH_OWED_PAUSE_S:-180}; SSH_PAUSE_S=${FETCH_OWED_SSH_PAUSE_S:-10}; TRY_S=${FETCH_OWED_TRY_S:-600}
g() { env -u PYTHONPATH "$GC" --configuration="$GCLOUD_CONFIGURATION" --project="$SIM_PROJECT" "$@"; }
status() { g compute instances describe "$SIM_VM" --zone "$SIM_ZONE" --format='value(status)' 2>/dev/null; }

read -r SID SHA SIZE <<< "$(python3 - "$IN/session.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
f = (d.get("fetch") or {}).get("sim") or {}
print(d.get("session_id") or "-", f.get("sha256") or "-", f.get("bytes") or "-")
PY
)"
SHA=${FETCH_OWED_SHA:-$SHA}; SIZE=${FETCH_OWED_BYTES:-$SIZE}
[[ "$SID" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || { echo "refused: no session id in $IN/session.json"; exit 2; }
[[ "$SHA" =~ ^[0-9a-f]{64}$ ]] && [[ "$SIZE" =~ ^[0-9]+$ ]] \
  || { echo "refused: no sha256 and size of the pack in session.json fetch.sim (FETCH_OWED_SHA, FETCH_OWED_BYTES)"; exit 2; }
D=$IN/sim/.ranges; mkdir -p "$D" || exit 2
MIB=$FETCH_RANGE_MIB
if [ -f "$D/pack" ]; then
  read -r psha psize pmib < "$D/pack"
  [ "$psha" = "$SHA" ] && [ "$psize" = "$SIZE" ] \
    || { echo "refused: $D holds ranges of another pack ($psha); move them aside first"; exit 2; }
  MIB=$pmib
else
  echo "$SHA $SIZE $MIB" > "$D/pack"
fi
[[ "$MIB" =~ ^[1-9][0-9]*$ ]] || { echo "refused: range size '$MIB' MiB"; exit 2; }

st=$(status)
echo "before: $SIM_VM $st $(date -u +%FT%TZ)"
[ "$st" = TERMINATED ] || { echo "refused: $SIM_VM is '$st', not TERMINATED"; exit 2; }
units=$(systemctl --user list-units 'da-session-*' --no-legend 2>/dev/null) \
  || { echo "refused: the user units cannot be listed (systemctl --user)"; exit 2; }
[ -z "$units" ] || { echo "refused: a da-session unit is loaded: $units"; exit 2; }

stop_vm() {
  g compute instances stop "$SIM_VM" --zone "$SIM_ZONE" --quiet > /dev/null 2>&1
  echo "after: $(status) $(date -u +%FT%TZ)"
}
trap stop_vm EXIT
deadline=$(( $(date +%s) + 3600 ))
while :; do
  out=$(g compute instances start "$SIM_VM" --zone "$SIM_ZONE" --quiet 2>&1) && break
  case "$out" in
    *ZONE_RESOURCE_POOL_EXHAUSTED*|*STOCKOUT*|*"not have enough resources"*) ;;
    *) echo "start failed: $out"; exit 3 ;;
  esac
  [ "$(date +%s)" -lt "$deadline" ] || { echo "no capacity within 1 h"; exit 3; }
  echo "no capacity $(date -u +%FT%TZ): again in $PAUSE_S s"; sleep "$PAUSE_S"
done
ok=""
for _ in $(seq 1 30); do
  g compute ssh "$SIM_VM" --zone "$SIM_ZONE" --tunnel-through-iap --command true < /dev/null > /dev/null 2>&1 && { ok=1; break; }
  sleep "$SSH_PAUSE_S"
done
[ -n "$ok" ] || { echo "no ssh"; exit 3; }

N=$(( (SIZE + MIB * 1048576 - 1) / (MIB * 1048576) ))
TSV=$IN/sim/fetch_owed_ranges.tsv; [ -s "$TSV" ] || printf 'range\ttry\tstart_s\tend_s\tbytes\twant\tresult\n' > "$TSV"
range() {   # range <index>: FETCH_OWED_TRY_S per try, 3 tries, size-checked
  local i=$1 f want t s e got
  f=$D/$(printf 'p%06d' "$i"); want=$(( SIZE - i * MIB * 1048576 )); [ "$want" -gt $(( MIB * 1048576 )) ] && want=$(( MIB * 1048576 ))
  for t in 1 2 3; do
    s=$(date +%s.%N)
    timeout "$TRY_S" env -u PYTHONPATH "$GC" --configuration="$GCLOUD_CONFIGURATION" --project="$SIM_PROJECT" compute ssh \
      "$SIM_VM" --zone "$SIM_ZONE" --tunnel-through-iap --ssh-flag=-T \
      --command "dd if=\$HOME/da-kit/$SID/out.tgz bs=1M skip=$(( i * MIB )) count=$MIB status=none" < /dev/null > "$f.part" 2>/dev/null
    e=$(date +%s.%N); got=$(stat -c %s "$f.part" 2>/dev/null || echo 0)
    if [ "$got" = "$want" ]; then
      mv "$f.part" "$f"; printf '%s\t%s\t%s\t%s\t%s\t%s\tok\n' "$i" "$t" "$s" "$e" "$got" "$want" >> "$TSV"; return 0
    fi
    printf '%s\t%s\t%s\t%s\t%s\t%s\tshort\n' "$i" "$t" "$s" "$e" "$got" "$want" >> "$TSV"
  done
  rm -f "$f.part"; echo "range $i failed after 3 tries"; return 1
}
export -f range; export GC GCLOUD_CONFIGURATION SIM_PROJECT SIM_VM SIM_ZONE SID SIZE MIB D TSV TRY_S
todo=(); kept=0
for (( i = 0; i < N; i++ )); do
  if [ -f "$D/$(printf 'p%06d' "$i")" ]; then kept=$(( kept + 1 )); else todo+=("$i"); fi
done
t0=$(date +%s)
echo "ranges: $N of $MIB MiB, $kept kept from the session, ${#todo[@]} to read, $FETCH_PARALLEL in parallel, start $(date -u +%FT%TZ)"
rc=0
if [ ${#todo[@]} -gt 0 ]; then
  printf '%s\n' "${todo[@]}" | xargs -P "$FETCH_PARALLEL" -I{} bash -c 'range {}' || rc=4
fi
secs=$(( $(date +%s) - t0 ))
result=ok
for (( i = 0; i < N; i++ )); do [ -f "$D/$(printf 'p%06d' "$i")" ] || { result="range $i missing"; rc=4; }; done
if [ "$rc" = 0 ]; then
  cat "$D"/p[0-9][0-9][0-9][0-9][0-9][0-9] > "$IN/sim/out.tgz"
  got=$(sha256sum "$IN/sim/out.tgz" | cut -c1-64)
  echo "local: $(stat -c %s "$IN/sim/out.tgz") $got"
  if [ "$got" != "$SHA" ]; then echo "SHA MISMATCH (want $SHA)"; result="sha256 $got"; rc=5
  else
    echo "SHA OK"
    if tar -xzf "$IN/sim/out.tgz" -C "$IN/sim" && [ "$(cat "$IN/sim/out/session_id" 2>/dev/null)" = "$SID" ]; then
      rm -rf "$D"
    else result="not this session's files"; rc=5; fi
  fi
fi
python3 - "$IN/sim/fetch_owed.json" "$SHA" "$SIZE" "$N" "$kept" "${#todo[@]}" "$MIB" "$FETCH_PARALLEL" "$secs" "$result" <<'PY'
import json, sys
a = sys.argv
json.dump({"sha256": a[2], "bytes": int(a[3]), "ranges": int(a[4]), "kept_from_session": int(a[5]),
           "read_now": int(a[6]), "range_mib": int(a[7]), "parallel": int(a[8]), "seconds": int(a[9]),
           "result": a[10], "ranges_file": "sim/fetch_owed_ranges.tsv"}, open(a[1], "w"), indent=1)
PY
echo "fetch owed: $result ($secs s)"
exit "$rc"
