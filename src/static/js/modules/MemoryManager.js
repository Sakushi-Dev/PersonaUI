/**
 * MemoryManager - Verwaltet die Memory-Funktionalität
 */
import { UserSettings } from './UserSettings.js';

export class MemoryManager {
    constructor() {
        this.memoryBtn = document.getElementById('memory-btn');
        this.memorySettingsBtn = document.getElementById('memory-settings-btn');
        this.memoryOverlay = document.getElementById('memory-overlay');
        this.closeMemoryOverlay = document.getElementById('close-memory-overlay');
        this.memoriesEnabledToggle = document.getElementById('memories-enabled-toggle');
        this.memoriesList = document.getElementById('memories-list');
        
        // Memory Creation Overlay
        this.memoryCreationOverlay = document.getElementById('memory-creation-overlay');
        this.memoryLoadingState = document.getElementById('memory-loading-state');
        this.memoryPreviewState = document.getElementById('memory-preview-state');
        this.memoryPreviewText = document.getElementById('memory-preview-text');
        this.memorySaveBtn = document.getElementById('memory-save-btn');
        this.memoryRetryBtn = document.getElementById('memory-retry-btn');
        this.memoryCancelBtn = document.getElementById('memory-cancel-btn');
        this.closeMemoryCreation = document.getElementById('close-memory-creation');
        
        this.messageCount = 0;
        this.userMessagesSinceMarker = 0;
        this.isCreatingMemory = false;
        this.currentMemoryContent = null;
        this.contextLimitWarning = false;
        this.contextLimitCritical = false;
        this.memoryContextTruncated = false;
        this.memoryContextTotal = 0;
        
        this.init();
    }
    
    init() {
        // Event Listener für Memory-Button
        if (this.memoryBtn) {
            this.memoryBtn.addEventListener('click', () => this.createMemory());
        }
        
        // Event Listener für Memory Settings Button
        if (this.memorySettingsBtn) {
            this.memorySettingsBtn.addEventListener('click', () => this.openMemorySettings());
        }
        
        // Event Listener für Overlay schließen
        if (this.closeMemoryOverlay) {
            this.closeMemoryOverlay.addEventListener('click', () => this.closeSettings());
        }
        
        // Event Listener für Memories Toggle
        if (this.memoriesEnabledToggle) {
            this.memoriesEnabledToggle.addEventListener('change', () => this.toggleMemoriesEnabled());
        }
        
        // Event Listener für Memory Creation Overlay
        if (this.memorySaveBtn) {
            this.memorySaveBtn.addEventListener('click', () => this.saveMemory());
        }
        
        if (this.memoryRetryBtn) {
            this.memoryRetryBtn.addEventListener('click', () => this.retryMemoryCreation());
        }
        
        if (this.memoryCancelBtn) {
            this.memoryCancelBtn.addEventListener('click', () => this.closeMemoryCreationOverlay());
        }
        
        if (this.closeMemoryCreation) {
            this.closeMemoryCreation.addEventListener('click', () => this.closeMemoryCreationOverlay());
        }
        
        // Lade initiale Memory-Verfügbarkeit
        this.checkMemoryAvailability();
        
        // Lade gespeicherte Einstellungen
        this.loadSettings();
    }
    
    /**
     * Prüft ob der Memory-Button aktiviert werden soll
     */
    async checkMemoryAvailability() {
        if (!window.currentSessionId) return;
        
        try {
            const contextLimit = UserSettings.get('contextLimit', UserSettings.getDefault('contextLimit', 25));
            const response = await fetch(`/api/memory/check-availability/${window.currentSessionId}?persona_id=${encodeURIComponent(window.activePersonaId || 'default')}&context_limit=${contextLimit}`);
            const data = await response.json();
            
            if (data.success) {
                this.messageCount = data.message_count || 0;
                this.userMessagesSinceMarker = data.user_messages_since_marker || 0;
                this.contextLimitWarning = data.context_limit_warning || false;
                this.contextLimitCritical = data.context_limit_critical || false;
                this.memoryContextTruncated = data.memory_context_truncated || false;
                this.memoryContextTotal = data.memory_context_total || 0;
                
                if (data.available) {
                    this.enableMemoryButton();
                } else {
                    this.disableMemoryButton();
                }
                
                // Kontext-Limit-Highlighting
                this.updateContextLimitHighlight();
                
                // Truncation-Hinweis beim Availability-Check (einmalig pro Schwellwertüberschreitung)
                if (this.memoryContextTruncated && !this._truncationNotified) {
                    this._truncationNotified = true;
                    this.showNotification(
                        `Erinnerungs-Kontext auf 100 von ${this.memoryContextTotal} Nachrichten begrenzt – Erinnerung empfohlen`,
                        'warning'
                    );
                } else if (!this.memoryContextTruncated) {
                    this._truncationNotified = false;
                }
            } else {
                this.disableMemoryButton();
            }
        } catch (error) {
            console.error('Fehler beim Prüfen der Memory-Verfügbarkeit:', error);
        }
    }
    
    /**
     * Aktiviert den Memory-Button
     */
    enableMemoryButton() {
        if (this.memoryBtn) {
            this.memoryBtn.classList.remove('disabled');
            this.memoryBtn.title = 'Erinnerung erstellen';
        }
    }
    
    /**
     * Deaktiviert den Memory-Button
     */
    disableMemoryButton() {
        if (this.memoryBtn) {
            this.memoryBtn.classList.add('disabled');
            this.memoryBtn.classList.remove('context-warning', 'context-critical');
            const remaining = Math.max(0, 10 - this.userMessagesSinceMarker);
            this.memoryBtn.title = `Erinnerung erstellen (noch ${remaining} Nachrichten erforderlich)`;
        }
    }
    
    /**
     * Aktualisiert das visuelle Highlighting bei Kontext-Limit-Nähe
     * Nur wenn der Button verfügbar (nicht disabled) ist
     */
    updateContextLimitHighlight() {
        if (!this.memoryBtn) return;
        
        // Entferne vorherige Klassen
        this.memoryBtn.classList.remove('context-warning', 'context-critical');
        
        // Kein Highlighting wenn Button disabled ist
        if (this.memoryBtn.classList.contains('disabled')) return;
        
        if (this.contextLimitCritical) {
            this.memoryBtn.classList.add('context-critical');
            this.memoryBtn.title = 'Erinnerung dringend empfohlen – Kontextlimit fast erreicht!';
        } else if (this.contextLimitWarning) {
            this.memoryBtn.classList.add('context-warning');
            this.memoryBtn.title = 'Erinnerung empfohlen – Kontextlimit wird bald erreicht';
        }
    }
    
    /**
     * Wird nach jeder gesendeten Nachricht aufgerufen
     */
    onMessageSent() {
        this.messageCount++;
        this.checkMemoryAvailability();
    }
    
    /**
     * Erstellt eine neue Memory aus der aktuellen Session
     */
    async createMemory() {
        if (this.memoryBtn.classList.contains('disabled') || this.isCreatingMemory) {
            return;
        }
        
        if (!window.currentSessionId) {
            this.showNotification('Keine aktive Session gefunden', 'error');
            return;
        }
        
        this.isCreatingMemory = true;
        this.memoryBtn.classList.add('creating');
        
        // Zeige Overlay mit Ladeanimation
        this.showLoadingState();
        
        try {
            // Rufe Preview-API auf (generiert nur, speichert NICHT)
            const response = await fetch('/api/memory/preview', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: window.currentSessionId
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Speichere Content und zeige Vorschau (NICHT gespeichert!)
                this.currentMemoryContent = data.content || '';
                this.showPreviewState();
            } else {
                this.closeMemoryCreationOverlay();
                this.showNotification(data.error || 'Fehler beim Erstellen der Erinnerung', 'error');
                this.memoryBtn.textContent = 'Erinnern';
            }
        } catch (error) {
            console.error('Fehler beim Erstellen der Memory-Vorschau:', error);
            this.closeMemoryCreationOverlay();
            this.showNotification('Fehler beim Erstellen der Erinnerung', 'error');
            this.memoryBtn.textContent = 'Erinnern';
        } finally {
            this.isCreatingMemory = false;
            this.memoryBtn.classList.remove('creating');
        }
    }
    
    /**
     * Zeigt die Ladeanimation
     */
    showLoadingState() {
        if (this.memoryCreationOverlay) {
            this.memoryCreationOverlay.classList.remove('hidden');
        }
        if (this.memoryLoadingState) {
            this.memoryLoadingState.classList.remove('hidden');
        }
        if (this.memoryPreviewState) {
            this.memoryPreviewState.classList.add('hidden');
        }
    }
    
    /**
     * Zeigt die Vorschau mit editierbarem Content
     */
    showPreviewState() {
        if (this.memoryLoadingState) {
            this.memoryLoadingState.classList.add('hidden');
        }
        if (this.memoryPreviewState) {
            this.memoryPreviewState.classList.remove('hidden');
        }
        if (this.memoryPreviewText) {
            this.memoryPreviewText.value = this.currentMemoryContent;
            // Auto-resize textarea
            this.memoryPreviewText.style.height = 'auto';
            this.memoryPreviewText.style.height = Math.min(this.memoryPreviewText.scrollHeight, 400) + 'px';
        }
    }
    
    /**
     * Speichert die bearbeitete Memory
     */
    async saveMemory() {
        const editedContent = this.memoryPreviewText?.value?.trim();
        
        if (!editedContent) {
            this.showNotification('Erinnerung darf nicht leer sein', 'error');
            return;
        }
        
        this.currentMemoryContent = editedContent;
        
        try {
            // Jetzt erst speichern mit dem finalen Content (editiert oder original)
            const response = await fetch('/api/memory/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: window.currentSessionId,
                    content: editedContent  // Übergebe den finalen (editierten) Content
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Erinnerung erfolgreich gespeichert', 'success');
                this.closeMemoryCreationOverlay();
                this.memoryBtn.textContent = '✓ Gespeichert';
                
                // Hinweis wenn Kontext gekürzt wurde
                if (data.context_truncated) {
                    setTimeout(() => {
                        this.showNotification(
                            `Erinnerung basiert auf 100 von ${data.context_total_available || '?'} Nachrichten`,
                            'info'
                        );
                    }, 1500);
                }
                
                // Soft-Reload: Alle bisherigen Bubbles als "memorized" markieren
                const lastMarker = data.last_memory_message_id;
                if (lastMarker) {
                    window.lastMemoryMessageId = lastMarker;
                }
                
                // DOM komplett neu rendern damit memorized-Bubbles korrekt angezeigt werden
                if (window.messageManager) {
                    await window.messageManager.refreshSession();
                }
                
                // Memory-Verfügbarkeit neu prüfen (Marker wurde gesetzt)
                this.checkMemoryAvailability();
                
                // Nach 2 Sekunden zurück zum normalen Text
                setTimeout(() => {
                    this.memoryBtn.textContent = 'Erinnern';
                }, 2000);
            } else {
                this.showNotification(data.error || 'Fehler beim Speichern der Erinnerung', 'error');
            }
        } catch (error) {
            console.error('Fehler beim Speichern der Memory:', error);
            this.showNotification('Fehler beim Speichern der Erinnerung', 'error');
        }
    }
    
    /**
     * Wiederholt die Memory-Erstellung
     */
    async retryMemoryCreation() {
        this.closeMemoryCreationOverlay();
        // Kurze Verzögerung für besseres UX
        setTimeout(() => {
            this.createMemory();
        }, 300);
    }
    
    /**
     * Schließt das Memory Creation Overlay
     */
    closeMemoryCreationOverlay() {
        if (this.memoryCreationOverlay) {
            this.memoryCreationOverlay.classList.add('hidden');
        }
        this.currentMemoryContent = null;
    }
    
    /**
     * Öffnet die Memory-Einstellungen
     */
    async openMemorySettings() {
        if (this.memoryOverlay) {
            this.memoryOverlay.classList.remove('hidden');
            await this.loadMemories();
            await this.updateMemoryCounter();
        }
    }
    
    /**
     * Schließt die Memory-Einstellungen
     */
    closeSettings() {
        if (this.memoryOverlay) {
            this.memoryOverlay.classList.add('hidden');
        }
    }
    
    /**
     * Aktualisiert den Memory-Zähler
     */
    async updateMemoryCounter() {
        try {
            const personaId = window.activePersonaId || 'default';
            const response = await fetch(`/api/memory/stats?persona_id=${encodeURIComponent(personaId)}`);
            const data = await response.json();
            
            if (data.success) {
                const counter = document.getElementById('memory-counter');
                if (counter) {
                    counter.textContent = `${data.active_count}/${data.limit}`;
                }
            }
        } catch (error) {
            console.error('Fehler beim Laden der Memory-Stats:', error);
        }
    }
    
    /**
     * Lädt alle Memories
     */
    async loadMemories() {
        try {
            const personaId = window.activePersonaId || 'default';
            const response = await fetch(`/api/memory/list?persona_id=${encodeURIComponent(personaId)}`);
            const data = await response.json();
            
            if (data.success) {
                this.renderMemories(data.memories);
                await this.updateMemoryCounter();
            } else {
                console.error('Fehler beim Laden der Memories:', data.error);
            }
        } catch (error) {
            console.error('Fehler beim Laden der Memories:', error);
        }
    }
    
    /**
     * Rendert die Memories-Liste
     */
    renderMemories(memories) {
        if (!this.memoriesList) return;
        
        if (!memories || memories.length === 0) {
            this.memoriesList.innerHTML = `
                <div class="no-memories">
                    Noch keine Erinnerungen vorhanden. Erstelle eine Erinnerung nach mindestens 10 User-Nachrichten.
                </div>
            `;
            return;
        }
        
        // Sortiere nach Datum (neueste zuerst)
        memories.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        
        this.memoriesList.innerHTML = memories.map(memory => this.renderMemoryItem(memory)).join('');
        
        // Event Listener für Aktionen
        this.attachMemoryEventListeners();
    }
    
    /**
     * Rendert ein einzelnes Memory-Item
     */
    renderMemoryItem(memory) {
        const date = new Date(memory.created_at);
        const formattedDate = date.toLocaleString('de-DE', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
        
        // Extrahiere Datum aus Content falls vorhanden
        const contentLines = memory.content.split('\n');
        const displayContent = contentLines.slice(1).join('\n').trim() || memory.content;
        
        return `
            <div class="memory-item ${memory.is_active ? 'active' : 'inactive'}" data-memory-id="${memory.id}">
                <div class="memory-header">
                    <span class="memory-date">${formattedDate}</span>
                    <div class="memory-actions">
                        <label class="switch memory-toggle">
                            <input type="checkbox" ${memory.is_active ? 'checked' : ''} data-memory-id="${memory.id}">
                            <span class="slider"></span>
                        </label>
                        <button class="memory-edit-btn" data-memory-id="${memory.id}" title="Bearbeiten">✏️</button>
                        <button class="memory-delete-btn" data-memory-id="${memory.id}" title="Löschen">❌</button>
                    </div>
                </div>
                <div class="memory-content">${this.escapeHtml(displayContent)}</div>
            </div>
        `;
    }
    
    /**
     * Fügt Event Listener für Memory-Aktionen hinzu
     */
    attachMemoryEventListeners() {
        // Toggle Event Listener
        document.querySelectorAll('.memory-toggle input').forEach(toggle => {
            toggle.addEventListener('change', (e) => {
                const memoryId = e.target.dataset.memoryId;
                this.toggleMemory(memoryId);
            });
        });
        
        // Edit Event Listener
        document.querySelectorAll('.memory-edit-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const memoryId = e.target.dataset.memoryId;
                this.editMemory(memoryId);
            });
        });
        
        // Delete Event Listener
        document.querySelectorAll('.memory-delete-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const memoryId = e.target.dataset.memoryId;
                this.deleteMemory(memoryId);
            });
        });
    }
    
    /**
     * Schaltet den Aktiv-Status einer Memory um
     */
    async toggleMemory(memoryId) {
        try {
            const response = await fetch(`/api/memory/${memoryId}/toggle`, {
                method: 'PATCH'
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Aktualisiere UI
                const memoryItem = document.querySelector(`.memory-item[data-memory-id="${memoryId}"]`);
                if (memoryItem) {
                    memoryItem.classList.toggle('active');
                    memoryItem.classList.toggle('inactive');
                }
                
                // DOM neu rendern: memorized-Markierungen aktualisieren
                if (window.messageManager) {
                    await window.messageManager.refreshSession();
                }
            } else {
                console.error('Fehler beim Umschalten der Memory:', data.error);
                this.showNotification('Fehler beim Umschalten der Erinnerung', 'error');
            }
        } catch (error) {
            console.error('Fehler beim Umschalten der Memory:', error);
            this.showNotification('Fehler beim Umschalten der Erinnerung', 'error');
        }
    }
    
    /**
     * Bearbeitet eine Memory
     */
    editMemory(memoryId) {
        const memoryItem = document.querySelector(`.memory-item[data-memory-id="${memoryId}"]`);
        if (!memoryItem) return;
        
        const contentDiv = memoryItem.querySelector('.memory-content');
        const currentContent = contentDiv.textContent.trim();
        
        // Prüfe ob bereits im Bearbeitungsmodus
        if (contentDiv.querySelector('.memory-edit-textarea')) {
            return; // Bereits im Bearbeitungsmodus, ignoriere Klick
        }
        
        // Deaktiviere Edit-Button während Bearbeitung
        const editBtn = memoryItem.querySelector('.memory-edit-btn');
        if (editBtn) {
            editBtn.style.opacity = '0.3';
            editBtn.style.cursor = 'not-allowed';
            editBtn.style.pointerEvents = 'none';
        }
        
        // Erstelle Textarea für Bearbeitung
        const textarea = document.createElement('textarea');
        textarea.className = 'memory-edit-textarea';
        textarea.value = currentContent;
        
        // Erstelle Buttons
        const btnContainer = document.createElement('div');
        btnContainer.className = 'memory-edit-buttons';
        btnContainer.innerHTML = `
            <button class="btn btn-sm btn-primary memory-save-btn">Speichern</button>
            <button class="btn btn-sm btn-secondary memory-cancel-btn">Abbrechen</button>
        `;
        
        // Ersetze Content mit Textarea
        contentDiv.innerHTML = '';
        contentDiv.appendChild(textarea);
        contentDiv.appendChild(btnContainer);
        
        // Event Listener für Buttons
        btnContainer.querySelector('.memory-save-btn').addEventListener('click', () => {
            this.saveMemoryEdit(memoryId, textarea.value);
        });
        
        btnContainer.querySelector('.memory-cancel-btn').addEventListener('click', () => {
            contentDiv.textContent = currentContent;
            // Aktiviere Edit-Button wieder
            if (editBtn) {
                editBtn.style.opacity = '';
                editBtn.style.cursor = '';
                editBtn.style.pointerEvents = '';
            }
        });
        
        textarea.focus();
    }
    
    /**
     * Speichert die bearbeitete Memory
     */
    async saveMemoryEdit(memoryId, newContent) {
        try {
            const response = await fetch(`/api/memory/${memoryId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    content: newContent
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Erinnerung erfolgreich aktualisiert', 'success');
                await this.loadMemories(); // Neu laden
            } else {
                this.showNotification(data.error || 'Fehler beim Aktualisieren der Erinnerung', 'error');
            }
        } catch (error) {
            console.error('Fehler beim Speichern der Memory:', error);
            this.showNotification('Fehler beim Aktualisieren der Erinnerung', 'error');
        }
    }
    
    /**
     * Löscht eine Memory
     */
    async deleteMemory(memoryId) {
        if (!confirm('Möchtest du diese Erinnerung wirklich löschen?')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/memory/${memoryId}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Erinnerung erfolgreich gelöscht', 'success');
                await this.loadMemories(); // Memory-Liste neu laden
                
                // DOM neu rendern: memorized-Markierungen aktualisieren
                if (window.messageManager) {
                    await window.messageManager.refreshSession();
                }
                
                // Memory-Verfügbarkeit neu prüfen
                this.checkMemoryAvailability();
            } else {
                this.showNotification(data.error || 'Fehler beim Löschen der Erinnerung', 'error');
            }
        } catch (error) {
            console.error('Fehler beim Löschen der Memory:', error);
            this.showNotification('Fehler beim Löschen der Erinnerung', 'error');
        }
    }
    
    /**
     * Schaltet die Memories-Funktion global ein/aus
     */
    toggleMemoriesEnabled() {
        const isEnabled = this.memoriesEnabledToggle.checked;
        UserSettings.set('memoriesEnabled', isEnabled);
        
        // TODO: Diese Einstellung kann später für das Ausblenden von Memories im Prompt verwendet werden
        console.log('Memories enabled:', isEnabled);
    }
    
    /**
     * Lädt gespeicherte Einstellungen
     */
    loadSettings() {
        const isEnabled = UserSettings.get('memoriesEnabled', UserSettings.getDefault('memoriesEnabled', true));
        if (isEnabled !== null) {
            this.memoriesEnabledToggle.checked = isEnabled;
        }
    }
    
    /**
     * Zeigt eine Benachrichtigung
     */
    showNotification(message, type = 'info') {
        // Verwende bestehende Notification-Funktion falls vorhanden
        if (window.showNotification) {
            window.showNotification(message, type);
        } else {
            alert(message);
        }
    }
    
    /**
     * Escaped HTML für sichere Anzeige
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    /**
     * Wird aufgerufen wenn eine neue Session geladen wird
     */
    onSessionChange() {
        this.messageCount = 0;
        this.userMessagesSinceMarker = 0;
        this.contextLimitWarning = false;
        this.contextLimitCritical = false;
        this.memoryContextTruncated = false;
        this._truncationNotified = false;
        this.checkMemoryAvailability();
    }
    
    /**
     * Markiert alle Chat-Bubbles bis zum Memory-Marker als "memorized"
     * (Soft-Reload ohne Page-Refresh)
     */
    markMemorizedBubbles(lastMemoryMessageId) {
        if (!lastMemoryMessageId) return;
        
        const allMessages = document.querySelectorAll('.message[data-message-id]');
        allMessages.forEach(msgDiv => {
            const msgId = parseInt(msgDiv.dataset.messageId, 10);
            const bubble = msgDiv.querySelector('.message-bubble');
            if (bubble && msgId && msgId <= lastMemoryMessageId) {
                bubble.classList.add('memorized');
            }
        });
    }
}
