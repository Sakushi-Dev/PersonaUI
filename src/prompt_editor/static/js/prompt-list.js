/**
 * PromptList – Sidebar-Verwaltung.
 * Rendert die Prompt-Liste gruppiert nach Category.
 * Phase 4: Drag & Drop Reordering innerhalb einer Kategorie.
 */
const PromptList = {
    /** Alle Prompt-Metadata, indexiert nach ID. */
    prompts: {},

    /** Aktuell ausgewählte Prompt-ID. */
    selectedId: null,

    /** Drag & Drop State. */
    _dragItem: null,
    _dragCategory: null,

    /** Sortierreihenfolge der Kategorien. */
    CATEGORY_ORDER: [
        'system', 'persona', 'context', 'prefill', 'dialog_injection',
        'afterthought', 'summary', 'spec_autofill', 'utility', 'cortex', 'custom'
    ],

    /** Anzeigenamen. */
    CATEGORY_LABELS: {
        system: 'System',
        persona: 'Persona',
        context: 'Context',
        prefill: 'Prefill',
        dialog_injection: 'Dialog Injection',
        afterthought: 'Afterthought',
        summary: 'Summary',
        spec_autofill: 'Spec Autofill',
        utility: 'Utility',
        cortex: 'Cortex',
        custom: 'Custom'
    },

    /** Farben pro Kategorie. */
    CATEGORY_COLORS: {
        system: '#3b82f6',
        persona: '#a855f7',
        context: '#14b8a6',
        prefill: '#f97316',
        dialog_injection: '#f43f5e',
        afterthought: '#ec4899',
        summary: '#22c55e',
        spec_autofill: '#eab308',
        utility: '#6b7280',
        cortex: '#06b6d4',
        custom: '#94a3b8'
    },

    /**
     * Alle Prompts vom Backend laden und rendern.
     */
    async load() {
        const res = await Utils.apiCall('get_all_prompts');
        if (res.status === 'ok') {
            this.prompts = res.prompts;
            this.render();
        } else {
            Utils.showToast('Prompts konnten nicht geladen werden', 'error');
        }
    },

    /**
     * Sidebar rendern (optional gefiltert).
     * @param {string} filter  Suchtext (lowercase)
     */
    render(filter = '') {
        const container = document.getElementById('prompt-list');
        container.innerHTML = '';

        // Nach Kategorie gruppieren
        const groups = {};
        for (const [id, meta] of Object.entries(this.prompts)) {
            const cat = meta.category || 'custom';
            if (!groups[cat]) groups[cat] = [];
            groups[cat].push({ id, ...meta });
        }

        // Kategorien rendern
        for (const cat of this.CATEGORY_ORDER) {
            const items = groups[cat];
            if (!items || items.length === 0) continue;

            // Filtern
            const filtered = filter
                ? items.filter(p =>
                    p.name.toLowerCase().includes(filter) ||
                    p.id.toLowerCase().includes(filter))
                : items;
            if (filtered.length === 0) continue;

            // Nach Order sortieren
            filtered.sort((a, b) => (a.order || 0) - (b.order || 0));

            const color = this.CATEGORY_COLORS[cat] || '#888';
            const label = this.CATEGORY_LABELS[cat] || cat;

            // Gruppen-Container
            const group = document.createElement('div');
            group.className = 'prompt-group';
            group.dataset.category = cat;
            group.innerHTML = `
                <div class="prompt-group-header" data-category="${cat}">
                    <span class="group-arrow">\u25BE</span>
                    <span class="group-dot" style="background:${color}"></span>
                    <span class="group-label">${label}</span>
                    <span class="group-count">${filtered.length}</span>
                </div>
                <div class="prompt-group-items" data-category="${cat}"></div>
            `;

            const itemsEl = group.querySelector('.prompt-group-items');

            for (const prompt of filtered) {
                const item = document.createElement('div');
                item.className = 'prompt-item' + (prompt.id === this.selectedId ? ' active' : '');
                item.dataset.id = prompt.id;
                item.dataset.category = cat;
                item.draggable = !filter; // Drag nur ohne Filter

                const enabledClass = prompt.enabled ? 'enabled' : 'disabled';

                item.innerHTML = `
                    <span class="drag-handle" title="Ziehen zum Sortieren">\u2630</span>
                    <span class="item-dot" style="background:${color}; opacity:${prompt.enabled ? 1 : 0.3}"></span>
                    <span class="item-name ${enabledClass}">${Utils.escapeHtml(prompt.name)}</span>
                    <label class="toggle-switch" title="${prompt.enabled ? 'Deaktivieren' : 'Aktivieren'}">
                        <input type="checkbox" ${prompt.enabled ? 'checked' : ''} data-toggle-id="${prompt.id}">
                        <span class="toggle-slider"></span>
                    </label>
                `;

                // Klick: Prompt auswählen
                item.addEventListener('click', (e) => {
                    if (e.target.closest('.toggle-switch') || e.target.closest('.drag-handle')) return;
                    App.selectPrompt(prompt.id);
                });

                // Toggle: Enable/Disable
                const toggle = item.querySelector('input[type="checkbox"]');
                toggle.addEventListener('change', (e) => {
                    e.stopPropagation();
                    App.togglePrompt(prompt.id, toggle.checked);
                });

                // --- Drag & Drop ---
                if (!filter) {
                    this._bindDragEvents(item, cat);
                }

                itemsEl.appendChild(item);
            }

            // Gruppen-Header klick: Collapse
            const header = group.querySelector('.prompt-group-header');
            header.addEventListener('click', () => {
                group.classList.toggle('collapsed');
            });

            container.appendChild(group);
        }

        // Falls leer nach Filter
        if (container.children.length === 0 && filter) {
            container.innerHTML = '<div class="sidebar-loading">Keine Treffer</div>';
        }
    },

    /** Drag & Drop Event-Listener für ein Item binden. */
    _bindDragEvents(item, category) {
        item.addEventListener('dragstart', (e) => {
            this._dragItem = item;
            this._dragCategory = category;
            item.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/plain', item.dataset.id);
        });

        item.addEventListener('dragend', () => {
            item.classList.remove('dragging');
            document.querySelectorAll('.drag-over').forEach(el => el.classList.remove('drag-over'));
            this._dragItem = null;
            this._dragCategory = null;
        });

        item.addEventListener('dragover', (e) => {
            e.preventDefault();
            if (!this._dragItem || this._dragItem === item) return;
            // Nur innerhalb derselben Kategorie
            if (item.dataset.category !== this._dragCategory) return;
            e.dataTransfer.dropEffect = 'move';
            item.classList.add('drag-over');
        });

        item.addEventListener('dragleave', () => {
            item.classList.remove('drag-over');
        });

        item.addEventListener('drop', (e) => {
            e.preventDefault();
            item.classList.remove('drag-over');
            if (!this._dragItem || this._dragItem === item) return;
            if (item.dataset.category !== this._dragCategory) return;

            const container = item.parentNode;
            const allItems = [...container.children];
            const fromIdx = allItems.indexOf(this._dragItem);
            const toIdx = allItems.indexOf(item);

            if (fromIdx < toIdx) {
                container.insertBefore(this._dragItem, item.nextSibling);
            } else {
                container.insertBefore(this._dragItem, item);
            }

            // Neue Reihenfolge speichern
            this._saveNewOrder(container);
        });
    },

    /** Neue Reihenfolge nach DnD speichern. */
    async _saveNewOrder(container) {
        const items = [...container.querySelectorAll('.prompt-item')];
        const orderMap = {};
        items.forEach((el, idx) => {
            const id = el.dataset.id;
            const newOrder = (idx + 1) * 100;
            orderMap[id] = newOrder;
            if (this.prompts[id]) this.prompts[id].order = newOrder;
        });

        const res = await Utils.apiCall('reorder_prompts', JSON.stringify(orderMap));
        if (res.status === 'ok') {
            Utils.showToast('Reihenfolge gespeichert', 'success', 1500);
        } else {
            Utils.showToast('Reorder fehlgeschlagen', 'error');
        }
    },

    /**
     * Aktives Element visuell markieren.
     */
    setActive(id) {
        this.selectedId = id;
        document.querySelectorAll('.prompt-item').forEach(el => {
            el.classList.toggle('active', el.dataset.id === id);
        });
    },

    /**
     * Toggle-Status in lokaler Kopie aktualisieren.
     */
    updateToggle(id, enabled) {
        if (this.prompts[id]) {
            this.prompts[id].enabled = enabled;
        }
    }
};
