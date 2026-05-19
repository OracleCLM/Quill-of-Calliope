#!/usr/bin/env bash
# Calliope Discord bot heartbeat — health check + auto-restart on crash
# Usage: bash scripts/discord_bot_heartbeat.sh [--once]
set -euo pipefail

REPO=/home/nic/Scrivania/Quill_of_Calliope
LOG=/tmp/calliope_discord_bot.log
PID_FILE=/tmp/calliope_discord_bot.pid
BOT_SCRIPT="$REPO/scripts/discord_bot.py"
CHECK_INTERVAL=30  # seconds

_is_running() {
    if [ -f "$PID_FILE" ]; then
        local pid
        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
    fi
    # Fallback: pgrep
    pgrep -f "discord_bot.py" >/dev/null 2>&1
}

_start_bot() {
    echo "[heartbeat] Starting Calliope Discord bot..."
    cd "$REPO"
    nohup python3 "$BOT_SCRIPT" >> "$LOG" 2>&1 &
    echo $! > "$PID_FILE"
    echo "[heartbeat] Bot started PID=$(cat "$PID_FILE")"
}

_check_once() {
    if _is_running; then
        echo "[heartbeat] Bot running (OK)"
    else
        echo "[heartbeat] Bot NOT running — restarting..."
        _start_bot
    fi
}

if [ "${1:-}" = "--once" ]; then
    _check_once
    exit 0
fi

echo "[heartbeat] Starting monitor loop (interval=${CHECK_INTERVAL}s)"
while true; do
    _check_once
    sleep "$CHECK_INTERVAL"
done
