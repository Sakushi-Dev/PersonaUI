/**
 * Autocomplete – Placeholder-Autocomplete für die Content-Textarea.
 * Phase 4: Erkennt "{{" Eingabe und zeigt Dropdown mit Placeholder-Keys.
 */
const Autocomplete = {
    /** Dropdown-Element. */
    dropdown: null,

    /** Aktuell sichtbar? */
    isOpen: false,

    /** Gefilterte Vorschläge. */
    suggestions: [],

    /** Index des hervorgehobenen Items. */
    selectedIndex: -1,

    /** Position des "{{" im Text. */
    triggerStart: -1,

    /** Aktive Textarea (für multi-turn Unterstützung). */
    activeTextarea: null,

    /**
     * Autocomplete initialisieren.
     * Verwendet Event-Delegation für #content-editor und .mt-content Textareas.
     */
    init() {
        this.dropdown = document.getElementById('autocomplete-dropdown');
        if (!this.dropdown) return;

        // Delegated input handling for both main editor and multi-turn textareas
        document.addEventListener('input', (e) => {
            const ta = e.target;
            if (ta.id === 'content-editor' || ta.classList.contains('mt-content')) {
                this.activeTextarea = ta;
                this._handleInput(ta);
            }
        });

        // Keyboard navigation (delegated)
        document.addEventListener('keydown', (e) => {
            if (!this.isOpen) return;
            this._onKeydown(e);
        });

        // Close on click outside
        document.addEventListener('click', (e) => {
            if (this.isOpen && !this.dropdown.contains(e.target)) {
                this.close();
            }
        });
    },

    /**
     * Input-Handling: Prüfen ob Autocomplete geöffnet werden soll.
     * @param {HTMLTextAreaElement} textarea
     */
    _handleInput(textarea) {
        const cursorPos = textarea.selectionStart;
        const text = textarea.value;

        // Text vor dem Cursor
        const before = text.substring(0, cursorPos);

        // Suche nach "{{" gefolgt von optionalen Wortzeichen
        const match = before.match(/\{\{(\w*)$/);

        if (match) {
            this.triggerStart = cursorPos - match[0].length;
            const query = match[1].toLowerCase();
            this._showSuggestions(query, textarea);
        } else {
            this.close();
        }
    },

    /**
     * Keyboard-Navigation im Dropdown.
     */
    _onKeydown(e) {
        if (!this.isOpen) return;

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.selectedIndex = Math.min(this.selectedIndex + 1, this.suggestions.length - 1);
                this._updateHighlight();
                break;

            case 'ArrowUp':
                e.preventDefault();
                this.selectedIndex = Math.max(this.selectedIndex - 1, 0);
                this._updateHighlight();
                break;

            case 'Enter':
            case 'Tab':
                if (this.selectedIndex >= 0 && this.suggestions[this.selectedIndex]) {
                    e.preventDefault();
                    this._insertSuggestion(this.suggestions[this.selectedIndex]);
                }
                break;

            case 'Escape':
                e.preventDefault();
                e.stopPropagation();
                this.close();
                break;
        }
    },

    /**
     * Passende Vorschläge filtern und Dropdown anzeigen.
     */
    _showSuggestions(query, textarea) {
        const allKeys = Object.keys(PlaceholderInfo.allPlaceholders);

        this.suggestions = allKeys
            .filter(key => key.toLowerCase().includes(query))
            .sort((a, b) => {
                // Exakter Prefix-Match zuerst
                const aStarts = a.toLowerCase().startsWith(query) ? 0 : 1;
                const bStarts = b.toLowerCase().startsWith(query) ? 0 : 1;
                if (aStarts !== bStarts) return aStarts - bStarts;
                return a.localeCompare(b);
            })
            .slice(0, 12);

        if (this.suggestions.length === 0) {
            this.close();
            return;
        }

        this.selectedIndex = 0;
        this.isOpen = true;

        // Dropdown positionieren
        this._positionDropdown(textarea);

        // Inhalt rendern
        this.dropdown.innerHTML = '';
        for (let i = 0; i < this.suggestions.length; i++) {
            const key = this.suggestions[i];
            const ph = PlaceholderInfo.allPlaceholders[key];
            const phase = ph ? ph.resolve_phase : '?';

            const item = document.createElement('div');
            item.className = 'ac-item' + (i === 0 ? ' highlighted' : '');
            item.dataset.index = i;

            item.innerHTML = `
                <span class="ac-key">${Utils.escapeHtml(key)}</span>
                <span class="ph-badge phase-${phase}" style="font-size:9px">${Utils.escapeHtml(phase)}</span>
            `;

            item.addEventListener('mousedown', (e) => {
                e.preventDefault();
                this._insertSuggestion(key);
            });

            item.addEventListener('mouseenter', () => {
                this.selectedIndex = i;
                this._updateHighlight();
            });

            this.dropdown.appendChild(item);
        }

        this.dropdown.style.display = 'block';
    },

    /**
     * Dropdown unter dem Cursor positionieren.
     */
    _positionDropdown(textarea) {
        // Einfache Positionierung relativ zur Textarea
        const rect = textarea.getBoundingClientRect();
        const lineHeight = parseInt(getComputedStyle(textarea).lineHeight) || 18;

        // Cursor-Position schätzen
        const text = textarea.value.substring(0, textarea.selectionStart);
        const lines = text.split('\n');
        const currentLine = lines.length - 1;
        const scrollTop = textarea.scrollTop;

        const top = rect.top + (currentLine * lineHeight) - scrollTop + lineHeight + 4;
        const left = rect.left + 20;

        this.dropdown.style.top = Math.min(top, window.innerHeight - 250) + 'px';
        this.dropdown.style.left = Math.min(left, window.innerWidth - 280) + 'px';
    },

    /**
     * Vorschlag einfügen.
     */
    _insertSuggestion(key) {
        const textarea = this.activeTextarea;
        if (!textarea) return;
        const cursorPos = textarea.selectionStart;
        const text = textarea.value;

        // Ersetze "{{teiltext" mit "{{key}}"
        const before = text.substring(0, this.triggerStart);
        const after = text.substring(cursorPos);
        const insertion = `{{${key}}}`;

        textarea.value = before + insertion + after;

        // Cursor hinter die eingefügte Stelle setzen
        const newPos = this.triggerStart + insertion.length;
        textarea.setSelectionRange(newPos, newPos);
        textarea.focus();

        this.close();

        // Change-Event triggern für Dirty-Tracking
        textarea.dispatchEvent(new Event('input', { bubbles: true }));
    },

    /**
     * Hervorhebung aktualisieren.
     */
    _updateHighlight() {
        this.dropdown.querySelectorAll('.ac-item').forEach((el, i) => {
            el.classList.toggle('highlighted', i === this.selectedIndex);
        });
        // Ins Sichtfeld scrollen
        const highlighted = this.dropdown.querySelector('.highlighted');
        if (highlighted) highlighted.scrollIntoView({ block: 'nearest' });
    },

    /**
     * Dropdown schließen.
     */
    close() {
        if (this.dropdown) {
            this.dropdown.style.display = 'none';
        }
        this.isOpen = false;
        this.selectedIndex = -1;
        this.suggestions = [];
        this.triggerStart = -1;
    }
};
