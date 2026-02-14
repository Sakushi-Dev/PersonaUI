/**
 * Modal – Einfaches Modal-System.
 */
const Modal = {
    /**
     * Modal anzeigen.
     * @param {string} title
     * @param {string} bodyHtml
     * @param {string} [footerHtml]
     */
    show(title, bodyHtml, footerHtml = '') {
        document.getElementById('modal-title').textContent = title;
        document.getElementById('modal-body').innerHTML = bodyHtml;
        document.getElementById('modal-footer').innerHTML = footerHtml;
        document.getElementById('modal-overlay').style.display = 'flex';
    },

    /** Modal schließen. */
    hide() {
        document.getElementById('modal-overlay').style.display = 'none';
    }
};


/**
 * App – Haupt-Koordinator.
 * Initialisiert alles, bindet Events, koordiniert zwischen Modulen.
 */
const App = {
    /**
     * Initialisierung beim Start.
     */
    async init() {
        try {
            // Paralleles Laden der initialen Daten
            await Promise.all([
                PromptList.load(),
                PlaceholderInfo.loadAll()
            ]);

            // Status-Bar aktualisieren
            await this.updateStatus();

            // Events binden
            this.bindEvents();

            // Autocomplete initialisieren
            Autocomplete.init();

            // Placeholder-Highlighting initialisieren
            PlaceholderHighlight.init();

            console.log('Prompt Editor initialisiert');
        } catch (e) {
            console.error('Initialisierung fehlgeschlagen:', e);
            Utils.showToast('Initialisierung fehlgeschlagen', 'error');
        }
    },

    /**
     * Alle Event-Listener binden.
     */
    bindEvents() {
        // --- Suche ---
        document.getElementById('search-input').addEventListener('input', (e) => {
            PromptList.render(e.target.value.toLowerCase());
            if (PromptList.selectedId) {
                PromptList.setActive(PromptList.selectedId);
            }
        });

        // --- Content-Änderungen ---
        document.getElementById('content-editor').addEventListener('input', () => {
            PromptEditor.markDirty();
            PlaceholderInfo.update();
            Preview.update();
            PlaceholderHighlight.sync(document.getElementById('content-editor'));
        });

        // --- Metadata-Änderungen tracken ---
        const metaFields = ['meta-name', 'meta-description', 'meta-category', 'meta-target', 'meta-position', 'meta-order', 'meta-domain'];
        for (const fieldId of metaFields) {
            const el = document.getElementById(fieldId);
            if (el) {
                el.addEventListener('input', () => PromptEditor.markDirty());
                el.addEventListener('change', () => PromptEditor.markDirty());
            }
        }
        document.getElementById('meta-enabled')?.addEventListener('change', () => PromptEditor.markDirty());

        // --- Save / Discard / Delete ---
        document.getElementById('btn-save').addEventListener('click', () => {
            PromptEditor.save();
        });

        document.getElementById('btn-discard').addEventListener('click', () => {
            PromptEditor.discard();
        });

        document.getElementById('btn-delete').addEventListener('click', () => {
            this.deletePrompt();
        });

        // --- Duplicate ---
        document.getElementById('btn-duplicate').addEventListener('click', () => {
            this.duplicatePrompt();
        });

        // --- Restore (Default Reset) ---
        document.getElementById('btn-restore').addEventListener('click', () => {
            if (PromptEditor.currentPrompt) {
                this.resetToDefault(PromptEditor.currentPrompt.id);
            }
        });

        // --- Sidebar-Buttons ---
        document.getElementById('btn-new-prompt').addEventListener('click', () => {
            this.showNewPromptDialog();
        });

        document.getElementById('btn-validate').addEventListener('click', () => {
            this.validate();
        });

        document.getElementById('btn-full-preview').addEventListener('click', () => {
            Preview.showFullPreview();
        });

        document.getElementById('btn-compositor').addEventListener('click', () => {
            Compositor.show();
        });

        document.getElementById('btn-placeholder-mgr').addEventListener('click', () => {
            PlaceholderInfo.showManager();
        });

        document.getElementById('btn-insert-placeholder').addEventListener('click', () => {
            PlaceholderInfo.showInsertPicker();
        });

        // --- Multi-Turn Editor Events ---
        document.getElementById('multiturn-editor').addEventListener('click', (e) => {
            const roleBtn = e.target.closest('.mt-role-btn');
            if (roleBtn) {
                const role = roleBtn.dataset.role;
                if (role !== PromptEditor._mtStartRole) {
                    PromptEditor._mtStartRole = role;
                    document.querySelectorAll('.mt-role-btn').forEach(btn => {
                        btn.classList.toggle('active', btn.dataset.role === role);
                    });
                    PromptEditor._updateMtRoles();
                    PromptEditor.markDirty();
                    PlaceholderInfo.update();
                    Preview.update();
                }
            }
            if (e.target.closest('#btn-mt-add')) {
                const count = document.querySelectorAll('#mt-messages .mt-message').length;
                PromptEditor._addMtRow('', count);
                PromptEditor._updateMtRemoveBtn();
                PromptEditor.markDirty();
                const newTa = document.querySelector('#mt-messages .mt-message:last-child .mt-content');
                if (newTa) newTa.focus();
            }
            if (e.target.closest('#btn-mt-remove')) {
                const messages = document.querySelectorAll('#mt-messages .mt-message');
                if (messages.length > 1) {
                    messages[messages.length - 1].remove();
                    PromptEditor._updateMtRemoveBtn();
                    PromptEditor.markDirty();
                    PlaceholderInfo.update();
                    Preview.update();
                }
            }
        });

        document.getElementById('btn-reload').addEventListener('click', () => {
            this.reload();
        });

        // --- Keyboard Shortcuts ---
        document.addEventListener('keydown', (e) => {
            // Autocomplete ist offen → nicht weiter
            if (Autocomplete.isOpen) return;

            // Ctrl+S → Speichern
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                PromptEditor.save();
            }
            // Ctrl+Shift+N → Neuer Prompt
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'N') {
                e.preventDefault();
                this.showNewPromptDialog();
            }
            // Ctrl+Shift+D → Duplizieren
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'D') {
                e.preventDefault();
                this.duplicatePrompt();
            }
            // Ctrl+Shift+P → Placeholder Manager
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'P') {
                e.preventDefault();
                PlaceholderInfo.showManager();
            }
            // Ctrl+Shift+K → Compositor
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'K') {
                e.preventDefault();
                Compositor.show();
            }
            // Ctrl+F → Suche fokussieren
            if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
                e.preventDefault();
                document.getElementById('search-input').focus();
                document.getElementById('search-input').select();
            }
            // Escape → Modal schließen oder Suche leeren
            if (e.key === 'Escape') {
                const overlay = document.getElementById('modal-overlay');
                if (overlay.style.display === 'flex') {
                    Modal.hide();
                } else {
                    const search = document.getElementById('search-input');
                    if (document.activeElement === search && search.value) {
                        search.value = '';
                        PromptList.render();
                        if (PromptList.selectedId) PromptList.setActive(PromptList.selectedId);
                    }
                }
            }
        });

        // --- Modal schließen ---
        document.getElementById('modal-close').addEventListener('click', () => {
            Modal.hide();
        });

        document.getElementById('modal-overlay').addEventListener('click', (e) => {
            if (e.target.id === 'modal-overlay') Modal.hide();
        });
    },

    // ===== Aktionen =====

    /**
     * Prompt auswählen und im Editor laden.
     * @param {string} id
     */
    async selectPrompt(id) {
        if (PromptEditor.isDirty) {
            if (!confirm('Ungespeicherte Änderungen verwerfen?')) return;
        }
        PromptList.setActive(id);
        await PromptEditor.load(id);
    },

    /**
     * Prompt ein/ausschalten.
     * @param {string} id
     * @param {boolean} enabled
     */
    async togglePrompt(id, enabled) {
        const res = await Utils.apiCall('toggle_prompt', id, enabled);
        if (res.status === 'ok') {
            PromptList.updateToggle(id, enabled);
            const name = PromptList.prompts[id]?.name || id;
            Utils.showToast(
                `${enabled ? 'Aktiviert' : 'Deaktiviert'}: ${name}`,
                'success',
                2000
            );
        } else {
            Utils.showToast('Toggle fehlgeschlagen', 'error');
            // Checkbox zurücksetzen
            const cb = document.querySelector(`input[data-toggle-id="${id}"]`);
            if (cb) cb.checked = !enabled;
        }
    },

    /**
     * Aktuellen Prompt löschen (mit Bestätigung).
     */
    async deletePrompt() {
        if (!PromptEditor.currentPrompt) return;

        const id = PromptEditor.currentPrompt.id;
        const name = PromptEditor.currentPrompt.meta.name || id;

        Modal.show(
            'Prompt löschen',
            `<p class="confirm-text">Soll der Prompt <strong>${Utils.escapeHtml(name)}</strong> (${Utils.escapeHtml(id)}) wirklich gelöscht werden?<br>Diese Aktion kann nicht rückgängig gemacht werden.</p>
             <div class="confirm-actions">
                 <button class="btn btn-outline" onclick="Modal.hide()">Abbrechen</button>
                 <button class="btn btn-danger" id="btn-confirm-delete">Löschen</button>
             </div>`
        );

        document.getElementById('btn-confirm-delete').addEventListener('click', async () => {
            const res = await Utils.apiCall('delete_prompt', id);
            if (res.status === 'ok') {
                Modal.hide();
                PromptEditor.hide();
                PromptList.selectedId = null;
                delete PromptList.prompts[id];
                PromptList.render(document.getElementById('search-input').value.toLowerCase());
                await this.updateStatus();
                Utils.showToast(`Gelöscht: ${name}`, 'success');
            } else {
                Utils.showToast('Löschen fehlgeschlagen: ' + (res.message || ''), 'error');
            }
        });
    },

    /**
     * Aktuellen Prompt duplizieren.
     */
    async duplicatePrompt() {
        if (!PromptEditor.currentPrompt) {
            Utils.showToast('Kein Prompt zum Duplizieren ausgewählt', 'warning');
            return;
        }

        const sourceId = PromptEditor.currentPrompt.id;
        const sourceName = PromptEditor.currentPrompt.meta.name || sourceId;

        const html = `
            <div class="new-prompt-form">
                <p style="font-size:12px;color:var(--text-muted);margin-bottom:8px">
                    Kopie von <strong>${Utils.escapeHtml(sourceName)}</strong>
                </p>
                <div class="form-field">
                    <label>Neue ID (snake_case)</label>
                    <input type="text" id="dup-prompt-id" value="${Utils.escapeHtml(sourceId + '_copy')}" spellcheck="false">
                </div>
                <div class="form-field">
                    <label>Neuer Name</label>
                    <input type="text" id="dup-prompt-name" value="${Utils.escapeHtml(sourceName + ' (Kopie)')}" spellcheck="false">
                </div>
                <button class="btn btn-accent" id="btn-do-duplicate">Duplizieren</button>
            </div>
        `;

        Modal.show('Prompt duplizieren', html);

        // Auto-ID aus Name
        const nameInput = document.getElementById('dup-prompt-name');
        const idInput = document.getElementById('dup-prompt-id');
        nameInput.addEventListener('input', () => {
            idInput.value = Utils.nameToId(nameInput.value);
        });

        document.getElementById('btn-do-duplicate').addEventListener('click', async () => {
            const newId = idInput.value.trim();
            const newName = nameInput.value.trim();

            if (!newId || !newName) {
                Utils.showToast('ID und Name sind Pflichtfelder', 'warning');
                return;
            }

            if (!/^[a-z][a-z0-9_]*$/.test(newId)) {
                Utils.showToast('ID: nur Kleinbuchstaben, Zahlen und _ erlaubt', 'warning');
                return;
            }

            const res = await Utils.apiCall('duplicate_prompt', sourceId, newId, newName);
            if (res.status === 'ok') {
                Modal.hide();
                await PromptList.load();
                await App.selectPrompt(res.id);
                await App.updateStatus();
                Utils.showToast('Dupliziert \u2713', 'success');
            } else {
                Utils.showToast('Fehler: ' + (res.message || ''), 'error');
            }
        });
    },

    // ===== Restore / Reset =====

    /**
     * Prompt auf Factory-Default zurücksetzen.
     */
    async resetToDefault(promptId) {
        const name = PromptEditor.currentPrompt?.meta?.name || promptId;
        if (!confirm(`„${name}" auf Factory-Default zurücksetzen?\n\nAlle Änderungen gehen verloren.`)) return;

        const res = await Utils.apiCall('reset_prompt_to_default', promptId);
        if (res.status === 'ok') {
            await PromptEditor.load(promptId);
            Utils.showToast('Auf Default zurückgesetzt ✓', 'success');
        } else {
            Utils.showToast('Fehler: ' + (res.message || ''), 'error');
        }
    },

    /**
     * Alle Prompts validieren.
     */
    async validate() {
        const res = await Utils.apiCall('validate_all');
        if (res.status !== 'ok') {
            Utils.showToast('Validierung fehlgeschlagen', 'error');
            return;
        }

        const errors = res.errors || [];
        const warnings = res.warnings || [];

        if (errors.length === 0 && warnings.length === 0) {
            Utils.showToast('\u2713 Alle Prompts valide', 'success');
            return;
        }

        let html = '';
        if (errors.length > 0) {
            html += '<div class="validation-section"><h3>Fehler (' + errors.length + ')</h3><ul>';
            for (const e of errors) {
                html += `<li class="v-error">${Utils.escapeHtml(e)}</li>`;
            }
            html += '</ul></div>';
        }
        if (warnings.length > 0) {
            html += '<div class="validation-section"><h3>Warnungen (' + warnings.length + ')</h3><ul>';
            for (const w of warnings) {
                html += `<li class="v-warning">${Utils.escapeHtml(w)}</li>`;
            }
            html += '</ul></div>';
        }

        Modal.show('Validierungsergebnis', html);
    },

    /**
     * Alles neu laden (Engine + UI).
     */
    async reload() {
        const res = await Utils.apiCall('reload');
        if (res.status === 'ok') {
            await PromptList.load();
            await PlaceholderInfo.loadAll();
            PromptEditor.hide();
            PromptList.selectedId = null;
            await this.updateStatus();
            Utils.showToast('Neu geladen \u2713', 'success');
        } else {
            Utils.showToast('Reload fehlgeschlagen: ' + (res.message || ''), 'error');
        }
    },

    /**
     * Dialog zum Erstellen eines neuen Prompts.
     */
    async showNewPromptDialog() {
        const html = `
            <div class="new-prompt-form">
                <div class="form-field">
                    <label>Name</label>
                    <input type="text" id="new-prompt-name" placeholder="Mein Prompt" spellcheck="false">
                </div>
                <div class="form-field">
                    <label>ID (auto-generiert, anpassbar)</label>
                    <input type="text" id="new-prompt-id" placeholder="wird_aus_name_generiert" spellcheck="false">
                </div>
                <div class="form-field">
                    <label>Category</label>
                    <select id="new-prompt-category">
                        <option value="custom" selected>Custom</option>
                        <option value="system">System</option>
                        <option value="persona">Persona</option>
                        <option value="context">Context</option>
                        <option value="prefill">Prefill</option>
                        <option value="dialog_injection">Dialog Injection</option>
                        <option value="afterthought">Afterthought</option>
                        <option value="summary">Summary</option>
                        <option value="utility">Utility</option>
                    </select>
                </div>
                <div class="form-field">
                    <label>Domain-Datei (1 Datei pro Prompt)</label>
                    <input type="text" id="new-prompt-domain" placeholder="auto: prompt_id.json" value="" spellcheck="false">
                </div>
                <button class="btn btn-accent" id="btn-create-prompt">Erstellen</button>
            </div>
        `;

        Modal.show('Neuen Prompt erstellen', html);

        // Auto-ID aus Name
        const nameInput = document.getElementById('new-prompt-name');
        const idInput = document.getElementById('new-prompt-id');
        const domainInput = document.getElementById('new-prompt-domain');
        nameInput.addEventListener('input', () => {
            const newId = Utils.nameToId(nameInput.value);
            idInput.value = newId;
            if (domainInput && newId) {
                domainInput.value = newId + '.json';
            }
        });
        // Fokus auf Name-Feld
        nameInput.focus();

        // Event nach dem Rendern binden
        document.getElementById('btn-create-prompt').addEventListener('click', async () => {
            const name = document.getElementById('new-prompt-name').value.trim();
            let id = document.getElementById('new-prompt-id').value.trim();
            const category = document.getElementById('new-prompt-category').value;
            const domain = document.getElementById('new-prompt-domain').value.trim();

            if (!name) {
                Utils.showToast('Name ist ein Pflichtfeld', 'warning');
                return;
            }

            // Auto-ID falls leer
            if (!id) {
                id = Utils.nameToId(name);
            }

            // ID-Format prüfen
            if (!/^[a-z][a-z0-9_]*$/.test(id)) {
                Utils.showToast('ID: nur Kleinbuchstaben, Zahlen und _ erlaubt', 'warning');
                return;
            }

            const data = {
                id: id,
                meta: {
                    name: name,
                    description: '',
                    category: category,
                    type: category === 'dialog_injection' ? 'multi_turn' : 'text',
                    target: category === 'dialog_injection' ? 'message' : 'system_prompt',
                    position: category === 'dialog_injection' ? 'consent_dialog' : 'system_prompt',
                    order: 9999,
                    enabled: true,
                    domain_file: domain || (id + '.json'),
                    tags: ['custom']
                },
                content: {
                    variants: {
                        default: category === 'dialog_injection'
                            ? { messages: [{ role: 'assistant', content: '' }] }
                            : { content: '' }
                    }
                }
            };

            const res = await Utils.apiCall('create_prompt', JSON.stringify(data));
            if (res.status === 'ok') {
                Modal.hide();
                await PromptList.load();
                await App.selectPrompt(res.id);
                await App.updateStatus();
                Utils.showToast('Prompt erstellt \u2713', 'success');
            } else {
                Utils.showToast('Fehler: ' + (res.message || ''), 'error');
            }
        });
    },

    /**
     * Status-Bar aktualisieren.
     */
    async updateStatus() {
        const res = await Utils.apiCall('get_engine_info');
        if (res.status === 'ok') {
            const el = document.getElementById('status-text');
            const hasErrors = res.load_errors.length > 0;
            const errorText = hasErrors
                ? `${res.load_errors.length} Fehler`
                : 'Keine Fehler';
            const errorClass = hasErrors ? 'status-error' : 'status-ok';
            el.innerHTML = `<span class="${errorClass}">\u25CF</span> ${res.prompt_count} Prompts | ${res.placeholder_count} Placeholder | ${errorText}`;
        }
    }
};


// ===== Initialisierung bei pywebview-ready =====
window.addEventListener('pywebviewready', () => {
    App.init().catch(e => {
        console.error('Init failed:', e);
        document.getElementById('status-text').textContent = 'Fehler bei der Initialisierung';
    });
});
