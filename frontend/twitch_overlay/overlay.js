/**
 * Quill of Calliope — Twitch Overlay
 * OBS browser source: ws://localhost:8767 | Live2D mascot + scene text bubble
 */

const WS_URL = 'ws://localhost:8767';
const MODEL_URL = 'https://cdn.jsdelivr.net/gh/guansss/pixi-live2d-display/test/assets/hiyori/hiyori_pro_t10.model3.json';
const BUBBLE_DURATION_MS = 7000;
const TYPEWRITER_MS = 32;

let _model = null;
let _typewriterTimer = null;
let _bubbleHideTimer = null;

// ── Live2D init ───────────────────────────────────────────────────────────────
async function initLive2D() {
  const { Live2DModel } = PIXI.live2d;
  const canvas = document.getElementById('live2d-canvas');
  const size = 380;

  const app = new PIXI.Application({
    view: canvas,
    width: size,
    height: size,
    backgroundAlpha: 0,
    antialias: true,
  });

  try {
    _model = await Live2DModel.from(MODEL_URL);
    _model.scale.set(0.32);
    _model.anchor.set(0.5, 1.0);
    _model.position.set(size / 2, size);
    app.stage.addChild(_model);
    _model.motion('Idle');
    console.log('[Overlay] Live2D model loaded');
  } catch (err) {
    console.error('[Overlay] Model load failed:', err);
  }
}

// ── State machine ─────────────────────────────────────────────────────────────
function setOverlayState(state) {
  if (!_model) return;
  const motionMap = {
    idle: 'Idle', talking: 'TapBody', listening: 'Idle', thinking: 'Idle',
    happy: 'TapBody', surprise: 'TapBody',
  };
  try { _model.motion(motionMap[state] || 'Idle'); } catch (_) {}
}

const EMOTION_STATE = {
  happy: 'happy', sad: 'idle', angry: 'thinking',
  neutral: 'idle', fearful: 'idle', determined: 'talking',
};

// ── Scene bubble (typewriter) ─────────────────────────────────────────────────
function showSceneBubble(text, sceneType) {
  const bubble = document.getElementById('scene-bubble');
  const nameEl = document.getElementById('mascot-name');
  const textEl = document.getElementById('bubble-text');

  clearTimeout(_typewriterTimer);
  clearTimeout(_bubbleHideTimer);

  nameEl.textContent = (sceneType || 'scene').replace(/_/g, ' ').toUpperCase();
  textEl.textContent = '';
  textEl.classList.add('typing');
  bubble.classList.add('visible');

  let i = 0;
  const tick = () => {
    if (i < text.length) {
      textEl.textContent += text[i++];
      _typewriterTimer = setTimeout(tick, TYPEWRITER_MS);
    } else {
      textEl.classList.remove('typing');
    }
  };
  tick();

  _bubbleHideTimer = setTimeout(() => {
    bubble.classList.remove('visible');
    setTimeout(() => {
      textEl.textContent = '';
      nameEl.textContent = '';
    }, 400);
  }, BUBBLE_DURATION_MS);
}

// ── WebSocket ─────────────────────────────────────────────────────────────────
function connectWS() {
  const ws = new WebSocket(WS_URL);

  ws.onopen  = () => console.log('[Overlay] WS connected');
  ws.onclose = () => { console.log('[Overlay] WS disconnected — retry 3s'); setTimeout(connectWS, 3000); };
  ws.onerror = () => {};

  ws.onmessage = (evt) => {
    let data;
    try { data = JSON.parse(evt.data); } catch (_) { return; }

    switch (data.type) {
      case 'mascot_state':
        setOverlayState(data.state || 'idle');
        break;
      case 'scene_text':
        showSceneBubble(data.text || '', data.scene_type || '');
        setOverlayState('talking');
        break;
      case 'mood':
        setOverlayState(EMOTION_STATE[data.emotion] || 'idle');
        break;
      // Twitch events pushed by twitch_bot.py
      case 'twitch_event':
        if (data.event === 'mascot_state') setOverlayState(data.state || 'idle');
        if (data.event === 'scene_text')   showSceneBubble(data.text || '', data.scene_type || '');
        break;
    }
  };
}

window.addEventListener('load', () => {
  initLive2D();
  connectWS();
});
