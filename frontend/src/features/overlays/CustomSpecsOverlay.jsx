// ── CustomSpecsOverlay ──
// 5 category tabs with expandable forms for custom persona specs
// Per-field autofill: each field gets its own ✨ button + optional hint textarea
// Pattern: ifaceSection / ifaceCard (like InterfaceSettingsOverlay)

import { useState, useEffect } from 'react';
import Overlay from '../../components/Overlay/Overlay';
import OverlayHeader from '../../components/Overlay/OverlayHeader';
import { GearIcon } from '../../components/Icons/Icons';
import OverlayBody from '../../components/Overlay/OverlayBody';
import Button from '../../components/Button/Button';
import Spinner from '../../components/Spinner/Spinner';
import { createCustomSpec, autofillCustomSpec } from '../../services/customSpecsApi';
import styles from './Overlays.module.css';

// ── Categories (no emojis) ──
const CATEGORIES = [
  { key: 'persona-type', label: 'Persona Typ' },
  { key: 'core-trait', label: 'Core Trait' },
  { key: 'knowledge', label: 'Wissen' },
  { key: 'scenario', label: 'Szenario' },
  { key: 'expression-style', label: 'Schreibstil' },
];

// ── Helpers ──
const toKey = (name) => (name || '').trim().toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '').slice(0, 30);

// Map frontend tab keys to backend spec_type values
const toSpecType = (tab) => tab.replace(/-/g, '_');

// Initial form state per category
const makeInitialForm = (cat) => {
  switch (cat) {
    case 'persona-type':
    case 'knowledge':
      return { name: '', description: '' };
    case 'core-trait':
      return { name: '', description: '', items: [''] };
    case 'scenario':
      return { name: '', description: '', items: [''] };
    case 'expression-style':
      return { name: '', description: '', example: '', items: [''] };
    default:
      return { name: '', description: '' };
  }
};

// Which categories have expandable items
const HAS_ITEMS = { 'core-trait': true, scenario: true, 'expression-style': true };
const ITEM_LABEL = {
  'core-trait': 'Verhaltensweise',
  scenario: 'Setting',
  'expression-style': 'Merkmal',
};
const ITEM_MAX = 6;

export default function CustomSpecsOverlay({ open, onClose, onOpenList }) {
  const [activeTab, setActiveTab] = useState('persona-type');
  const [forms, setForms] = useState(() =>
    Object.fromEntries(CATEGORIES.map((c) => [c.key, makeInitialForm(c.key)]))
  );
  // Per-field filling state: { description: false, example: false, items: false }
  const [fillingField, setFillingField] = useState({});

  useEffect(() => {
    if (open) {
      setActiveTab('persona-type');
      setForms(Object.fromEntries(CATEGORIES.map((c) => [c.key, makeInitialForm(c.key)])));
      setFillingField({});
    }
  }, [open]);

  const isFilling = Object.values(fillingField).some(Boolean);

  // ── Form Helpers ──
  const form = forms[activeTab] || {};

  const updateField = (field, value) => {
    setForms((prev) => ({
      ...prev,
      [activeTab]: { ...prev[activeTab], [field]: value },
    }));
  };

  const updateItem = (index, value) => {
    setForms((prev) => {
      const items = [...(prev[activeTab].items || [])];
      items[index] = value;
      return { ...prev, [activeTab]: { ...prev[activeTab], items } };
    });
  };

  const addItem = () => {
    setForms((prev) => {
      const items = [...(prev[activeTab].items || [])];
      if (items.length >= ITEM_MAX) return prev;
      return { ...prev, [activeTab]: { ...prev[activeTab], items: [...items, ''] } };
    });
  };

  const removeItem = (index) => {
    setForms((prev) => {
      const items = [...(prev[activeTab].items || [])];
      if (items.length <= 1) return prev;
      items.splice(index, 1);
      return { ...prev, [activeTab]: { ...prev[activeTab], items } };
    });
  };

  const resetForm = () => {
    setForms((prev) => ({ ...prev, [activeTab]: makeInitialForm(activeTab) }));
  };

  // ── Per-Field Auto-Fill ──
  // field: 'description' | 'example' | 'items'
  // The current text in the field is sent as a hint to the AI
  const handleFieldAutofill = async (field) => {
    if (!form.name) return;

    // Determine hint: current field value that user may have typed
    let hint = '';
    if (field === 'description') hint = form.description || '';
    else if (field === 'example') hint = form.example || '';
    else if (field === 'items') hint = (form.items || []).filter(Boolean).join(', ');

    setFillingField((prev) => ({ ...prev, [field]: true }));
    try {
      const resp = await autofillCustomSpec({
        type: toSpecType(activeTab),
        field,
        input: form.name,
        hint: hint.trim(),
        item_count: (form.items || []).length || 3,
      });

      if (field === 'items' && resp?.items) {
        // Fill items array
        const newItems = [...(form.items || [])];
        const items = resp.items;
        for (let i = 0; i < newItems.length && i < items.length; i++) {
          newItems[i] = items[i];
        }
        updateField('items', newItems);
      } else if (resp?.text) {
        updateField(field, resp.text);
      } else {
        console.warn('[AutoFill] Unexpected response:', resp);
      }
    } catch (err) {
      console.error('[AutoFill] Error:', err);
    } finally {
      setFillingField((prev) => ({ ...prev, [field]: false }));
    }
  };

  // ── Create ──
  const handleCreate = async () => {
    const key = toKey(form.name);
    if (!key) return;

    let body;
    const items = (form.items || []).filter(Boolean);

    switch (activeTab) {
      case 'persona-type':
      case 'knowledge':
        body = { key, description: form.description };
        break;
      case 'core-trait':
        body = { key, description: form.description, behaviors: items };
        break;
      case 'scenario':
        body = { key, name: form.name, description: form.description, setting: items };
        break;
      case 'expression-style':
        body = { key, name: form.name, description: form.description, example: form.example, characteristics: items };
        break;
    }

    try {
      await createCustomSpec(activeTab, body);
      resetForm();
    } catch (err) {
      console.error('Create spec failed:', err);
    }
  };

  // ── Tab Change ──
  const handleTabChange = (key) => {
    setActiveTab(key);
    setFillingField({});
  };

  const hasItems = HAS_ITEMS[activeTab];
  const itemLabel = ITEM_LABEL[activeTab] || 'Eintrag';
  const derivedKey = toKey(form.name);

  // ── Autofill Button helper ──
  const AutofillBtn = ({ field }) => (
    <Button
      variant="secondary"
      size="sm"
      onClick={() => handleFieldAutofill(field)}
      disabled={isFilling || !form.name}
      title="KI generiert dieses Feld basierend auf dem Namen"
    >
      {fillingField[field] ? 'Generiert...' : 'Auto-Fill'}
    </Button>
  );

  return (
    <Overlay open={open} onClose={onClose} width="600px">
      <OverlayHeader title="Custom Specs" icon={<GearIcon size={20} />} onClose={onClose} />
      <OverlayBody>

        {/* ═══ Section: Kategorie ═══ */}
        <div className={styles.ifaceSection}>
          <h3 className={styles.ifaceSectionTitle}>Kategorie</h3>
          <div className={styles.ifaceCard}>
            <div className={styles.cortexTabBar}>
              {CATEGORIES.map((cat) => (
                <button
                  key={cat.key}
                  type="button"
                  className={`${styles.cortexTab} ${activeTab === cat.key ? styles.cortexTabActive : ''}`}
                  onClick={() => handleTabChange(cat.key)}
                >
                  {cat.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* ═══ Section: Neuer Eintrag ═══ */}
        <div className={styles.ifaceSection}>
          <h3 className={styles.ifaceSectionTitle}>Neuer Eintrag</h3>
          <div className={styles.ifaceCard}>

            {/* Name */}
            <div className={styles.ifaceFieldGroup}>
              <span className={styles.ifaceFieldLabel}>Name</span>
              <input
                className={styles.textInput}
                value={form.name}
                onChange={(e) => updateField('name', e.target.value)}
                maxLength={40}
                placeholder="Name eingeben"
                disabled={isFilling}
              />
              {derivedKey && (
                <span className={styles.csKeyPreview}>
                  Key: {derivedKey}
                </span>
              )}
            </div>

            <div className={styles.ifaceDivider} />

            {/* Description with per-field autofill */}
            <div className={styles.ifaceFieldGroup}>
              <div className={styles.csFieldHeader}>
                <span className={styles.ifaceFieldLabel}>Beschreibung</span>
                <AutofillBtn field="description" />
              </div>
              <span className={styles.ifaceFieldHint}>
                Eigenen Text eingeben oder Auto-Fill nutzen — vorhandener Text dient als Hinweis
              </span>
              <div className={styles.backgroundTextareaWrapper}>
                <textarea
                  className={styles.textarea}
                  value={form.description}
                  onChange={(e) => updateField('description', e.target.value)}
                  rows={3}
                  placeholder="Beschreibung eingeben oder leer lassen für Auto-Fill..."
                  disabled={fillingField.description}
                />
                {fillingField.description && (
                  <div className={styles.autofillOverlay}>
                    <Spinner />
                    <span className={styles.autofillOverlayText}>Generiere Beschreibung...</span>
                  </div>
                )}
              </div>
            </div>

            {/* Example (expression-style only) with per-field autofill */}
            {activeTab === 'expression-style' && (
              <>
                <div className={styles.ifaceDivider} />
                <div className={styles.ifaceFieldGroup}>
                  <div className={styles.csFieldHeader}>
                    <span className={styles.ifaceFieldLabel}>Beispiel</span>
                    <AutofillBtn field="example" />
                  </div>
                  <span className={styles.ifaceFieldHint}>Ein typischer Satz in diesem Schreibstil</span>
                  <div className={styles.backgroundTextareaWrapper}>
                    <textarea
                      className={styles.textarea}
                      value={form.example}
                      onChange={(e) => updateField('example', e.target.value)}
                      rows={2}
                      placeholder="Beispiel-Text eingeben oder Auto-Fill nutzen..."
                      disabled={fillingField.example}
                    />
                    {fillingField.example && (
                      <div className={styles.autofillOverlay}>
                        <Spinner />
                        <span className={styles.autofillOverlayText}>Generiere Beispiel...</span>
                      </div>
                    )}
                  </div>
                </div>
              </>
            )}

            {/* Expandable Items (core-trait / scenario / expression-style) with per-field autofill */}
            {hasItems && (
              <>
                <div className={styles.ifaceDivider} />
                <div className={styles.ifaceFieldGroup}>
                  <div className={styles.csFieldHeader}>
                    <div className={styles.csItemsHeader}>
                      <span className={styles.ifaceFieldLabel}>
                        {itemLabel === 'Verhaltensweise' ? 'Verhaltensweisen' : itemLabel === 'Setting' ? 'Settings' : 'Merkmale'}
                      </span>
                      <span className={styles.ifaceFieldHint} style={{ margin: 0 }}>
                        {(form.items || []).length} / {ITEM_MAX}
                      </span>
                    </div>
                    <AutofillBtn field="items" />
                  </div>
                  <span className={styles.ifaceFieldHint}>
                    Items hinzufügen, dann Auto-Fill nutzen — bestehender Text dient als Hinweis
                  </span>

                  <div className={styles.csItemsList}>
                    {(form.items || []).map((item, idx) => (
                      <div key={idx} className={styles.csItemRow}>
                        <textarea
                          className={styles.textarea}
                          value={item}
                          onChange={(e) => updateItem(idx, e.target.value)}
                          rows={2}
                          placeholder={`${itemLabel} ${idx + 1}`}
                          disabled={fillingField.items}
                        />
                        {(form.items || []).length > 1 && (
                          <button
                            type="button"
                            className={styles.csRemoveItemBtn}
                            onClick={() => removeItem(idx)}
                            title="Entfernen"
                            disabled={isFilling}
                          >
                            &minus;
                          </button>
                        )}
                      </div>
                    ))}
                  </div>

                  {fillingField.items && (
                    <div className={styles.csItemsGenerating}>
                      <Spinner size={14} /> Generiere...
                    </div>
                  )}

                  {(form.items || []).length < ITEM_MAX && (
                    <button
                      type="button"
                      className={styles.csAddItemBtn}
                      onClick={addItem}
                      disabled={isFilling}
                    >
                      + {itemLabel} hinzufuegen
                    </button>
                  )}
                </div>
              </>
            )}

            <div className={styles.ifaceDivider} />

            {/* Actions */}
            <div className={styles.csFormActions}>
              <Button
                variant="primary"
                size="sm"
                onClick={handleCreate}
                disabled={isFilling || !form.name}
              >
                Erstellen
              </Button>
            </div>
          </div>
        </div>

        {/* ═══ Link to library ═══ */}
        {onOpenList && (
          <div className={styles.cslLinkRow}>
            <button type="button" className={styles.cslLinkBtn} onClick={onOpenList}>
              Vorhandene Specs anzeigen
            </button>
          </div>
        )}

      </OverlayBody>
    </Overlay>
  );
}
