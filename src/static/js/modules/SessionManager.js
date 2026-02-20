/**
 * SessionManager - Handles session creation, loading, deletion, and sidebar
 * Two-level navigation: Personas (Messenger-Kontakte) → Sessions (Chat-Verläufe)
 */
export class SessionManager {
    constructor(dom) {
        this.dom = dom;
        this.currentSessionId = window.currentSessionId || null;
        this.activePersonaId = window.activePersonaId || 'default';
        this.selectedPersonaId = null; // Aktuell in der Sidebar angezeigte Persona
        this.sidebarCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
        this.personas = [];
        this.personaSessions = {}; // Cache: persona_id -> sessions[]
        this.sidebarView = 'personas'; // 'personas' oder 'sessions'
        this.messageManager = null; // Wird von ChatApp gesetzt
    }

    async init() {
        // Sidebar startet immer eingeklappt
        this.sidebarCollapsed = true;
        this.dom.sidebar.classList.add('collapsed');
        localStorage.setItem('sidebarCollapsed', 'true');
        
        // Lade Personas und zeige immer zuerst die Persona-Liste
        await this.loadPersonas();
        this.showPersonasView();
    }

    toggleSidebar() {
        this.sidebarCollapsed = !this.sidebarCollapsed;
        
        if (this.sidebarCollapsed) {
            this.dom.sidebar.classList.add('collapsed');
        } else {
            this.dom.sidebar.classList.remove('collapsed');
        }
        
        localStorage.setItem('sidebarCollapsed', this.sidebarCollapsed);
    }

    openSidebar() {
        if (this.sidebarCollapsed) {
            this.sidebarCollapsed = false;
            this.dom.sidebar.classList.remove('collapsed');
            localStorage.setItem('sidebarCollapsed', 'false');
        }
    }

    closeSidebar() {
        if (!this.sidebarCollapsed) {
            this.sidebarCollapsed = true;
            this.dom.sidebar.classList.add('collapsed');
            localStorage.setItem('sidebarCollapsed', 'true');
        }
    }
    
    // ===== DATA LOADING =====
    
    async loadPersonas() {
        try {
            const [personasRes, summaryRes] = await Promise.all([
                fetch('/api/personas'),
                fetch('/api/sessions/persona_summary')
            ]);
            
            const personasData = await personasRes.json();
            const summaryData = await summaryRes.json();
            
            if (personasData.success) {
                this.personas = personasData.personas;
            }
            
            // Session-Counts und letzte Aktivität aus Summary mergen
            if (summaryData.success) {
                const summaryMap = {};
                summaryData.summary.forEach(s => {
                    summaryMap[s.persona_id] = {
                        session_count: s.session_count,
                        last_updated: s.last_updated
                    };
                });
                this.personas.forEach(p => {
                    const info = summaryMap[p.id] || {};
                    p.session_count = info.session_count || 0;
                    p.last_updated = info.last_updated || null;
                });
            }
            
            // Sortiere: Aktive Persona zuerst, dann nach letzter Aktivität
            this.personas.sort((a, b) => {
                if (a.id === this.activePersonaId) return -1;
                if (b.id === this.activePersonaId) return 1;
                const aTime = a.last_updated || '';
                const bTime = b.last_updated || '';
                return bTime.localeCompare(aTime);
            });
        } catch (error) {
            console.error('Fehler beim Laden der Personas:', error);
        }
    }
    
    async loadSessionsForPersona(personaId) {
        try {
            const response = await fetch(`/api/sessions?persona_id=${encodeURIComponent(personaId)}`);
            const data = await response.json();
            
            if (data.success) {
                this.personaSessions[personaId] = data.sessions;
                return data.sessions;
            }
            return [];
        } catch (error) {
            console.error('Fehler beim Laden der Sessions:', error);
            return [];
        }
    }
    
    // ===== HELPER: Datum/Uhrzeit formatieren =====
    
    formatDateTime(dateStr) {
        if (!dateStr) return '';
        try {
            // Erwartetes Format: "YYYY-MM-DD HH:MM:SS" oder ISO
            const date = new Date(dateStr.replace(' ', 'T'));
            if (isNaN(date.getTime())) return dateStr;
            
            const now = new Date();
            const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
            const yesterday = new Date(today);
            yesterday.setDate(yesterday.getDate() - 1);
            const dateOnly = new Date(date.getFullYear(), date.getMonth(), date.getDate());
            
            const timeStr = date.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
            
            if (dateOnly.getTime() === today.getTime()) {
                return timeStr;
            } else if (dateOnly.getTime() === yesterday.getTime()) {
                return 'Gestern';
            } else {
                return date.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: '2-digit' });
            }
        } catch (e) {
            return dateStr;
        }
    }
    
    formatFullDateTime(dateStr) {
        if (!dateStr) return '';
        try {
            const date = new Date(dateStr.replace(' ', 'T'));
            if (isNaN(date.getTime())) return dateStr;
            
            const dateFormatted = date.toLocaleDateString('de-DE', { 
                day: '2-digit', month: '2-digit', year: 'numeric' 
            });
            const timeFormatted = date.toLocaleTimeString('de-DE', { 
                hour: '2-digit', minute: '2-digit' 
            });
            
            return `${dateFormatted} · ${timeFormatted}`;
        } catch (e) {
            return dateStr;
        }
    }
    
    // ===== VIEW SWITCHING =====
    
    showPersonasView() {
        this.sidebarView = 'personas';
        this.selectedPersonaId = null;
        
        // Header anpassen
        this.dom.sidebarTitle.textContent = 'Chats';
        this.dom.sidebarBackBtn.classList.add('hidden');
        
        // Views umschalten
        this.dom.sidebarPersonaView.classList.remove('hidden');
        this.dom.sidebarSessionsView.classList.add('hidden');
        
        this.renderPersonaList();
    }
    
    async showSessionsView(personaId) {
        this.sidebarView = 'sessions';
        this.selectedPersonaId = personaId;
        
        // Persona-Name finden
        const persona = this.personas.find(p => p.id === personaId);
        const personaName = persona ? persona.name : 'Unbekannt';
        
        // Header anpassen
        this.dom.sidebarTitle.textContent = personaName;
        this.dom.sidebarBackBtn.classList.remove('hidden');
        
        // Views umschalten
        this.dom.sidebarPersonaView.classList.add('hidden');
        this.dom.sidebarSessionsView.classList.remove('hidden');
        
        // Sessions laden und rendern
        const sessions = await this.loadSessionsForPersona(personaId);
        this.renderSessionList(sessions);
    }
    
    goBackToPersonas() {
        this.showPersonasView();
    }
    
    /**
     * Öffnet die neueste Session einer Persona direkt.
     * Falls keine Sessions existieren, wird eine neue erstellt.
     */
    async openPersonaLatestSession(personaId) {
        try {
            // Sofort zur Sessions-View wechseln (zeigt Lade-Zustand)
            this.selectedPersonaId = personaId;
            this.sidebarView = 'sessions';
            
            // Persona-Name finden und Header sofort umschalten
            const persona = this.personas.find(p => p.id === personaId);
            const personaName = persona ? persona.name : 'Unbekannt';
            this.dom.sidebarTitle.textContent = personaName;
            this.dom.sidebarBackBtn.classList.remove('hidden');
            this.dom.sidebarPersonaView.classList.add('hidden');
            this.dom.sidebarSessionsView.classList.remove('hidden');
            
            // Lade-Hinweis anzeigen
            this.dom.sessionsList.innerHTML = '<div class="sessions-empty">Laden...</div>';
            
            const sessions = await this.loadSessionsForPersona(personaId);
            
            if (sessions.length > 0) {
                // Neueste Session laden (sessions sind nach updated_at DESC sortiert)
                await this.loadSession(sessions[0].id);
            } else {
                // Keine Sessions vorhanden → neue erstellen
                await this.createNewSession();
            }
            
            // Sessions-Liste aktualisieren (nach soft reload, da neue Session erstellt sein könnte)
            const updatedSessions = await this.loadSessionsForPersona(personaId);
            this.renderSessionList(updatedSessions);
        } catch (error) {
            console.error('Fehler beim Öffnen der Persona-Session:', error);
        }
    }
    
    // ===== RENDERING =====
    
    renderPersonaList() {
        const container = this.dom.sidebarPersonaList;
        container.innerHTML = '';
        
        this.personas.forEach(persona => {
            const item = document.createElement('div');
            item.className = 'sidebar-contact-item';
            if (persona.id === this.activePersonaId) {
                item.classList.add('active');
            }
            item.dataset.personaId = persona.id;
            
            // Avatar
            let avatarHTML = '';
            if (persona.avatar) {
                const imgPath = persona.avatar_type === 'custom'
                    ? `/static/images/custom/${persona.avatar}`
                    : `/static/images/avatars/${persona.avatar}`;
                avatarHTML = `<div class="contact-avatar" style="background-image: url('${imgPath}');"></div>`;
            } else {
                const initial = (persona.name || '?')[0].toUpperCase();
                avatarHTML = `<div class="contact-avatar contact-avatar-letter"><span>${initial}</span></div>`;
            }
            
            // Online-Indikator für aktive Persona
            const onlineIndicator = persona.id === this.activePersonaId
                ? '<span class="contact-online-dot"></span>'
                : '';
            
            // Letzte Aktivität
            const lastActivity = this.formatDateTime(persona.last_updated);
            const sessionCount = persona.session_count || 0;
            const subtitle = sessionCount > 0 
                ? `${sessionCount} ${sessionCount === 1 ? 'Chat' : 'Chats'}`
                : 'Kein Chat vorhanden';
            
            item.innerHTML = `
                <div class="contact-avatar-wrapper">
                    ${avatarHTML}
                    ${onlineIndicator}
                </div>
                <div class="contact-info">
                    <div class="contact-name-row">
                        <span class="contact-name">${persona.name || 'Unbenannt'}</span>
                        ${lastActivity ? `<span class="contact-time">${lastActivity}</span>` : ''}
                    </div>
                    <div class="contact-subtitle">${subtitle}</div>
                </div>
            `;
            
            item.addEventListener('click', () => {
                this.openPersonaLatestSession(persona.id);
            });
            
            container.appendChild(item);
        });
    }
    
    renderSessionList(sessions) {
        const container = this.dom.sessionsList;
        container.innerHTML = '';
        
        if (sessions.length === 0) {
            container.innerHTML = '<div class="sessions-empty">Noch keine Chats.<br>Starte einen neuen Chat!</div>';
            return;
        }
        
        sessions.forEach(session => {
            const item = document.createElement('div');
            item.className = 'session-item';
            if (session.id === this.currentSessionId) {
                item.classList.add('active');
            }
            item.dataset.sessionId = session.id;
            
            const dateStr = this.formatFullDateTime(session.updated_at || session.created_at);
            const createdStr = this.formatFullDateTime(session.created_at);
            
            item.innerHTML = `
                <div class="session-info">
                    <div class="session-date-primary">${dateStr}</div>
                    ${createdStr !== dateStr ? `<div class="session-date-created">Erstellt: ${createdStr}</div>` : ''}
                </div>
                <button class="session-delete" data-session-id="${session.id}" title="Chat löschen">×</button>
            `;
            
            container.appendChild(item);
        });
        
        this.updateDeleteButtonStates();
    }
    
    // ===== SESSION ACTIONS =====
    
    async createNewSession() {
        try {
            // Bestimme die persona_id für die neue Session
            const personaId = this.selectedPersonaId || this.activePersonaId;
            
            // Wenn die Session für eine andere Persona erstellt wird, aktiviere sie zuerst
            if (personaId !== this.activePersonaId) {
                await fetch(`/api/personas/${personaId}/activate`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
            }
            
            // Leere aktuelle Session automatisch löschen
            if (this.currentSessionId) {
                await this.checkAndDeleteEmptySession(this.currentSessionId);
            }
            
            const response = await fetch('/api/sessions/new', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ persona_id: personaId })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.applySoftReload(data.session_id, personaId, data);
            } else {
                alert('Fehler beim Erstellen einer neuen Session');
            }
        } catch (error) {
            console.error('Fehler beim Erstellen einer neuen Session:', error);
            alert('Verbindungsfehler');
        }
    }
    
    async loadSession(sessionId) {
        const personaId = this.selectedPersonaId || this.activePersonaId;
        if (sessionId === this.currentSessionId && personaId === this.activePersonaId) {
            return;
        }
        
        try {
            if (this.currentSessionId) {
                await this.checkAndDeleteEmptySession(this.currentSessionId);
            }
            
            // Persona aktivieren falls nötig
            if (personaId !== this.activePersonaId) {
                await fetch(`/api/personas/${personaId}/activate`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
            }
            
            // Session-Daten per API laden (Soft-Reload)
            const response = await fetch(`/api/sessions/${sessionId}?persona_id=${encodeURIComponent(personaId)}`);
            const data = await response.json();
            
            if (data.success) {
                this.applySoftReload(sessionId, data.persona_id || personaId, data);
            } else {
                console.error('Session nicht gefunden, Fallback auf Navigation');
                window.location.href = `/?session=${sessionId}&persona_id=${personaId}`;
            }
        } catch (error) {
            console.error('Fehler beim Laden der Session:', error);
            alert('Verbindungsfehler');
        }
    }
    
    /**
     * Soft-Reload: Aktualisiert Header, Chat-Bubbles und interne States
     * ohne die Seite komplett neu zu laden. Sidebar bleibt offen.
     */
    applySoftReload(sessionId, personaId, data) {
        // 1. Globale Variablen aktualisieren
        this.currentSessionId = sessionId;
        this.activePersonaId = personaId;
        window.currentSessionId = sessionId;
        window.activePersonaId = personaId;
        
        // 2. URL aktualisieren ohne Reload
        const newUrl = `/?session=${sessionId}&persona_id=${personaId}`;
        window.history.replaceState({}, '', newUrl);
        
        // 3. Header aktualisieren (Avatar + Name)
        if (data.character) {
            this.updateHeader(data.character);
            // window.characterAvatar aktualisieren für Chat-Bubble-Avatare
            window.characterAvatar = {
                image: data.character.avatar || null,
                type: data.character.avatar_type || 'standard'
            };
        }
        
        // 4. Chat-Nachrichten aktualisieren
        if (this.messageManager) {
            // Afterthought-Timer stoppen
            this.messageManager.stopAfterthoughtTimer();
            
            // Session-ID im MessageManager aktualisieren
            this.messageManager.currentSessionId = sessionId;
            this.messageManager.totalMessageCount = data.total_message_count || 0;
            this.messageManager.loadedMessageCount = 0;
            
            // Alte Nachrichten und Welcome-Screen entfernen
            const messages = this.dom.chatMessages.querySelectorAll('.message');
            messages.forEach(msg => msg.remove());
            const welcomeScreen = this.dom.chatMessages.querySelector('.welcome-container');
            if (welcomeScreen) welcomeScreen.remove();
            
            // Input-Feld aktivieren (war ggf. bei Welcome-Screen disabled)
            this.dom.messageInput.disabled = false;
            this.dom.messageInput.placeholder = 'Deine Nachricht...';
            const sendBtn = document.getElementById('send-button');
            if (sendBtn) sendBtn.disabled = false;
            
            // Chat-Historie rendern
            const chatHistory = data.chat_history || [];
            chatHistory.forEach(msg => {
                const msgDiv = this.messageManager.addMessage(
                    msg.message,
                    msg.is_user,
                    msg.character_name,
                    msg.timestamp
                );
                if (msg.memorized && msgDiv) {
                    const bubble = msgDiv.querySelector('.message-bubble');
                    if (bubble) bubble.classList.add('memorized');
                }
                if (msg.id && msgDiv) {
                    msgDiv.dataset.messageId = msg.id;
                }
            });
            
            // UI-Updates
            this.messageManager.updateLoadMoreButton();
            this.messageManager.updateNewChatButtonState();
            this.messageManager.scrollToBottom(true);
            this.messageManager.autoResize();
        }
        
        // 5. Loading-State zurücksetzen (damit sendMessage wieder funktioniert)
        if (this.messageManager) {
            this.messageManager.setLoading(false);
        }
        
        // 6. Persona-Liste in Sidebar aktualisieren (aktive Markierung)
        this.loadPersonas().then(() => {
            if (this.sidebarView === 'personas') {
                this.renderPersonaList();
            }
        });
        
        // 8. Sessions-Liste aktualisieren falls sichtbar
        if (this.sidebarView === 'sessions' && this.selectedPersonaId) {
            this.loadSessionsForPersona(this.selectedPersonaId).then(sessions => {
                this.renderSessionList(sessions);
            });
        }
        
        // 9. Input-Feld fokussieren
        setTimeout(() => {
            this.dom.messageInput.focus();
        }, 100);
    }
    
    /**
     * Aktualisiert den Header (Avatar + Charakter-Name)
     */
    updateHeader(character) {
        // Name aktualisieren
        const nameEl = document.querySelector('.character-name');
        if (nameEl) {
            nameEl.textContent = character.char_name || 'Assistant';
        }
        
        // Avatar aktualisieren
        const avatarEl = document.getElementById('character-avatar-display');
        if (avatarEl) {
            if (character.avatar) {
                const avatarPath = character.avatar_type === 'custom'
                    ? `/static/images/custom/${character.avatar}`
                    : `/static/images/avatars/${character.avatar}`;
                avatarEl.style.backgroundImage = `url('${avatarPath}')`;
                avatarEl.style.backgroundSize = 'cover';
                avatarEl.style.backgroundPosition = 'center';
                avatarEl.style.backgroundRepeat = 'no-repeat';
                // Placeholder-Text entfernen falls vorhanden
                const placeholder = avatarEl.querySelector('.avatar-placeholder');
                if (placeholder) placeholder.remove();
            } else {
                avatarEl.style.backgroundImage = '';
                // Placeholder-Buchstabe setzen
                let placeholder = avatarEl.querySelector('.avatar-placeholder');
                if (!placeholder) {
                    placeholder = document.createElement('span');
                    placeholder.className = 'avatar-placeholder';
                    avatarEl.appendChild(placeholder);
                }
                placeholder.textContent = (character.char_name || 'A')[0];
            }
        }
    }
    
    async checkAndDeleteEmptySession(sessionId) {
        try {
            // Aktuelle Session gehört immer zur aktiven Persona, nicht zur ausgewählten Sidebar-Persona
            const personaId = this.activePersonaId;
            const response = await fetch(`/api/sessions/${sessionId}/is_empty?persona_id=${encodeURIComponent(personaId)}`);
            const data = await response.json();
            
            if (data.success && data.is_empty) {
                await fetch(`/api/sessions/${sessionId}?persona_id=${encodeURIComponent(personaId)}`, {
                    method: 'DELETE',
                    headers: { 'Content-Type': 'application/json' }
                });
            }
        } catch (error) {
            console.error('Fehler beim Prüfen/Löschen der leeren Session:', error);
        }
    }
    
    async deleteSession(sessionId) {
        if (!confirm('Möchtest du diesen Chat wirklich löschen?')) {
            return;
        }
        
        try {
            const personaForDelete = this.selectedPersonaId || this.activePersonaId;
            const response = await fetch(`/api/sessions/${sessionId}?persona_id=${encodeURIComponent(personaForDelete)}`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' }
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Update Session-Count im Cache
                if (this.selectedPersonaId && this.personaSessions[this.selectedPersonaId]) {
                    this.personaSessions[this.selectedPersonaId] = 
                        this.personaSessions[this.selectedPersonaId].filter(s => s.id !== sessionId);
                }
                
                if (sessionId === this.currentSessionId) {
                    // Aktive Session gelöscht → nächste Session laden oder neue erstellen
                    const remainingSessions = await this.loadSessionsForPersona(personaForDelete);
                    if (remainingSessions.length > 0) {
                        await this.loadSession(remainingSessions[0].id);
                    } else {
                        await this.createNewSession();
                    }
                    // Sessions-Liste aktualisieren
                    if (this.sidebarView === 'sessions') {
                        this.renderSessionList(remainingSessions.length > 0 ? remainingSessions : await this.loadSessionsForPersona(personaForDelete));
                    }
                } else {
                    const sessionItem = this.dom.sessionsList.querySelector(`[data-session-id="${sessionId}"]`);
                    if (sessionItem) {
                        sessionItem.remove();
                    }
                    
                    // Wenn keine Sessions mehr, zeige leere Nachricht
                    const remaining = this.dom.sessionsList.querySelectorAll('.session-item');
                    if (remaining.length === 0) {
                        this.dom.sessionsList.innerHTML = '<div class="sessions-empty">Noch keine Chats.<br>Starte einen neuen Chat!</div>';
                    }
                    
                    this.updateDeleteButtonStates();
                }
            } else {
                alert('Fehler beim Löschen des Chats');
            }
        } catch (error) {
            console.error('Fehler beim Löschen der Session:', error);
            alert('Verbindungsfehler');
        }
    }

    updateDeleteButtonStates() {
        const deleteButtons = this.dom.sessionsList.querySelectorAll('.session-delete');
        deleteButtons.forEach(btn => {
            btn.disabled = false;
            btn.style.opacity = '1';
            btn.style.cursor = 'pointer';
        });
    }
}
