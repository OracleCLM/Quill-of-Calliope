// mascot.js — Calliope Live2D sidebar renderer + WebSocket emotion sync
(function () {
    'use strict';

    const CANVAS_ID = 'mascot';
    const MODEL_PATH = '/static/models/calliope/calliope.model3.json';
    const EMOTION_MAP_URL = '/api/mascot/emotion_map';
    const DEFAULT_WS_URL = 'ws://localhost:9876/mascot';
    const RETRY_DELAY = 3000;
    const MAX_RETRIES = 5;
    const STORAGE_KEY = 'mascot_last_emotion';

    const PIXI = window.PIXI;
    const Live2DModel = window.PIXI && window.PIXI.live2d ? window.PIXI.live2d.Live2DModel : null;

    let app = null;
    let model = null;
    let ws = null;
    let retryCount = 0;
    let isConnecting = false;
    window._emotionMap = {};

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

        if (!PIXI) {
            console.warn('[mascot] PIXI not loaded — CDN unavailable, skipping init');
            return;
        }

        app = new PIXI.Application({
            view: canvas,
            width: 320,
            height: 600,
            backgroundAlpha: 0,
            resolution: window.devicePixelRatio || 1,
            autoDensity: true,
        });

        try {
            const response = await fetch(EMOTION_MAP_URL);
            if (response.ok) {
                window._emotionMap = await response.json();
            } else {
                throw new Error('HTTP ' + response.status);
            }
        } catch (err) {
            console.warn('[mascot] emotion_map fetch failed, using empty map:', err.message);
            window._emotionMap = {};
        }

        if (Live2DModel) {
            try {
                model = await Live2DModel.from(MODEL_PATH);
                const scale = 280 / model.width;
                model.scale.set(scale);
                model.x = app.screen.width / 2;
                model.y = app.screen.height / 2;
                model.anchor.set(0.5);
                app.stage.addChild(model);

                const lastRaw = sessionStorage.getItem(STORAGE_KEY);
                if (lastRaw) {
                    try {
                        const last = JSON.parse(lastRaw);
                        if (last.expression) model.expression(last.expression);
                        if (last.state) model.motion(last.state);
                    } catch (e) {
                        console.warn('[mascot] sessionStorage restore failed:', e);
                    }
                }
            } catch (err) {
                console.warn('[mascot] Live2D model load failed, showing placeholder:', err.message);
                _drawPlaceholder();
            }
        } else {
            console.warn('[mascot] pixi-live2d-display not loaded, showing placeholder');
            _drawPlaceholder();
        }

        connectWebSocket();
    }

    function _drawPlaceholder() {
        const g = new PIXI.Graphics();
        g.beginFill(0xc0c0c0);
        g.drawCircle(160, 180, 70);
        g.endFill();
        g.beginFill(0x2c3e6b);
        g.drawRect(110, 255, 100, 130);
        g.endFill();
        g.beginFill(0x8b6914);
        g.drawRect(95, 105, 130, 25);
        g.endFill();
        app.stage.addChild(g);

        const label = new PIXI.Text('Calliope', {
            fontFamily: 'serif',
            fontSize: 18,
            fill: 0xffffff,
            align: 'center',
        });
        label.x = 160 - label.width / 2;
        label.y = 410;
        app.stage.addChild(label);

        const sub = new PIXI.Text('[ placeholder — model WIP ]', {
            fontFamily: 'sans-serif',
            fontSize: 10,
            fill: 0x888888,
            align: 'center',
        });
        sub.x = 160 - sub.width / 2;
        sub.y = 436;
        app.stage.addChild(sub);
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
