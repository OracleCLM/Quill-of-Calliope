#!/usr/bin/env bash
# ChromaDB incremental indexing hook — runs after merge_delta_messages.py
# Uses build_chromadb_index.py --incremental (skip already-indexed chunks)
# and optionally --since-id <last_msg_id> from .planning/last_chroma_index.json
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_PYTHON="${VENV_PYTHON:-/tmp/calliope_venv/bin/python}"
STATE_FILE="$PROJECT_DIR/.planning/last_chroma_index.json"
LOG_FILE="/tmp/discord_import/chroma_hook.log"
MESSAGES_FILE="$PROJECT_DIR/datasets/discord_yokai/messages_clean.jsonl"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$LOG_FILE"; }

mkdir -p "$(dirname "$LOG_FILE")"
log "=== chromadb_incremental_hook.sh start ==="

# Source .env
if [[ -f "$PROJECT_DIR/.env" ]]; then
    set -a; source "$PROJECT_DIR/.env"; set +a
fi

if [[ ! -f "$MESSAGES_FILE" ]]; then
    log "WARNING: $MESSAGES_FILE not found — nothing to index"; exit 0
fi

# Read last indexed message_id (for --since-id optimization)
SINCE_ID_ARG=""
if [[ -f "$STATE_FILE" ]]; then
    SINCE_ID=$(python3 -c "
import json, sys
d = json.load(open('$STATE_FILE'))
sid = d.get('last_indexed_msg_id')
if sid: print(sid)
" 2>/dev/null || true)
    if [[ -n "${SINCE_ID:-}" ]]; then
        SINCE_ID_ARG="--since-id $SINCE_ID"
        log "Using --since-id $SINCE_ID"
    fi
fi

log "Running incremental ChromaDB index..."
cd "$PROJECT_DIR"
"$VENV_PYTHON" scripts/build_chromadb_index.py \
    --input "$MESSAGES_FILE" \
    --incremental \
    ${SINCE_ID_ARG} \
    2>&1 | tee -a "$LOG_FILE"

# Record last message_id as optimization for next run
LAST_ID=$(tail -1 "$MESSAGES_FILE" | python3 -c "import json,sys; print(json.loads(sys.stdin.read()).get('message_id',''))" 2>/dev/null || true)
if [[ -n "${LAST_ID:-}" ]]; then
    TMP_STATE="${STATE_FILE}.tmp.$$"
    python3 -c "import json; json.dump({'last_indexed_msg_id': '$LAST_ID'}, open('$TMP_STATE','w'))"
    mv "$TMP_STATE" "$STATE_FILE"
    log "State updated: last_indexed_msg_id=$LAST_ID"
fi

log "=== chromadb_incremental_hook.sh done ==="
exit 0
