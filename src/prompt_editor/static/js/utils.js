/**
 * Shared Utilities für den Prompt Editor.
 */
const Utils = {
    /**
     * Debounce – verzögert Ausführung bis keine Eingabe mehr kommt.
     */
    debounce(fn, delay) {
        let timer;
        return function (...args) {
            clearTimeout(timer);
            timer = setTimeout(() => fn.apply(this, args), delay);
        };
    },

    /**
     * HTML-Sonderzeichen escapen.
     */
    escapeHtml(text) {
        if (!text) return '';
        const el = document.createElement('div');
        el.textContent = String(text);
        return el.innerHTML;
    },

    /**
     * Kurzform für querySelector.
     */
    $(selector) {
        return document.querySelector(selector);
    },

    /**
     * Kurzform für querySelectorAll.
     */
    $$(selector) {
        return document.querySelectorAll(selector);
    },

    /**
     * PyWebView API-Aufruf mit Fehlerbehandlung.
     */
    async apiCall(method, ...args) {
        try {
            const result = await window.pywebview.api[method](...args);
            return result;
        } catch (e) {
            console.error(`API call '${method}' failed:`, e);
            return { status: 'error', message: e.toString() };
        }
    },

    /**
     * Toast-Benachrichtigung anzeigen.
     * @param {string} message
     * @param {'success'|'error'|'warning'|'info'} type
     * @param {number} duration  ms
     */
    showToast(message, type = 'info', duration = 3000) {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        container.appendChild(toast);

        requestAnimationFrame(() => {
            requestAnimationFrame(() => toast.classList.add('visible'));
        });

        setTimeout(() => {
            toast.classList.remove('visible');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    },

    /**
     * Placeholder in Text farbig hervorheben (HTML-Output).
     */
    highlightPlaceholders(text) {
        if (!text) return '';
        return Utils.escapeHtml(text).replace(
            /\{\{(\w+)\}\}/g,
            '<span class="placeholder-highlight">{{$1}}</span>'
        );
    },

    /**
     * Alle Placeholder-Keys aus Text extrahieren (unique).
     */
    extractPlaceholders(text) {
        if (!text) return [];
        const matches = text.matchAll(/\{\{(\w+)\}\}/g);
        return [...new Set([...matches].map(m => m[1]))];
    },

    /**
     * ID aus Name generieren (snake_case).
     */
    nameToId(name) {
        return name
            .toLowerCase()
            .replace(/[äöüß]/g, m => ({ä:'ae',ö:'oe',ü:'ue',ß:'ss'})[m] || m)
            .replace(/[^a-z0-9]+/g, '_')
            .replace(/^_|_$/g, '')
            .replace(/_+/g, '_');
    }
};
