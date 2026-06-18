// Lore > PERSONAGGI sub-view (R-CALLIOPE-MC-LORE-SPLIT).
//
// SSOT: reads the SAME store the chat uses — the DB `characters` table
// (card_json Character Card V2) via GET /api/db/characters. This is what
// scene_characters / list_characters_in_scene resolve against, so the list
// can never be empty while the DB has rows (kills the YAML/lore-KB
// discordance by-design). It deliberately does NOT read /api/characters
// (YAML) nor the lore-KB `characters_events` category.
(function () {
    const STYLE = {
        cardBg: "#111827",
        cardBorder: "#1f2a3a",
        cardHover: "#2a3a5a",
        name: "#dde",
        muted: "#8899aa",
        chipBg: "#1a2a4a",
        chipColor: "#aac",
        chipBorder: "#2a3a5a",
        sectionLabel: "#88aaff",
        detailText: "#cdd",
        error: "#ff6b6b",
        avatarBg: "#1e3a6e",
    };

    function parseCard(raw) {
        // card_json is an opaque string column; tolerate null / non-JSON.
        if (!raw) return {};
        if (typeof raw === "object") return raw;
        try {
            return JSON.parse(raw);
        } catch (e) {
            return {};
        }
    }

    function cardData(card) {
        return (card && card.data) || {};
    }

    function calliopeExt(data) {
        return ((data.extensions || {}).calliope) || {};
    }

    function excerpt(str, max) {
        if (!str) return "";
        const s = String(str).replace(/\s+/g, " ").trim();
        return s.length > max ? s.slice(0, max) + "…" : s;
    }

    function chip(text) {
        const el = document.createElement("span");
        el.textContent = text;
        el.style.backgroundColor = STYLE.chipBg;
        el.style.color = STYLE.chipColor;
        el.style.border = `1px solid ${STYLE.chipBorder}`;
        el.style.borderRadius = "10px";
        el.style.padding = "1px 8px";
        el.style.fontSize = ".72em";
        el.style.marginRight = "4px";
        el.style.marginTop = "2px";
        el.style.display = "inline-block";
        return el;
    }

    function avatarEl(name, imagePath, size) {
        if (imagePath) {
            const img = document.createElement("img");
            img.src = imagePath;
            img.alt = name || "";
            img.style.width = size + "px";
            img.style.height = size + "px";
            img.style.objectFit = "cover";
            img.style.borderRadius = "8px";
            img.style.flexShrink = "0";
            // graceful fallback to initial if the image fails to load
            img.addEventListener("error", () => {
                const ph = initialAvatar(name, size);
                if (img.parentNode) img.parentNode.replaceChild(ph, img);
            });
            return img;
        }
        return initialAvatar(name, size);
    }

    function initialAvatar(name, size) {
        const ph = document.createElement("div");
        ph.textContent = (name || "?").trim().charAt(0).toUpperCase() || "?";
        ph.style.width = size + "px";
        ph.style.height = size + "px";
        ph.style.borderRadius = "8px";
        ph.style.background = STYLE.avatarBg;
        ph.style.color = "#fff";
        ph.style.display = "flex";
        ph.style.alignItems = "center";
        ph.style.justifyContent = "center";
        ph.style.fontWeight = "bold";
        ph.style.fontSize = (size * 0.42) + "px";
        ph.style.flexShrink = "0";
        return ph;
    }

    let cached = [];
    let grid = null;
    let detail = null;
    let searchInput = null;

    function normalize(row) {
        // row = { id, name, kind, card_json, image_path }
        const card = parseCard(row.card_json);
        const data = cardData(card);
        const ext = calliopeExt(data);
        const name = data.name || row.name || "(senza nome)";
        const imagePath = ext.image_path || row.image_path || "";
        const description = data.description || "";
        const personality = data.personality || "";
        const tags = Array.isArray(data.tags) ? data.tags : [];
        // a short, human "compact" line for the card body
        const compact = excerpt(description || personality, 90);
        return {
            id: row.id,
            name,
            kind: row.kind || data.extensions && ext.kind || "",
            imagePath,
            description,
            personality,
            tags,
            compact,
            data,
        };
    }

    function renderCard(c) {
        const card = document.createElement("div");
        card.style.backgroundColor = STYLE.cardBg;
        card.style.border = `1px solid ${STYLE.cardBorder}`;
        card.style.borderRadius = "8px";
        card.style.padding = "12px";
        card.style.cursor = "pointer";
        card.style.width = "220px";
        card.style.boxSizing = "border-box";
        card.addEventListener("mouseenter", () => {
            card.style.borderColor = STYLE.cardHover;
        });
        card.addEventListener("mouseleave", () => {
            card.style.borderColor = STYLE.cardBorder;
        });
        card.addEventListener("click", () => openDetail(c.id));

        const head = document.createElement("div");
        head.style.display = "flex";
        head.style.alignItems = "center";
        head.style.gap = "8px";
        head.style.marginBottom = "6px";
        head.appendChild(avatarEl(c.name, c.imagePath, 38));

        const headText = document.createElement("div");
        headText.style.minWidth = "0";
        const name = document.createElement("div");
        name.textContent = c.name;
        name.style.fontWeight = "bold";
        name.style.color = STYLE.name;
        name.style.whiteSpace = "nowrap";
        name.style.overflow = "hidden";
        name.style.textOverflow = "ellipsis";
        headText.appendChild(name);
        if (c.kind) {
            const kind = document.createElement("div");
            kind.textContent = c.kind;
            kind.style.fontSize = ".72em";
            kind.style.color = STYLE.muted;
            headText.appendChild(kind);
        }
        head.appendChild(headText);
        card.appendChild(head);

        if (c.compact) {
            const compact = document.createElement("div");
            compact.textContent = c.compact;
            compact.style.fontSize = ".82em";
            compact.style.color = STYLE.muted;
            compact.style.marginBottom = "6px";
            card.appendChild(compact);
        }

        if (c.tags.length) {
            const tagsBox = document.createElement("div");
            c.tags.slice(0, 6).forEach(t => tagsBox.appendChild(chip(t)));
            card.appendChild(tagsBox);
        }
        return card;
    }

    function renderGrid(list) {
        if (!grid) return;
        grid.textContent = "";
        if (!list || !list.length) {
            const empty = document.createElement("div");
            empty.textContent = "Nessun personaggio in DB.";
            empty.style.color = STYLE.muted;
            empty.style.padding = "12px";
            grid.appendChild(empty);
            return;
        }
        grid.style.display = "flex";
        grid.style.flexWrap = "wrap";
        grid.style.gap = "12px";
        grid.style.alignContent = "flex-start";
        grid.style.overflowY = "auto";
        list.forEach(c => grid.appendChild(renderCard(c)));
    }

    function applyFilter() {
        if (!searchInput) {
            renderGrid(cached);
            return;
        }
        const q = (searchInput.value || "").trim().toLowerCase();
        if (!q) {
            renderGrid(cached);
            return;
        }
        const filtered = cached.filter(c => {
            return (c.name && c.name.toLowerCase().includes(q)) ||
                (c.compact && c.compact.toLowerCase().includes(q)) ||
                (c.tags && c.tags.some(t => String(t).toLowerCase().includes(q)));
        });
        renderGrid(filtered);
    }

    function section(container, label, value) {
        if (value === undefined || value === null || value === "") return;
        const labelEl = document.createElement("div");
        labelEl.textContent = label + ":";
        labelEl.style.color = STYLE.sectionLabel;
        labelEl.style.fontSize = ".8em";
        labelEl.style.fontWeight = "bold";
        labelEl.style.marginTop = "12px";
        container.appendChild(labelEl);
        const valueEl = document.createElement("div");
        valueEl.textContent = value;
        valueEl.style.color = STYLE.detailText;
        valueEl.style.whiteSpace = "pre-wrap";
        valueEl.style.marginBottom = "8px";
        container.appendChild(valueEl);
    }

    function renderDetail(c) {
        if (!detail) return;
        detail.textContent = "";

        const head = document.createElement("div");
        head.style.display = "flex";
        head.style.alignItems = "center";
        head.style.gap = "12px";
        head.style.marginBottom = "8px";
        head.appendChild(avatarEl(c.name, c.imagePath, 64));
        const title = document.createElement("h2");
        title.textContent = c.name;
        title.style.margin = "0";
        title.style.color = STYLE.name;
        head.appendChild(title);
        detail.appendChild(head);

        if (c.kind) {
            const kind = document.createElement("div");
            kind.textContent = "Tipo: " + c.kind;
            kind.style.fontSize = ".82em";
            kind.style.color = STYLE.muted;
            detail.appendChild(kind);
        }

        const d = c.data || {};
        section(detail, "Description", d.description);
        section(detail, "Personality", d.personality);
        section(detail, "Scenario", d.scenario);
        section(detail, "First Message", d.first_mes);
        section(detail, "Message Example", d.mes_example);
        section(detail, "System Prompt", d.system_prompt);
        section(detail, "Post History Instructions", d.post_history_instructions);

        if (c.tags && c.tags.length) {
            const labelEl = document.createElement("div");
            labelEl.textContent = "Tags:";
            labelEl.style.color = STYLE.sectionLabel;
            labelEl.style.fontSize = ".8em";
            labelEl.style.fontWeight = "bold";
            labelEl.style.marginTop = "12px";
            detail.appendChild(labelEl);
            const tagsBox = document.createElement("div");
            c.tags.forEach(t => tagsBox.appendChild(chip(t)));
            detail.appendChild(tagsBox);
        }
    }

    function openDetail(id) {
        const c = cached.find(x => x.id === id);
        if (c) renderDetail(c);
    }

    window.loadLoreCharacters = function () {
        grid = document.getElementById("lore-chars-grid");
        detail = document.getElementById("lore-chars-detail");
        searchInput = document.getElementById("lore-chars-search");
        if (!grid) return;

        if (searchInput && !searchInput._loreCharBound) {
            searchInput.addEventListener("input", applyFilter);
            searchInput._loreCharBound = true;
        }

        grid.textContent = "Caricamento…";
        fetch("/api/db/characters")
            .then(r => {
                if (!r.ok) throw new Error("Network error");
                return r.json();
            })
            .then(data => {
                const rows = (data && data.characters) || [];
                cached = rows.map(normalize);
                cached.sort((a, b) => a.name.localeCompare(b.name));
                applyFilter();
            })
            .catch(err => {
                grid.textContent = "";
                const e = document.createElement("div");
                e.textContent = "Errore nel caricamento personaggi: " + err.message;
                e.style.color = STYLE.error;
                e.style.padding = "12px";
                grid.appendChild(e);
            });
    };
})();
