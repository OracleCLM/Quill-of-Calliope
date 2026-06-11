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
        const resp = await fetch('/api/scenes/' + encodeURIComponent(sceneId));
        const s = await resp.json();
        if (s.error) throw new Error(s.error);
        document.getElementById('scene-detail-title').textContent = s.title || sceneId;
        document.getElementById('scene-detail-meta').textContent =
            `ID: ${s.scene_id} | ${s.date_started || ''} | ${s.message_count || 0} msg | Partecipanti: ${(s.participants||[]).join(', ')}`;
        document.getElementById('scene-detail-summary').textContent = s.summary || '(nessun sommario)';
        document.getElementById('scene-detail-first').textContent = s.first_msg_excerpt || '—';
        document.getElementById('scene-detail-last').textContent = s.last_msg_excerpt || '—';
        // Populate char select
        const sel = document.getElementById('scene-char-select');
        sel.innerHTML = '<option value="">— Seleziona personaggio —</option>' +
            (s.participants||[]).map(p => `<option value="${p}">${p}</option>`).join('');
        sel.onchange = () => { document.getElementById('continue-btn').disabled = !sel.value; };
    } catch(e) {
        document.getElementById('scene-detail-title').textContent = 'Errore: ' + e.message;
    }
}

async function _generateNextMsg() {
    const sceneId = window._currentSceneId;
    const char = document.getElementById('scene-char-select').value;
    const hint = document.getElementById('scene-ctx-hint').value.trim();
    const lastScene = _allScenes.find(s => s.scene_id === sceneId);
    const lastMsg = lastScene ? lastScene.last_msg_excerpt : '';
    const statusEl = document.getElementById('continue-status');
    const outEl = document.getElementById('gen-output');
    const btn = document.getElementById('continue-btn');
    if (!char) return;
    btn.disabled = true;
    statusEl.textContent = `Generando prossimo messaggio per ${char}...`;
    outEl.style.display = 'none';
    try {
        const resp = await cloudCall('/api/messages/next', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({scene_id: sceneId, char, last_msg: lastMsg, context_hint: hint}),
        }, {kind: 'next_msg'});
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error || resp.statusText);
        outEl.textContent = data.next_msg || '(vuoto)';
        outEl.style.display = 'block';
        statusEl.textContent = `✓ Generato — ctx: facts=${data.context_used?.char_facts||0}, scene=${data.context_used?.scene_context}`;
    } catch(e) {
        statusEl.textContent = '✗ ' + e.message;
    } finally {
        btn.disabled = false;
    }
}

// ── Messages panel (Gap A) ──
async function _loadMessages() {
    const char = document.getElementById('msg-char-filter').value.trim();
    const statusEl = document.getElementById('msg-status');
    const ul = document.getElementById('message-list');
    statusEl.textContent = 'Caricamento...';
    ul.innerHTML = '';
    try {
        const url = '/api/messages/recent?limit=20' + (char ? '&char=' + encodeURIComponent(char) : '');
        const resp = await fetch(url);
        const data = await resp.json();
        const msgs = data.messages || [];
        statusEl.textContent = `${msgs.length} messaggi` + (char ? ` per "${char}"` : '');
        if (!msgs.length) {
            renderEmptyState('message-list', {
                icon: '◇', title: 'Nessun messaggio',
                hint: char ? `Nessun messaggio per "${char}". Verifica spelling o rimuovi il filtro.` : 'Importa messaggi da Discord/ChatGPT export per popolare il database.',
            });
            return;
        }
        ul.innerHTML = msgs.map((m, i) => `
            <li class="message-item" onclick="_useMessageAsContext(${i})">
                <div class="message-item-meta">${JSON.stringify(m.meta).slice(0,80)} | dist=${m.distance}</div>
                <div class="message-item-text">${(m.text||'').replace(/</g,'&lt;')}</div>
            </li>`).join('');
        window._recentMessages = msgs;
    } catch(e) {
        statusEl.textContent = '✗ ' + e.message;
    }
}

function _useMessageAsContext(idx) {
    const msg = (window._recentMessages||[])[idx];
    if (!msg) return;
    showView('scenes');
    // Put msg text in scene hint for continuation
    setTimeout(() => {
        const hint = document.getElementById('scene-ctx-hint');
        if (hint) hint.value = (msg.text||'').slice(0, 200);
    }, 300);
}
