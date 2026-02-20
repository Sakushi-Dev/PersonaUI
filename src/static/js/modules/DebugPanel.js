/**
 * DebugPanel - Developer testing panel for UI states
 */
import { UserSettings } from './UserSettings.js';

export class DebugPanel {
    constructor() {
        this.overlay = document.getElementById('debug-overlay');
        this.closeBtn = document.getElementById('close-debug-overlay');
        this.openBtn = document.getElementById('debug-panel-btn');
        
        this.init();
    }
    
    init() {
        // Open / Close
        if (this.openBtn) {
            this.openBtn.addEventListener('click', () => this.open());
        }
        if (this.closeBtn) {
            this.closeBtn.addEventListener('click', () => this.close());
        }
        
        // === Toast Notification Buttons ===
        this._btn('debug-toast-info', () => {
            window.showNotification('Dies ist eine Info-Benachrichtigung', 'info');
        });
        this._btn('debug-toast-success', () => {
            window.showNotification('Erinnerung erfolgreich gespeichert', 'success');
        });
        this._btn('debug-toast-warning', () => {
            window.showNotification('Erinnerung empfohlen – Kontextlimit wird bald erreicht', 'warning');
        });
        this._btn('debug-toast-error', () => {
            window.showNotification('Fehler beim Speichern der Erinnerung', 'error');
        });
        this._btn('debug-toast-truncation', () => {
            window.showNotification('Erinnerungs-Kontext auf 100 von 247 Nachrichten begrenzt – Erinnerung empfohlen', 'warning');
        });
        
        // === Bubble Highlighting Buttons ===
        this._btn('debug-bubble-memorize-all', () => {
            document.querySelectorAll('.message .message-bubble').forEach(b => b.classList.add('memorized'));
        });
        
        this._btn('debug-bubble-clear-all', () => {
            document.querySelectorAll('.message .message-bubble.memorized').forEach(b => b.classList.remove('memorized'));
        });
        
        this._btn('debug-bubble-memorize-half', () => {
            const msgs = document.querySelectorAll('.message .message-bubble');
            const half = Math.ceil(msgs.length / 2);
            msgs.forEach((b, i) => {
                if (i < half) b.classList.add('memorized');
                else b.classList.remove('memorized');
            });
        });
        
        // === Page Tools ===
        this._btn('debug-page-reload', () => {
            // PyWebView-kompatibel: location.reload() funktioniert in beiden Kontexten
            window.location.reload();
        });

        // === Refresh Info ===
        this._btn('debug-refresh-info', () => this.refreshSessionInfo());
    }
    
    /**
     * Helper: Bind click handler to button by ID
     */
    _btn(id, handler) {
        const el = document.getElementById(id);
        if (el) el.addEventListener('click', handler);
    }
    
    open() {
        if (this.overlay) {
            this.overlay.classList.remove('hidden');
            this.refreshSessionInfo();
        }
    }
    
    close() {
        if (this.overlay) {
            this.overlay.classList.add('hidden');
        }
    }
    
    /**
     * Fetches and displays current session/debug info
     */
    async refreshSessionInfo() {
        // Static values
        this._setVal('debug-val-session', window.currentSessionId || '–');
        this._setVal('debug-val-persona', window.activePersonaId || 'default');
        
        // Fetch from API
        if (!window.currentSessionId) return;
        
        try {
            const response = await fetch(`/api/sessions/${window.currentSessionId}`);
            const data = await response.json();
            if (data.success) {
                this._setVal('debug-val-total-msgs', data.message_count || '–');
            }
        } catch (e) {
            console.error('Debug: Fehler beim Laden der Session-Info', e);
        }
    }
    
    _setVal(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = String(value);
    }
}
