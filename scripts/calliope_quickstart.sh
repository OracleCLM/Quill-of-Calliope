#!/usr/bin/env bash
# setup-or-heal – script idempotente per avviare o verificare lo stack Calliope
# ------------------------------------------------------------
# Requisiti:
#   - venv in .venv (python interpreter .venv/bin/python)
#   - requirements.txt al root del repo
#   - 4 servizi (gateway, SillyTavern, Mascot WS, Flask shell)
#   - log in /tmp/quill_of_calliope/
#   - flag opzionale --fix per creare venv e installare dipendenze
# ------------------------------------------------------------

set -euo pipefail

# ---------- Configurazione di base ----------
# Cartella radice del repository (assunta come padre di questo script)
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$REPO/.venv/bin/python"
LOG_DIR="/tmp/quill_of_calliope"
mkdir -p "$LOG_DIR"

# Flag --fix
FIX=false
for arg in "$@"; do
  if [[ "$arg" == "--fix" ]]; then
    FIX=true
  fi
done

# ---------- Funzioni di utilità ----------
print_banner() {
  echo "═══════════════════════════════════════════════"
  echo "      Quill of Calliope — Setup / Heal"
  echo "═══════════════════════════════════════════════"
  echo
}

check_deps() {
  # Verifica che le dipendenze siano importabili nella venv
  if "$PY" -c "import uvicorn, fastapi, pydantic, httpx, mcp, flask, chromadb, rapidfuzz, yaml, requests" 2>/dev/null; then
    return 0
  else
    return 1
  fi
}

install_deps() {
  echo "[fix] Creazione venv (se assente) e installazione dipendenze..."
  if [[ ! -d "$REPO/.venv" ]]; then
    python3 -m venv "$REPO/.venv"
  fi
  "$PY" -m pip install --upgrade pip setuptools wheel >/dev/null
  "$PY" -m pip install -r "$REPO/requirements.txt"
}

health_check() {
  local url=$1
  curl -s --max-time 3 "$url" || true
}

health_ok() {
  local url=$1
  curl -s --max-time 3 -o /dev/null -w "%{http_code}" "$url" 2>/dev/null | grep -q "^200$"
}

# ---------- Inizio script ----------
print_banner

# 1) Controllo / installazione dipendenze
if ! check_deps; then
  echo "[!!] Dipendenze mancanti nella venv."
  if $FIX; then
    install_deps
    # Riprova il controllo dopo l'installazione
    if ! check_deps; then
      echo "[!!] Impossibile risolvere le dipendenze anche dopo --fix. Interrompo."
      exit 1
    fi
  else
    echo "    -> Rilancia lo script con --fix per creare la venv e installare le dipendenze."
    # Prosegui comunque con i servizi che non richiedono le dipendenze (es. SillyTavern)
  fi
fi

# ---------- Avvio / verifica dei servizi ----------
declare -A SERVICE_STATUS=(
  ["Gateway"]="KO"
  ["SillyTavern"]="KO"
  ["Mascot WS"]="KO"
  ["Flask shell"]="KO"
)

# ---- 1. LLM Gateway (porta 8766) ----
GATEWAY_PORT=8766
GATEWAY_URL="http://localhost:${GATEWAY_PORT}/health"
if health_ok "$GATEWAY_URL"; then
  # Controlliamo che il body contenga la parola "providers"
  if health_check "$GATEWAY_URL" | grep -q "providers"; then
    echo "[ok] LLM gateway già attivo (porta $GATEWAY_PORT)."
    SERVICE_STATUS["Gateway"]="OK"
  else
    echo "[CONFLITTO] Porta $GATEWAY_PORT occupata da servizio estraneo (probabile Nelson/LibreOffice) - gateway Calliope NON avviato."
    echo "    Libera la porta o riconfigura il servizio."
    SERVICE_STATUS["Gateway"]="KO"
  fi
else
  # Porta libera o servizio non risponde correttamente
  if [[ -f "$REPO/scripts/llm_gateway_http.py" ]]; then
    echo "[>>] Avvio LLM gateway..."
    nohup "$PY" "$REPO/scripts/llm_gateway_http.py" >> "$LOG_DIR/gateway.log" 2>&1 &
    disown
    sleep 2
    if health_ok "$GATEWAY_URL" && health_check "$GATEWAY_URL" | grep -q "providers"; then
      echo "[ok] LLM gateway avviato correttamente."
      SERVICE_STATUS["Gateway"]="OK"
    else
      echo "[!!] LLM gateway non risponde correttamente dopo l'avvio."
      echo "---- Log (ultime 15 righe) ----"
      tail -n 15 "$LOG_DIR/gateway.log" || true
    fi
  else
    echo "[--] llm_gateway_http.py non trovato – skip"
  fi
fi

# ---- 2. SillyTavern (porta 8001) ----
SILLY_PORT=8001
SILLY_URL="http://localhost:${SILLY_PORT}/"
if health_ok "$SILLY_URL"; then
  echo "[ok] SillyTavern già attivo (porta $SILLY_PORT)."
  SERVICE_STATUS["SillyTavern"]="OK"
else
  if [[ -d "$REPO/external/sillytavern" ]]; then
    echo "[>>] Avvio SillyTavern (cold start ~6s)..."
    (cd "$REPO/external/sillytavern" && nohup bash start.sh >> "$LOG_DIR/sillytavern.log" 2>&1 & disown)
    sleep 6
    if health_ok "$SILLY_URL"; then
      echo "[ok] SillyTavern avviato correttamente."
      SERVICE_STATUS["SillyTavern"]="OK"
    else
      echo "[!!] SillyTavern non risponde dopo l'avvio."
      echo "---- Log (ultime 15 righe) ----"
      tail -n 15 "$LOG_DIR/sillytavern.log" || true
    fi
  else
    echo "[--] Cartella external/sillytavern non trovata – skip"
  fi
fi

# ---- 3. Mascot WS (porta 9876) ----
MASCOT_PORT=9876
MASCOT_URL="http://localhost:${MASCOT_PORT}/health"
if health_ok "$MASCOT_URL"; then
  echo "[ok] Mascot WS già attivo (porta $MASCOT_PORT)."
  SERVICE_STATUS["Mascot WS"]="OK"
else
  if [[ -f "$REPO/scripts/mascot_ws_server.py" ]]; then
    echo "[>>] Avvio Mascot WS..."
    nohup "$PY" "$REPO/scripts/mascot_ws_server.py" --port "$MASCOT_PORT" >> "$LOG_DIR/mascot.log" 2>&1 &
    disown
    sleep 1
    if health_ok "$MASCOT_URL"; then
      echo "[ok] Mascot WS avviato correttamente."
      SERVICE_STATUS["Mascot WS"]="OK"
    else
      echo "[!!] Mascot WS non risponde dopo l'avvio."
      echo "---- Log (ultime 15 righe) ----"
      tail -n 15 "$LOG_DIR/mascot.log" || true
    fi
  else
    echo "[--] mascot_ws_server.py non trovato – skip"
  fi
fi

# ---- 4. Flask shell (porta 5000) ----
FLASK_PORT=5000
FLASK_URL="http://localhost:${FLASK_PORT}/health"
if health_ok "$FLASK_URL"; then
  echo "[ok] Flask shell già attivo (porta $FLASK_PORT)."
  SERVICE_STATUS["Flask shell"]="OK"
else
  echo "[>>] Avvio Flask shell..."
  # FIX: `python -m app.calliope_shell.server` richiede la repo-root su sys.path.
  # Senza cwd=repo-root né PYTHONPATH falliva con ModuleNotFoundError: No module named 'app'.
  # server.py usa path assoluti (Path(__file__)), quindi PYTHONPATH="$REPO" è sufficiente.
  PYTHONPATH="$REPO" nohup "$PY" -m app.calliope_shell.server >> "$LOG_DIR/flask.log" 2>&1 &
  disown
  sleep 3
  if health_ok "$FLASK_URL"; then
    echo "[ok] Flask shell avviato correttamente."
    SERVICE_STATUS["Flask shell"]="OK"
  else
    echo "[!!] Flask shell non risponde dopo l'avvio."
    echo "---- Log (ultime 15 righe) ----"
    tail -n 15 "$LOG_DIR/flask.log" || true
  fi
fi

# ---------- Report finale ----------
echo
echo "─── Stato salute dei servizi ───"
printf "  %-12s %-6s %s\n" "Servizio" "Porta" "Stato"
printf "  %-12s %-6s %s\n" "--------" "------" "------"
printf "  %-12s %-6s %s\n" "Gateway"   "$GATEWAY_PORT" "${SERVICE_STATUS["Gateway"]}"
printf "  %-12s %-6s %s\n" "SillyTavern" "$SILLY_PORT" "${SERVICE_STATUS["SillyTavern"]}"
printf "  %-12s %-6s %s\n" "Mascot WS" "$MASCOT_PORT" "${SERVICE_STATUS["Mascot WS"]}"
printf "  %-12s %-6s %s\n" "Flask shell" "$FLASK_PORT" "${SERVICE_STATUS["Flask shell"]}"
echo "─────────────────────────────────"

if [[ "${SERVICE_STATUS["Flask shell"]}" == "OK" ]]; then
  echo "✅ Tutto pronto – apri il browser su http://localhost:${FLASK_PORT}/"
else
  echo "⚠️ Alcuni servizi non sono attivi – controlla i log in $LOG_DIR/"
fi

echo
echo "Logs:  $LOG_DIR/"
echo "Stop:  bash scripts/stop_all_calliope_daemons.sh"
echo "─────────────────────────────────"
