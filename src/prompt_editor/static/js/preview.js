/**
 * Preview – Preview-Panel und Full-Preview-Modal.
 */
const Preview = {
    /**
     * Einzelnen Prompt live auflösen und im Preview-Bereich anzeigen.
     * Verwendet den aktuellen Textarea-Content + geladene Placeholder-Werte
     * → zeigt Änderungen sofort vor dem Speichern.
     */
    update: Utils.debounce(function () {
        if (!PromptEditor.currentPrompt) return;

        const container = document.getElementById('preview-content');
        const raw = PromptEditor.getCurrentContent();

        if (!raw || !raw.trim()) {
            container.innerHTML = '<span class="preview-empty">(leer)</span>';
            return;
        }

        // Multi-Turn: Messages als Dialog anzeigen
        if (PromptEditor.isMultiTurn()) {
            try {
                const messages = JSON.parse(raw);
                if (!Array.isArray(messages) || messages.length === 0) {
                    container.innerHTML = '<span class="preview-empty">(keine Nachrichten)</span>';
                    return;
                }
                let html = '';
                for (const msg of messages) {
                    const resolved = (msg.content || '').replace(/\{\{(\w+)\}\}/g, (match, key) => {
                        const val = PlaceholderInfo.values[key];
                        if (val !== undefined && val !== null && val !== '') return val;
                        return match;
                    });
                    const roleClass = msg.role === 'assistant' ? 'mt-role-assistant' : 'mt-role-user';
                    html += `<div class="preview-msg">
                        <span class="preview-msg-role ${roleClass}">${msg.role === 'assistant' ? 'Assistant' : 'User'}</span>
                        <span class="preview-msg-text">${Utils.highlightPlaceholders(resolved)}</span>
                    </div>`;
                }
                container.innerHTML = html;
            } catch {
                container.innerHTML = '<span class="preview-error">Ung\u00fcltiges Format</span>';
            }
            return;
        }

        // Regular: Client-side Placeholder-Aufl\u00f6sung
        const resolved = raw.replace(/\{\{(\w+)\}\}/g, (match, key) => {
            const val = PlaceholderInfo.values[key];
            if (val !== undefined && val !== null && val !== '') return val;
            return match;   // unbekannte bleiben stehen
        });

        container.innerHTML = Utils.highlightPlaceholders(resolved);
    }, 200),

    /**
     * Full Preview im Modal mit Kategorie-Tabs.
     * @param {string} [variant]
     * @param {string} [category]  'chat'|'afterthought'|'summary'|'spec_autofill'
     */
    async showFullPreview(variant, category) {
        variant  = variant  || PromptEditor.currentVariant || 'default';
        category = category || 'chat';

        const categories = [
            { key: 'chat',             label: 'Chat' },
            { key: 'afterthought',     label: 'Afterthought' },
            { key: 'summary',          label: 'Summary' },
            { key: 'spec_autofill',    label: 'Spec Autofill' },
        ];

        let html = '<div class="preview-cat-tabs">';
        for (const cat of categories) {
            const active = cat.key === category ? ' active' : '';
            html += `<button class="ph-tab${active}" onclick="Preview.showFullPreview('${variant}','${cat.key}')">${cat.label}</button>`;
        }
        html += '</div>';

        html += '<div class="full-preview">';

        if (category === 'chat') {
            // Chat: Special view with System / Message sections
            const res = await Utils.apiCall('preview_chat', variant);
            if (res.status !== 'ok') {
                Utils.showToast('Preview-Fehler: ' + (res.message || ''), 'error');
                return;
            }

            // --- System Section ---
            if (res.system_blocks.length > 0) {
                html += '<div class="preview-section-group">';
                html += '<h2 class="preview-group-title">System Prompt</h2>';
                for (const block of res.system_blocks) {
                    html += this._renderPreviewBlock(block);
                }
                html += '</div>';
            }

            // --- Message Section ---
            if (res.message_blocks.length > 0) {
                html += '<div class="preview-section-group">';
                html += '<h2 class="preview-group-title">Messages</h2>';
                for (const block of res.message_blocks) {
                    html += this._renderPreviewBlock(block);
                }
                html += '</div>';
            }

            if (res.system_blocks.length === 0 && res.message_blocks.length === 0) {
                html += '<p class="preview-empty">Keine aktiven Prompts für Chat.</p>';
            } else {
                html += `<div class="preview-total">Gesamt: ~${res.total_tokens_est} Tokens (${res.system_blocks.length + res.message_blocks.length} Prompts)</div>`;
            }
        } else {
            // Afterthought, Summary, Spec Autofill: grouped by System/Message
            const res = await Utils.apiCall('preview_category', category, variant);
            if (res.status !== 'ok') {
                Utils.showToast('Preview-Fehler: ' + (res.message || ''), 'error');
                return;
            }

            if (res.blocks.length === 0) {
                html += '<p class="preview-empty">Keine aktiven Prompts in dieser Kategorie.</p>';
            } else {
                const systemBlocks = res.blocks.filter(b => b.target === 'system_prompt');
                const messageBlocks = res.blocks.filter(b => b.target !== 'system_prompt');

                if (systemBlocks.length > 0) {
                    html += '<div class="preview-section-group">';
                    html += '<h2 class="preview-group-title">System Prompt</h2>';
                    for (const block of systemBlocks) {
                        html += this._renderPreviewBlock(block);
                    }
                    html += '</div>';
                }

                if (messageBlocks.length > 0) {
                    html += '<div class="preview-section-group">';
                    html += '<h2 class="preview-group-title">Messages</h2>';
                    for (const block of messageBlocks) {
                        html += this._renderPreviewBlock(block);
                    }
                    html += '</div>';
                }

                html += `<div class="preview-total">Gesamt: ~${res.total_tokens_est} Tokens (${res.blocks.length} Prompts)</div>`;
            }
        }

        html += '</div>';

        // Footer: Variant-Switch + Compositor-Link
        const footer = `
            <div style="display:flex;gap:6px;justify-content:space-between;align-items:center">
                <button class="btn btn-outline btn-sm" onclick="Modal.hide(); Compositor.show('${variant}')">Compositor \u2192</button>
                <div style="display:flex;gap:6px">
                    <button class="btn btn-outline btn-sm${variant === 'default' ? ' btn-active' : ''}" onclick="Preview.showFullPreview('default','${category}')">Default</button>
                    <button class="btn btn-outline btn-sm${variant === 'experimental' ? ' btn-active' : ''}" onclick="Preview.showFullPreview('experimental','${category}')">Experimental</button>
                </div>
            </div>
        `;

        Modal.show(`Preview – ${categories.find(c => c.key === category)?.label || category} (${variant})`, html, footer);

        // Klick auf Prompt-Name → Prompt öffnen
        document.querySelectorAll('.full-preview .ph-usage-link').forEach(link => {
            link.addEventListener('click', () => {
                const pid = link.dataset.gotoPrompt;
                if (pid) {
                    Modal.hide();
                    App.selectPrompt(pid);
                }
            });
        });
    },

    /**
     * Render a single preview block.
     * @param {Object} block
     * @returns {string} HTML
     */
    _renderPreviewBlock(block) {
        const posLabel = block.position && block.position !== block.target ? ` → ${block.position}` : '';
        const catBadge = block.category ? `<span class="preview-cat-badge">${block.category}</span>` : '';
        const typeBadge = block.type === 'multi_turn' ? '<span class="preview-type-badge">multi_turn</span>' : '';
        return `
            <div class="preview-section">
                <h3>
                    <span class="ph-usage-link" data-goto-prompt="${block.id}">${Utils.escapeHtml(block.name)}</span>
                    ${catBadge}${typeBadge}
                    <span class="token-count">${block.target}${posLabel} · ~${block.tokens_est} Tokens</span>
                </h3>
                <pre class="preview-pre">${block.content ? Utils.highlightPlaceholders(block.content) : '<span class="preview-empty">(leer / variant-bedingt ausgeblendet)</span>'}</pre>
            </div>`;
    }
};
