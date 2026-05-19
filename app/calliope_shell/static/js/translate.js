// translate.js — Bilingual translate tab handler
(function () {
    'use strict';

    const API_URL = '/api/translate';

    function init() {
        const btnTranslate = document.getElementById('btn-translate');
        const inputEl = document.getElementById('translate-input');
        const outputEl = document.getElementById('translate-output');
        const statusEl = document.getElementById('translate-status');

        if (!btnTranslate) return;

        btnTranslate.addEventListener('click', async () => {
            const text = inputEl.value.trim();
            if (!text) {
                _setStatus(statusEl, 'error', 'Inserisci testo da tradurre.');
                return;
            }
            const direction = document.querySelector('input[name="translate-direction"]:checked')?.value || 'IT_to_EN';

            btnTranslate.disabled = true;
            outputEl.value = '';
            _setStatus(statusEl, 'loading', 'Traduzione in corso...');

            try {
                const resp = await fetch(API_URL, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({text, direction, context: 'fantasy_rp'}),
                });
                const data = await resp.json();
                if (!resp.ok) {
                    _setStatus(statusEl, 'error', data.error || 'Errore gateway.');
                } else {
                    outputEl.value = data.translation || '';
                    _setStatus(statusEl, 'done', `✓ ${data.model_used}`);
                }
            } catch (err) {
                _setStatus(statusEl, 'error', 'Errore connessione: ' + err.message);
            } finally {
                btnTranslate.disabled = false;
            }
        });
    }

    function _setStatus(el, type, msg) {
        if (!el) return;
        el.textContent = msg;
        el.className = 'translate-status ' + type;
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
