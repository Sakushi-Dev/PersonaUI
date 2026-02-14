/**
 * PromptEditor – Editor-Panel-Verwaltung.
 * Metadata-Formular, Content-Textarea, Varianten-Tabs.
 */
const PromptEditor = {
    /** Aktuell geladener Prompt (vollständig: id, meta, content). */
    currentPrompt: null,

    /** Aktuell ausgewählte Variante. */
    currentVariant: 'default',

    /** Ungespeicherte Änderungen? */
    isDirty: false,

    /** Originalinhalt zum Vergleich. */
    originalContent: '',

    /** Editor-Bereich anzeigen. */
    show() {
        document.getElementById('welcome-screen').style.display = 'none';
        document.getElementById('editor-container').style.display = 'block';
    },

    /** Editor-Bereich ausblenden, Welcome anzeigen. */
    hide() {
        document.getElementById('welcome-screen').style.display = 'flex';
        document.getElementById('editor-container').style.display = 'none';
        this.currentPrompt = null;
    },

    /**
     * Prompt laden und im Editor anzeigen.
     * @param {string} promptId
     */
    async load(promptId) {
        const res = await Utils.apiCall('get_prompt', promptId);
        if (res.status !== 'ok') {
            Utils.showToast('Fehler beim Laden: ' + (res.message || ''), 'error');
            return;
        }

        this.currentPrompt = res.prompt;
        this.currentVariant = 'default';
        this.isDirty = false;

        this.show();
        this.fillForm();
        this.updateVariantTabs();
        this.fillContent();
        PlaceholderInfo.update();
        Preview.update();
    },

    /** Formularfelder mit Metadata befüllen. */
    fillForm() {
        const meta = this.currentPrompt.meta;
        document.getElementById('meta-id').value = this.currentPrompt.id;
        document.getElementById('meta-name').value = meta.name || '';
        document.getElementById('meta-description').value = meta.description || '';
        document.getElementById('meta-category').value = meta.category || 'custom';
        document.getElementById('meta-target').value = meta.target || 'system_prompt';
        document.getElementById('meta-position').value = meta.position || 'system_prompt';
        document.getElementById('meta-order').value = meta.order || 0;
        document.getElementById('meta-domain').value = meta.domain_file || '';
        document.getElementById('meta-enabled').checked = meta.enabled !== false;
    },

    /** Content-Textarea mit der aktuellen Variante befüllen. */
    fillContent() {
        const content = this.currentPrompt.content || {};
        const variants = content.variants || {};
        // Für die ausgewählte Variante: nur exakt diese Variante laden.
        // Kein Fallback auf default – sonst kann man keine neue Variante anlegen.
        const variantData = variants[this.currentVariant] || {};

        const textarea = document.getElementById('content-editor');
        const mtEditor = document.getElementById('multiturn-editor');

        if (this.isMultiTurn()) {
            textarea.style.display = 'none';
            mtEditor.style.display = 'block';
            const messages = variantData.messages || [];
            this.fillMultiTurn(messages);
            this.originalContent = JSON.stringify(messages);
        } else {
            textarea.style.display = '';
            mtEditor.style.display = 'none';
            textarea.value = variantData.content || '';
            this.originalContent = textarea.value;
            PlaceholderHighlight.sync(textarea);
        }
        this.isDirty = false;
        this.updateDirtyIndicator();
    },

    /** Varianten-Tabs rendern. Experimental wird immer angezeigt. */
    updateVariantTabs() {
        const content = this.currentPrompt.content || {};
        const variants = Object.keys(content.variants || {});
        const tabContainer = document.getElementById('variant-tabs');
        tabContainer.innerHTML = '';

        // default + experimental immer, plus weitere falls vorhanden
        const allVariants = ['default', 'experimental', ...variants.filter(v => v !== 'default' && v !== 'experimental')];
        const unique = [...new Set(allVariants)];

        for (const v of unique) {
            const exists = variants.includes(v);
            const tab = document.createElement('button');
            tab.className = 'variant-tab' + (v === this.currentVariant ? ' active' : '') + (!exists && v !== 'default' ? ' variant-empty' : '');
            tab.dataset.variant = v;
            tab.textContent = v.charAt(0).toUpperCase() + v.slice(1);
            tab.addEventListener('click', () => this.switchVariant(v));
            tabContainer.appendChild(tab);
        }
    },

    /**
     * Variante wechseln.
     * @param {string} variant
     */
    switchVariant(variant) {
        if (variant === this.currentVariant) return;
        if (this.isDirty && !confirm('Ungespeicherte Änderungen verwerfen?')) return;

        this.currentVariant = variant;
        this.fillContent();
        this.updateVariantTabs();
        PlaceholderInfo.update();
        Preview.update();
    },

    /** Prüft ob aktueller Prompt multi_turn ist. */
    isMultiTurn() {
        return this.currentPrompt?.meta?.type === 'multi_turn';
    },

    /** Multi-Turn Startrolle. */
    _mtStartRole: 'assistant',

    /** Aktuellen Content holen (Text oder JSON für multi_turn). */
    getCurrentContent() {
        if (this.isMultiTurn()) {
            return JSON.stringify(this.getMultiTurnMessages(), null, 2);
        }
        return document.getElementById('content-editor').value;
    },

    /** Multi-Turn Editor befüllen. */
    fillMultiTurn(messages) {
        const container = document.getElementById('mt-messages');
        container.innerHTML = '';
        this._mtStartRole = (messages.length > 0) ? (messages[0].role || 'assistant') : 'assistant';

        document.querySelectorAll('.mt-role-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.role === this._mtStartRole);
        });

        if (messages.length === 0) {
            this._addMtRow('', 0);
        } else {
            for (let i = 0; i < messages.length; i++) {
                this._addMtRow(messages[i].content || '', i);
            }
        }
        this._updateMtRemoveBtn();
    },

    /** Rolle für Index berechnen. */
    _getMtRole(index) {
        const other = this._mtStartRole === 'assistant' ? 'user' : 'assistant';
        return (index % 2 === 0) ? this._mtStartRole : other;
    },

    /** Eine Message-Zeile zum Multi-Turn Editor hinzufügen. */
    _addMtRow(content, index) {
        const container = document.getElementById('mt-messages');
        const role = this._getMtRole(index);

        const row = document.createElement('div');
        row.className = 'mt-message';
        row.dataset.index = index;

        const header = document.createElement('div');
        header.className = 'mt-msg-header';

        const badge = document.createElement('span');
        badge.className = `mt-role-badge mt-role-${role}`;
        badge.textContent = role === 'assistant' ? 'Assistant' : 'User';

        const num = document.createElement('span');
        num.className = 'mt-msg-num';
        num.textContent = `#${index + 1}`;

        header.appendChild(badge);
        header.appendChild(num);

        const textarea = document.createElement('textarea');
        textarea.className = 'mt-content';
        textarea.rows = 3;
        textarea.value = content;
        textarea.spellcheck = false;
        textarea.placeholder = role === 'assistant' ? 'Assistant-Nachricht...' : 'User-Nachricht...';
        textarea.addEventListener('input', () => {
            this.markDirty();
            PlaceholderInfo.update();
            Preview.update();
        });

        row.appendChild(header);
        row.appendChild(textarea);
        container.appendChild(row);
        PlaceholderHighlight.attach(textarea);
    },

    /** Alle Rollen-Badges aktualisieren (nach Startrolle-Wechsel). */
    _updateMtRoles() {
        document.querySelectorAll('#mt-messages .mt-message').forEach((row, i) => {
            row.dataset.index = i;
            const role = this._getMtRole(i);
            const badge = row.querySelector('.mt-role-badge');
            badge.className = `mt-role-badge mt-role-${role}`;
            badge.textContent = role === 'assistant' ? 'Assistant' : 'User';
            const ta = row.querySelector('.mt-content');
            ta.placeholder = role === 'assistant' ? 'Assistant-Nachricht...' : 'User-Nachricht...';
        });
    },

    /** Messages aus Multi-Turn Editor auslesen. */
    getMultiTurnMessages() {
        const messages = [];
        document.querySelectorAll('#mt-messages .mt-message').forEach((row, i) => {
            const ta = row.querySelector('.mt-content');
            messages.push({ role: this._getMtRole(i), content: ta.value });
        });
        return messages;
    },

    /** Remove-Button State aktualisieren. */
    _updateMtRemoveBtn() {
        const btn = document.getElementById('btn-mt-remove');
        if (btn) {
            const count = document.querySelectorAll('#mt-messages .mt-message').length;
            btn.disabled = count <= 1;
            btn.style.opacity = count <= 1 ? '0.3' : '1';
        }
    },

    /** Als geändert markieren. */
    markDirty() {
        this.isDirty = true;
        this.updateDirtyIndicator();
    },

    /** Save-Button visuell aktualisieren. */
    updateDirtyIndicator() {
        const btn = document.getElementById('btn-save');
        if (btn) {
            btn.classList.toggle('has-changes', this.isDirty);
            btn.textContent = this.isDirty ? 'Speichern *' : 'Speichern';
        }
    },

    /** Prompt speichern (Content + Metadata). */
    async save() {
        if (!this.currentPrompt) return;

        const promptId = this.currentPrompt.id;
        const content = this.getCurrentContent();

        // Content-Struktur zusammenbauen
        const existingContent = this.currentPrompt.content || {};
        const variants = { ...(existingContent.variants || {}) };

        if (this.currentPrompt.meta.type === 'multi_turn') {
            try {
                variants[this.currentVariant] = { messages: JSON.parse(content) };
            } catch (e) {
                Utils.showToast('Ungültiges JSON: ' + e.message, 'error');
                return;
            }
        } else {
            variants[this.currentVariant] = { content: content };
        }

        // Metadata aus Formular
        const meta = {
            name: document.getElementById('meta-name').value,
            description: document.getElementById('meta-description').value,
            category: document.getElementById('meta-category').value,
            type: this.currentPrompt.meta.type || 'text',
            target: document.getElementById('meta-target').value,
            position: document.getElementById('meta-position').value,
            order: parseInt(document.getElementById('meta-order').value) || 0,
            domain_file: document.getElementById('meta-domain').value,
            enabled: document.getElementById('meta-enabled').checked,
            tags: this.currentPrompt.meta.tags || [],
        };

        // Variant condition beibehalten wenn vorhanden
        if (this.currentPrompt.meta.variant_condition) {
            meta.variant_condition = this.currentPrompt.meta.variant_condition;
        }

        // Validierung vor dem Speichern
        if (!meta.name.trim()) {
            Utils.showToast('Name darf nicht leer sein', 'warning');
            return;
        }

        // Prüfe auf unregistrierte Placeholder
        const usedPlaceholders = Utils.extractPlaceholders(
            this.isMultiTurn() ? JSON.stringify(this.getMultiTurnMessages()) : document.getElementById('content-editor').value
        );
        const knownPlaceholders = PlaceholderInfo.allPlaceholders ? Object.keys(PlaceholderInfo.allPlaceholders) : [];
        const unknownPh = usedPlaceholders.filter(p => !knownPlaceholders.includes(p));
        if (unknownPh.length > 0) {
            const proceed = confirm(`Unregistrierte Placeholder gefunden: ${unknownPh.join(', ')}\n\nTrotzdem speichern?`);
            if (!proceed) return;
        }

        const data = { content: { variants }, meta };

        const res = await Utils.apiCall('save_prompt', promptId, JSON.stringify(data));
        if (res.status === 'ok') {
            this.isDirty = false;
            this.originalContent = content;
            // Lokalen Prompt aktualisieren
            this.currentPrompt.content = { variants };
            this.currentPrompt.meta = meta;
            this.updateDirtyIndicator();
            Utils.showToast('Gespeichert \u2713', 'success');

            // placeholders_used automatisch aktualisieren
            const allUsed = new Set();
            for (const vData of Object.values(variants)) {
                const texts = [];
                if (vData.content) texts.push(vData.content);
                if (vData.messages) {
                    for (const msg of vData.messages) {
                        if (msg.content) texts.push(msg.content);
                    }
                }
                for (const text of texts) {
                    for (const m of text.matchAll(/\{\{(\w+)\}\}/g)) {
                        allUsed.add(m[1]);
                    }
                }
            }
            Utils.apiCall('update_placeholders_used', promptId, JSON.stringify([...allUsed]));

            // Sidebar aktualisieren
            PromptList.prompts[promptId] = { ...PromptList.prompts[promptId], ...meta };
            PromptList.render(document.getElementById('search-input').value.toLowerCase());
            PromptList.setActive(promptId);
        } else {
            Utils.showToast('Fehler: ' + (res.message || ''), 'error');
        }
    },

    /** Änderungen verwerfen. */
    discard() {
        if (!this.isDirty) return;
        if (!confirm('Änderungen verwerfen?')) return;

        if (this.isMultiTurn()) {
            try {
                const messages = JSON.parse(this.originalContent);
                this.fillMultiTurn(messages);
            } catch {
                this.fillMultiTurn([]);
            }
        } else {
            const ta = document.getElementById('content-editor');
            ta.value = this.originalContent;
            PlaceholderHighlight.sync(ta);
        }
        this.isDirty = false;
        this.updateDirtyIndicator();
        PlaceholderInfo.update();
        Preview.update();
    }
};
