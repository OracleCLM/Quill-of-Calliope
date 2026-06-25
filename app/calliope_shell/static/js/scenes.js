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
    } catch(e) {
        ul.innerHTML = '<li style="color:#f66;padding:12px">Errore: ' + e.message + '</li>';
    }
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
    const _statusColor = {'active':'#4c8','draft':'#c90','dormant':'#667'};
    ul.innerHTML = scenes.map(s => {
        const st = s.status || 'draft';
        const col = _statusColor[st] || '#556';
        const msgCount = s.message_count != null ? ` · ${s.message_count} msg` : '';
        return `
        <li onclick="_loadSceneDetail('${s.id}')">
            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${col};margin-right:6px;vertical-align:middle"></span>
            <span class="scene-item-title">${_escHtml(s.title || s.id)}</span>
            <div class="scene-item-meta">${_escHtml(st)}${msgCount}</div>
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

// ── Chat thread renderer ──────────────────────────────────────────────────────

function _renderChatThread(messages) {
    const thread = document.getElementById('chat-thread');
    if (!messages.length) {
        thread.innerHTML = '<div style="color:#334;padding:16px;text-align:center;font-size:.85em;">Nessun messaggio in questa scena</div>';
        return;
    }
    thread.innerHTML = messages.map(m => `
        <div class="chat-msg">
            <div class="chat-msg-author">${_escHtml(m.author_name || '?')}</div>
            <div class="chat-msg-content">${_escHtml(m.content_original || '')}</div>
        </div>
    `).join('');
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
        const resp = await fetch('/api/db/scenes/' + encodeURIComponent(sceneId) + '/messages', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({author_name: author, content_original: content}),
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
        _renderChatThread(messages);
        // FE-2: roster personaggi-in-scena dal DB
        const sel = document.getElementById('scene-char-select');
        sel.innerHTML = '<option value="">— Seleziona personaggio —</option>';
        try {
            const rresp = await fetch('/api/db/scenes/' + encodeURIComponent(sceneId) + '/characters');
            const rdata = await rresp.json();
            (rdata.characters || []).forEach(c => {
                const opt = document.createElement('option');
                opt.value = c.id;
                opt.textContent = c.role ? `${c.name} (${c.role})` : c.name;
                sel.appendChild(opt);
            });
        } catch (e) { /* roster opzionale */ }
        const contBtn = document.getElementById('continue-btn');
        sel.onchange = () => { if (contBtn) contBtn.disabled = !sel.value; };
    } catch(e) {
        document.getElementById('scene-detail-title').textContent = 'Errore: ' + e.message;
        document.getElementById('chat-thread').innerHTML = '';
    }
}
