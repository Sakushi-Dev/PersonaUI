/**
 * PlaceholderInfo – Zeigt verwendete Placeholder im aktuellen Prompt.
 * Phase 4: Full Placeholder Manager Modal mit Usages, Orphaned, Unused.
 */
const PlaceholderInfo = {
    /** Alle registrierten Placeholder (aus Registry). */
    allPlaceholders: {},

    /** Aktuelle aufgelöste Werte. */
    values: {},

    /**
     * Placeholder-Daten und aktuelle Werte vom Backend laden.
     */
    async loadAll() {
        const [phRes, valRes] = await Promise.all([
            Utils.apiCall('get_all_placeholders'),
            Utils.apiCall('get_placeholder_values', 'default')
        ]);
        if (phRes.status === 'ok') this.allPlaceholders = phRes.placeholders;
        if (valRes.status === 'ok') this.values = valRes.values;
    },

    /**
     * Placeholder-Anzeige unter dem Editor aktualisieren.
     * Liest den aktuellen Content und zeigt die verwendeten Placeholder.
     * Jeder Placeholder bekommt einen Entfernen-Button (×).
     */
    update() {
        const container = document.getElementById('placeholder-list');
        if (!container) return;

        const content = PromptEditor.getCurrentContent();
        const used = Utils.extractPlaceholders(content);

        if (used.length === 0) {
            container.innerHTML = '<span class="placeholder-none">Keine Placeholder im Content</span>';
            return;
        }

        container.innerHTML = '';

        for (const key of used) {
            const ph = this.allPlaceholders[key];
            const value = this.values[key];
            const isKnown = !!ph;

            const el = document.createElement('div');
            el.className = 'placeholder-item' + (isKnown ? '' : ' unknown');

            const phase = ph ? ph.resolve_phase : '?';
            const phaseClass = `phase-${phase}`;

            // Wert-Anzeige (gekürzt)
            let displayValue = '\u2014';
            if (value !== undefined && value !== null && value !== '') {
                displayValue = String(value);
                if (displayValue.length > 80) {
                    displayValue = displayValue.substring(0, 77) + '...';
                }
            }

            el.innerHTML = `
                <span class="ph-key">{{${Utils.escapeHtml(key)}}}</span>
                <span class="ph-badge ${phaseClass}">${Utils.escapeHtml(phase)}</span>
                <span class="ph-value" title="${Utils.escapeHtml(String(value || ''))}">${Utils.escapeHtml(displayValue)}</span>
                ${!isKnown ? '<span class="ph-warning" title="Nicht in Registry registriert">\u26A0</span>' : ''}
                <button class="ph-remove-btn" data-ph-key="${Utils.escapeHtml(key)}" title="Alle {{${Utils.escapeHtml(key)}}} aus Content entfernen">&times;</button>
            `;

            container.appendChild(el);
        }

        // Remove-Button-Events
        container.querySelectorAll('.ph-remove-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const key = btn.dataset.phKey;
                this.removePlaceholderFromContent(key);
            });
        });
    },

    /**
     * Entfernt alle Vorkommen von {{key}} aus dem aktuellen Prompt-Content.
     * @param {string} key  Placeholder-Name ohne Klammern.
     */
    removePlaceholderFromContent(key) {
        const pattern = new RegExp(`\\{\\{${key}\\}\\}`, 'g');

        if (PromptEditor.isMultiTurn()) {
            let changed = false;
            document.querySelectorAll('#mt-messages .mt-content').forEach(ta => {
                const newVal = ta.value.replace(pattern, '');
                if (newVal !== ta.value) { ta.value = newVal; changed = true; }
            });
            if (changed) {
                PromptEditor.markDirty();
                this.update();
                Preview.update();
            }
            return;
        }

        const textarea = document.getElementById('content-editor');
        if (!textarea) return;

        const oldVal = textarea.value;
        const newVal = oldVal.replace(pattern, '');

        if (oldVal === newVal) return;

        textarea.value = newVal;
        PromptEditor.markDirty();
        this.update();
        Preview.update();
    },

    /**
     * Picker-Dialog: alle verfügbaren Placeholder anzeigen,
     * Klick fügt {{key}} an der Cursorposition ein.
     */
    showInsertPicker() {
        const keys = Object.keys(this.allPlaceholders).sort();
        if (keys.length === 0) {
            Utils.showToast('Keine Placeholder in der Registry', 'warning');
            return;
        }

        // Kategorien gruppieren
        const groups = {};
        for (const key of keys) {
            const cat = this.allPlaceholders[key].category || 'other';
            if (!groups[cat]) groups[cat] = [];
            groups[cat].push(key);
        }

        let html = '<div class="ph-picker">';

        // Bereits im Content verwendete Placeholder
        const content = PromptEditor.getCurrentContent();
        const usedSet = new Set(Utils.extractPlaceholders(content));

        for (const [cat, phKeys] of Object.entries(groups).sort((a, b) => a[0].localeCompare(b[0]))) {
            html += `<div class="ph-picker-group"><h4>${Utils.escapeHtml(cat)}</h4>`;
            for (const key of phKeys) {
                const ph = this.allPlaceholders[key];
                const inUse = usedSet.has(key);
                html += `<button class="ph-picker-item${inUse ? ' in-use' : ''}" data-ph-insert="${key}" title="${Utils.escapeHtml(ph.description || '')}">
                    <span class="ph-picker-key">{{${Utils.escapeHtml(key)}}}</span>
                    <span class="ph-picker-name">${Utils.escapeHtml(ph.name || key)}</span>
                    ${inUse ? '<span class="ph-picker-used">\u2713</span>' : ''}
                </button>`;
            }
            html += '</div>';
        }
        html += '</div>';

        Modal.show('Placeholder einfügen', html);

        // Klick auf Placeholder → einfügen
        document.querySelectorAll('.ph-picker-item').forEach(btn => {
            btn.addEventListener('click', () => {
                const key = btn.dataset.phInsert;
                Modal.hide();
                this.insertPlaceholderAtCursor(key);
            });
        });
    },

    /**
     * Fügt {{key}} an der aktuellen Cursorposition ein.
     * @param {string} key  Placeholder-Name ohne Klammern.
     */
    insertPlaceholderAtCursor(key) {
        const tag = `{{${key}}}`;

        // Multi-Turn: in fokussiertes oder letztes Textfeld einfügen
        if (PromptEditor.isMultiTurn()) {
            let target = document.activeElement;
            if (!target || !target.classList.contains('mt-content')) {
                const all = document.querySelectorAll('#mt-messages .mt-content');
                target = all[all.length - 1];
            }
            if (!target) return;
            const start = target.selectionStart;
            const end = target.selectionEnd;
            const val = target.value;
            target.value = val.substring(0, start) + tag + val.substring(end);
            target.selectionStart = target.selectionEnd = start + tag.length;
            target.focus();
            PromptEditor.markDirty();
            this.update();
            Preview.update();
            return;
        }

        const textarea = document.getElementById('content-editor');
        if (!textarea) return;

        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const val = textarea.value;

        textarea.value = val.substring(0, start) + tag + val.substring(end);
        textarea.selectionStart = textarea.selectionEnd = start + tag.length;
        textarea.focus();

        PromptEditor.markDirty();
        this.update();
        Preview.update();
    },

    /**
     * Full Placeholder Manager Modal anzeigen.
     * Zeigt alle Placeholder mit Usages, orphaned, unused.
     */
    async showManager() {
        const res = await Utils.apiCall('get_placeholder_usages');
        if (res.status !== 'ok') {
            Utils.showToast('Placeholder-Daten konnten nicht geladen werden', 'error');
            return;
        }

        const { usages, orphaned, unused } = res;
        let html = '<div class="ph-manager">';

        // --- Filter-Tabs ---
        html += `<div class="ph-manager-tabs">
            <button class="ph-tab active" data-ph-filter="all">Alle (${Object.keys(this.allPlaceholders).length})</button>
            <button class="ph-tab${unused.length ? ' has-issues' : ''}" data-ph-filter="unused">Unbenutzt (${unused.length})</button>
            <button class="ph-tab${Object.keys(orphaned).length ? ' has-issues' : ''}" data-ph-filter="orphaned">Verwaist (${Object.keys(orphaned).length})</button>
            <button class="ph-tab" data-ph-filter="static">Statisch</button>
        </div>`;

        // --- Neuer Placeholder Button ---
        html += `<div style="margin-bottom:10px">
            <button class="btn btn-accent btn-sm" id="btn-new-placeholder">+ Neuer Placeholder</button>
        </div>`;

        // --- Alle Placeholder ---
        html += '<div class="ph-manager-list" id="ph-manager-list">';

        // Registered Placeholders
        const phKeys = Object.keys(this.allPlaceholders).sort();
        for (const key of phKeys) {
            const ph = this.allPlaceholders[key];
            const phUsages = usages[key] || [];
            const isUnused = unused.includes(key);
            const phase = ph.resolve_phase || '?';
            const isStatic = ph.source === 'static' || ph.source === 'custom';

            html += `<div class="ph-manager-item${isUnused ? ' is-unused' : ''}" data-ph-type="registered${isUnused ? ' unused' : ''}${isStatic ? ' static' : ''}">
                <div class="ph-manager-header">
                    <span class="ph-key-lg">{{${Utils.escapeHtml(key)}}}</span>
                    <span class="ph-badge phase-${phase}">${Utils.escapeHtml(phase)}</span>
                    <span class="ph-usage-count">${phUsages.length} Prompt${phUsages.length !== 1 ? 's' : ''}</span>
                    ${isUnused ? '<span class="ph-badge-warn">Unbenutzt</span>' : ''}
                    ${isStatic ? `<button class="btn btn-danger btn-xs ph-delete-btn" data-ph-delete="${Utils.escapeHtml(key)}" title="Placeholder löschen">×</button>` : ''}
                </div>`;

            if (ph.description) {
                html += `<div class="ph-manager-desc">${Utils.escapeHtml(ph.description)}</div>`;
            }

            // Wert-Anzeige
            const val = this.values[key];
            if (val !== undefined && val !== null && val !== '') {
                let displayVal = String(val);
                if (displayVal.length > 120) displayVal = displayVal.substring(0, 117) + '...';
                html += `<div class="ph-manager-value"><strong>Wert:</strong> <code>${Utils.escapeHtml(displayVal)}</code></div>`;
            }

            // Usages
            if (phUsages.length > 0) {
                html += '<div class="ph-manager-usages">';
                for (const pid of phUsages) {
                    const pName = PromptList.prompts[pid]?.name || pid;
                    html += `<span class="ph-usage-link" data-goto-prompt="${pid}">${Utils.escapeHtml(pName)}</span>`;
                }
                html += '</div>';
            }

            html += '</div>';
        }

        // Orphaned Placeholders (in Content aber nicht in Registry)
        for (const [key, promptIds] of Object.entries(orphaned)) {
            html += `<div class="ph-manager-item is-orphaned" data-ph-type="orphaned">
                <div class="ph-manager-header">
                    <span class="ph-key-lg">{{${Utils.escapeHtml(key)}}}</span>
                    <span class="ph-badge-danger">Verwaist</span>
                    <span class="ph-usage-count">${promptIds.length} Prompt${promptIds.length !== 1 ? 's' : ''}</span>
                </div>
                <div class="ph-manager-desc">Nicht in der Registry registriert – wird nicht aufgelöst!</div>
                <div class="ph-manager-usages">`;
            for (const pid of promptIds) {
                const pName = PromptList.prompts[pid]?.name || pid;
                html += `<span class="ph-usage-link" data-goto-prompt="${pid}">${Utils.escapeHtml(pName)}</span>`;
            }
            html += '</div></div>';
        }

        html += '</div></div>';

        Modal.show(`Placeholder Manager`, html);

        // Filter-Tab-Events
        document.querySelectorAll('.ph-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.ph-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                const filter = tab.dataset.phFilter;
                document.querySelectorAll('.ph-manager-item').forEach(item => {
                    const type = item.dataset.phType;
                    if (filter === 'all') {
                        item.style.display = '';
                    } else if (filter === 'unused') {
                        item.style.display = type.includes('unused') ? '' : 'none';
                    } else if (filter === 'orphaned') {
                        item.style.display = type === 'orphaned' ? '' : 'none';
                    } else if (filter === 'static') {
                        item.style.display = type.includes('static') ? '' : 'none';
                    }
                });
            });
        });

        // Klick auf Prompt-Usage Link → Prompt öffnen
        document.querySelectorAll('.ph-usage-link').forEach(link => {
            link.addEventListener('click', () => {
                const pid = link.dataset.gotoPrompt;
                if (pid) {
                    Modal.hide();
                    App.selectPrompt(pid);
                }
            });
        });

        // Neuer Placeholder Button
        document.getElementById('btn-new-placeholder')?.addEventListener('click', () => {
            this.showNewPlaceholderDialog();
        });

        // Delete Buttons für statische Placeholder
        document.querySelectorAll('.ph-delete-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const key = btn.dataset.phDelete;
                if (!confirm(`Placeholder "{{${key}}}" wirklich löschen?`)) return;
                const delRes = await Utils.apiCall('delete_placeholder', key);
                if (delRes.status === 'ok') {
                    Utils.showToast(`Placeholder "${key}" gelöscht`, 'success');
                    await this.loadAll();
                    this.showManager();
                } else {
                    Utils.showToast('Fehler: ' + (delRes.message || ''), 'error');
                }
            });
        });
    },

    /**
     * Dialog zum Erstellen eines neuen statischen Placeholders.
     * Felder: Name + Standard-Wert. Key wird automatisch aus dem Namen generiert.
     * Registriert den Placeholder in der placeholder_registry.json als source=static.
     */
    showNewPlaceholderDialog() {
        const html = `
            <div class="new-prompt-form">
                <div class="form-field">
                    <label>Name</label>
                    <input type="text" id="new-ph-name" placeholder="Mein Placeholder" spellcheck="false">
                </div>
                <div class="form-field">
                    <label>Key: <code id="new-ph-key-preview" style="color:var(--accent)">...</code></label>
                </div>
                <div class="form-field">
                    <label>Standard-Wert</label>
                    <textarea id="new-ph-default" rows="4" spellcheck="false" placeholder="Wert eingeben..."
                        style="width:100%;font-family:'Cascadia Code',Consolas,monospace;font-size:12px;resize:vertical;background:var(--bg-input);color:var(--text-primary);border:1px solid var(--border);border-radius:var(--radius);padding:8px"></textarea>
                </div>
                <button class="btn btn-accent" id="btn-create-ph">Erstellen</button>
            </div>
        `;

        Modal.show('Neuer Placeholder', html);
        document.getElementById('new-ph-name')?.focus();

        // Key-Preview live aktualisieren
        document.getElementById('new-ph-name')?.addEventListener('input', () => {
            const name = document.getElementById('new-ph-name').value.trim();
            const key = Utils.nameToId(name);
            document.getElementById('new-ph-key-preview').textContent = key ? `{{${key}}}` : '...';
        });

        document.getElementById('btn-create-ph')?.addEventListener('click', async () => {
            const name = document.getElementById('new-ph-name').value.trim();
            const defaultVal = document.getElementById('new-ph-default').value;

            if (!name) {
                Utils.showToast('Name ist ein Pflichtfeld', 'warning');
                return;
            }

            const key = Utils.nameToId(name);
            if (!key || !/^[a-z][a-z0-9_]*$/.test(key)) {
                Utils.showToast('Ungültiger Name (muss gültige ID ergeben)', 'warning');
                return;
            }

            const data = { key, name, description: '', default: defaultVal, category: 'custom' };
            const res = await Utils.apiCall('create_placeholder', JSON.stringify(data));
            if (res.status === 'ok') {
                Utils.showToast(`Placeholder "{{${key}}}" erstellt ✓`, 'success');
                await this.loadAll();
                this.showManager();
            } else {
                Utils.showToast('Fehler: ' + (res.message || ''), 'error');
            }
        });
    }
};
