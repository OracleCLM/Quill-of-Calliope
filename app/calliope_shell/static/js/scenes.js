// Scene/Messages panel — estratto da templates/shell.html (FE-0 enablement 2026-06-11).
// Classic script (NON module): le function declarations restano globali e sono
// invocate da showView()/onclick inline. Dipendenze globali definite in shell.html
// (renderEmptyState, cloudCall, showView) sono disponibili a runtime (script caricato dopo).

// ── Scenes panel (Gap B) ──
window._currentSceneId = null;
let _allScenes = [];

async function _loadScenes() {
    const ul = document.getElementById('scenes-list');
    ul.innerHTML = '<li style="color:#334;padding:12px">Caricamento 332 scene...</li>';
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
        return `
        <li onclick="_loadSceneDetail('${s.id}')">
            <div class="scene-item-title">${s.title || s.id}</div>
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

async function _loadSceneDetail(sceneId) {
    window._currentSceneId = sceneId;
    document.getElementById('scene-empty-state').style.display = 'none';
    document.getElementById('scene-detail').style.display = 'block';
    document.getElementById('scene-detail-title').textContent = '…';
    document.getElementById('gen-output').style.display = 'none';
    document.getElementById('continue-status').textContent = '';
    try {
        // FE-1: dettaglio scena dal DB. GET /api/db/scenes/<id> -> {scene:{...}, messages:[...]}
        const resp = await fetch('/api/db/scenes/' + encodeURIComponent(sceneId));
        const data = await resp.json();
        if (data.error) throw new Error(data.error);
        const s = data.scene || {};
        const messages = data.messages || [];
        document.getElementById('scene-detail-title').textContent = s.title || sceneId;
        document.getElementById('scene-detail-meta').textContent =
            `ID: ${s.id} | ${s.location || ''} | ${messages.length} msg`;
        // C1: render del thread-chat (bolle ordinate) + reset compose.
        _renderSceneThread(messages);
        const ct = document.getElementById('scene-compose-text');
        if (ct) ct.value = '';
        const cs = document.getElementById('scene-compose-status');
        if (cs) cs.textContent = '';
        document.getElementById('scene-detail-summary').textContent =
            messages.map(m => `${m.author_name}: ${m.content_original}`).join('\n') || '(nessun messaggio)';
        document.getElementById('scene-detail-first').textContent = messages[0] ? messages[0].content_original : '—';
        document.getElementById('scene-detail-last').textContent =
            messages.length ? messages[messages.length - 1].content_original : '—';
        // FE-2: roster personaggi-in-scena dal DB (GET /api/db/scenes/<id>/characters -> {characters:[{id,name,role}]})
        const sel = document.getElementById('scene-char-select');
        sel.innerHTML = '<option value="">— Seleziona personaggio —</option>';
        // C1: popola anche il select del compose-chat (personaggio mittente).
        const composeSel = document.getElementById('compose-char-select');
        if (composeSel) composeSel.innerHTML = '<option value="">— Personaggio —</option>';
        try {
            const rresp = await fetch('/api/db/scenes/' + encodeURIComponent(sceneId) + '/characters');
            const rdata = await rresp.json();
            (rdata.characters || []).forEach(c => {
                const opt = document.createElement('option');
                opt.value = c.id;
                opt.textContent = c.role ? `${c.name} (${c.role})` : c.name;
                sel.appendChild(opt);
                if (composeSel) {
                    const o2 = document.createElement('option');
                    o2.value = c.id;
                    o2.textContent = c.name;
                    o2.dataset.name = c.name;
                    composeSel.appendChild(o2);
                }
            });
        } catch (e) { /* roster opzionale: il dettaglio resta usabile senza */ }
        sel.onchange = () => { document.getElementById('continue-btn').disabled = !sel.value; };
    } catch(e) {
        document.getElementById('scene-detail-title').textContent = 'Errore: ' + e.message;
    }
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
        return `
        <div class="msg-bubble ${isNarrator ? 'msg-narrator' : ''}">
            <div class="msg-avatar">${_escapeHtml(_msgAvatarChar(author))}</div>
            <div class="msg-body">
                <div class="msg-author">${_escapeHtml(author)}</div>
                <div class="msg-text">${_escapeHtml(text)}</div>
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
