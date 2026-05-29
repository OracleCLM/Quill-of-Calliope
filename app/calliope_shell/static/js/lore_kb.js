(function() {
    const CATEGORY_LABELS = {
        world_setting: "Mondo & Ambientazione",
        places: "Capitale & Città",
        characters_events: "Personaggi & Eventi",
        mechanics_magic: "Meccaniche & Magia",
        other: "Altro"
    };

    const STYLE = {
        panelText: "#cdd",
        sectionLabel: "#88aaff",
        muted: "#8899aa",
        listBg: "#111827",
        listBorder: "#1f2a3a",
        listHover: "#2a3a5a",
        chipBg: "#1a2a4a",
        chipBorder: "#2a3a5a",
        buttonBg: "#1e3a6e",
        buttonColor: "#fff",
        inputBg: "#0d1117",
        inputColor: "#dde",
        inputBorder: "#2a3a5a",
        errorColor: "#ff6b6b"
    };

    function txt(tag, text) {
        const el = document.createElement(tag);
        el.textContent = text;
        return el;
    }

    async function fetchJSON(url, opts) {
        const resp = await fetch(url, opts);
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.error || resp.statusText);
        }
        return resp.json();
    }

    function truncate(str, max) {
        if (!str) return "";
        return str.length > max ? str.slice(0, max) + "…" : str;
    }

    async function renderCategories() {
        const container = document.getElementById("lorekb-categories");
        if (!container) return;
        container.innerHTML = "";
        const categories = await fetchJSON("/api/lore/categories");
        const allBtn = txt("button", "Tutte");
        allBtn.dataset.category = "";
        styleCategoryBtn(allBtn);
        container.appendChild(allBtn);
        allBtn.addEventListener("click", () => loadEntries(""));
        categories.categories.forEach(id => {
            const btn = txt("button", CATEGORY_LABELS[id] || id);
            btn.dataset.category = id;
            styleCategoryBtn(btn);
            btn.addEventListener("click", () => loadEntries(id));
            container.appendChild(btn);
        });
        setActiveCategoryBtn("");
    }

    function styleCategoryBtn(btn) {
        btn.style.background = STYLE.listBg;
        btn.style.color = STYLE.panelText;
        btn.style.border = `1px solid ${STYLE.listBorder}`;
        btn.style.borderRadius = "8px";
        btn.style.padding = "8px 12px";
        btn.style.margin = "2px";
        btn.style.cursor = "pointer";
        btn.addEventListener("mouseenter", () => {
            btn.style.borderColor = STYLE.listHover;
        });
        btn.addEventListener("mouseleave", () => {
            btn.style.borderColor = STYLE.listBorder;
        });
    }

    function setActiveCategoryBtn(cat) {
        const container = document.getElementById("lorekb-categories");
        if (!container) return;
        Array.from(container.children).forEach(btn => {
            btn.style.fontWeight = btn.dataset.category === cat ? "bold" : "normal";
        });
    }

    async function loadEntries(category) {
        selectedCategory = category;
        setActiveCategoryBtn(category);
        const container = document.getElementById("lorekb-entries");
        if (!container) return;
        container.innerHTML = "";
        container.style.overflowY = "auto";
        const url = category ? `/api/lore/entries?category=${encodeURIComponent(category)}` : "/api/lore/entries";
        const data = await fetchJSON(url);
        if (!data.entries.length) {
            const empty = txt("div", "Nessuna voce. Usa “+ Nuova voce” per crearne una.");
            empty.style.color = STYLE.muted;
            empty.style.padding = "10px";
            container.appendChild(empty);
            return;
        }
        data.entries.forEach(entry => {
            const item = document.createElement("div");
            item.style.background = STYLE.listBg;
            item.style.color = STYLE.panelText;
            item.style.border = `1px solid ${STYLE.listBorder}`;
            item.style.borderRadius = "8px";
            item.style.padding = "10px";
            item.style.margin = "4px 0";
            item.style.cursor = "pointer";
            item.addEventListener("mouseenter", () => {
                item.style.borderColor = STYLE.listHover;
            });
            item.addEventListener("mouseleave", () => {
                item.style.borderColor = STYLE.listBorder;
            });
            const title = txt("strong", entry.title);
            const catLabel = txt("span", ` (${CATEGORY_LABELS[entry.category] || entry.category})`);
            catLabel.style.fontSize = ".8em";
            catLabel.style.color = STYLE.muted;
            const preview = txt("div", truncate(entry.content, 120));
            preview.style.fontSize = ".9em";
            preview.style.color = STYLE.muted;
            item.appendChild(title);
            item.appendChild(catLabel);
            item.appendChild(preview);
            item.addEventListener("click", () => showEntry(entry.id));
            container.appendChild(item);
        });
    }

    async function showEntry(id) {
        const detail = document.getElementById("lorekb-detail");
        if (!detail) return;
        detail.innerHTML = "";
        detail.style.overflowY = "auto";
        let entry;
        try {
            entry = await fetchJSON(`/api/lore/entries/${encodeURIComponent(id)}`);
        } catch (e) {
            detail.textContent = "Errore nel caricamento dell'elemento.";
            return;
        }

        const title = txt("h2", entry.title);
        title.style.color = STYLE.panelText;
        const cat = txt("div", CATEGORY_LABELS[entry.category] || entry.category);
        cat.style.fontSize = ".8em";
        cat.style.color = STYLE.sectionLabel;
        const keysDiv = document.createElement("div");
        (entry.keys || []).forEach(k => {
            const chip = txt("span", k);
            chip.style.background = STYLE.chipBg;
            chip.style.color = STYLE.panelText;
            chip.style.border = `1px solid ${STYLE.chipBorder}`;
            chip.style.borderRadius = "10px";
            chip.style.padding = "1px 8px";
            chip.style.margin = "2px";
            chip.style.fontSize = ".72em";
            keysDiv.appendChild(chip);
        });
        const scope = txt("div", `Scope: ${entry.scope}`);
        scope.style.fontSize = ".85em";
        scope.style.color = STYLE.muted;
        if (entry.constant) {
            const constTag = txt("div", "Costante");
            constTag.style.fontSize = ".85em";
            constTag.style.color = "#ffcc00";
            scope.appendChild(constTag);
        }
        const content = txt("pre", entry.content);
        content.style.whiteSpace = "pre-wrap";
        content.style.color = STYLE.panelText;

        const editBtn = txt("button", "✎ Modifica");
        const delBtn = txt("button", "🗑 Elimina");
        [editBtn, delBtn].forEach(b => {
            b.style.background = STYLE.buttonBg;
            b.style.color = STYLE.buttonColor;
            b.style.border = "none";
            b.style.borderRadius = "6px";
            b.style.padding = "8px 14px";
            b.style.margin = "4px";
            b.style.cursor = "pointer";
        });
        editBtn.addEventListener("click", () => renderForm(entry));
        delBtn.addEventListener("click", async () => {
            if (confirm("Sei sicuro di eliminare questa voce?")) {
                try {
                    await fetchJSON(`/api/lore/entries/${encodeURIComponent(id)}`, {method: "DELETE"});
                    await loadEntries(selectedCategory);
                    detail.innerHTML = "";
                } catch (e) {
                    alert("Errore durante l'eliminazione.");
                }
            }
        });

        detail.appendChild(title);
        detail.appendChild(cat);
        detail.appendChild(keysDiv);
        detail.appendChild(scope);
        detail.appendChild(content);
        detail.appendChild(editBtn);
        detail.appendChild(delBtn);
    }

    function renderForm(entry = null) {
        const detail = document.getElementById("lorekb-detail");
        if (!detail) return;
        detail.innerHTML = "";
        const isEdit = !!entry;
        const form = document.createElement("form");
        form.style.display = "flex";
        form.style.flexDirection = "column";
        form.style.gap = "8px";

        const titleInput = document.createElement("input");
        titleInput.type = "text";
        titleInput.placeholder = "Titolo";
        titleInput.value = entry ? entry.title : "";
        styleInput(titleInput);
        form.appendChild(titleInput);

        const categorySelect = document.createElement("select");
        Object.entries(CATEGORY_LABELS).forEach(([id, label]) => {
            const opt = document.createElement("option");
            opt.value = id;
            opt.textContent = label;
            if (entry && entry.category === id) opt.selected = true;
            categorySelect.appendChild(opt);
        });
        styleInput(categorySelect);
        form.appendChild(categorySelect);

        const keysInput = document.createElement("input");
        keysInput.type = "text";
        keysInput.placeholder = "Chiavi (separate con virgola)";
        keysInput.value = entry ? (entry.keys || []).join(", ") : "";
        styleInput(keysInput);
        form.appendChild(keysInput);

        const scopeInput = document.createElement("input");
        scopeInput.type = "text";
        scopeInput.placeholder = "Scope";
        scopeInput.value = entry ? entry.scope : "global";
        styleInput(scopeInput);
        form.appendChild(scopeInput);

        const constDiv = document.createElement("div");
        const constLabel = txt("label", " Costante");
        const constCheckbox = document.createElement("input");
        constCheckbox.type = "checkbox";
        constCheckbox.checked = entry ? !!entry.constant : false;
        constLabel.prepend(constCheckbox);
        constLabel.style.color = STYLE.panelText;
        constDiv.appendChild(constLabel);
        form.appendChild(constDiv);

        const contentArea = document.createElement("textarea");
        contentArea.rows = 8;
        contentArea.placeholder = "Contenuto";
        contentArea.value = entry ? entry.content : "";
        styleInput(contentArea);
        form.appendChild(contentArea);

        const msg = txt("div", "");
        msg.style.color = STYLE.errorColor;
        form.appendChild(msg);

        const btnContainer = document.createElement("div");
        const saveBtn = txt("button", "Salva");
        saveBtn.type = "button";
        const cancelBtn = txt("button", "Annulla");
        cancelBtn.type = "button";
        [saveBtn, cancelBtn].forEach(b => {
            b.style.background = STYLE.buttonBg;
            b.style.color = STYLE.buttonColor;
            b.style.border = "none";
            b.style.borderRadius = "6px";
            b.style.padding = "8px 14px";
            b.style.cursor = "pointer";
            b.style.marginRight = "8px";
        });
        btnContainer.appendChild(saveBtn);
        btnContainer.appendChild(cancelBtn);
        form.appendChild(btnContainer);

        saveBtn.addEventListener("click", async (e) => {
            e.preventDefault();
            if (!titleInput.value.trim()) {
                msg.textContent = "Il titolo è obbligatorio.";
                return;
            }
            const body = {
                title: titleInput.value.trim(),
                category: categorySelect.value,
                keys: keysInput.value.split(",").map(k => k.trim()).filter(Boolean),
                scope: scopeInput.value.trim() || "global",
                constant: constCheckbox.checked,
                content: contentArea.value
            };
            try {
                let result;
                if (isEdit) {
                    result = await fetchJSON(`/api/lore/entries/${encodeURIComponent(entry.id)}`, {
                        method: "PUT",
                        headers: {"Content-Type": "application/json"},
                        body: JSON.stringify(body)
                    });
                } else {
                    result = await fetchJSON("/api/lore/entries", {
                        method: "POST",
                        headers: {"Content-Type": "application/json"},
                        body: JSON.stringify(body)
                    });
                }
                await loadEntries(selectedCategory);
                showEntry(result.id || (entry && entry.id));
            } catch (err) {
                msg.textContent = "Errore nel salvataggio.";
            }
        });

        cancelBtn.addEventListener("click", (e) => {
            e.preventDefault();
            if (isEdit) showEntry(entry.id);
            else detail.innerHTML = "";
        });

        detail.appendChild(form);
    }

    function styleInput(el) {
        el.style.background = STYLE.inputBg;
        el.style.color = STYLE.inputColor;
        el.style.border = `1px solid ${STYLE.inputBorder}`;
        el.style.borderRadius = "6px";
        el.style.padding = "8px";
    }

    async function runSearch() {
        const input = document.getElementById("lorekb-search-input");
        const resultsDiv = document.getElementById("lorekb-search-results");
        if (!input || !resultsDiv) return;
        const query = input.value.trim();
        if (!query) return;
        resultsDiv.innerHTML = "";
        try {
            const resp = await fetchJSON("/api/lore/search", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({query})
            });
            if (resp.error) {
                const note = txt("div", "Ricerca semantica offline (vector DB non raggiungibile).");
                note.style.color = STYLE.muted;
                resultsDiv.appendChild(note);
                return;
            }
            const list = resp.results || [];
            if (!list.length) {
                resultsDiv.textContent = "Nessun risultato";
                resultsDiv.style.color = STYLE.muted;
                return;
            }
            list.forEach(r => {
                const item = document.createElement("div");
                item.style.background = STYLE.listBg;
                item.style.color = STYLE.panelText;
                item.style.border = `1px solid ${STYLE.listBorder}`;
                item.style.borderRadius = "8px";
                item.style.padding = "10px";
                item.style.margin = "4px 0";
                const txtDiv = txt("div", truncate(r.text, 200));
                const srcDiv = txt("div", `Fonte: ${r.source}`);
                srcDiv.style.fontSize = ".85em";
                srcDiv.style.color = STYLE.muted;
                const distDiv = txt("div", `Distanza: ${r.distance}`);
                distDiv.style.fontSize = ".85em";
                distDiv.style.color = STYLE.muted;
                item.appendChild(txtDiv);
                item.appendChild(srcDiv);
                item.appendChild(distDiv);
                resultsDiv.appendChild(item);
            });
        } catch (e) {
            const errMsg = txt("div", "Errore nella ricerca.");
            errMsg.style.color = STYLE.errorColor;
            resultsDiv.appendChild(errMsg);
        }
    }

    function bindGlobal() {
        const newBtn = document.getElementById("lorekb-new-btn");
        const searchBtn = document.getElementById("lorekb-search-btn");
        const searchInput = document.getElementById("lorekb-search-input");
        if (newBtn && !newBtn._bound) {
            newBtn.addEventListener("click", () => renderForm());
            newBtn._bound = true;
        }
        if (searchBtn && !searchBtn._bound) {
            searchBtn.addEventListener("click", runSearch);
            searchBtn._bound = true;
        }
        if (searchInput && !searchInput._bound) {
            searchInput.addEventListener("keypress", (e) => {
                if (e.key === "Enter") {
                    e.preventDefault();
                    runSearch();
                }
            });
            searchInput._bound = true;
        }
    }

    let selectedCategory = "";

    window.loadLoreKB = async function() {
        const required = ["lorekb-categories", "lorekb-entries", "lorekb-detail", "lorekb-search-input", "lorekb-search-results"];
        for (const id of required) {
            if (!document.getElementById(id)) return;
        }
        bindGlobal();
        await renderCategories();
        selectedCategory = "";
        await loadEntries("");
    };
})();
