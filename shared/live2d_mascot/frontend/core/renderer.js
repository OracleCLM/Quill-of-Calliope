/* renderer.js — entry-point del renderer Live2D condiviso.
 *
 * Definisce window.createMascotRenderer(config): inizializza PIXI (v7) +
 * pixi-live2d-display (cubism4), carica il model, lo monta su #canvas con
 * sfondo trasparente, pubblica window.mascotApp = { app, model } e segnala
 * 'mascotReady'. È il file che pet_page.py / dashboard.html si aspettano in
 * <script src="/core/renderer.js"> e che invocano via createMascotRenderer().
 *
 * Contratto config (da MASCOT_CONFIG):
 *   modelUrl, canvasId, backgroundAlpha, idleMotion, errorBannerId, fitWidth
 *
 * Richiede che PIXI e PIXI.live2d (vendor) siano già caricati.
 */
(function () {
  'use strict';

  function _fail(msg) {
    var e = new Error(msg);
    e.name = 'MascotRendererError';
    return e;
  }

  async function createMascotRenderer(cfg) {
    cfg = cfg || {};

    if (typeof PIXI === 'undefined') throw _fail('PIXI non caricato (vendor/pixi.min.js)');
    if (!PIXI.live2d || !PIXI.live2d.Live2DModel) {
      throw _fail('pixi-live2d-display non caricato (vendor/pixi-live2d-cubism4.min.js)');
    }

    var canvas = document.getElementById(cfg.canvasId || 'live2d-canvas');
    if (!canvas) throw _fail('canvas #' + (cfg.canvasId || 'live2d-canvas') + ' non trovato');

    // Le motion/physics auto-update richiedono un ticker registrato.
    try { PIXI.live2d.Live2DModel.registerTicker(PIXI.Ticker); } catch (e) { /* già registrato */ }

    var app = new PIXI.Application({
      view: canvas,
      backgroundAlpha: (cfg.backgroundAlpha != null ? cfg.backgroundAlpha : 0),
      resizeTo: window,           // canvas = dimensione finestra Qt
      antialias: true,
      autoDensity: true,
      resolution: window.devicePixelRatio || 1,
    });

    // autoInteract off: il drag/right-click li gestisce l'overlay Qt (shell.py).
    var model = await PIXI.live2d.Live2DModel.from(cfg.modelUrl, { autoInteract: false });

    // Ancoraggio al centro-orizzontale, leggermente in alto (testa+busto visibili
    // in una finestra verticale stretta come il pet).
    model.anchor.set(0.5, 0.0);
    app.stage.addChild(model);

    function layout() {
      var W = app.renderer.width;
      var H = app.renderer.height;
      // larghezza nativa del model (coordinate canvas Live2D).
      var nativeW = (model.internalModel && model.internalModel.originalWidth)
        || model.width || (cfg.fitWidth || W);
      var targetW = cfg.fitWidth || W;
      var scale = targetW / nativeW;
      model.scale.set(scale);
      model.x = W / 2;
      model.y = H * 0.04;          // piccolo margine dall'alto
    }
    layout();
    window.addEventListener('resize', layout);

    // Idle motion se il model la dichiara (Mao minimale → no-op silenzioso).
    if (cfg.idleMotion) {
      try { model.motion(cfg.idleMotion); } catch (e) { /* nessuna motion: model statico */ }
    }

    window.mascotApp = { app: app, model: model };
    window.dispatchEvent(new Event('mascotReady'));
    return window.mascotApp;
  }

  window.createMascotRenderer = createMascotRenderer;
})();
