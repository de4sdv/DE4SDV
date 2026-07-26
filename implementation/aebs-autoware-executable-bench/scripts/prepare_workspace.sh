#!/usr/bin/env bash
set -euo pipefail
BENCH="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$BENCH/workspace/src" "$BENCH/evidence"
docker compose -f "$BENCH/compose.yaml" run --rm bench bash -lc '
  set -eo pipefail
  source /opt/autoware/setup.bash
  set -u
  cd /de4sdv/implementation/aebs-autoware-executable-bench/workspace
  vcs import --skip-existing src < /de4sdv/implementation/aebs-autoware-executable-bench/autoware-009a.repos
  ln -sfn /de4sdv/implementation/aebs-autoware-executable-bench/src/de4sdv_aebs_bench src/de4sdv_aebs_bench
  vcs status src
'
# Source-import evidence is emitted only after the command succeeds; runtime gates
# enrich it with image/map identities rather than implying launch success.
python3 - "$BENCH" <<'PY'
import datetime,hashlib,json,platform,subprocess,sys,yaml
from pathlib import Path
b=Path(sys.argv[1]); lock=b/'runtime-lock.yaml'; data=yaml.safe_load(lock.read_text())
head=subprocess.run(['git','rev-parse','HEAD'],cwd=b.parents[1],text=True,capture_output=True)
out={'utc_time':datetime.datetime.now(datetime.timezone.utc).isoformat(),'host_architecture':platform.machine(),'repository_head':head.stdout.strip() if head.returncode==0 else None,'lock_sha256':hashlib.sha256(lock.read_bytes()).hexdigest(),'map_sha256':data['map']['sha256'],'image_id':None,'image_digest':data['container']['index_digest'],'command_exit_status':0}
(b/'evidence/source-import.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
PY
python3 "$BENCH/scripts/record_source_heads.py" \
  "$BENCH" "$BENCH/evidence/source-import.json"
