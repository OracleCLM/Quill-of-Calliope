(() => {
  const CARD_BG = '#111827';
  const CARD_BORDER = '#1f2a3a';
  const CARD_HOVER_BORDER = '#2a3a5a';
  const NAME_COLOR = '#dde';
  const MUTED_COLOR = '#8899aa';
  const CHIP_BG = '#1a2a4a';
  const CHIP_COLOR = '#aac';
  const CHIP_BORDER = '#2a3a5a';
  const SECTION_LABEL_COLOR = '#88aaff';
  const DETAIL_TEXT_COLOR = '#cdd';
  const ERROR_COLOR = '#ff6b6b';
  const EMPTY_COLOR = '#8899aa';

  let cached = [];
  let searchInput = null;
  let grid = null;
  let detail = null;

  function showEmpty(container, message) {
    container.textContent = '';
    const msg = document.createElement('div');
    msg.textContent = message;
    msg.style.color = EMPTY_COLOR;
    msg.style.padding = '12px';
    container.appendChild(msg);
  }

  function showError(container, message) {
    container.textContent = '';
    const msg = document.createElement('div');
    msg.textContent = message;
    msg.style.color = ERROR_COLOR;
    msg.style.padding = '12px';
    container.appendChild(msg);
  }

  function createChip(text) {
    const chip = document.createElement('span');
    chip.textContent = text;
    chip.style.backgroundColor = CHIP_BG;
    chip.style.color = CHIP_COLOR;
    chip.style.border = `1px solid ${CHIP_BORDER}`;
    chip.style.borderRadius = '10px';
    chip.style.padding = '1px 8px';
    chip.style.fontSize = '.72em';
    chip.style.marginRight = '4px';
    return chip;
  }

  function renderCard(char) {
    const card = document.createElement('div');
    card.style.backgroundColor = CARD_BG;
    card.style.border = `1px solid ${CARD_BORDER}`;
    card.style.borderRadius = '8px';
    card.style.padding = '12px';
    card.style.cursor = 'pointer';
    card.style.width = '220px';
    card.style.boxSizing = 'border-box';
    card.addEventListener('mouseenter', () => {
      card.style.borderColor = CARD_HOVER_BORDER;
    });
    card.addEventListener('mouseleave', () => {
      card.style.borderColor = CARD_BORDER;
    });
    card.addEventListener('click', () => openCharacterDetail(char.stem));

    const name = document.createElement('div');
    name.textContent = char.name;
    name.style.fontWeight = 'bold';
    name.style.color = NAME_COLOR;
    name.style.marginBottom = '4px';
    card.appendChild(name);

    if (char.compact) {
      const compact = document.createElement('div');
      compact.textContent = char.compact;
      compact.style.fontSize = '.85em';
      compact.style.color = MUTED_COLOR;
      compact.style.whiteSpace = 'nowrap';
      compact.style.overflow = 'hidden';
      compact.style.textOverflow = 'ellipsis';
      compact.style.marginBottom = '6px';
      card.appendChild(compact);
    }

    if (char.tags && char.tags.length) {
      const tagsContainer = document.createElement('div');
      char.tags.forEach(t => tagsContainer.appendChild(createChip(t)));
      card.appendChild(tagsContainer);
    }

    return card;
  }

  function renderGrid(list) {
    grid.textContent = '';
    if (!list || list.length === 0) {
      showEmpty(grid, 'Nessun personaggio');
      return;
    }
    grid.style.display = 'flex';
    grid.style.flexWrap = 'wrap';
    grid.style.gap = '12px';
    grid.style.alignContent = 'flex-start';
    grid.style.overflowY = 'auto';
    list.forEach(char => grid.appendChild(renderCard(char)));
  }

  function filter() {
    const query = (searchInput.value || '').trim().toLowerCase();
    if (query === '') {
      renderGrid(cached);
      return;
    }
    const filtered = cached.filter(c => {
      const nameMatch = c.name.toLowerCase().includes(query);
      const compactMatch = c.compact.toLowerCase().includes(query);
      const tagsMatch = c.tags && c.tags.some(t => t.toLowerCase().includes(query));
      return nameMatch || compactMatch || tagsMatch;
    });
    renderGrid(filtered);
  }

  function renderDetail(container, data) {
    container.textContent = '';
    const name = document.createElement('h2');
    name.textContent = data.name;
    name.style.margin = '0 0 12px 0';
    name.style.color = NAME_COLOR;
    container.appendChild(name);

    const sections = [
      ['description', 'Description'],
      ['personality', 'Personality'],
      ['scenario', 'Scenario'],
      ['first_mes', 'First Message'],
      ['mes_example', 'Message Example'],
      ['system_prompt', 'System Prompt'],
      ['post_history_instructions', 'Post History Instructions']
    ];
    sections.forEach(([key, label]) => {
      const value = data[key];
      if (value !== undefined && value !== null && value !== '') {
        const labelEl = document.createElement('div');
        labelEl.textContent = label + ':';
        labelEl.style.color = SECTION_LABEL_COLOR;
        labelEl.style.fontSize = '.8em';
        labelEl.style.fontWeight = 'bold';
        labelEl.style.marginTop = '12px';
        container.appendChild(labelEl);

        const valueEl = document.createElement('div');
        valueEl.textContent = value;
        valueEl.style.color = DETAIL_TEXT_COLOR;
        valueEl.style.whiteSpace = 'pre-wrap';
        valueEl.style.marginBottom = '8px';
        container.appendChild(valueEl);
      }
    });

    if (data.alternate_greetings && data.alternate_greetings.length) {
      const labelEl = document.createElement('div');
      labelEl.textContent = 'Alternate Greetings:';
      labelEl.style.color = SECTION_LABEL_COLOR;
      labelEl.style.fontSize = '.8em';
      labelEl.style.fontWeight = 'bold';
      labelEl.style.marginTop = '12px';
      container.appendChild(labelEl);

      const listEl = document.createElement('ul');
      listEl.style.margin = '4px 0 8px 20px';
      listEl.style.color = DETAIL_TEXT_COLOR;
      data.alternate_greetings.forEach(g => {
        const li = document.createElement('li');
        li.textContent = g;
        li.style.whiteSpace = 'pre-wrap';
        listEl.appendChild(li);
      });
      container.appendChild(listEl);
    }

    const maybeRenderJson = (obj, label) => {
      if (!obj || typeof obj !== 'object' || Array.isArray(obj) || Object.keys(obj).length === 0) return;
      const labelEl = document.createElement('div');
      labelEl.textContent = label + ':';
      labelEl.style.color = SECTION_LABEL_COLOR;
      labelEl.style.fontSize = '.8em';
      labelEl.style.fontWeight = 'bold';
      labelEl.style.marginTop = '12px';
      container.appendChild(labelEl);

      const pre = document.createElement('pre');
      pre.textContent = JSON.stringify(obj, null, 2);
      pre.style.backgroundColor = '#0d1117';
      pre.style.color = '#c9d1d9';
      pre.style.padding = '8px';
      pre.style.borderRadius = '4px';
      pre.style.overflowX = 'auto';
      container.appendChild(pre);
    };

    maybeRenderJson(data.character_book, 'Character Book');
    maybeRenderJson(data.extensions, 'Extensions');

    if (data.tags && data.tags.length) {
      const labelEl = document.createElement('div');
      labelEl.textContent = 'Tags:';
      labelEl.style.color = SECTION_LABEL_COLOR;
      labelEl.style.fontSize = '.8em';
      labelEl.style.fontWeight = 'bold';
      labelEl.style.marginTop = '12px';
      container.appendChild(labelEl);

      const tagsContainer = document.createElement('div');
      data.tags.forEach(t => tagsContainer.appendChild(createChip(t)));
      container.appendChild(tagsContainer);
    }
  }

  window.loadCharactersPanel = function() {
    searchInput = document.getElementById('char-search');
    grid = document.getElementById('characters-grid');
    detail = document.getElementById('character-detail');
    if (!searchInput || !grid || !detail) return;

    if (searchInput._charListener) {
      searchInput.removeEventListener('input', searchInput._charListener);
    }
    const listener = () => filter();
    searchInput._charListener = listener;
    searchInput.addEventListener('input', listener);

    fetch('/api/characters')
      .then(resp => {
        if (!resp.ok) throw new Error('Network error');
        return resp.json();
      })
      .then(data => {
        if (!Array.isArray(data)) throw new Error('Invalid response');
        cached = data;
        if (data.length === 0) {
          showEmpty(grid, 'Nessun personaggio');
        } else {
          renderGrid(data);
        }
      })
      .catch(err => showError(grid, err.message));
  };

  function renderEditForm(container, data, dbId) {
    container.textContent = '';
    const fields = [
      ['description', 'Description', 'textarea'],
      ['personality', 'Personality', 'textarea'],
      ['scenario', 'Scenario', 'textarea'],
      ['first_mes', 'First Message', 'textarea'],
    ];
    const nameIn = document.createElement('input');
    nameIn.value = data.name || '';
    nameIn.placeholder = 'Nome';
    nameIn.style.cssText = 'width:100%;background:#111827;color:#eee;border:1px solid #2a3a5a;border-radius:6px;padding:6px 10px;font-size:.9em;box-sizing:border-box;margin-bottom:10px;';
    container.appendChild(nameIn);

    const kindSel = document.createElement('select');
    kindSel.style.cssText = 'background:#111827;color:#aab;border:1px solid #2a3a5a;border-radius:6px;padding:6px 8px;font-size:.85em;margin-bottom:10px;cursor:pointer;';
    ['npc','player','operator'].forEach(k => {
      const opt = document.createElement('option');
      opt.value = k; opt.textContent = k;
      if (k === data.kind) opt.selected = true;
      kindSel.appendChild(opt);
    });
    container.appendChild(kindSel);

    const inputs = {};
    fields.forEach(([key, label]) => {
      const lbl = document.createElement('div');
      lbl.textContent = label + ':';
      lbl.style.cssText = 'color:#88aaff;font-size:.8em;font-weight:bold;margin-top:8px;';
      container.appendChild(lbl);
      const ta = document.createElement('textarea');
      ta.value = data[key] || '';
      ta.rows = 3;
      ta.style.cssText = 'width:100%;box-sizing:border-box;background:#111827;color:#eee;border:1px solid #2a3a5a;border-radius:6px;padding:6px 10px;font-size:.83em;resize:vertical;margin-bottom:4px;';
      container.appendChild(ta);
      inputs[key] = ta;
    });

    const statusEl = document.createElement('div');
    statusEl.style.cssText = 'font-size:.8em;color:#88aaff;min-height:1.2em;margin:6px 0;';
    container.appendChild(statusEl);

    const btnRow = document.createElement('div');
    btnRow.style.cssText = 'display:flex;gap:8px;margin-top:6px;';

    const saveBtn = document.createElement('button');
    saveBtn.textContent = '✓ Salva';
    saveBtn.style.cssText = 'background:#1a3a1a;color:#8f8;border:1px solid #2a5a2a;border-radius:6px;padding:6px 16px;cursor:pointer;font-size:.85em;';
    saveBtn.onclick = async () => {
      saveBtn.disabled = true;
      statusEl.textContent = 'Salvataggio…';
      const card = Object.assign({}, data);
      fields.forEach(([key]) => { card[key] = inputs[key].value; });
      card.name = nameIn.value.trim();
      const body = {name: card.name, kind: kindSel.value, card_json: JSON.stringify(card)};
      try {
        const r = await fetch('/api/db/characters/' + encodeURIComponent(dbId), {
          method: 'PATCH',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(body),
        });
        if (r.ok) { statusEl.textContent = '✓ Salvato'; statusEl.style.color = '#8f8'; }
        else { statusEl.textContent = '✗ Errore ' + r.status; saveBtn.disabled = false; }
      } catch(e) { statusEl.textContent = '✗ ' + e.message; saveBtn.disabled = false; }
    };

    const cancelBtn = document.createElement('button');
    cancelBtn.textContent = 'Annulla';
    cancelBtn.style.cssText = 'background:#1a2a3a;color:#aab;border:1px solid #2a3a5a;border-radius:6px;padding:6px 14px;cursor:pointer;font-size:.85em;';
    cancelBtn.onclick = () => { container.textContent = ''; renderDetail(container, data); _addEditBtn(container, data); };

    btnRow.appendChild(saveBtn);
    btnRow.appendChild(cancelBtn);
    container.appendChild(btnRow);
  }

  function _addEditBtn(container, data) {
    fetch('/api/db/characters?name=' + encodeURIComponent(data.name || ''))
      .then(r => r.json())
      .then(d => {
        const chars = d.characters || [];
        if (!chars.length) return;
        const dbId = chars[0].id;
        const btn = document.createElement('button');
        btn.textContent = '✎ Modifica';
        btn.style.cssText = 'background:#1a2a4a;color:#aac;border:1px solid #2a3a5a;border-radius:6px;padding:5px 14px;cursor:pointer;font-size:.8em;margin-top:10px;';
        const mergedData = Object.assign({}, data, {kind: chars[0].kind});
        btn.onclick = () => { container.textContent = ''; renderEditForm(container, mergedData, dbId); };
        container.appendChild(btn);
      })
      .catch(() => {});
  }

  window.openCharacterDetail = function(stem) {
    if (!detail) return;
    detail.textContent = '';
    const url = '/api/characters/' + encodeURIComponent(stem);
    fetch(url)
      .then(resp => {
        if (!resp.ok) {
          if (resp.status === 404) throw new Error('Not found');
          throw new Error('Network error');
        }
        return resp.json();
      })
      .then(data => {
        if (data && data.error) throw new Error(data.error);
        renderDetail(detail, data);
        _addEditBtn(detail, data);
      })
      .catch(err => showError(detail, err.message));
  };
})();
