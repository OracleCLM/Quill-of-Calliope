// mascot.js — Calliope product-shell sidebar mascot.
//
// Thin CONSUMER of the shared renderer factory (createMascotRenderer in
// shared/live2d_mascot/frontend/core/renderer.js, served at
// /shared/live2d_mascot/frontend/core/renderer.js). The engine/rendering logic
// lives there — this file only supplies the model registry + selection and the
// product-specific WebSocket emotion sync. It does NOT duplicate the engine.
(function () {
    'use strict';

    const CANVAS_ID = 'mascot';
    const EMOTION_MAP_URL = '/api/mascot/emotion_map';
    const DEFAULT_WS_URL = 'ws://localhost:9876/mascot';
    const RETRY_DELAY = 3000;
    const MAX_RETRIES = 5;
    const STORAGE_KEY = 'mascot_last_emotion';
    const MODELS_BASE = '/shared/live2d_mascot/models';

    // Model registry — mirrors the dev dashboard (frontend/live2d/app.js) so the
    // same ?model=mao|koko|tingyun switch works on the product home. Mao is the
    // shippable default (Live2D Free Material License); koko/tingyun are
    // gitignored dev-only references (tingyun has a Chinese filename → encodeURI).
    const MASCOT_MODELS = {
        mao: { modelUrl: `${MODELS_BASE}/mao/Mao.model3.json` },
        koko: { modelUrl: `${MODELS_BASE}/koko/KITU15.model3.json` },
        tingyun: { modelUrl: encodeURI(`${MODELS_BASE}/tingyun/停云.model3.json`) },
    };

    let ws = null;
    let retryCount = 0;
    let isConnecting = false;
    window._emotionMap = {};

    function selectedModelKey() {
        try {
            const q = new URLSearchParams(window.location.search).get('model');
            if (q && MASCOT_MODELS[q]) return q;
        } catch (_) { /* file:// without search — fall through */ }
        return 'mao';
    }

    // The shared renderer publishes window.mascotApp = { app, model }.
    function getModel() {
        return window.mascotApp && window.mascotApp.model;
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    async function init() {
        const canvas = document.getElementById(CANVAS_ID);
        if (!canvas) {
            console.warn('[mascot] Canvas not found:', CANVAS_ID);
            return;
        }
        if (typeof window.PIXI === 'undefined') {
            console.warn('[mascot] PIXI not loaded — CDN/vendor unavailable, skipping init');
            return;
        }
        if (typeof window.createMascotRenderer !== 'function') {
            console.warn('[mascot] shared renderer not loaded — check renderer.js script tag');
            return;
        }

        const key = selectedModelKey();
        window.MASCOT_ACTIVE = { key, ...MASCOT_MODELS[key] };
        window.MASCOT_MODELS = MASCOT_MODELS;

        try {
            await window.createMascotRenderer({
                modelUrl: MASCOT_MODELS[key].modelUrl,
                canvasId: CANVAS_ID,
                width: canvas.width || 320,
                height: canvas.height || 440,
                backgroundAlpha: 0,
                fitWidth: (canvas.width || 320) - 40,
                idleMotion: 'Idle',
            });
            _restoreLastEmotion();
        } catch (err) {
            // renderer.js surfaces its own banner; the rest of the shell stays usable.
            console.warn('[mascot] shared renderer load failed:', err && err.message);
        }

        loadEmotionMap();
        connectWebSocket();
    }

    async function loadEmotionMap() {
        try {
            const response = await fetch(EMOTION_MAP_URL);
            if (response.ok) {
                window._emotionMap = await response.json();
            } else {
                throw new Error('HTTP ' + response.status);
            }
        } catch (err) {
            console.warn('[mascot] emotion_map fetch failed, using empty map:', err && err.message);
            window._emotionMap = {};
        }
    }

    function _restoreLastEmotion() {
        const model = getModel();
        if (!model) return;
        const raw = sessionStorage.getItem(STORAGE_KEY);
        if (!raw) return;
        try {
            const last = JSON.parse(raw);
            if (last.expression) model.expression(last.expression);
            if (last.state) model.motion(last.state);
        } catch (e) {
            console.warn('[mascot] sessionStorage restore failed:', e);
        }
    }

    function connectWebSocket() {
        if (isConnecting || retryCount > MAX_RETRIES) return;
        isConnecting = true;

        const wsUrl = window.MASCOT_WS_URL || DEFAULT_WS_URL;
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            retryCount = 0;
            isConnecting = false;
            console.log('[mascot] WS connected');
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                const model = getModel();
                switch (data.type) {
                    case 'SET_EXPRESSION':
                        if (model && data.expression) {
                            model.expression(data.expression);
                            _saveState(data.expression, null);
                        }
                        break;
                    case 'SET_STATE':
                        if (model && data.state) {
                            model.motion(data.state);
                            _saveState(null, data.state);
                        }
                        break;
                    case 'CONNECTED':
                        console.log('[mascot] WS handshake:', data.msg);
                        break;
                    default:
                        break;
                }
            } catch (err) {
                console.warn('[mascot] WS message parse error:', err);
            }
        };

        ws.onclose = () => {
            isConnecting = false;
            if (retryCount < MAX_RETRIES) {
                retryCount++;
                console.log('[mascot] WS closed, retry', retryCount + '/' + MAX_RETRIES, 'in', RETRY_DELAY + 'ms');
                setTimeout(connectWebSocket, RETRY_DELAY);
            } else {
                console.warn('[mascot] WS max retries reached');
            }
        };

        ws.onerror = (err) => {
            console.warn('[mascot] WS error:', err);
        };
    }

    function _saveState(expression, state) {
        try {
            const current = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || '{}');
            if (expression) current.expression = expression;
            if (state) current.state = state;
            sessionStorage.setItem(STORAGE_KEY, JSON.stringify(current));
        } catch (e) {
            console.warn('[mascot] sessionStorage write failed:', e);
        }
    }
})();
