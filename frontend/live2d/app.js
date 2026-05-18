document.addEventListener('DOMContentLoaded', async () => {
  const MODEL_URL =
    'https://cdn.jsdelivr.net/gh/guansss/pixi-live2d-display/test/assets/hiyori/hiyori_pro_t10.model3.json';

  try {
    const app = new PIXI.Application({
      view: document.getElementById('live2d-canvas'),
      backgroundColor: 0x1a1a2e,
      antialias: true,
      resizeTo: window,
    });

    const { Live2DModel } = PIXI.live2d;

    const model = await Live2DModel.from(MODEL_URL);

    // Center and scale model
    const scale = Math.min(window.innerWidth, window.innerHeight) / 1600;
    model.scale.set(Math.max(0.3, scale));
    model.anchor.set(0.5, 0.5);
    model.position.set(app.screen.width / 2, app.screen.height / 2);

    app.stage.addChild(model);

    // Start idle
    model.motion('Idle');

    // Expose globally for state_machine.js and tts_sync.js
    window.mascotApp = { app, model };

    window.dispatchEvent(new CustomEvent('mascotReady'));
    console.log('[Live2D] Mascot ready:', MODEL_URL);

    // Reposition on window resize
    window.addEventListener('resize', () => {
      model.position.set(app.screen.width / 2, app.screen.height / 2);
    });
  } catch (err) {
    console.error('[Live2D] Load failed:', err);
    const banner = document.getElementById('error-banner');
    if (banner) {
      banner.style.display = 'block';
      banner.textContent =
        'Failed to load mascot model. Check console. ' +
        'Ensure CDN is reachable and cubismcore script is loaded.';
    }
  }
});
