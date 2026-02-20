/**
 * Compositor – Request Compositor View.
 * Phase 4: Zeigt den vollständigen Request aufgeschlüsselt nach Prompt-Blöcken.
 * Gruppiert nach API-Request-Typ (Chat, Afterthought, Summary, Spec Autofill)
 * und innerhalb jedes Typs nach System / Message.
 */
const Compositor = {
    /**
     * Compositor-Modal anzeigen.
     * @param {string} variant
     */
    async show(variant) {
        variant = variant || PromptEditor.currentVariant || 'default';

        const res = await Utils.apiCall('get_compositor_data', variant);
        if (res.status !== 'ok') {
            Utils.showToast('Compositor-Daten konnten nicht geladen werden', 'error');
            return;
        }

        const blocks = res.blocks;
        let totalTokens = 0;
        let enabledTokens = 0;

        let html = '<div class="compositor">';

        // --- Statistik-Header ---
        blocks.forEach(b => {
            totalTokens += b.tokens_est;
            if (b.enabled) enabledTokens += b.tokens_est;
        });

        html += `<div class="compositor-stats">
            <span class="compositor-stat"><strong>${blocks.length}</strong> Blöcke</span>
            <span class="compositor-stat"><strong>${blocks.filter(b => b.enabled).length}</strong> aktiv</span>
            <span class="compositor-stat"><strong>~${enabledTokens}</strong> Tokens (aktiv)</span>
            <span class="compositor-stat">Variante: <strong>${Utils.escapeHtml(variant)}</strong></span>
        </div>`;

        // --- Gruppierung nach Request-Typ ---
        const REQUEST_TYPE_LABELS = {
            'chat': 'Chat',
            'afterthought': 'Afterthought',
            'summary': 'Summary',
            'spec_autofill': 'Spec Autofill',
            'utility': 'Utility',
            'cortex': 'Cortex Update',
        };

        const REQUEST_TYPE_ORDER = ['chat', 'cortex', 'afterthought', 'summary', 'spec_autofill', 'utility'];

        for (const reqType of REQUEST_TYPE_ORDER) {
            const typeBlocks = blocks.filter(b => b.request_type === reqType);
            if (typeBlocks.length === 0) continue;

            const typeLabel = REQUEST_TYPE_LABELS[reqType] || reqType;
            const typeTokens = typeBlocks.filter(b => b.enabled).reduce((sum, b) => sum + b.tokens_est, 0);

            html += `<div class="compositor-request-type">
                <h2 class="compositor-type-title">
                    ${Utils.escapeHtml(typeLabel)}
                    <span class="token-count">~${typeTokens} Tokens</span>
                </h2>`;

            // System und Message Blöcke trennen
            const systemBlocks = typeBlocks.filter(b => b.section === 'system');
            const messageBlocks = typeBlocks.filter(b => b.section === 'message');

            if (systemBlocks.length > 0) {
                html += '<div class="compositor-section">';
                html += '<h3 class="compositor-section-title">System Prompt</h3>';
                for (const block of systemBlocks) {
                    html += this._renderBlock(block);
                }
                html += '</div>';
            }

            if (messageBlocks.length > 0) {
                html += '<div class="compositor-section">';
                html += '<h3 class="compositor-section-title">Messages</h3>';
                for (const block of messageBlocks) {
                    html += this._renderBlock(block);
                }
                html += '</div>';
            }

            html += '</div>';
        }

        html += '</div>';

        // Footer mit Varianten-Switch
        const footer = `<div style="display:flex;gap:6px;justify-content:flex-end">
            <button class="btn btn-outline btn-sm" onclick="Compositor.show('default')">Default</button>
            <button class="btn btn-outline btn-sm" onclick="Compositor.show('experimental')">Experimental</button>
        </div>`;

        Modal.show(`Request Compositor (${variant})`, html, footer);

        // Klick auf Block → Prompt im Editor öffnen
        document.querySelectorAll('.compositor-block').forEach(el => {
            el.addEventListener('click', () => {
                const id = el.dataset.compositorId;
                if (id) {
                    Modal.hide();
                    App.selectPrompt(id);
                }
            });
        });
    },

    /**
     * Render a single compositor block.
     * @param {Object} block
     * @returns {string} HTML
     */
    _renderBlock(block) {
        const catColor = PromptList.CATEGORY_COLORS[block.category] || '#888';
        const disabledClass = block.enabled ? '' : ' compositor-disabled';
        const typeBadge = block.type === 'multi_turn' ? '<span class="preview-type-badge">multi_turn</span>' : '';

        let html = `<div class="compositor-block${disabledClass}" data-compositor-id="${block.id}">
            <div class="compositor-block-header">
                <span class="compositor-dot" style="background:${catColor}"></span>
                <span class="compositor-name">${Utils.escapeHtml(block.name)}</span>
                <span class="compositor-id">${Utils.escapeHtml(block.id)}</span>
                <span class="compositor-order">#${block.order}</span>
                ${typeBadge}
                ${!block.enabled ? '<span class="ph-badge-warn">Deaktiviert</span>' : ''}
                ${block.variant_condition ? `<span class="compositor-vc" title="Variant Condition">VC: ${Utils.escapeHtml(block.variant_condition)}</span>` : ''}
                <span class="token-count">~${block.tokens_est} Tok</span>
            </div>`;

        if (block.content && block.enabled) {
            let preview = block.content;
            if (preview.length > 300) preview = preview.substring(0, 297) + '...';
            html += `<pre class="compositor-content">${Utils.highlightPlaceholders(preview)}</pre>`;
        } else if (!block.enabled) {
            html += '<div class="compositor-content-disabled">(deaktiviert)</div>';
        } else {
            html += '<div class="compositor-content-disabled">(leer)</div>';
        }

        html += '</div>';
        return html;
    }
};
