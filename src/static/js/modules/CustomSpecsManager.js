/**
 * CustomSpecsManager - Manages custom persona specifications
 * Allows users to create their own persona types, traits, knowledge areas, scenarios, and expression styles
 */
export class CustomSpecsManager {
    constructor(dom) {
        this.dom = dom;
        this.customSpecs = null;
        this.activeCategory = 'persona-type';
        this.settingsManager = null; // Wird von chat.js gesetzt
    }

    /**
     * Aktualisiert den Persona Creator nach Änderungen an Custom Specs
     */
    async _refreshPersonaCreator() {
        if (this.settingsManager) {
            await this.settingsManager.refreshAvailableOptions();
        }
    }

    // ===== OVERLAY =====
    async openCustomSpecs() {
        try {
            const response = await fetch('/api/custom-specs');
            const data = await response.json();
            
            if (data.success) {
                this.customSpecs = data.specs;
            } else {
                this.customSpecs = { persona_spec: { persona_type: {}, core_traits_details: {}, knowledge_areas: {}, expression_styles: {}, scenarios: {} } };
            }
            
            this.activeCategory = 'persona-type';
            this._renderCategoryButtons();
            this._showFrame('persona-type');
            this._renderAllExistingItems();
            this._setupInputListeners();
            
            const overlay = document.getElementById('custom-specs-overlay');
            if (overlay) overlay.classList.remove('hidden');
        } catch (error) {
            console.error('Fehler beim Laden der Custom Specs:', error);
            alert('Verbindungsfehler beim Laden der Custom Specs');
        }
    }

    closeCustomSpecs() {
        const overlay = document.getElementById('custom-specs-overlay');
        if (overlay) overlay.classList.add('hidden');
    }

    // ===== CATEGORY SWITCHING =====
    _renderCategoryButtons() {
        const buttons = document.querySelectorAll('.custom-specs-cat-btn');
        buttons.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.category === this.activeCategory);
            
            // Remove old listeners by cloning
            const newBtn = btn.cloneNode(true);
            btn.parentNode.replaceChild(newBtn, btn);
            
            newBtn.addEventListener('click', () => {
                this.activeCategory = newBtn.dataset.category;
                this._renderCategoryButtons();
                this._showFrame(newBtn.dataset.category);
            });
        });
    }

    _showFrame(category) {
        document.querySelectorAll('.custom-specs-frame').forEach(frame => {
            frame.classList.remove('active');
        });
        const targetFrame = document.getElementById(`cs-frame-${category}`);
        if (targetFrame) {
            targetFrame.classList.add('active');
        }
    }

    // ===== INPUT LISTENERS =====
    _setupInputListeners() {
        // Char count for persona type description
        const typeDesc = document.getElementById('cs-type-description');
        const typeCount = document.getElementById('cs-type-desc-count');
        if (typeDesc && typeCount) {
            typeDesc.addEventListener('input', () => {
                typeCount.textContent = `${typeDesc.value.length}/120`;
            });
        }

        // AI Auto-Fill buttons
        document.querySelectorAll('.cs-ai-btn').forEach(btn => {
            const newBtn = btn.cloneNode(true);
            btn.parentNode.replaceChild(newBtn, btn);
            
            newBtn.addEventListener('click', () => this._handleAutoFill(newBtn));
        });

        // Create buttons
        this._setupCreateButton('cs-create-persona-type', () => this._createPersonaType());
        this._setupCreateButton('cs-create-core-trait', () => this._createCoreTrait());
        this._setupCreateButton('cs-create-knowledge', () => this._createKnowledge());
        this._setupCreateButton('cs-create-scenario', () => this._createScenario());
        this._setupCreateButton('cs-create-expression-style', () => this._createExpressionStyle());
    }

    _setupCreateButton(id, handler) {
        const btn = document.getElementById(id);
        if (btn) {
            const newBtn = btn.cloneNode(true);
            btn.parentNode.replaceChild(newBtn, btn);
            newBtn.addEventListener('click', handler);
        }
    }

    // ===== AI AUTO-FILL =====
    async _handleAutoFill(btn) {
        const aiType = btn.dataset.aiType;
        const sourceId = btn.dataset.aiSource;
        const targetId = btn.dataset.aiTarget;
        
        const sourceInput = document.getElementById(sourceId);
        if (!sourceInput || !sourceInput.value.trim()) {
            alert('Bitte gib zuerst einen Namen ein, damit die KI weiß, was sie generieren soll.');
            return;
        }
        
        const inputText = sourceInput.value.trim();
        
        // Loading state
        btn.classList.add('loading');
        
        try {
            const response = await fetch('/api/custom-specs/autofill', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ type: aiType, input: inputText })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this._applyAutoFillResult(aiType, targetId, data.result);
                
                // Show token info
                if (data.tokens) {
                    const totalTokens = (data.tokens.input || 0) + (data.tokens.output || 0);
                    const estimatedCost = ((data.tokens.input || 0) * 0.000003 + (data.tokens.output || 0) * 0.000015).toFixed(6);
                    console.log(`Auto-Fill Tokens: ${totalTokens} (Input: ${data.tokens.input}, Output: ${data.tokens.output}) | ~$${estimatedCost}`);
                }
            } else {
                alert('Auto-Fill Fehler: ' + (data.error || 'Unbekannt'));
            }
        } catch (error) {
            console.error('Auto-Fill Fehler:', error);
            alert('Verbindungsfehler bei Auto-Fill');
        } finally {
            btn.classList.remove('loading');
        }
    }

    _applyAutoFillResult(aiType, targetId, result) {
        if (aiType === 'persona_type' || aiType === 'knowledge') {
            // Simple text result
            const target = document.getElementById(targetId);
            if (target) {
                target.value = typeof result === 'string' ? result : JSON.stringify(result);
                target.dispatchEvent(new Event('input'));
            }
        } else if (aiType === 'core_trait' && targetId === 'cs-trait-full') {
            // JSON result with description + behaviors
            if (typeof result === 'object') {
                const descInput = document.getElementById('cs-trait-description');
                if (descInput && result.description) descInput.value = result.description;
                
                const behaviors = result.behaviors || [];
                for (let i = 0; i < 3; i++) {
                    const input = document.getElementById(`cs-trait-behavior-${i + 1}`);
                    if (input && behaviors[i]) input.value = behaviors[i];
                }
            }
        } else if (aiType === 'scenario' && targetId === 'cs-scenario-full') {
            // JSON result with name, description, setting
            if (typeof result === 'object') {
                const nameInput = document.getElementById('cs-scenario-name');
                const descInput = document.getElementById('cs-scenario-description');
                if (nameInput && result.name) nameInput.value = result.name;
                if (descInput && result.description) descInput.value = result.description;
                
                const settings = result.setting || [];
                for (let i = 0; i < 4; i++) {
                    const input = document.getElementById(`cs-scenario-setting-${i + 1}`);
                    if (input && settings[i]) input.value = settings[i];
                }
            }
        } else if (aiType === 'expression_style' && targetId === 'cs-expression-full') {
            // JSON result with name, description, example, characteristics
            if (typeof result === 'object') {
                const nameInput = document.getElementById('cs-expression-name');
                const descInput = document.getElementById('cs-expression-description');
                const exampleInput = document.getElementById('cs-expression-example');
                if (nameInput && result.name) nameInput.value = result.name;
                if (descInput && result.description) descInput.value = result.description;
                if (exampleInput && result.example) exampleInput.value = result.example;
                
                const chars = result.characteristics || [];
                for (let i = 0; i < 4; i++) {
                    const input = document.getElementById(`cs-expression-char-${i + 1}`);
                    if (input && chars[i]) input.value = chars[i];
                }
            }
        }
    }

    // ===== CREATE HANDLERS =====
    async _createPersonaType() {
        const name = document.getElementById('cs-type-name')?.value.trim();
        const description = document.getElementById('cs-type-description')?.value.trim();
        
        if (!name) { alert('Bitte gib einen Namen ein.'); return; }
        
        try {
            const response = await fetch('/api/custom-specs/persona-type', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key: name, description })
            });
            const data = await response.json();
            
            if (data.success) {
                if (!this.customSpecs.persona_spec.persona_type) this.customSpecs.persona_spec.persona_type = {};
                this.customSpecs.persona_spec.persona_type[name] = description;
                
                this._renderExistingItems('persona-type');
                this._clearInputs('cs-type-name', 'cs-type-description');
                document.getElementById('cs-type-desc-count').textContent = '0/120';
                await this._refreshPersonaCreator();
            } else {
                alert('Fehler: ' + (data.error || 'Unbekannt'));
            }
        } catch (error) {
            console.error('Fehler beim Erstellen:', error);
            alert('Verbindungsfehler');
        }
    }

    async _createCoreTrait() {
        const name = document.getElementById('cs-trait-name')?.value.trim();
        const description = document.getElementById('cs-trait-description')?.value.trim();
        const b1 = document.getElementById('cs-trait-behavior-1')?.value.trim();
        const b2 = document.getElementById('cs-trait-behavior-2')?.value.trim();
        const b3 = document.getElementById('cs-trait-behavior-3')?.value.trim();
        
        if (!name) { alert('Bitte gib einen Namen ein.'); return; }
        if (!b1 || !b2 || !b3) { alert('Bitte fülle alle 3 Verhaltensmuster aus.'); return; }
        
        try {
            const response = await fetch('/api/custom-specs/core-trait', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key: name, description, behaviors: [b1, b2, b3] })
            });
            const data = await response.json();
            
            if (data.success) {
                if (!this.customSpecs.persona_spec.core_traits_details) this.customSpecs.persona_spec.core_traits_details = {};
                this.customSpecs.persona_spec.core_traits_details[name] = { description, behaviors: [b1, b2, b3] };
                
                this._renderExistingItems('core-trait');
                this._clearInputs('cs-trait-name', 'cs-trait-description', 'cs-trait-behavior-1', 'cs-trait-behavior-2', 'cs-trait-behavior-3');
                await this._refreshPersonaCreator();
            } else {
                alert('Fehler: ' + (data.error || 'Unbekannt'));
            }
        } catch (error) {
            console.error('Fehler beim Erstellen:', error);
            alert('Verbindungsfehler');
        }
    }

    async _createKnowledge() {
        const name = document.getElementById('cs-knowledge-name')?.value.trim();
        const description = document.getElementById('cs-knowledge-description')?.value.trim();
        
        if (!name) { alert('Bitte gib einen Namen ein.'); return; }
        
        try {
            const response = await fetch('/api/custom-specs/knowledge', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key: name, description })
            });
            const data = await response.json();
            
            if (data.success) {
                if (!this.customSpecs.persona_spec.knowledge_areas) this.customSpecs.persona_spec.knowledge_areas = {};
                this.customSpecs.persona_spec.knowledge_areas[name] = description;
                
                this._renderExistingItems('knowledge');
                this._clearInputs('cs-knowledge-name', 'cs-knowledge-description');
                await this._refreshPersonaCreator();
            } else {
                alert('Fehler: ' + (data.error || 'Unbekannt'));
            }
        } catch (error) {
            console.error('Fehler beim Erstellen:', error);
            alert('Verbindungsfehler');
        }
    }

    async _createScenario() {
        const key = document.getElementById('cs-scenario-key')?.value.trim();
        const name = document.getElementById('cs-scenario-name')?.value.trim();
        const description = document.getElementById('cs-scenario-description')?.value.trim();
        const s1 = document.getElementById('cs-scenario-setting-1')?.value.trim();
        const s2 = document.getElementById('cs-scenario-setting-2')?.value.trim();
        const s3 = document.getElementById('cs-scenario-setting-3')?.value.trim();
        const s4 = document.getElementById('cs-scenario-setting-4')?.value.trim();
        
        if (!key) { alert('Bitte gib einen Key ein.'); return; }
        if (!s1 || !s2 || !s3 || !s4) { alert('Bitte fülle alle 4 Setting-Elemente aus.'); return; }
        
        try {
            const response = await fetch('/api/custom-specs/scenario', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key, name, description, setting: [s1, s2, s3, s4] })
            });
            const data = await response.json();
            
            if (data.success) {
                if (!this.customSpecs.persona_spec.scenarios) this.customSpecs.persona_spec.scenarios = {};
                this.customSpecs.persona_spec.scenarios[key] = { name: name || key, description, setting: [s1, s2, s3, s4] };
                
                this._renderExistingItems('scenario');
                this._clearInputs('cs-scenario-key', 'cs-scenario-name', 'cs-scenario-description', 
                    'cs-scenario-setting-1', 'cs-scenario-setting-2', 'cs-scenario-setting-3', 'cs-scenario-setting-4');
                await this._refreshPersonaCreator();
            } else {
                alert('Fehler: ' + (data.error || 'Unbekannt'));
            }
        } catch (error) {
            console.error('Fehler beim Erstellen:', error);
            alert('Verbindungsfehler');
        }
    }

    async _createExpressionStyle() {
        const key = document.getElementById('cs-expression-key')?.value.trim();
        const name = document.getElementById('cs-expression-name')?.value.trim();
        const description = document.getElementById('cs-expression-description')?.value.trim();
        const example = document.getElementById('cs-expression-example')?.value.trim();
        const c1 = document.getElementById('cs-expression-char-1')?.value.trim();
        const c2 = document.getElementById('cs-expression-char-2')?.value.trim();
        const c3 = document.getElementById('cs-expression-char-3')?.value.trim();
        const c4 = document.getElementById('cs-expression-char-4')?.value.trim();
        
        if (!key) { alert('Bitte gib einen Key ein.'); return; }
        
        const characteristics = [c1, c2, c3, c4].filter(Boolean);
        
        try {
            const response = await fetch('/api/custom-specs/expression-style', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key, name, description, example, characteristics })
            });
            const data = await response.json();
            
            if (data.success) {
                if (!this.customSpecs.persona_spec.expression_styles) this.customSpecs.persona_spec.expression_styles = {};
                this.customSpecs.persona_spec.expression_styles[key] = { name: name || key, description, example, characteristics };
                
                this._renderExistingItems('expression-style');
                this._clearInputs('cs-expression-key', 'cs-expression-name', 'cs-expression-description', 
                    'cs-expression-example', 'cs-expression-char-1', 'cs-expression-char-2', 'cs-expression-char-3', 'cs-expression-char-4');
                await this._refreshPersonaCreator();
            } else {
                alert('Fehler: ' + (data.error || 'Unbekannt'));
            }
        } catch (error) {
            console.error('Fehler beim Erstellen:', error);
            alert('Verbindungsfehler');
        }
    }

    // ===== RENDER EXISTING ITEMS =====
    _renderAllExistingItems() {
        this._renderExistingItems('persona-type');
        this._renderExistingItems('core-trait');
        this._renderExistingItems('knowledge');
        this._renderExistingItems('scenario');
        this._renderExistingItems('expression-style');
    }

    _renderExistingItems(category) {
        const container = document.getElementById(`cs-items-${category}`);
        if (!container) return;
        
        container.innerHTML = '';
        
        const categoryMap = {
            'persona-type': 'persona_type',
            'core-trait': 'core_traits_details',
            'knowledge': 'knowledge_areas',
            'scenario': 'scenarios',
            'expression-style': 'expression_styles'
        };
        
        const specKey = categoryMap[category];
        const items = this.customSpecs?.persona_spec?.[specKey] || {};
        const keys = Object.keys(items);
        
        if (keys.length === 0) {
            container.innerHTML = '<div class="cs-empty-message">Noch keine eigenen Einträge vorhanden.</div>';
            return;
        }
        
        keys.forEach(key => {
            const item = items[key];
            const desc = typeof item === 'string' ? item : (item.description || item.name || '');
            
            const el = document.createElement('div');
            el.className = 'cs-existing-item';
            el.innerHTML = `
                <div class="cs-existing-item-info">
                    <div class="cs-existing-item-name">${key}</div>
                    <div class="cs-existing-item-desc">${desc}</div>
                </div>
                <button class="cs-existing-item-delete" data-category="${category}" data-key="${key}" title="Löschen">✕</button>
            `;
            container.appendChild(el);
            
            // Delete handler
            el.querySelector('.cs-existing-item-delete').addEventListener('click', async (e) => {
                const cat = e.target.dataset.category;
                const k = e.target.dataset.key;
                if (!confirm(`"${k}" wirklich löschen?`)) return;
                await this._deleteItem(cat, k);
            });
        });
    }

    async _deleteItem(category, key) {
        try {
            const response = await fetch(`/api/custom-specs/${category}/${encodeURIComponent(key)}`, {
                method: 'DELETE'
            });
            const data = await response.json();
            
            if (data.success) {
                // Update local data
                const categoryMap = {
                    'persona-type': 'persona_type',
                    'core-trait': 'core_traits_details',
                    'knowledge': 'knowledge_areas',
                    'scenario': 'scenarios',
                    'expression-style': 'expression_styles'
                };
                const specKey = categoryMap[category];
                if (this.customSpecs?.persona_spec?.[specKey]?.[key]) {
                    delete this.customSpecs.persona_spec[specKey][key];
                }
                this._renderExistingItems(category);
                await this._refreshPersonaCreator();
            } else {
                alert('Fehler beim Löschen: ' + (data.error || 'Unbekannt'));
            }
        } catch (error) {
            console.error('Fehler beim Löschen:', error);
            alert('Verbindungsfehler');
        }
    }

    // ===== HELPERS =====
    _clearInputs(...ids) {
        ids.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
    }

    /**
     * Returns the set of custom spec keys for a given category.
     * Used by SettingsManager to identify which tags need custom highlighting.
     */
    getCustomKeys(category) {
        const categoryMap = {
            'persona_types': 'persona_type',
            'core_traits': 'core_traits_details',
            'knowledge': 'knowledge_areas',
            'expression_styles': 'expression_styles',
            'scenarios': 'scenarios'
        };
        const specKey = categoryMap[category];
        if (!this.customSpecs?.persona_spec?.[specKey]) return new Set();
        return new Set(Object.keys(this.customSpecs.persona_spec[specKey]));
    }
}
