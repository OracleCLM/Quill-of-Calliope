/* M-D — Pannello-azioni CONTESTUALE del composer/editor di scena.
 *
 * UNA sola UI intelligente (NON 6 bottoni sparsi): quando l'operatore SELEZIONA
 * del testo nel compositore (`#scene-compose-text`) o in una bolla del thread
 * (`.msg-text`), compare un pannello fluttuante con i 6 verbi di scrittura che
 * espongono `POST /api/write` (assemblatore-prompt condiviso M-B) sul testo
 * selezionato. Il risultato è poi APPLICATO in-place (replace/insert) nel
 * compositore, oppure mostrato come avviso (coerenza).
 *
 * Mappa verbo -> payload /api/write -> campo-risultato -> modalità-applica:
 *   genera     intent_it=sel  -> draft_text   -> insert (dopo la selezione)
 *   continua   intent_it=sel  -> draft_text   -> insert
 *   rifinisci  text=sel       -> refined_text -> replace
 *   traduci    text=sel       -> translation  -> replace
 *   riassumi   text=sel       -> summary      -> replace
 *   coerenza   text=sel       -> issues[]     -> avviso (no applica)
 *
 * Sorgente selezione:
 *   - textarea compositore -> si può REPLACE/INSERT in-place.
 *   - bolla thread (read-only) -> "Inserisci nel compositore" (append).
 */
(function () {
    'use strict';

    var VERBS = [
        { key: 'genera',    label: '✦ Genera',    field: 'draft_text',   apply: 'insert',  intent: true  },
        { key: 'continua',  label: '➤ Continua',  field: 'draft_text',   apply: 'insert',  intent: true  },
        { key: 'rifinisci', label: '✎ Rifinisci', field: 'refined_text', apply: 'replace', intent: false },
        { key: 'traduci',   label: '🌐 Traduci',  field: 'translation',  apply: 'replace', intent: false },
        { key: 'riassumi',  label: '≣ Riassumi',  field: 'summary',      apply: 'replace', intent: false },
        { key: 'coerenza',  label: '⚖ Coerenza',  field: null,           apply: 'advise',  intent: false }
    ];

    // Stato della selezione corrente catturata all'apertura del pannello.
    var _sel = null;   // { text, source:'textarea'|'bubble', taStart, taEnd }
    var _pop = null;   // elemento DOM del pannello (singleton)

    function _charFocus() {
        var sel = document.getElementById('compose-char-select');
        if (sel && sel.value) {
            var opt = sel.options[sel.selectedIndex];
            return (opt && opt.dataset && opt.dataset.name) ? opt.dataset.name
                 : (opt ? opt.textContent : '');
        }
        return '';
    }

    function _escape(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    // ── Costruzione singleton del pannello ──────────────────────────────────
    function _ensurePop() {
        if (_pop) return _pop;
        _pop = document.createElement('div');
        _pop.className = 'write-actions-pop';
        _pop.style.display = 'none';
        var bar = document.createElement('div');
        bar.className = 'wa-bar';
        VERBS.forEach(function (v) {
            var b = document.createElement('button');
            b.className = 'wa-btn';
            b.textContent = v.label;
            b.title = v.key + ' — agisce sul testo selezionato';
            b.addEventListener('click', function (e) { e.preventDefault(); _runVerb(v); });
            bar.appendChild(b);
        });
        // Direzione traduzione (rilevante solo per "traduci"): compatta, accanto alla barra.
        var dir = document.createElement('select');
        dir.className = 'wa-dir';
        dir.title = 'Direzione traduzione';
        dir.innerHTML = '<option value="IT_to_EN">IT→EN</option>' +
                        '<option value="EN_to_IT">EN→IT</option>';
        bar.appendChild(dir);
        _pop.appendChild(bar);

        var res = document.createElement('div');
        res.className = 'wa-result';
        res.style.display = 'none';
        _pop.appendChild(res);

        document.body.appendChild(_pop);
        _pop._dir = dir;
        _pop._res = res;
        return _pop;
    }

    function _hide() {
        if (_pop) { _pop.style.display = 'none'; _pop._res.style.display = 'none'; _pop._res.innerHTML = ''; }
        _sel = null;
    }

    function _showAt(x, y) {
        var p = _ensurePop();
        p._res.style.display = 'none';
        p._res.innerHTML = '';
        p.style.display = 'block';
        // Clampa dentro il viewport.
        var maxX = window.scrollX + window.innerWidth - p.offsetWidth - 12;
        var px = Math.max(window.scrollX + 8, Math.min(x, maxX));
        p.style.left = px + 'px';
        p.style.top = (y + 10) + 'px';
    }

    // ── Rilevamento selezione ───────────────────────────────────────────────
    function _detectSelection() {
        var ta = document.getElementById('scene-compose-text');
        // 1) Selezione nel compositore (textarea): usa selectionStart/End.
        if (ta && document.activeElement === ta && ta.selectionStart !== ta.selectionEnd) {
            var t = ta.value.slice(ta.selectionStart, ta.selectionEnd).trim();
            if (t.length >= 2) {
                return { text: t, source: 'textarea', taStart: ta.selectionStart, taEnd: ta.selectionEnd };
            }
        }
        // 2) Selezione in una bolla del thread (read-only).
        var ws = window.getSelection ? window.getSelection() : null;
        if (ws && ws.rangeCount && !ws.isCollapsed) {
            var node = ws.anchorNode;
            var el = node && (node.nodeType === 1 ? node : node.parentElement);
            if (el && el.closest && el.closest('#scene-thread')) {
                var bt = ws.toString().trim();
                if (bt.length >= 2) return { text: bt, source: 'bubble' };
            }
        }
        return null;
    }

    function _onMouseUp(e) {
        // Click DENTRO il pannello: non ri-valutare (lascia agire i bottoni).
        if (e.target.closest && e.target.closest('.write-actions-pop')) return;
        // Ritarda: lascia che il browser finalizzi la selezione.
        setTimeout(function () {
            var sel = _detectSelection();
            if (sel) { _sel = sel; _showAt(e.pageX, e.pageY); }
            else { _hide(); }
        }, 0);
    }

    // ── Esecuzione di un verbo ──────────────────────────────────────────────
    function _runVerb(v) {
        if (!_sel) return;
        var sceneId = window._currentSceneId || '';
        var payload = { action: v.key, scene_id: sceneId, char_focus: _charFocus() };
        if (v.intent) payload.intent_it = _sel.text;
        else payload.text = _sel.text;
        if (v.key === 'traduci') payload.direction = _pop._dir.value;

        var res = _pop._res;
        res.style.display = 'block';
        res.innerHTML = '<div class="wa-status">… elaboro (' + _escape(v.key) + ')</div>';

        var caller = (typeof window.cloudCall === 'function') ? window.cloudCall : window.fetch;
        caller('/api/write', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        }, { kind: 'write_' + v.key }).then(function (r) {
            return r.json().then(function (d) { return { ok: r.ok, status: r.status, d: d }; });
        }).then(function (o) {
            if (!o.ok) {
                _renderError(v, (o.d && (o.d.error || o.d.message)) || ('HTTP ' + o.status));
                return;
            }
            if (v.apply === 'advise') { _renderCoerenza(o.d); return; }
            var out = (o.d && o.d[v.field]) || '';
            _renderResult(v, out);
        }).catch(function (err) {
            _renderError(v, (err && err.message) || 'errore di rete');
        });
    }

    function _renderError(v, msg) {
        _pop._res.innerHTML =
            '<div class="wa-error">⚠ ' + _escape(msg) + ' ' +
            '<button class="wa-retry">Riprova</button></div>';
        _pop._res.querySelector('.wa-retry').addEventListener('click', function () { _runVerb(v); });
    }

    function _renderResult(v, out) {
        if (!out) { _renderError(v, 'risposta vuota dal gateway'); return; }
        var fromBubble = (_sel.source === 'bubble');
        var applyLabel = fromBubble ? '↧ Inserisci nel compositore'
                       : (v.apply === 'replace' ? '✓ Sostituisci' : '✓ Inserisci');
        var res = _pop._res;
        res.innerHTML =
            '<div class="wa-preview"></div>' +
            '<div class="wa-actions">' +
            '  <button class="wa-apply">' + applyLabel + '</button>' +
            '  <button class="wa-cancel">Annulla</button>' +
            '</div>';
        res.querySelector('.wa-preview').textContent = out;
        res.querySelector('.wa-apply').addEventListener('click', function () { _apply(v, out); });
        res.querySelector('.wa-cancel').addEventListener('click', _hide);
    }

    function _renderCoerenza(d) {
        var coherent = d && d.coherent;
        var issues = (d && d.issues) || [];
        var html = '<div class="wa-coerenza ' + (coherent ? 'ok' : 'warn') + '">' +
            (coherent ? '✓ Coerente con personaggi e lore' : '⚠ Possibili incongruenze') + '</div>';
        if (issues.length) {
            html += '<ul class="wa-issues">' + issues.map(function (i) {
                var desc = (typeof i === 'string') ? i : (i.description || JSON.stringify(i));
                var sev = (i && i.severity) ? ('[' + i.severity + '] ') : '';
                return '<li>' + _escape(sev + desc) + '</li>';
            }).join('') + '</ul>';
        }
        html += '<div class="wa-actions"><button class="wa-cancel">Chiudi</button></div>';
        _pop._res.innerHTML = html;
        _pop._res.querySelector('.wa-cancel').addEventListener('click', _hide);
    }

    // ── Applicazione del risultato ──────────────────────────────────────────
    function _apply(v, out) {
        var ta = document.getElementById('scene-compose-text');
        if (!ta) { _hide(); return; }
        if (_sel.source === 'bubble') {
            // Bolla read-only: append al compositore.
            ta.value = (ta.value ? ta.value.replace(/\s*$/, '') + '\n\n' : '') + out;
        } else if (v.apply === 'replace') {
            var val = ta.value;
            ta.value = val.slice(0, _sel.taStart) + out + val.slice(_sel.taEnd);
        } else { // insert dopo la selezione
            var v2 = ta.value;
            ta.value = v2.slice(0, _sel.taEnd) + '\n\n' + out + v2.slice(_sel.taEnd);
        }
        ta.focus();
        ta.dispatchEvent(new Event('input', { bubbles: true }));
        _hide();
    }

    // ── Wiring ──────────────────────────────────────────────────────────────
    function _init() {
        document.addEventListener('mouseup', _onMouseUp);
        // ESC chiude il pannello.
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') _hide();
        });
        // Scroll del thread/pagina: chiudi per evitare pannelli orfani.
        window.addEventListener('scroll', _hide, true);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', _init);
    } else {
        _init();
    }

    // Esposto per i test/journey.
    window._writeActions = { detect: _detectSelection, verbs: VERBS, hide: _hide };
})();
