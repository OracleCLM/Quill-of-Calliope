#!/usr/bin/env bash
# Discord delta export wrapper — sources .env, reads/writes last_dce_export.json
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="/tmp/discord_import/delta_export.log"
STATE_FILE="$PROJECT_DIR/.planning/last_dce_export.json"
DCE="${HOME}/.local/bin/dce"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$LOG_FILE"; }

mkdir -p /tmp/discord_import
mkdir -p "$(dirname "$LOG_FILE")"

log "=== discord_delta_export.sh start ==="

# Source .env
if [[ -f "$PROJECT_DIR/.env" ]]; then
    set -a; source "$PROJECT_DIR/.env"; set +a
fi

# Validate required vars
if [[ -z "${DISCORD_USER_TOKEN:-}" ]]; then
    log "ERROR: DISCORD_USER_TOKEN not set"; exit 1
fi
if [[ -z "${KOY_GUILD_ID:-}" ]]; then
    log "ERROR: KOY_GUILD_ID not set"; exit 1
fi

# Read last export timestamp (default: epoch)
if [[ -f "$STATE_FILE" ]]; then
    LAST_TS=$(python3 -c "import json,sys; d=json.load(open('$STATE_FILE')); print(d.get('last_ts','1970-01-01T00:00:00Z'))" 2>/dev/null || echo "1970-01-01T00:00:00Z")
else
    LAST_TS="1970-01-01T00:00:00Z"
fi
log "Last export timestamp: $LAST_TS"

# Create timestamped output dir
EPOCH=$(date +%s)
OUT_DIR="/tmp/discord_import/delta_${EPOCH}"
mkdir -p "$OUT_DIR"
log "Output dir: $OUT_DIR"

# Run DCE export
log "Running DCE delta export after $LAST_TS..."
if "$DCE" exportguild \
    -t "$DISCORD_USER_TOKEN" \
    -g "$KOY_GUILD_ID" \
    -f Json \
    --include-threads All \
    --media \
    --utc \
    --after "$LAST_TS" \
    --fuck-russia \
    -o "$OUT_DIR/" 2>&1 | tee -a "$LOG_FILE"; then
    log "DCE export succeeded."
else
    log "ERROR: DCE export failed (exit $?)"
    exit 1
fi

# Atomic update of state file
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
TMP_STATE="${STATE_FILE}.tmp.$$"
python3 -c "import json; json.dump({'last_ts': '$NOW', 'last_dir': '$OUT_DIR'}, open('$TMP_STATE','w'))"
mv "$TMP_STATE" "$STATE_FILE"
log "State updated: last_ts=$NOW"

log "=== discord_delta_export.sh done ==="
exit 0
