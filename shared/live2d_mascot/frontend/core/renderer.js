/**
 * Shared Live2D mascot renderer — repo-agnostic bootstrap.
 *
 * Extracted from Quill of Calliope frontend/live2d/app.js (which hardcoded its
 * model URL). Here the renderer is a factory parameterized by config, so both
 * Calliope and Vesta can mount the same engine layer with their own model.
 *
 * Engine: PIXI + pixi-live2d-display (Cubism 4). For Vesta's Inochi2D convergence
 * (see VESTA_IMPORT_PATH.md), provide an alternate renderer that fulfils the SAME
 * downstream contract below — the 6 core JS files depend only on this contract,
 * never on PIXI directly.
 *
 * Downstream contract (consumed by state_machine.js / tts_sync.js / expressions.js):
 *   window.mascotApp = { app, model }
 *   model.motion(name, index?)
 *   model.expression(slot)              + model.internalModel.expressionManager
 *   model.internalModel.coreModel.setParameterValueById('ParamMouthOpenY', v)
 *   window dispatches CustomEvent('mascotReady') once the model is loaded
 *
 * @file renderer.js
 */

/**
 * Create and mount a Live2D mascot renderer.
 *
 * @param {Object} config
 * @param {string} config.modelUrl        URL/path to a .model3.json (repo-specific).
 * @param {string} [config.canvasId='live2d-canvas']  Canvas element id.
 * @param {number} [config.backgroundColor=0x1a1a2e]
 * @param {string} [config.idleMotion='Idle']         Motion group played on load.
 * @param {string} [config.errorBannerId='error-banner']
 * @returns {Promise<{app: any, model: any}>}  Resolves to window.mascotApp.
 */
async function createMascotRenderer(config) {
  const {
    modelUrl,
    canvasId = 'live2d-canvas',
    backgroundColor = 0x1a1a2e,
    idleMotion = 'Idle',
    errorBannerId = 'error-banner',
  } = config || {};

  if (!modelUrl) {
    throw new Error('[renderer] config.modelUrl is required');
  }

  try {
    const app = new PIXI.Application({
      view: document.getElementById(canvasId),
      backgroundColor,
      antialias: true,
      resizeTo: window,
    });

    const { Live2DModel } = PIXI.live2d;
    const model = await Live2DModel.from(modelUrl);

    // Center and scale model relative to viewport.
    const scale = Math.min(window.innerWidth, window.innerHeight) / 1600;
    model.scale.set(Math.max(0.3, scale));
    model.anchor.set(0.5, 0.5);
    model.position.set(app.screen.width / 2, app.screen.height / 2);

    app.stage.addChild(model);

    // Start idle motion (no-op if the model declares no such group).
    model.motion(idleMotion);

    // Fallback idle liveliness: some models (e.g. VTube-Studio exports) ship no
    // Cubism motion3 files and pixi-live2d-display leaves breath/eye-blink
    // unconfigured, so they render frozen. When the model has no motion groups,
    // drive a gentle breath sway + periodic blink ourselves so idle looks alive.
    _ensureIdleLiveliness(app, model);

    // Expose globally for state_machine.js, tts_sync.js, expressions.js (the contract).
    window.mascotApp = { app, model };

    window.dispatchEvent(new CustomEvent('mascotReady'));
    console.log('[renderer] Mascot ready:', modelUrl);

    // Reposition on window resize.
    window.addEventListener('resize', () => {
      model.position.set(app.screen.width / 2, app.screen.height / 2);
    });

    return window.mascotApp;
  } catch (err) {
    console.error('[renderer] Load failed:', err);
    const banner = document.getElementById(errorBannerId);
    if (banner) {
      banner.style.display = 'block';
      banner.textContent =
        'Failed to load mascot model. Check console. ' +
        'Ensure the engine scripts (cubismcore + pixi-live2d-display) are loaded ' +
        'and the model URL is reachable.';
    }
    throw err;
  }
}

/**
 * Synthesize an idle breath/sway + blink when the model has no motion groups.
 * Applied on the PIXI ticker at LOW priority so it runs AFTER the model's own
 * per-frame update (otherwise the model would overwrite our parameter writes).
 */
function _ensureIdleLiveliness(app, model) {
  const im = model.internalModel;
  const groups = (im && im.motionManager && im.motionManager.definitions) || {};
  if (Object.keys(groups).length > 0) return; // real motions present — nothing to do

  const core = im && im.coreModel;
  if (!core) return;

  const has = (id) => {
    try { core.getParameterValueById(id); return true; } catch (_) { return false; }
  };
  const set = (id, v) => { try { core.setParameterValueById(id, v); } catch (_) {} };

  const canBreath = has('ParamBreath');
  const canAngleX = has('ParamAngleX');
  const canAngleY = has('ParamAngleY');
  const canBody = has('ParamBodyAngleX');
  const canEyeL = has('ParamEyeLOpen');
  const canEyeR = has('ParamEyeROpen');

  let t = 0;
  let nextBlink = 1.5 + Math.random() * 3;
  let blinkUntil = -1;

  const prio = (typeof PIXI !== 'undefined' && PIXI.UPDATE_PRIORITY)
    ? PIXI.UPDATE_PRIORITY.LOW : undefined;

  app.ticker.add((dt) => {
    t += dt / 60; // PIXI dt is frames (~1 @60fps) → seconds
    if (canBreath) set('ParamBreath', 0.5 + 0.5 * Math.sin(t * 1.8));
    if (canAngleX) set('ParamAngleX', 6 * Math.sin(t * 0.7));
    if (canAngleY) set('ParamAngleY', 4 * Math.sin(t * 0.5));
    if (canBody) set('ParamBodyAngleX', 4 * Math.sin(t * 0.7));

    // Periodic blink: snap closed briefly, then reopen.
    if (t >= nextBlink && blinkUntil < 0) blinkUntil = t + 0.12;
    if (blinkUntil > 0) {
      const open = t < blinkUntil ? 0 : 1;
      if (canEyeL) set('ParamEyeLOpen', open);
      if (canEyeR) set('ParamEyeROpen', open);
      if (t >= blinkUntil) { blinkUntil = -1; nextBlink = t + 2 + Math.random() * 3; }
    }
  }, undefined, prio);

  console.log('[renderer] idle liveliness fallback active (no motion groups)');
}

// UMD-ish export: browser global + CommonJS (for node-based structure tests).
if (typeof window !== 'undefined') {
  window.createMascotRenderer = createMascotRenderer;
}
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { createMascotRenderer };
}
