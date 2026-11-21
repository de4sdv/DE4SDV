#!/bin/bash
# DE4SDV driver-assistance bench (INC-DRIVING-002): the S-CORE host's disk check before the first run of a p10-2
# (ENTRY_SCORE_DISK of session/entrypoints.env; contract in session/README.md "Entry-point contracts").
#
#   disk_check.sh <out> <need_bytes> <need_stage_bytes>
#
# The candidate writes its Rerun record (rrd_on = true, the model's: the evaluators' record of the warnings) into its
# working directory in the stage, and stop_score_side.sh keeps it on this host: a hard link in <out> where the stage
# and <out> share a filesystem, a copy otherwise. The session computes the need from the highest record rate
# (calib_steer of 20261119T174606Z: 4,729,613,610 B in 542 passes, at most 10 passes a second, rounded up to
# 88 MB/s) times the planned running
# seconds: <need_bytes> for every run of the session (held in <out>'s filesystem), <need_stage_bytes> for the longest
# run (held in the stage's filesystem until the next start). On one filesystem the need is <need_bytes>; on two, each
# filesystem's own. Nothing is deleted to make room.
#
# Writes <out>/disk_check.json and one line `DISK_CHECK ok|short need_bytes=.. avail_bytes=.. same_filesystem=0|1 ..`.
# Exit status: 0 enough space; 2 usage; 9 short ("DISK SPACE SHORT", named, before any run starts).
set -uo pipefail
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=lib_score_side.sh
. "$HERE/lib_score_side.sh"

OUT=${1:?usage: disk_check.sh <out> <need_bytes> <need_stage_bytes>}
NEED=${2:?usage: disk_check.sh <out> <need_bytes> <need_stage_bytes>}
NEED_STAGE=${3:?usage: disk_check.sh <out> <need_bytes> <need_stage_bytes>}
[[ "$NEED" =~ ^[0-9]+$ ]] && [[ "$NEED_STAGE" =~ ^[0-9]+$ ]] || { echo "disk_check: the needs must be whole bytes"; exit 2; }
mkdir -p "$OUT" || exit 2
# the stage may not exist yet: its nearest existing parent is on the filesystem it will be on
s=$DA_STAGE; while [ ! -e "$s" ] && [ "$s" != / ]; do s=$(dirname "$s"); done
fs() { df -P -B1 "$1" 2>/dev/null | awk 'NR == 2 { print $4, $6 }'; }   # avail bytes, mount point
read -r out_avail out_mount <<< "$(fs "$OUT")"
read -r st_avail st_mount <<< "$(fs "$s")"
[ -n "${out_avail:-}" ] && [ -n "${st_avail:-}" ] || { echo "DISK_CHECK short reason=no_df_answer"; echo "DISK SPACE SHORT: df gave no answer for $OUT or $s"; exit 9; }
if [ "$(stat -c %d "$OUT")" = "$(stat -c %d "$s")" ]; then
  same=1; enough=$([ "$out_avail" -ge "$NEED" ] && echo true || echo false)
else
  same=0; enough=$([ "$out_avail" -ge "$NEED" ] && [ "$st_avail" -ge "$NEED_STAGE" ] && echo true || echo false)
fi
cat > "$OUT/disk_check.json" <<EOF
{"need_bytes": $NEED, "need_stage_bytes": $NEED_STAGE, "out": "$OUT", "out_mount": "$out_mount",
 "avail_bytes": $out_avail, "stage": "$DA_STAGE", "stage_mount": "$st_mount", "stage_avail_bytes": $st_avail,
 "same_filesystem": $([ "$same" = 1 ] && echo true || echo false), "enough": $enough}
EOF
words="need_bytes=$NEED avail_bytes=$out_avail same_filesystem=$same out_mount=$out_mount need_stage_bytes=$NEED_STAGE stage_avail_bytes=$st_avail stage_mount=$st_mount"
if [ "$enough" = true ]; then
  ss_log "DISK_CHECK ok $words"
  exit 0
fi
ss_log "DISK_CHECK short $words"
ss_log "DISK SPACE SHORT: the candidate's Rerun records of this session need $NEED B on $out_mount ($out_avail B free)$([ "$same" = 0 ] && echo " and $NEED_STAGE B on $st_mount ($st_avail B free)"); no run starts, and nothing is deleted"
exit 9
