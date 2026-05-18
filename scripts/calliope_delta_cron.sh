#!/usr/bin/env bash
# Calliope delta cron orchestrator — wrapper called by cron */6h.
# Reasons:
#  - cron cwd = $HOME, not repo. Need cd first.
#  - merge needs SPECIFIC last delta dir (from state file), not glob.
#  - error handling chained (set -e propagates).

set -euo pipefail

REPO=/home/nic/Scrivania/Calliope.AI
PY=/home/nic/anaconda3/bin/python
LOG=/tmp/discord_import/cron.log

cd "$REPO"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] === calliope_delta_cron.sh start ===" | tee -a "$LOG"

./scripts/discord_delta_export.sh

DELTA_DIR=$("$PY" -c "import json; print(json.load(open('.planning/last_dce_export.json'))['last_dir'])")
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Delta dir from state: $DELTA_DIR" | tee -a "$LOG"

"$PY" scripts/merge_delta_messages.py \
    --delta-dir "$DELTA_DIR" \
    --main-output datasets/discord_yokai/messages_clean.jsonl

./scripts/chromadb_incremental_hook.sh

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] === calliope_delta_cron.sh done ===" | tee -a "$LOG"
