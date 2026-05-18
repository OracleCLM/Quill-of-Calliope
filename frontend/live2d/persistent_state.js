/**
 * Persistent mascot state — Phase-2
 * Saves/restores expression, scene type, and mood across page loads via localStorage.
 * State is discarded if older than 30 minutes.
 *
 * API (globals): saveMascotState() / loadMascotState()
 *
 * @file persistent_state.js
 */

const STORAGE_KEY    = 'calliope_mascot_state';
const EXPIRY_MS      = 30 * 60 * 1000; // 30 minutes

/**
 * Saves the current mascot state to localStorage.
 * @returns {boolean} true if saved successfully
 */
function saveMascotState() {
  const state = {
    expression:    window.getCurrentExpression?.() || 'neutral',
    lastSceneType: window._lastSceneType || null,
    lastMood:      window._lastMood      || null,
    timestamp:     Date.now(),
  };
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    return true;
  } catch (_) {
    return false;
  }
}

/**
 * Loads mascot state from localStorage and applies it if fresh (<30 min).
 * @returns {Object|null} Restored state object, or null if missing/expired
 */
function loadMascotState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;

    const state = JSON.parse(raw);
    if (!state || typeof state !== 'object') return null;

    // Discard stale state
    if (Date.now() - state.timestamp > EXPIRY_MS) return null;

    // Restore expression
    if (state.expression && typeof window.setExpression === 'function') {
      window.setExpression(state.expression);
    }

    // Restore globals (consumers can read these)
    if (state.lastSceneType !== undefined) window._lastSceneType = state.lastSceneType;
    if (state.lastMood      !== undefined) window._lastMood      = state.lastMood;

    return state;
  } catch (_) {
    return null;
  }
}

// Auto-save on page unload
window.addEventListener('beforeunload', saveMascotState);

// Auto-save on relevant state changes
window.addEventListener('stateChanged',      saveMascotState);
window.addEventListener('expressionChanged', saveMascotState);

// Auto-load once the mascot model is ready
window.addEventListener('mascotReady', loadMascotState);

// Expose globals
window.saveMascotState = saveMascotState;
window.loadMascotState = loadMascotState;
