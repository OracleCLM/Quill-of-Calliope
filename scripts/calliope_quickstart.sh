#!/usr/bin/env bash
set -euo pipefail

REPO=/home/nic/Scrivania/Quill_of_Calliope
LOG_DIR=/tmp/quill_of_calliope
mkdir -p "$LOG_DIR"
cd "$REPO"

echo "═══════════════════════════════════════════════"
echo "      Quill of Calliope — QuickStart"
echo "═══════════════════════════════════════════════"
echo

# 1. LLM gateway :8766
if curl -sf http://localhost:8766/health >/dev/null 2>&1; then
  echo "  [ok] LLM gateway già attivo :8766"
else
  echo "  [>>] Avvio LLM gateway..."
  nohup python3 scripts/llm_gateway_http.py >> "$LOG_DIR/gateway.log" 2>&1 &
  disown
  sleep 2
fi

# 2. SillyTavern :8001
if curl -sf http://localhost:8001/ >/dev/null 2>&1; then
  echo "  [ok] SillyTavern già attivo :8001"
else
  echo "  [>>] Avvio SillyTavern (cold start ~5s)..."
  (cd external/sillytavern && nohup bash start.sh >> "$LOG_DIR/sillytavern.log" 2>&1 & disown)
  sleep 6
fi

# 3. Mascot WS :9876
if [ -f scripts/mascot_ws_server.py ]; then
  if ss -ltn 2>/dev/null | grep -q :9876; then
    echo "  [ok] Mascot WS già attivo :9876"
  else
    echo "  [>>] Avvio Mascot WS..."
    nohup python3 scripts/mascot_ws_server.py --port 9876 >> "$LOG_DIR/mascot_ws.log" 2>&1 &
    disown
    sleep 1
  fi
else
  echo "  [--] mascot_ws_server.py non trovato — skip"
fi

# 4. Flask shell :5000
if curl -sf http://localhost:5000/health >/dev/null 2>&1; then
  echo "  [ok] Flask shell già attivo :5000"
else
  echo "  [>>] Avvio Flask shell..."
  nohup python3 -m app.calliope_shell.server >> "$LOG_DIR/flask_shell.log" 2>&1 &
  disown
  sleep 3
fi

echo
echo "── Verifica salute servizi ──"

# Post-launch health check con ✓/✗
declare -A SERVICES=(
  ["Gateway"]="http://localhost:8766/health"
  ["SillyTavern"]="http://localhost:8001/"
  ["Mascot WS"]="http://localhost:9876/health"
  ["Flask shell"]="http://localhost:5000/health"
)
declare -A SERVICE_ORDER=(["1"]="Gateway" ["2"]="SillyTavern" ["3"]="Mascot WS" ["4"]="Flask shell")

ALL_OK=true
for i in 1 2 3 4; do
  name="${SERVICE_ORDER[$i]}"
  url="${SERVICES[$name]}"
  if curl -sf --max-time 3 "$url" >/dev/null 2>&1; then
    printf "  ✓ %-12s %s\n" "$name" "$url"
  else
    printf "  ✗ %-12s %s (NON RAGGIUNGIBILE)\n" "$name" "$url"
    ALL_OK=false
  fi
done

echo
echo "═══════════════════════════════════════════════"
if $ALL_OK; then
  echo "  ✓ Stack avviato — apri http://localhost:5000/"
else
  echo "  ⚠ Stack parziale — controlla i log in $LOG_DIR/"
fi
echo "═══════════════════════════════════════════════"
echo
echo "  Logs:  $LOG_DIR/"
echo "  Stop:  bash scripts/stop_all_calliope_daemons.sh"
echo

# Browser auto-open (solo se DISPLAY + stack completo)
if [ -n "${DISPLAY:-}" ] && $ALL_OK; then
  echo "  Apro browser su http://localhost:5000/ ..."
  (xdg-open http://localhost:5000/ >/dev/null 2>&1 &)
elif [ -z "${DISPLAY:-}" ]; then
  echo "  (DISPLAY non set — apri manualmente http://localhost:5000/)"
fi
