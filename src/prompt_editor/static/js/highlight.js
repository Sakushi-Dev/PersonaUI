/**
 * PlaceholderHighlight – Hebt {{placeholder}} im Editor visuell hervor.
 *
 * Technik: Ein unsichtbarer Backdrop-Div wird hinter jede Textarea gelegt.
 * Die Textarea bekommt transparenten Text (Caret bleibt sichtbar).
 * Der Backdrop rendert denselben Text mit farbigen <mark>-Tags um Placeholder.
 */
const PlaceholderHighlight = {
    /** Regex für Placeholder-Erkennung. */
    PLACEHOLDER_RE: /(\{\{[\w.]+\}\})/g,

    /** Gesetzte Textareas (WeakSet verhindert doppeltes Setup). */
    _initialized: new WeakSet(),

    /**
     * Haupt-Content-Textarea initialisieren.
     */
    init() {
        const textarea = document.getElementById('content-editor');
        if (textarea) this.attach(textarea);
    },

    /**
     * Highlight-Backdrop an eine Textarea anhängen.
     * @param {HTMLTextAreaElement} textarea
     */
    attach(textarea) {
        if (this._initialized.has(textarea)) {
            // Nur aktualisieren
            this.sync(textarea);
            return;
        }

        // Container basteln
        const wrapper = document.createElement('div');
        wrapper.className = 'highlight-wrapper';

        // Backdrop erstellen
        const backdrop = document.createElement('div');
        backdrop.className = 'highlight-backdrop';

        // Textarea in Wrapper verschieben
        textarea.parentNode.insertBefore(wrapper, textarea);
        wrapper.appendChild(backdrop);
        wrapper.appendChild(textarea);

        // Textarea-Klasse für transparenten Text
        textarea.classList.add('highlight-textarea');

        // Referenz speichern
        textarea._highlightBackdrop = backdrop;
        this._initialized.add(textarea);

        // Events binden
        textarea.addEventListener('input', () => this.sync(textarea));
        textarea.addEventListener('scroll', () => this._syncScroll(textarea));

        // ResizeObserver für resize: vertical
        if (window.ResizeObserver) {
            const ro = new ResizeObserver(() => this._syncSize(textarea));
            ro.observe(textarea);
        }

        // Initial rendern
        this.sync(textarea);
    },

    /**
     * Backdrop-Inhalt mit der Textarea synchronisieren.
     * @param {HTMLTextAreaElement} textarea
     */
    sync(textarea) {
        const backdrop = textarea._highlightBackdrop;
        if (!backdrop) return;

        const text = textarea.value;
        // HTML-Entities escapen, dann Placeholder hervorheben
        const highlighted = this._escapeHtml(text)
            .replace(this.PLACEHOLDER_RE, '<mark class="ph-mark">$1</mark>');

        // Trailing Newline braucht ein extra Zeichen damit die Höhe stimmt
        backdrop.innerHTML = highlighted + '\n';

        this._syncScroll(textarea);
        this._syncSize(textarea);
    },

    /**
     * Scroll-Position synchronisieren.
     */
    _syncScroll(textarea) {
        const backdrop = textarea._highlightBackdrop;
        if (!backdrop) return;
        backdrop.scrollTop = textarea.scrollTop;
        backdrop.scrollLeft = textarea.scrollLeft;
    },

    /**
     * Größe synchronisieren (bei resize: vertical).
     */
    _syncSize(textarea) {
        const backdrop = textarea._highlightBackdrop;
        if (!backdrop) return;
        backdrop.style.height = textarea.offsetHeight + 'px';
        backdrop.style.width = textarea.offsetWidth + 'px';
    },

    /**
     * Alle Multi-Turn Textareas aktualisieren (nach fillMultiTurn).
     */
    attachMultiTurn() {
        document.querySelectorAll('#mt-messages .mt-content').forEach(ta => {
            this.attach(ta);
        });
    },

    /**
     * HTML-Entities escapen.
     */
    _escapeHtml(text) {
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    }
};
