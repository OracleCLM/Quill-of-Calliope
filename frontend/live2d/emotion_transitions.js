/**
 * Emotion-tied animation transitions — Phase-2
 * Uses PIXI.Ticker (or rAF fallback) for smooth head-param interpolation.
 * Transition matrix: from-state + to-state → animation + expression sequence.
 *
 * @file emotion_transitions.js
 */

const TRANSITION_MATRIX = {
  'idle→talking':      { motion: 'TapBody', expression: 'joy',      headPitch: 0.0,  delay: 0   },
  'talking→idle':      { motion: 'Idle',    expression: 'neutral',  headPitch: 0.0,  delay: 100 },
  'talking→listening': { motion: 'Idle',    expression: 'neutral',  headTilt: -0.2,  delay: 50  },
  'listening→thinking':{ motion: 'Idle',    expression: 'thinking', headPitch: 0.3,  delay: 0   },
  'thinking→talking':  { motion: 'TapBody', expression: 'joy',      headPitch: 0.0,  delay: 200 },
  'thinking→idle':     { motion: 'Idle',    expression: 'neutral',  headPitch: 0.0,  delay: 0   },
};

const PARAM_HEAD_ANGLE_X = 'ParamAngleX';
const PARAM_HEAD_ANGLE_Y = 'ParamAngleY';
const FADE_DURATION = 300; // ms

class EmotionTransitionManager {
  constructor() {
    this._ticker         = null;    // PIXI.Ticker instance or RAF sentinel
    this._interpolations = [];      // active interpolation descriptors
    this._prevState      = null;
    this._lastTimestamp  = undefined;
    this._bindStateEvents();
  }

  /** Listen to stateChanged; track previous state to build transition key. */
  _bindStateEvents() {
    window.addEventListener('stateChanged', (e) => {
      const newState = e.detail?.state;
      if (newState && this._prevState !== null && this._prevState !== newState) {
        this._applyTransition(this._prevState, newState);
      }
      this._prevState = newState;
    });
  }

  /**
   * Look up transition matrix and apply motion + expression + head interpolation.
   * @param {string} from  Previous state name
   * @param {string} to    New state name
   */
  _applyTransition(from, to) {
    const entry = TRANSITION_MATRIX[`${from}→${to}`];
    if (!entry) return;

    setTimeout(() => {
      const model = window.mascotApp?.model;
      if (!model) return;

      // Trigger motion
      try { model.motion(entry.motion); } catch (_) {}

      // Apply expression via global helper
      if (typeof window.setExpression === 'function') {
        window.setExpression(entry.expression);
      }

      // Interpolate head params
      const core = model.internalModel?.coreModel;
      if (!core) return;

      if (entry.headPitch !== undefined) {
        const current = this._safeGetParam(core, PARAM_HEAD_ANGLE_Y);
        this._startInterpolation(PARAM_HEAD_ANGLE_Y, current, entry.headPitch, FADE_DURATION);
      }
      if (entry.headTilt !== undefined) {
        const current = this._safeGetParam(core, PARAM_HEAD_ANGLE_X);
        this._startInterpolation(PARAM_HEAD_ANGLE_X, current, entry.headTilt, FADE_DURATION);
      }
    }, entry.delay);
  }

  /** Safely read a Live2D parameter; returns 0 on failure. */
  _safeGetParam(core, paramId) {
    try {
      return core.getParameterValueById?.(paramId) ?? 0;
    } catch (_) {
      return 0;
    }
  }

  /**
   * Push an interpolation task and ensure the ticker is running.
   * @param {string} paramId     Live2D parameter ID
   * @param {number} from        Start value
   * @param {number} to          Target value
   * @param {number} durationMs  Duration in milliseconds
   */
  _startInterpolation(paramId, from, to, durationMs) {
    // Remove any existing interpolation for the same param
    this._interpolations = this._interpolations.filter(i => i.paramId !== paramId);
    this._interpolations.push({ paramId, from, to, elapsed: 0, duration: durationMs });
    this._ensureTicker();
  }

  /** Start PIXI.Ticker or rAF loop if not already running. */
  _ensureTicker() {
    if (this._ticker) return;

    if (window.PIXI?.Ticker) {
      this._ticker = new window.PIXI.Ticker();
      this._ticker.add((delta) => {
        // PIXI passes delta in frames; convert to ms at ~60 fps
        this._tickLoop(delta * (1000 / 60));
      });
      this._ticker.start();
    } else {
      // rAF fallback
      this._ticker = { active: true };
      const loop = (timestamp) => {
        if (!this._ticker?.active) return;
        const delta = this._lastTimestamp === undefined ? 16 : timestamp - this._lastTimestamp;
        this._lastTimestamp = timestamp;
        this._tickLoop(delta);
        if (this._interpolations.length > 0) {
          requestAnimationFrame(loop);
        } else {
          this._ticker = null;
          this._lastTimestamp = undefined;
        }
      };
      requestAnimationFrame(loop);
    }
  }

  /**
   * Advance all active interpolations by delta ms and update Live2D params.
   * @param {number} deltaMs  Elapsed time in milliseconds since last tick
   */
  _tickLoop(deltaMs) {
    if (this._interpolations.length === 0) {
      this._stopTicker();
      return;
    }

    const core = window.mascotApp?.model?.internalModel?.coreModel;

    for (let i = this._interpolations.length - 1; i >= 0; i--) {
      const interp = this._interpolations[i];
      interp.elapsed += deltaMs;

      const t = Math.min(interp.elapsed / interp.duration, 1);
      // easeInOutQuad
      const eased = t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
      const value = interp.from + (interp.to - interp.from) * eased;

      if (core) {
        try { core.setParameterValueById(interp.paramId, value); } catch (_) {}
      }

      if (t >= 1) {
        this._interpolations.splice(i, 1);
      }
    }

    // Stop ticker if no more work
    if (this._interpolations.length === 0) {
      this._stopTicker();
    }
  }

  _stopTicker() {
    if (!this._ticker) return;
    if (this._ticker.stop) {
      this._ticker.stop();
      this._ticker.destroy?.();
    } else {
      this._ticker.active = false;
    }
    this._ticker = null;
    this._lastTimestamp = undefined;
  }
}

window.emotionTransitions = new EmotionTransitionManager();
