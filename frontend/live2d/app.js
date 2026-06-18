/**
 * Calliope mascot bootstrap — thin config wrapper over the shared renderer.
 *
 * The rendering/engine logic now lives in the repo-agnostic factory
 * `createMascotRenderer` (shared/live2d_mascot/frontend/core/renderer.js).
 * This file only supplies Calliope's config and is the consumer that proves
 * the shared renderer reuse path (the same factory mounts the Vesta mascot).
 *
 * MODEL ASSET — operator aesthetic choice: the real calliope.moc3 art does not
 * exist yet (see shared/live2d_mascot/models/calliope/README.md). Until it lands,
 * this falls back to a placeholder Cubism model so the dashboard renders. Override
 * by defining `window.MASCOT_CONFIG = { modelUrl, canvasId, idleMotion }` before
 * this script loads.
 */
document.addEventListener('DOMContentLoaded', () => {
  const PLACEHOLDER_MODEL =
    'https://cdn.jsdelivr.net/gh/guansss/pixi-live2d-display/test/assets/hiyori/hiyori_pro_t10.model3.json';

  const config = window.MASCOT_CONFIG || {
    modelUrl: PLACEHOLDER_MODEL,
    canvasId: 'live2d-canvas',
    idleMotion: 'Idle',
  };

  if (typeof createMascotRenderer !== 'function') {
    console.error('[Calliope] shared renderer not loaded — check renderer.js script tag');
    return;
  }

  createMascotRenderer(config).catch((err) => {
    console.error('[Calliope] mascot init failed:', err);
  });
});
