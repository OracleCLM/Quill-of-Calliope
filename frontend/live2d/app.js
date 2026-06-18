/**
 * Calliope mascot bootstrap — thin config wrapper over the shared renderer.
 *
 * The rendering/engine logic lives in the repo-agnostic factory
 * `createMascotRenderer` (shared/live2d_mascot/frontend/core/renderer.js).
 * This file only supplies the model registry + selection, proving the shared
 * renderer reuse path (the same factory mounts the Vesta mascot).
 *
 * MODEL CHOICE — operator aesthetic decision:
 *   - mao     → SHIPPABLE DEFAULT. Live2D official sample model (Free Material
 *               License). The only model committed to git / shippable open-source.
 *   - koko    → dev-reference ONLY (license no-redistribute). gitignored.
 *   - tingyun → dev-reference ONLY (fan-IP HoYoverse). gitignored. Chinese
 *               filename → modelUrl built with encodeURI.
 *
 * Select a model with the `?model=` query param (default: mao):
 *   index.html?model=koko
 * Override entirely by defining `window.MASCOT_CONFIG` before this script loads.
 */
(function () {
  // Path from frontend/live2d/index.html to the shared models dir.
  const MODELS_BASE = '../../shared/live2d_mascot/models';

  // Per-model config. `expressions` lists the REAL expression names declared in
  // each model3.json — used by the browser-verify harness to exercise ≥1 change.
  const MASCOT_MODELS = {
    mao: {
      modelUrl: `${MODELS_BASE}/mao/Mao.model3.json`,
      idleMotion: 'Idle',
      expressions: ['exp_01', 'exp_02', 'exp_03', 'exp_04', 'exp_05', 'exp_06', 'exp_07', 'exp_08'],
      shippable: true,
    },
    koko: {
      // VTube-Studio export — Chinese-free path but expressions injected locally.
      modelUrl: `${MODELS_BASE}/koko/KITU15.model3.json`,
      idleMotion: 'Idle',
      expressions: ['Kirakira', 'Scared', 'Shy', 'Angry', 'Cute'],
      shippable: false,
    },
    tingyun: {
      // Chinese model filename → encodeURI so the fetch URL is percent-encoded.
      modelUrl: encodeURI(`${MODELS_BASE}/tingyun/停云.model3.json`),
      idleMotion: 'Idle',
      expressions: ['脸黑', '尾巴', '心心眼', '脸红'],
      shippable: false,
    },
  };

  function selectedModelKey() {
    try {
      const q = new URLSearchParams(window.location.search).get('model');
      if (q && MASCOT_MODELS[q]) return q;
    } catch (_) { /* file:// without search — fall through */ }
    return 'mao';
  }

  document.addEventListener('DOMContentLoaded', () => {
    const key = selectedModelKey();
    const model = MASCOT_MODELS[key];

    const config = window.MASCOT_CONFIG || {
      modelUrl: model.modelUrl,
      canvasId: 'live2d-canvas',
      idleMotion: model.idleMotion,
    };

    // Expose the active selection so the verify harness / UI can cycle expressions.
    window.MASCOT_ACTIVE = { key, ...model };
    window.MASCOT_MODELS = MASCOT_MODELS;

    if (typeof createMascotRenderer !== 'function') {
      console.error('[Calliope] shared renderer not loaded — check renderer.js script tag');
      return;
    }

    createMascotRenderer(config).catch((err) => {
      console.error('[Calliope] mascot init failed:', err);
    });
  });
})();
