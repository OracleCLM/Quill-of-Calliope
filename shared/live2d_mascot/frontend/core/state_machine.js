/**
 * Calliope mascot state machine.
 * States: idle | talking | listening | thinking
 * API: setMascotState(newState) — global function
 * Triggers: window.postMessage({ type:'SET_STATE', state:'...' })
 *           WebSocket ws://localhost:8767 (optional, reconnects on close)
 */

const STATES = { IDLE: 'idle', TALKING: 'talking', LISTENING: 'listening', THINKING: 'thinking' };
let currentState = STATES.IDLE;

// ---- WebSocket (optional backend wire) ----
let _ws = null;
function _connectWS() {
  try {
    _ws = new WebSocket('ws://localhost:8767');
    _ws.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data);
        if (d?.type === 'SET_STATE' && d.state) setMascotState(d.state);
      } catch (_) {}
    };
    _ws.onerror = () => {};
    _ws.onclose = () => setTimeout(_connectWS, 3000);
  } catch (_) {
    setTimeout(_connectWS, 3000);
  }
}
_connectWS();

// ---- postMessage ----
window.addEventListener('message', (e) => {
  if (e.data?.type === 'SET_STATE' && e.data.state) setMascotState(e.data.state);
});

// ---- Core state setter ----
function setMascotState(newState) {
  const s = (newState || '').toLowerCase();
  if (!Object.values(STATES).includes(s)) {
    console.warn(`[StateMachine] Unknown state: ${newState}`);
    return;
  }
  if (currentState === s) return;

  const { model } = window.mascotApp || {};
  if (!model) {
    console.warn('[StateMachine] Model not ready, queuing state:', s);
    // Retry once model is ready
    window.addEventListener('mascotReady', () => setMascotState(s), { once: true });
    return;
  }

  console.log(`[StateMachine] ${currentState} → ${s}`);
  const prev = currentState;
  currentState = s;

  switch (s) {
    case STATES.IDLE:
      model.motion('Idle');
      _tryExpression(model, null);
      break;
    case STATES.TALKING:
      model.motion('TapBody');
      _tryExpression(model, 'exp_02');
      break;
    case STATES.LISTENING:
      model.motion('Idle', 1);
      _tryExpression(model, 'exp_05');
      break;
    case STATES.THINKING:
      model.motion('Idle', 2);
      _tryExpression(model, 'exp_04');
      break;
  }

  window.dispatchEvent(new CustomEvent('stateChanged', { detail: { state: s, prev } }));
}

function _tryExpression(model, name) {
  try {
    if (name && model.internalModel?.expressionManager) {
      model.expression(name);
    }
  } catch (_) {}
}
