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
        // Roster personaggi-in-scena -> popola il select del compose (personaggio mittente).
        const composeSel = document.getElementById('compose-char-select');
        if (composeSel) composeSel.innerHTML = '<option value="">— Personaggio —</option>';
        try {
            const rresp = await fetch('/api/db/scenes/' + encodeURIComponent(sceneId) + '/characters');
            const rdata = await rresp.json();
            (rdata.characters || []).forEach(c => {
                if (composeSel) {
                    const o2 = document.createElement('option');
                    o2.value = c.id;
                    o2.textContent = c.name;
                    o2.dataset.name = c.name;
                    composeSel.appendChild(o2);
                }
            });
        } catch (e) { /* roster opzionale: il dettaglio resta usabile senza */ }
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
        // POST /api/characters = stessa fonte della griglia Personaggi (così compare subito).
        const r = await fetch('/api/characters', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ name }),
        });
        const d = await r.json();
        if (!r.ok) throw new Error(d.error || ('HTTP ' + r.status));
        if (typeof loadCharactersPanel === 'function') loadCharactersPanel();
        if (typeof loadCharList === 'function') loadCharList();
        window.alert('Personaggio "' + name + '" creato. Aprilo per compilarne la scheda.');
    } catch (e) {
        window.alert('Errore creazione personaggio: ' + e.message);
    }
}

// Affordance informativa: import/scrape Discord (oggi via CLI — reso DISCOVERABILE).
function _importInfo() {
    window.alert(
        'Importa storico Discord\n\n' +
        'Lo scraping per-canale/data avviene da terminale (selezione manuale dei messaggi):\n\n' +
        '  python scripts/import_discord_history.py\n\n' +
        'I messaggi importati popolano le scene e compaiono qui nella Scene-Chat.\n' +
        'In alternativa, per un estratto rapido usa il tab "∑ Summarize" incollando il log Discord.'
    );
}
