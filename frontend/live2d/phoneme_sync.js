/**
 * Phoneme-level lip sync — Phase-2
 * Reads phoneme timing JSON from backend and drives Live2D mouth params.
 * Fallback: amplitude sync (Phase-1 TTSSync) if phoneme data unavailable.
 *
 * API:
 *   window.phonemeSync.start(phonemeData, audioStartTime)
 *   window.phonemeSync.stop()
 *
 * phonemeData: [{phoneme: string, start_ms: number, end_ms: number}, ...]
 * audioStartTime: Date.now() captured at the moment audio.play() is called.
 */

/** @type {Object<string, {openY: number, form: number}>} */
const PHONEME_MOUTH_SHAPES = {
  a: { openY: 1.0, form: 0.5 },
  e: { openY: 0.7, form: 0.8 },
  i: { openY: 0.4, form: 1.0 },
  o: { openY: 0.9, form: -0.3 },
  u: { openY: 0.6, form: -0.8 },
  default: { openY: 0.2, form: 0.0 },
};

/** @type {string} */
const PARAM_MOUTH_OPEN_Y = 'ParamMouthOpenY';

/** @type {string} */
const PARAM_MOUTH_FORM = 'ParamMouthForm';

class PhonemeSyncManager {
  constructor() {
    /** @type {number[]} Pending setTimeout IDs */
    this._timeouts = [];

    /** @type {boolean} */
    this._running = false;
  }

  /**
   * Start phoneme-level lip sync.
   * If phonemeData is null/empty, emits a warning and falls back to
   * the Phase-1 amplitude sync (window.ttsSync must already be active).
   *
   * @param {Array<{phoneme: string, start_ms: number, end_ms: number}>|null} phonemeData
   * @param {number} audioStartTime - Date.now() at audio play start
   */
  start(phonemeData, audioStartTime) {
    this.stop();

    if (!phonemeData || phonemeData.length === 0) {
      console.warn('[PhonemeSyncManager] No phoneme data — fallback to amplitude sync');
      return;
    }

    this._running = true;
    setMascotState('talking');
    this._schedule(phonemeData, audioStartTime);
  }

  /**
   * Stop all scheduled updates and reset mouth to closed.
   */
  stop() {
    this._timeouts.forEach((id) => clearTimeout(id));
    this._timeouts = [];
    this._running = false;
    this._setMouthParams(0, 0);
  }

  /**
   * Apply a phoneme's mouth shape to the model immediately.
   * @param {string} phoneme - IPA symbol
   * @private
   */
  _applyPhoneme(phoneme) {
    const shape = PHONEME_MOUTH_SHAPES[phoneme] ?? PHONEME_MOUTH_SHAPES['default'];
    this._setMouthParams(shape.openY, shape.form);
  }

  /**
   * Schedule all phoneme updates using setTimeout.
   * Delay = phoneme.start_ms − elapsed time since audioStartTime.
   *
   * @param {Array<{phoneme: string, start_ms: number, end_ms: number}>} phonemeData
   * @param {number} audioStartTime
   * @private
   */
  _schedule(phonemeData, audioStartTime) {
    const sorted = [...phonemeData].sort((a, b) => a.start_ms - b.start_ms);

    sorted.forEach((item, index) => {
      const elapsed = Date.now() - audioStartTime;
      const delay = Math.max(0, item.start_ms - elapsed);

      const id = setTimeout(() => {
        if (!this._running) return;
        this._applyPhoneme(item.phoneme);

        // After last phoneme ends, return mouth to rest + set idle state
        if (index === sorted.length - 1) {
          const postDelay = Math.max(50, (item.end_ms - item.start_ms));
          const idleId = setTimeout(() => {
            this._setMouthParams(0, 0);
            setMascotState('idle');
          }, postDelay);
          this._timeouts.push(idleId);
        }
      }, delay);

      this._timeouts.push(id);
    });
  }

  /**
   * Write mouth params directly to the Live2D core model.
   * @param {number} openY - ParamMouthOpenY value (0–1)
   * @param {number} form  - ParamMouthForm value (−1 to 1)
   * @private
   */
  _setMouthParams(openY, form) {
    const model = window.mascotApp?.model;
    if (!model) return;
    try {
      const core = model.internalModel?.coreModel;
      if (!core) return;
      core.setParameterValueById(PARAM_MOUTH_OPEN_Y, openY);
      core.setParameterValueById(PARAM_MOUTH_FORM, form);
    } catch (_) {
      // Model not ready — silent fail
    }
  }
}

window.phonemeSync = new PhonemeSyncManager();
