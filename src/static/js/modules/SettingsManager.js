/**
 * SettingsManager - Handles all settings-related functionality
 */
import { UserSettings } from './UserSettings.js';

export class SettingsManager {
    constructor(dom) {
        this.dom = dom;
        this.pendingAvatar = null; // Avatar-Daten im Creator-Modus
        this.editingPersonaId = null; // ID der Persona im Edit-Mode
    }

    // ===== DROPDOWN =====
    toggleDropdown() {
        const wasOpen = this.dom.settingsMenu.classList.contains('show');
        this.dom.settingsMenu.classList.toggle('show');
        // Submenu zurücksetzen wenn Dropdown frisch geöffnet wird
        if (!wasOpen) {
            this._closeSubmenu();
        }
    }
    
    closeDropdown() {
        this.dom.settingsMenu.classList.remove('show');
        this._closeSubmenu();
    }
    
    _closeSubmenu() {
        const toggle = document.getElementById('settings-submenu-toggle');
        const sub = document.getElementById('settings-submenu');
        if (toggle) toggle.classList.remove('open');
        if (sub) sub.classList.remove('open');
    }

    // ===== PERSONA SETTINGS =====
    async openCharacterSettings() {
        try {
            // Lade verfügbare Optionen und aktuelle Config
            const [optionsResponse, configResponse, personasResponse] = await Promise.all([
                fetch('/get_available_options'),
                fetch('/get_char_config'),
                fetch('/api/personas')
            ]);
            
            const optionsData = await optionsResponse.json();
            const configData = await configResponse.json();
            const personasData = await personasResponse.json();
            
            if (optionsData.success && configData.success) {
                this.availableOptions = optionsData.options;
                this.optionDetails = optionsData.details;
                this.customKeys = optionsData.custom_keys || {};
                this.currentConfig = configData.config;
                this.personas = personasData.success ? personasData.personas : [];
                
                // Zeige Persona-Liste, verstecke Creator
                this.showPersonaList();
                this.renderPersonaGrid();
                
                this.dom.characterOverlay.classList.remove('hidden');
            } else {
                alert('Fehler beim Laden der Persona-Optionen');
            }
        } catch (error) {
            console.error('Fehler beim Laden der Persona-Einstellungen:', error);
            alert('Verbindungsfehler beim Laden der Einstellungen');
        }
    }
    
    /**
     * Lädt verfügbare Optionen vom Server neu und rendert den Persona Creator.
     * Wird nach dem Erstellen/Löschen von Custom Specs aufgerufen.
     */
    async refreshAvailableOptions() {
        try {
            const response = await fetch('/get_available_options');
            const optionsData = await response.json();
            
            if (optionsData.success) {
                this.availableOptions = optionsData.options;
                this.optionDetails = optionsData.details;
                this.customKeys = optionsData.custom_keys || {};
                
                // Persona Creator neu rendern falls sichtbar
                if (this.dom.personaCreatorView && !this.dom.personaCreatorView.classList.contains('hidden')) {
                    this.renderPersonaTypeSelector();
                    this.renderCoreTraitsTags();
                    this.renderKnowledgeTags();
                    this.renderExpressionTags();
                    this.renderScenarioTags();
                }
            }
        } catch (error) {
            console.error('Fehler beim Refresh der Optionen:', error);
        }
    }
    
    showPersonaList() {
        this.dom.personaListView.classList.remove('hidden');
        this.dom.personaCreatorView.classList.add('hidden');
    }
    
    /**
     * Setzt Avatar-Daten im Creator (wird vom AvatarManager-Callback aufgerufen).
     * Aktualisiert nur die Creator-Vorschau, kein Server-Call.
     */
    setCreatorAvatar(avatarData) {
        this.pendingAvatar = avatarData;
        
        // Creator-Vorschau aktualisieren
        const preview = this.dom.creatorAvatarPreview;
        const imgPath = avatarData.avatar_type === 'custom'
            ? `/static/images/custom/${avatarData.avatar}`
            : `/static/images/avatars/${avatarData.avatar}`;
        
        preview.innerHTML = '';
        preview.style.backgroundImage = `url('${imgPath}')`;
        preview.style.backgroundSize = 'cover';
        preview.style.backgroundPosition = 'center';
        preview.style.backgroundRepeat = 'no-repeat';
    }
    
    /**
     * Setzt die Creator-Avatar-Vorschau zurück
     */
    _resetCreatorAvatarPreview() {
        const preview = this.dom.creatorAvatarPreview;
        preview.style.backgroundImage = '';
        preview.style.backgroundSize = '';
        preview.style.backgroundPosition = '';
        preview.style.backgroundRepeat = '';
        preview.innerHTML = '<span class="avatar-placeholder-text">Kein Avatar</span>';
    }
    
    showPersonaCreator(editMode = false, personaData = null) {
        this.dom.personaListView.classList.add('hidden');
        this.dom.personaCreatorView.classList.remove('hidden');
        
        this.editingPersonaId = editMode ? personaData?.id : null;
        
        // Titel anpassen
        const editorTitle = document.getElementById('persona-editor-title');
        if (editorTitle) {
            editorTitle.textContent = editMode ? `${personaData.name} bearbeiten` : 'Persona Creator';
        }
        
        if (editMode && personaData) {
            // Edit-Mode: bestehende Daten laden
            this.currentConfig = {
                name: personaData.name || '',
                age: personaData.age || 18,
                gender: personaData.gender || 'divers',
                persona: personaData.persona || 'KI',
                core_traits: [...(personaData.core_traits || [])],
                knowledge: [...(personaData.knowledge || [])],
                expression: personaData.expression || 'normal',
                scenarios: [...(personaData.scenarios || [])],
                start_msg_enabled: personaData.start_msg_enabled || false,
                start_msg: personaData.start_msg || '',
                background: personaData.background || ''
            };
            
            // Avatar im Edit-Mode setzen
            this.pendingAvatar = null;
            if (personaData.avatar) {
                this.pendingAvatar = {
                    avatar: personaData.avatar,
                    avatar_type: personaData.avatar_type || 'default'
                };
                this.setCreatorAvatar(this.pendingAvatar);
            } else {
                this._resetCreatorAvatarPreview();
            }
        } else {
            // Neuer Creator: Reset Config
            this.currentConfig = {
                name: '',
                age: 18,
                gender: 'divers',
                persona: 'KI',
                core_traits: [],
                knowledge: [],
                expression: 'normal',
                scenarios: [],
                start_msg_enabled: false,
                start_msg: '',
                background: ''
            };
            
            this.pendingAvatar = null;
            this._resetCreatorAvatarPreview();
        }
        
        this._cleanupPersonaListeners();
        this.renderNameInput();
        this.renderPersonaTypeSelector();
        this.renderCoreTraitsTags();
        this.renderKnowledgeTags();
        this.renderExpressionTags();
        this.renderScenarioTags();
        this.updateScenarioVisibility();
        this.renderBackgroundInput();
        this.renderFirstMessageToggle();
    }
    
    async renderPersonaGrid(highlightId = null) {
        const grid = this.dom.personaGrid;
        grid.innerHTML = '';
        
        this.personas.forEach(persona => {
            const item = document.createElement('div');
            item.className = 'persona-contact-item' + (highlightId && persona.id === highlightId ? ' persona-card-new' : '');
            item.dataset.personaId = persona.id;
            
            // Avatar
            let avatarHTML;
            if (persona.avatar) {
                const imgPath = persona.avatar_type === 'custom'
                    ? `/static/images/custom/${persona.avatar}`
                    : `/static/images/avatars/${persona.avatar}`;
                avatarHTML = `<div class="persona-contact-avatar" style="background-image: url('${imgPath}');"></div>`;
            } else {
                avatarHTML = `<div class="persona-contact-avatar"><span class="persona-contact-initial">${(persona.name || '?')[0]}</span></div>`;
            }
            
            // Badges
            const badges = [];
            if (persona.is_active) badges.push('<span class="persona-badge active-badge">Aktiv</span>');
            if (persona.is_default) badges.push('<span class="persona-badge default-badge">Standard</span>');
            const badgeHTML = badges.length > 0 ? `<div class="persona-contact-badges">${badges.join('')}</div>` : '';
            
            item.innerHTML = `
                ${avatarHTML}
                <div class="persona-contact-info">
                    <span class="persona-contact-name">${persona.name || 'Unbenannt'}</span>
                    <span class="persona-contact-type">${persona.persona || 'KI'}</span>
                </div>
                ${badgeHTML}
                <div class="persona-contact-actions">
                    ${!persona.is_default ? `<button class="persona-edit-btn" data-id="${persona.id}" title="Bearbeiten">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                        </svg>
                    </button>
                     <button class="persona-delete-btn" data-id="${persona.id}" title="Löschen">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="3 6 5 6 21 6"></polyline>
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                        </svg>
                    </button>` : ''}
                </div>
            `;
            
            grid.appendChild(item);
        });
        
        // Event Listener für Bearbeiten
        grid.querySelectorAll('.persona-edit-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const id = e.currentTarget.dataset.id;
                this.editPersona(id);
            });
        });
        
        // Event Listener für Löschen
        grid.querySelectorAll('.persona-delete-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const id = e.currentTarget.dataset.id;
                this.deletePersona(id);
            });
        });
    }
    
    editPersona(personaId) {
        const persona = this.personas.find(p => p.id === personaId);
        if (!persona) {
            console.error('Persona nicht gefunden:', personaId);
            return;
        }
        this.showPersonaCreator(true, persona);
    }
    
    async deletePersona(personaId) {
        if (!confirm('Möchtest du diese Persona wirklich löschen?')) return;
        
        try {
            const response = await fetch(`/api/personas/${personaId}`, {
                method: 'DELETE'
            });
            const data = await response.json();
            
            if (data.success) {
                // Refreshe die Liste
                const personasResponse = await fetch('/api/personas');
                const personasData = await personasResponse.json();
                this.personas = personasData.success ? personasData.personas : [];
                this.renderPersonaGrid();
                
                // Sidebar Persona-Liste aktualisieren (soft reload)
                if (this.sessionManager) {
                    await this.sessionManager.loadPersonas();
                    this.sessionManager.renderPersonaList();
                }
            } else {
                alert('Fehler beim Löschen: ' + (data.error || 'Unbekannter Fehler'));
            }
        } catch (error) {
            console.error('Fehler beim Löschen der Persona:', error);
            alert('Verbindungsfehler');
        }
    }
    
    _cleanupPersonaListeners() {
        // Name Input: Clone und Replace um alte Listener zu entfernen
        const nameInput = document.getElementById('persona-name-input');
        if (nameInput) {
            const newInput = nameInput.cloneNode(true);
            nameInput.parentNode.replaceChild(newInput, nameInput);
        }
        
        // Age Slider: Clone und Replace
        const ageInput = document.getElementById('persona-age-input');
        if (ageInput) {
            const newAge = ageInput.cloneNode(true);
            ageInput.parentNode.replaceChild(newAge, ageInput);
        }
        
        // Gender Radio Buttons: Clone und Replace
        const genderRadios = document.querySelectorAll('input[name="persona-gender"]');
        genderRadios.forEach(radio => {
            const newRadio = radio.cloneNode(true);
            radio.parentNode.replaceChild(newRadio, radio);
        });
        
        // Persona Type: Container wird bei renderPersonaTypeSelector() neu befüllt
        const personaTypeContainer = document.getElementById('persona-type-selector');
        if (personaTypeContainer) personaTypeContainer.innerHTML = '';
        
        // Background Input: Clone und Replace
        const bgInput = document.getElementById('persona-background-input');
        if (bgInput) {
            const newBg = bgInput.cloneNode(true);
            bgInput.parentNode.replaceChild(newBg, bgInput);
        }
        
        // Background Autofill Button: Clone und Replace
        const bgAutofill = document.getElementById('background-autofill-btn');
        if (bgAutofill) {
            const newBgAutofill = bgAutofill.cloneNode(true);
            bgAutofill.parentNode.replaceChild(newBgAutofill, bgAutofill);
        }
        
        // First Message Toggle: Clone und Replace
        const startMsgToggle = document.getElementById('start-msg-toggle');
        if (startMsgToggle) {
            const newToggle = startMsgToggle.cloneNode(true);
            startMsgToggle.parentNode.replaceChild(newToggle, startMsgToggle);
        }
        
        // First Message Textarea: Clone und Replace
        const startMsgInput = document.getElementById('persona-start-msg-input');
        if (startMsgInput) {
            const newStartMsg = startMsgInput.cloneNode(true);
            startMsgInput.parentNode.replaceChild(newStartMsg, startMsgInput);
        }
    }
    
    renderNameInput() {
        const nameInput = document.getElementById('persona-name-input');
        if (nameInput) {
            nameInput.value = this.currentConfig.name || '';
            
            // Im Edit-Mode: Name ist nicht änderbar
            if (this.editingPersonaId) {
                nameInput.readOnly = true;
                nameInput.classList.add('input-readonly');
                nameInput.title = 'Name kann nicht geändert werden';
            } else {
                nameInput.readOnly = false;
                nameInput.classList.remove('input-readonly');
                nameInput.title = '';
            }
            
            nameInput.addEventListener('input', (e) => {
                if (!this.editingPersonaId) {
                    this.currentConfig.name = e.target.value;
                }
            });
        }
        
        // Age Slider
        const ageInput = document.getElementById('persona-age-input');
        const ageValue = document.getElementById('persona-age-value');
        if (ageInput) {
            const age = this.currentConfig.age || 18;
            ageInput.value = age;
            if (ageValue) ageValue.textContent = age;
            ageInput.addEventListener('input', (e) => {
                this.currentConfig.age = parseInt(e.target.value);
                if (ageValue) ageValue.textContent = e.target.value;
            });
        }
        
        // Gender Selector
        const genderRadios = document.querySelectorAll('input[name="persona-gender"]');
        genderRadios.forEach(radio => {
            if (radio.value === this.currentConfig.gender) {
                radio.checked = true;
            }
            radio.addEventListener('change', (e) => {
                if (e.target.checked) {
                    this.currentConfig.gender = e.target.value;
                }
            });
        });
    }
    
    renderPersonaTypeSelector() {
        const container = document.getElementById('persona-type-selector');
        if (!container) return;
        
        container.innerHTML = '';
        
        // Geordnete Liste aus availableOptions verwenden (Default zuerst, Custom danach)
        const personaTypes = this.optionDetails?.persona_types || {};
        const typeKeys = this.availableOptions?.persona_types || Object.keys(personaTypes);
        
        // Fallback falls leer
        if (typeKeys.length === 0) {
            typeKeys.push('KI');
        }
        
        typeKeys.forEach((typeKey, index) => {
            const label = document.createElement('label');
            label.className = 'radio-option';
            
            // Custom Spec Highlighting
            const isCustom = (this.customKeys?.persona_types || []).includes(typeKey);
            if (isCustom) label.classList.add('custom-spec');
            
            const input = document.createElement('input');
            input.type = 'radio';
            input.name = 'persona-type';
            input.value = typeKey;
            
            if (typeKey === this.currentConfig.persona) {
                input.checked = true;
            } else if (!this.currentConfig.persona && index === 0) {
                input.checked = true;
            }
            
            const description = personaTypes[typeKey] || typeKey;
            input.title = description;
            
            input.addEventListener('change', (e) => {
                if (e.target.checked) {
                    this.currentConfig.persona = e.target.value;
                    // Scenarios leeren wenn KI gewählt wird
                    if (e.target.value === 'KI') {
                        this.currentConfig.scenarios = [];
                    }
                    this.updateScenarioVisibility();
                    this.renderScenarioTags();
                }
            });
            
            const span = document.createElement('span');
            span.textContent = typeKey;
            
            label.appendChild(input);
            label.appendChild(span);
            container.appendChild(label);
        });
    }
    
    renderCoreTraitsTags() {
        const availableContainer = document.getElementById('traits-available');
        const activeContainer = document.getElementById('traits-active');
        const countSpan = document.getElementById('traits-count');
        
        availableContainer.innerHTML = '';
        activeContainer.innerHTML = '';
        
        const activeCount = this.currentConfig.core_traits.length;
        countSpan.textContent = activeCount;
        
        // Render available traits
        this.availableOptions.core_traits.forEach(key => {
            if (!this.currentConfig.core_traits.includes(key)) {
                const isCustom = (this.customKeys?.core_traits || []).includes(key);
                const tag = this.createTagButton(
                    key,
                    key, // Display trait name as is
                    'trait',
                    false,
                    false,
                    isCustom
                );
                availableContainer.appendChild(tag);
            }
        });
        
        // Render active traits
        this.currentConfig.core_traits.forEach(key => {
            const isCustom = (this.customKeys?.core_traits || []).includes(key);
            const activeTag = this.createTagButton(
                key,
                key, // Display trait name as is
                'trait',
                true,
                false,
                isCustom
            );
            activeContainer.appendChild(activeTag);
        });
    }
    
    renderKnowledgeTags() {
        const availableContainer = document.getElementById('knowledge-available');
        const activeContainer = document.getElementById('knowledge-active');
        const countSpan = document.getElementById('knowledge-count');
        
        availableContainer.innerHTML = '';
        activeContainer.innerHTML = '';
        
        const activeCount = this.currentConfig.knowledge.length;
        countSpan.textContent = activeCount;
        
        // Render available knowledge
        this.availableOptions.knowledge.forEach(key => {
            if (!this.currentConfig.knowledge.includes(key)) {
                const isCustom = (this.customKeys?.knowledge || []).includes(key);
                const tag = this.createTagButton(
                    key,
                    key, // Display knowledge name as is
                    'knowledge',
                    false,
                    false,
                    isCustom
                );
                availableContainer.appendChild(tag);
            }
        });
        
        // Render active knowledge
        this.currentConfig.knowledge.forEach(key => {
            const isCustom = (this.customKeys?.knowledge || []).includes(key);
            const activeTag = this.createTagButton(
                key,
                key, // Display knowledge name as is
                'knowledge',
                true,
                false,
                isCustom
            );
            activeContainer.appendChild(activeTag);
        });
    }
    
    renderExpressionTags() {
        const availableContainer = document.getElementById('expression-available');
        const activeContainer = document.getElementById('expression-active');
        
        availableContainer.innerHTML = '';
        activeContainer.innerHTML = '';
        
        // Render available expressions
        this.availableOptions.expression_styles.forEach(key => {
            if (key !== this.currentConfig.expression) {
                const expresssionData = this.optionDetails.expression_styles[key] || {};
                const label = expresssionData.name || key;
                const isCustom = (this.customKeys?.expression_styles || []).includes(key);
                const tag = this.createTagButton(
                    key,
                    label,
                    'expression',
                    false,
                    false,
                    isCustom
                );
                availableContainer.appendChild(tag);
            }
        });
        
        // Render active expression
        if (this.currentConfig.expression) {
            const expresssionData = this.optionDetails.expression_styles[this.currentConfig.expression] || {};
            const label = expresssionData.name || this.currentConfig.expression;
            const isCustom = (this.customKeys?.expression_styles || []).includes(this.currentConfig.expression);
            const activeTag = this.createTagButton(
                this.currentConfig.expression,
                label,
                'expression',
                true,
                false,
                isCustom
            );
            activeContainer.appendChild(activeTag);
        }
    }
    
    renderScenarioTags() {
        const availableContainer = document.getElementById('scenario-available');
        const activeContainer = document.getElementById('scenario-active');
        const countSpan = document.getElementById('scenario-count');
        
        if (!availableContainer || !activeContainer) return;
        
        availableContainer.innerHTML = '';
        activeContainer.innerHTML = '';
        
        if (!this.currentConfig.scenarios) {
            this.currentConfig.scenarios = [];
        }
        
        const activeCount = this.currentConfig.scenarios.length;
        if (countSpan) countSpan.textContent = activeCount;
        
        const scenarioOptions = this.availableOptions.scenarios || [];
        const scenarioDetails = this.optionDetails.scenarios || {};
        
        // Render available scenarios
        scenarioOptions.forEach(key => {
            if (!this.currentConfig.scenarios.includes(key)) {
                const scenarioData = scenarioDetails[key] || {};
                const label = scenarioData.name || key;
                const isCustom = (this.customKeys?.scenarios || []).includes(key);
                const tag = this.createTagButton(key, label, 'scenario', false, false, isCustom);
                availableContainer.appendChild(tag);
            }
        });
        
        // Render active scenarios
        this.currentConfig.scenarios.forEach(key => {
            const scenarioData = scenarioDetails[key] || {};
            const label = scenarioData.name || key;
            const isCustom = (this.customKeys?.scenarios || []).includes(key);
            const activeTag = this.createTagButton(key, label, 'scenario', true, false, isCustom);
            activeContainer.appendChild(activeTag);
        });
    }
    
    updateScenarioVisibility() {
        const scenarioSection = document.getElementById('scenario-section');
        if (!scenarioSection) return;
        
        if (this.currentConfig.persona === 'KI') {
            scenarioSection.classList.remove('scenario-visible');
        } else {
            scenarioSection.classList.add('scenario-visible');
        }
    }
    
    renderBackgroundInput() {
        const textarea = document.getElementById('persona-background-input');
        const charCount = document.getElementById('background-char-count');
        const autofillBtn = document.getElementById('background-autofill-btn');
        
        if (textarea) {
            textarea.value = this.currentConfig.background || '';
            if (charCount) charCount.textContent = textarea.value.length;
            
            textarea.addEventListener('input', (e) => {
                this.currentConfig.background = e.target.value;
                if (charCount) charCount.textContent = e.target.value.length;
            });
        }
        
        if (autofillBtn) {
            autofillBtn.addEventListener('click', async () => {
                if (!this.currentConfig.name) {
                    alert('Bitte gib zuerst einen Namen für die Persona ein.');
                    return;
                }
                
                autofillBtn.disabled = true;
                autofillBtn.textContent = '⏳ Generiere...';
                
                try {
                    const requestData = {
                        name: this.currentConfig.name,
                        age: this.currentConfig.age,
                        gender: this.currentConfig.gender,
                        persona: this.currentConfig.persona,
                        core_traits: this.currentConfig.core_traits,
                        knowledge: this.currentConfig.knowledge,
                        expression: this.currentConfig.expression,
                        scenarios: this.currentConfig.scenarios,
                        background_hint: textarea ? textarea.value.trim() : ''
                    };
                    
                    const response = await fetch('/api/personas/background-autofill', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(requestData)
                    });
                    
                    const data = await response.json();
                    
                    if (data.success && data.background) {
                        if (textarea) {
                            textarea.value = data.background;
                            this.currentConfig.background = data.background;
                            if (charCount) charCount.textContent = data.background.length;
                        }
                    } else {
                        alert('Fehler: ' + (data.error || 'Keine Antwort erhalten'));
                    }
                } catch (error) {
                    console.error('Background Autofill Fehler:', error);
                    alert('Verbindungsfehler beim Auto-Fill');
                } finally {
                    autofillBtn.disabled = false;
                    autofillBtn.textContent = '✨ Auto-Fill';
                }
            });
        }
    }
    
    renderFirstMessageToggle() {
        const toggle = document.getElementById('start-msg-toggle');
        const inputArea = document.getElementById('start-msg-input-area');
        const textarea = document.getElementById('persona-start-msg-input');
        const charCount = document.getElementById('start-msg-char-count');
        
        if (toggle) {
            toggle.checked = this.currentConfig.start_msg_enabled || false;
            
            // Sichtbarkeit initial setzen
            if (inputArea) {
                inputArea.classList.toggle('hidden', !toggle.checked);
            }
            
            toggle.addEventListener('change', (e) => {
                this.currentConfig.start_msg_enabled = e.target.checked;
                if (inputArea) {
                    inputArea.classList.toggle('hidden', !e.target.checked);
                }
            });
        }
        
        if (textarea) {
            textarea.value = this.currentConfig.start_msg || '';
            if (charCount) charCount.textContent = textarea.value.length;
            
            textarea.addEventListener('input', (e) => {
                this.currentConfig.start_msg = e.target.value;
                if (charCount) charCount.textContent = e.target.value.length;
            });
        }
    }
    
    createTagButton(key, label, type, isActive, isDisabled = false, isCustom = false) {
        const button = document.createElement('button');
        button.className = 'tag-button';
        button.textContent = label;
        button.dataset.key = key;
        button.dataset.type = type;
        
        if (isActive) {
            button.classList.add('active');
        }
        
        if (isDisabled) {
            button.classList.add('disabled');
            button.disabled = true;
        }
        
        if (isCustom) {
            button.classList.add('custom-spec');
        }
        
        // Click handler
        button.addEventListener('click', () => this.toggleTag(key, type));
        
        // Hover handler für Vorschau
        button.addEventListener('mouseenter', () => this.showPreview(key, type));
        
        return button;
    }
    
    toggleTag(key, type) {
        switch (type) {
            case 'trait':
                // Toggle trait (no limit)
                const traitIndex = this.currentConfig.core_traits.indexOf(key);
                if (traitIndex > -1) {
                    // Remove trait
                    this.currentConfig.core_traits.splice(traitIndex, 1);
                } else {
                    // Add trait
                    this.currentConfig.core_traits.push(key);
                }
                this.renderCoreTraitsTags();
                break;
                
            case 'knowledge':
                // Toggle knowledge (no limit)
                const knowledgeIndex = this.currentConfig.knowledge.indexOf(key);
                if (knowledgeIndex > -1) {
                    // Remove knowledge
                    this.currentConfig.knowledge.splice(knowledgeIndex, 1);
                } else {
                    // Add knowledge
                    this.currentConfig.knowledge.push(key);
                }
                this.renderKnowledgeTags();
                break;
                
            case 'expression':
                // Toggle expression style (only one active)
                this.currentConfig.expression = key;
                this.renderExpressionTags();
                break;
                
            case 'scenario':
                // Toggle scenario (combinable, like traits)
                const scenarioIndex = this.currentConfig.scenarios.indexOf(key);
                if (scenarioIndex > -1) {
                    this.currentConfig.scenarios.splice(scenarioIndex, 1);
                } else {
                    this.currentConfig.scenarios.push(key);
                }
                this.renderScenarioTags();
                break;
        }
        
        // Update full preview nach jedem Toggle
    }
    
    showPreview(key, type) {
        // Preview removed
    }
    
    closeCharacterSettings() {
        this.dom.characterOverlay.classList.add('hidden');
    }
    
    async saveCharacterSettings() {
        try {
            if (!this.currentConfig.name || this.currentConfig.name.trim() === '') {
                alert('Bitte gib einen Namen für die Persona ein.');
                return;
            }
            
            // Avatar-Daten zur Config hinzufügen (falls vorhanden)
            const saveData = { ...this.currentConfig };
            if (this.pendingAvatar) {
                saveData.avatar = this.pendingAvatar.avatar;
                saveData.avatar_type = this.pendingAvatar.avatar_type;
            }
            
            let response;
            let isUpdate = !!this.editingPersonaId;
            
            if (isUpdate) {
                // Update bestehende Persona (PUT)
                response = await fetch(`/api/personas/${this.editingPersonaId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(saveData)
                });
            } else {
                // Neue Persona erstellen (POST)
                response = await fetch('/api/personas', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(saveData)
                });
            }
            
            const data = await response.json();
            
            if (data.success) {
                const highlightId = isUpdate ? this.editingPersonaId : data.id;
                
                // Refreshe die Persona-Liste
                const personasResponse = await fetch('/api/personas');
                const personasData = await personasResponse.json();
                this.personas = personasData.success ? personasData.personas : [];
                this.renderPersonaGrid(highlightId);
                this.showPersonaList();
                
                // Sidebar Persona-Liste aktualisieren (soft reload)
                if (this.sessionManager) {
                    await this.sessionManager.loadPersonas();
                    this.sessionManager.renderPersonaList();
                }
                
                // Reset
                this.pendingAvatar = null;
                this.editingPersonaId = null;
            } else {
                alert('Fehler beim Speichern: ' + (data.error || 'Unbekannter Fehler'));
            }
        } catch (error) {
            console.error('Fehler beim Speichern der Persona:', error);
            alert('Verbindungsfehler beim Speichern');
        }
    }
    
    async resetCharacterSettings() {
        if (!confirm('Möchtest du das Formular zurücksetzen?')) {
            return;
        }
        
        // Reset to empty/defaults for new persona creation
        this.editingPersonaId = null;
        this.currentConfig = {
            name: '',
            age: 18,
            gender: 'divers',
            persona: 'KI',
            core_traits: [],
            knowledge: [],
            expression: 'normal',
            scenarios: [],
            start_msg_enabled: false,
            start_msg: '',
            background: ''
        };
        
        // Reset pending Avatar
        this.pendingAvatar = null;
        this._resetCreatorAvatarPreview();
        
        this._cleanupPersonaListeners();
        this.renderNameInput();
        this.renderPersonaTypeSelector();
        this.renderCoreTraitsTags();
        this.renderKnowledgeTags();
        this.renderExpressionTags();
        this.renderScenarioTags();
        this.updateScenarioVisibility();
        this.renderBackgroundInput();
        this.renderFirstMessageToggle();
    }

    // ===== API KEY SETTINGS =====
    openApiKeySettings() {
        this.dom.apiKeyInput.value = '';
        this.dom.apiKeyStatus.className = 'api-key-status';
        this.dom.apiKeyStatus.textContent = '';
        this.dom.saveApiKeyBtn.classList.add('hidden');
        this.dom.apiKeyOverlay.classList.remove('hidden');
    }
    
    closeApiKeySettings() {
        this.dom.apiKeyOverlay.classList.add('hidden');
        // Setze Focus zurück auf Message-Input
        setTimeout(() => {
            if (this.dom.messageInput) {
                this.dom.messageInput.focus();
            }
        }, 100);
    }
    
    async testApiKey() {
        const apiKey = this.dom.apiKeyInput.value.trim();
        
        if (!apiKey) {
            this.showApiKeyStatus('Bitte geben Sie einen API-Key ein', 'error');
            this.dom.saveApiKeyBtn.classList.add('hidden');
            return;
        }
        
        if (!apiKey.startsWith('sk-ant-api')) {
            this.showApiKeyStatus('Ungültiges API-Key Format. Key sollte mit "sk-ant-api" beginnen', 'error');
            this.dom.saveApiKeyBtn.classList.add('hidden');
            return;
        }
        
        this.dom.testApiKeyBtn.disabled = true;
        this.showApiKeyStatus('Teste API-Key...', 'loading');
        
        try {
            const response = await fetch('/api/test_api_key', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    api_key: apiKey,
                    api_model: UserSettings.get('apiModel') || UserSettings.getDefault('apiModel')
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showApiKeyStatus('✓ API-Key ist gültig! Sie können ihn jetzt speichern.', 'success');
                this.dom.saveApiKeyBtn.classList.remove('hidden');
                this.dom.saveApiKeyBtn.disabled = false;
            } else {
                this.showApiKeyStatus('✗ ' + (data.error || 'API-Key ist ungültig'), 'error');
                this.dom.saveApiKeyBtn.classList.add('hidden');
            }
        } catch (error) {
            console.error('Fehler beim Testen des API-Keys:', error);
            this.showApiKeyStatus('✗ Verbindungsfehler beim Testen', 'error');
            this.dom.saveApiKeyBtn.classList.add('hidden');
        } finally {
            this.dom.testApiKeyBtn.disabled = false;
        }
    }
    
    async saveApiKey() {
        const apiKey = this.dom.apiKeyInput.value.trim();
        
        this.dom.saveApiKeyBtn.disabled = true;
        this.showApiKeyStatus('Speichere API-Key...', 'loading');
        
        try {
            const response = await fetch('/api/save_api_key', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ api_key: apiKey })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showApiKeyStatus('✓ API-Key erfolgreich gespeichert!', 'success');
                // Warte kurz, dann aktualisiere den Status und lade die Seite neu
                setTimeout(async () => {
                    await this.checkApiStatus();
                    this.closeApiKeySettings();
                    // Seite neu laden, damit der API-Client aktiv wird
                    window.location.reload();
                }, 1000);
            } else {
                this.showApiKeyStatus('✗ ' + (data.error || 'Fehler beim Speichern'), 'error');
                this.dom.saveApiKeyBtn.disabled = false;
            }
        } catch (error) {
            console.error('Fehler beim Speichern des API-Keys:', error);
            this.showApiKeyStatus('✗ Verbindungsfehler beim Speichern', 'error');
            this.dom.saveApiKeyBtn.disabled = false;
        }
    }
    
    showApiKeyStatus(message, type) {
        this.dom.apiKeyStatus.className = `api-key-status show ${type}`;
        this.dom.apiKeyStatus.textContent = message;
    }

    async checkApiStatus() {
        const indicator = document.getElementById('api-status-indicator');
        if (!indicator) return;
        
        try {
            const response = await fetch('/api/check_api_status');
            const data = await response.json();
            
            if (data.has_api_key) {
                indicator.classList.remove('disconnected');
                indicator.classList.add('connected');
                indicator.title = 'Bestätigter API Zugang';
            } else {
                indicator.classList.remove('connected');
                indicator.classList.add('disconnected');
                indicator.title = 'API Zugang benötigt';
            }
        } catch (error) {
            console.error('Fehler beim Prüfen des API-Status:', error);
            indicator.classList.remove('connected');
            indicator.classList.add('disconnected');
            indicator.title = 'API Zugang benötigt';
        }
    }

    // ===== INTERFACE SETTINGS =====
    openInterfaceSettings() {
        // Dark Mode
        const darkMode = UserSettings.get('darkMode', UserSettings.getDefault('darkMode', false));
        document.getElementById('dark-mode-toggle').checked = darkMode;
        document.getElementById('dark-mode-label').textContent = darkMode ? 'Dunkel' : 'Hell';
        
        // Dynamic Background
        const dynamicBg = UserSettings.get('dynamicBackground', UserSettings.getDefault('dynamicBackground', true));
        document.getElementById('dynamic-bg-toggle').checked = dynamicBg;
        document.getElementById('dynamic-bg-label').textContent = dynamicBg ? 'Aktiv' : 'Inaktiv';
        
        // Load colors based on current mode
        this.loadColorsForMode(darkMode);
        
        const nonverbalColor = UserSettings.get('nonverbalColor', UserSettings.getDefault('nonverbalColor', '#e4ba00'));
        document.getElementById('nonverbal-color').value = nonverbalColor;
        document.getElementById('nonverbal-color-text').value = nonverbalColor;
        this.updatePreviewNonverbalColor(nonverbalColor);
        
        const bubbleFontSize = UserSettings.get('bubbleFontSize', UserSettings.getDefault('bubbleFontSize', '18'));
        document.getElementById('bubble-font-size').value = bubbleFontSize;
        document.getElementById('bubble-font-size-number').value = bubbleFontSize;
        document.getElementById('font-size-display').textContent = bubbleFontSize + 'px';
        this.updateFontSizePreview(bubbleFontSize);
        
        const bubbleFontFamily = UserSettings.get('bubbleFontFamily', UserSettings.getDefault('bubbleFontFamily', 'ubuntu'));
        const fontRadio = document.querySelector(`input[name="bubble-font-family"][value="${bubbleFontFamily}"]`);
        if (fontRadio) fontRadio.checked = true;
        this.updateFontFamilyPreview(bubbleFontFamily);
        
        this.setupColorSync();
        this.setupToggleSync();
        this.setupFontSizeSync();
        this.setupFontFamilySync();
        
        // Initialize preview with current colors
        this.updatePreviewColors();
        this.updatePreviewDynamicBg(dynamicBg);
        this.updatePreviewDarkMode(darkMode);
        
        this.dom.interfaceSettingsOverlay.classList.remove('hidden');
    }
    
    closeInterfaceSettings() {
        this.dom.interfaceSettingsOverlay.classList.add('hidden');
    }
    
    loadColorsForMode(darkMode) {
        const mode = darkMode ? 'dark' : 'light';
        
        const defaults = {
            bg: UserSettings.getDefault(`backgroundColor_${mode}`),
            gradient1: UserSettings.getDefault(`colorGradient1_${mode}`),
            color2: UserSettings.getDefault(`color2_${mode}`)
        };
        
        const backgroundColor = UserSettings.get(`backgroundColor_${mode}`, defaults.bg);
        document.getElementById('background-color').value = backgroundColor;
        document.getElementById('background-color-text').value = backgroundColor;
        
        const colorGradient1 = UserSettings.get(`colorGradient1_${mode}`, defaults.gradient1);
        document.getElementById('color-gradient1').value = colorGradient1;
        document.getElementById('color-gradient1-text').value = colorGradient1;
        
        const color2 = UserSettings.get(`color2_${mode}`, defaults.color2);
        document.getElementById('color-2').value = color2;
        document.getElementById('color-2-text').value = color2;
        
        this.updatePreviewColors();
    }
    
    setupToggleSync() {
        const darkModeToggle = document.getElementById('dark-mode-toggle');
        const darkModeLabel = document.getElementById('dark-mode-label');
        
        darkModeToggle.addEventListener('change', (e) => {
            const isDark = e.target.checked;
            darkModeLabel.textContent = isDark ? 'Dunkel' : 'Hell';
            this.updatePreviewDarkMode(isDark);
            // Load colors for the new mode
            this.loadColorsForMode(isDark);
        });
        
        const dynamicBgToggle = document.getElementById('dynamic-bg-toggle');
        const dynamicBgLabel = document.getElementById('dynamic-bg-label');
        
        dynamicBgToggle.addEventListener('change', (e) => {
            dynamicBgLabel.textContent = e.target.checked ? 'Aktiv' : 'Inaktiv';
            this.updatePreviewDynamicBg(e.target.checked);
        });
    }
    
    setupColorSync() {
        // Background Color (Color 1)
        const colorPicker = document.getElementById('background-color');
        const colorText = document.getElementById('background-color-text');
        
        colorPicker.addEventListener('input', (e) => {
            colorText.value = e.target.value;
            this.updatePreviewColors();
        });
        
        colorText.addEventListener('input', (e) => {
            const value = e.target.value.trim();
            if (/^#[0-9A-Fa-f]{6}$/.test(value)) {
                colorPicker.value = value;
                this.updatePreviewColors();
            }
        });
        
        // Color Gradient 1 (Rosa)
        const gradient1Picker = document.getElementById('color-gradient1');
        const gradient1Text = document.getElementById('color-gradient1-text');
        
        gradient1Picker.addEventListener('input', (e) => {
            gradient1Text.value = e.target.value;
            this.updatePreviewColors();
        });
        
        gradient1Text.addEventListener('input', (e) => {
            const value = e.target.value.trim();
            if (/^#[0-9A-Fa-f]{6}$/.test(value)) {
                gradient1Picker.value = value;
                this.updatePreviewColors();
            }
        });
        
        // Color 2 (Sky Blue)
        const color2Picker = document.getElementById('color-2');
        const color2Text = document.getElementById('color-2-text');
        
        color2Picker.addEventListener('input', (e) => {
            color2Text.value = e.target.value;
            this.updatePreviewColors();
        });
        
        color2Text.addEventListener('input', (e) => {
            const value = e.target.value.trim();
            if (/^#[0-9A-Fa-f]{6}$/.test(value)) {
                color2Picker.value = value;
                this.updatePreviewColors();
            }
        });
        
        // Nonverbal Color
        const nonverbalPicker = document.getElementById('nonverbal-color');
        const nonverbalText = document.getElementById('nonverbal-color-text');
        
        nonverbalPicker.addEventListener('input', (e) => {
            nonverbalText.value = e.target.value;
            this.updatePreviewNonverbalColor(e.target.value);
        });
        
        nonverbalText.addEventListener('input', (e) => {
            const value = e.target.value.trim();
            if (/^#[0-9A-Fa-f]{6}$/.test(value)) {
                nonverbalPicker.value = value;
                this.updatePreviewNonverbalColor(value);
            }
        });
    }
    
    updatePreviewColors() {
        const bg = document.getElementById('background-color').value;
        const gradient1 = document.getElementById('color-gradient1').value;
        const color2 = document.getElementById('color-2').value;
        
        const previewBg = document.getElementById('preview-background');
        const blob1 = document.getElementById('preview-blob-1');
        const blob2 = document.getElementById('preview-blob-2');
        
        if (previewBg) previewBg.style.backgroundColor = bg;
        if (blob1) blob1.style.background = gradient1;
        if (blob2) blob2.style.background = color2;
    }
    
    updatePreviewDynamicBg(enabled) {
        const blob1 = document.getElementById('preview-blob-1');
        const blob2 = document.getElementById('preview-blob-2');
        if (blob1) blob1.style.display = enabled ? 'block' : 'none';
        if (blob2) blob2.style.display = enabled ? 'block' : 'none';
    }
    
    updatePreviewDarkMode(enabled) {
        const previewBg = document.getElementById('preview-background');
        const previewBubble = document.querySelector('.preview-bubble');
        
        if (previewBg) {
            if (enabled) {
                previewBg.classList.add('dark-preview');
            } else {
                previewBg.classList.remove('dark-preview');
            }
        }
        
        // Explizit die Bubble-Styles setzen um sicherzustellen dass sie sich ändern
        if (previewBubble) {
            if (enabled) {
                previewBubble.style.background = 'rgba(30, 30, 40, 0.5)';
                previewBubble.style.color = 'white';
                previewBubble.style.border = '1px solid rgba(255, 255, 255, 0.25)';
                previewBubble.style.boxShadow = '0 8px 20px rgba(0, 0, 0, 0.15), inset 0 1px 2px rgba(255, 255, 255, 0.1)';
            } else {
                previewBubble.style.background = 'rgba(255, 255, 255, 0.65)';
                previewBubble.style.color = '#1a1a1a';
                previewBubble.style.border = '1px solid rgba(255, 255, 255, 0.9)';
                previewBubble.style.boxShadow = '0 4px 15px rgba(0, 0, 0, 0.08)';
            }
        }
    }
    
    updatePreviewNonverbalColor(color) {
        const previewNonverbal = document.querySelector('.preview-nonverbal');
        if (previewNonverbal) {
            previewNonverbal.style.color = color;
        }
    }
    
    setupFontSizeSync() {
        const slider = document.getElementById('bubble-font-size');
        const numberInput = document.getElementById('bubble-font-size-number');
        const display = document.getElementById('font-size-display');
        
        slider.addEventListener('input', (e) => {
            const value = e.target.value;
            numberInput.value = value;
            display.textContent = value + 'px';
            this.updateFontSizePreview(value);
        });
        
        numberInput.addEventListener('input', (e) => {
            let value = parseInt(e.target.value);
            if (value < 14) value = 14;
            if (value > 28) value = 28;
            if (!isNaN(value)) {
                slider.value = value;
                numberInput.value = value;
                display.textContent = value + 'px';
                this.updateFontSizePreview(value);
            }
        });
    }
    
    updateFontSizePreview(fontSize) {
        const previewBubble = document.querySelector('.preview-bubble');
        if (previewBubble) {
            previewBubble.style.fontSize = fontSize + 'px';
        }
    }
    
    setupFontFamilySync() {
        const fontRadios = document.querySelectorAll('input[name="bubble-font-family"]');
        fontRadios.forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.updateFontFamilyPreview(e.target.value);
            });
        });
    }
    
    updateFontFamilyPreview(fontFamily) {
        const previewBubble = document.querySelector('.preview-bubble');
        if (!previewBubble) return;
        
        let fontFamilyValue;
        switch(fontFamily) {
            case 'ubuntu':
                fontFamilyValue = "'Ubuntu', 'Roboto', 'Segoe UI', system-ui, -apple-system, sans-serif";
                break;
            case 'comic':
                fontFamilyValue = "'Comic Sans MS', 'Comic Sans', cursive";
                break;
            case 'times':
                fontFamilyValue = "'Times New Roman', Times, serif";
                break;
            case 'courier':
                fontFamilyValue = "'Courier New', Courier, monospace";
                break;
            default:
                fontFamilyValue = "'Ubuntu', 'Roboto', 'Segoe UI', system-ui, -apple-system, sans-serif";
        }
        previewBubble.style.fontFamily = fontFamilyValue;
    }
    
    saveInterfaceSettings() {
        const darkMode = document.getElementById('dark-mode-toggle').checked;
        this.applyDarkMode(darkMode);
        
        const dynamicBg = document.getElementById('dynamic-bg-toggle').checked;
        this.applyDynamicBackground(dynamicBg);
        
        const mode = darkMode ? 'dark' : 'light';
        
        const backgroundColor = document.getElementById('background-color').value;
        this.applyBackgroundColor(backgroundColor, mode);
        
        const colorGradient1 = document.getElementById('color-gradient1').value;
        this.applyColorGradient1(colorGradient1, mode);
        
        const color2 = document.getElementById('color-2').value;
        this.applyColor2(color2, mode);
        
        const nonverbalColor = document.getElementById('nonverbal-color').value;
        this.applyNonverbalColor(nonverbalColor);
        
        const bubbleFontSize = document.getElementById('bubble-font-size').value;
        this.applyBubbleFontSize(bubbleFontSize);
        
        const bubbleFontFamily = document.querySelector('input[name="bubble-font-family"]:checked').value;
        this.applyBubbleFontFamily(bubbleFontFamily);
        
        alert('Interface-Einstellungen wurden gespeichert!');
        this.closeInterfaceSettings();
    }
    
    resetInterfaceSettings() {
        if (!confirm('Möchtest du die Interface-Einstellungen auf die Standardwerte zurücksetzen?')) {
            return;
        }
        
        const defaultDarkMode = false;
        const defaultDynamicBg = true;
        
        // Light mode defaults
        const defaultBackgroundColor = '#a3baff';
        const defaultColorGradient1 = '#66cfff';
        const defaultColor2 = '#fd91ee';
        
        // Dark mode defaults
        const defaultBackgroundColorDark = '#1a2332';
        const defaultColorGradient1Dark = '#2a3f5f';
        const defaultColor2Dark = '#3d4f66';
        const defaultNonverbalColor = '#e4ba00';
        const defaultBubbleFontSize = '18';
        const defaultBubbleFontFamily = 'ubuntu';
        
        this.applyDarkMode(defaultDarkMode);
        this.applyDynamicBackground(defaultDynamicBg);
        
        // Reset both light and dark mode colors
        this.applyBackgroundColor(defaultBackgroundColor, 'light');
        this.applyColorGradient1(defaultColorGradient1, 'light');
        this.applyColor2(defaultColor2, 'light');
        
        this.applyBackgroundColor(defaultBackgroundColorDark, 'dark');
        this.applyColorGradient1(defaultColorGradient1Dark, 'dark');
        this.applyColor2(defaultColor2Dark, 'dark');
        
        // Apply current mode colors to UI
        this.applyCurrentModeColors();
        this.applyNonverbalColor(defaultNonverbalColor);
        this.applyBubbleFontSize(defaultBubbleFontSize);
        this.applyBubbleFontFamily(defaultBubbleFontFamily);
        
        document.getElementById('dark-mode-toggle').checked = defaultDarkMode;
        document.getElementById('dark-mode-label').textContent = defaultDarkMode ? 'Dunkel' : 'Hell';
        document.getElementById('dynamic-bg-toggle').checked = defaultDynamicBg;
        document.getElementById('dynamic-bg-label').textContent = defaultDynamicBg ? 'Aktiv' : 'Inaktiv';
        document.getElementById('background-color').value = defaultBackgroundColor;
        document.getElementById('background-color-text').value = defaultBackgroundColor;
        document.getElementById('color-gradient1').value = defaultColorGradient1;
        document.getElementById('color-gradient1-text').value = defaultColorGradient1;
        document.getElementById('color-2').value = defaultColor2;
        document.getElementById('color-2-text').value = defaultColor2;
        document.getElementById('nonverbal-color').value = defaultNonverbalColor;
        document.getElementById('nonverbal-color-text').value = defaultNonverbalColor;
        document.getElementById('bubble-font-size').value = defaultBubbleFontSize;
        document.getElementById('bubble-font-size-number').value = defaultBubbleFontSize;
        document.getElementById('font-size-display').textContent = defaultBubbleFontSize + 'px';
        const fontRadio = document.querySelector(`input[name="bubble-font-family"][value="${defaultBubbleFontFamily}"]`);
        if (fontRadio) fontRadio.checked = true;
        this.updateFontSizePreview(defaultBubbleFontSize);
        this.updateFontFamilyPreview(defaultBubbleFontFamily);
        
        alert('Interface-Einstellungen wurden zurückgesetzt!');
    }

    applyDarkMode(darkMode) {
        document.body.classList.toggle('dark-mode', darkMode);
        document.documentElement.classList.remove('dark-mode-early');
        UserSettings.set('darkMode', darkMode);
        // Load colors for the new mode
        this.applyCurrentModeColors();
    }
    
    applyDynamicBackground(enabled) {
        const dynamicBg = document.querySelector('.dynamic-background');
        if (dynamicBg) {
            dynamicBg.style.display = enabled ? 'block' : 'none';
        }
        UserSettings.set('dynamicBackground', enabled);
    }

    applyBackgroundColor(color, mode) {
        if (mode) {
            UserSettings.set(`backgroundColor_${mode}`, color);
        }
        document.documentElement.style.setProperty('--color-white', color);
        const dynamicBg = document.querySelector('.dynamic-background');
        if (dynamicBg) {
            dynamicBg.style.background = color;
        }
    }
    
    applyColorGradient1(color, mode) {
        if (mode) {
            UserSettings.set(`colorGradient1_${mode}`, color);
        }
        document.documentElement.style.setProperty('--color-gradient1', color);
    }
    
    applyColor2(color, mode) {
        if (mode) {
            UserSettings.set(`color2_${mode}`, color);
        }
        document.documentElement.style.setProperty('--color-sky', color);
    }
    
    applyCurrentModeColors() {
        const darkMode = document.body.classList.contains('dark-mode');
        const mode = darkMode ? 'dark' : 'light';
        
        const defaults = {
            bg: UserSettings.getDefault(`backgroundColor_${mode}`),
            gradient1: UserSettings.getDefault(`colorGradient1_${mode}`),
            color2: UserSettings.getDefault(`color2_${mode}`)
        };
        
        const backgroundColor = UserSettings.get(`backgroundColor_${mode}`, defaults.bg);
        const colorGradient1 = UserSettings.get(`colorGradient1_${mode}`, defaults.gradient1);
        const color2 = UserSettings.get(`color2_${mode}`, defaults.color2);
        
        this.applyBackgroundColor(backgroundColor, null);
        this.applyColorGradient1(colorGradient1, null);
        this.applyColor2(color2, null);
    }
    
    applyNonverbalColor(color) {
        document.documentElement.style.setProperty('--nonverbal-color', color);
        UserSettings.set('nonverbalColor', color);
    }
    
    applyBubbleFontSize(fontSize) {
        document.documentElement.style.setProperty('--bubble-font-size', fontSize + 'px');
        UserSettings.set('bubbleFontSize', fontSize);
    }
    
    applyBubbleFontFamily(fontFamily) {
        let fontFamilyValue;
        switch(fontFamily) {
            case 'ubuntu':
                fontFamilyValue = "'Ubuntu', 'Roboto', 'Segoe UI', system-ui, -apple-system, sans-serif";
                break;
            case 'comic':
                fontFamilyValue = "'Comic Sans MS', 'Comic Sans', cursive";
                break;
            case 'times':
                fontFamilyValue = "'Times New Roman', Times, serif";
                break;
            case 'courier':
                fontFamilyValue = "'Courier New', Courier, monospace";
                break;
            default:
                fontFamilyValue = "'Ubuntu', 'Roboto', 'Segoe UI', system-ui, -apple-system, sans-serif";
        }
        document.documentElement.style.setProperty('--bubble-font-family', fontFamilyValue);
        UserSettings.set('bubbleFontFamily', fontFamily);
    }

    // ===== API SETTINGS =====
    openApiSettings() {
        const apiModelSelect = document.getElementById('api-model');
        const apiModelOptions = UserSettings.getDefault('apiModelOptions', []);
        const currentModel = UserSettings.get('apiModel') || UserSettings.getDefault('apiModel');
        this._populateApiModelOptions(apiModelSelect, apiModelOptions, currentModel);
        
        const apiTemperature = UserSettings.get(
            'apiTemperature',
            UserSettings.getDefault('apiTemperature')
        );
        document.getElementById('api-temperature').value = apiTemperature;
        document.getElementById('temperature-display').textContent = apiTemperature;
        
        const contextLimit = UserSettings.get(
            'contextLimit',
            UserSettings.getDefault('contextLimit')
        );
        document.getElementById('context-limit').value = contextLimit;
        document.getElementById('context-limit-display').textContent = contextLimit;
        
        // Nachgedanke Toggle laden
        const nachgedankeEnabled = UserSettings.get('nachgedankeEnabled', UserSettings.getDefault('nachgedankeEnabled', false));
        const nachgedankeToggle = document.getElementById('nachgedanke-toggle');
        if (nachgedankeToggle) {
            nachgedankeToggle.checked = nachgedankeEnabled;
            this._updateNachgedankeLabels(nachgedankeEnabled);
        }
        
        this.setupSliderSync();
        this.dom.apiSettingsOverlay.classList.remove('hidden');
    }
    
    closeApiSettings() {
        this.dom.apiSettingsOverlay.classList.add('hidden');
    }
    
    setupSliderSync() {
        const tempSlider = document.getElementById('api-temperature');
        const tempDisplay = document.getElementById('temperature-display');
        
        tempSlider.addEventListener('input', (e) => {
            const value = parseFloat(e.target.value).toFixed(1);
            tempDisplay.textContent = value;
        });
        
        const contextSlider = document.getElementById('context-limit');
        const contextDisplay = document.getElementById('context-limit-display');
        
        contextSlider.addEventListener('input', (e) => {
            const value = e.target.value;
            contextDisplay.textContent = value;
        });
        
        // Nachgedanke Toggle Sync
        const nachgedankeToggle = document.getElementById('nachgedanke-toggle');
        if (nachgedankeToggle) {
            nachgedankeToggle.addEventListener('change', () => {
                this._updateNachgedankeLabels(nachgedankeToggle.checked);
            });
        }
    }
    
    _updateNachgedankeLabels(enabled) {
        const offLabel = document.querySelector('.nachgedanke-off-label');
        const onLabel = document.querySelector('.nachgedanke-on-label');
        if (offLabel) offLabel.classList.toggle('active', !enabled);
        if (onLabel) onLabel.classList.toggle('active', enabled);
    }
    
    saveApiSettings() {
        const apiModel = document.getElementById('api-model').value;
        const apiTemperature = document.getElementById('api-temperature').value;
        const contextLimit = document.getElementById('context-limit').value;
        
        UserSettings.setMany({
            apiModel: apiModel,
            apiTemperature: apiTemperature,
            contextLimit: contextLimit
        });
        
        // Nachgedanke Toggle speichern
        const nachgedankeToggle = document.getElementById('nachgedanke-toggle');
        if (nachgedankeToggle) {
            UserSettings.set('nachgedankeEnabled', nachgedankeToggle.checked);
        }
        
        alert('API-Einstellungen wurden gespeichert!');
        this.closeApiSettings();
    }
    
    resetApiSettings() {
        if (!confirm('Möchtest du die API-Einstellungen auf die Standardwerte zurücksetzen?')) {
            return;
        }
        
        const defaultModel = UserSettings.getDefault('apiModel');
        const defaultTemperature = UserSettings.getDefault('apiTemperature');
        const defaultContextLimit = UserSettings.getDefault('contextLimit');
        
        UserSettings.setMany({
            apiModel: defaultModel,
            apiTemperature: defaultTemperature,
            contextLimit: defaultContextLimit,
            nachgedankeEnabled: false
        });
        
        document.getElementById('api-model').value = defaultModel || '';
        document.getElementById('api-temperature').value = defaultTemperature;
        document.getElementById('temperature-display').textContent = defaultTemperature;
        document.getElementById('context-limit').value = defaultContextLimit;
        document.getElementById('context-limit-display').textContent = defaultContextLimit;
        
        const nachgedankeToggle = document.getElementById('nachgedanke-toggle');
        if (nachgedankeToggle) {
            nachgedankeToggle.checked = false;
            this._updateNachgedankeLabels(false);
        }
        
        alert('API-Einstellungen wurden zurückgesetzt!');
    }

    _populateApiModelOptions(selectEl, options, selectedValue) {
        if (!selectEl) return;
        selectEl.innerHTML = '';
        if (!Array.isArray(options)) return;

        options.forEach((option) => {
            if (!option || !option.value) return;
            const opt = document.createElement('option');
            opt.value = option.value;
            opt.textContent = option.label || option.value;
            if (selectedValue && option.value === selectedValue) {
                opt.selected = true;
            }
            selectEl.appendChild(opt);
        });
    }

    // ===== SERVER SETTINGS =====
    async openServerSettings() {
        this.setupServerModeHandlers();
        this.setupAccessControlToggle();
        await this.loadServerSettings();
        await this.loadAccessControlStatus();
        this.dom.serverSettingsOverlay.classList.remove('hidden');
    }
    
    closeServerSettings() {
        this.dom.serverSettingsOverlay.classList.add('hidden');
    }
    
    async loadServerSettings() {
        try {
            const response = await fetch('/api/get_server_settings');
            const data = await response.json();
            
            if (data.success) {
                const serverMode = data.server_mode || 'local';
                document.getElementById('server-mode').value = serverMode;
            }
        } catch (error) {
            console.error('Fehler beim Laden der Server-Einstellungen:', error);
        }
    }
    
    async loadAccessControlStatus() {
        try {
            const response = await fetch('/api/access/lists');
            const data = await response.json();
            
            if (data.success) {
                const checkbox = document.getElementById('access-control-enabled');
                if (checkbox) {
                    checkbox.checked = data.access_control_enabled !== false;
                }
            }
        } catch (error) {
            console.error('Fehler beim Laden des Zugangskontrolle-Status:', error);
        }
    }
    
    setupAccessControlToggle() {
        const checkbox = document.getElementById('access-control-enabled');
        if (!checkbox) return;
        
        // Remove old listener
        const newCheckbox = checkbox.cloneNode(true);
        checkbox.parentNode.replaceChild(newCheckbox, checkbox);
        
        newCheckbox.addEventListener('change', async (e) => {
            try {
                const response = await fetch('/api/access/toggle', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ enabled: e.target.checked })
                });
                const data = await response.json();
                
                if (!data.success) {
                    e.target.checked = !e.target.checked; // Revert
                    alert('Fehler: ' + data.error);
                }
            } catch (error) {
                e.target.checked = !e.target.checked; // Revert
                console.error('Fehler beim Umschalten der Zugangskontrolle:', error);
            }
        });
    }

    
    setupServerModeHandlers() {
        const serverModeSelect = document.getElementById('server-mode');
        
        // Remove old listeners
        const newServerModeSelect = serverModeSelect.cloneNode(true);
        serverModeSelect.parentNode.replaceChild(newServerModeSelect, serverModeSelect);
        
        // Keine zusätzliche Logik mehr nötig - QR-Code wird über separates Overlay angezeigt
    }
    
    async saveServerSettings() {
        const serverMode = document.getElementById('server-mode').value;
        
        if (!confirm('Der Server-Modus wird geändert und der Server neu gestartet.\n\nFortfahren?')) {
            return;
        }
        
        try {
            const response = await fetch('/api/save_and_restart_server', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    server_mode: serverMode
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Show restart message
                const overlay = document.createElement('div');
                overlay.style.cssText = `
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.9);
                    z-index: 10000;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-size: 20px;
                    text-align: center;
                `;
                overlay.innerHTML = `
                    <div>
                        <div style="font-size: 48px; margin-bottom: 20px;">🔄</div>
                        <div>Server wird neu gestartet...</div>
                        <div style="font-size: 14px; margin-top: 10px; opacity: 0.7;">Die Seite wird automatisch neu geladen</div>
                    </div>
                `;
                document.body.appendChild(overlay);
                
                // Wait for server to restart and reload
                setTimeout(() => {
                    this.waitForServerAndReload();
                }, 2000);
            } else {
                alert('Fehler beim Speichern: ' + (data.error || 'Unbekannter Fehler'));
            }
        } catch (error) {
            console.error('Fehler beim Speichern der Server-Einstellungen:', error);
            alert('Fehler beim Speichern der Server-Einstellungen.');
        }
    }
    
    async waitForServerAndReload() {
        let attempts = 0;
        const maxAttempts = 30; // 30 Sekunden warten
        
        const checkServer = async () => {
            try {
                const response = await fetch('/api/check_api_status', {
                    cache: 'no-cache',
                    headers: { 'Cache-Control': 'no-cache' }
                });
                if (response.ok) {
                    // Server ist wieder online
                    // Lade zur Hauptseite oder Login-Seite um (je nach Auth-Status)
                    window.location.href = '/';
                    return true;
                }
            } catch (error) {
                // Server noch nicht erreichbar
            }
            
            attempts++;
            if (attempts < maxAttempts) {
                setTimeout(checkServer, 1000);
            } else {
                // Nach 30 Sekunden: Gib Hinweis und versuche trotzdem neu zu laden
                const overlay = document.querySelector('[style*="z-index: 10000"]');
                if (overlay) {
                    overlay.innerHTML = `
                        <div>
                            <div style="font-size: 48px; margin-bottom: 20px;">⚠️</div>
                            <div>Server-Neustart dauert länger als erwartet</div>
                            <div style="font-size: 14px; margin-top: 20px;">
                                <button onclick="window.location.href='/'" style="
                                    padding: 12px 24px;
                                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                    border: none;
                                    border-radius: 8px;
                                    color: white;
                                    font-size: 14px;
                                    cursor: pointer;
                                    font-weight: 600;
                                ">Seite neu laden</button>
                            </div>
                        </div>
                    `;
                }
            }
        };
        
        checkServer();
    }

    loadSavedSettings() {
        // Dark Mode
        const darkMode = UserSettings.get('darkMode', UserSettings.getDefault('darkMode', false));
        if (darkMode) {
            document.body.classList.add('dark-mode');
        }
        
        // Dynamic Background
        const dynamicBg = UserSettings.get('dynamicBackground', UserSettings.getDefault('dynamicBackground', true));
        this.applyDynamicBackground(dynamicBg);
        
        // Load colors for current mode
        this.applyCurrentModeColors();
        
        const savedNonverbalColor = UserSettings.get('nonverbalColor');
        if (savedNonverbalColor) {
            this.applyNonverbalColor(savedNonverbalColor);
        }
        
        const savedBubbleFontSize = UserSettings.get('bubbleFontSize');
        if (savedBubbleFontSize) {
            this.applyBubbleFontSize(savedBubbleFontSize);
        }
        
        const savedBubbleFontFamily = UserSettings.get('bubbleFontFamily');
        if (savedBubbleFontFamily) {
            this.applyBubbleFontFamily(savedBubbleFontFamily);
        }
        
        // Hintergrund sichtbar machen nachdem alle Farben geladen sind
        const dynamicBgEl = document.querySelector('.dynamic-background');
        if (dynamicBgEl) {
            dynamicBgEl.classList.add('colors-loaded');
        }
        // dark-mode-early entfernen falls nicht im Dark Mode
        document.documentElement.classList.remove('dark-mode-early');
    }
}
