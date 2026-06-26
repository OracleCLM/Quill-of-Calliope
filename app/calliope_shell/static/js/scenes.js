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

async function _loadScenes() {
    const ul = document.getElementById('scenes-list');
    ul.innerHTML = '<li style="color:#334;padding:12px">Caricamento scene...</li>';
    try {
        const resp = await fetch('/api/db/scenes');
        const data = await resp.json();
        _allScenes = data.scenes || [];
        _renderSceneList(_allScenes);
        _loadArcFilterOptions();
    } catch(e) {
        ul.innerHTML = '<li style="color:#f66;padding:12px">Errore: ' + e.message + '</li>';
    }
}

async function _loadArcFilterOptions() {
    const sel = document.getElementById('scene-arc-filter');
    if (!sel) return;
    try {
        const r = await fetch('/api/db/arcs');
        const d = await r.json();
        const arcs = d.arcs || [];
        sel.innerHTML = '<option value="">— Tutti gli archi —</option>';
        arcs.forEach(a => {
            const opt = document.createElement('option');
            opt.value = a.id; opt.textContent = a.title || a.id;
            sel.appendChild(opt);
        });
    } catch(_) {}
}

function _scenesArcFilter(arcId) {
    if (!arcId) { _renderSceneList(_allScenes); return; }
    _renderSceneList(_allScenes.filter(s => s.arc_id === arcId));
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

function _scenesFilter(val) {
    const f = val.toLowerCase();
    if (!f) { _renderSceneList(_allScenes); return; }
    _renderSceneList(_allScenes.filter(s =>
        (s.title||'').toLowerCase().includes(f) ||
        (s.summary||'').toLowerCase().includes(f) ||
        (s.participants||[]).some(p => p.toLowerCase().includes(f))
    ));
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
        return `<div class="chat-msg">
            <div class="chat-msg-author">${_escHtml(m.author_name || '?')}${srcBadge}${enhBadge}<span style="float:right;font-size:.72em;color:#445;font-weight:normal">${_escHtml(ts)}</span></div>
            <div class="chat-msg-content" style="${msgStyle}border-radius:8px;padding:8px 12px;font-size:.87em;color:#ccd;white-space:pre-wrap;line-height:1.5;">${_escHtml(body)}</div>
        </div>`;
    }).join('');
    thread.scrollTop = thread.scrollHeight;
}

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
    document.getElementById('gen-output').style.display = 'none';
    document.getElementById('continue-status').textContent = '';
    document.getElementById('chat-thread').innerHTML = '<div style="color:#334;padding:12px">Caricamento messaggi...</div>';
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
            `${s.location || ''} · ${messages.length} messaggi`;
        const arcBadge = document.getElementById('scene-arc-badge');
        if (arcBadge) {
            if (s.arc_id) {
                arcBadge.innerHTML = `<span style="font-size:.75em;background:#1a1a2e;color:#8899cc;border:1px solid #2a3a5a;border-radius:10px;padding:2px 10px;cursor:pointer;" onclick="showView('arc')" title="Vai all'arco">📚 ${_escHtml(s.arc_id)}</span>`;
                arcBadge.style.display = 'block';
            } else {
                arcBadge.style.display = 'none';
            }
        }
        _renderChatThread(messages);
        // FE-2: roster personaggi-in-scena dal DB
        const sel = document.getElementById('scene-char-select');
        const composeWho = document.getElementById('compose-who');
        const rosterListEl = document.getElementById('roster-list');
        sel.innerHTML = '<option value="">— Seleziona personaggio —</option>';
        if (composeWho) composeWho.innerHTML = '<option value="">— Chi scrive —</option><option value="Narratore">Narratore</option>';
        if (rosterListEl) rosterListEl.innerHTML = '';
        try {
            const rresp = await fetch('/api/db/scenes/' + encodeURIComponent(sceneId) + '/characters');
            const rdata = await rresp.json();
            (rdata.characters || []).forEach(c => {
                const label = c.role ? `${c.name} (${c.role})` : c.name;
                const opt = document.createElement('option');
                opt.value = c.id; opt.textContent = label;
                sel.appendChild(opt);
                if (composeWho) {
                    const opt2 = document.createElement('option');
                    opt2.value = c.name; opt2.textContent = label;
                    opt2.dataset.charId = c.id;
                    composeWho.appendChild(opt2);
                }
                if (rosterListEl) {
                    const badge = document.createElement('span');
                    badge.textContent = label;
                    badge.style.cssText = 'background:#1a2a3a;color:#aab;border:1px solid #2a3a5a;border-radius:12px;padding:2px 8px;font-size:.75em;display:inline-flex;align-items:center;gap:4px;';
                    const rm = document.createElement('button');
                    rm.textContent = '×';
                    rm.title = 'Rimuovi dal roster';
                    rm.style.cssText = 'background:none;border:none;color:#c66;cursor:pointer;font-size:1em;padding:0 2px;line-height:1;';
                    rm.onclick = () => window._removeFromRoster(c.id);
                    badge.appendChild(rm);
                    rosterListEl.appendChild(badge);
                }
            });
        } catch (e) { /* roster opzionale */ }
        const contBtn = document.getElementById('continue-btn');
        sel.onchange = () => { if (contBtn) contBtn.disabled = !sel.value; };
        if (composeWho) {
            composeWho.onchange = () => {
                const authorEl = document.getElementById('compose-author');
                if (authorEl && composeWho.value) authorEl.value = composeWho.value;
            };
        }
    } catch(e) {
        document.getElementById('scene-detail-title').textContent = 'Errore: ' + e.message;
        document.getElementById('chat-thread').innerHTML = '';
    }
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
            _loadArcFilterOptions().then(() => {
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
