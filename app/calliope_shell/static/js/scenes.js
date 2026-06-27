// Scene/Messages panel — redesign lista-flat stile JanitorAI (GATED-1, 2026-06-25).
// Classic script (NON module): le function declarations restano globali e sono
// invocate da showView()/onclick inline. Dipendenze globali definite in shell.html
// (renderEmptyState, cloudCall, showView) sono disponibili a runtime (script caricato dopo).

function _escHtml(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// ── Scenes panel (Gap B) ──
window._currentSceneId = null;
let _allScenes = [];
let _scenesOffset = 0;
let _scenesTotal = 0;
const _SCENES_PAGE = 50;

async function _loadScenes() {
    const ul = document.getElementById('scenes-list');
    ul.innerHTML = '<li style="color:#334;padding:12px">Caricamento scene...</li>';
    _scenesOffset = 0;
    try {
        const resp = await fetch('/api/db/scenes?limit=' + _SCENES_PAGE + '&offset=0');
        const data = await resp.json();
        _allScenes = data.scenes || [];
        _scenesTotal = data.total || _allScenes.length;
        _renderSceneList(_allScenes);
        _updateLoadMoreBtn();
        _loadArcFilterOptions();
    } catch(e) {
        ul.innerHTML = '<li style="color:#f66;padding:12px">Errore: ' + e.message + '</li>';
    }
}

async function _loadMoreScenes() {
    _scenesOffset += _SCENES_PAGE;
    try {
        const resp = await fetch('/api/db/scenes?limit=' + _SCENES_PAGE + '&offset=' + _scenesOffset);
        const data = await resp.json();
        const more = data.scenes || [];
        _allScenes = _allScenes.concat(more);
        _scenesTotal = data.total || _scenesTotal;
        _renderSceneList(_getActiveSceneFilters());
        _updateLoadMoreBtn();
    } catch(e) {
        const info = document.getElementById('scenes-count-info');
        if (info) info.textContent = 'Errore: ' + e.message;
    }
}

function _updateLoadMoreBtn() {
    const div = document.getElementById('scenes-load-more');
    const info = document.getElementById('scenes-count-info');
    if (!div) return;
    const hasMore = _allScenes.length < _scenesTotal;
    div.style.display = hasMore ? 'block' : 'none';
    if (info) info.textContent = `Mostrate ${_allScenes.length} di ${_scenesTotal} scene`;
}

async function _cleanFixtureScenes() {
    const patterns = ['flow3', 'test_scene', 'fixture_'];
    if (!confirm(`Eliminare tutte le scene fixture test? (prefissi: ${patterns.join(', ')})`)) return;
    const btn = document.getElementById('btn-clean-fixtures');
    if (btn) btn.disabled = true;
    let total = 0;
    try {
        for (const p of patterns) {
            const r = await fetch('/api/db/scenes/batch-delete', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({pattern: p}),
            });
            if (r.ok) {
                const d = await r.json();
                total += d.deleted || 0;
            }
        }
        alert(`✓ Eliminate ${total} scene fixture. Ricarico lista.`);
        await _loadScenes();
    } catch(e) {
        alert('Errore: ' + e.message);
    } finally {
        if (btn) btn.disabled = false;
    }
}

async function _loadArcFilterOptions(editSel = null) {
    const sel = document.getElementById('scene-arc-filter');
    if (!sel && !editSel) return;
    try {
        const r = await fetch('/api/db/arcs');
        const d = await r.json();
        const arcs = d.arcs || [];
        const optHtml = arcs.map(a =>
            `<option value="${_escHtml(String(a.id))}">${_escHtml(a.title || a.id)}</option>`
        ).join('');
        if (sel) sel.innerHTML = '<option value="">— Tutti gli archi —</option>' + optHtml;
        if (editSel) editSel.innerHTML = '<option value="">— Nessun arco —</option>' + optHtml;
    } catch(_) {}
}

function _getActiveSceneFilters() {
    const hasMsgEl = document.getElementById('scene-has-msg-filter');
    const hasMsg = hasMsgEl ? hasMsgEl.checked : false;
    const arc = document.getElementById('scene-arc-filter');
    const arcId = arc ? arc.value : '';
    const txt = document.getElementById('scene-filter');
    const f = txt ? txt.value.toLowerCase() : '';
    let base = hasMsg ? _allScenes.filter(s => (s.message_count || 0) > 0) : _allScenes;
    if (arcId) base = base.filter(s => s.arc_id === arcId);
    if (f) base = base.filter(s =>
        (s.title||'').toLowerCase().includes(f) ||
        (s.summary||'').toLowerCase().includes(f) ||
        (s.participants||[]).some(p => p.toLowerCase().includes(f))
    );
    return base;
}

function _scenesArcFilter(_arcId) {
    _renderSceneList(_getActiveSceneFilters());
}

function _scenesHasMsgFilter(_checked) {
    _renderSceneList(_getActiveSceneFilters());
}

function _renderSceneList(scenes) {
    const ul = document.getElementById('scenes-list');
    if (!scenes.length) {
        renderEmptyState('scenes-list', {
            icon: '◆', title: 'Nessuna scena',
            hint: 'Importa scene da Discord/Excel con scripts/import_discord_history.py o crea una nuova scena dal tab Draft.',
        });
        return;
    }
    ul.innerHTML = scenes.map(s => {
        const readonly = s.is_readonly === 1;
        const col = readonly ? '#667' : '#4c8';
        const label = readonly ? 'legacy' : 'active';
        const msgCount = s.message_count != null ? ` · ${s.message_count} msg` : '';
        return `
        <li onclick="_loadSceneDetail('${s.id}')">
            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${col};margin-right:6px;vertical-align:middle"></span>
            <span class="scene-item-title">${_escHtml(s.title || s.id)}</span>
            <div class="scene-item-meta">${label}${msgCount}</div>
        </li>`;
    }).join('');
}

function _scenesFilter(_val) {
    _renderSceneList(_getActiveSceneFilters());
}

function _newSceneInline() {
    document.getElementById('new-scene-form').style.display = 'block';
    document.getElementById('new-scene-title').focus();
}

function _cancelNewScene() {
    document.getElementById('new-scene-form').style.display = 'none';
    document.getElementById('new-scene-title').value = '';
    document.getElementById('new-scene-location').value = '';
    document.getElementById('new-scene-status').textContent = '';
}

async function _submitNewScene() {
    const title = (document.getElementById('new-scene-title').value || '').trim();
    const location = (document.getElementById('new-scene-location').value || '').trim() || undefined;
    const status = document.getElementById('new-scene-status');
    if (!title) { status.textContent = '⚠ Titolo obbligatorio.'; return; }
    status.textContent = 'Creazione…';
    try {
        const resp = await fetch('/api/db/scenes', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({title, location}),
        });
        const data = await resp.json();
        if (!resp.ok) { status.textContent = '✗ ' + (data.error || resp.status); return; }
        _cancelNewScene();
        await _loadScenes();
        _loadSceneDetail(data.id);
    } catch(e) {
        status.textContent = '✗ ' + e.message;
    }
}

// ── Chat thread renderer ──────────────────────────────────────────────────────

function _fmtTs(ts) {
    if (!ts) return '';
    try {
        const d = new Date(ts.includes('T') ? ts : ts + 'Z');
        return d.toLocaleTimeString('it-IT', {hour:'2-digit', minute:'2-digit'});
    } catch (_) { return ''; }
}

function _renderChatThread(messages) {
    const thread = document.getElementById('chat-thread');
    if (!messages.length) {
        thread.innerHTML = '<div style="color:#334;padding:16px;text-align:center;font-size:.85em;">Nessun messaggio in questa scena</div>';
        return;
    }
    thread.innerHTML = messages.map(m => {
        const isSummary = m.is_summary === 1 || m.is_summary === true;
        const isDiscord = (m.source || '') === 'discord';
        const body = (m.content_enhanced && m.content_enhanced !== m.content_original)
            ? m.content_enhanced : (m.content_original || '');
        const hasEnhanced = m.content_enhanced && m.content_enhanced !== m.content_original;
        const msgStyle = isSummary
            ? 'background:#111d11;border:1px solid #2a442a;'
            : 'background:#111827;border:1px solid #1e2f4a;';
        const srcBadge = isDiscord
            ? '<span style="font-size:.7em;color:#7788cc;margin-left:6px;vertical-align:middle">discord</span>'
            : '';
        const enhBadge = hasEnhanced
            ? '<span style="font-size:.7em;color:#aa88cc;margin-left:6px;vertical-align:middle" title="testo raffinato">✎</span>'
            : '';
        const ts = _fmtTs(m.ts);
        const mid = m.id || '';
        return `<div class="chat-msg" id="msg-${_escHtml(mid)}">
            <div class="chat-msg-author">${_escHtml(m.author_name || '?')}${srcBadge}${enhBadge}<span style="float:right;font-size:.72em;color:#445;font-weight:normal">${_escHtml(ts)}</span></div>
            <div class="chat-msg-content" style="${msgStyle}border-radius:8px;padding:8px 12px;font-size:.87em;color:#ccd;white-space:pre-wrap;line-height:1.5;">${_escHtml(body)}</div>
            <div class="chat-msg-actions" style="display:none;gap:4px;margin-top:4px;">
                <button onclick="_editMsgInline('${_escHtml(mid)}')" style="background:#1a2a3a;color:#aac;border:1px solid #2a3a5a;border-radius:4px;padding:2px 8px;cursor:pointer;font-size:.72em;">✎ Modifica</button>
                <button onclick="_deleteMsg('${_escHtml(mid)}')" style="background:#2a1a1a;color:#c66;border:1px solid #4a2a2a;border-radius:4px;padding:2px 8px;cursor:pointer;font-size:.72em;">✕ Elimina</button>
            </div>
        </div>`;
    }).join('');
    thread.querySelectorAll('.chat-msg').forEach(el => {
        el.addEventListener('mouseenter', () => {
            const btns = el.querySelector('.chat-msg-actions');
            if (btns) btns.style.display = 'flex';
        });
        el.addEventListener('mouseleave', () => {
            const btns = el.querySelector('.chat-msg-actions');
            if (btns) btns.style.display = 'none';
        });
    });
    thread.scrollTop = thread.scrollHeight;
}

window._deleteMsg = async function(msgId) {
    if (!msgId || !confirm('Elimina messaggio?')) return;
    const r = await fetch('/api/db/messages/' + encodeURIComponent(msgId), {method: 'DELETE'});
    if (r.ok || r.status === 204) await _loadSceneDetail(window._currentSceneId);
};

window._editMsgInline = function(msgId) {
    const el = document.getElementById('msg-' + msgId);
    if (!el) return;
    const contentEl = el.querySelector('.chat-msg-content');
    if (!contentEl) return;
    const currentText = contentEl.textContent;
    const ta = document.createElement('textarea');
    ta.value = currentText;
    ta.rows = 3;
    ta.style.cssText = 'width:100%;box-sizing:border-box;background:#111827;color:#eee;border:1px solid #2a3a5a;border-radius:6px;padding:6px;font-size:.85em;resize:vertical;margin-top:4px;';
    const saveBtn = document.createElement('button');
    saveBtn.textContent = '✓ Salva';
    saveBtn.style.cssText = 'background:#1a3a1a;color:#8f8;border:1px solid #2a5a2a;border-radius:4px;padding:3px 10px;cursor:pointer;font-size:.75em;margin-top:4px;margin-right:6px;';
    const cancelBtn = document.createElement('button');
    cancelBtn.textContent = 'Annulla';
    cancelBtn.style.cssText = 'background:#1a2a3a;color:#aab;border:1px solid #2a3a5a;border-radius:4px;padding:3px 8px;cursor:pointer;font-size:.75em;margin-top:4px;';
    saveBtn.onclick = async () => {
        const r = await fetch('/api/db/messages/' + encodeURIComponent(msgId), {
            method: 'PATCH', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({content_original: ta.value}),
        });
        if (r.ok) await _loadSceneDetail(window._currentSceneId);
    };
    cancelBtn.onclick = () => _loadSceneDetail(window._currentSceneId);
    contentEl.replaceWith(ta);
    el.querySelector('.chat-msg-actions').after(saveBtn);
    saveBtn.after(cancelBtn);
};

// FE-3: append nuovo messaggio → POST /api/db/scenes/<id>/messages
async function _appendMessage() {
    const sceneId = window._currentSceneId;
    if (!sceneId) return;
    const author = (document.getElementById('compose-author').value || '').trim();
    const content = (document.getElementById('compose-content').value || '').trim();
    const status = document.getElementById('compose-status');
    if (!author || !content) { status.textContent = '⚠ Autore e testo obbligatori.'; return; }
    status.textContent = 'Invio…';
    try {
        const composeWho = document.getElementById('compose-who');
        const selectedOpt = composeWho && composeWho.options[composeWho.selectedIndex];
        const charId = (selectedOpt && selectedOpt.dataset.charId) || undefined;
        const msgBody = {author_name: author, content_original: content};
        if (charId) msgBody.character_id = charId;
        const resp = await fetch('/api/db/scenes/' + encodeURIComponent(sceneId) + '/messages', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(msgBody),
        });
        const data = await resp.json();
        if (!resp.ok) { status.textContent = '✗ ' + (data.error || resp.status); return; }
        status.textContent = '✓ Inviato';
        document.getElementById('compose-content').value = '';
        await _loadSceneDetail(sceneId);
    } catch(e) {
        status.textContent = '✗ ' + e.message;
    }
}

async function _loadSceneDetail(sceneId) {
    window._currentSceneId = sceneId;
    document.getElementById('scene-empty-state').style.display = 'none';
    document.getElementById('scene-detail').style.display = 'block';
    document.getElementById('scene-detail-title').textContent = '…';
    try {
        // GET /api/db/scenes/<id> → {scene:{...}, messages:[...]}
        const resp = await fetch('/api/db/scenes/' + encodeURIComponent(sceneId));
        const data = await resp.json();
        if (data.error) throw new Error(data.error);
        const s = data.scene || {};
        const messages = data.messages || [];
        window._currentScene = s;
        window._currentSceneMessages = messages;
        document.getElementById('scene-detail-title').textContent = s.title || sceneId;
        document.getElementById('scene-detail-meta').textContent =
            `ID: ${s.id} | ${s.location || ''} | ${messages.length} msg`;
        const arcBadge = document.getElementById('scene-arc-badge');
        if (arcBadge) {
            if (s.arc_id) {
                arcBadge.innerHTML = `<span style="font-size:.75em;background:#1a1a2e;color:#8899cc;border:1px solid #2a3a5a;border-radius:10px;padding:2px 10px;cursor:pointer;" onclick="showView('arc')" title="Vai all'arco">📚 ${_escapeHtml(s.arc_id)}</span>`;
                arcBadge.style.display = 'block';
            } else {
                arcBadge.style.display = 'none';
            }
        }
        // C1: render del thread-chat (bolle ordinate) + reset compose.
        _renderChatThread(messages);
        const ct = document.getElementById('scene-compose-text');
        if (ct) ct.value = '';
        const cs = document.getElementById('scene-compose-status');
        if (cs) cs.textContent = '';
        document.getElementById('scene-detail-summary').textContent =
            messages.map(m => `${m.author_name}: ${m.content_original}`).join('\n') || '(nessun messaggio)';
        document.getElementById('scene-detail-first').textContent = messages[0] ? messages[0].content_original : '—';
        document.getElementById('scene-detail-last').textContent =
            messages.length ? messages[messages.length - 1].content_original : '—';
        // Roster personaggi-in-scena: chip + compose-select + add-select (binding manuale).
        let roster = [];
        try {
            const rresp = await fetch('/api/db/scenes/' + encodeURIComponent(sceneId) + '/characters');
            const rdata = await rresp.json();
            roster = rdata.characters || [];
        } catch (e) { /* roster opzionale */ }
        _renderRoster(sceneId, roster);
        await _populateRosterAddSelect(sceneId, roster);
        _loadWriteModel();
    } catch(e) {
        document.getElementById('scene-detail-title').textContent = 'Errore: ' + e.message;
        document.getElementById('chat-thread').innerHTML = '';
    }
}

// ── GAP-5: switch modello-scrittura cloud/locale (VISION decisione #4) ──
async function _loadWriteModel() {
    const sel = document.getElementById('write-profile-select');
    const lbl = document.getElementById('write-model-label');
    if (!sel) return;
    try {
        const r = await fetch('/api/scene-chat/write-model');
        const d = await r.json();
        sel.value = d.profile || 'cloud';
        if (lbl) lbl.textContent = '(' + (d.provider || '?') + '/' + (d.model || '?') + ')';
    } catch (e) { /* non-fatale */ }
}

async function _setWriteProfile(profile) {
    const lbl = document.getElementById('write-model-label');
    try {
        const r = await fetch('/api/scene-chat/write-model', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ profile }),
        });
        const d = await r.json();
        if (!r.ok) throw new Error(d.error || ('HTTP ' + r.status));
        if (lbl) lbl.textContent = '(' + (d.provider || '?') + '/' + (d.model || '?') + ')';
    } catch (e) {
        if (lbl) lbl.textContent = '(errore)';
    }
}

// ── Roster scena (binding manuale personaggio↔scena) ──
// Sblocca: scrivere COME un personaggio + retrieval delle schede-attive nel refine.
function _renderRoster(sceneId, roster) {
    const chips = document.getElementById('scene-roster-chips');
    const composeSel = document.getElementById('compose-char-select');
    if (composeSel) composeSel.innerHTML = '<option value="">— Personaggio —</option>';
    if (chips) {
        if (!roster.length) {
            chips.innerHTML = '<span class="roster-empty">nessuno — aggiungine uno per scrivere come personaggio</span>';
        } else {
            chips.innerHTML = roster.map(c =>
                '<span class="roster-chip">' + _escapeHtml(c.name) +
                '<span class="chip-x" title="Rimuovi dalla scena" onclick="_removeCharFromScene(\'' +
                _escapeHtml(c.id) + '\')">×</span></span>'
            ).join('');
        }
    }
    roster.forEach(c => {
        if (composeSel) {
            const o = document.createElement('option');
            o.value = c.id; o.textContent = c.name; o.dataset.name = c.name;
            composeSel.appendChild(o);
        }
    });
}

async function _populateRosterAddSelect(sceneId, roster) {
    const sel = document.getElementById('roster-add-select');
    if (!sel) return;
    sel.innerHTML = '<option value="">＋ Aggiungi personaggio…</option>';
    const inRoster = new Set(roster.map(c => c.id));
    try {
        const r = await fetch('/api/db/characters');
        if (!r.ok) return;
        const d = await r.json();
        (d.characters || []).filter(c => !inRoster.has(c.id)).forEach(c => {
            const o = document.createElement('option');
            o.value = c.id; o.textContent = c.name;
            sel.appendChild(o);
        });
    } catch (e) { /* lista opzionale */ }
}

async function _addCharToScene(charId) {
    const sceneId = window._currentSceneId;
    if (!sceneId || !charId) return;
    try {
        const r = await fetch('/api/db/scenes/' + encodeURIComponent(sceneId) + '/characters', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ character_id: charId }),
        });
        if (!r.ok && r.status !== 409) {
            const d = await r.json().catch(() => ({}));
            throw new Error(d.error || ('HTTP ' + r.status));
        }
        await _loadSceneDetail(sceneId);   // ricarica roster + compose-select
    } catch (e) {
        window.alert('Errore aggiunta personaggio: ' + e.message);
    }
}

async function _removeCharFromScene(charId) {
    const sceneId = window._currentSceneId;
    if (!sceneId || !charId) return;
    try {
        await fetch('/api/db/scenes/' + encodeURIComponent(sceneId) + '/characters/' +
            encodeURIComponent(charId), { method: 'DELETE' });
        await _loadSceneDetail(sceneId);
    } catch (e) { /* non-fatale */ }
}

// ── C1: chat-thread render + compose narratore/personaggio ──

// Inizializza colorato dell'avatar (primo carattere autore) — placeholder; avatar
// immagine pieno = goal evolutivo JanitorAI.
function _msgAvatarChar(name) {
    return (name || '?').trim().charAt(0).toUpperCase() || '?';
}

function _renderSceneThread(messages) {
    const wrap = document.getElementById('scene-thread');
    if (!wrap) return;
    if (!messages || !messages.length) {
        wrap.innerHTML = '<div style="color:#445;font-size:.85em;padding:8px">(scena vuota — scrivi il primo messaggio)</div>';
        return;
    }
    wrap.innerHTML = messages.map(m => {
        const author = m.author_name || 'Narratore';
        // Narratore = nessun character_id associato → stile dedicato.
        const isNarrator = !m.character_id;
        const text = (m.content_enhanced && m.content_enhanced.trim())
            ? m.content_enhanced : (m.content_original || '');
        const mid = m.id || '';
        const alreadyRefined = m.content_enhanced && m.content_enhanced.trim();
        return `
        <div class="msg-bubble ${isNarrator ? 'msg-narrator' : ''}" data-mid="${_escapeHtml(mid)}">
            <div class="msg-avatar">${_escapeHtml(_msgAvatarChar(author))}</div>
            <div class="msg-body">
                <div class="msg-author">${_escapeHtml(author)}</div>
                <div class="msg-text">${_escapeHtml(text)}</div>
                <div class="msg-actions">
                    <button class="msg-refine-btn" onclick="_refineMessage('${_escapeHtml(mid)}', this)">✦ raffina</button>
                    ${alreadyRefined ? '<span class="msg-refined-tag">✓ raffinato</span>' : ''}
                </div>
                <div class="msg-refined" style="display:none"></div>
            </div>
        </div>`;
    }).join('');
    // Scrolla all'ultimo messaggio.
    wrap.scrollTop = wrap.scrollHeight;
}

function _escapeHtml(s) {
    return String(s == null ? '' : s)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function _setComposeRole(role) {
    const composeSel = document.getElementById('compose-char-select');
    if (!composeSel) return;
    composeSel.disabled = (role !== 'character');
    if (role !== 'character') composeSel.value = '';
}

// R2: raffina un singolo messaggio via route E3 (POST .../<mid>/refine).
// Mostra originale + raffinato con toggle; content_enhanced è già persistito server-side.
async function _refineMessage(mid, btn) {
    const sceneId = window._currentSceneId;
    if (!sceneId || !mid) return;
    const bubble = btn.closest('.msg-bubble');
    const panel = bubble.querySelector('.msg-refined');
    const oldLabel = btn.textContent;
    btn.disabled = true;
    btn.textContent = '… raffino';
    try {
        const resp = await fetch('/api/db/scenes/' + encodeURIComponent(sceneId) +
            '/messages/' + encodeURIComponent(mid) + '/refine', { method: 'POST' });
        const data = await resp.json().catch(() => ({}));
        if (!resp.ok) {
            // Messaggio-utente PULITO (gateway sovraccarico ecc.) + affordance Riprova.
            const userMsg = data.message || data.error || ('Errore di rete (' + resp.status + ')');
            panel.style.display = 'block';
            panel.innerHTML = '<div class="msg-refined-error">⚠ ' + _escapeHtml(userMsg) + ' ' +
                '<button class="msg-refine-retry">Riprova</button></div>';
            panel.querySelector('.msg-refine-retry').onclick = () => _refineMessage(mid, btn);
            btn.textContent = oldLabel;
            return;
        }
        panel.dataset.original = data.content_original || '';
        panel.dataset.refined = data.content_enhanced || '';
        panel.dataset.showing = 'refined';
        panel.innerHTML =
            '<div class="msg-refined-label">✦ Raffinato (salvato) — ' +
            '<a href="#" onclick="return _toggleRefined(this)">vedi originale</a></div>' +
            '<div class="msg-refined-text">' + _escapeHtml(panel.dataset.refined) + '</div>';
        panel.style.display = 'block';
        btn.textContent = '✓ raffinato';
    } catch (e) {
        // Errore imprevisto (rete): messaggio pulito, mai DOM rotto.
        panel.style.display = 'block';
        panel.innerHTML = '<div class="msg-refined-error">⚠ Impossibile raffinare ora. ' +
            '<button class="msg-refine-retry">Riprova</button></div>';
        panel.querySelector('.msg-refine-retry').onclick = () => _refineMessage(mid, btn);
        btn.textContent = oldLabel;
    } finally {
        btn.disabled = false;
    }
}

function _toggleRefined(a) {
    const panel = a.closest('.msg-refined');
    const txt = panel.querySelector('.msg-refined-text');
    const label = panel.querySelector('.msg-refined-label');
    if (panel.dataset.showing === 'refined') {
        txt.textContent = panel.dataset.original;
        label.innerHTML = '◦ Originale — <a href="#" onclick="return _toggleRefined(this)">vedi raffinato</a>';
        panel.dataset.showing = 'original';
    } else {
        txt.textContent = panel.dataset.refined;
        label.innerHTML = '✦ Raffinato (salvato) — <a href="#" onclick="return _toggleRefined(this)">vedi originale</a>';
        panel.dataset.showing = 'refined';
    }
    return false;
}

async function _sendSceneMessage() {
    const sceneId = window._currentSceneId;
    if (!sceneId) return;
    const textEl = document.getElementById('scene-compose-text');
    const statusEl = document.getElementById('scene-compose-status');
    const btn = document.getElementById('scene-send-btn');
    const content = (textEl.value || '').trim();
    if (!content) { statusEl.textContent = 'Scrivi qualcosa prima di inviare.'; return; }

    const roleEl = document.querySelector('input[name="compose-role"]:checked');
    const role = roleEl ? roleEl.value : 'narrator';
    let author_name = 'Narratore';
    let character_id = null;
    if (role === 'character') {
        const composeSel = document.getElementById('compose-char-select');
        if (!composeSel.value) { statusEl.textContent = 'Seleziona un personaggio.'; return; }
        character_id = composeSel.value;
        const opt = composeSel.options[composeSel.selectedIndex];
        author_name = (opt && opt.dataset.name) ? opt.dataset.name : opt.textContent;
    }

    btn.disabled = true;
    statusEl.textContent = 'Invio…';
    try {
        const resp = await fetch('/api/db/scenes/' + encodeURIComponent(sceneId) + '/messages', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ author_name, content_original: content, character_id }),
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error || ('HTTP ' + resp.status));
        textEl.value = '';
        statusEl.textContent = 'Inviato.';
        // Ricarica il thread per mostrare il nuovo messaggio in coda.
        await _loadSceneDetail(sceneId);
    } catch (e) {
        statusEl.textContent = 'Errore: ' + e.message;
    } finally {
        btn.disabled = false;
    }
}

// ── Affordance: crea-scena / crea-personaggio (flussi resi visibili in UI) ──
async function _createScene() {
    const title = (window.prompt('Titolo della nuova scena:') || '').trim();
    if (!title) return;
    try {
        const r = await fetch('/api/db/scenes', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ title }),
        });
        const d = await r.json();
        if (!r.ok) throw new Error(d.error || ('HTTP ' + r.status));
        await _loadScenes();
        _loadSceneDetail(d.id);   // apre subito la scena nuova
    } catch (e) {
        window.alert('Errore creazione scena: ' + e.message);
    }
}

async function _createCharacter() {
    const name = (window.prompt('Nome del nuovo personaggio (anche scheda di altro giocatore):') || '').trim();
    if (!name) return;
    try {
        // GAP-6 unify: crea in DB (identità/roster -> BINDABILE alla scena) E in YAML
        // (griglia Personaggi + scheda-ricca editabile). Stesso nome = stesso personaggio.
        const [rdb, ryaml] = await Promise.all([
            fetch('/api/db/characters', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ name, kind: 'player' }),
            }),
            fetch('/api/characters', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ name }),
            }),
        ]);
        if (!rdb.ok && rdb.status !== 409) {
            const d = await rdb.json().catch(() => ({}));
            throw new Error(d.error || ('HTTP ' + rdb.status));
        }
        if (!ryaml.ok) {
            const d = await ryaml.json().catch(() => ({}));
            throw new Error(d.error || ('HTTP ' + ryaml.status));
        }
        if (typeof loadCharactersPanel === 'function') loadCharactersPanel();
        if (typeof loadCharList === 'function') loadCharList();
        window.alert('Personaggio "' + name + '" creato (visibile in griglia e aggiungibile alle scene). Aprilo per compilarne la scheda.');
    } catch (e) {
        window.alert('Errore creazione personaggio: ' + e.message);
    }
}

// ── GAP-4: importer Discord in-UI (scan -> preview per-canale -> selezione -> import in scena) ──
let _importDir = '';

async function _importScan() {
    const dir = (document.getElementById('import-dir').value || '').trim();
    const filesEl = document.getElementById('import-files');
    if (!dir) { filesEl.innerHTML = '<span style="color:#a66;font-size:.82em">Indica una cartella.</span>'; return; }
    _importDir = dir;
    filesEl.innerHTML = '<span style="color:#556;font-size:.82em">Scansione…</span>';
    try {
        const r = await fetch('/api/import/discord/scan', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ dir }),
        });
        const d = await r.json();
        if (!r.ok) throw new Error(d.error || ('HTTP ' + r.status));
        if (!d.files.length) { filesEl.innerHTML = '<span style="color:#556;font-size:.82em">Nessun *.json nella cartella.</span>'; return; }
        filesEl.innerHTML = d.files.map(f =>
            '<button class="import-file-chip" onclick="_importPreview(\'' + _escapeHtml(f.file).replace(/'/g, "\\'") + '\')" ' +
            'style="background:#1a2440;color:#cde;border:1px solid #2a3a5a;border-radius:6px;padding:6px 10px;cursor:pointer;font-size:.8em;">' +
            _escapeHtml(f.channel || f.file) + (f.count != null ? ' (' + f.count + ')' : '') + '</button>'
        ).join('');
    } catch (e) {
        filesEl.innerHTML = '<span style="color:#f66;font-size:.82em">Errore: ' + _escapeHtml(e.message) + '</span>';
    }
}

async function _importPreview(file) {
    const area = document.getElementById('import-preview-area');
    const msgsEl = document.getElementById('import-messages');
    area.style.display = 'flex';
    msgsEl.innerHTML = '<span style="color:#556;font-size:.82em">Caricamento anteprima…</span>';
    // popola le scene-destinazione
    const sceneSel = document.getElementById('import-target-scene');
    try {
        const sr = await fetch('/api/db/scenes'); const sd = await sr.json();
        sceneSel.innerHTML = '<option value="">— Scena destinazione —</option>' +
            (sd.scenes || []).map(s => '<option value="' + _escapeHtml(s.id) + '">' + _escapeHtml(s.title || s.id) + '</option>').join('');
    } catch (e) { /* opzionale */ }
    try {
        const r = await fetch('/api/import/discord/preview', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ dir: _importDir, file }),
        });
        const d = await r.json();
        if (!r.ok) throw new Error(d.error || ('HTTP ' + r.status));
        msgsEl.innerHTML = (d.messages || []).map((m, i) =>
            '<label class="import-msg" data-search="' + _escapeHtml((m.author_name + ' ' + m.content).toLowerCase()) + '" ' +
            'style="display:flex;gap:8px;align-items:flex-start;padding:4px 2px;border-bottom:1px solid #141c2c;font-size:.82em;">' +
            '<input type="checkbox" class="import-cb" data-i="' + i + '" checked>' +
            '<span><b style="color:#88aaff">' + _escapeHtml(m.author_name || '—') + '</b> ' +
            '<span style="color:#566;font-size:.92em">' + _escapeHtml((m.timestamp || '').slice(0, 16)) + '</span><br>' +
            '<span style="color:#cdd">' + _escapeHtml(m.content || '') + '</span></span></label>'
        ).join('');
        // tieni i dati per l'import
        msgsEl._messages = d.messages || [];
        document.getElementById('import-status').textContent = d.count + ' messaggi nel canale "' + (d.channel || '') + '"';
    } catch (e) {
        msgsEl.innerHTML = '<span style="color:#f66;font-size:.82em">Errore: ' + _escapeHtml(e.message) + '</span>';
    }
}

function _importFilter() {
    const f = (document.getElementById('import-filter').value || '').toLowerCase();
    document.querySelectorAll('#import-messages .import-msg').forEach(el => {
        el.style.display = (!f || (el.dataset.search || '').includes(f)) ? 'flex' : 'none';
    });
}

function _importToggleAll(checked) {
    document.querySelectorAll('#import-messages .import-msg').forEach(el => {
        if (el.style.display !== 'none') el.querySelector('.import-cb').checked = checked;
    });
}

async function _importSelected() {
    const sceneId = document.getElementById('import-target-scene').value;
    const statusEl = document.getElementById('import-status');
    const msgsEl = document.getElementById('import-messages');
    if (!sceneId) { statusEl.textContent = 'Scegli una scena destinazione.'; return; }
    const all = msgsEl._messages || [];
    const selected = [];
    document.querySelectorAll('#import-messages .import-cb').forEach(cb => {
        if (cb.checked) {
            const m = all[parseInt(cb.dataset.i, 10)];
            if (m) selected.push({ author_name: m.author_name, content: m.content, timestamp: m.timestamp });
        }
    });
    if (!selected.length) { statusEl.textContent = 'Nessun messaggio selezionato.'; return; }
    statusEl.textContent = 'Import in corso…';
    try {
        const r = await fetch('/api/import/discord/to-scene', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ scene_id: sceneId, messages: selected }),
        });
        const d = await r.json();
        if (!r.ok) throw new Error(d.error || ('HTTP ' + r.status));
        statusEl.textContent = '✓ Importati ' + d.imported + ' messaggi nella scena.';
    } catch (e) {
        statusEl.textContent = 'Errore: ' + e.message;
    }
}

// Affordance informativa legacy (non più usata in UI — tenuta per riferimento CLI).
function _importInfo() {
    window.alert(
        'Importa storico Discord\n\n' +
        'CLI alternativa:\n  python scripts/import_discord_history.py\n'
    );
}

// "+ Roster": mostra form con dropdown di tutti i personaggi DB
window._showAddRoster = async function() {
    const form = document.getElementById('add-roster-form');
    const sel = document.getElementById('add-roster-char-sel');
    if (!form || !sel) return;
    sel.innerHTML = '<option value="">— Personaggio —</option>';
    try {
        const r = await fetch('/api/db/characters');
        const d = await r.json();
        (d.characters || []).forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.id; opt.textContent = c.name;
            sel.appendChild(opt);
        });
    } catch(_) {}
    form.style.display = 'flex';
};

window._addToRoster = async function() {
    const sceneId = window._currentSceneId;
    const charSel = document.getElementById('add-roster-char-sel');
    const roleSel = document.getElementById('add-roster-role-sel');
    const statusEl = document.getElementById('add-roster-status');
    if (!sceneId || !charSel || !charSel.value) {
        if (statusEl) statusEl.textContent = '⚠ Seleziona personaggio';
        return;
    }
    if (statusEl) statusEl.textContent = 'Aggiunta…';
    try {
        const r = await fetch('/api/db/scenes/' + encodeURIComponent(sceneId) + '/characters', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({character_id: charSel.value, role: roleSel.value}),
        });
        if (r.ok || r.status === 409) {
            document.getElementById('add-roster-form').style.display = 'none';
            await _loadSceneDetail(sceneId);
        } else {
            const d = await r.json();
            if (statusEl) statusEl.textContent = '✗ ' + (d.error || r.status);
        }
    } catch(e) {
        if (statusEl) statusEl.textContent = '✗ ' + e.message;
    }
};

window._removeFromRoster = async function(charId) {
    const sceneId = window._currentSceneId;
    if (!sceneId) return;
    try {
        const r = await fetch('/api/db/scenes/' + encodeURIComponent(sceneId) + '/characters/' + encodeURIComponent(charId), {method: 'DELETE'});
        if (r.ok) await _loadSceneDetail(sceneId);
    } catch(e) { /* silenzioso */ }
};

window._toggleSceneEdit = function() {
    const form = document.getElementById('scene-edit-form');
    const s = window._currentScene || {};
    if (!form) return;
    if (form.style.display === 'none' || !form.style.display) {
        const titleIn = document.getElementById('scene-edit-title');
        const locIn = document.getElementById('scene-edit-location');
        const arcSel = document.getElementById('scene-edit-arc');
        if (titleIn) titleIn.value = s.title || '';
        if (locIn) locIn.value = s.location || '';
        if (arcSel) {
            _loadArcFilterOptions(arcSel).then(() => {
                if (s.arc_id) arcSel.value = s.arc_id;
            });
        }
        form.style.display = 'flex';
        if (titleIn) titleIn.focus();
    } else {
        form.style.display = 'none';
    }
};

window._saveSceneEdit = async function() {
    const sceneId = window._currentSceneId;
    if (!sceneId) return;
    const title = (document.getElementById('scene-edit-title').value || '').trim();
    const location = (document.getElementById('scene-edit-location').value || '').trim();
    const arcSel = document.getElementById('scene-edit-arc');
    const arcId = arcSel ? (arcSel.value || null) : undefined;
    const statusEl = document.getElementById('scene-edit-status');
    if (!title) { if (statusEl) statusEl.textContent = '⚠ Titolo obbligatorio'; return; }
    if (statusEl) statusEl.textContent = 'Salvataggio…';
    try {
        const body = {title};
        if (location !== undefined) body.location = location || null;
        if (arcId !== undefined) body.arc_id = arcId;
        const r = await fetch('/api/db/scenes/' + encodeURIComponent(sceneId), {
            method: 'PATCH',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(body),
        });
        if (r.ok) {
            document.getElementById('scene-edit-form').style.display = 'none';
            await _loadSceneDetail(sceneId);
        } else {
            const d = await r.json();
            if (statusEl) statusEl.textContent = '✗ ' + (d.error || r.status);
        }
    } catch(e) {
        if (statusEl) statusEl.textContent = '✗ ' + e.message;
    }
};

function _escHtml(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// ── Scenes panel (Gap B) ──
window._currentSceneId = null;
let _allScenes = [];
let _scenesOffset = 0;
let _scenesTotal = 0;
const _SCENES_PAGE = 50;

function _fmtTs(ts) {
    if (!ts) return '';
    try {
        const d = new Date(ts.includes('T') ? ts : ts + 'Z');
        return d.toLocaleTimeString('it-IT', {hour:'2-digit', minute:'2-digit'});
    } catch (_) { return ''; }
}

async function _loadMoreScenes() {
    _scenesOffset += _SCENES_PAGE;
    try {
        const resp = await fetch('/api/db/scenes?limit=' + _SCENES_PAGE + '&offset=' + _scenesOffset);
        const data = await resp.json();
        const more = data.scenes || [];
        _allScenes = _allScenes.concat(more);
        _scenesTotal = data.total || _scenesTotal;
        _renderSceneList(_getActiveSceneFilters());
        _updateLoadMoreBtn();
    } catch(e) {
        const info = document.getElementById('scenes-count-info');
        if (info) info.textContent = 'Errore: ' + e.message;
    }
}

function _updateLoadMoreBtn() {
    const div = document.getElementById('scenes-load-more');
    const info = document.getElementById('scenes-count-info');
    if (!div) return;
    const hasMore = _allScenes.length < _scenesTotal;
    div.style.display = hasMore ? 'block' : 'none';
    if (info) info.textContent = `Mostrate ${_allScenes.length} di ${_scenesTotal} scene`;
}

async function _cleanFixtureScenes() {
    const patterns = ['flow3', 'test_scene', 'fixture_'];
    if (!confirm(`Eliminare tutte le scene fixture test? (prefissi: ${patterns.join(', ')})`)) return;
    const btn = document.getElementById('btn-clean-fixtures');
    if (btn) btn.disabled = true;
    let total = 0;
    try {
        for (const p of patterns) {
            const r = await fetch('/api/db/scenes/batch-delete', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({pattern: p}),
            });
            if (r.ok) {
                const d = await r.json();
                total += d.deleted || 0;
            }
        }
        alert(`✓ Eliminate ${total} scene fixture. Ricarico lista.`);
        await _loadScenes();
    } catch(e) {
        alert('Errore: ' + e.message);
    } finally {
        if (btn) btn.disabled = false;
    }
}

async function _loadArcFilterOptions(editSel = null) {
    const sel = document.getElementById('scene-arc-filter');
    if (!sel && !editSel) return;
    try {
        const r = await fetch('/api/db/arcs');
        const d = await r.json();
        const arcs = d.arcs || [];
        const optHtml = arcs.map(a =>
            `<option value="${_escHtml(String(a.id))}">${_escHtml(a.title || a.id)}</option>`
        ).join('');
        if (sel) sel.innerHTML = '<option value="">— Tutti gli archi —</option>' + optHtml;
        if (editSel) editSel.innerHTML = '<option value="">— Nessun arco —</option>' + optHtml;
    } catch(_) {}
}

function _getActiveSceneFilters() {
    const hasMsgEl = document.getElementById('scene-has-msg-filter');
    const hasMsg = hasMsgEl ? hasMsgEl.checked : false;
    const arc = document.getElementById('scene-arc-filter');
    const arcId = arc ? arc.value : '';
    const txt = document.getElementById('scene-filter');
    const f = txt ? txt.value.toLowerCase() : '';
    let base = hasMsg ? _allScenes.filter(s => (s.message_count || 0) > 0) : _allScenes;
    if (arcId) base = base.filter(s => s.arc_id === arcId);
    if (f) base = base.filter(s =>
        (s.title||'').toLowerCase().includes(f) ||
        (s.summary||'').toLowerCase().includes(f) ||
        (s.participants||[]).some(p => p.toLowerCase().includes(f))
    );
    return base;
}

function _scenesArcFilter(_arcId) {
    _renderSceneList(_getActiveSceneFilters());
}

function _scenesHasMsgFilter(_checked) {
    _renderSceneList(_getActiveSceneFilters());
}

function _newSceneInline() {
    document.getElementById('new-scene-form').style.display = 'block';
    document.getElementById('new-scene-title').focus();
}

function _cancelNewScene() {
    document.getElementById('new-scene-form').style.display = 'none';
    document.getElementById('new-scene-title').value = '';
    document.getElementById('new-scene-location').value = '';
    document.getElementById('new-scene-status').textContent = '';
}

async function _submitNewScene() {
    const title = (document.getElementById('new-scene-title').value || '').trim();
    const location = (document.getElementById('new-scene-location').value || '').trim() || undefined;
    const status = document.getElementById('new-scene-status');
    if (!title) { status.textContent = '⚠ Titolo obbligatorio.'; return; }
    status.textContent = 'Creazione…';
    try {
        const resp = await fetch('/api/db/scenes', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({title, location}),
        });
        const data = await resp.json();
        if (!resp.ok) { status.textContent = '✗ ' + (data.error || resp.status); return; }
        _cancelNewScene();
        await _loadScenes();
        _loadSceneDetail(data.id);
    } catch(e) {
        status.textContent = '✗ ' + e.message;
    }
}

// ── Chat thread renderer ──────────────────────────────────────────────────────

async function _appendMessage() {
    const sceneId = window._currentSceneId;
    if (!sceneId) return;
    const author = (document.getElementById('compose-author').value || '').trim();
    const content = (document.getElementById('compose-content').value || '').trim();
    const status = document.getElementById('compose-status');
    if (!author || !content) { status.textContent = '⚠ Autore e testo obbligatori.'; return; }
    status.textContent = 'Invio…';
    try {
        const composeWho = document.getElementById('compose-who');
        const selectedOpt = composeWho && composeWho.options[composeWho.selectedIndex];
        const charId = (selectedOpt && selectedOpt.dataset.charId) || undefined;
        const msgBody = {author_name: author, content_original: content};
        if (charId) msgBody.character_id = charId;
        const resp = await fetch('/api/db/scenes/' + encodeURIComponent(sceneId) + '/messages', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(msgBody),
        });
        const data = await resp.json();
        if (!resp.ok) { status.textContent = '✗ ' + (data.error || resp.status); return; }
        status.textContent = '✓ Inviato';
        document.getElementById('compose-content').value = '';
        await _loadSceneDetail(sceneId);
    } catch(e) {
        status.textContent = '✗ ' + e.message;
    }
}

window._toggleSceneEdit = function() {
    const form = document.getElementById('scene-edit-form');
    const s = window._currentScene || {};
    if (!form) return;
    if (form.style.display === 'none' || !form.style.display) {
        const titleIn = document.getElementById('scene-edit-title');
        const locIn = document.getElementById('scene-edit-location');
        const arcSel = document.getElementById('scene-edit-arc');
        if (titleIn) titleIn.value = s.title || '';
        if (locIn) locIn.value = s.location || '';
        if (arcSel) {
            _loadArcFilterOptions(arcSel).then(() => {
                if (s.arc_id) arcSel.value = s.arc_id;
            });
        }
        form.style.display = 'flex';
        if (titleIn) titleIn.focus();
    } else {
        form.style.display = 'none';
    }
};

window._saveSceneEdit = async function() {
    const sceneId = window._currentSceneId;
    if (!sceneId) return;
    const title = (document.getElementById('scene-edit-title').value || '').trim();
    const location = (document.getElementById('scene-edit-location').value || '').trim();
    const arcSel = document.getElementById('scene-edit-arc');
    const arcId = arcSel ? (arcSel.value || null) : undefined;
    const statusEl = document.getElementById('scene-edit-status');
    if (!title) { if (statusEl) statusEl.textContent = '⚠ Titolo obbligatorio'; return; }
    if (statusEl) statusEl.textContent = 'Salvataggio…';
    try {
        const body = {title};
        if (location !== undefined) body.location = location || null;
        if (arcId !== undefined) body.arc_id = arcId;
        const r = await fetch('/api/db/scenes/' + encodeURIComponent(sceneId), {
            method: 'PATCH',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(body),
        });
        if (r.ok) {
            document.getElementById('scene-edit-form').style.display = 'none';
            await _loadSceneDetail(sceneId);
        } else {
            const d = await r.json();
            if (statusEl) statusEl.textContent = '✗ ' + (d.error || r.status);
        }
    } catch(e) {
        if (statusEl) statusEl.textContent = '✗ ' + e.message;
    }
};
