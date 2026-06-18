/**
 * Mascot expression library.
 * Maps emotion names → Live2D expression slot (the .exp3.json "Name").
 * API: setExpression(name, fadeDuration?) — global, fade 300ms default
 *
 * Default slots target the SHIPPABLE model (Mao): exp_01..exp_08, the REAL
 * expression Names in models/mao/Mao.model3.json. Mao's .exp3.json files carry
 * the visual params, so we trigger the slot and let Live2D blend — no hand-poked
 * raw params (Mao has no ParamMouthForm). A consuming repo with a different model
 * can override the map via window.MASCOT_CONFIG.expressionMap.
 *
 * @file expressions.js
 */

(function () {
  'use strict';

  // emotion → { slot } where slot is the model3.json Expression Name.
  const DEFAULT_EXPRESSIONS = {
    neutral:  { slot: 'exp_01' },
    joy:      { slot: 'exp_02' },
    surprise: { slot: 'exp_03' },
    thinking: { slot: 'exp_04' },
    sad:      { slot: 'exp_05' },
    confused: { slot: 'exp_06' },
    anger:    { slot: 'exp_07' },
    special:  { slot: 'exp_08' },
  };

  const EXPRESSIONS =
    (window.MASCOT_CONFIG && window.MASCOT_CONFIG.expressionMap) || DEFAULT_EXPRESSIONS;

  // Map app states → default expression
  const STATE_DEFAULT_EXPRESSION = {
    idle:      'neutral',
    talking:   'joy',
    listening: 'neutral',
    thinking:  'thinking',
  };

  let _currentExpression = 'neutral';
  let _pendingExpression  = null;

  /**
   * Sets the current expression on the Live2D model.
   * @param {string} name         - An emotion key from the active expression map.
   * @param {number} fadeDuration - Fade duration in ms (default 300; Live2D handles fade).
   */
  function setExpression(name, fadeDuration = 300) {
    if (!EXPRESSIONS[name]) {
      console.warn('[expressions] Unknown expression:', name);
      return;
    }

    const model = window.mascotApp?.model;
    if (!model) {
      // Model not ready — stash and retry on mascotReady
      _pendingExpression = { name, fadeDuration };
      return;
    }

    try {
      // Trigger the expression slot (pixi-live2d-display handles its own fade).
      model.expression(EXPRESSIONS[name].slot);
    } catch (err) {
      console.warn('[expressions] Error applying expression:', err);
      _pendingExpression = { name, fadeDuration };
      return;
    }

    _currentExpression = name;
    _pendingExpression = null;

    window.dispatchEvent(new CustomEvent('expressionChanged', {
      detail: { expression: name },
    }));
  }

  /**
   * Returns the currently active expression name.
   * @returns {string}
   */
  function getCurrentExpression() {
    return _currentExpression;
  }

  // Retry pending expression when mascot becomes ready
  function _onMascotReady() {
    if (_pendingExpression) {
      const { name, fadeDuration } = _pendingExpression;
      _pendingExpression = null;
      setTimeout(() => setExpression(name, fadeDuration), 50);
    }
  }

  // Auto-apply default expression on state changes
  window.addEventListener('stateChanged', function (e) {
    const expr = STATE_DEFAULT_EXPRESSION[e.detail?.state];
    if (expr) setExpression(expr);
  });

  window.addEventListener('mascotReady', _onMascotReady);

  // Expose globals
  window.setExpression        = setExpression;
  window.getCurrentExpression = getCurrentExpression;

  // Set initial pending so it fires once model is ready
  _pendingExpression = { name: 'neutral', fadeDuration: 0 };
})();
