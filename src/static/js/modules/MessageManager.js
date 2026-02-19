/**
 * MessageManager - Handles message sending, formatting, and display
 */
import { UserSettings } from './UserSettings.js';

export class MessageManager {
    constructor(dom) {
        this.dom = dom;
        this.isLoading = false;
        this.currentSessionId = window.currentSessionId || null;
        this.messageSentCallback = null;
        this.loadedMessageCount = 0; // Wird in updateLoadMoreButton() korrekt gesetzt
        this.totalMessageCount = window.totalMessageCount || 0; // Gesamtzahl der Nachrichten
        this.isLoadingMore = false;
        
        // === Nachgedanke (Afterthought) System ===
        this.afterthoughtTimer = null;
        this.afterthoughtStage = 0; // 0=10s, 1=1min, 2=5min, 3=15min, 4=1h, 5=stop
        this.afterthoughtIntervals = [10000, 60000, 300000, 900000, 3600000]; // 10s, 1min, 5min, 15min, 1h
        this.afterthoughtElapsedLabels = ['10 Sekunden', '1 Minute', '5 Minuten', '15 Minuten', '1 Stunde'];
        this.afterthoughtActive = false;
        this.afterthoughtStreaming = false; // true while afterthought response is streaming
        this.lastResponseTime = null; // Timestamp der letzten Antwort
        
        // === Notification Sound ===
        this.notificationSoundEnabled = UserSettings.get('notificationSound', UserSettings.getDefault('notificationSound', true));
        this._audioContext = null;
        
        console.log('MessageManager initialized:', {
            sessionId: this.currentSessionId,
            totalMessageCount: this.totalMessageCount
        });
        
        // Erstelle "Ältere laden" Button
        this.createLoadMoreButton();
        
        // Setup Scroll-Listener für Load-More-Button
        this.setupScrollListener();

        // Persona-Name Sync (Header -> Bubble Sender)
        this._personaNameObserver = null;
        this._lastPersonaName = null;
    }

    /**
     * Spielt einen angenehmen Benachrichtigungston ab (wie eine Handy-Nachricht)
     */
    playNotificationSound() {
        if (!this.notificationSoundEnabled) return;
        
        try {
            if (!this._audioContext) {
                this._audioContext = new (window.AudioContext || window.webkitAudioContext)();
            }
            const ctx = this._audioContext;
            const now = ctx.currentTime;
            
            // Angenehmer "Blop"-Sound: zwei kurze Töne
            const playTone = (freq, startTime, duration, volume) => {
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.connect(gain);
                gain.connect(ctx.destination);
                
                osc.type = 'sine';
                osc.frequency.setValueAtTime(freq, startTime);
                osc.frequency.exponentialRampToValueAtTime(freq * 1.2, startTime + duration * 0.3);
                
                gain.gain.setValueAtTime(0, startTime);
                gain.gain.linearRampToValueAtTime(volume, startTime + 0.01);
                gain.gain.exponentialRampToValueAtTime(0.001, startTime + duration);
                
                osc.start(startTime);
                osc.stop(startTime + duration);
            };
            
            // Zwei aufsteigende Töne für einen freundlichen "blop blop"
            playTone(587, now, 0.12, 0.15);        // D5
            playTone(784, now + 0.1, 0.15, 0.12);  // G5
            
        } catch (e) {
            console.warn('Notification sound failed:', e);
        }
    }
    
    /**
     * Setzt den Benachrichtigungston an/aus
     */
    setNotificationSound(enabled) {
        this.notificationSoundEnabled = enabled;
        UserSettings.set('notificationSound', enabled);
    }

    getCurrentPersonaName() {
        const nameEl = document.querySelector('.character-name');
        const name = nameEl ? nameEl.textContent.trim() : '';
        return name || null;
    }

    syncBotSenderNames(characterName = null) {
        const effectiveName = characterName || this.getCurrentPersonaName();
        if (!effectiveName) return;

        const root = this.dom?.chatMessages || document;
        const senderDivs = root.querySelectorAll('.message.bot-message .message-sender');
        senderDivs.forEach(senderDiv => {
            senderDiv.textContent = effectiveName;
        });
    }

    observePersonaNameChanges() {
        if (this._personaNameObserver) return;

        const nameEl = document.querySelector('.character-name');
        if (!nameEl) return;

        this._lastPersonaName = nameEl.textContent.trim();
        this.syncBotSenderNames(this._lastPersonaName);

        this._personaNameObserver = new MutationObserver(() => {
            const newName = nameEl.textContent.trim();
            if (!newName || newName === this._lastPersonaName) return;
            this._lastPersonaName = newName;
            this.syncBotSenderNames(newName);
        });

        this._personaNameObserver.observe(nameEl, {
            characterData: true,
            childList: true,
            subtree: true
        });
    }

    async refreshSession() {
        // Stoppe Nachgedanke-Timer bei Session-Refresh
        this.stopAfterthoughtTimer();
        
        try {
            // Hole aktualisierte Session-Daten vom Backend
            const response = await fetch(`/api/sessions/${this.currentSessionId}?persona_id=${encodeURIComponent(window.activePersonaId || 'default')}`);
            const data = await response.json();
            
            if (data.success) {
                // Aktualisiere interne Variablen
                this.totalMessageCount = data.total_message_count || 0;
                
                // Lösche alle Nachrichten aus dem DOM
                const messages = this.dom.chatMessages.querySelectorAll('.message');
                messages.forEach(msg => msg.remove());
                
                // Lade Chat-Historie neu und zeige sie an
                const chatHistory = data.chat_history || [];
                chatHistory.forEach(msg => {
                    const msgDiv = this.addMessage(
                        msg.message,
                        msg.is_user,
                        msg.character_name,
                        msg.timestamp
                    );
                    
                    // Memorized-Status aus dem Backend übernehmen
                    if (msg.memorized && msgDiv) {
                        const bubble = msgDiv.querySelector('.message-bubble');
                        if (bubble) bubble.classList.add('memorized');
                    }
                    
                    // Message-ID für spätere Referenz setzen
                    if (msg.id && msgDiv) {
                        msgDiv.dataset.messageId = msg.id;
                    }
                });
                
                // Aktualisiere Load-More-Button
                this.updateLoadMoreButton();
                
                // Rufe Callbacks auf für Button-Updates
                if (this.messageSentCallback) {
                    this.messageSentCallback();
                }
                
                // Scrolle nach unten
                this.scrollToBottom();
                
                // Setze Loading-Status zurück
                this.setLoading(false);
            }
        } catch (error) {
            console.error('Fehler beim Aktualisieren der Session:', error);
            this.setLoading(false);
        }
    }
    
    setupScrollListener() {
        let scrollTimeout;
        let hideTimeout;
        
        const showButtonTemporarily = () => {
            const loadMoreBtn = document.getElementById('load-more-btn');
            if (!loadMoreBtn) return;
            
            // Prüfe ob Button überhaupt etwas zu laden hat
            const hasMessagesToLoad = this.loadedMessageCount < this.totalMessageCount;
            
            if (!hasMessagesToLoad) {
                loadMoreBtn.classList.remove('show');
                return;
            }
            
            // Zeige Button mit show-Klasse
            loadMoreBtn.classList.add('show');
            
            // Lösche vorherigen Hide-Timeout
            clearTimeout(hideTimeout);
            
            // Verstecke Button nach 5 Sekunden
            hideTimeout = setTimeout(() => {
                loadMoreBtn.classList.remove('show');
            }, 5000);
        };
        
        // Standard Scroll-Event (wenn scrollbar vorhanden)
        this.dom.chatMessages.addEventListener('scroll', () => {
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(() => {
                const scrollTop = this.dom.chatMessages.scrollTop;
                
                // Zeige Button wenn User ganz oben ist
                if (scrollTop < 50) {
                    showButtonTemporarily();
                }
            }, 100);
        });
        
        // Wheel-Event für Scroll-Versuche (auch ohne Scrollbar)
        this.dom.chatMessages.addEventListener('wheel', (e) => {
            // Nur bei Scroll nach oben (deltaY negativ)
            if (e.deltaY < 0) {
                const scrollTop = this.dom.chatMessages.scrollTop;
                
                // Wenn bereits ganz oben oder kein Scroll möglich
                if (scrollTop <= 0) {
                    showButtonTemporarily();
                }
            }
        }, { passive: true });
    }

    setMessageSentCallback(callback) {
        this.messageSentCallback = callback;
    }
    
    createLoadMoreButton() {
        // Prüfe ob Button bereits existiert
        if (document.getElementById('load-more-btn')) {
            return;
        }
        
        const loadMoreBtn = document.createElement('button');
        loadMoreBtn.id = 'load-more-btn';
        loadMoreBtn.className = 'load-more-btn'; // Ohne hidden - initial nicht sichtbar durch CSS
        loadMoreBtn.innerHTML = '<span>↑ Ältere Nachrichten laden</span>';
        loadMoreBtn.addEventListener('click', () => this.loadMoreMessages());
        
        // Füge den Button am Anfang des Chat-Containers ein
        this.dom.chatMessages.insertBefore(loadMoreBtn, this.dom.chatMessages.firstChild);
        
        // Zeige Button nur wenn es mehr Nachrichten gibt
        this.updateLoadMoreButton();
    }
    
    updateLoadMoreButton() {
        const loadMoreBtn = document.getElementById('load-more-btn');
        if (!loadMoreBtn) return;
        
        // Zähle aktuell angezeigte Nachrichten (ohne den Button selbst)
        const displayedMessages = this.dom.chatMessages.querySelectorAll('.message').length;
        this.loadedMessageCount = displayedMessages;
        
        // Update nur den Button-Text, Sichtbarkeit wird durch Scroll-Listener gesteuert
        console.log('Load More Button Update:', {
            displayedMessages: this.loadedMessageCount,
            totalMessageCount: this.totalMessageCount
        });
        
        if (this.loadedMessageCount < this.totalMessageCount) {
            const remaining = this.totalMessageCount - this.loadedMessageCount;
            loadMoreBtn.querySelector('span').textContent = 
                `↑ Ältere Nachrichten laden (${remaining} weitere)`;
        } else {
            // Keine Nachrichten mehr verfügbar - Button bleibt versteckt
            loadMoreBtn.classList.remove('show');
        }
    }
    
    async loadMoreMessages() {
        if (this.isLoadingMore || !this.currentSessionId) {
            return;
        }
        
        this.isLoadingMore = true;
        const loadMoreBtn = document.getElementById('load-more-btn');
        
        if (loadMoreBtn) {
            loadMoreBtn.disabled = true;
            loadMoreBtn.querySelector('span').textContent = 'Lädt...';
        }
        
        try {
            const response = await fetch(`/api/sessions/${this.currentSessionId}/load_more`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    offset: this.loadedMessageCount,
                    limit: 30,
                    persona_id: window.activePersonaId || 'default'
                })
            });
            
            const data = await response.json();
            
            if (data.success && data.messages.length > 0) {
                // Speichere aktuelle Scroll-Position
                const currentScrollHeight = this.dom.chatMessages.scrollHeight;
                
                // Nachrichten kommen chronologisch (älteste zuerst).
                // Wir müssen sie umgekehrt durchgehen, damit prependMessage
                // sie in der richtigen Reihenfolge einfügt (jedes Element
                // wird nach dem Load-More-Button eingefügt).
                const reversed = [...data.messages].reverse();
                reversed.forEach(msg => {
                    this.prependMessage(msg.message, msg.is_user, msg.character_name, msg.timestamp, msg.memorized);
                });
                
                // Update total count
                this.totalMessageCount = data.total_count;
                
                // Stelle Scroll-Position wieder her (damit User an gleicher Stelle bleibt)
                const newScrollHeight = this.dom.chatMessages.scrollHeight;
                this.dom.chatMessages.scrollTop = newScrollHeight - currentScrollHeight;
                
                // Update Button
                this.updateLoadMoreButton();
            }
        } catch (error) {
            console.error('Fehler beim Laden weiterer Nachrichten:', error);
        } finally {
            this.isLoadingMore = false;
            if (loadMoreBtn) {
                loadMoreBtn.disabled = false;
                this.updateLoadMoreButton();
            }
        }
    }
    
    prependMessage(message, isUser, characterName, timestamp, memorized) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
        
        const avatarDiv = this.createAvatarDiv(isUser, characterName);
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        const senderDiv = document.createElement('div');
        senderDiv.className = 'message-sender';
        const effectiveCharacterName = this.getCurrentPersonaName() || characterName;
        senderDiv.textContent = isUser ? this.getUserDisplayName() : effectiveCharacterName;
        
        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = `message-bubble${memorized ? ' memorized' : ''}`;
        
        // Formatiere die Nachricht
        let formattedMessage = message;
        const hasCodeBlocks = formattedMessage.includes('<div class="code-block">');
        
        if (!hasCodeBlocks) {
            formattedMessage = formattedMessage
                .replace(/\*(.*?)\*/g, '<span class="non_verbal">$1</span>');
            
            if (formattedMessage.startsWith('\n')) {
                formattedMessage = formattedMessage.replace(/^\n+/, '');
            }
            
            formattedMessage = formattedMessage.trim();
            formattedMessage = formattedMessage.replace(/\n/g, '<br>');
        } else {
            formattedMessage = formattedMessage
                .replace(/\*(.*?)\*/g, '<span class="non_verbal">$1</span>');
            formattedMessage = formattedMessage.trim();
        }
        
        bubbleDiv.innerHTML = formattedMessage;
        
        // Parse timestamp
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        const date = new Date(timestamp);
        timeDiv.textContent = date.toLocaleTimeString('de-DE', { 
            hour: '2-digit', 
            minute: '2-digit',
            timeZone: 'Europe/Berlin'
        });
        
        bubbleDiv.appendChild(timeDiv);
        contentDiv.appendChild(senderDiv);
        contentDiv.appendChild(bubbleDiv);
        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(contentDiv);
        
        // Füge nach dem Load-More-Button ein
        const loadMoreBtn = document.getElementById('load-more-btn');
        if (loadMoreBtn && loadMoreBtn.nextSibling) {
            this.dom.chatMessages.insertBefore(messageDiv, loadMoreBtn.nextSibling);
        } else {
            this.dom.chatMessages.insertBefore(messageDiv, this.dom.chatMessages.firstChild);
        }
    }

    handleKeyPress(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            this.sendMessage();
        }
    }
    
    autoResize() {
        this.dom.messageInput.style.height = 'auto';
        this.dom.messageInput.style.height = Math.min(this.dom.messageInput.scrollHeight, 120) + 'px';
        
        // Dynamisch padding-bottom der Chat-Messages an die Input-Höhe anpassen
        const inputContainer = document.querySelector('.chat-input-container');
        if (inputContainer && this.dom.chatMessages) {
            const inputHeight = inputContainer.offsetHeight;
            this.dom.chatMessages.style.paddingBottom = (inputHeight + 30) + 'px';
        }
    }
    
    async sendMessage() {
        const message = this.dom.messageInput.value.trim();
        
        if (!message || this.isLoading || this.afterthoughtStreaming) {
            return;
        }
        
        // Stoppe Nachgedanke-Timer bei neuer Nachricht
        this.stopAfterthoughtTimer();
        
        // Speichere die Nachricht temporär, falls wir sie wiederherstellen müssen
        const savedMessage = message;
        
        this.isLoading = true;
        this.dom.messageInput.value = '';
        this.autoResize();
        
        this.addMessage(message, true);
        this.setLoading(true);
        
        // Hole API-Einstellungen aus UserSettings
        const apiModel = UserSettings.get('apiModel');
        const apiTemperature = UserSettings.get('apiTemperature');
        const contextLimit = UserSettings.get('contextLimit');
        
        try {
            const requestBody = { 
                message: message,
                session_id: this.currentSessionId,
                persona_id: window.activePersonaId || 'default'
            };
            
            // Füge API-Einstellungen hinzu, falls vorhanden
            if (apiModel) {
                requestBody.api_model = apiModel;
            }
            if (apiTemperature) {
                requestBody.api_temperature = parseFloat(apiTemperature);
            }
            if (contextLimit) {
                requestBody.context_limit = parseInt(contextLimit);
            }
            
            // Experimental-Modus aus Toggle lesen
            const modeToggle = document.getElementById('mode-toggle');
            if (modeToggle && modeToggle.checked) {
                requestBody.experimental_mode = true;
            }
            
            // Streaming-Anfrage
            const response = await fetch('/chat_stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            });
            
            // Prüfe ob die Antwort ein JSON-Error ist (z.B. api_key_missing)
            const contentType = response.headers.get('content-type') || '';
            if (contentType.includes('application/json')) {
                const data = await response.json();
                if (data.error_type === 'api_key_missing') {
                    this.removeLastUserMessage();
                    this.showApiKeyWarning();
                    this.dom.messageInput.value = savedMessage;
                    this.autoResize();
                    return;
                }
                if (data.error_type === 'credit_balance_exhausted') {
                    this.removeLastUserMessage();
                    this.addTypingMessage('Das API-Guthaben ist erschöpft. Bitte lade dein Guthaben auf, um weiterhin Nachrichten senden zu können.', false);
                    this.showCreditExhaustedOverlay();
                    this.dom.messageInput.value = savedMessage;
                    this.autoResize();
                    return;
                }
                if (!data.success) {
                    this.addTypingMessage('Entschuldigung, es gab einen Fehler bei der Verarbeitung deiner Nachricht.', false);
                    return;
                }
            }
            
            // SSE Stream verarbeiten
            await this.processStream(response);
            
        } catch (error) {
            console.error('Fehler beim Senden der Nachricht:', error);
            this.addTypingMessage('Verbindungsfehler. Bitte versuche es erneut.', false);
        } finally {
            this.setLoading(false);
            this.dom.messageInput.focus();
        }
    }
    
    async processStream(response) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let rawText = '';
        let streamingBubble = null;
        let streamingMessageDiv = null;
        let characterName = 'Assistant';
        let promptStats = null;
        
        // Erstelle die Streaming-Nachricht-Bubble
        const { messageDiv, bubbleDiv, contentDiv } = this.createStreamingMessage();
        streamingBubble = bubbleDiv;
        streamingMessageDiv = messageDiv;
        
        // Loading-Animation ausblenden sobald erster Chunk kommt
        let firstChunk = true;
        
        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                buffer += decoder.decode(value, { stream: true });
                
                // SSE Events parsen
                const events = buffer.split('\n\n');
                buffer = events.pop(); // Unvollständiges Event behalten
                
                for (const event of events) {
                    if (!event.startsWith('data: ')) continue;
                    
                    try {
                        const data = JSON.parse(event.slice(6));
                        
                        if (data.type === 'chunk') {
                            if (firstChunk) {
                                firstChunk = false;
                                this.dom.loadingAnimation.classList.add('hidden');
                            }
                            rawText += data.text;
                            this.updateStreamingBubble(streamingBubble, rawText);
                        } else if (data.type === 'done') {
                            characterName = data.character_name || 'Assistant';
                            promptStats = data.stats || null;
                            
                            // Finalisiere die Bubble mit der bereinigten Antwort
                            this.finalizeStreamingBubble(streamingBubble, contentDiv, data.response, characterName, promptStats);
                            
                            // Update Sender-Name
                            const senderDiv = streamingMessageDiv.querySelector('.message-sender');
                            const effectiveCharacterName = this.getCurrentPersonaName() || characterName;
                            if (senderDiv) senderDiv.textContent = effectiveCharacterName;
                            
                            // Update message counts
                            this.totalMessageCount += 2;
                            this.updateLoadMoreButton();
                            
                            // Callbacks
                            if (this.messageSentCallback) this.messageSentCallback();
                            
                            // Benachrichtigungston abspielen
                            this.playNotificationSound();
                            
                            // Nachgedanke-Timer starten nach erfolgreicher Antwort
                            this.startAfterthoughtTimer(false);
                        } else if (data.type === 'error') {
                            console.error('Stream-Fehler:', data.error);
                            if (data.error_type === 'credit_balance_exhausted' || (data.error && data.error.includes && data.error.includes('credit_balance_exhausted'))) {
                                streamingBubble.innerHTML = 'Das API-Guthaben ist erschöpft. Bitte lade dein Guthaben auf, um weiterhin Nachrichten senden zu können.';
                                this.addTimeStamp(streamingBubble);
                                this.showCreditExhaustedOverlay();
                            } else {
                                streamingBubble.innerHTML = 'Entschuldigung, es gab einen Fehler bei der Verarbeitung.';
                                this.addTimeStamp(streamingBubble);
                            }
                        }
                    } catch (parseError) {
                        console.error('SSE Parse-Fehler:', parseError, event);
                    }
                }
            }
        } catch (error) {
            console.error('Stream-Lesefehler:', error);
            if (streamingBubble && !rawText) {
                streamingBubble.innerHTML = 'Verbindungsfehler. Bitte versuche es erneut.';
                this.addTimeStamp(streamingBubble);
            }
        }
    }
    
    createStreamingMessage() {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot-message';

        const effectiveCharacterName = this.getCurrentPersonaName() || 'Assistant';
        const avatarDiv = this.createAvatarDiv(false, effectiveCharacterName);
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        const senderDiv = document.createElement('div');
        senderDiv.className = 'message-sender';
        senderDiv.textContent = effectiveCharacterName;
        
        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = 'message-bubble streaming';
        
        contentDiv.appendChild(senderDiv);
        contentDiv.appendChild(bubbleDiv);
        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(contentDiv);
        
        this.dom.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
        
        return { messageDiv, bubbleDiv, contentDiv };
    }
    
    formatStreamingText(rawText) {
        // Ersetze \n+ mit Leerzeichen (wie clean_api_response im Backend)
        let text = rawText.replace(/\n+/g, ' ');
        
        // Entferne "---" am Anfang
        text = text.replace(/^\s*---\s*/, '');
        
        // Nonverbale Formatierung: Nur vollständige *...* Paare ersetzen
        text = text.replace(/\*(.*?)\*/g, '<span class="non_verbal">$1</span>');
        
        return text.trim();
    }
    
    updateStreamingBubble(bubbleDiv, rawText) {
        const formatted = this.formatStreamingText(rawText);
        bubbleDiv.innerHTML = formatted + '<span class="streaming-cursor"></span>';
        this.scrollToBottom();
    }
    
    finalizeStreamingBubble(bubbleDiv, contentDiv, finalResponse, characterName, promptStats) {
        // Entferne streaming-Klasse
        bubbleDiv.classList.remove('streaming');
        
        // Finales HTML aufbereiten (gleiche Logik wie addTypingMessage)
        let finalHTML = finalResponse;
        const hasCodeBlocks = finalHTML.includes('<div class="code-block">');
        
        if (!hasCodeBlocks) {
            if (finalHTML.startsWith('\n')) {
                finalHTML = finalHTML.replace(/^\n+/, '');
            }
            finalHTML = finalHTML.trim();
            finalHTML = finalHTML.replace(/\n/g, '<br>');
        } else {
            finalHTML = finalHTML.trim();
        }
        
        // Nonverbale Formatierung
        finalHTML = finalHTML.replace(/\*(.*?)\*/g, '<span class="non_verbal">$1</span>');
        
        bubbleDiv.innerHTML = finalHTML;
        
        // Zeitstempel hinzufügen
        this.addTimeStamp(bubbleDiv);
        
        // Info-Button für Prompt-Stats
        if (promptStats) {
            const infoButton = document.createElement('button');
            infoButton.className = 'prompt-info-btn';
            infoButton.innerHTML = 'i';
            infoButton.title = 'Prompt Informationen';
            infoButton.dataset.promptStats = JSON.stringify(promptStats);
            infoButton.addEventListener('click', (e) => {
                e.stopPropagation();
                this.showPromptInfoOverlay(promptStats);
            });
            contentDiv.appendChild(infoButton);
        }
        
        this.scrollToBottom();
    }
    
    addTimeStamp(bubbleDiv) {
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = new Date().toLocaleTimeString('de-DE', { 
            hour: '2-digit', 
            minute: '2-digit',
            timeZone: 'Europe/Berlin'
        });
        bubbleDiv.appendChild(timeDiv);
    }
    
    addMessage(message, isUser, characterName = 'Assistant', timestamp = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
        
        const avatarDiv = this.createAvatarDiv(isUser, characterName);
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        const senderDiv = document.createElement('div');
        senderDiv.className = 'message-sender';
        const effectiveCharacterName = this.getCurrentPersonaName() || characterName;
        senderDiv.textContent = isUser ? this.getUserDisplayName() : effectiveCharacterName;
        
        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = 'message-bubble';
        
        // Formatiere die Nachricht (Code-Blöcke werden bereits vom Backend als HTML geliefert)
        let formattedMessage = message;
        
        // Nur normalen Text formatieren, Code-Blöcke nicht anfassen
        // Code-Blöcke sind bereits als <div class="code-block">...</div> formatiert
        const hasCodeBlocks = formattedMessage.includes('<div class="code-block">');
        
        if (!hasCodeBlocks) {
            // Standard-Formatierung ohne Code-Blöcke
            formattedMessage = formattedMessage
                .replace(/\*(.*?)\*/g, '<span class="non_verbal">$1</span>');
            
            if (formattedMessage.startsWith('\n')) {
                formattedMessage = formattedMessage.replace(/^\n+/, '');
            }
            
            formattedMessage = formattedMessage.trim();
            formattedMessage = formattedMessage.replace(/\n/g, '<br>');
        } else {
            // Mit Code-Blöcken: Nur Text außerhalb der Code-Blöcke formatieren
            formattedMessage = formattedMessage
                .replace(/\*(.*?)\*/g, '<span class="non_verbal">$1</span>');
            formattedMessage = formattedMessage.trim();
        }
        
        bubbleDiv.innerHTML = formattedMessage;
        
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        const displayDate = timestamp ? new Date(timestamp) : new Date();
        timeDiv.textContent = displayDate.toLocaleTimeString('de-DE', { 
            hour: '2-digit', 
            minute: '2-digit',
            timeZone: 'Europe/Berlin'
        });
        
        bubbleDiv.appendChild(timeDiv);
        contentDiv.appendChild(senderDiv);
        contentDiv.appendChild(bubbleDiv);
        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(contentDiv);
        
        this.dom.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
        
        // Update button state after adding user message
        if (isUser) {
            this.updateNewChatButtonState();
        }
        
        return messageDiv;
    }
    
    addTypingMessage(message, isUser, characterName = 'Assistant', promptStats = null) {
        if (isUser) {
            return this.addMessage(message, true, characterName);
        }
        
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot-message';
        
        const avatarDiv = this.createAvatarDiv(isUser, characterName);
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        const senderDiv = document.createElement('div');
        senderDiv.className = 'message-sender';
        senderDiv.textContent = this.getCurrentPersonaName() || characterName;
        
        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = 'message-bubble';
        
        contentDiv.appendChild(senderDiv);
        contentDiv.appendChild(bubbleDiv);
        
        // Add info button if we have prompt stats
        if (promptStats) {
            const infoButton = document.createElement('button');
            infoButton.className = 'prompt-info-btn';
            infoButton.innerHTML = 'i';
            infoButton.title = 'Prompt Informationen';
            
            // Store stats in data attribute
            infoButton.dataset.promptStats = JSON.stringify(promptStats);
            
            // Add click handler
            infoButton.addEventListener('click', (e) => {
                e.stopPropagation();
                this.showPromptInfoOverlay(promptStats);
            });
            
            contentDiv.appendChild(infoButton);
        }
        
        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(contentDiv);
        
        this.dom.chatMessages.appendChild(messageDiv);
        
        // Direkte Einblendung für alle Nachrichten
        let finalHTML = message;
        
        // Prüfe ob Code-Blöcke vorhanden sind
        const hasCodeBlocks = finalHTML.includes('<div class="code-block">');
        
        if (!hasCodeBlocks) {
            // Ohne Code-Blöcke: Standard-Formatierung mit <br>
            if (finalHTML.startsWith('\n')) {
                finalHTML = finalHTML.replace(/^\n+/, '');
            }
            finalHTML = finalHTML.trim();
            finalHTML = finalHTML.replace(/\n/g, '<br>');
        } else {
            // Mit Code-Blöcken: Nur trimmen
            finalHTML = finalHTML.trim();
        }
        
        // Formatiere non-verbalen Text
        finalHTML = finalHTML.replace(/\*(.*?)\*/g, '<span class="non_verbal">$1</span>');
        
        bubbleDiv.innerHTML = finalHTML;
        
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = new Date().toLocaleTimeString('de-DE', { 
            hour: '2-digit', 
            minute: '2-digit',
            timeZone: 'Europe/Berlin'
        });
        bubbleDiv.appendChild(timeDiv);
        
        this.scrollToBottom();
        
        return messageDiv;
    }

    createAvatarDiv(isUser, characterName) {
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        
        if (isUser && window.userProfile && window.userProfile.user_avatar) {
            // User hat ein Profilbild
            const up = window.userProfile;
            const avatarPath = up.user_avatar_type === 'custom'
                ? `/static/images/custom/${up.user_avatar}`
                : `/static/images/avatars/${up.user_avatar}`;
            avatarDiv.style.backgroundImage = `url('${avatarPath}')`;
            avatarDiv.style.backgroundSize = 'cover';
            avatarDiv.style.backgroundPosition = 'center';
        } else if (!isUser && window.characterAvatar && window.characterAvatar.image) {
            const avatarPath = window.characterAvatar.type === 'custom' 
                ? `/static/images/custom/${window.characterAvatar.image}`
                : `/static/images/avatars/${window.characterAvatar.image}`;
            avatarDiv.style.backgroundImage = `url('${avatarPath}')`;
            avatarDiv.style.backgroundSize = 'cover';
            avatarDiv.style.backgroundPosition = 'center';
        } else {
            const avatarText = document.createElement('span');
            avatarText.className = 'avatar-text';
            if (isUser) {
                const userName = (window.userProfile && window.userProfile.user_name) || 'Du';
                avatarText.textContent = userName.charAt(0).toUpperCase();
            } else {
                avatarText.textContent = characterName[0];
            }
            avatarDiv.appendChild(avatarText);
        }
        
        return avatarDiv;
    }

    /**
     * Gibt den User-Anzeigenamen zurück
     */
    getUserDisplayName() {
        return (window.userProfile && window.userProfile.user_name) || 'Du';
    }
    
    setLoading(loading) {
        this.isLoading = loading;
        this.dom.sendButton.disabled = loading;
        // Textarea bleibt IMMER enabled – Fokus darf nie gestohlen werden.
        // Senden wird durch isLoading-Flag in sendMessage() blockiert.
        this.dom.messageInput.classList.toggle('streaming-active', loading);
        
        if (loading) {
            this.dom.loadingAnimation.classList.remove('hidden');
        } else {
            this.dom.loadingAnimation.classList.add('hidden');
        }
    }
    
    scrollToBottom(isPageLoad = false) {
        setTimeout(() => {
            if (isPageLoad) {
                // Bei Seitenladung: Scrolle komplett bis zum Ende
                this.dom.chatMessages.scrollTop = this.dom.chatMessages.scrollHeight;
            } else {
                // Bei neuer Nachricht: Scrolle nur leicht nach unten (300px)
                const currentScroll = this.dom.chatMessages.scrollTop;
                const targetScroll = currentScroll + 300;
                
                this.dom.chatMessages.scrollTo({
                    top: targetScroll,
                    behavior: 'smooth'
                });
            }
        }, 100);
    }
    
    scrollToEnd() {
        // Hilfsfunktion für komplettes Scrollen bis zum Ende
        setTimeout(() => {
            this.dom.chatMessages.scrollTop = this.dom.chatMessages.scrollHeight;
        }, 100);
    }

    processExistingMessages() {
        const messageBubbles = document.querySelectorAll('.message-bubble');
        
        messageBubbles.forEach(bubble => {
            if (!bubble.querySelector('.non_verbal') && bubble.textContent.includes('*')) {
                // Speichere die message-time Element, falls vorhanden
                const timeElement = bubble.querySelector('.message-time');
                
                let content = bubble.innerHTML;
                
                // Entferne temporär das time-Element aus dem HTML-String
                if (timeElement) {
                    const tempDiv = document.createElement('div');
                    tempDiv.innerHTML = content;
                    const tempTimeElement = tempDiv.querySelector('.message-time');
                    if (tempTimeElement) {
                        tempTimeElement.remove();
                    }
                    content = tempDiv.innerHTML;
                }
                
                if (content.startsWith('&#10;') || content.startsWith('\n')) {
                    content = content.replace(/^(&#10;)+/, '');
                    content = content.replace(/^\n+/, '');
                }
                
                content = content.replace(/\*(.*?)\*/g, '<span class="non_verbal">$1</span>');
                bubble.innerHTML = content;
                
                // Füge das time-Element wieder hinzu
                if (timeElement) {
                    bubble.appendChild(timeElement);
                }
            }
        });

        // Nach dem Rendern: Bot-Sendernamen an aktuellen Persona-Namen anpassen
        this.syncBotSenderNames();
    }

    updateNewChatButtonState() {
        // Neuer Chat-Button ist IMMER aktiviert
        // Leere Sessions werden beim Wechsel automatisch gelöscht
        this.dom.newChatBtn.disabled = false;
        this.dom.newChatBtn.classList.remove('disabled');
    }
    
    removeLastUserMessage() {
        // Entfernt die zuletzt hinzugefügte User-Nachricht aus dem DOM
        const userMessages = this.dom.chatMessages.querySelectorAll('.message.user-message');
        if (userMessages.length > 0) {
            const lastUserMessage = userMessages[userMessages.length - 1];
            lastUserMessage.remove();
        }
    }
    
    showApiKeyWarning() {
        // Zeigt das API-Key Warning Overlay an
        const overlay = document.getElementById('api-key-warning-overlay');
        if (overlay) {
            overlay.classList.remove('hidden');
        }
    }

    showCreditExhaustedOverlay() {
        // Zeigt das Credit-Erschöpft Overlay an
        const overlay = document.getElementById('credit-exhausted-overlay');
        if (overlay) {
            overlay.classList.remove('hidden');
        }
    }
    
    showPromptInfoOverlay(stats) {
        // Check if overlay already exists, remove it
        const existingOverlay = document.getElementById('prompt-info-overlay');
        if (existingOverlay) {
            existingOverlay.remove();
        }
        
        // Create overlay
        const overlay = document.createElement('div');
        overlay.id = 'prompt-info-overlay';
        overlay.className = 'prompt-info-overlay';
        
        // Create content container
        const content = document.createElement('div');
        content.className = 'prompt-info-content';
        
        // Echte API-Werte (die Wahrheit)
        const apiInput = stats.api_input_tokens || 0;
        const outputTokens = stats.output_tokens || 0;
        const grandTotal = apiInput + outputTokens;
        
        // Schätzungen für Breakdown-Proportionen
        const systemEst = stats.system_prompt_est || 0;
        const memoryEst = stats.memory_est || 0;
        const historyEst = stats.history_est || 0;
        const userMsgEst = stats.user_msg_est || 0;
        const prefillEst = stats.prefill_est || 0;
        const totalEst = stats.total_est || 1; // avoid div/0
        
        // Skaliere Schätzungen proportional auf den echten API-Wert
        const scale = apiInput > 0 && totalEst > 0 ? apiInput / totalEst : 1;
        const systemScaled = Math.round(systemEst * scale);
        const memoryScaled = Math.round(memoryEst * scale);
        const historyScaled = Math.round(historyEst * scale);
        const userMsgScaled = Math.round(userMsgEst * scale);
        const prefillScaled = Math.round(prefillEst * scale);
        
        // Get current model for pricing (falls von UserSettings nicht verfügbar, verwende Default)
        const currentModel = UserSettings.get('apiModel') || UserSettings.getDefault('apiModel');
        const apiModelOptions = UserSettings.getDefault('apiModelOptions', []);
        const modelMeta = Array.isArray(apiModelOptions)
            ? apiModelOptions.find((option) => option && option.value === currentModel)
            : null;
        
        // Model-specific pricing ($ per Million tokens)
        // Quelle: https://www.anthropic.com/pricing (Stand: Februar 2026)
        const inputPrice = modelMeta && modelMeta.inputPrice !== undefined ? modelMeta.inputPrice : 0;
        const outputPrice = modelMeta && modelMeta.outputPrice !== undefined ? modelMeta.outputPrice : 0;
        const modelDisplayName = (modelMeta && (modelMeta.pricingName || modelMeta.label)) || currentModel || 'Unbekannt';
        
        // Calculate costs
        const inputCost = (apiInput / 1000000) * inputPrice;
        const outputCost = (outputTokens / 1000000) * outputPrice;
        const totalCost = inputCost + outputCost;
        
        // Create header
        const header = document.createElement('div');
        header.className = 'prompt-info-header';
        header.innerHTML = `
            <div class="pi-title-group">
                <div class="pi-icon">📊</div>
                <h3>Prompt Informationen</h3>
            </div>
            <button class="close-btn">&times;</button>
        `;
        
        // Create progress bar
        const progressBar = document.createElement('div');
        progressBar.className = 'token-progress-bar';
        
        const minTokens = 1000;
        const maxTokens = 50000;
        const percentage = Math.min(Math.max(((grandTotal - minTokens) / (maxTokens - minTokens)) * 100, 0), 100);
        
        let barColor;
        if (percentage <= 20) {
            barColor = '#34a853';
        } else {
            const transition = (percentage - 20) / 80;
            const red = Math.round(52 + (239 - 52) * transition);
            const green = Math.round(168 - (168 - 68) * transition);
            const blue = Math.round(83 - 83 * transition);
            barColor = `rgb(${red}, ${green}, ${blue})`;
        }
        
        progressBar.innerHTML = `
            <div class="progress-bar-container">
                <div class="progress-bar-fill" style="width: ${percentage}%; background: ${barColor};"></div>
            </div>
            <div class="progress-bar-labels">
                <span class="progress-label-left">1k</span>
                <span class="progress-label-center">${grandTotal.toLocaleString()} Tokens</span>
                <span class="progress-label-right">50k</span>
            </div>
            <div class="cost-info">~ $${totalCost.toFixed(6)} (Input: $${inputCost.toFixed(6)} | Output: $${outputCost.toFixed(6)})</div>
            <div class="cost-disclaimer">⚠️ Ungefähre Berechnung - Die API gibt keine Kosteninformationen zurück. Preise basieren auf ${modelDisplayName} ($${inputPrice}/M Input, $${outputPrice}/M Output). Bitte mit Anbieter-Rechnung abgleichen.</div>
        `;
        
        // Create stats display
        const statsDiv = document.createElement('div');
        statsDiv.className = 'prompt-info-stats';
        
        // System Prompt Section
        const systemSection = document.createElement('div');
        systemSection.className = 'stat-section system-prompt';
        systemSection.innerHTML = `
            <div class="stat-label"><span class="stat-dot"></span>System Prompt</div>
            <div class="stat-breakdown">
                <div class="stat-item">
                    <span class="stat-name">Prompt + Persona</span>
                    <span class="stat-value">${systemScaled.toLocaleString()} Token</span>
                </div>
                ${memoryScaled > 0 ? `
                <div class="stat-item">
                    <span class="stat-name">Memory</span>
                    <span class="stat-value">${memoryScaled.toLocaleString()} Token</span>
                </div>
                ` : ''}
            </div>
        `;
        
        // Messages Section
        const messagesSection = document.createElement('div');
        messagesSection.className = 'stat-section history';
        messagesSection.innerHTML = `
            <div class="stat-label"><span class="stat-dot"></span>Messages</div>
            <div class="stat-breakdown">
                <div class="stat-item">
                    <span class="stat-name">Chat History</span>
                    <span class="stat-value">${historyScaled.toLocaleString()} Token</span>
                </div>
                <div class="stat-item">
                    <span class="stat-name">User Nachricht</span>
                    <span class="stat-value">${userMsgScaled.toLocaleString()} Token</span>
                </div>
                <div class="stat-item">
                    <span class="stat-name">Prefill</span>
                    <span class="stat-value">${prefillScaled.toLocaleString()} Token</span>
                </div>
            </div>
        `;
        
        // Total Section - echte API-Werte
        const totalSection = document.createElement('div');
        totalSection.className = 'stat-section total';
        totalSection.innerHTML = `
            <div class="stat-label"><span class="stat-dot"></span>Gesamt (Anthropic API)</div>
            <div class="stat-breakdown">
                <div class="stat-item">
                    <span class="stat-name">Input</span>
                    <span class="stat-value">${apiInput.toLocaleString()} Token</span>
                </div>
                <div class="stat-item">
                    <span class="stat-name">Output</span>
                    <span class="stat-value">${outputTokens.toLocaleString()} Token</span>
                </div>
                <div class="stat-item stat-sum">
                    <span class="stat-name">Total</span>
                    <span class="stat-value">${grandTotal.toLocaleString()} Token</span>
                </div>
            </div>
        `;
        
        statsDiv.appendChild(systemSection);
        statsDiv.appendChild(messagesSection);
        statsDiv.appendChild(totalSection);
        
        content.appendChild(header);
        content.appendChild(progressBar);
        content.appendChild(statsDiv);
        overlay.appendChild(content);
        
        // Add to body
        document.body.appendChild(overlay);
        
        // Close handlers
        const closeBtn = header.querySelector('.close-btn');
        closeBtn.addEventListener('click', () => overlay.remove());
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.remove();
            }
        });
    }

    // === NACHGEDANKE (AFTERTHOUGHT) SYSTEM ===
    
    /**
     * Prüft ob das Nachgedanke-Feature aktiviert ist
     */
    isAfterthoughtEnabled() {
        return UserSettings.get('nachgedankeEnabled', UserSettings.getDefault('nachgedankeEnabled', false));
    }
    
    /**
     * Startet den Nachgedanke-Timer nach einer Persona-Antwort.
     * @param {boolean} afterFollowup - true wenn nach einer Ergänzung (startet bei 5min)
     */
    startAfterthoughtTimer(afterFollowup = false) {
        // Stoppe vorherigen Timer
        this.stopAfterthoughtTimer();
        
        if (!this.isAfterthoughtEnabled()) return;
        if (!this.currentSessionId) return;
        
        this.afterthoughtActive = true;
        this.lastResponseTime = Date.now();
        
        if (afterFollowup) {
            // Nach einer Ergänzung: starte bei 5min (Stage 2)
            this.afterthoughtStage = 2;
        } else {
            // Nach normaler Antwort: starte bei 10s (Stage 0)
            this.afterthoughtStage = 0;
        }
        
        this._scheduleNextAfterthought();
    }
    
    /**
     * Stoppt den Nachgedanke-Timer
     */
    stopAfterthoughtTimer() {
        if (this.afterthoughtTimer) {
            clearTimeout(this.afterthoughtTimer);
            this.afterthoughtTimer = null;
        }
        this.afterthoughtActive = false;
        this.afterthoughtStage = 0;
    }
    
    /**
     * Plant den nächsten Nachgedanke-Check
     */
    _scheduleNextAfterthought() {
        if (this.afterthoughtStage >= this.afterthoughtIntervals.length) {
            // Alle Stufen durchlaufen → kein weiterer Check
            console.log('🤔 Nachgedanke: Alle Stufen durchlaufen, kein weiterer Check.');
            this.afterthoughtActive = false;
            return;
        }
        
        const delay = this.afterthoughtIntervals[this.afterthoughtStage];
        const label = this.afterthoughtElapsedLabels[this.afterthoughtStage];
        console.log(`🤔 Nachgedanke: Nächster Check in ${label} (Stage ${this.afterthoughtStage})`);
        
        this.afterthoughtTimer = setTimeout(() => {
            this._executeAfterthoughtCheck();
        }, delay);
    }
    
    /**
     * Führt den Nachgedanke-Check durch (innerer Dialog)
     */
    async _executeAfterthoughtCheck() {
        // Prüfe ob Nachgedanke zwischenzeitlich deaktiviert wurde
        if (!this.isAfterthoughtEnabled()) {
            console.log('🤔 Nachgedanke: Deaktiviert – Timer wird gestoppt.');
            this.stopAfterthoughtTimer();
            return;
        }
        
        if (!this.afterthoughtActive || this.isLoading || this.afterthoughtStreaming) {
            // Wenn gerade eine Nachricht gesendet wird oder gestreamt wird, abbrechen
            console.log('🤔 Nachgedanke: Übersprungen (isLoading oder streaming)');
            return;
        }
        
        if (!this.currentSessionId) return;
        
        // Berechne vergangene Zeit
        const elapsed = Date.now() - this.lastResponseTime;
        const elapsedLabel = this._formatElapsedTime(elapsed);
        
        console.log(`🤔 Nachgedanke: Innerer Dialog... (${elapsedLabel} vergangen)`);
        
        // Hole API-Einstellungen
        const apiModel = UserSettings.get('apiModel');
        const apiTemperature = UserSettings.get('apiTemperature');
        const contextLimit = UserSettings.get('contextLimit');
        const modeToggle = document.getElementById('mode-toggle');
        const experimentalMode = modeToggle && modeToggle.checked;
        
        try {
            const requestBody = {
                session_id: this.currentSessionId,
                elapsed_time: elapsedLabel,
                phase: 'decision',
                persona_id: window.activePersonaId || 'default'
            };
            
            if (apiModel) requestBody.api_model = apiModel;
            if (apiTemperature) requestBody.api_temperature = parseFloat(apiTemperature);
            if (contextLimit) requestBody.context_limit = parseInt(contextLimit);
            if (experimentalMode) requestBody.experimental_mode = true;
            
            const response = await fetch('/afterthought', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            });
            
            const data = await response.json();
            
            if (!data.success) {
                console.error('🤔 Nachgedanke Fehler:', data.error);
                return;
            }
            
            if (data.decision) {
                // Persona will etwas ergänzen → Followup streamen
                console.log('🤔 Nachgedanke: Persona will ergänzen!');
                await this._streamAfterthoughtFollowup(data.inner_dialogue, elapsedLabel);
            } else {
                // Persona schweigt → nächste Stufe
                console.log('🤔 Nachgedanke: Persona schweigt.');
                this.afterthoughtStage++;
                this._scheduleNextAfterthought();
            }
            
        } catch (error) {
            console.error('🤔 Nachgedanke Fehler:', error);
            // Bei Fehler: nächste Stufe versuchen
            this.afterthoughtStage++;
            this._scheduleNextAfterthought();
        }
    }
    
    /**
     * Streamt die Nachgedanke-Ergänzung
     */
    async _streamAfterthoughtFollowup(innerDialogue, elapsedLabel) {
        if (this.isLoading) return; // Sicherheitscheck
        
        // Setze Streaming-Flag (blockiert Senden in sendMessage())
        this.afterthoughtStreaming = true;
        this.dom.sendButton.disabled = true;
        // Textarea bleibt IMMER enabled – Fokus darf nie gestohlen werden.
        this.dom.messageInput.classList.add('streaming-active');
        
        const apiModel = UserSettings.get('apiModel');
        const apiTemperature = UserSettings.get('apiTemperature');
        const contextLimit = UserSettings.get('contextLimit');
        const modeToggle = document.getElementById('mode-toggle');
        const experimentalMode = modeToggle && modeToggle.checked;
        
        try {
            const requestBody = {
                session_id: this.currentSessionId,
                elapsed_time: elapsedLabel,
                phase: 'followup',
                inner_dialogue: innerDialogue,
                persona_id: window.activePersonaId || 'default'
            };
            
            if (apiModel) requestBody.api_model = apiModel;
            if (apiTemperature) requestBody.api_temperature = parseFloat(apiTemperature);
            if (contextLimit) requestBody.context_limit = parseInt(contextLimit);
            if (experimentalMode) requestBody.experimental_mode = true;
            
            const response = await fetch('/afterthought', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            });
            
            // SSE Stream verarbeiten (ähnlich wie processStream)
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let rawText = '';
            
            // Erstelle Streaming-Bubble
            const { messageDiv, bubbleDiv, contentDiv } = this.createStreamingMessage();
            let characterName = 'Assistant';
            let promptStats = null;
            
            try {
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    
                    buffer += decoder.decode(value, { stream: true });
                    const events = buffer.split('\n\n');
                    buffer = events.pop();
                    
                    for (const event of events) {
                        if (!event.startsWith('data: ')) continue;
                        
                        try {
                            const data = JSON.parse(event.slice(6));
                            
                            if (data.type === 'chunk') {
                                rawText += data.text;
                                this.updateStreamingBubble(bubbleDiv, rawText);
                            } else if (data.type === 'done') {
                                characterName = data.character_name || 'Assistant';
                                promptStats = data.stats || null;
                                
                                this.finalizeStreamingBubble(bubbleDiv, contentDiv, data.response, characterName, promptStats);
                                
                                const senderDiv = messageDiv.querySelector('.message-sender');
                                const effectiveCharacterName = this.getCurrentPersonaName() || characterName;
                                if (senderDiv) senderDiv.textContent = effectiveCharacterName;
                                
                                // Update message counts (nur +1 da es nur eine Bot-Nachricht ist)
                                this.totalMessageCount += 1;
                                this.updateLoadMoreButton();
                                
                                if (this.messageSentCallback) this.messageSentCallback();
                                
                                // Benachrichtigungston abspielen
                                this.playNotificationSound();
                            } else if (data.type === 'error') {
                                console.error('🤔 Nachgedanke Stream-Fehler:', data.error);
                                bubbleDiv.innerHTML = '';
                                messageDiv.remove();
                            }
                        } catch (parseError) {
                            console.error('SSE Parse-Fehler (Nachgedanke):', parseError);
                        }
                    }
                }
            } catch (error) {
                console.error('Nachgedanke Stream-Lesefehler:', error);
            }
            
            // Nach erfolgreicher Ergänzung: Timer neu starten bei 5min
            this.afterthoughtStreaming = false;
            this.dom.sendButton.disabled = false;
            this.dom.messageInput.classList.remove('streaming-active');
            this.startAfterthoughtTimer(true); // afterFollowup=true → startet bei 5min
            
        } catch (error) {
            console.error('🤔 Nachgedanke Followup Fehler:', error);
            this.afterthoughtStreaming = false;
            this.dom.sendButton.disabled = false;
            this.dom.messageInput.classList.remove('streaming-active');
        }
    }
    
    /**
     * Formatiert vergangene Zeit menschenlesbar
     */
    _formatElapsedTime(ms) {
        const seconds = Math.floor(ms / 1000);
        if (seconds < 60) return `${seconds} Sekunden`;
        const minutes = Math.floor(seconds / 60);
        if (minutes < 60) return `${minutes} Minute${minutes > 1 ? 'n' : ''}`;
        const hours = Math.floor(minutes / 60);
        return `${hours} Stunde${hours > 1 ? 'n' : ''}`;
    }
}
