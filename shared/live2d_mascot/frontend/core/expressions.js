/**
 * Calliope expression library — Phase-2
 * Maps emotion names to Live2D expression slots.
 * API: setExpression(name, fadeDuration?) — global, fade 300ms default
 *
 * @file expressions.js
 */

(function () {
  'use strict';

  // Expression definitions: slot + Live2D param values
  const EXPRESSIONS = {
    joy:      { slot: 'f00', paramMouthForm: 1.0,  paramBrowY: 0.5  },
    sad:      { slot: 'f01', paramMouthForm: -1.0, paramBrowY: -0.5 },
    anger:    { slot: 'f02', paramMouthForm: -0.5, paramBrowY: -1.0 },
    surprise: { slot: 'f03', paramMouthForm: 0.8,  paramBrowY: 1.0  },
    neutral:  { slot: 'f04', paramMouthForm: 0.0,  paramBrowY: 0.0  },
    thinking: { slot: 'f05', paramMouthForm: -0.2, paramBrowY: 0.3  },
    confused: { slot: 'f06', paramMouthForm: -0.3, paramBrowY: 0.7  },
  };

  // Map app states → default expression
  const STATE_DEFAULT_EXPRESSION = {
    idle:      'neutral',
    talking:   'joy',
    listening: 'neutral',
    thinking:  'thinking',
  };

  // Live2D parameter IDs
  const PARAM_MOUTH_FORM = 'ParamMouthForm';
  const PARAM_BROW_L_Y   = 'ParamBrowLY';
  const PARAM_BROW_R_Y   = 'ParamBrowRY';

  let _currentExpression = 'neutral';
  let _pendingExpression  = null;

  /**
   * Sets the current expression on the Live2D model.
   * @param {string} name         - One of: joy | sad | anger | surprise | neutral | thinking | confused
   * @param {number} fadeDuration - Fade duration in ms (default 300)
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

    const expr = EXPRESSIONS[name];

    try {
      // Trigger the expression slot (pixi-live2d-display handles its own fade)
      model.expression(expr.slot);

      // Also set raw parameters for precision control
      const core = model.internalModel?.coreModel;
      if (core) {
        core.setParameterValueById(PARAM_MOUTH_FORM, expr.paramMouthForm);
        core.setParameterValueById(PARAM_BROW_L_Y,   expr.paramBrowY);
        core.setParameterValueById(PARAM_BROW_R_Y,   expr.paramBrowY);
      }
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
  window.setExpression      = setExpression;
  window.getCurrentExpression = getCurrentExpression;

  // Set initial pending so it fires once model is ready
  _pendingExpression = { name: 'neutral', fadeDuration: 0 };
})();
