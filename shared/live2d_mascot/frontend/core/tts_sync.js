/**
 * TTS lip-sync via WebAudio API amplitude analysis.
 * Phase-1: stub polling localhost:8767/tts-status (backend Phase-2).
 * Phase-1 real: attach to <audio> element for amplitude-driven lip sync.
 */

class TTSSync {
  /** @param {HTMLAudioElement} audioElement */
  constructor(audioElement) {
    this.audio = audioElement;
    this.ctx = null;
    this.analyser = null;
    this.dataArray = null;
    this.rafId = null;
    this.silenceTimer = null;
    this.active = false;
  }

  start() {
    if (this.active) return;
    this.active = true;
    try {
      this.ctx = new (window.AudioContext || window.webkitAudioContext)();
      this.analyser = this.ctx.createAnalyser();
      this.analyser.fftSize = 256;
      const src = this.ctx.createMediaElementSource(this.audio);
      src.connect(this.analyser);
      this.analyser.connect(this.ctx.destination);
      this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
      this._loop();
    } catch (err) {
      console.error('[TTSSync] start failed:', err);
      this.active = false;
    }
  }

  stop() {
    this.active = false;
    if (this.rafId) { cancelAnimationFrame(this.rafId); this.rafId = null; }
    if (this.silenceTimer) { clearTimeout(this.silenceTimer); this.silenceTimer = null; }
    // Reset mouth
    const model = window.mascotApp?.model;
    if (model) {
      try { model.internalModel?.coreModel?.setParameterValueById('ParamMouthOpenY', 0); } catch (_) {}
    }
    if (this.ctx?.state !== 'closed') this.ctx?.close().catch(() => {});
  }

  _loop() {
    if (!this.active) return;
    this.rafId = requestAnimationFrame(() => this._loop());

    this.analyser.getByteFrequencyData(this.dataArray);
    const avg = this.dataArray.reduce((a, b) => a + b, 0) / this.dataArray.length;
    const amplitude = avg / 255; // 0-1

    // Drive mouth open parameter
    const model = window.mascotApp?.model;
    if (model) {
      try {
        model.internalModel?.coreModel?.setParameterValueById('ParamMouthOpenY', amplitude);
      } catch (_) {}
    }

    // State transitions
    if (amplitude > 0.1) {
      if (this.silenceTimer) { clearTimeout(this.silenceTimer); this.silenceTimer = null; }
      setMascotState('talking');
    } else if (!this.silenceTimer) {
      this.silenceTimer = setTimeout(() => {
        setMascotState('idle');
        this.silenceTimer = null;
      }, 500);
    }
  }
}

/** Attach TTSSync to an audio element. @returns {TTSSync} */
function attachToAudio(audioElement) {
  return new TTSSync(audioElement);
}

// ---- Stub polling localhost:8767/tts-status ----
function _pollTTSStatus() {
  fetch('http://localhost:8767/tts-status')
    .then((r) => r.json())
    .then((data) => {
      if (data?.playing) {
        let audio = document.getElementById('tts-audio');
        if (!audio) {
          audio = Object.assign(new Audio(), { id: 'tts-audio' });
          document.body.appendChild(audio);
        }
        if (!window.ttsSync) window.ttsSync = attachToAudio(audio);
        window.ttsSync.start();
      } else if (window.ttsSync) {
        window.ttsSync.stop();
      }
    })
    .catch(() => {}) // backend not running in Phase-1 — silent
    .finally(() => setTimeout(_pollTTSStatus, 1000));
}

document.addEventListener('DOMContentLoaded', () => {
  // Start polling after short delay to let model load first
  setTimeout(_pollTTSStatus, 2000);
});
